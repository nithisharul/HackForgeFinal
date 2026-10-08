"""AuditNext: rank the next verification step by expected information per hour of audit time.

Ported from feature/clinical-audit-rag (0de52bd). For each candidate action a:
    U(a) = I(a) / cost_hours(a)
where I(a) is the expected reduction in uncertainty (bits) about "this case is fraud" from doing a: the
mutual information between the fraud outcome and the action's result, H(p) - E[H(posterior)]. The action is
modelled as a test that gives the right answer with probability `discriminative_power` either way.

Inputs and what they are:
  p                 the case's confidence score (evidence strength + precedent). It is a routing score, not a
                    calibrated probability of fraud, so U(a) is a ranking aid, not a forecast.
  catalog           costs and accuracies are illustrative assumptions written for the prototype, not measured.
US only: the catalog follows CMS program-integrity steps. India uses the field audit checklist instead.
Read-only: nothing here changes a score, a verdict or the Second Brain.
"""
import math
from typing import Any, Dict, List

METHOD = "U(a) = expected information gain I(a) in bits / cost in hours; I(a) = H(p) - E[H(posterior)]"
ASSUMPTIONS = ("Action costs and accuracies are illustrative assumptions written for this prototype, not measured. "
               "The prior is the case's confidence score, a routing score rather than a calibrated probability.")


def shannon_entropy(p: float) -> float:
    """Computes Shannon entropy H(p) in bits for binary fraud outcome."""
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -p * math.log2(p) - (1.0 - p) * math.log2(1.0 - p)


def expected_gain(p: float, accuracy: float) -> float:
    """Expected entropy reduction (bits) from a test that is right with probability `accuracy` either way."""
    positive = accuracy * p + (1 - accuracy) * (1 - p)
    after = 0.0
    for prob, post in ((positive, accuracy * p / positive if positive else p),
                       (1 - positive, (1 - accuracy) * p / (1 - positive) if positive < 1 else p)):
        after += prob * shannon_entropy(post)
    return max(0.0, shannon_entropy(p) - after)


