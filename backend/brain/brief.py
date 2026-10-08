"""Investigation brief: Retrieve -> Interpret -> Apply rules -> Propose -> Score -> Cite.

The brief is assembled from structured evidence. If an LLM is configured (see llm.py), it
rewrites the summary paragraph only; its text is then checked by ground():
every claim ID, provider ID, case ID, procedure code and dollar figure must match
the case's own data, otherwise the LLM text is discarded and the template is used.
"""
import re

from backend.pipeline import reference

from . import llm

PATTERN_WORDS = {
    "duplicate_billing": "duplicate billing", "upcoding": "upcoding of visit levels",
    "impossible_timing": "impossible timing between facilities", "unbundling": "unbundling of component codes",
    "collusive_ring": "a coordinated referral network", "excessive_utilization": "utilization far above peers",
}

def copilot_recommendation(case, ctx, conf):
    pat = case.get("pattern", "")
    tier = conf.get("tier", "medium")
    exp = money(case.get("potential_dollars", 0))
    members = case.get("member_impact", 0)
    
    playbooks = {
        "impossible_timing": (
            "Primary Directive: High-priority impossible travel flag across facilities. Verify physical presence vs. telehealth place of service.\n\n"
            "Targeted Investigation Steps:\n"
            "1. Audit Facility Access Logs: Request electronic badge swipe logs and EHR workstation login timestamps at flagged facilities to verify physical presence.\n"
            "2. Review Place of Service (POS): Confirm whether secondary claims were misbilled under POS 11 (Office) rather than POS 02/10 (Telehealth).\n"
            f"3. Sample Records for {members} Affected Members: Issue an Additional Documentation Request (ADR) under CMS Pub 100-08 Ch. 3 to evaluate {exp} in flagged claims.\n\n"
            "Statutory Basis: CMS Program Integrity Manual (Pub 100-08) Ch. 3 / Texas Medicaid Travel & Telehealth Standards."
        ),
        "unbundling": (
            "Primary Directive: Automated NCCI Procedure-to-Procedure (PTP) unbundling detected. Prevent improper separate payment.\n\n"
            "Targeted Investigation Steps:\n"
            "1. Cross-Reference PTP Edits: Validate Column 1 (80053) vs Column 2 (80048) claim lines against CMS NCCI Practitioner edit tables.\n"
            "2. Modifier Audit: Verify whether unbundling modifiers (Modifier 59 or X{EPSU}) were appropriately appended with supporting clinical documentation.\n"
            f"3. Recovery & Prepayment Suspension: Initiate an overpayment demand letter for {exp} and place an automated prepayment edit on component code submissions.\n\n"
            "Statutory Basis: CMS NCCI Policy Manual Ch. 1 / Social Security Act §1862(a)(1)(A)."
        ),
        "upcoding": (
            "Primary Directive: Level-5 office visit distribution exceeds specialty baseline (35%+ volume). Potential E/M grade inflation.\n\n"
            "Targeted Investigation Steps:\n"
            "1. Medical Necessity & MDM Review: Issue ADRs for 30 sample Level-5 encounter charts to evaluate Medical Decision Making (MDM) complexity.\n"
            "2. Time Documentation Audit: Verify provider spent documented minimum thresholds (54+ mins for 99215) or met high-complexity MDM criteria.\n"
            f"3. Specialty Comparison: Benchmark provider visit distribution against regional specialty peers across {members} impacted beneficiaries.\n\n"
            "Statutory Basis: CMS Evaluation and Management (E/M) Guidelines / CMS Pub 100-08 Ch. 3 §3.2."
        ),
        "duplicate_billing": (
            "Primary Directive: Identical claim submission within 72 hours. Potential duplicate reimbursement without adjustment indicator.\n\n"
            "Targeted Investigation Steps:\n"
            "1. Transmission Audit: Verify whether duplicate claims represent uncorrected resubmissions or separate distinct clinical encounters.\n"
            "2. Clearinghouse Reconciliation: Review electronic remittance advice (835) and clearinghouse logs to ensure duplicate claims were not paid twice.\n"
            f"3. Automated Recoupment: Flag {exp} for immediate clawback if provider lacks distinct clinical encounter notes.\n\n"
            "Statutory Basis: CMS Claims Processing Manual (Pub 100-04) Ch. 1 §120 / CMS Pub 100-08 Ch. 3."
        ),
        "collusive_ring": (
            "Primary Directive: Coordinated referral network under common ownership structure. Evaluate cross-referral necessity.\n\n"
            "Targeted Investigation Steps:\n"
            "1. Subpoena Entity Operating Agreements: Audit ownership links between provider, diagnostic labs, and therapy clinics under common holding entity.\n"
            "2. Referral Order Verification: Review clinical orders for the shared patient pool to confirm medical necessity and independent clinical rationale.\n"
            f"3. Stark Law / AKS Review: Assess closed referral loop patterns across {members} shared beneficiaries for anti-kickback vulnerabilities.\n\n"
            "Statutory Basis: 42 U.S.C. §1395nn (Stark Law) / 42 U.S.C. §1320a-7b (Anti-Kickback Statute)."
        ),
        "excessive_utilization": (
            "Primary Directive: Per-member utilization substantially exceeds specialty baseline. Evaluate patient panel severity.\n\n"
            "Targeted Investigation Steps:\n"
            "1. Panel Case-Mix Assessment: Audit whether patient panel represents a documented high-intensity chronic care cohort or regional tertiary referral center.\n"
            "2. Plan of Care (POC) Review: Verify treatment plans and physician orders justify frequency and duration of billed services.\n"
            f"3. Precedent Comparison: Compare against closed second-brain cases to determine whether volume represents legitimate regional specialization.\n\n"
            "Statutory Basis: CMS Program Integrity Manual (Pub 100-08) Ch. 3 §3.6 (Overutilization Monitoring)."
        ),
    }
    return playbooks.get(pat, ACTIONS.get(tier, ACTIONS["medium"]))

