"""Investigation brief: Retrieve -> Interpret -> Apply rules -> Propose -> Score -> Cite.

The brief is assembled from structured evidence. If an LLM is configured (see llm.py), it
rewrites the summary paragraph and writes the first line of the recommended action; its text is then checked by ground():
every claim ID, provider ID, case ID, procedure code and dollar figure must match
the case's own data, otherwise the LLM text is discarded and the template is used.

India briefs check rupee amounts and package codes instead, and add the checklist a State Anti-Fraud
Unit field auditor works through (registers, photographs, scar check, bed count).
"""
import hashlib
import threading
import json
import re

from backend import region
from backend.pipeline import reference, reference_in

from . import llm, refpages


PATTERN_WORDS = {
    "duplicate_billing": "duplicate billing", "upcoding": "upcoding of visit levels",
    "impossible_timing": "impossible timing between facilities", "unbundling": "unbundling of component codes",
    "collusive_ring": "a coordinated referral network", "excessive_utilization": "utilization far above peers",
}

def _plain(text):
    """The case page splits this text on 'N.' markers, so a full stop straight after a digit is dropped."""
    return re.sub(r"(\d)\.(?=\s|$)", r"\1", " ".join(str(text).split())).replace(":", ",")


def _sentence(text):
    text = str(text).strip()
    return text if text.endswith((".", "!", "?")) else text + "."


def _directive(case, ctx, conf, facts):
    """One or two sentences saying what to do first. Written by the LLM once per case state and saved;
    the text is discarded if it contains an ID, code or dollar figure that is not in the case."""
    confirmed = [p for p in ctx["precedents"] if p["verdict"] == "confirmed"]
    cleared = [p for p in ctx["precedents"] if p["verdict"] == "cleared"]
    words = PATTERN_WORDS_IN if region.current().code == "in" else PATTERN_WORDS
    fallback = (f"{conf['route']}. Flagged for {words[case['pattern']]}; "
                f"{case['signals']['families_agreeing']} of 3 detection methods agree"
                + (f"; nearest precedent {confirmed[0]['case_id']} was confirmed" if confirmed else "")
                + (f"; note that {cleared[0]['case_id']} was cleared for the same pattern" if cleared else "") + ".")
    def clean(out):
        out = re.sub(r"[\[(]?\b(ID|REF|SOURCE)\b[:,]?\s*[A-Z][A-Z_]*\d+[\])]?", "", out)  # invented reference tags
        out = re.sub(r"\s+([.,;])", r"\1", " ".join(out.split())).strip()
        return "" if re.search(r"\b[A-Z]{3,}_\w+", out) or len(out) > 420 else out
    system = ("You advise a fraud investigator on the single most useful first step for a case. Use ONLY the facts "
              "given, which come from the team's knowledge base. Weigh the precedents: if a similar case was cleared, "
              "say to check that reason first; if one was confirmed, say what it suggests. If the tier is low, say what "
              "would need to appear before a case is opened. Two sentences, plain text, no lists, no colons, no brackets. "
              "The only identifiers you may mention are the provider and the case IDs listed under precedents; do not "
              "label or number the facts. Never say fraud occurred. Do not cite laws.")
    out = saved_llm("directive", facts, lambda: verified_chat(system, facts, case, ctx, 160, clean))
    return (out, "llm (verified)") if out else (fallback, "template")


