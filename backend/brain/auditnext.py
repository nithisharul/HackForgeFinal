"""AuditNext: which check to do next on a case, ranked by expected information gain per hour.

    U(a) = E[uncertainty reduction from a] / cost(a)

Inputs
  prior p        the case's confidence score (evidence strength plus precedent adjustment)
  accuracy(a)    how reliably check `a` separates a real problem from an innocent explanation.
                 Starts from an assumed value and is updated from the Second Brain: closed cases of the
                 same pattern that this check decided raise it; cases where it came back unusable lower it.
  cost(a)        investigator minutes. ASSUMED values, stated on the panel; replace with the unit's own.

E[uncertainty reduction] is the mutual information between the case outcome and the check's result,
treating the check as a binary test that is right with probability accuracy(a). Unlike a fixed
checklist, the ranking moves with the case's prior and with every verdict recorded.
"""
import math

from backend import region

from . import wiki

HOURLY_RATE = {"us": 90, "in": 1200}   # assumed loaded cost of an investigator hour, in the region's currency
PRIOR_WEIGHT = 4   # the assumed accuracy counts as this many closed cases

CALLS = {"id": "member_calls", "name": "Call a Sample of Members", "cost_mins": 180, "accuracy": 0.72, "settles": [], "fails": [],
         "description": "Ask a sample of the affected members whether, where and for how long they were seen."}
RECORDS_FAIL = ["partially fulfilled"]

CATALOG = {
    "impossible_timing": [
        {"id": "pos_check", "name": "Check Place-of-Service and Telehealth Coding", "cost_mins": 10, "accuracy": 0.60,
         "description": "See whether the second-site claims are telehealth visits billed with an office place of service.",
         "settles": ["telehealth", "place of service"], "fails": []},
        {"id": "site_records", "name": "Request Schedules and Sign-In Records for Both Sites", "cost_mins": 120, "accuracy": 0.82,
         "description": "Appointment schedules, sign-in sheets and access logs show where the provider was at the billed times.",
         "settles": ["physically present", "two sites"], "fails": RECORDS_FAIL},
        CALLS,
        {"id": "site_visit", "name": "Visit the Second Site", "cost_mins": 480, "accuracy": 0.90, "settles": [], "fails": [],
         "description": "Confirm on site who delivers services there. Highest cost; use only if records are inconclusive."},
    ],
    "duplicate_billing": [
        {"id": "remit_check", "name": "Check Remittance and Rejection History", "cost_mins": 10, "accuracy": 0.70,
         "description": "See whether the first claim was rejected and never paid, which makes the second a corrected resubmission.",
         "settles": ["resubmission", "clearinghouse", "never paid"], "fails": []},
        {"id": "visit_notes", "name": "Request Visit Notes for Both Dates", "cost_mins": 90, "accuracy": 0.75,
         "description": "Notes show whether two separate services were delivered or one was billed twice.",
         "settles": ["distinct", "billed twice"], "fails": RECORDS_FAIL},
        CALLS,
    ],
    "upcoding": [
        {"id": "panel_review", "name": "Review Patient Panel Complexity", "cost_mins": 30, "accuracy": 0.62,
         "description": "Check diagnoses on the provider's claims for a complex, multi-condition panel that would support high levels.",
         "settles": ["complex", "multi-condition"], "fails": []},
        {"id": "chart_sample", "name": "Request a Sample of Level-5 Visit Notes", "cost_mins": 180, "accuracy": 0.85,
         "description": "Compare documented decision making or time with the level billed on 10-20 visits.",
         "settles": ["sampled charts"], "fails": RECORDS_FAIL},
        {"id": "peer_trend", "name": "Compare Level Mix With Peers Over 12 Months", "cost_mins": 15, "accuracy": 0.55,
         "description": "A sudden rise against same-specialty peers is weak evidence alone but cheap to check.",
         "settles": ["far above specialty peers"], "fails": []},
    ],
    "unbundling": [
        {"id": "modifier_check", "name": "Check Modifiers and Dates on the Claim Lines", "cost_mins": 10, "accuracy": 0.68,
         "description": "Rule out a supported modifier or a date entry error before requesting anything.",
         "settles": ["modifier", "date"], "fails": []},
        {"id": "lab_report", "name": "Request the Lab or Procedure Report", "cost_mins": 60, "accuracy": 0.86,
         "description": "One draw or one session means the component code was included in the comprehensive code.",
         "settles": ["same draw", "bundling edit"], "fails": RECORDS_FAIL},
        {"id": "pair_history", "name": "Review 12 Months of the Same Code Pair", "cost_mins": 20, "accuracy": 0.58,
         "description": "A one-off pair suggests an error; a steady pattern suggests a billing practice.", "settles": [], "fails": []},
    ],
    "collusive_ring": [
        {"id": "ownership", "name": "Review Ownership and Disclosure Filings", "cost_mins": 30, "accuracy": 0.58,
         "description": "Confirm the common owner and whether referral relationships were disclosed.",
         "settles": ["commonly owned"], "fails": []},
        {"id": "referral_records", "name": "Request Referral Orders and Care Plans", "cost_mins": 180, "accuracy": 0.85,
         "description": "For a sample of shared members, check each referral has an order and a clinical reason.",
         "settles": ["clinical rationale", "lacked orders", "care plans"], "fails": RECORDS_FAIL},
        CALLS,
        {"id": "site_visit", "name": "Visit Network Locations", "cost_mins": 480, "accuracy": 0.86, "settles": [], "fails": [],
         "description": "Confirm the providers operate separately. Highest cost; use only if records are inconclusive."},
    ],
    "excessive_utilization": [
        {"id": "program_check", "name": "Check for a Referral Centre or Documented Program", "cost_mins": 20, "accuracy": 0.65,
         "description": "A regional referral centre or high-intensity program explains volume far above peers.",
         "settles": ["referral centre", "high-intensity program"], "fails": []},
        {"id": "plans_of_care", "name": "Request Plans of Care for the Highest-Use Members", "cost_mins": 150, "accuracy": 0.80,
         "description": "Orders and plans of care show whether the frequency billed was ordered and delivered.",
         "settles": ["plans of care", "medical necessity"], "fails": RECORDS_FAIL},
        CALLS,
    ],
}

