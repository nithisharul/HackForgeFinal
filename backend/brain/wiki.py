"""The Second Brain: a persistent, interlinked markdown wiki (LLM-wiki pattern).

Layers
  knowledge/sources/   raw material, never edited by the system
  knowledge/wiki/      maintained pages: patterns/, providers/, networks/, cases/,
                       sources/ (one summary per raw document), notes/ (filed answers),
                       index.md, log.md
  knowledge/SCHEMA.md  the conventions every page follows

Operations
  ingest  a verdict or a new source document is read (by the LLM when one is configured),
          a page is written, and every linked page, the index and the log are updated.
          A human previews and approves every change.
  query   ask(): read the index, pick pages, read them, answer with [[citations]].
          Good answers can be filed back as notes, so questions compound too.
  lint    health check: broken links, orphans, patterns that are mostly cleared.
"""
import datetime as dt
import json
import re

from backend import region

from . import confidence, llm

LINK = re.compile(r"\[\[([^\]|#]+)")
TOKEN = re.compile(r"\bC\d{6}\b|\bP\d{3}\b|\bINV\d{3}\b|\$[\d,]+(?:\.\d+)?|₹[\d,]+(?:\.\d+)?")
_PENDING = {}

PATTERNS = {
    "duplicate_billing": {
        "title": "Duplicate billing", "policy": "POL-001", "policy_title": "Duplicate claim submission",
        "definition": "The same service for the same member is billed more than once without a corrected-claim or repeat-procedure indicator.",
        "signals": ["Rule R1: same member, provider, code and amount within 3 days", "Rule R4: units above the per-day limit for the code"],
        "policy_text": "A service is payable once per member, provider and date of service unless the claim carries a corrected-claim indicator or a repeat-procedure modifier supported by the record.",
        "public_basis": "CMS Medicare Claims Processing Manual (duplicate claim edits); CMS NCCI Medically Unlikely Edits",
        "innocent": ["Corrected resubmission after a clearinghouse rejection, where the original was never paid", "A procedure legitimately repeated on the same day and billed with a repeat-procedure modifier"],
    },
    "upcoding": {
        "title": "Upcoding of visit levels", "policy": "POL-002", "policy_title": "Evaluation and management level selection",
        "definition": "Office visits are billed at a higher level (99214, 99215) than the documented complexity or time supports.",
        "signals": ["Rule R5: level-5 share of office visits at or above 35% in a month with 10+ visits", "Anomaly model: level-5 share far above specialty peers", "Trend: level mix drifting upward month over month"],
        "policy_text": "The visit level billed must be supported by documented medical decision making or total time on the date of the encounter. A level distribution far from specialty peers triggers a records review, not a denial.",
        "public_basis": "CMS Evaluation and Management Services Guide; AMA CPT office visit codes 99211-99215",
        "innocent": ["A documented complex, multi-condition patient panel that supports high visit levels"],
    },
    "impossible_timing": {
        "title": "Impossible timing or travel", "policy": "POL-003", "policy_title": "Place and time of service integrity",
        "definition": "One rendering provider bills services at locations too far apart to reach in the time between them, suggesting services not rendered as billed.",
        "signals": ["Rule R2: same provider at two facilities 100+ km apart within 60 minutes", "Anomaly model: more billing facilities than specialty peers"],
        "policy_text": "The rendering provider must be physically present at the place of service billed, unless the service is billed as telehealth with the correct place-of-service code.",
        "public_basis": "CMS place-of-service code set; CMS telehealth billing guidance",
        "innocent": ["Telehealth visits billed with the wrong place of service", "A group billing identifier used by more than one clinician"],
    },
    "unbundling": {
        "title": "Unbundling", "policy": "POL-004", "policy_title": "Bundled services and component codes",
        "definition": "A component service is billed separately alongside the comprehensive service that already includes it.",
        "signals": ["Rule R3: a column-2 code billed with its column-1 code for the same member, provider and date"],
        "policy_text": "When a comprehensive code and one of its component codes are billed for the same member, provider and date, only the comprehensive code is payable unless the edit pair allows a modifier and the record supports it.",
        "public_basis": "CMS National Correct Coding Initiative (NCCI) Procedure-to-Procedure edits and Policy Manual",
        "innocent": ["Tests drawn on separate dates that appear same-day because of a date-of-service entry error", "An edit pair that allows a modifier, billed with a supported modifier"],
    },
    "collusive_ring": {
        "title": "Collusive referral network", "policy": "POL-005", "policy_title": "Referrals among commonly owned providers",
        "definition": "A group of providers, often commonly owned, repeatedly bill the same small set of members and refer them to each other in a loop.",
        "signals": ["Graph: Leiden community with member overlap far above chance", "Graph: circular referrals among the community", "Ownership: majority of the community shares one owner", "BiRank: risk propagated through shared members"],
        "policy_text": "Referrals among providers with common ownership must be clinically justified in the record and disclosed. Patterns of circular referral on a shared member group trigger a network-level review.",
        "public_basis": "Physician self-referral (Stark) law and federal Anti-Kickback Statute, as general background",
        "innocent": ["A legitimate multi-specialty group whose referrals match documented care plans"],
    },
    "excessive_utilization": {
        "title": "Excessive utilization", "policy": "POL-006", "policy_title": "Utilization review",
        "definition": "Volume, visits per member or dollars far above specialty peers without a documented reason.",
        "signals": ["Anomaly model: Isolation Forest score with drivers such as claims per member or total paid", "Rule R4: units above the per-day limit"],
        "policy_text": "Utilization far above specialty peers triggers a review of plans of care and orders. High volume alone is not evidence of fraud, waste or abuse.",
        "public_basis": "CMS Medicare Program Integrity Manual (data analysis and medical review), as general background",
        "innocent": ["A regional referral centre with a very large panel and normal use per member", "A documented high-intensity program such as intensive rehabilitation or home health"],
    },
}

