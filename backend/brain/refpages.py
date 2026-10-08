"""Reference pages of the Second Brain: business rules, data definitions, runbooks,
technical documentation and regulatory background.

These are written by code, not by the LLM. Counts, table sizes, tier thresholds and
column lists are read from the pipeline and the data files each time the wiki is rebuilt,
so the pages cannot drift from what the system actually does.
"""
import csv
import json
from functools import lru_cache

from backend.pipeline import reference
from backend.pipeline.common import PROC, RAW

from . import confidence

GROUPS = ("rules", "data", "process", "system", "regulatory")
NOTE = "> Reference page written by code from the pipeline. Rebuilt on every change; do not edit by hand.\n"

# ------------------------------------------------------------------ rules ---
RULES = {
    "R1": {
        "key": "duplicate_billing", "title": "R1 Duplicate claim", "patterns": ["duplicate_billing"],
        "checks": "The same member, provider, procedure code and billed amount appear again within 3 days.",
        "threshold": "Gap between the two claims of 3 days or less; all four fields must match exactly.",
        "fields": ["member_id", "provider_id", "procedure_code", "billed_amount", "service_datetime"],
        "table": "None. The rule compares claims with each other.",
        "exceptions": ["A corrected resubmission where the original was rejected and never paid",
                       "A procedure repeated on the same day with a repeat-procedure modifier (modifiers are not in this data)"],
        "regs": ["REG-CLAIMS"],
    },
    "R2": {
        "key": "impossible_timing", "title": "R2 Impossible travel", "patterns": ["impossible_timing"],
        "checks": "One provider bills at two different facilities that are too far apart to travel between in the time available.",
        "threshold": "Facilities more than 100 km apart (straight-line distance from coordinates) and claims 60 minutes or less apart. Both claims are flagged.",
        "fields": ["provider_id", "facility_id", "service_datetime", "facilities.lat", "facilities.lon"],
        "table": "None. Distance is computed from the facility coordinates in [[data_facilities]].",
        "exceptions": ["Telehealth billed with the wrong place of service",
                       "A group billing identifier shared by more than one clinician"],
        "regs": ["REG-CLAIMS"],
    },
    "R3": {
        "key": "unbundling", "title": "R3 Bundling edit pair (PTP)", "patterns": ["unbundling"],
        "checks": "A component code (column 2) is billed together with the comprehensive code that already includes it (column 1), for the same member, provider and date.",
        "threshold": "Any matching pair on the same member, provider and service date. The component claim is flagged.",
        "fields": ["member_id", "provider_id", "procedure_code", "service_datetime"],
        "table": "PTP",
        "exceptions": ["Pairs with modifier indicator 1 are payable when a supported modifier is on the claim (modifiers are not in this data)",
                       "Tests drawn on separate dates that look same-day because of a date entry error"],
        "regs": ["REG-NCCI"],
    },
    "R4": {
        "key": "mue_exceeded", "title": "R4 Unit limit (MUE)", "patterns": ["excessive_utilization", "duplicate_billing"],
        "checks": "The units billed for one code, for one member by one provider on one date, are above the most a provider would plausibly report.",
        "threshold": "Running total of units for the member, provider, code and date exceeds the code's limit.",
        "fields": ["member_id", "provider_id", "procedure_code", "units", "service_datetime"],
        "table": "MUE",
        "exceptions": ["Some limits are per claim line rather than per day, and some can be exceeded with documentation of medical necessity"],
        "regs": ["REG-NCCI"],
    },
    "R5": {
        "key": "upcoding", "title": "R5 Visit-level drift", "patterns": ["upcoding"],
        "checks": "A provider's share of the highest office-visit level (level 5) in a month is far above normal.",
        "threshold": "Level 5 is 35% or more of the provider's office visits in a month with at least 10 office visits. Only the level-5 claims of that month are flagged.",
        "fields": ["provider_id", "em_level", "service_datetime"],
        "table": "None. The comparison figure is the level-5 share across all providers.",
        "exceptions": ["A documented complex, multi-condition patient panel",
                       "The rule compares with all providers, not same-specialty peers; the anomaly model does the peer comparison"],
        "regs": ["REG-EM"],
    },
}
PATTERN_RULES = {}
for _rid, _r in RULES.items():
    for _p in _r["patterns"]:
        PATTERN_RULES.setdefault(_p, []).append(_rid)
