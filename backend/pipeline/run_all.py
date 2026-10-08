"""Run the whole offline pipeline and write the region's processed folder.

    python -m backend.pipeline.run_all                         # US: score with the saved models
    python -m backend.pipeline.run_all --retrain               # US: retrain and overwrite backend/models/
    python -m backend.pipeline.run_all --region in [--retrain] # India: data/india/ -> data/india/processed/,
                                                               #   models in backend/models/india/
"""
import json
import sys

import numpy as np
import pandas as pd

from backend import region
from backend.brain import wiki

from . import anomaly, graph, predict, reference, reference_in, rules, rules_in
from .common import load

SEVERITY = {"collusive_ring": 1.0, "impossible_timing": 0.9, "upcoding": 0.7, "duplicate_billing": 0.6,
            "unbundling": 0.5, "excessive_utilization": 0.5}
RULE_PATTERN = {"mue_exceeded": "excessive_utilization"}
# India (PM-JAY): patient harm and billing for people who were not treated rank highest.
SEVERITY_IN = {"collusive_ring": 1.0, "claim_after_death": 1.0, "ghost_beneficiary": 0.95, "unnecessary_procedure": 0.9,
               "overlapping_admission": 0.9, "duplicate_document": 0.85, "bed_overrun": 0.8, "package_upcoding": 0.7,
               "opd_to_ipd": 0.6, "duplicate_package": 0.6, "excessive_utilization": 0.5}
RULE_PATTERN_IN = {"package_mismatch": "package_upcoding", "ward_upcoding": "package_upcoding", "age_audit": "unnecessary_procedure",
                   "camp_cluster": "unnecessary_procedure", "long_stay": "excessive_utilization",
                   "suspicious_identity": "ghost_beneficiary", "not_empanelled": "bed_overrun"}
# India pattern when only the anomaly model fired: the first anomaly driver that names a pattern
DRIVER_PATTERN_IN = [("ICU", "package_upcoding"), ("per bed", "bed_overrun"), ("0-1 day", "opd_to_ipd"),
                     ("cards under 30 days", "ghost_beneficiary"), ("agent-referred", "unnecessary_procedure")]


def main(train=False, code="us"):
    with region.use(code):
        _run(train)