ACTIONS = {
    "high": "Fast-track to the SIU. Open a case, request records for the flagged claims, and have an investigator confirm before any action is taken against the provider.",
    "medium": "Assign to an investigator. Review the sample claims and the precedents below, then confirm, correct or clear.",
    "low": "Not enough evidence to open a case. Keep the provider on monitoring and re-score next month.",
}
TOKEN = re.compile(r"\bC\d{6}\b|\bP\d{3}\b|\bF\d{3}\b|\bO\d{3}\b|\bN\d{2}\b|\bINV\d{3}\b|\bCASE-P\d{3}\b|\$[\d,]+(?:\.\d+)?|\b\d{5}\b|\b[AE]\d{4}\b")


_CACHE = {}


def money(x):
    return f"${x:,.0f}"


def allowed_tokens(case, ctx):
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
    found = TOKEN.findall(text)
    bad = sorted({t for t in found if t not in ok})
    return {"tokens_checked": len(found), "verified": len(found) - len([t for t in found if t in bad]),
            "unverified": bad, "passed": not bad}


def template_summary(case, conf):
    p = case["prediction"]
    s = (f"{case['provider_id']} ({case['specialty']}, {case['city']}) is flagged for a pattern consistent with "
         f"{PATTERN_WORDS[case['pattern']]}. {case['signals']['families_agreeing']} of 3 detection methods agree "
         f"(rules, anomaly model, network analysis). Potential exposure is {money(case['potential_dollars'])} across "
         f"{case['member_impact']} members. The model estimates a {p['p90']:.0%} chance of further flagged activity "
         f"in the next 90 days. Confidence is {conf['score']:.0%} ({conf['tier']}). This is a lead for human review, "
         f"not a finding of fraud.")
    return s


def llm_summary(case, ctx, conf):
    facts = {"provider": case["provider_id"], "specialty": case["specialty"], "pattern": PATTERN_WORDS[case["pattern"]],
             "evidence": [e["text"] for e in case["evidence"]], "exposure": money(case["potential_dollars"]),
             "members": case["member_impact"], "p90": f"{case['prediction']['p90']:.0%}",
             "confidence": f"{conf['score']:.0%}", "tier": conf["tier"],
             "precedents": [f"{p['case_id']} {p['verdict']}" for p in ctx["precedents"]]}
    key = str(facts)
    if key not in _CACHE:
        _CACHE[key] = llm.chat(
            "You write case summaries for fraud investigators. Use ONLY the facts given. Copy every ID, code and dollar "
        "figure exactly. Never say fraud occurred; say 'flagged' or 'consistent with'. Four sentences. "
        "End by saying this needs human review.", key, max_tokens=300)
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
    limitations = [
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
        "headline": f"{case['provider_id']} {case['provider_name']}: {PATTERN_WORDS[case['pattern']]}",
        "summary": summary, "generated_by": by,
        "evidence": case["evidence"],
        "timeline": {"monthly": case["timeline"], "events": case["events"]},
        "network_context": (
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
        "recommended_action": copilot_recommendation(case, ctx, conf),
        "grounding": ground(text_for_check, case, ctx) | ({"llm_rejected": True, "llm_unverified": llm_check["unverified"]}
                                                           if llm_check and not llm_check["passed"] else {}),
    }
    return b
