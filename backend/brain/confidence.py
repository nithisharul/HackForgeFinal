"""Confidence score and routing tier.

confidence = evidence strength (rules, ML, graph agreeing)  +  precedent adjustment
Routing follows the three-tier control model: high -> fast track with audit trail,
medium -> investigator review, low -> "not enough evidence".

PrecedentGuard (on unless GUARD is False) keeps a wrong verdict from spreading through the queue:
- contradiction: confirmed and cleared verdicts on the same pattern for the same provider or network cancel out
- evidence compatibility: the network bonus needs the new case to share the evidence the verdict rested on
- freshness: a precedent's pull halves every HALF_LIFE_DAYS
- reversible influence: revoked precedents are never retrieved (see retrieve.precedents, store.influence)
"""
import datetime as dt

from backend import region

GUARD = True
HALF_LIFE_DAYS = 730

TIERS = {
    "high": {"label": "High confidence", "route": "Fast-track to SIU with audit trail",
             "owner": "SIU lead", "threshold": 0.70},
    "medium": {"label": "Medium confidence", "route": "Assign to an investigator for review",
               "owner": "SIU investigator", "threshold": 0.35},
    "low": {"label": "Low confidence", "route": "Not enough evidence: monitor, do not open a case",
            "owner": "Program integrity analyst", "threshold": 0.0},
}
# India: cases go to the State Anti-Fraud Unit (SAFU), which verifies by desk and field audit.
TIERS_IN = {
    "high": {"label": "High confidence", "route": "Fast-track to the State Anti-Fraud Unit for field audit, with audit trail",
             "owner": "SAFU lead", "threshold": 0.70},
    "medium": {"label": "Medium confidence", "route": "Assign to a SAFU investigator for desk audit",
               "owner": "SAFU investigator", "threshold": 0.35},
    "low": {"label": "Low confidence", "route": "Not enough evidence: keep on the watch list, do not open a case",
            "owner": "SHA analytics team", "threshold": 0.0},
}


def evidence_keys(case):
    """What a verdict on this case rested on: the rules that fired, plus the network if the graph flagged it."""
    return set(case.get("rule_counts") or {}) | ({"graph"} if case["signals"].get("graph", 0) > 0 else set())


def contradictions(precs):
    """Ids of confirmed/cleared precedents that disagree on the same pattern for the same provider or network."""
    out = set()
    for a in precs:
        for b in precs:
            if (a["verdict"], b["verdict"]) == ("confirmed", "cleared") and a["pattern"] == b["pattern"] and (
                    a["provider_id"] == b["provider_id"] or (a.get("network") and a.get("network") == b.get("network"))):
                out |= {a["case_id"], b["case_id"]}
    return out


def freshness(p, today=None):
    try:
        age = ((today or dt.date.today()) - dt.date.fromisoformat(p.get("closed", ""))).days
    except ValueError:
        return 1.0
    return 0.5 ** (max(age, 0) / HALF_LIFE_DAYS)


def score(case, precs, guard=None):
    guard = GUARD if guard is None else guard
    base = case["evidence_strength"]
    reasons, adj = [], 0.0
    net = (case.get("network") or {}).get("cluster_id")
    keys = evidence_keys(case)
    conflict = contradictions(precs) if guard else set()
    for p in precs:
        if p["verdict"] not in ("confirmed", "cleared"):
            continue
        tag = f"{p['case_id']} {p['verdict']}"
        if p["case_id"] in conflict:
            reasons.append(f"+0.00 {tag} set aside: contradicts another verdict on the same provider or network")
            continue
        exact_net = bool(net) and p.get("network") == net
        if guard and exact_net and p.get("evidence") is not None and not set(p["evidence"]) & keys:
            exact_net = False
            reasons.append(f"{tag}: same network but none of its evidence, so no network bonus")
        same_prov = p["provider_id"] == case["provider_id"] and p["pattern"] == case["pattern"]
        if p["verdict"] == "confirmed":
            d = 0.25 if exact_net else 0.10 * p["similarity"]
        else:
            d = -0.30 if same_prov else -0.04 * p["similarity"]
        w = freshness(p) if guard else 1.0
        d *= w
        reasons.append(f"{d:+.2f} {tag} ({', '.join(p['why'])})" + (f", weight {w:.2f} for age" if w < 0.99 else ""))
        adj += d
    adj = max(-0.35, min(0.30, adj))
    value = max(0.02, min(0.98, base + adj))
    tier = "high" if value >= 0.70 else "medium" if value >= 0.35 else "low"
    tiers = TIERS_IN if region.current().code == "in" else TIERS
    return {"score": round(value, 3), "tier": tier, **{k: v for k, v in tiers[tier].items() if k != "threshold"},
            "evidence_strength": round(base, 3), "precedent_adjustment": round(adj, 3),
            "precedent_reasons": reasons, "contradictions": sorted(conflict),
            "formula": "evidence strength (rules + ML + graph agreement) + precedent adjustment; high >= 0.70, medium >= 0.35"}
