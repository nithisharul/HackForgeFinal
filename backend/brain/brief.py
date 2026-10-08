"""Investigation brief: Retrieve -> Interpret -> Apply rules -> Propose -> Score -> Cite.

The brief is assembled from structured evidence. If an LLM is configured (see llm.py), it
rewrites the summary paragraph only; its text is then checked by ground():
every claim ID, provider ID, case ID, procedure code and dollar figure must match
the case's own data, otherwise the LLM text is discarded and the template is used.

India briefs check rupee amounts and package codes instead, and add the checklist a State Anti-Fraud
Unit field auditor works through (registers, photographs, scar check, bed count).
"""
import re

from backend import region
from backend.pipeline import reference, reference_in

from . import llm

PATTERN_WORDS = {
    "duplicate_billing": "duplicate billing", "upcoding": "upcoding of visit levels",
    "impossible_timing": "impossible timing between facilities", "unbundling": "unbundling of component codes",
    "collusive_ring": "a coordinated referral network", "excessive_utilization": "utilization far above peers",
}
ACTIONS = {
    "high": "Fast-track to the SIU. Open a case, request records for the flagged claims, and have an investigator confirm before any action is taken against the provider.",
    "medium": "Assign to an investigator. Review the sample claims and the precedents below, then confirm, correct or clear.",
    "low": "Not enough evidence to open a case. Keep the provider on monitoring and re-score next month.",
}
TOKEN = re.compile(r"\bC\d{6}\b|\bP\d{3}\b|\bF\d{3}\b|\bO\d{3}\b|\bN\d{2}\b|\bINV\d{3}\b|\bCASE-P\d{3}\b|\$[\d,]+(?:\.\d+)?|\b\d{5}\b|\b[AE]\d{4}\b")
# India: package codes, agents, villages, card operators, document hashes, mobile tokens and rupee amounts
TOKEN_IN = re.compile(r"\bC\d{6}\b|\bP\d{3}\b|\bF\d{3}\b|\bO\d{3}\b|\bN\d{2}\b|\bINV\d{3}\b|\bCASE-P\d{3}\b|\bM\d{6}\b"
                      r"|\b[A-Z]{2}\d{3}[A-Z]?\b|\bAG-[A-Z]{3}-\d{2}\b|\bVIL-[A-Z]{3}-\d{2}\b|\bOP-[A-Z]{3}-\d{2}\b|\bDOC[0-9a-f]{10}\b"
                      r"|\bMOB\d{6}\b|₹[\d,]+(?:\.\d+)?")
PATTERN_WORDS_IN = {
    "collusive_ring": "a coordinated hospital network fed by shared agents or owners", "bed_overrun": "admissions beyond bed strength or empanelment",
    "opd_to_ipd": "outpatient conditions converted to short admissions", "ghost_beneficiary": "doubtful beneficiary identities",
    "unnecessary_procedure": "surgery without a clear indication, sourced through agents or camps", "duplicate_document": "documents reused across beneficiaries",
    "package_upcoding": "higher-paying packages, wards or rates than supported", "overlapping_admission": "simultaneous admissions at two hospitals",
    "claim_after_death": "claims after a recorded death", "duplicate_package": "the same package claimed twice for one episode",
    "excessive_utilization": "utilisation far above hospitals of the same type",
}
ACTIONS_IN = {
    "high": "Fast-track to the State Anti-Fraud Unit. Hold further payments on the flagged packages, run an unannounced field audit using the checklist below, and have an investigator confirm before any penalty or de-empanelment.",
    "medium": "Assign to a SAFU investigator for a desk audit of the sample claims and the precedents below, then confirm, correct or clear.",
    "low": "Not enough evidence to open a case. Keep the hospital on the watch list and re-score next month.",
}
# What a State Anti-Fraud Unit field auditor checks on site (NHA Field Investigation and Medical Audit Manual, 2020)
AUDIT_BASE = [
    "Match each sampled beneficiary to the Aadhaar authentication log and the admission and discharge photographs.",
    "Inspect the inpatient register, OT register and discharge summaries for the sampled claims.",
    "Ask sampled beneficiaries whether they paid any money for a covered package.",
]
AUDIT_BY_PATTERN = {
    "bed_overrun": ["Count occupied beds on an unannounced visit and compare with the TMS inpatient list for that day."],
    "opd_to_ipd": ["Check admission vitals, investigations and treatment notes for the 0-1 day admissions."],
    "package_upcoding": ["Match ICU days to the ICU register, nursing charts and ventilator logs.",
                         "Confirm the hospital's NABH status and city tier against its empanelment record."],
    "unnecessary_procedure": ["Check the documented indication, pre-operative investigations and histopathology report.",
                              "Examine for a surgical scar where surgery was claimed, with the beneficiary's consent.",
                              "Ask beneficiaries how they reached the hospital: health camp, agent or own choice."],
    "ghost_beneficiary": ["Phone or visit sampled beneficiaries at home and confirm the card-creation record with the operator."],
    "overlapping_admission": ["Compare both hospitals' registers for the overlapping dates."],
    "claim_after_death": ["Obtain the death certificate and check the date in the beneficiary database."],
    "duplicate_document": ["Compare the reused documents with the originals held in the hospital's records."],
    "collusive_ring": ["Interview beneficiaries about who brought them; check payments to agents and camp records.",
                       "Visit the other hospitals in the network on the same day."],
    "duplicate_package": ["Check whether each repeat claim is a documented readmission with a new indication."],
    "excessive_utilization": ["Review case sheets for stays far beyond the package norm."],
}
# Rules that add a pattern's audit steps whatever pattern the case was given
RULE_AUDIT = {"IN1": "overlapping_admission", "IN3": "claim_after_death", "IN4a": "package_upcoding", "IN4b": "unnecessary_procedure",
              "IN5": "package_upcoding", "IN6b": "opd_to_ipd", "IN7": "ghost_beneficiary", "IN8": "duplicate_document",
              "IN9a": "bed_overrun", "IN10": "unnecessary_procedure"}