def _run(train):
    R = region.current()
    india = R.code == "in"
    PROC = R.proc
    PROC.mkdir(parents=True, exist_ok=True)
    claims, prov, fac, members = load("claims"), load("providers"), load("facilities"), load("members")
    referrals, inv, own, gt = load("referrals"), load("investigations"), load("ownership"), load("ground_truth")
    owner_name = own.drop_duplicates("owner_id").set_index("owner_id").owner_name.to_dict()

    # 1 rules
    if india:
        flags, RULES, severity, rule_pattern = rules_in.run(claims, prov, members), rules_in.RULES, SEVERITY_IN, RULE_PATTERN_IN
    else:
        flags, RULES, severity, rule_pattern = rules.run(claims, fac), rules.RULES, SEVERITY, RULE_PATTERN
    flags.to_csv(PROC / "claim_flags.csv", index=False)
    uniq = flags.drop_duplicates("claim_id")
    n_claims = claims.groupby("provider_id").size()
    n_flag = uniq.groupby("provider_id").size().reindex(n_claims.index).fillna(0)
    rule_score = (0.6 * (n_flag / 25).clip(upper=1) + 0.4 * (n_flag / n_claims / 0.10).clip(upper=1)).round(4)

    # 2 anomaly
    feats, m_anom = anomaly.run(claims, prov, labels=gt, train=train, members=members)

    # 3 graph
    prior_confirmed = set(inv[inv.verdict == "confirmed"].provider_id)
    seeds = {p: float(rule_score[p]) + (1.0 if p in prior_confirmed else 0.0) for p in n_claims.index}
    net, edges, clusters = graph.run(claims, prov, members, referrals, seeds)
    edges.to_csv(PROC / "edges.csv", index=False)

    # 4 prediction
    pred, m_pred = predict.run(claims, flags, inv, train=train)

    S = (prov.merge(feats.drop(columns=["specialty"]), on="provider_id").merge(net, on="provider_id")
         .merge(pred, on="provider_id"))
    S["n_flagged"] = S.provider_id.map(n_flag).astype(int)
    S["rule_score"] = S.provider_id.map(rule_score)
    S.drop(columns=["drivers"]).to_csv(PROC / "provider_scores.csv", index=False)

    # 5 cases
    peer_paid = S.groupby("specialty").total_paid.transform("median")
    S["excess_paid"] = (S.total_paid - peer_paid).clip(lower=0)
    cand = S[(S.n_flagged >= 3) | (S.p_anomaly >= 0.25) | (S.cluster_score > 0)]
    claims["month"] = claims.service_datetime.dt.strftime("%Y-%m")
    flagged_ids = set(uniq.claim_id)
    cases = []
    for r in cand.itertuples():
        pid = r.provider_id
        pf = flags[flags.provider_id == pid]
        pu = pf.drop_duplicates("claim_id")
        pc = claims[claims.provider_id == pid]
        cl = clusters.get(r.cluster_id)
        counts = pf.rule.value_counts()
        by_pattern = pf.assign(p=pf.rule.map(lambda x: rule_pattern.get(x, x))).p.value_counts()
        if cl:
            pattern = "collusive_ring"
        elif len(pu) >= 3:
            pattern = by_pattern.index[0]
        elif india:
            pattern = next((p for key, p in DRIVER_PATTERN_IN if key in r.drivers), "excessive_utilization")
        else:
            pattern = "upcoding" if "level-5" in r.drivers else "excessive_utilization"

        evidence, refs = [], []
        for rule, n in counts.items():
            sub = pf[pf.rule == rule]
            evidence.append({
                "type": "rule", "rule": RULES[rule],
                "text": f"{n} claims flagged by {RULES[rule]}, {R.money(sub.paid_amount.sum())} paid",
                "source": rules_in.SOURCE[rule] if india else
                "claims.csv: member_id, provider_id, procedure_code, units, billed_amount, service_datetime, facility_id",
                "claim_ids": sub.claim_id.head(5).tolist()})
        if r.p_anomaly >= 0.25 or r.drivers:
            evidence.append({
                "type": "ml", "rule": "Isolation Forest + isotonic calibration",
                "text": f"Anomaly probability {r.p_anomaly:.0%}" + (f"; drivers: {r.drivers}" if r.drivers else ""),
                "source": "hospital features from claims.csv and members.csv, compared with hospitals of the same type" if india
                else "provider features from claims.csv, compared with same-specialty peers", "claim_ids": []})
        shared_ids = set(cl["shared_member_ids"]) if cl else set()
        if cl and india:
            evidence.append({
                "type": "graph", "rule": f"{cl['method'].title()} community + agents and referral cycles",
                "text": (f"Member of network {cl['cluster_id']}: {cl['size']} hospitals sharing {cl['shared_members']} beneficiaries"
                         + (f"; {cl['owner_share']:.0%} share owner {cl['top_owner']}" if cl["top_owner"] else "")
                         + (f"; agent {cl['top_agent']} brought {cl['agent_share']:.0%} of their admissions" if cl["agent_share"] >= 0.2 else "")
                         + (f"; {cl['village_share']:.0%} of the shared beneficiaries live in villages {', '.join(cl['top_villages'])}"
                            if cl["village_share"] >= 0.5 else "")
                         + ("; referrals form a closed loop" if cl["referral_cycle"] else "")),
                "source": "claims.csv beneficiary overlap and referred_by_agent_id, referrals.csv, ownership.csv, members.csv village_code",
                "claim_ids": []})
        elif cl:
            evidence.append({
                "type": "graph", "rule": f"{cl['method'].title()} community + referral cycles",
                "text": (f"Member of network {cl['cluster_id']}: {cl['size']} providers sharing {cl['shared_members']} members; "
                         f"{cl['owner_share']:.0%} share owner {cl['top_owner']}"
                         + ("; referrals form a closed loop" if cl["referral_cycle"] else "")),
                "source": "claims.csv member overlap, referrals.csv, ownership.csv", "claim_ids": []})
        if r.birank >= 0.3 and not cl:
            evidence.append({"type": "graph", "rule": "BiRank propagation",
                             "text": f"Network risk {r.birank:.2f} of 1.00, propagated from flagged "
                                     + ("hospitals through shared beneficiaries" if india else "providers through shared members"),
                             "source": "claims.csv provider-member graph", "claim_ids": []})
        prior = inv[inv.provider_id == pid]
        for q in prior.itertuples():
            evidence.append({"type": "history", "rule": "Prior investigation",
                             "text": f"Prior case {q.case_id} ({q.pattern.replace('_', ' ')}) closed {q.closed_date}: {q.verdict}",
                             "source": "investigations.csv", "claim_ids": []})

        if cl:
            net_claims = pc[pc.member_id.isin(shared_ids)]
            dollars = float(net_claims.paid_amount.sum()) + float(pu[~pu.claim_id.isin(net_claims.claim_id)].paid_amount.sum())
            impact = int(pd.concat([net_claims.member_id, pu.member_id]).nunique())
        elif len(pu) >= 3:
            dollars, impact = float(pu.paid_amount.sum()), int(pu.member_id.nunique())
        else:
            dollars, impact = float(r.excess_paid), int(r.n_members)

        if len(pu):
            samp = pf.sort_values("paid_amount", ascending=False).drop_duplicates("claim_id").head(8)
            sample = [{"claim_id": s.claim_id, "date": str(s.service_datetime)[:16], "member_id": s.member_id,
                       "procedure_code": s.procedure_code, "facility_id": s.facility_id, "paid_amount": s.paid_amount,
                       "rule": RULES[s.rule], "detail": s.detail, **_package(s.procedure_code, india)} for s in samp.itertuples()]
        elif cl:
            samp = pc[pc.member_id.isin(shared_ids)].sort_values("paid_amount", ascending=False).head(8)
            sample = [{"claim_id": s.claim_id, "date": str(s.service_datetime)[:16], "member_id": s.member_id,
                       "procedure_code": s.procedure_code, "facility_id": s.facility_id, "paid_amount": s.paid_amount,
                       "rule": "Network", "detail": ("Beneficiary also admitted by 3+ hospitals in the same network" if india
                                                     else "Member also billed by 3+ providers in the same network"),
                       **_package(s.procedure_code, india)} for s in samp.itertuples()]
        else:
            sample = []

        monthly = pc.groupby("month").agg(claims=("claim_id", "size"), paid=("paid_amount", "sum"))
        monthly["flagged"] = pc[pc.claim_id.isin(flagged_ids)].groupby("month").size()
        timeline = [{"month": m, "claims": int(v.claims), "paid": round(float(v.paid), 2),
                     "flagged": int(v.flagged) if pd.notna(v.flagged) else 0} for m, v in monthly.iterrows()]
        events = [{"date": str(q.closed_date), "event": f"Prior case {q.case_id} closed: {q.verdict}"} for q in prior.itertuples()]
        if len(pu):
            events.append({"date": str(pu.service_datetime.min())[:10], "event": "First rule flag"})
            events.append({"date": str(pu.service_datetime.max())[:10], "event": "Most recent rule flag"})

        families = {"rules": float(r.rule_score), "ml": float(r.p_anomaly), "graph": float(r.cluster_score)}
        agree = sum([families["rules"] >= 0.3, families["ml"] >= 0.25, families["graph"] >= 0.5])
        strength = min(1.0, 0.5 * families["rules"] + 0.2 * min(1, families["ml"] * 2) + 0.4 * families["graph"]
                       + (0.15 if agree >= 2 else 0))
        cases.append({
            "case_id": f"CASE-{pid}", "provider_id": pid, "provider_name": r.name, "specialty": r.specialty,
            "city": r.city, "facility_id": r.facility_id, "owner_id": r.owner_id,
            "owner_name": owner_name.get(r.owner_id, ""), "pattern": pattern,
            "signals": {**{k: round(v, 3) for k, v in families.items()}, "birank": float(r.birank), "families_agreeing": agree},
            "evidence_strength": round(strength, 3), "severity": severity[pattern],
            "prediction": {"p30": float(r.p30), "p60": float(r.p60), "p90": float(r.p90),
                           "volume_velocity": float(r.volume_velocity), "flag_velocity": float(r.flag_velocity)},
            "potential_dollars": round(dollars, 2), "member_impact": impact,
            "n_claims": int(r.n_claims), "n_flagged": int(r.n_flagged), "total_paid": round(float(r.total_paid), 2),
            "rule_counts": {RULES[k]: int(v) for k, v in counts.items()},
            "anomaly_drivers": r.drivers, "evidence": evidence, "sample_claims": sample,
            "timeline": timeline, "events": sorted(events, key=lambda e: e["date"]),
            "network": ({k: v for k, v in cl.items() if k != "shared_member_ids"} if cl else None),
            "codes": sorted(pc.procedure_code.unique().tolist()),
            **({"hospital": {"state": r.state, "district": r.district, "beds": int(r.beds), "city_tier": r.city_tier,
                             "nabh_status": r.nabh_status, "sector": r.sector, "teaching": bool(r.teaching)}} if india else {}),
        })
    (PROC / "cases.json").write_text(json.dumps(cases, indent=1, default=_j))
    (PROC / "clusters.json").write_text(json.dumps(
        {k: {a: b for a, b in v.items() if a != "shared_member_ids"} for k, v in clusters.items()}, indent=1, default=_j))

    # 6 evaluation against the injected labels (never used as model features)
    fwa = set(gt[gt.is_fwa == 1].provider_id)
    legit = set(gt[gt.pattern.str.startswith("legit")].provider_id)
    in_queue = {c["provider_id"] for c in cases}
    labels = load("claim_labels")
    lab = labels.set_index("claim_id").injected_pattern
    rule_recall = {}
    for pat in (sorted(lab.unique()) if india else ["duplicate_billing", "upcoding", "impossible_timing", "unbundling"]):
        ids = set(lab[lab == pat].index)
        rule_recall[pat] = round(len(ids & flagged_ids) / len(ids), 3)
    metrics = {
        "note": "Evaluated against injected synthetic scenarios. Not evidence of performance on real claims.",
        "funnel": {"claims": int(len(claims)), "raw_alerts": int(len(flags)), "providers_with_any_alert": int((n_flag > 0).sum()),
                   "cases": len(cases)},
        "provider_level": {"fwa_providers": len(fwa), "fwa_in_queue": len(fwa & in_queue),
                           "recall": round(len(fwa & in_queue) / len(fwa), 3),
                           "queue_precision": round(len(fwa & in_queue) / len(cases), 3),
                           "legit_outliers_in_queue": len(legit & in_queue)},
        "claim_level": {"flag_precision": round(float(uniq.claim_id.isin(lab.index).mean()), 3), "recall_by_pattern": rule_recall},
        "anomaly": m_anom,
        "prediction": m_pred,
        "rule_tables": ({"packages": reference_in.SOURCE} if india else
                        {"bundling_pairs": reference.PTP_SOURCE, "unit_limits": reference.MUE_SOURCE}),
        "network": {"clusters": len(clusters), "method": next(iter(clusters.values()))["method"] if clusters else "none"},
    }
    if india:  # a wrong flag delays a hospital's payment or a patient's discharge, so false positives are reported too
        normal = set(gt[gt.pattern == "normal"].provider_id)
        metrics["false_positives"] = {
            "normal_hospitals_in_queue": len(normal & in_queue),
            "flagged_claims_not_injected": int((~uniq.claim_id.isin(lab.index)).sum()),
            "flagged_claims": int(len(uniq)),
        }
    (PROC / "metrics.json").write_text(json.dumps(metrics, indent=1, default=_j))

    # 7 second brain
    wiki.seed(inv, prov)
    if india:  # triage as the API serves it: tiers include the precedents just seeded into the Second Brain
        from backend.app import store
        store._DATA.pop(R.code, None)
        metrics["triage"] = _triage(store.queue(90, 3)["cases"], fwa)
        (PROC / "metrics.json").write_text(json.dumps(metrics, indent=1, default=_j))
    print(json.dumps({k: metrics[k] for k in ("funnel", "provider_level", "claim_level", "anomaly", "network")}, indent=1))
    print("prediction:", {k: v for k, v in m_pred.items() if k.endswith("d")})