SCHEMA = """# Second Brain schema

Every page is markdown with a small `key: value` header between `---` lines.
Pages link to each other with `[[PageName]]`; the name is the file name without `.md`.

## Page types
- `patterns/<pattern>.md`   one per FWA pattern: definition, detection signals, policy basis,
  known innocent explanations, lessons from closed cases, notes from sources, every closed case.
- `providers/<P###>.md`     one per investigated or networked provider: investigation history.
- `networks/<N##>.md`       one per detected provider network: members, shared ownership, cases.
- `cases/<id>.md`           one per closed case: verdict, reasoning, lesson, evidence summary.
- `sources/<SRC-###>.md`    one summary per raw document added to `knowledge/sources/documents/`.
- `notes/<NOTE-###>.md`     an answer to a question that a human chose to keep.
- `index.md`                catalog of all pages, read first on every query.
- `log.md`                  append-only record of every change, newest last.

## Rules
1. Raw files in `knowledge/sources/` are never edited.
2. Nothing is written without a named human approving the previewed change.
3. Blocks between `<!-- auto:... -->` and `<!-- /auto -->` are regenerated from other pages;
   edit anything outside them by hand.
4. Every case links to exactly one pattern and one provider. Every page is reachable from the index.
5. A cleared case adds its reasoning to the pattern's "Known innocent explanations".
6. Verdict values: `confirmed`, `cleared`, `inconclusive`.
7. A new pattern may be proposed by the LLM when a source document describes a scheme the library
   does not cover. It becomes a pattern page only after a named human approves it, and it is marked
   "knowledge only" until a detection rule exists.
8. The system proposes; it never states that fraud occurred. Wording is "flagged", "consistent with".
9. Text written by the LLM may only use IDs and dollar figures that appear in its input.
"""
SCHEMA_IN = SCHEMA + ("10. India region: a provider is a hospital, a member is a PM-JAY beneficiary and amounts are rupees.\n"
                      "11. Never write a beneficiary's name, Aadhaar number or mobile number into a page; IDs are tokens.\n")