PATTERN_REGS = {
    "duplicate_billing": ["REG-CLAIMS", "REG-FCA"], "upcoding": ["REG-EM", "REG-FCA"],
    "impossible_timing": ["REG-CLAIMS", "REG-FCA"], "unbundling": ["REG-NCCI", "REG-FCA"],
    "collusive_ring": ["REG-STARK", "REG-AKS"], "excessive_utilization": ["REG-PIM", "REG-NCCI"],
}

# ------------------------------------------------------------------- data ---
SYN = "Synthetic, written by `data/generate_data.py` with a fixed seed"
DATA = {
    "claims": {
        "what": "One row per billed service line. This is the main input to every rule and model.",
        "lineage": f"{SYN}. Procedure code numbers are real CPT/HCPCS codes; prices approximate national Medicare fee schedule rates.",
        "fields": {
            "claim_id": "Unique claim line identifier (C + 6 digits)",
            "member_id": "The patient the service was billed for; links to [[data_members]]",
            "provider_id": "The rendering provider who billed; links to [[data_providers]]",
            "facility_id": "Where the service was billed as delivered; links to [[data_facilities]]",
            "service_datetime": "Date and time of service",
            "claim_type": "professional, laboratory, dme (equipment), home_health, ambulance or behavioral_health",
            "procedure_code": "CPT/HCPCS code for the service",
            "em_level": "Office-visit level 1 to 5 for codes 99211-99215; empty for other codes",
            "units": "Number of units billed on the line",
            "billed_amount": "Amount the provider charged",
            "paid_amount": "Amount the plan paid; used for dollar exposure",
        },
    },
    "providers": {
        "what": "One row per provider that bills the plan.",
        "lineage": f"{SYN}. Names are invented; cities and coordinates are real Texas locations.",
        "fields": {
            "provider_id": "Unique provider identifier (P + 3 digits)", "name": "Invented display name",
            "specialty": "Used to compare a provider with same-specialty peers",
            "facility_id": "Home facility", "owner_id": "Owning entity; links to [[data_ownership]]",
            "city": "Home city", "lat": "Latitude of the home facility", "lon": "Longitude of the home facility",
        },
    },
    "members": {
        "what": "One row per plan member (patient).",
        "lineage": f"{SYN}. No real person is represented.",
        "fields": {
            "member_id": "Unique member identifier (M + 5 digits)", "age": "Age in years", "gender": "F or M",
            "city": "Home city", "chronic_flag": "1 if the member has a chronic condition and so uses more care",
        },
    },
    "facilities": {
        "what": "One row per place of service.",
        "lineage": f"{SYN}. Coordinates are real, so travel distances in [[R2]] are true distances.",
        "fields": {
            "facility_id": "Unique facility identifier (F + 3 digits)", "name": "Invented display name",
            "type": "Clinic, Medical Office or Hospital Outpatient", "city": "City", "lat": "Latitude", "lon": "Longitude",
        },
    },
    "referrals": {
        "what": "One row each time a provider refers a member to another provider. Used to find closed referral loops.",
        "lineage": SYN + ".",
        "fields": {
            "referral_id": "Unique referral identifier", "from_provider_id": "Provider who referred",
            "to_provider_id": "Provider who received the referral", "member_id": "Member referred",
            "referral_date": "Date of the referral",
        },
    },
    "ownership": {
        "what": "Which owner controls which provider or facility. Used to measure how much of a network shares one owner.",
        "lineage": SYN + ".",
        "fields": {
            "owner_id": "Unique owner identifier (O + 3 digits)", "owner_name": "Invented company name",
            "entity_type": "provider or facility", "entity_id": "The provider or facility owned",
        },
    },
    "investigations": {
        "what": "Historical closed investigations. They seed the case pages and are the first precedents.",
        "lineage": f"{SYN}. A copy is kept unedited at `knowledge/sources/investigations.csv`.",
        "fields": {
            "case_id": "Historical case identifier (INV + 3 digits)", "provider_id": "Provider investigated",
            "specialty": "Provider specialty at the time", "pattern": "The pattern investigated; one of the pattern pages",
            "verdict": "confirmed, cleared or inconclusive", "reasoning": "The investigator's stated reason",
            "exposure_amount": "Dollars in question", "recovered_amount": "Dollars recovered",
            "opened_date": "Date opened", "closed_date": "Date closed",
        },
    },
}
EVAL_ONLY = {"ground_truth": "which providers had a scenario injected", "claim_labels": "which claims were injected"}