_CACHE = {}


def money(x):
    return region.current().money(x)


def _token():
    return TOKEN_IN if region.current().code == "in" else TOKEN


def allowed_tokens(case, ctx):
    TOKEN = _token()
    ok = {case["case_id"], case["provider_id"], case["facility_id"], case["owner_id"]} | set(case["codes"])
    ok |= {p["case_id"] for p in ctx["precedents"]} | {p["provider_id"] for p in ctx["precedents"]}
    for e in case["evidence"]:
        ok |= set(TOKEN.findall(e["text"])) | set(e["claim_ids"])
    for s in case["sample_claims"]:
        ok |= {s["claim_id"], s["facility_id"], s["procedure_code"], money(s["paid_amount"])} | set(TOKEN.findall(s["detail"]))
    if case["network"]:
        ok |= set(case["network"]["providers"]) | {case["network"]["cluster_id"], case["network"]["top_owner"],
                                                   money(case["network"]["paid_on_shared_members"])}
    ok |= {money(case["potential_dollars"]), money(case["total_paid"])}
    return ok


def ground(text, case, ctx):
    """Check every ID, code and dollar figure in the text against the case data."""
    ok = allowed_tokens(case, ctx)
    found = _token().findall(text)
    bad = sorted({t for t in found if t not in ok})
    return {"tokens_checked": len(found), "verified": len(found) - len([t for t in found if t in bad]),
            "unverified": bad, "passed": not bad}


def template_summary(case, conf):
    p = case["prediction"]
    if region.current().code == "in":
        return (f"{case['provider_id']} ({case['specialty']}, {case['city']}) is flagged for a pattern consistent with "
                f"{PATTERN_WORDS_IN[case['pattern']]}. {case['signals']['families_agreeing']} of 3 detection methods agree "
                f"(rules, anomaly model, network analysis). Potential exposure is {money(case['potential_dollars'])} across "
                f"{case['member_impact']} beneficiaries. The model estimates a {p['p90']:.0%} chance of further flagged activity "
                f"in the next 90 days. Confidence is {conf['score']:.0%} ({conf['tier']}). This is a lead for State Anti-Fraud "
                f"Unit review, not a finding of fraud.")
    s = (f"{case['provider_id']} ({case['specialty']}, {case['city']}) is flagged for a pattern consistent with "
         f"{PATTERN_WORDS[case['pattern']]}. {case['signals']['families_agreeing']} of 3 detection methods agree "
         f"(rules, anomaly model, network analysis). Potential exposure is {money(case['potential_dollars'])} across "
         f"{case['member_impact']} members. The model estimates a {p['p90']:.0%} chance of further flagged activity "
         f"in the next 90 days. Confidence is {conf['score']:.0%} ({conf['tier']}). This is a lead for human review, "
         f"not a finding of fraud.")
    return s


def llm_summary(case, ctx, conf):
    india = region.current().code == "in"
    facts = {"provider": case["provider_id"], "specialty": case["specialty"],
             "pattern": (PATTERN_WORDS_IN if india else PATTERN_WORDS)[case["pattern"]],
             "evidence": [e["text"] for e in case["evidence"]], "exposure": money(case["potential_dollars"]),
             "members": case["member_impact"], "p90": f"{case['prediction']['p90']:.0%}",
             "confidence": f"{conf['score']:.0%}", "tier": conf["tier"],
             "precedents": [f"{p['case_id']} {p['verdict']}" for p in ctx["precedents"]]}
    key = str(facts)
    if key not in _CACHE:
        _CACHE[key] = llm.chat(
            "You write case summaries for fraud investigators. Use ONLY the facts given. Copy every ID, code and dollar "
        "figure exactly. Never say fraud occurred; say 'flagged' or 'consistent with'. Four sentences. "
        "End by saying this needs human review."
        + (" The provider is a hospital in India's PM-JAY scheme; amounts are rupees written with the ₹ sign." if india else ""),
        key, max_tokens=300)
    return _CACHE[key]