def copilot_recommendation(case, ctx, conf):
    """Proposed next action, assembled from Second Brain pages: the runbook's evidence request, the pattern
    page's innocent explanations, the nearest closed cases and the regulatory pages. The directive is written by the LLM."""
    pat, precs = case["pattern"], ctx["precedents"]
    cleared = [p for p in precs if p["verdict"] == "cleared"]
    confirmed = [p for p in precs if p["verdict"] == "confirmed"]
    innocent = ctx["pattern"]["innocent_explanations"]
    request = refpages.REQUESTS.get(pat, "Records supporting the flagged claims.")
    claim_ids = [c["claim_id"] for c in case["sample_claims"][:3]]
    net = case["network"]
    facts = {"provider": case["provider_id"], "pattern": PATTERN_WORDS[pat], "tier": conf["tier"],
             "methods_agreeing": case["signals"]["families_agreeing"],
             "evidence": [e["text"] for e in case["evidence"] if e["type"] != "history"][:4],
             "innocent_explanations": innocent[:3], "evidence_to_request": request,
             "precedents": [{"case": p["case_id"], "verdict": p["verdict"], "reason": p["reasoning"]} for p in precs]}
    directive, by = _directive(case, ctx, conf, facts)

    steps = []
    if cleared:
        steps.append(("Check why a similar case was cleared", f"{cleared[0]['case_id']} ({', '.join(cleared[0]['why'])}) was cleared, "
                      f"{_sentence(cleared[0]['reasoning'])} Rule this out before requesting records"))
    elif innocent:
        steps.append(("Rule out innocent explanations", "; ".join(innocent[:2]) + " (from the pattern page)"))
    steps.append(("Request evidence", request + (f" Cite claims {', '.join(claim_ids)} in the request" if claim_ids else "")
                  + " (runbook, evidence to request)"))
    if net:
        others = [p for p in net["providers"] if p != case["provider_id"]]
        steps.append((f"Review with network {net['cluster_id']} open", f"This provider shares {net['shared_members']} members with "
                      f"{', '.join(others)}; a verdict here changes the confidence of the other members"))
    elif confirmed:
        steps.append(("Compare with confirmed precedent", f"{confirmed[0]['case_id']} ({', '.join(confirmed[0]['why'])}) was confirmed, "
                      f"{_sentence(confirmed[0]['reasoning'])} Look for the same finding here"))
    steps.append(("Record a verdict", "Confirmed, cleared or inconclusive, with the reason. It is saved to the Second Brain and "
                  "becomes precedent for similar cases"))

    regs = refpages.PATTERN_REGS.get(pat, [])
    basis = f"{ctx['policy']['id']} {ctx['policy']['title']} (synthetic policy)" + "".join(
        f" / {refpages.REGS[g]['title']}" for g in regs) + ". Background only, see the regulatory pages in the Second Brain."
    text = (f"Primary Directive: {_plain(directive)}\n\nTargeted Investigation Steps:\n"
            + "\n".join(f"{i}. {t}: {_plain(d)}." for i, (t, d) in enumerate(steps, 1))
            + f"\n\nStatutory Basis: {basis}")
    return text, by, [pat, "runbook_evidence", "runbook_verdict"] + regs + [p["case_id"] for p in precs] + ([net["cluster_id"]] if net else [])


def india_recommendation(case, ctx, conf):
    """India: the LLM's first step for the State Anti-Fraud Unit, from the case, the pattern page and the field audit
    checklist (which the case page shows in full)."""
    precs = ctx["precedents"]
    facts = {"provider": case["provider_id"], "pattern": PATTERN_WORDS_IN[case["pattern"]], "tier": conf["tier"],
             "route": conf["route"], "methods_agreeing": case["signals"]["families_agreeing"],
             "evidence": [e["text"] for e in case["evidence"] if e["type"] != "history"][:4],
             "innocent_explanations": ctx["pattern"]["innocent_explanations"][:3],
             "field_audit_first_steps": audit_checklist(case)[:3],
             "precedents": [{"case": p["case_id"], "verdict": p["verdict"], "reason": p["reasoning"]} for p in precs]}
    directive, by = _directive(case, ctx, conf, facts)
    return directive, by, [case["pattern"]] + [p["case_id"] for p in precs]