# India (PM-JAY). Policies are synthetic, written for this prototype; the public basis names the real documents.
PATTERNS_IN = {
    "collusive_ring": {
        "title": "Collusive hospital network", "policy": "POL-IN-001", "policy_title": "Agents, camps and referrals among linked hospitals",
        "definition": "A group of hospitals, often under one owner and fed by one agent, repeatedly admits the same small pool of beneficiaries and refers them to each other.",
        "signals": ["Graph: Leiden community of hospitals with beneficiary overlap far above chance", "Graph: one agent brings most of the network's admissions", "Ownership: most hospitals share one private owner", "Graph: referrals form a closed loop", "BiRank: risk propagated through shared beneficiaries"],
        "policy_text": "Hospitals may not pay agents or camp organisers for referrals. Repeated admission of the same beneficiaries across commonly owned hospitals, or a network fed by one agent, triggers a network-level field investigation by the State Anti-Fraud Unit.",
        "public_basis": "NHA Anti-Fraud Framework Practitioners' Guidebook (2020); NHA Field Investigation and Medical Audit Manual (2020); the Khyati Hospital case (Ahmedabad, 2024) as background",
        "innocent": ["A referral chain where district hospitals send patients to one teaching hospital, with documented referral letters", "Beneficiaries from one area who use the nearest group of empanelled hospitals"],
    },
    "bed_overrun": {
        "title": "Capacity and empanelment violations", "policy": "POL-IN-002", "policy_title": "Bed strength and scope of empanelment",
        "definition": "A hospital admits more patients than its sanctioned beds can hold, or bills packages outside the specialties and dates it is empanelled for.",
        "signals": ["Rule IN9a: admissions on one day above bed strength", "Rule IN9b: package specialty not empanelled, or a claim before empanelment", "Anomaly model: busiest day's admissions per bed far above hospital-type peers"],
        "policy_text": "Admissions are payable only within the hospital's registered bed strength and empanelled specialties. Admissions above bed strength trigger an unannounced field visit with a bed count and an inpatient register check.",
        "public_basis": "NHA Field Investigation and Medical Audit Manual (2020): fewer patients on site than shown in TMS; PM-JAY hospital empanelment guidelines",
        "innocent": ["A government medical college running above sanctioned beds, recorded in its inpatient register", "Day-care volume such as cataract or dialysis sessions counted against inpatient beds"],
    },
    "opd_to_ipd": {
        "title": "OPD-to-IPD conversion", "policy": "POL-IN-003", "policy_title": "Admission criteria for conditions treatable as outpatients",
        "definition": "Conditions usually treated as outpatients (fever, gastroenteritis, urinary infection) are admitted for a day or less so that an inpatient package can be claimed.",
        "signals": ["Rule IN6b: 0-1 day stays are half or more of a hospital's fever, gastroenteritis and UTI admissions in a month (a prototype threshold; PM-JAY publishes none)", "Anomaly model: share of 0-1 day medical stays far above hospital-type peers", "Several members of one family admitted on the same day"],
        "policy_text": "Admission is payable only when the condition required inpatient care, documented with admission vitals, investigations and treatment notes. Short admissions for outpatient-treatable conditions trigger a medical audit.",
        "public_basis": "NHA anti-fraud triggers (OPD-to-IPD conversion is an official trigger; no threshold is published)",
        "innocent": ["Severe dehydration or high fever needing an overnight stay, recorded in the vitals chart", "An outbreak such as dengue driving genuine short admissions in one area"],
    },
    "ghost_beneficiary": {
        "title": "Ghost or impersonated beneficiaries", "policy": "POL-IN-004", "policy_title": "Beneficiary identity verification",
        "definition": "Claims for beneficiaries whose identity is doubtful: cards created days before a claim, or mobile numbers shared far beyond one household.",
        "signals": ["Rule IN7: beneficiary card created 7 days or less before admission", "Rule IN7: mobile number registered to more beneficiaries than a household", "Anomaly model: share of new cards far above hospital-type peers"],
        "policy_text": "Every admission requires Aadhaar-based beneficiary authentication and a patient photograph at admission and discharge. Cards created shortly before a claim and shared contact details trigger beneficiary verification by phone or home visit.",
        "public_basis": "CAG Report 11 of 2023 (lakhs of beneficiaries on one placeholder mobile number); NHA Anti-Fraud Framework Practitioners' Guidebook (2020)",
        "innocent": ["A newly eligible family enrolled at the hospital help desk on the day of an emergency", "A placeholder mobile number typed at enrolment, which is a data-quality issue rather than a flag on its own"],
    },
    "unnecessary_procedure": {
        "title": "Unnecessary procedures", "policy": "POL-IN-005", "policy_title": "Medical necessity for elective surgery",
        "definition": "Surgery without a documented indication, often on patients brought in groups from camps by agents, such as hysterectomy in young women or angioplasty without cardiac history.",
        "signals": ["Rule IN10: 3 or more agent-referred surgeries for one package from one village in one week", "Rule IN4b: hysterectomy for a woman under 35 (mandatory audit trigger)", "Anomaly model: share of agent-referred admissions far above hospital-type peers"],
        "policy_text": "Elective surgery requires a documented indication and prior investigations; hysterectomy under 35 also needs a second opinion before pre-authorisation. Camp-sourced surgical clusters trigger a medical audit of case sheets and histopathology.",
        "public_basis": "Health Ministry audit guidance on hysterectomy in women under 35; NHA Field Investigation and Medical Audit Manual (2020); the Khyati Hospital case (2024) as background",
        "innocent": ["A visiting surgeon's fixed operating days concentrating surgery on certain dates", "Hysterectomy under 35 for a documented indication, confirmed by histopathology"],
    },
    "duplicate_document": {
        "title": "Reused documents", "policy": "POL-IN-006", "policy_title": "Uniqueness of clinical documents and images",
        "definition": "The same document, image or report is attached to claims for different beneficiaries.",
        "signals": ["Rule IN8: the same document hash on claims for different beneficiaries"],
        "policy_text": "Every claim document must belong to the patient named on it. A document or image reused across beneficiaries puts every claim it supports on hold pending a desk audit.",
        "public_basis": "NHA anti-fraud triggers (the same image or document reused across claims)",
        "innocent": ["A blank consent form or template scanned identically for several patients", "A family document such as a ration card legitimately attached for two members"],
    },
    "package_upcoding": {
        "title": "Package upcoding and mismatch", "policy": "POL-IN-007", "policy_title": "Package, ward and rate selection",
        "definition": "A higher-paying package, ward or rate is claimed than the diagnosis, patient or hospital supports: ICU rates for general-ward care, a package that does not fit the diagnosis or sex, or incentives the hospital is not entitled to.",
        "signals": ["Rule IN5: ICU or ventilator share of medical admissions far above all hospitals in a month or over the whole period (prototype thresholds)", "Rule IN4a: diagnosis or sex the package does not fit, or an amount above the hospital's entitled rate", "Anomaly model: ICU share far above hospital-type peers"],
        "policy_text": "The package, ward and rate claimed must match the documented diagnosis, the patient and the hospital's own tier and accreditation. ICU days must be supported by the ICU register and vitals charts. A first upcoding offence can be penalised up to 10 times the excess claimed.",
        "public_basis": "NHA Anti-Fraud Framework Practitioners' Guidebook (2020) on upcoding penalties; HBP 2.0 and HBP 2.2 package, ward and incentive rates (5 of the 45 package rates used here are estimates, not verified HBP rates)",
        "innocent": ["A hospital with a genuine critical-care unit taking referred sick patients, supported by ICU registers", "A new NABH accreditation not yet updated in the hospital registry"],
    },
    "overlapping_admission": {
        "title": "Overlapping admissions", "policy": "POL-IN-008", "policy_title": "One beneficiary, one admission at a time",
        "definition": "A beneficiary is claimed as an inpatient at two hospitals at the same time.",
        "signals": ["Rule IN1: admitted while an inpatient at another hospital, with an overlap of 24 hours or more"],
        "policy_text": "A beneficiary can be an inpatient at only one hospital at a time, except for a documented transfer with discharge from the first hospital. Overlapping stays are checked against both hospitals' registers.",
        "public_basis": "CAG Report 11 of 2023 (claims with overlapping admissions)",
        "innocent": ["A transfer where the first hospital recorded the discharge late", "A data-entry error in the discharge date, corrected at audit"],
    },
    "claim_after_death": {
        "title": "Claims after recorded death", "policy": "POL-IN-009", "policy_title": "Claims for deceased beneficiaries",
        "definition": "A claim is made for a beneficiary after the date of death recorded against their card.",
        "signals": ["Rule IN3: admission after the beneficiary's recorded date of death"],
        "policy_text": "No claim is payable for an admission after the beneficiary's recorded death. Every such claim is audited, as are all in-hospital deaths.",
        "public_basis": "CAG Report 11 of 2023 (claims for patients already recorded as dead); NHA audit norm of auditing every death case",
        "innocent": ["A wrong date of death in the beneficiary database, corrected with the death certificate"],
    },
    "duplicate_package": {
        "title": "Duplicate package claims", "policy": "POL-IN-010", "policy_title": "One package per episode of care",
        "definition": "The same inpatient package is claimed again for the same beneficiary at the same hospital within days.",
        "signals": ["Rule IN2: same inpatient package, beneficiary and hospital within 7 days"],
        "policy_text": "A package is payable once per episode of care. A repeat claim within 7 days needs a documented readmission with a new indication.",
        "public_basis": "NHA anti-fraud triggers on repeat claims",
        "innocent": ["A genuine readmission for a complication, documented with new investigations", "A resubmission after a rejection where the first claim was never paid"],
    },
    "excessive_utilization": {
        "title": "Excessive utilisation", "policy": "POL-IN-011", "policy_title": "Utilisation and length-of-stay review",
        "definition": "Admissions, stay lengths or amounts far above hospitals of the same type without a documented reason.",
        "signals": ["Rule IN6a: stay more than twice the typical stay assumed for the package plus 3 days (an assumption, not a published PM-JAY norm)", "Anomaly model: Isolation Forest score with drivers such as admissions per beneficiary or total paid"],
        "policy_text": "Utilisation far above hospitals of the same type, or stays far beyond the package norm, triggers a review of case sheets. High volume alone is not evidence of fraud.",
        "public_basis": "NHA Field Investigation and Medical Audit Manual (2020): stay not matching the package; typical stays here are assumed, not published",
        "innocent": ["A high-volume dialysis or eye centre with normal use per beneficiary", "A complicated case with a documented reason for a long stay"],
    },
}