# ---------------------------------------------------------------- process ---
REQUESTS = {
    "duplicate_billing": "Remittance history for both claims; any corrected-claim or rejection notice.",
    "upcoding": "A sample of 10-20 level-5 visit notes, to compare documented complexity or time with the level billed.",
    "impossible_timing": "Appointment schedules and sign-in records for both sites; telehealth logs.",
    "unbundling": "The claim lines with modifiers and the lab or procedure report for the date.",
    "collusive_ring": "Referral records and care plans for the shared members; ownership and financial-relationship disclosures.",
    "excessive_utilization": "Plans of care, orders and delivery or attendance records for the highest-volume members.",
}

REGS = {
    "REG-NCCI": {
        "title": "CMS National Correct Coding Initiative (NCCI)",
        "what": "CMS publishes two public tables to stop improper coding. Procedure-to-Procedure (PTP) edits list pairs of codes that "
                "should not be paid together, with a modifier indicator (0 never, 1 with a supported modifier, 9 not applicable). "
                "Medically Unlikely Edits (MUE) give the most units of a code a provider would report for one patient on one day.",
        "use": "The PTP pairs drive [[R3]] and the MUE values drive [[R4]].",
        "source": "CMS NCCI edit files and the NCCI Policy Manual, published on cms.gov and updated quarterly.",
    },
    "REG-FCA": {
        "title": "False Claims Act",
        "what": "United States federal law (31 U.S.C. 3729-3733) that makes a person liable for knowingly submitting false claims for "
                "payment to the government. It is the main civil enforcement tool for health care fraud in federal programmes.",
        "use": "Background for why confirmed duplicate, upcoded, unbundled or not-rendered services matter. The system never decides "
               "that a claim was false or that anyone acted knowingly; that is for investigators and counsel.",
        "source": "31 U.S.C. 3729-3733.",
    },
    "REG-AKS": {
        "title": "Anti-Kickback Statute",
        "what": "United States federal criminal law (42 U.S.C. 1320a-7b(b)) that prohibits offering or receiving anything of value "
                "to induce or reward referrals of services paid by federal health care programmes.",
        "use": "Background for the collusive network pattern. Referral loops among related providers are a reason to look, not proof of a kickback.",
        "source": "42 U.S.C. 1320a-7b(b); safe harbours at 42 CFR 1001.952.",
    },
    "REG-STARK": {
        "title": "Physician self-referral law (Stark)",
        "what": "United States federal law (42 U.S.C. 1395nn) that restricts physicians from referring Medicare patients for certain "
                "services to entities they have a financial relationship with, unless an exception applies.",
        "use": "Background for the shared-ownership signal on network pages.",
        "source": "42 U.S.C. 1395nn; regulations at 42 CFR 411.350-411.389.",
    },
    "REG-EM": {
        "title": "Evaluation and management (office visit) coding guidance",
        "what": "Office visits are billed with CPT codes 99211-99215. The level must be supported by documented medical decision "
                "making or total time on the date of the visit.",
        "use": "Basis for [[R5]] and the upcoding pattern. A high level mix triggers a records review, not a denial.",
        "source": "CMS Evaluation and Management Services Guide; AMA CPT office visit guidelines.",
    },
    "REG-PIM": {
        "title": "Medicare Program Integrity Manual",
        "what": "CMS manual (Publication 100-08) describing how Medicare contractors use data analysis and medical review to find "
                "and act on improper payments.",
        "use": "Background for peer comparison in the anomaly model and for the excessive utilization pattern.",
        "source": "CMS Internet-Only Manual, Publication 100-08.",
    },
    "REG-CLAIMS": {
        "title": "Medicare claims processing rules (duplicates, place of service)",
        "what": "CMS claims processing guidance covers duplicate claim edits and the place-of-service code set, including how "
                "telehealth is reported.",
        "use": "Background for [[R1]] and [[R2]].",
        "source": "CMS Medicare Claims Processing Manual (Publication 100-04); CMS place-of-service code set.",
    },
    "REG-HIPAA": {
        "title": "HIPAA Privacy and Security Rules",
        "what": "United States rules (45 CFR Parts 160 and 164) on how protected health information may be used, disclosed and safeguarded.",
        "use": "The reason this prototype uses only synthetic data and a local LLM. A real deployment would hold member data and "
               "would need access control, audit logging and a compliant LLM arrangement.",
        "source": "45 CFR Parts 160 and 164.",
    },
}


