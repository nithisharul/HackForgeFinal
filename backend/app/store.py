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


def health():
    """State of the last pipeline run, the LLM and the knowledge integrity check. Read fresh on every call."""
    import datetime as dt
    import urllib.request

    from backend.brain import llm
    from backend.security import log_integrity
    path = PROC / "health.json"
    run = json.loads(path.read_text()) if path.exists() else {"ran_at": None, "detectors": {}, "degraded": []}
    age = None
    if run.get("ran_at"):
        age = round((dt.datetime.now() - dt.datetime.fromisoformat(run["ran_at"])).total_seconds() / 3600, 1)
    cfg, reachable = llm.config(), False
    if cfg["base"]:
        try:
            req = urllib.request.Request(cfg["base"] + "/models", headers={"Authorization": f"Bearer {cfg['key']}"} if cfg["key"] else {})
            reachable = urllib.request.urlopen(req, timeout=1.5).status == 200
        except Exception:  # noqa: BLE001 - unreachable for any reason means template mode
            reachable = False
    integrity = log_integrity.verify(raise_events=False)
    serving = sorted({u for c in CASES.values() for u in c.get("unavailable", [])})
    notes = [f"{name} did not run in the last pipeline run; cases are scored from the remaining detectors." for name in serving]
    if set(run.get("degraded", [])) != set(serving):
        notes.append("A newer pipeline run exists. Restart the API to load it.")
    if age is not None and age > 24 * 7:
        notes.append(f"Detection results are {age / 24:.0f} days old.")
    if not integrity["ok"]:
        notes.append(f"Knowledge integrity alert: {len(integrity['problems'])} problem(s). See the Security panel.")
    return {"status": "degraded" if notes else "ok", "notes": notes,
            "pipeline": {"ran_at": run.get("ran_at"), "age_hours": age, "detectors": run.get("detectors", {}), "unavailable": serving},
            "llm": {"configured": bool(cfg["base"]), "reachable": reachable, "model": cfg["model"] if cfg["base"] else None,
                    "effect": None if reachable else "Summaries, suggestions and answers use templates and keyword lookup."},
            "integrity_ok": integrity["ok"], "cases": len(CASES)}


def status_of(case_id):
    meta, _ = wiki.read(case_id)
    return meta["verdict"] if meta else "open"


def enrich(case, horizon=90):
    ctx = retrieve.query(case)
    conf = confidence.score(case, ctx["precedents"])
    s, p = case["signals"], case["prediction"][f"p{horizon}"]
    # Risk weights are spread over the detectors that ran in the last pipeline run.
    down = set(case.get("unavailable", []))
    parts = [(0.35, s["rules"], "Claim rules"), (0.20, min(1, s["ml"] * 2), "Anomaly model"), (0.20, s["graph"], "Network analysis"),
             (0.05, s["birank"], "Network analysis"), (0.20, p, "30/60/90-day prediction models")]
    live = [(w, v) for w, v, name in parts if name not in down]
    risk = sum(w * v for w, v in live) / sum(w for w, _ in live) if live else 0.0
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