def patterns():
    """The active region's pattern catalogue."""
    return PATTERNS_IN if region.current().code == "in" else PATTERNS


def _wiki():
    return region.current().know / "wiki"


def _src():
    return region.current().know / "sources"


def _registry():
    return region.current().know / "learned_patterns.json"


def load_learned():
    """Patterns a human approved from a source document, kept per region beside the built-in ones."""
    for code in region.REGIONS:
        with region.use(code):
            if _registry().exists():
                patterns().update(json.loads(_registry().read_text(encoding="utf-8")))


load_learned()


# ---------------------------------------------------------------- page io ---
def pages():
    return {p.stem: p for p in _wiki().rglob("*.md")}


def parse(text):
    meta, body = {}, text
    if text.startswith("---"):
        head, body = text[3:].split("\n---", 1)
        for line in head.strip().splitlines():
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta, body.lstrip("\n")


def read(name):
    path = pages().get(name)
    return parse(path.read_text(encoding="utf-8")) if path else (None, None)


def render(meta, body):
    return "---\n" + "\n".join(f"{k}: {v}" for k, v in meta.items()) + "\n---\n" + body


def section(body, heading):
    m = re.search(rf"## {re.escape(heading)}\n(.*?)(?=\n## |\Z)", body or "", re.S)
    return m.group(1).strip() if m else ""


def metas(sub):
    """Header fields (+ body) of every page in a wiki sub-folder, including pages pending approval."""
    d = _wiki() / sub
    texts = {p: p.read_text(encoding="utf-8") for p in sorted(d.glob("*.md"))} if d.exists() else {}
    texts.update({p: t for p, t in _PENDING.items() if p.parent == d})
    out = []
    for t in texts.values():
        meta, body = parse(t)
        out.append(meta | {"_body": body})
    return out


def case_metas():
    return sorted(metas("cases"), key=lambda c: c.get("closed", ""))


def reasoning_of(case):
    return section(case.get("_body", ""), "Reasoning")


def clusters():
    path = region.current().proc / "clusters.json"
    return json.loads(path.read_text()) if path.exists() else {}


def next_id(prefix, sub):
    d = _wiki() / sub
    return f"{prefix}-{len(list(d.glob('*.md'))) + 1:03d}" if d.exists() else f"{prefix}-001"


def source_path(*parts):
    """Repository path of a raw source, e.g. knowledge/india/sources/policies/POL-IN-001.md."""
    return "/".join((_src() / "/".join(parts)).relative_to(region.ROOT).parts)


def policy_path(policy_id):
    return source_path("policies", f"{policy_id}.md")


def grounded(text, allowed_text):
    """True when every claim/provider/case ID and dollar figure in text also appears in allowed_text."""
    ok = set(TOKEN.findall(allowed_text))
    return all(t in ok for t in TOKEN.findall(text))


# -------------------------------------------------------- page generators ---
def _case_line(c, link_provider=True):
    who = f"[[{c['provider']}]] ({c.get('specialty', '')})" if link_provider else f"[[{c['pattern']}]]"
    revoked = f" | revoked as precedent {c['revoked']}" if c.get("revoked") else ""
    return f"- [[{c['id']}]] | {who} | **{c['verdict']}** | closed {c['closed']}{revoked}"


def _auto(name, lines):
    return f"<!-- auto:{name} -->\n" + "\n".join(lines) + ("\n" if lines else "") + "<!-- /auto -->\n"


def pattern_page(pid, cases, sources):
    p = patterns()[pid]
    mine = [c for c in cases if c["pattern"] == pid]
    n = {v: sum(c["verdict"] == v for c in mine) for v in ("confirmed", "cleared", "inconclusive")}
    # a revoked verdict stays listed under Cases but no longer teaches anything
    learned = [f"- {reasoning_of(c)} (learned from [[{c['id']}]])" for c in mine
               if c["verdict"] == "cleared" and c.get("source") == "live" and reasoning_of(c) and not c.get("revoked")]
    lessons = [f"- {section(c['_body'], 'Lesson')} (from [[{c['id']}]], {c['verdict']})" for c in mine
               if section(c["_body"], "Lesson") and not c.get("revoked")]
    notes = []
    for s in sources:
        for line in section(s["_body"], "What this changes").splitlines():
            m = re.match(rf"- \[\[{pid}\]\]:\s*(.+)", line)
            if m:
                notes.append(f"- {m.group(1)} (from [[{s['id']}]])")
    body = f"# {p['title']}\n\n## Definition\n{p['definition']}\n\n## Detection signals\n"
    body += "\n".join(f"- {s}" for s in p["signals"])
    if p.get("learned"):
        body += ("\n- Status: knowledge only. No rule or model detects this pattern yet."
                 f"\n\n## Policy basis\n- No policy mapped yet. Proposed by the LLM from [[{p['origin']}]], "
                 f"approved by {p['approved_by']} on {p['added']}.\n\n## Known innocent explanations\n")
    else:
        body += (f"\n\n## Policy basis\n- {p['policy']} {p['policy_title']} (`{policy_path(p['policy'])}`)\n"
                 f"- Public basis: {p['public_basis']}\n\n## Known innocent explanations\n")
    body += "\n".join(f"- {s}" for s in p["innocent"]) + "\n" + _auto("learned", learned)
    body += "\n## Lessons from closed cases\n" + _auto("lessons", lessons)
    body += "\n## Notes from sources\n" + _auto("notes", notes)
    body += ("\n## Precedent summary\n" + _auto("summary", [
        f"{len(mine)} closed cases: {n['confirmed']} confirmed, {n['cleared']} cleared, {n['inconclusive']} inconclusive."
        + (f" {sum(bool(c.get('revoked')) for c in mine)} revoked as precedent." if any(c.get("revoked") for c in mine) else "")]))
    body += "\n## Cases\n" + _auto("cases", [_case_line(c) for c in mine])
    meta = {"type": "pattern", "id": pid, "title": p["title"], "policy": p.get("policy") or "none"}
    if p.get("learned"):
        meta["origin"] = f"learned from {p['origin']}"
    return render(meta, body)