@lru_cache(maxsize=None)
def _csv(name):
    path = RAW / f"{name}.csv"
    if not path.exists():
        return [], 0
    with path.open(newline="", encoding="utf-8") as f:
        header = next(csv.reader(f), [])
        return header, sum(1 for _ in f)


def _json(name):
    path = PROC / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _alerts():
    path, out = PROC / "claim_flags.csv", {}
    if path.exists():
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                out[row["rule"]] = out.get(row["rule"], 0) + 1
    return out


def _page(kind, pid, title, body):
    return f"---\ntype: {kind}\nid: {pid}\ntitle: {title}\nwritten_by: code\n---\n# {title}\n\n{NOTE}\n{body}"


def undefined_fields():
    """Columns present in a data file that have no definition, and the reverse. Used by the health check."""
    out = []
    for name, d in DATA.items():
        header, _ = _csv(name)
        if not header:
            continue
        for col in header:
            if col not in d["fields"]:
                out.append((f"data_{name}", f"column `{col}` is in {name}.csv but has no definition"))
        for col in d["fields"]:
            if col not in header:
                out.append((f"data_{name}", f"`{col}` is defined but is not a column in {name}.csv"))
    return out


def rule_pages(pattern_titles):
    alerts, out = _alerts(), {}
    for rid, r in RULES.items():
        if r["table"] == "PTP":
            table = (f"{len(reference.PTP_EDITS):,} code pairs: {reference.PTP_SOURCE}. Loaded by `backend/pipeline/reference.py`. "
                     "See [[REG-NCCI]].")
        elif r["table"] == "MUE":
            table = (f"{len(reference.MUE_LIMITS):,} unit limits: {reference.MUE_SOURCE}. Loaded by `backend/pipeline/reference.py`. "
                     "See [[REG-NCCI]].")
        else:
            table = r["table"]
        tables = sorted({f.split(".")[0] for f in r["fields"] if "." in f} | {"claims"})
        body = (f"## What it checks\n{r['checks']}\n\n## Threshold\n{r['threshold']}\n\n## Reference table\n{table}\n\n"
                f"## Data used\n" + "\n".join(f"- `{f}`" for f in r["fields"])
                + "\n- Defined in: " + ", ".join(f"[[data_{t}]]" for t in tables)
                + "\n\n## Known exceptions\n" + "\n".join(f"- {e}" for e in r["exceptions"])
                + "\n\n## Patterns it supports\n" + "\n".join(f"- [[{p}]] | {pattern_titles.get(p, p)}" for p in r["patterns"])
                + "\n\n## Regulatory background\n" + "\n".join(f"- [[{g}]] | {REGS[g]['title']}" for g in r["regs"])
                + f"\n\n## Current results\n- {alerts.get(r['key'], 0):,} claim alerts in the current data.\n"
                  "- Implemented in `backend/pipeline/rules.py`.\n- A flag is a reason to look. It is not a finding.\n")
        out[rid] = _page("rule", rid, r["title"], body)
    return out


def data_pages():
    out = {}
    for name, d in DATA.items():
        header, rows = _csv(name)
        cols = header or list(d["fields"])
        used = [rid for rid, r in RULES.items() if name == "claims" or any(f.startswith(name + ".") for f in r["fields"])]
        body = (f"## What it is\n{d['what']}\n\n## Where it comes from\n{d['lineage']}\n\n"
                f"## Size\n- {rows:,} rows in `data/raw/{name}.csv`.\n\n## Fields\n"
                + "\n".join(f"- `{c}`: {d['fields'].get(c, 'NOT DEFINED')}" for c in cols)
                + "\n\n## Used by\n" + ("\n".join(f"- [[{r}]] | {RULES[r]['title']}" for r in used) if used else
                                          "- The models and the network analysis; see [[system_models]].")
                + "\n- See also [[system_architecture]].\n")
        out[f"data_{name}"] = _page("data", f"data_{name}", f"Data: {name}", body)
    return out