TOKEN = re.compile(r"\bC\d{6}\b|\bP\d{3}\b|\bF\d{3}\b|\bO\d{3}\b|\bN\d{2}\b|\bINV\d{3}\b|\bCASE-P\d{3}\b|\$\d(?:[\d,]*\d)?(?:\.\d+)?|\b\d{5}\b|\b[AE]\d{4}\b")
# India: package codes, agents, villages, card operators, document hashes, mobile tokens and rupee amounts
TOKEN_IN = re.compile(r"\bC\d{6}\b|\bP\d{3}\b|\bF\d{3}\b|\bO\d{3}\b|\bN\d{2}\b|\bINV\d{3}\b|\bCASE-P\d{3}\b|\bM\d{6}\b"
                      r"|\b[A-Z]{2}\d{3}[A-Z]?\b|\bAG-[A-Z]{3}-\d{2}\b|\bVIL-[A-Z]{3}-\d{2}\b|\bOP-[A-Z]{3}-\d{2}\b|\bDOC[0-9a-f]{10}\b"
                      r"|\bMOB\d{6}\b|₹\d(?:[\d,]*\d)?(?:\.\d+)?")
PATTERN_WORDS_IN = {
    "collusive_ring": "a coordinated hospital network fed by shared agents or owners", "bed_overrun": "admissions beyond bed strength or empanelment",
    "opd_to_ipd": "outpatient conditions converted to short admissions", "ghost_beneficiary": "doubtful beneficiary identities",
    "unnecessary_procedure": "surgery without a clear indication, sourced through agents or camps", "duplicate_document": "documents reused across beneficiaries",
    "package_upcoding": "higher-paying packages, wards or rates than supported", "overlapping_admission": "simultaneous admissions at two hospitals",
    "claim_after_death": "claims after a recorded death", "duplicate_package": "the same package claimed twice for one episode",
    "excessive_utilization": "utilisation far above hospitals of the same type",
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
# Prototype assumptions behind India rules, shown in a brief whenever that rule contributed to the case
ASSUMED_IN = {
    "IN5": "IN5 ICU drift uses thresholds set by this prototype (35% of a month's medical admissions, or a whole-period "
           "binomial test against all hospitals); PM-JAY publishes no threshold for this trigger.",
    "IN6a": "IN6a compares stays with typical stays assumed by this prototype; PM-JAY publishes no length-of-stay norm, "
            "so these flags are indicative only.",
    "IN6b": "IN6b uses a prototype threshold (0-1 day stays at half or more of a month's fever, gastroenteritis and UTI "
            "admissions); PM-JAY names the trigger but publishes no threshold.",
    "IN10": "IN10 counts 3 or more agent-referred surgeries from one village in a week, a prototype threshold rather "
            "than a published PM-JAY rule.",
}
# Rules that add a pattern's audit steps whatever pattern the case was given
RULE_AUDIT = {"IN1": "overlapping_admission", "IN3": "claim_after_death", "IN4a": "package_upcoding", "IN4b": "unnecessary_procedure",
              "IN5": "package_upcoding", "IN6b": "opd_to_ipd", "IN7": "ghost_beneficiary", "IN8": "duplicate_document",
              "IN9a": "bed_overrun", "IN10": "unnecessary_procedure"}


_LOCK = threading.Lock()


def saved_llm(kind, facts, make):
    """LLM text for one case state, written once and kept per region (data/.../processed/llm_text.json), so it
    survives restarts and every later page load is instant. `make` returns verified text or None."""
    path = region.current().proc / "llm_text.json"
    key = f"{kind}:{hashlib.sha1(json.dumps(facts, sort_keys=True, default=str).encode()).hexdigest()}"
    with _LOCK:
        saved = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if key in saved:
        return saved[key]
    text = make()
    if text:
        with _LOCK:
            saved = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            saved[key] = text
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(saved, indent=1, ensure_ascii=False), encoding="utf-8")
    return text