def provider_page(pid, cases, info, net):
    mine = [c for c in cases if c["provider"] == pid]
    if region.current().code == "in":
        line = (f"Hospital type: {info.get('specialty', '')} | {info.get('city', '')}, {info.get('state', '')} | "
                f"{info.get('beds', '')} beds | Tier {info.get('city_tier', '')} | NABH: {info.get('nabh_status', '')} | "
                f"{info.get('sector', '')} | Owner: {info.get('owner_id', '')}")
    else:
        line = f"Specialty: {info.get('specialty', '')} | City: {info.get('city', '')} | Owner: {info.get('owner_id', '')}"
    body = (f"# {pid} {info.get('name', '')}\n\n{line}" + (f" | Network: [[{net}]]" if net else "") + "\n\n## Investigation history\n")
    body += _auto("cases", [_case_line(c, link_provider=False) for c in mine])
    return render({"type": "provider", "id": pid, "name": info.get("name", ""), "specialty": info.get("specialty", "")}, body)


def network_page(cl, cases, info):
    cid = cl["cluster_id"]
    mine = [c for c in cases if c["provider"] in cl["providers"]]
    if region.current().code == "in":
        body = (f"# Network {cid}\n\nPattern: [[collusive_ring]]\n\n## What links these hospitals\n"
                f"- {cl['size']} hospitals found as one community ({cl['method']})\n"
                f"- {cl['shared_members']} beneficiaries are admitted by 3 or more of them\n"
                + (f"- {round(cl['owner_share'] * 100)}% share private owner {cl['top_owner']}\n" if cl.get('top_owner') else "")
                + (f"- Agent {cl['top_agent']} brought {round(cl['agent_share'] * 100)}% of their admissions\n" if cl.get('top_agent') else "")
                + (f"- {round(cl['village_share'] * 100)}% of shared beneficiaries live in {', '.join(cl['top_villages'])}\n" if cl.get('top_villages') else "")
                + (f"- {round(cl['operator_share'] * 100)}% of their cards were created by operator {cl['top_card_operator']}\n" if cl.get('top_card_operator') else "")
                + f"- Referrals {'form a closed loop' if cl['referral_cycle'] else 'do not form a closed loop'}\n"
                f"- {region.current().money(cl['paid_on_shared_members'])} paid on the shared beneficiaries\n\n## Members\n")
    else:
        body = (f"# Network {cid}\n\nPattern: [[collusive_ring]]\n\n## What links these providers\n"
                f"- {cl['size']} providers found as one community ({cl['method']})\n"
                f"- {cl['shared_members']} members are billed by 3 or more of them\n"
                f"- {round(cl['owner_share'] * 100)}% share owner {cl['top_owner']}\n"
                f"- Referrals {'form a closed loop' if cl['referral_cycle'] else 'do not form a closed loop'}\n"
                f"- ${cl['paid_on_shared_members']:,.0f} paid on the shared members\n\n## Members\n")
    body += _auto("members", [f"- [[{p}]] | {info.get(p, {}).get('specialty', '')}" for p in cl["providers"]])
    body += "\n## Cases involving members\n" + _auto("cases", [_case_line(c) for c in mine])
    return render({"type": "network", "id": cid, "size": cl["size"], "owner": cl["top_owner"]}, body)


def case_page(meta, reasoning, evidence, lesson=""):
    body = (f"# {meta['id']} | {patterns()[meta['pattern']]['title']} | {meta['verdict']}\n\n"
            f"Provider: [[{meta['provider']}]] | Pattern: [[{meta['pattern']}]]"
            + (f" | Network: [[{meta['network']}]]" if meta.get("network") else "") + f"\n\n## Reasoning\n{reasoning}\n")
    if lesson:
        body += f"\n## Lesson\n{lesson}\n"
    if evidence:
        body += "\n## Evidence at decision time\n" + "\n".join(f"- {e}" for e in evidence) + "\n"
    return render(meta, body)


def index_page(cases, sources, notes, nets):
    lines = ["# Second Brain index", "", "Read this page first. Every page in the wiki is listed here.", "", "## Patterns"]
    for pid, p in patterns().items():
        mine = [c for c in cases if c["pattern"] == pid]
        lines.append(f"- [[{pid}]] | {p['title']} | {len(mine)} cases, {sum(c['verdict'] == 'confirmed' for c in mine)} confirmed")
    lines += ["", "## Networks"] + [f"- [[{c['cluster_id']}]] | {c['size']} providers, owner {c['top_owner']}" for c in nets.values()]
    lines += ["", "## Sources"] + [f"- [[{s['id']}]] | {s.get('title', '')} | added {s.get('added', '')}" for s in sources]
    lines += ["", "## Notes"] + [f"- [[{n['id']}]] | {n.get('title', '')}" for n in notes]
    prov = sorted({c["provider"] for c in cases} | {p for c in nets.values() for p in c["providers"]})
    lines += ["", "## Hospitals" if region.current().code == "in" else "## Providers"] + [f"- [[{p}]]" for p in prov]
    lines += ["", "## Cases"] + [f"- [[{c['id']}]] | {c['pattern']} | {c['verdict']} | {c['closed']}"
                                 + (f" | revoked {c['revoked']}" if c.get("revoked") else "") for c in cases]
    return "\n".join(lines) + "\n"