def process_pages(pattern_titles):
    t, out = confidence.TIERS, {}
    hi, med = t["high"]["threshold"], t["medium"]["threshold"]
    body = ("## Purpose\nWhat an investigator does with a case, depending on its confidence tier.\n\n## The three tiers\n"
            f"- **Fast-track** (confidence {hi:.2f} or above). {t['high']['route']}. Owner: {t['high']['owner']}. "
            "Open the case now, request records (see [[runbook_evidence]]), and record a verdict when the review ends.\n"
            f"- **Review** (confidence {med:.2f} to {hi:.2f}). {t['medium']['route']}. Owner: {t['medium']['owner']}. "
            "Read the brief and the cited precedents first; check each innocent explanation on the pattern page before requesting records.\n"
            f"- **Not enough evidence** (below {med:.2f}). {t['low']['route']}. Owner: {t['low']['owner']}. "
            "No case is opened. The provider stays in monitoring and is re-scored on the next run.\n\n"
            "## Order of work\n- Work the queue from the top; it is ordered by priority, defined in [[system_scoring]].\n"
            "- The capacity line shows how many cases the team can take: 5 open cases per investigator.\n"
            "- A case in a network is reviewed with the network page open; a verdict on one member changes the others.\n\n"
            "## Rules that always apply\n- The system proposes; a named person decides.\n"
            "- Never tell a provider they were flagged by a model; requests cite the claims and the policy.\n"
            "- When the evidence is thin, record `inconclusive`, not a guess.\n- Next step: [[runbook_verdict]].\n")
    out["runbook_triage"] = _page("process", "runbook_triage", "Runbook: triage by confidence tier", body)
    body = ("## Purpose\nHow a decision is recorded so that it becomes precedent.\n\n## Steps\n"
            "- Open the case and choose a verdict: `confirmed`, `cleared` or `inconclusive`.\n"
            "- Write the reason in one or two sentences. State what the records showed, not what the model scored.\n"
            "- Enter your name and preview. The preview lists every page that will change and the lesson to be saved.\n"
            "- Approve. A case page is created; the pattern, provider and network pages, the index and the log are updated.\n\n"
            "## What each verdict does to later cases\n"
            "- `confirmed`: similar open cases gain confidence; cases in the same network gain the most.\n"
            "- `cleared`: similar open cases lose a little confidence; the same provider and pattern loses the most, "
            "and the reason is added to the pattern's known innocent explanations.\n"
            "- `inconclusive`: saved as history; no change to confidence.\n- The exact amounts are in [[system_scoring]].\n\n"
            "## Corrections\n- A wrong verdict is corrected by a named person and logged; pages are never edited silently. See [[runbook_knowledge]].\n")
    out["runbook_verdict"] = _page("process", "runbook_verdict", "Runbook: recording a verdict", body)
    body = ("## Purpose\nWhat to ask a provider for, by pattern. Request the least that settles the question.\n\n## By pattern\n"
            + "\n".join(f"- [[{p}]] | {pattern_titles.get(p, p)}: {txt}" for p, txt in REQUESTS.items())
            + "\n\n## Before sending a request\n- Check the pattern page for an innocent explanation that the claims already rule in or out.\n"
              "- Cite the specific claim IDs shown in the brief.\n- Back to [[runbook_triage]].\n")
    out["runbook_evidence"] = _page("process", "runbook_evidence", "Runbook: evidence to request", body)
    body = ("## Purpose\nHow new knowledge enters the Second Brain and who may approve it.\n\n## Three ways in\n"
            "- **A verdict** on a case: see [[runbook_verdict]].\n"
            "- **A source document** (policy, bulletin, audit memo): the LLM summarises it and proposes notes for the patterns it "
            "affects. If it describes a scheme not in the library, the LLM proposes a new pattern; the approver creates it, "
            "adds it to an existing pattern, or saves the document only.\n"
            "- **A kept answer**: a good answer to a question is saved as a note page.\n\n"
            "## Controls\n- Nothing is saved without a preview and a named approver.\n"
            "- Raw documents are stored unedited in `knowledge/sources/documents/`.\n"
            "- A document can add notes and patterns. It cannot change a verdict, a score or a rule.\n"
            "- A pattern learned from a document is marked knowledge only until a detection rule is written.\n"
            "- Every change is recorded in [[log]]. The health check reports broken links, orphan pages, patterns that are mostly "
            "cleared, and data columns with no definition.\n- Limits of the system: [[system_limits]].\n")
    out["runbook_knowledge"] = _page("process", "runbook_knowledge", "Runbook: adding and approving knowledge", body)
    return out