# Candidate verification action catalog by fraud pattern
ACTION_CATALOG = {
    "impossible_timing": [
        {
            "id": "telehealth_pos_audit",
            "name": "Audit Telehealth Modifier (POS 02/10)",
            "description": "Inspect claim line modifiers to rule out clerical Place of Service miscoding vs true in-person encounter.",
            "cost_mins": 5,
            "cost_dollars": 10,
            "discriminative_power": 0.65,
            "evidence_tier": "Administrative",
        },
        {
            "id": "physical_badge_logs",
            "name": "Subpoena Physical Turnstile & Badge Logs",
            "description": "Cross-reference electronic parking turnstiles and inpatient terminal IP sessions across facilities.",
            "cost_mins": 25,
            "cost_dollars": 45,
            "discriminative_power": 0.95,
            "evidence_tier": "Forensic / Decisive",
        },
        {
            "id": "adr_chart_request",
            "name": "Issue CMS ADR for Complete Medical Record",
            "description": "Request signed clinical progress charts, vitals timestamps, and nursing encounter notes.",
            "cost_mins": 90,
            "cost_dollars": 150,
            "discriminative_power": 0.60,
            "evidence_tier": "Clinical Document",
        },
        {
            "id": "onsite_field_inspection",
            "name": "Deploy On-Site Clinic Field Investigator",
            "description": "Dispatch special investigation team to physical clinic location to conduct interviews.",
            "cost_mins": 480,
            "cost_dollars": 750,
            "discriminative_power": 0.88,
            "evidence_tier": "Field Audit",
        }
    ],
    "upcoding": [
        {
            "id": "time_based_session_audit",
            "name": "Audit Provider EHR Session Time vs Encounter Length",
            "description": "Extract raw active keystroke and chart viewing duration to verify 40+ min requirement for Level 5 (99215).",
            "cost_mins": 15,
            "cost_dollars": 25,
            "discriminative_power": 0.92,
            "evidence_tier": "Digital Forensics",
        },
        {
            "id": "review_mdm_complexity",
            "name": "Evaluate Medical Decision Making (MDM) Complexity",
            "description": "Cross-reference number of presenting problems and risk of complication against CMS 2021 E/M guidelines.",
            "cost_mins": 20,
            "cost_dollars": 35,
            "discriminative_power": 0.82,
            "evidence_tier": "Clinical Coding",
        },
        {
            "id": "comprehensive_peer_review",
            "name": "Retain Outside Independent Medical Peer Reviewer",
            "description": "Contract external board-certified physician to re-adjudicate clinical necessity of documentation.",
            "cost_mins": 240,
            "cost_dollars": 500,
            "discriminative_power": 0.85,
            "evidence_tier": "Independent Peer Review",
        }
    ],
    "default": [
        {
            "id": "cross_facility_billing_audit",
            "name": "Cross-Reference Concurrent Claims Database",
            "description": "Query statewide claims warehouse for simultaneous overlap across provider NPIs.",
            "cost_mins": 10,
            "cost_dollars": 15,
            "discriminative_power": 0.75,
            "evidence_tier": "Data Verification",
        },
        {
            "id": "targeted_records_request",
            "name": "Issue Targeted Documentation Request (ADR)",
            "description": "Request supporting clinical notes and itemized bills for flagged date of service.",
            "cost_mins": 60,
            "cost_dollars": 90,
            "discriminative_power": 0.70,
            "evidence_tier": "Document Request",
        },
        {
            "id": "patient_interview_sample",
            "name": "Sample Direct Beneficiary Confirmation Calls",
            "description": "Contact patient cohort to verify actual service receipt and approximate visit duration.",
            "cost_mins": 180,
            "cost_dollars": 220,
            "discriminative_power": 0.80,
            "evidence_tier": "Beneficiary Outreach",
        }
    ]
}

def catalog_key(pattern_type: str) -> str:
    norm = (pattern_type or "").lower().replace("-", "_").replace(" ", "_")
    if "travel" in norm or "timing" in norm or "impossible" in norm:
        return "impossible_timing"
    if "upcoding" in norm or "level" in norm:
        return "upcoding"
    return "default"


def plan_investigation(prior: float, pattern_type: str, case_id: str = "") -> Dict[str, Any]:
    """Rank the catalog's actions for this pattern by U(a), best first."""
    p = max(0.01, min(0.99, prior))
    h = shannon_entropy(p)
    key = catalog_key(pattern_type)
    actions: List[Dict[str, Any]] = []
    for act in ACTION_CATALOG[key]:
        gain = expected_gain(p, act["discriminative_power"])
        actions.append({
            "id": act["id"], "name": act["name"], "description": act["description"],
            "cost_mins": act["cost_mins"], "cost_dollars": act["cost_dollars"],
            "discriminative_power_pct": int(round(act["discriminative_power"] * 100)),
            "info_gain_bits": round(gain, 3), "expected_residual_entropy": round(h - gain, 3),
            "utility_score": round(gain / (act["cost_mins"] / 60.0), 3),
            "evidence_tier": act["evidence_tier"], "is_optimal": False,
        })
    actions.sort(key=lambda a: a["utility_score"], reverse=True)
    if actions:
        actions[0]["is_optimal"] = True
    return {"status": "available", "case_id": case_id, "pattern_type": key, "prior_probability": round(p, 3),
            "prior_source": "case confidence score", "prior_entropy_bits": round(h, 3),
            "optimal_action_id": actions[0]["id"] if actions else None, "actions": actions,
            "method": METHOD, "assumptions": ASSUMPTIONS}


def unavailable(case_id: str, reason: str) -> Dict[str, Any]:
    return {"status": "unavailable", "case_id": case_id, "reason": reason, "actions": [], "optimal_action_id": None}