def build_all(info):
    """Every derived page, regenerated from the case, source and note pages."""
    cases, sources, notes, nets = case_metas(), metas("sources"), metas("notes"), clusters()
    net_of = {p: c["cluster_id"] for c in nets.values() for p in c["providers"]}
    wiki = _wiki()
    out = {wiki / "index.md": index_page(cases, sources, notes, nets)}
    for pid in patterns():
        out[wiki / "patterns" / f"{pid}.md"] = pattern_page(pid, cases, sources)
    for p in sorted({c["provider"] for c in cases} | set(net_of)):
        out[wiki / "providers" / f"{p}.md"] = provider_page(p, cases, info.get(p, {}), net_of.get(p))
    for c in nets.values():
        out[wiki / "networks" / f"{c['cluster_id']}.md"] = network_page(c, cases, info)
    return out


def log(kind, title, detail=""):
    path = _wiki() / "log.md"
    if not path.exists():
        path.write_text("# Change log\n\nAppend-only. Newest entries last.\n", encoding="utf-8")
    with path.open("a", encoding="utf-8") as f:
        f.write(f"\n## [{dt.date.today()}] {kind} | {title}\n{detail}\n")


def _apply(pending, info, dry_run, log_entry):
    """Stage new pages, regenerate everything that depends on them, and return the diff."""
    _PENDING.clear()
    _PENDING.update(pending)
    try:
        new = build_all(info)
    finally:
        _PENDING.clear()
    new.update(pending)
    changes = []
    for path, content in new.items():
        old = path.read_text(encoding="utf-8") if path.exists() else ""
        if old != content:
            seen = set(old.splitlines())
            added = [l for l in content.splitlines() if l.strip() and l not in seen]
            changes.append({"page": path.stem, "path": str(path.relative_to(region.current().know)).replace("\\", "/"),
                            "action": "update" if old else "create", "added": added[:12]})
    if not dry_run:
        for path, content in new.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        kind, title, detail = log_entry
        log(kind, title, f"{detail} Pages touched: {', '.join(c['page'] for c in changes)}.")
    return changes


# ---------------------------------------------------------------- seeding ---
def seed(inv, prov):
    """Create the wiki from the raw sources. Existing live pages are kept."""
    WIKI, SRC, india = _wiki(), _src(), region.current().code == "in"
    for d in ("patterns", "providers", "cases", "networks", "sources", "notes"):
        (WIKI / d).mkdir(parents=True, exist_ok=True)
    (SRC / "policies").mkdir(parents=True, exist_ok=True)
    (SRC / "documents").mkdir(parents=True, exist_ok=True)
    (region.current().know / "SCHEMA.md").write_text(SCHEMA_IN if india else SCHEMA, encoding="utf-8")
    for p in patterns().values():
        if not p.get("policy"):
            continue
        (SRC / "policies" / f"{p['policy']}.md").write_text(
            f"# {p['policy']} {p['policy_title']}\n\n> Synthetic policy written for this prototype. Not a real "
            f"{'scheme or insurer' if india else 'payer'} policy.\n\n"
            f"{p['policy_text']}\n\nPublic basis to verify: {p['public_basis']}\n", encoding="utf-8")
    inv.to_csv(SRC / "investigations.csv", index=False)
    fresh = not (WIKI / "index.md").exists()
    for r in inv.itertuples():
        path = WIKI / "cases" / f"{r.case_id}.md"
        if not path.exists():
            meta = {"type": "case", "id": r.case_id, "provider": r.provider_id, "specialty": r.specialty,
                    "pattern": r.pattern, "verdict": r.verdict, "closed": r.closed_date,
                    "exposure": r.exposure_amount, "source": "seed", "investigator": "historical record"}
            path.write_text(case_page(meta, r.reasoning, [f"Source record: {source_path('investigations.csv')}, row {r.case_id}"]), encoding="utf-8")
    info = prov.set_index("provider_id").to_dict("index")
    for path, text in build_all(info).items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    if fresh:
        log("seed", "wiki created", f"{len(inv)} historical cases ingested from {source_path('investigations.csv')}.")


# ------------------------------------------------------- ingest: verdicts ---
def write_lesson(case, verdict, reasoning, pattern):
    """Ask the LLM for the reusable takeaway of a closed case. Returns '' without an LLM or if ungrounded."""
    facts = "\n".join(f"- {e['text']}" for e in case["evidence"])
    text = llm.chat(
        "You maintain a fraud investigation wiki. Write the reusable lesson from a closed case in one or two plain "
        "sentences for future investigators. Use only the facts given. Never state that fraud occurred. "
        "Do not invent IDs or dollar figures. Reply with the lesson only.",
        f"Pattern: {patterns()[pattern]['title']}\nProvider specialty: {case['specialty']}\nVerdict: {verdict}\n"
        f"Investigator reasoning: {reasoning}\nEvidence at decision time:\n{facts}", max_tokens=160)
    if not text:
        return ""
    text = " ".join(text.split())
    return text if grounded(text, facts + " " + reasoning + " " + case["provider_id"]) else ""


def ingest(case, verdict, reasoning, investigator, info, pattern=None, lesson=None, dry_run=False):
    """Human-approved writeback of a verdict. With dry_run=True nothing is written."""
    pattern = pattern or case["pattern"]
    if lesson is None:
        lesson = write_lesson(case, verdict, reasoning, pattern)
    meta = {"type": "case", "id": case["case_id"], "provider": case["provider_id"], "specialty": case["specialty"],
            "pattern": pattern, "verdict": verdict, "closed": str(dt.date.today()),
            "exposure": case["potential_dollars"], "source": "live", "investigator": investigator,
            "network": (case.get("network") or {}).get("cluster_id", ""),
            "evidence": "|".join(sorted(confidence.evidence_keys(case)))}
    text = case_page(meta, reasoning, [e["text"] for e in case["evidence"]], lesson)
    changes = _apply({_wiki() / "cases" / f"{meta['id']}.md": text}, info, dry_run,
                     ("ingest", f"{meta['id']} {verdict}",
                      f"Approved by {investigator}. Pattern [[{pattern}]], provider [[{meta['provider']}]]."))
    return {"changes": changes, "lesson": lesson, "lesson_by": "llm" if lesson else "none"}