def system_pages():
    m, out = _json("metrics.json"), {}
    fn, pv, pr, an = m.get("funnel", {}), m.get("provider_level", {}), m.get("prediction", {}), m.get("anomaly", {})
    body = ("## Flow\n- Claims and reference data are read from `data/raw/` (see [[data_claims]]).\n"
            "- Five claim rules flag individual claims: [[R1]], [[R2]], [[R3]], [[R4]], [[R5]].\n"
            "- An anomaly model compares each provider with same-specialty peers; a graph step finds provider networks; "
            "a prediction model estimates repeat risk. See [[system_models]].\n"
            "- Signals are combined into one case per provider, scored and ranked. See [[system_scoring]].\n"
            "- The Second Brain supplies precedents that adjust confidence, and stores every verdict.\n\n"
            + (f"## Current funnel\n- {fn.get('claims', 0):,} claims, {fn.get('raw_alerts', 0):,} claim alerts, "
               f"{fn.get('cases', 0)} cases.\n\n" if fn else "")
            + "## Components\n- Pipeline: `backend/pipeline/` (rules, anomaly, graph, predict, run_all). Run offline.\n"
              "- Second Brain: `backend/brain/` (wiki, retrieve, confidence, brief, llm).\n"
              "- API: FastAPI in `backend/app/`. Interface: React in `frontend/`.\n"
              "- Knowledge: markdown files in `knowledge/`; conventions in `knowledge/SCHEMA.md`.\n\n"
              "## Dependencies\n- Python: pandas, numpy, scikit-learn, networkx, igraph and leidenalg, FastAPI.\n"
              "- LLM: any OpenAI-compatible endpoint; the default is a local Ollama model, so no data leaves the machine. "
              "Without an LLM the system runs from templates.\n- No database; data is CSV and JSON, knowledge is markdown.\n"
              "- Limits: [[system_limits]].\n")
    out["system_architecture"] = _page("system", "system_architecture", "System: architecture and dependencies", body)
    preds = "".join(f"- {h}: cross-validated AUC {pr[h]['auc_cv']:.2f} on {pr[h]['positives']} positive examples.\n"
                    for h in ("30d", "60d", "90d") if h in pr)
    body = ("## Anomaly model\n- Isolation Forest, 300 trees, on provider features expressed relative to same-specialty peers.\n"
            "- An isotonic calibrator turns the raw score into a probability.\n"
            + (f"- AUC {an['anomaly_auc']:.2f} against the injected scenarios.\n" if an.get("anomaly_auc") else "")
            + "\n## Network analysis\n- Providers are linked when they share far more members than chance would give "
              "(lift of 3 or more and at least 15 shared members).\n"
              "- Leiden community detection groups linked providers; groups of 3 or more become a network page.\n"
              "- Referral loops are found from [[data_referrals]]; shared ownership from [[data_ownership]].\n"
              "- BiRank spreads risk from flagged providers through shared members.\n\n"
              "## Prediction model\n- Three gradient boosting classifiers, one each for 30, 60 and 90 days.\n"
              "- Target: the provider receives 3 or more rule flags in the horizon. It predicts repeat detection, not proven fraud.\n"
            + preds
            + "\n## What the LLM does and does not do\n- It writes: the lesson from a verdict, document summaries, pattern notes, "
              "new-pattern proposals, answers to questions, and the brief summary.\n"
              "- It does not score, rank or decide. Any LLM text containing an ID or dollar figure not in its input is discarded.\n"
              "- Saved models are in `backend/models/`. How scores combine: [[system_scoring]].\n")
    out["system_models"] = _page("system", "system_models", "System: models", body)
    t = confidence.TIERS
    body = ("## Evidence strength\n- 0.5 x rule score + 0.2 x anomaly (capped) + 0.4 x network score, plus 0.15 when at least two of "
            "the three methods agree. Capped at 1.\n\n## Precedent adjustment\n"
            "- Confirmed precedent: +0.25 if in the same network, otherwise +0.10 x similarity.\n"
            "- Cleared precedent: -0.30 if same provider and pattern, otherwise -0.04 x similarity.\n"
            "- Total adjustment is limited to between -0.35 and +0.30. Up to three most similar closed cases are used.\n\n"
            "## Confidence and tier\n- Confidence = evidence strength + precedent adjustment.\n"
            f"- {t['high']['threshold']:.2f} or above: fast-track. {t['medium']['threshold']:.2f} or above: review. "
            "Below that: not enough evidence. What to do in each: [[runbook_triage]].\n\n"
            "## Risk and priority\n- Risk = 0.35 x rules + 0.20 x anomaly + 0.20 x network + 0.05 x BiRank + 0.20 x predicted repeat risk.\n"
            "- Priority = 0.30 x risk + 0.20 x dollars + 0.10 x members affected + 0.15 x severity + 0.25 x confidence.\n"
            "- Implemented in `backend/brain/confidence.py` and `backend/app/store.py`.\n- Models behind the inputs: [[system_models]].\n")
    out["system_scoring"] = _page("system", "system_scoring", "System: scoring and routing", body)
    body = ("## Data\n- All data is synthetic. Results show recovery of scenarios we injected, not performance on real claims.\n"
            + (f"- {pv.get('fwa_in_queue', 0)} of {pv.get('fwa_providers', 0)} injected providers are in the queue; "
               f"{pv.get('legit_outliers_in_queue', 0)} legitimate outlier(s) are also in it.\n" if pv else "")
            + "- Prices and the visit-level mix are approximations.\n- Claims carry no modifiers. The only provider record is one synthetic sample used to show record review.\n\n"
              "## Rules and tables\n- The bundling table is a subset of the CMS file plus pairs derived from code definitions; see [[R3]].\n"
              "- Three equipment unit limits are illustrative; see [[R4]].\n\n"
              "## Models\n- Calibration uses injected labels in place of audited outcomes.\n"
              "- The prediction target is future rule flags.\n\n"
              "## Second Brain\n- Policies in `knowledge/sources/policies/` and the regulatory pages are short summaries written for this "
              "prototype, not legal advice.\n- Patterns learned from documents have no detection rule.\n"
              "- There is no login; the approver's name is typed, not verified.\n- No medical-necessity judgment is made.\n"
              "- Privacy basis: [[REG-HIPAA]]. Overview: [[system_architecture]].\n")
    out["system_limits"] = _page("system", "system_limits", "System: known limits", body)
    return out