# India (PM-JAY). Same model; checks a State Anti-Fraud Unit can run. Accuracy and minutes are ASSUMED, as above.
CALLS_IN = {"id": "beneficiary_calls", "name": "Call a Sample of Beneficiaries", "cost_mins": 180, "accuracy": 0.72, "settles": [], "fails": [],
            "description": "Ask a sample of the beneficiaries whether they were admitted, where, and for how long."}
FIELD_IN = {"id": "field_visit", "name": "State Anti-Fraud Unit Field Visit", "cost_mins": 480, "accuracy": 0.92,
            "settles": ["field visit", "inspection", "on site"], "fails": [],
            "description": "Inspect the hospital, its admission and bed registers, and the patients on the ward. Highest cost."}
CASE_SHEETS = {"id": "case_sheets", "name": "Request Case Sheets and Discharge Summaries", "cost_mins": 120, "accuracy": 0.82,
               "settles": ["case sheet", "discharge summary", "medically necessary", "not indicated"], "fails": RECORDS_FAIL,
               "description": "Clinical notes show whether the package billed matches the diagnosis and the treatment given."}
PREAUTH = {"id": "preauth_review", "name": "Review Pre-Authorisation Notes and Package Rules", "cost_mins": 20, "accuracy": 0.62,
           "settles": ["pre-authorisation", "preauth", "package rule"], "fails": [],
           "description": "Check what was requested and approved before admission against the package actually claimed."}
CATALOG_IN = {
    "claim_after_death": [{"id": "death_registry", "name": "Check the Death Registry and Beneficiary Identity", "cost_mins": 20, "accuracy": 0.95,
                           "settles": ["death", "registry", "deceased"], "fails": [],
                           "description": "A recorded death before admission settles the claim; a registry error clears it."}, CASE_SHEETS, CALLS_IN],
    "ghost_beneficiary": [{"id": "identity_check", "name": "Verify Beneficiary Identity and Card History", "cost_mins": 30, "accuracy": 0.85,
                           "settles": ["identity", "card", "aadhaar", "e-kyc"], "fails": [],
                           "description": "Card creation date, e-KYC and linked mobile numbers show whether the beneficiary is real."}, CALLS_IN, FIELD_IN],
    "bed_overrun": [{"id": "bed_census", "name": "Compare Admissions With the Bed Census", "cost_mins": 30, "accuracy": 0.88,
                     "settles": ["census", "bed register", "beds"], "fails": [],
                     "description": "Admissions above the beds the hospital has could not all have been treated as inpatients."}, FIELD_IN],
    "overlapping_admission": [{"id": "discharge_register", "name": "Match Both Hospitals' Admission and Discharge Registers", "cost_mins": 30,
                               "accuracy": 0.88, "settles": ["discharge", "register", "overlap"], "fails": [],
                               "description": "One person cannot be an inpatient at two hospitals at once; the registers show which stay is real."},
                              CALLS_IN, FIELD_IN],
    "duplicate_document": [{"id": "document_match", "name": "Match the Reused Documents Across Claims", "cost_mins": 20, "accuracy": 0.85,
                            "settles": ["document", "same report", "reused"], "fails": [],
                            "description": "The same report or image attached to different beneficiaries cannot be genuine for all of them."},
                           CASE_SHEETS],
    "duplicate_package": [{"id": "repeat_package", "name": "Review the Repeat Package Claims in TMS", "cost_mins": 20, "accuracy": 0.8,
                           "settles": ["repeat", "same package", "resubmission"], "fails": [],
                           "description": "A rejected first claim makes the second a resubmission rather than a duplicate."}, CASE_SHEETS],
    "package_upcoding": [PREAUTH, CASE_SHEETS],
    "opd_to_ipd": [PREAUTH, CASE_SHEETS, CALLS_IN],
    "unnecessary_procedure": [CASE_SHEETS, CALLS_IN, FIELD_IN],
    "excessive_utilization": [CASE_SHEETS, CALLS_IN],
    "collusive_ring": [{"id": "agent_payments", "name": "Check Ownership, Agent Payments and Referral Records", "cost_mins": 45, "accuracy": 0.7,
                        "settles": ["owner", "agent", "referral", "camp"], "fails": [],
                        "description": "Common owners or payments to the same agents tie the hospitals together."}, CALLS_IN, FIELD_IN],
}