def verified_chat(system, facts, case, ctx, max_tokens, clean=lambda t: t, attempts=3):
    """Ask the LLM, fact-check the answer, and on failure tell it exactly which identifiers or amounts were not in
    the facts and ask again. Returns verified text, or None if the LLM is unreachable or never passes."""
    feedback = ""
    for _ in range(attempts):
        out = llm.chat(system, json.dumps(facts, ensure_ascii=False) + feedback, max_tokens=max_tokens)
        if not out:
            return None
        out = clean(out)
        check = ground(out, case, ctx)
        if out and check["passed"]:
            return out
        feedback = (f"\n\nYour previous draft mentioned {', '.join(check['unverified']) or 'text that could not be checked'}, "
                    "which is not in the facts. Rewrite it using only identifiers and amounts that appear in the facts above.")
    return None


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
    system = ("You write case summaries for fraud investigators. Use ONLY the facts given. Copy every ID, code and "
              "amount exactly as written in the facts. Never say fraud occurred; say 'flagged' or 'consistent with'. "
              "Four sentences. End by saying this needs human review."
              + (" The provider is a hospital in India's PM-JAY scheme; amounts are rupees written with the ₹ sign." if india else ""))
    return saved_llm("summary", facts, lambda: verified_chat(system, facts, case, ctx, 300))


def build(case, ctx, conf, horizon=90):
    # The LLM writes the summary; the template appears only when no LLM is reachable (degraded mode).
    written = llm_summary(case, ctx, conf)
    summary, by = (written, "llm (verified)") if written else (template_summary(case, conf), "template")
    net = case["network"]
    india = region.current().code == "in"
    # The playbook is assembled from the US reference pages (runbooks, CMS rules); India keeps its PM-JAY action
    # text, and its steps come from the field audit checklist below.
    action, action_by, action_pages = india_recommendation(case, ctx, conf) if india else copilot_recommendation(case, ctx, conf)
    limitations = [
        "All data is synthetic. Results show the method works on injected scenarios, not on real PM-JAY claims.",
        "The system flags patterns in claim, beneficiary and hospital records. It reads no documents, photographs or case "
        "sheets and makes no judgment on medical necessity; a field or medical audit decides.",
        "This is a post-payment investigation aid that sits behind pre-authorisation; it does not replace TMS checks.",
        "The 30/60/90-day model predicts future rule flags, learned from 7 monthly snapshots; treat it as a ranking aid.",
        f"Package rules use {reference_in.SOURCE}.",
        *assumption_notes(case),
    ] if india else [
        "All data is synthetic. Results show the method works on injected scenarios, not on real claims.",
        "The system flags patterns in billing data. It cannot see medical records and makes no judgment on medical necessity.",
        "The 30/60/90-day model predicts future rule flags, learned from 7 monthly snapshots; treat it as a ranking aid.",
        f"Bundling rule uses {reference.PTP_SOURCE}. Unit-limit rule uses {reference.MUE_SOURCE}.",
    ]
    if case["signals"]["families_agreeing"] < 2:
        limitations.insert(0, "Only one detection method fired. Single-source evidence is weaker and more likely to be a false positive.")
    if case.get("unavailable"):
        limitations.insert(0, f"{', '.join(case['unavailable'])} did not run in the last pipeline run. This case is scored from the "
                              "remaining detectors, so treat the score with more caution.")
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
        "recommended_action": action,
        "recommended_action_by": action_by,
        "recommended_action_sources": action_pages,
        "grounding": ground(text_for_check, case, ctx),
    }
    if india:
        b["field_audit_checklist"] = audit_checklist(case)
    return b



def assumption_notes(case):
    """India: which assumed norms, prototype thresholds and estimated package rates this case's evidence rests on."""
    fired = {k.split()[0] for k in case["rule_counts"]}
    notes = [text for rule, text in ASSUMED_IN.items() if rule in fired]
    estimated = sorted(c for c in case["codes"] if reference_in.PACKAGES.rate_source.get(c, "verified") != "verified")
    if estimated and "IN4a" in fired:
        notes.append(f"Package rates for {', '.join(estimated)} are estimates, not verified HBP rates; "
                     "amount checks on those packages are indicative.")
    return notes


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
