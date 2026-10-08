"""Investigation brief: Retrieve -> Interpret -> Apply rules -> Propose -> Score -> Cite.

The brief is assembled from structured evidence. If an LLM is configured (see llm.py), it
rewrites the summary paragraph and writes the first line of the recommended action; its text is then checked by ground():
every claim ID, provider ID, case ID, procedure code and dollar figure must match
the case's own data, otherwise the LLM text is discarded and the template is used.
"""
import hashlib
import json
import re

from backend.pipeline import reference
from backend.pipeline.common import PROC

from . import llm, refpages

REC_FILE = PROC / "recommendations.json"

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
    fallback = (f"{conf['route']}. Flagged for {PATTERN_WORDS[case['pattern']]}; "
                f"{case['signals']['families_agreeing']} of 3 detection methods agree"
                + (f"; nearest precedent {confirmed[0]['case_id']} was confirmed" if confirmed else "")
                + (f"; note that {cleared[0]['case_id']} was cleared for the same pattern" if cleared else "") + ".")
    key = hashlib.sha1(json.dumps(facts, sort_keys=True).encode()).hexdigest()
    saved = json.loads(REC_FILE.read_text(encoding="utf-8")) if REC_FILE.exists() else {}
    if key not in saved:
        out = llm.chat(
            "You advise a fraud investigator on the single most useful first step for a case. Use ONLY the facts "
            "given, which come from the team's knowledge base. Weigh the precedents: if a similar case was cleared, "
            "say to check that reason first; if one was confirmed, say what it suggests. Two sentences, plain text, "
            "no lists, no colons, no brackets. The only identifiers you may mention are the provider and the case IDs "
            "listed under precedents; do not label or number the facts. Never say fraud occurred. Do not cite laws.",
            json.dumps(facts), max_tokens=160)
        out = re.sub(r"[\[(]?\b(ID|REF|SOURCE)\b[:,]?\s*[A-Z][A-Z_]*\d+[\])]?", "", out or "")  # invented reference tags
        out = re.sub(r"\s+([.,;])", r"\1", " ".join(out.split()))
        if not out or re.search(r"\b[A-Z]{3,}_\w+", out) or len(out) > 420 or not ground(out, case, ctx)["passed"]:
            return fallback, "template"
        saved[key] = out.strip()
        REC_FILE.parent.mkdir(parents=True, exist_ok=True)
        REC_FILE.write_text(json.dumps(saved, indent=1), encoding="utf-8")
    return saved[key], "llm (verified)"


def copilot_recommendation(case, ctx, conf):
    """Proposed next action, assembled from Second Brain pages: the runbook's evidence request, the pattern
    page's innocent explanations, the nearest closed cases and the regulatory pages. Low-confidence cases
    get 'not enough evidence' and no steps."""
    if conf["tier"] == "low":
        return ACTIONS["low"], "template", ["runbook_triage"]
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
    action, action_by, action_pages = copilot_recommendation(case, ctx, conf)
    net = case["network"]
    limitations = [
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
        "recommended_action": action,
        "recommended_action_by": action_by,
        "recommended_action_sources": action_pages,
        "grounding": ground(text_for_check, case, ctx) | ({"llm_rejected": True, "llm_unverified": llm_check["unverified"]}
                                                           if llm_check and not llm_check["passed"] else {}),
    }
    return b
