"""Loads the precomputed pipeline outputs and joins them with the live Second Brain."""
import json
import math

import pandas as pd

from backend.brain import brief, confidence, retrieve, wiki
from backend.pipeline.common import PROC, RAW

CASES = {c["case_id"]: c for c in json.loads((PROC / "cases.json").read_text())}
METRICS = json.loads((PROC / "metrics.json").read_text())
EDGES = pd.read_csv(PROC / "edges.csv")
PROV = pd.read_csv(RAW / "providers.csv")
PROV_INFO = PROV.set_index("provider_id").to_dict("index")
FAC = pd.read_csv(RAW / "facilities.csv").set_index("facility_id").to_dict("index")
OWNERS = pd.read_csv(RAW / "ownership.csv").drop_duplicates("owner_id").set_index("owner_id").owner_name.to_dict()
SCORES = pd.read_csv(PROC / "provider_scores.csv").set_index("provider_id")
MAX_DOLLARS = max(c["potential_dollars"] for c in CASES.values()) or 1
MAX_MEMBERS = max(c["member_impact"] for c in CASES.values()) or 1
CASES_PER_INVESTIGATOR = 5


def status_of(case_id):
    meta, _ = wiki.read(case_id)
    return meta["verdict"] if meta else "open"


def enrich(case, horizon=90):
    ctx = retrieve.query(case)
    conf = confidence.score(case, ctx["precedents"])
    s, p = case["signals"], case["prediction"][f"p{horizon}"]
    risk = 0.35 * s["rules"] + 0.20 * min(1, s["ml"] * 2) + 0.20 * s["graph"] + 0.05 * s["birank"] + 0.20 * p
    dollars_n = math.log1p(case["potential_dollars"]) / math.log1p(MAX_DOLLARS)
    members_n = math.log1p(case["member_impact"]) / math.log1p(MAX_MEMBERS)
    priority = 0.30 * risk + 0.20 * dollars_n + 0.10 * members_n + 0.15 * case["severity"] + 0.25 * conf["score"]
    return ctx, conf, {
        "risk_score": round(risk, 3), "priority": round(priority, 3), "horizon_days": horizon,
        "p_horizon": p, "expected_dollars": round(conf["score"] * case["potential_dollars"], 2),
        "status": status_of(case["case_id"]),
    }


def queue(horizon=90, investigators=3):
    rows = []
    for c in CASES.values():
        _, conf, extra = enrich(c, horizon)
        rows.append({
            "case_id": c["case_id"], "provider_id": c["provider_id"], "provider_name": c["provider_name"],
            "specialty": c["specialty"], "city": c["city"], "pattern": c["pattern"],
            "network": (c["network"] or {}).get("cluster_id", ""),
            "potential_dollars": c["potential_dollars"], "member_impact": c["member_impact"],
            "severity": c["severity"], "evidence_strength": c["evidence_strength"],
            "confidence": conf["score"], "tier": conf["tier"], "route": conf["route"], **extra,
        })
    rows.sort(key=lambda r: (r["status"] != "open", -r["priority"]))
    capacity, used = investigators * CASES_PER_INVESTIGATOR, 0
    for i, r in enumerate(rows, start=1):
        r["rank"] = i
        r["in_capacity"] = r["status"] == "open" and r["tier"] != "low" and used < capacity
        used += r["in_capacity"]
    open_rows = [r for r in rows if r["status"] == "open"]
    summary = {
        **METRICS["funnel"],
        "open_cases": len(open_rows), "closed_cases": len(rows) - len(open_rows),
        "fast_track": sum(r["tier"] == "high" for r in open_rows),
        "review": sum(r["tier"] == "medium" for r in open_rows),
        "not_enough_evidence": sum(r["tier"] == "low" for r in open_rows),
        "capacity": capacity, "cases_per_investigator": CASES_PER_INVESTIGATOR,
        "dollars_in_capacity": round(sum(r["potential_dollars"] for r in rows if r["in_capacity"]), 2),
    }
    return {"summary": summary, "cases": rows}


def detail(case_id, horizon=90):
    case = CASES[case_id]
    ctx, conf, extra = enrich(case, horizon)
    return {**case, **extra, "confidence": conf, "brief": brief.build(case, ctx, conf, horizon)}


def graph(provider_id, limit=12):
    e = EDGES[(EDGES.a == provider_id) | (EDGES.b == provider_id)].copy()
    e["other"] = e.a.where(e.a != provider_id, e.b)
    e["refs"] = e.ref_ab + e.ref_ba
    strong = e[((e.shared >= 10) & (e.lift >= 3)) | (e.refs >= 10) | (e.same_owner == 1)]
    strong = strong.sort_values(["same_owner", "shared", "refs"], ascending=False).head(limit)
    ids = [provider_id] + strong.other.tolist()
    case_ids = {c["provider_id"] for c in CASES.values()}

    def node(p):
        i = PROV_INFO[p]
        return {"id": p, "type": "provider", "label": p, "name": i["name"], "specialty": i["specialty"],
                "flagged": p in case_ids, "cluster": SCORES.cluster_id.get(p) if isinstance(SCORES.cluster_id.get(p), str) else "",
                "center": p == provider_id}

    nodes = [node(p) for p in ids]
    links = []
    sub = EDGES[EDGES.a.isin(ids) & EDGES.b.isin(ids)]
    for r in sub.itertuples():
        if r.shared >= 10 and r.lift >= 3:
            links.append({"source": r.a, "target": r.b, "type": "shared_members", "weight": int(r.shared),
                          "label": f"{r.shared} shared members ({r.lift}x chance)"})
        if r.ref_ab >= 10:
            links.append({"source": r.a, "target": r.b, "type": "referral", "weight": int(r.ref_ab), "label": f"{r.ref_ab} referrals"})
        if r.ref_ba >= 10:
            links.append({"source": r.b, "target": r.a, "type": "referral", "weight": int(r.ref_ba), "label": f"{r.ref_ba} referrals"})
    owner = PROV_INFO[provider_id]["owner_id"]
    nodes.append({"id": owner, "type": "owner", "label": owner, "name": OWNERS.get(owner, "")})
    for p in ids:
        if PROV_INFO[p]["owner_id"] == owner:
            links.append({"source": p, "target": owner, "type": "ownership", "weight": 1, "label": "owned by"})
    facs = sorted({PROV_INFO[p]["facility_id"] for p in ids})[:6]
    for f in facs:
        nodes.append({"id": f, "type": "facility", "label": f, "name": FAC[f]["name"], "city": FAC[f]["city"]})
    for p in ids:
        if PROV_INFO[p]["facility_id"] in facs:
            links.append({"source": p, "target": PROV_INFO[p]["facility_id"], "type": "facility", "weight": 1, "label": "bills at"})
    return {"provider_id": provider_id, "nodes": nodes, "links": links}