def revoke(case_id, reason, investigator, info):
    """Withdraw a verdict as precedent. The page stays for the audit trail; retrieval skips it from now on."""
    meta, body = read(case_id)
    meta |= {"revoked": str(dt.date.today()), "revoked_by": investigator, "revoke_reason": " ".join(reason.split())}
    body = body.rstrip("\n") + (f"\n\n## Revoked as precedent\n{meta['revoked']} by {investigator}: {meta['revoke_reason']}\n"
                                "The verdict stands for this case; it no longer moves the score of any other case.\n")
    return _apply({_wiki() / "cases" / f"{case_id}.md": render(meta, body)}, info, False,
                  ("revoke", f"{case_id} revoked", f"By {investigator}: {meta['revoke_reason']}"))


# ------------------------------------------------------ ingest: documents ---
def clean_new_pattern(np):
    """Validate a pattern the LLM proposed. Returns None unless it is well formed and truly new."""
    if not isinstance(np, dict) or not isinstance(np.get("title"), str) or not isinstance(np.get("definition"), str):
        return None
    title, definition = " ".join(np["title"].split())[:80], " ".join(np["definition"].split())[:400]
    pid = re.sub(r"[^a-z0-9]+", "_", str(np.get("id") or title).lower()).strip("_")[:40]
    if len(pid) < 3 or len(definition) < 20 or pid in patterns() or pid in pages():
        return None
    words = set(re.findall(r"[a-z]{4,}", title.lower()))
    for p in patterns().values():   # reject a renamed copy of a pattern we already have
        have = set(re.findall(r"[a-z]{4,}", p["title"].lower()))
        if words and len(words & have) / len(words) >= 0.6:
            return None
    lines = lambda key, n: [" ".join(str(x).split())[:200] for x in (np.get(key) or []) if str(x).strip()][:n]
    return {"id": pid, "title": title, "definition": definition, "signals": lines("signals", 5),
            "innocent_explanations": lines("innocent_explanations", 4)}


def read_source(title, text):
    """Read a raw document and propose what it adds to the wiki."""
    catalog = "\n".join(f"- {pid}: {p['definition']}" for pid, p in patterns().items())
    out = llm.chat_json(
        "You maintain a fraud, waste and abuse investigation wiki. Read the document and return JSON with keys: "
        '"summary" (2-3 sentences), "key_points" (3-6 short strings), "pattern_notes" (list of objects with '
        '"pattern" and "note"). Each note is one sentence saying what this document changes or adds for that '
        "pattern. Only use pattern ids from the list. Omit patterns the document does not affect. "
        "Use only what the document says. Also include \"new_pattern\": set it to null unless the document clearly "
        "describes a fraud, waste or abuse scheme that NONE of the listed patterns covers. In that case set it to an "
        'object with "id" (short lowercase name with underscores), "title", "definition" (one sentence), '
        '"signals" (2-4 ways it could be detected in claims data) and "innocent_explanations" (1-3 legitimate reasons '
        "the same data could appear).\n\nPatterns:\n" + catalog,
        f"Title: {title}\n\n{text[:12000]}")
    if out and isinstance(out.get("summary"), str):
        notes = [{"pattern": n["pattern"], "note": " ".join(str(n["note"]).split())}
                 for n in out.get("pattern_notes", []) if isinstance(n, dict) and n.get("pattern") in patterns() and n.get("note")]
        return {"summary": out["summary"].strip(), "key_points": [str(k) for k in out.get("key_points", [])][:6],
                "pattern_notes": notes, "new_pattern": clean_new_pattern(out.get("new_pattern")), "written_by": "llm"}
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", " ".join(text.split())) if len(s.strip()) > 20]
    low = text.lower()
    notes = [{"pattern": pid, "note": "This document mentions the pattern; review it for changes to detection or policy."}
             for pid, p in patterns().items() if pid.replace("_", " ") in low or p["title"].lower() in low]
    return {"summary": " ".join(sentences[:2]), "key_points": sentences[2:6], "pattern_notes": notes,
            "new_pattern": None, "written_by": "template"}


def ingest_source(title, text, approved_by, info, proposal=None, dry_run=False):
    proposal = proposal or read_source(title, text)
    sid = next_id("SRC", "sources")
    new = clean_new_pattern(proposal.get("new_pattern"))
    proposal["new_pattern"] = new
    notes = [f"- [[{n['pattern']}]]: {n['note']}" for n in proposal["pattern_notes"]]
    entry = None
    if new:
        entry = {"title": new["title"], "definition": new["definition"], "signals": new["signals"],
                 "innocent": new["innocent_explanations"], "policy": "", "policy_title": "", "policy_text": "",
                 "public_basis": "", "learned": True, "origin": sid, "approved_by": approved_by or "pending",
                 "added": str(dt.date.today())}
        patterns()[new["id"]] = entry
        notes.append(f"- [[{new['id']}]]: This document is where the pattern was first described.")
    body = f"# {title}\n\nRaw document: `{source_path('documents', sid)}`\n\n## Summary\n{proposal['summary']}\n"
    if proposal["key_points"]:
        body += "\n## Key points\n" + "\n".join(f"- {k}" for k in proposal["key_points"]) + "\n"
    if notes:
        body += "\n## What this changes\n" + "\n".join(notes) + "\n"
    meta = {"type": "source", "id": sid, "title": title, "added": str(dt.date.today()),
            "approved_by": approved_by, "written_by": proposal.get("written_by", "template")}
    try:
        changes = _apply({_wiki() / "sources" / f"{sid}.md": render(meta, body)}, info, dry_run,
                         ("ingest", f"{sid} {title}", f"Source document approved by {approved_by}."
                          + (f" New pattern [[{new['id']}]] created." if new else "")))
    finally:
        if new and dry_run:
            patterns().pop(new["id"], None)
    if not dry_run:
        (_src() / "documents").mkdir(parents=True, exist_ok=True)
        (_src() / "documents" / f"{sid}.md").write_text(f"# {title}\n\n{text}\n", encoding="utf-8")
        if new:
            learned = json.loads(_registry().read_text(encoding="utf-8")) if _registry().exists() else {}
            learned[new["id"]] = entry
            _registry().write_text(json.dumps(learned, indent=1), encoding="utf-8")
    return {"source_id": sid, "proposal": proposal, "changes": changes, "new_pattern_id": new["id"] if new else None}