def build(case, ctx, conf, horizon=90):
    summary, by = template_summary(case, conf), "template"
    llm = llm_summary(case, ctx, conf)
    llm_check = None
    if llm:
        llm_check = ground(llm, case, ctx)
        if llm_check["passed"]:
            summary, by = llm, "llm (verified)"
    net = case["network"]
    india = region.current().code == "in"
    limitations = [
        "All data is synthetic. Results show the method works on injected scenarios, not on real PM-JAY claims.",
        "The system flags patterns in claim, beneficiary and hospital records. It reads no documents, photographs or case "
        "sheets and makes no judgment on medical necessity; a field or medical audit decides.",
        "This is a post-payment investigation aid that sits behind pre-authorisation; it does not replace TMS checks.",
        "The 30/60/90-day model predicts future rule flags, learned from 7 monthly snapshots; treat it as a ranking aid.",
        f"Package rules use {reference_in.SOURCE}.",
    ] if india else [
        "All data is synthetic. Results show the method works on injected scenarios, not on real claims.",
        "The system flags patterns in billing data. It cannot see medical records and makes no judgment on medical necessity.",
        "The 30/60/90-day model predicts future rule flags, learned from 7 monthly snapshots; treat it as a ranking aid.",
        f"Bundling rule uses {reference.PTP_SOURCE}. Unit-limit rule uses {reference.MUE_SOURCE}.",
    ]
    if case["signals"]["families_agreeing"] < 2:
        limitations.insert(0, "Only one detection method fired. Single-source evidence is weaker and more likely to be a false positive.")
    cleared = [p for p in ctx["precedents"] if p["verdict"] == "cleared"]
    if cleared:
        limitations.insert(0, f"{len(cleared)} similar past case(s) were cleared, e.g. {cleared[0]['case_id']}: {cleared[0]['reasoning']}")
    if ctx["pattern"]["innocent_explanations"]:
        limitations.append("Innocent explanations to rule out: " + "; ".join(ctx["pattern"]["innocent_explanations"][:3]) + ".")

    text_for_check = " ".join([summary] + [e["text"] for e in case["evidence"]])
    b = {
        "case_id": case["case_id"],
        "headline": f"{case['provider_id']} {case['provider_name']}: {(PATTERN_WORDS_IN if india else PATTERN_WORDS)[case['pattern']]}",
        "summary": summary, "generated_by": by,
        "evidence": case["evidence"],
        "timeline": {"monthly": case["timeline"], "events": case["events"]},
        "network_context": _network_in(case) if india else (
            f"Part of network {net['cluster_id']}: {net['size']} providers ({', '.join(net['providers'])}) sharing "
            f"{net['shared_members']} members, {net['owner_share']:.0%} under owner {net['top_owner']}"
            + (", with referrals forming a closed loop." if net["referral_cycle"] else ".")
        ) if net else f"No coordinated network found. Network risk from shared members with flagged providers: {case['signals']['birank']:.2f} of 1.00.",
        "prediction": {"horizon_days": horizon, "probability": case["prediction"][f"p{horizon}"], **case["prediction"]},
        "confidence": conf,
        "precedents": ctx["precedents"],
        "policy": ctx["policy"],
        "pages_read": ctx["pages_read"],
        "limitations": limitations,
        "recommended_action": (ACTIONS_IN if india else ACTIONS)[conf["tier"]],
        "grounding": ground(text_for_check, case, ctx) | ({"llm_rejected": True, "llm_unverified": llm_check["unverified"]}
                                                           if llm_check and not llm_check["passed"] else {}),
    }
    if india:
        b["field_audit_checklist"] = audit_checklist(case)
    return b



def audit_checklist(case):
    """Base checks, then the steps for the case's pattern and for every pattern its rules point to."""
    pats = [case["pattern"]] + [RULE_AUDIT[k.split()[0]] for k in case["rule_counts"] if k.split()[0] in RULE_AUDIT]
    return AUDIT_BASE + [step for p in dict.fromkeys(pats) for step in AUDIT_BY_PATTERN[p]]

def _network_in(case):
    net = case["network"]
    if not net:
        return ("No coordinated hospital network found. Network risk from beneficiaries shared with flagged hospitals: "
                f"{case['signals']['birank']:.2f} of 1.00.")
    return (f"Part of network {net['cluster_id']}: {net['size']} hospitals ({', '.join(net['providers'])}) sharing "
            f"{net['shared_members']} beneficiaries"
            + (f", {net['owner_share']:.0%} under owner {net['top_owner']}" if net.get("top_owner") else "")
            + (f"; agent {net['top_agent']} brought {net['agent_share']:.0%} of their admissions" if net.get("agent_share", 0) >= 0.2 else "")
            + ("; referrals form a closed loop." if net["referral_cycle"] else "."))