def entropy(p):
    return 0.0 if p <= 0 or p >= 1 else -p * math.log2(p) - (1 - p) * math.log2(1 - p)


def info_gain(p, acc):
    """Expected drop in entropy of the outcome after a binary check that is right with probability acc."""
    pos = p * acc + (1 - p) * (1 - acc)
    neg = 1 - pos
    after = pos * entropy(p * acc / pos) + neg * entropy(p * (1 - acc) / neg)
    return max(0.0, entropy(p) - after)


def plan(case, conf):
    pattern = case["pattern"]
    p = max(0.02, min(0.98, conf["score"]))
    closed = [c for c in wiki.case_metas() if c["pattern"] == pattern]
    india = region.current().code == "in"
    rate = HOURLY_RATE[region.current().code]
    label = wiki.patterns()[pattern]["title"].lower() if pattern in wiki.patterns() else pattern.replace("_", " ")
    actions = []
    for a in (CATALOG_IN.get(pattern, [CALLS_IN, FIELD_IN]) if india else CATALOG.get(pattern, [CALLS])):
        hit = lambda c, words: any(w in wiki.reasoning_of(c).lower() for w in words)
        settled = [c for c in closed if c["verdict"] != "inconclusive" and hit(c, a["settles"])]
        failed = [c for c in closed if c["verdict"] == "inconclusive" and hit(c, a["fails"])]
        own = sum(c["provider"] == case["provider_id"] for c in settled)   # this provider's own history counts double
        acc = (PRIOR_WEIGHT * a["accuracy"] + len(settled) + own) / (PRIOR_WEIGHT + len(settled) + own + len(failed))
        acc = max(0.5, min(0.97, acc))
        gain = info_gain(p, acc)
        basis = []
        if settled:
            basis.append(f"decided {len(settled)} of {len(closed)} closed {label} cases" + (", including one on this provider" if own else ""))
        if failed:
            basis.append(f"came back incomplete in {len(failed)}")
        actions.append({
            "id": a["id"], "name": a["name"], "description": a["description"],
            "cost_mins": a["cost_mins"], "cost": round(a["cost_mins"] / 60 * rate),  # in the region's currency
            "accuracy_pct": round(acc * 100), "assumed_accuracy_pct": round(a["accuracy"] * 100),
            "info_gain_bits": round(gain, 3), "utility_score": round(gain / (a["cost_mins"] / 60), 3),
            "basis": "Second Brain: " + "; ".join(basis) + "." if basis else "No closed case bears on this check yet; assumed accuracy used.",
            "is_optimal": False,
        })
    actions.sort(key=lambda x: x["utility_score"], reverse=True)
    if actions:
        actions[0]["is_optimal"] = True
    return {
        "case_id": case["case_id"], "pattern_type": pattern, "tier": conf["tier"],
        "prior_probability": round(p, 3), "prior_entropy_bits": round(entropy(p), 3),
        "closed_cases_used": len(closed), "optimal_action_id": actions[0]["id"] if actions else None, "actions": actions,
        "assumptions": f"Costs are assumed investigator minutes ({region.current().money(rate)}/hour). Accuracy starts from an assumed value and is "
                       "updated from closed cases in the Second Brain. A planning aid; the investigator chooses.",
    }