# ------------------------------------------------------------------ query ---
def _keyword_pages(question, k=4):
    words = {w for w in re.findall(r"[a-z0-9]{4,}", question.lower())}
    scored = []
    for name, path in pages().items():
        if name in ("index", "log"):
            continue
        text = (name.replace("_", " ") + " " + path.read_text(encoding="utf-8")).lower()
        score = sum(text.count(w) for w in words) + 5 * sum(w in name.lower() for w in words)
        if score:
            scored.append((score * (3 if path.parent.name in ("patterns", "notes", "sources", "networks") else 1), name))
    return [n for _, n in sorted(scored, reverse=True)[:k]]


def ask(question):
    """Answer a question from the wiki: read the index, choose pages, read them, answer with citations."""
    pg = pages()
    index = pg["index"].read_text(encoding="utf-8")
    chosen = []
    pick = llm.chat_json(
        'You are navigating a wiki. Given its index and a question, return JSON {"pages": [...]} with up to 6 page '
        "names (exactly as written inside [[ ]]) that are most likely to contain the answer. Prefer pattern, network, "
        "source and note pages, then specific cases.", f"Question: {question}\n\nIndex:\n{index}", max_tokens=200)
    if pick and isinstance(pick.get("pages"), list):
        chosen = [p for p in pick["pages"] if isinstance(p, str) and p in pg][:6]
    if not chosen:
        chosen = _keyword_pages(question)
    read_pages = ["index"] + chosen
    docs = "\n\n".join(f"=== [[{n}]] ===\n{pg[n].read_text(encoding='utf-8')[:3500]}" for n in chosen)
    answer = llm.chat(
        "Answer the investigator's question using ONLY the wiki pages provided. Cite the page for every claim as "
        "[[PageName]]. If the pages do not contain the answer, say so plainly. Never state that fraud occurred; "
        "use 'flagged' or 'confirmed by an investigator'. Keep it under 150 words. Plain sentences or short bullets.",
        f"Question: {question}\n\nWiki pages:\n{docs}", max_tokens=400) if chosen else None
    if answer:
        cited = list(dict.fromkeys(LINK.findall(answer)))
        for c in cited:  # a citation to a page that does not exist is shown as plain text, never as a link
            if c not in pg:
                answer = answer.replace(f"[[{c}]]", f"{c} (no such page)")
        return {"question": question, "answer": answer, "mode": "llm", "pages_read": read_pages,
                "citations": [c for c in cited if c in pg], "unknown_citations": [c for c in cited if c not in pg]}
    lines = ["No LLM is configured, so this is a page lookup, not a written answer. Most relevant pages:"] if chosen else \
            ["Nothing in the Second Brain matches that question yet."]
    for n in chosen:
        meta, body = parse(pg[n].read_text(encoding="utf-8"))
        first = next((l for l in body.splitlines() if l.strip() and not l.startswith(("#", "<!--", "Provider:", "Raw"))), "")
        lines.append(f"- [[{n}]]: {first[:220]}")
    return {"question": question, "answer": "\n".join(lines), "mode": "keyword", "pages_read": read_pages,
            "citations": chosen, "unknown_citations": []}


def file_note(question, answer, approved_by, info, dry_run=False):
    """Keep a good answer as a page, so the next question can build on it."""
    nid = next_id("NOTE", "notes")
    body = f"# {question}\n\n## Answer\n{answer.strip()}\n"
    meta = {"type": "note", "id": nid, "title": question[:90], "added": str(dt.date.today()), "approved_by": approved_by}
    changes = _apply({_wiki() / "notes" / f"{nid}.md": render(meta, body)}, info, dry_run,
                     ("query", f"{nid} filed", f"Answer kept by {approved_by}: {question[:90]}"))
    return {"note_id": nid, "changes": changes}


# ------------------------------------------------------------------- lint ---
def lint():
    pg = pages()
    issues, inbound = [], {n: 0 for n in pg}
    for name, path in pg.items():
        for target in set(LINK.findall(path.read_text(encoding="utf-8"))):
            if target not in pg:
                issues.append({"level": "error", "page": name, "issue": f"broken link [[{target}]]"})
            elif target != name:
                inbound[target] += 1
    for name, n in inbound.items():
        if n == 0 and name not in ("index", "log"):
            issues.append({"level": "warning", "page": name, "issue": "orphan page: nothing links here"})
    cases = case_metas()
    for pid in patterns():
        mine = [c for c in cases if c["pattern"] == pid]
        cleared, confirmed = (sum(c["verdict"] == v for c in mine) for v in ("cleared", "confirmed"))
        if len(mine) >= 4 and cleared > 2 * max(confirmed, 1):
            issues.append({"level": "review", "page": pid,
                           "issue": f"{cleared} of {len(mine)} cases were cleared; the detection rule may be too loose"})
    for pid, p in patterns().items():
        if p.get("learned"):
            issues.append({"level": "review", "page": pid,
                           "issue": "learned pattern with no detection rule yet; cases can cite it but nothing flags it"})
    for c in cases:
        if c["pattern"] not in patterns():
            issues.append({"level": "error", "page": c["id"], "issue": f"unknown pattern {c['pattern']}"})
    return {"pages": len(pg), "cases": len(cases), "issues": issues}