def reg_pages(pattern_titles):
    out = {}
    for gid, g in REGS.items():
        pats = [p for p, regs in PATTERN_REGS.items() if gid in regs]
        rules = [rid for rid, r in RULES.items() if gid in r["regs"]]
        body = ("> General background written for this prototype. It is a short summary, not legal advice; verify against the source.\n\n"
                f"## What it is\n{g['what']}\n\n## How this system uses it\n{g['use']}\n\n## Source to verify\n- {g['source']}\n\n"
                "## Linked pages\n" + "\n".join(f"- [[{r}]] | {RULES[r]['title']}" for r in rules)
                + ("\n" if rules else "") + "\n".join(f"- [[{p}]] | {pattern_titles.get(p, p)}" for p in pats)
                + ("\n" if pats else "") + "- [[system_limits]]\n")
        out[gid] = _page("regulatory", gid, g["title"], body)
    return out


def all_pages(pattern_titles):
    """{group: {page name: text}} for every reference page."""
    return {"rules": rule_pages(pattern_titles), "data": data_pages(), "process": process_pages(pattern_titles),
            "system": system_pages(), "regulatory": reg_pages(pattern_titles)}


def index_lines(pattern_titles):
    titles = {"rules": "Business rules", "data": "Data definitions", "process": "Runbooks",
              "system": "Technical documentation", "regulatory": "Regulatory material"}
    lines = []
    for group, pgs in all_pages(pattern_titles).items():
        lines += ["", f"## {titles[group]}"]
        for name, text in pgs.items():
            lines.append(f"- [[{name}]] | {text.split('title: ', 1)[1].splitlines()[0]}")
    return lines
