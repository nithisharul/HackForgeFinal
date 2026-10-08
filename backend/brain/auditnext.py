"""
ClaimShield Nexus - AuditNext Engine
Evidence-Aware Adaptive Investigation Planning under Limited Audit Budgets.
Calculates Expected Information Gain per Unit Verification Cost:
    U(a) = E[Uncertainty Reduction from a] / Cost(a)
"""

import math
from typing import Dict, Any, List

def shannon_entropy(p: float) -> float:
    """Computes Shannon entropy H(p) in bits for binary fraud outcome."""
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -p * math.log2(p) - (1.0 - p) * math.log2(1.0 - p)

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

def plan_investigation(anomaly_prob: float, pattern_type: str = "impossible_timing", case_id: str = "") -> Dict[str, Any]:
    """
    Ranks candidate verifications using the AuditNext utility objective:
    U(a) = Delta H(a) / Cost(a)
    """
    p = max(0.01, min(0.99, anomaly_prob))
    prior_entropy = shannon_entropy(p)

    # Normalize pattern key
    norm_pattern = pattern_type.lower().replace("-", "_").replace(" ", "_")
    if "travel" in norm_pattern or "timing" in norm_pattern or "impossible" in norm_pattern:
        catalog_key = "impossible_timing"
    elif "upcoding" in norm_pattern or "level" in norm_pattern:
        catalog_key = "upcoding"
    else:
        catalog_key = "default"

    raw_actions = ACTION_CATALOG.get(catalog_key, ACTION_CATALOG["default"])
    evaluated_actions: List[Dict[str, Any]] = []

    for act in raw_actions:
        # Expected post-verification entropy after applying evidence
        expected_posterior_entropy = prior_entropy * (1.0 - act["discriminative_power"])
        info_gain = max(0.005, prior_entropy - expected_posterior_entropy)
        
        # Cost normalized in hours for stable utility ratio
        cost_hours = act["cost_mins"] / 60.0
        utility = round(info_gain / cost_hours, 3)

        evaluated_actions.append({
            "id": act["id"],
            "name": act["name"],
            "description": act["description"],
            "cost_mins": act["cost_mins"],
            "cost_dollars": act["cost_dollars"],
            "discriminative_power_pct": int(act["discriminative_power"] * 100),
            "info_gain_bits": round(info_gain, 3),
            "expected_residual_entropy": round(expected_posterior_entropy, 3),
            "utility_score": utility,
            "evidence_tier": act["evidence_tier"],
            "is_optimal": False
        })

    # Rank actions descending by utility score U(a)
    evaluated_actions.sort(key=lambda x: x["utility_score"], reverse=True)
    if evaluated_actions:
        evaluated_actions[0]["is_optimal"] = True

    return {
        "case_id": case_id,
        "pattern_type": catalog_key,
        "prior_probability": round(p, 3),
        "prior_entropy_bits": round(prior_entropy, 3),
        "optimal_action_id": evaluated_actions[0]["id"] if evaluated_actions else None,
        "actions": evaluated_actions
    }
