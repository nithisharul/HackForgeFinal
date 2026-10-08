"""Confidence score and routing tier.

confidence = evidence strength (rules, ML, graph agreeing)  +  precedent adjustment
Routing follows the three-tier control model: high -> fast track with audit trail,
medium -> investigator review, low -> "not enough evidence".
"""

TIERS = {
    "high": {"label": "High confidence", "route": "Fast-track to SIU with audit trail",
             "owner": "SIU lead", "threshold": 0.70},
    "medium": {"label": "Medium confidence", "route": "Assign to an investigator for review",
               "owner": "SIU investigator", "threshold": 0.35},
    "low": {"label": "Low confidence", "route": "Not enough evidence: monitor, do not open a case",
            "owner": "Program integrity analyst", "threshold": 0.0},
}


def score(case, precs):
    base = case["evidence_strength"]
    reasons, adj = [], 0.0
    net = (case.get("network") or {}).get("cluster_id")
    for p in precs:
        exact_net = bool(net) and p.get("network") == net
        same_prov = p["provider_id"] == case["provider_id"] and p["pattern"] == case["pattern"]
        if p["verdict"] == "confirmed":
            d = 0.25 if exact_net else 0.10 * p["similarity"]
            reasons.append(f"+{d:.2f} {p['case_id']} confirmed ({', '.join(p['why'])})")
        elif p["verdict"] == "cleared":
            d = -0.30 if same_prov else -0.04 * p["similarity"]
            reasons.append(f"{d:.2f} {p['case_id']} cleared ({', '.join(p['why'])})")
        else:
            d = 0.0
        adj += d
    adj = max(-0.35, min(0.30, adj))
    value = max(0.02, min(0.98, base + adj))
    tier = "high" if value >= 0.70 else "medium" if value >= 0.35 else "low"
    return {"score": round(value, 3), "tier": tier, **{k: v for k, v in TIERS[tier].items() if k != "threshold"},
            "evidence_strength": round(base, 3), "precedent_adjustment": round(adj, 3),
            "precedent_reasons": reasons,
            "formula": "evidence strength (rules + ML + graph agreement) + precedent adjustment; high >= 0.70, medium >= 0.35"}