def _package(code, india):
    if not india:
        return {}
    pk = reference_in.PACKAGES
    name = pk.procedure_name.get(code, code)
    return {"package": name if pk.rate_source.get(code) == "verified" else f"{name} (estimated rate)"}


def _triage(rows, fwa):
    """Precision and recall of what investigators see: actionable cases (high and medium tiers), the watch list
    (low tier: weak evidence, monitored, not opened) and the cases that fit 3 investigators' capacity."""
    def pr(sel):
        hit = sum(r["provider_id"] in fwa for r in sel)
        return {"cases": len(sel), "planted": hit, "precision": round(hit / len(sel), 3) if sel else None,
                "recall": round(hit / len(fwa), 3)}
    open_ = [r for r in rows if r["status"] == "open"]
    return {"actionable": pr([r for r in open_ if r["tier"] != "low"]), "watch_list": pr([r for r in open_ if r["tier"] == "low"]),
            "at_capacity_3_investigators": pr([r for r in rows if r["in_capacity"]]), "all_candidates": pr(open_)}


def _j(o):
    if isinstance(o, np.generic):
        return o.item()
    return str(o)


if __name__ == "__main__":
    main(train="--retrain" in sys.argv, code=sys.argv[sys.argv.index("--region") + 1] if "--region" in sys.argv else "us")
