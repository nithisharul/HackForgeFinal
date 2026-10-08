"""PrecedentGuard experiment: inject wrong and conflicting synthetic verdicts, measure how far they spread.

    python -m backend.brain.guard_eval [--region us|in] [--trials 20] [--wrong 3] [--seed 7]

Each trial stages `wrong` synthetic verdicts in memory (never written to the wiki), then scores the queue
with the guard off and on and compares it with the same arm's clean queue. Ground truth only decides
which verdicts are wrong and grades the outcome; it never reaches the scorer.
Kinds of injected error:
  false_confirm  a legitimate provider is confirmed
  false_clear    a fraudulent provider is cleared
  conflict       one investigator confirms, another clears the same provider (or a network peer)
"""
import argparse
import datetime as dt
import random
import statistics

import pandas as pd
from scipy.stats import kendalltau

from backend import region
from backend.app import store
from backend.brain import confidence, wiki

RANK = {"low": 0, "medium": 1, "high": 2}


def stage(case, verdict, sid):
    meta = {"type": "case", "id": sid, "provider": case["provider_id"], "specialty": case["specialty"],
            "pattern": case["pattern"], "verdict": verdict, "closed": str(dt.date.today()), "exposure": 0,
            "source": "live", "investigator": "synthetic", "network": (case.get("network") or {}).get("cluster_id", ""),
            "evidence": "|".join(sorted(confidence.evidence_keys(case)))}
    wiki._PENDING[wiki._wiki() / "cases" / f"{sid}.md"] = wiki.case_page(meta, "Synthetic verdict (PrecedentGuard experiment).", [])


def snapshot(skip=()):
    """case_id -> tier, priority, base evidence, retrieved precedent ids, flagged contradictions."""
    out = {}
    for c in store.data().CASES.values():
        if c["case_id"] in skip or store.status_of(c["case_id"]) != "open":
            continue
        ctx, conf, extra = store.enrich(c)
        out[c["case_id"]] = {"tier": conf["tier"], "priority": extra["priority"], "base": conf["evidence_strength"],
                             "precs": {p["case_id"] for p in ctx["precedents"]}, "contra": set(conf["contradictions"])}
    return out


def inject(rng, cases, fwa, n):
    """Stage n wrong verdicts. Returns the source case ids (excluded from scoring) and the conflict pairs."""
    legit = [c for c in cases if not fwa[c["provider_id"]]]
    fraud = [c for c in cases if fwa[c["provider_id"]]]
    sources, pairs = set(), []
    for i in range(n):
        kind = rng.choice(["false_confirm", "false_clear", "conflict"])
        c = rng.choice(legit if kind == "false_confirm" else fraud)
        sources.add(c["case_id"])
        if kind == "conflict":
            net = (c.get("network") or {}).get("providers") or []
            peers = [x for x in fraud if x["provider_id"] in net and x is not c]
            other = rng.choice(peers) if peers else c
            sources.add(other["case_id"])
            stage(c, "confirmed", f"SYN-{i}A")
            stage(other, "cleared", f"SYN-{i}B")
            pairs.append({f"SYN-{i}A", f"SYN-{i}B"})
        else:
            stage(c, "confirmed" if kind == "false_confirm" else "cleared", f"SYN-{i}")
    return sources, pairs


def compare(clean, world, fwa, pairs):
    ids = [k for k in world if k in clean]
    m = {"incorrect_fast_track": 0, "legit_escalations": 0, "fraud_demotions": 0, "contradictions_seen": 0,
         "contradictions_flagged": 0}
    for k in ids:
        before, after, bad = RANK[clean[k]["tier"]], RANK[world[k]["tier"]], not fwa[k]
        m["incorrect_fast_track"] += bad and after == 2 and before < 2
        m["legit_escalations"] += bad and after > before
        m["fraud_demotions"] += (not bad) and after < before
        for pair in pairs:
            if pair <= world[k]["precs"]:
                m["contradictions_seen"] += 1
                m["contradictions_flagged"] += pair <= world[k]["contra"]
    m["rank_tau"] = kendalltau([clean[k]["priority"] for k in ids], [world[k]["priority"] for k in ids])[0]
    return m


def run(trials, wrong, seed):
    cases = list(store.data().CASES.values())
    gt = pd.read_csv(region.current().raw / "ground_truth.csv").set_index("provider_id").is_fwa.astype(bool).to_dict()
    fwa = {c["provider_id"]: gt.get(c["provider_id"], False) for c in cases}
    by_case = {c["case_id"]: fwa[c["provider_id"]] for c in cases}
    arms = {}
    for guard in (False, True):
        confidence.GUARD = guard
        clean, rng, rows = snapshot(), random.Random(seed), []
        for _ in range(trials):
            wiki._PENDING.clear()
            sources, pairs = inject(rng, cases, fwa, wrong)
            try:
                rows.append(compare(clean, snapshot(sources), by_case, pairs))
            finally:
                wiki._PENDING.clear()
        arms[guard] = (clean, rows)
    confidence.GUARD = True
    # promotions the plain system earns from (real) precedent on fraud cases; how many the guard keeps
    off_clean, on_clean = arms[False][0], arms[True][0]
    earned = [k for k, v in off_clean.items() if v["tier"] == "high" and v["base"] < 0.70 and by_case[k]]
    preserved = sum(on_clean[k]["tier"] == "high" for k in earned)
    return arms, earned, preserved


def report(arms, earned, preserved, trials, wrong):
    keys = ["incorrect_fast_track", "legit_escalations", "fraud_demotions", "contradictions_flagged", "rank_tau"]
    print(f"\nPrecedentGuard | region {region.current().code} | {trials} trials x {wrong} wrong verdicts (mean per trial)\n")
    print(f"{'metric':28}{'guard off':>12}{'guard on':>12}")
    for k in keys:
        vals = []
        for guard in (False, True):
            rows = arms[guard][1]
            if k == "contradictions_flagged":
                seen = sum(r["contradictions_seen"] for r in rows)
                vals.append(f"{sum(r[k] for r in rows)}/{seen}")
            else:
                vals.append(f"{statistics.mean(r[k] for r in rows):.3f}")
        print(f"{k:28}{vals[0]:>12}{vals[1]:>12}")
    print(f"{'preserved_promotions':28}{f'{len(earned)}/{len(earned)}':>12}{f'{preserved}/{len(earned)}':>12}")
    print("\npreserved_promotions: fraud cases fast-tracked by real precedent alone (no injection) that stay fast-tracked.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default="us", choices=list(region.REGIONS))
    ap.add_argument("--trials", type=int, default=20)
    ap.add_argument("--wrong", type=int, default=3)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    with region.use(a.region):
        report(*run(a.trials, a.wrong, a.seed), a.trials, a.wrong)
