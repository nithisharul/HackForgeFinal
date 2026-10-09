# ClaimShield Nexus: the SIU's Second Brain

NOTE : Nithi_Base is the Main branch 

Finds suspicious claims and coordinated provider networks in synthetic payer data, predicts 30/60/90-day
repeat risk, ranks cases for a Special Investigations Unit (SIU), and explains each case with evidence.
Every investigator decision is saved to a linked knowledge base, the Second Brain, and becomes precedent
for the next case.

All data is synthetic. The system produces leads for human review; it never decides that fraud occurred.

## What it does

| Stage | What happens | Where |
|---|---|---|
| Detect | Five claim rules, an anomaly model, network analysis and three prediction models score 80,452 claims from 300 providers | `backend/pipeline/` |
| Rank | 846 claim alerts become 34 cases in three tiers (fast-track, review, not enough evidence), ordered by priority against team capacity | `backend/app/store.py`, `backend/brain/confidence.py` |
| Explain | Each case has a brief with checked facts, a network diagram, precedents, and a plan for what to verify next | `backend/brain/brief.py`, `auditnext.py`, `clinical_audit.py` |
| Decide | A signed-in investigator records a verdict after previewing what it will change | `backend/app/routes/cases.py` |
| Remember | The verdict becomes a page in the Second Brain and moves the confidence of similar open cases | `backend/brain/wiki.py`, `retrieve.py` |
| Protect | Accounts and roles, a signed audit log, tamper detection, document screening, security events | `backend/app/auth.py`, `backend/security/` |

## Run it

Python 3.11+ and Node 18+. Two terminals, both starting in this folder.

```
python -m pip install -r backend/requirements.txt
python -m backend.pipeline.run_all
python -m uvicorn backend.app.main:app --reload
```

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5173, open Security and access in the sidebar and create an account. The first
account on a server becomes the admin.

The generated data, pipeline outputs and trained models are in the repository, so nothing has to be
generated or trained first. To rebuild:

```
python data/generate_data.py                  # regenerate the synthetic CSVs
python -m backend.pipeline.run_all            # re-score with the saved models and rebuild the Second Brain pages
python -m backend.pipeline.run_all --retrain  # retrain and overwrite backend/models/
python -m backend.pipeline.run_all --region in [--retrain]   # the India region (see below)
```

Restart the API after a pipeline run. If saved models fail to load, your scikit-learn version differs from
the pinned one; run with `--retrain`.

## Sign-in for writes

Reading, previews and questions are open. Saving a verdict, a kept answer or a source document needs a
signed-in account with the right role (see Accounts and roles below); the server checks every write, so
requests sent straight to the API or tunnel are refused too, and the signed-in name is what gets recorded.
The first account created in the app becomes the admin. Accounts can also be defined in the git-ignored
`.env`, never in the frontend or Cloudflare; these are admins:

```
python -m backend.app.auth add "Investigator Name"   # prompts for a passcode (12+ characters); restart the API
```

## Deploy (Cloudflare, free plan)

`cloudflare/` holds a Worker that serves the React build and forwards `/api/*` to the API on the host
machine through a Cloudflare quick tunnel. `cd cloudflare && npm install && npm run deploy` publishes the
site; with the API running on port 8000, `npm run go-live` opens the tunnel (keep it running). Some
campus and office networks block Cloudflare tunnels. `cloudflare/Dockerfile` builds the API image for
Cloudflare Containers (Workers Paid plan) or any Docker host.

## Connect a free LLM (optional, recommended for the demo)

Create `.env` in this folder. The default setup is a local model through Ollama, so no data leaves the machine:

```
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=gemma3:4b
```

Any OpenAI-compatible endpoint works. Without an LLM everything still runs, from templates and keyword lookup.

## Present it

The front page is also the presentation. Select Present (or press P): every section becomes a full-screen slide.
Arrow keys, Page Up/Down and Space move; F toggles full screen; Esc leaves. A rail on the right lists the slides,
with a counter and the elapsed time. The "Now the real app" slide starts a guided walkthrough of the live queue
and case, dimming everything but the part being explained; it returns to the slides when it ends. The app is
fully usable throughout. Some slides build: the arrow first steps through them (the funnel stage by stage, the
pipeline, and the architecture map's 8 scenes, where any part can be selected for what it does, what happens if
it fails and what protects it). N shows presenter notes and a pace clock for a 6-minute slot. Export saves the
slides as a PDF (one 16:9 page per slide, through the browser's Save as PDF) or as one HTML file that opens offline,
a backup for the day. Let the LLM warm-up finish before rehearsing (see Connect a free LLM).

## Integrations and operations

| | |
|---|---|
| Slack, Microsoft Teams, signed webhooks | Verdicts, withdrawn precedents, approved sources and patterns, and HIGH or CRITICAL security events, sent as they happen. IDs and links only. Settings in `.env.example` |
| Exports | `GET /api/cases/{id}/fhir` (FHIR ExplanationOfBenefit) and `GET /api/queue/export` (the ranked queue as CSV) |
| Probes | `GET /api/health/live`, `GET /api/health/ready` (both regions load and the database opens) |
| Logs and headers | One JSON line per request with an `X-Request-ID`; security headers; `no-store` on API responses; `CORS_ORIGINS` allowlist |

The Documentation page in the app (`#/docs`) covers all of this, with an API reference read live from the server.

## Detection

| Method | Looks at | Catches |
|---|---|---|
| R1 duplicate claim | Single claims | Same member, provider, code and amount within 3 days |
| R2 impossible travel | Single claims | One provider at two facilities over 100 km apart within 60 minutes |
| R3 bundling pair | Single claims | A component code billed with the comprehensive code that includes it (CMS NCCI pair table) |
| R4 unit limit | Single claims | Units above the CMS limit for one member in one day |
| R5 visit-level drift | A provider's month | Level 5 at 35% or more of office visits |
| Isolation Forest with isotonic calibration | A provider's overall behaviour against same-specialty peers | Unusual behaviour no rule describes |
| Network analysis (shared-member lift, Leiden communities, referral loops, common ownership, BiRank) | Groups of providers | Coordinated rings |
| Gradient boosting, one model per horizon | The trend over time | Who is likely to be flagged again in 30, 60 and 90 days |

A provider becomes a case with 3 or more flagged claims, an anomaly probability of 25% or more, or
membership of a detected network.

### If a detector fails

Detection runs offline and the app serves its saved results, so a detector outage never takes the
investigators' app down. Within a pipeline run each detector is isolated: if one fails, the run records why
and continues with the others. Scoring weights are spread over the detectors that ran, each affected case
carries a caution in its brief, the app shows a "degraded mode" banner naming what is missing, and a
security event is recorded. `GET /api/health` reports detectors, result age, LLM reachability and
knowledge integrity.

To see it: `CSN_SIMULATE_FAILURE=ml python -m backend.pipeline.run_all` (PowerShell:
`$env:CSN_SIMULATE_FAILURE="ml"; python -m backend.pipeline.run_all`). Values: `rules`, `ml`, `graph`,
`prediction`, comma-separated. Clear the variable and run again to return to normal.

## The Second Brain

A folder of linked markdown pages (`knowledge/wiki/`), with raw sources kept unedited in `knowledge/sources/`.

| Pages | Hold |
|---|---|
| Patterns | Each fraud, waste and abuse pattern: definition, signals, innocent explanations, lessons, cases |
| Cases, providers, networks | Every closed case with verdict, reason and lesson; provider history; detected networks |
| Sources, notes | Documents people added; answers people chose to keep |
| Rules, data definitions, runbooks, technical docs, regulatory | How the system and the team work. Written by code from the pipeline |
| Index, log | List of all pages; record of every change |

- **It changes scores.** Confirmed precedents raise the confidence of similar open cases; cleared ones lower it.
- **It fills the case page.** Precedents, innocent explanations and the evidence to request come from its pages.
- **It answers questions**, citing the pages used.
- **It grows** through verdicts, source documents (which can introduce a new pattern) and kept answers. Each
  shows a preview and needs a signed-in approver.

The LLM writes text only: case summaries, the suggested first step, the lesson from a verdict, document
summaries and pattern proposals, answers, and a reading of a returned provider record. It never scores, ranks
or decides. LLM text containing an ID or dollar figure that is not in its input is discarded.

## On a case page

- **Investigation brief** with every ID, code and dollar figure checked against the data.
- **AuditNext**: candidate checks ranked by expected information gain per hour. The starting uncertainty is
  the case's confidence; each check's accuracy starts from an assumed value and is updated from closed
  cases in the Second Brain. Costs are assumptions, stated on the panel.
- **Investigation steps** drawn from the Second Brain.
- **Provider record review**: when a record is on file for the case, the LLM compares it with the flagged
  claims and reports a possible discrepancy for the investigator to judge. One synthetic sample is included
  (CASE-P209).
- **Network, confidence and precedents**, and the verdict form.

## Accounts and roles

Accounts are stored in SQLite (`data/app.db`, not in git) with salted PBKDF2 passcode hashes.

| Role | May |
|---|---|
| viewer | Read only. Every new account after the first starts here |
| investigator | Record verdicts, keep answers |
| lead | Also approve source documents and new patterns |
| admin | Also manage accounts |

The server checks the role on every save and reads it from the database each time. Sessions last 8 hours;
five wrong passcodes lock a name for 5 minutes.

## Security

| Control | What it does |
|---|---|
| Signed audit log | Every approved change adds a chained, HMAC-signed entry: who, what, when, and the fingerprint of each file written |
| Tamper detection | Every knowledge file is compared with the log. A file changed, deleted or added outside the app is named in a red alert |
| Document scanner | Runs before the LLM reads a pasted document. Instruction-override text is blocked; softer signs are shown to the approver |
| Security events | Blocked documents, tampering, lockouts, refused actions and detector failures, each with severity and action |

Routes: `/api/security/status`, `/audit`, `/events`, `/reseal`. See the Security and access page. One signed log
covers both regions (India's files appear under `india/`).

## Demo script

1. **Queue.** 80,452 claims, 846 alerts, 34 cases in three tiers. Change the investigator count to move the capacity line.
2. **Case P081** (network N01). Show the network, the AuditNext plan and the precedents. Sign in as an
   investigator, record "confirmed" with a reason, preview, approve.
3. **Back in the queue**, P250, P263 and P274 have moved from Review to Fast-track, citing CASE-P081.
4. **Second Brain.** The new case page and the change log. Ask "What have we learned about referral rings?"
5. **Add a source document** as a lead. The LLM proposes a new pattern; approve it.
6. **Security.** Paste a document containing "ignore all previous instructions"; it is blocked. Edit a page
   file by hand and refresh; the Security and access page names it. Sign in as an investigator and try to approve a
   document; it is refused.
7. **Resilience.** Run the pipeline with a simulated detector failure and show the degraded-mode banner.

Reset between demos (both regions): restore the committed Second Brain, which removes demo verdicts, notes,
sources and learned patterns and keeps the seeded investigation history, then restart the API. Delete
`data/app.db` as well for a clean account list and audit log.

```
git restore knowledge && git clean -fd knowledge
```

## Results on the injected scenarios

All 25 injected providers are in the 34-case queue and the 6-provider ring is recovered as one network.
Details are in `data/processed/metrics.json`. These numbers measure recovery of scenarios we injected
ourselves; they are not evidence of performance on real claims.

## India (PM-JAY) region

A US / India switch in the header changes every page; the API takes `region=us|in` on every route
and defaults to `us`, so the US system is unchanged. India uses the synthetic PM-JAY-style dataset in
`data/india/` (75,721 admissions at 300 hospitals; see its README) and follows the India vs US
methodology note: the US polices the procedure-code line, India polices the hospital admission.

| Layer | India version | File |
|---|---|---|
| Claim rules | Overlapping admissions, duplicate packages, claims after death, package mismatch (diagnosis, sex, entitled rate) and the hysterectomy-under-35 audit trigger, ICU-rate drift, stay above package norm, OPD-to-IPD short stays, suspicious identity (new cards, shared mobiles), reused documents, admissions above bed strength, empanelment, camp clusters | `backend/pipeline/rules_in.py`, `reference_in.py` |
| Anomaly | Same Isolation Forest + calibration; features include admissions per bed, ICU share, short stays, new cards, agents, mortality; peers by hospital type | `backend/pipeline/anomaly.py` |
| Network | Same Leiden, referral cycles and BiRank, plus agent links; ring evidence names the agent, villages and card operator | `backend/pipeline/graph.py` |
| Prediction | Same 30/60/90-day gradient boosting with ICU and short-stay drift features | `backend/pipeline/predict.py` |
| Second Brain | India patterns, synthetic policies citing NHA, CAG and HBP sources, SAFU routing, a field-audit checklist, rupee-aware fact checks | `backend/brain/`, `knowledge/india/` |

India data, models (`backend/models/india/`), outputs (`data/india/processed/`), policies, cases and
investigation history (`knowledge/india/`) are kept apart from the US ones. Identifiers are tokens;
no name, Aadhaar or mobile number is written to the wiki.

The India queue separates actionable cases (fast-track and review) from a watch list (weak evidence:
monitored and re-scored, not opened); a precedent can move a hospital from one to the other. On the
injected India scenarios, measured as the API serves the queue:

| | Cases | Precision | Recall |
|---|---|---|---|
| Actionable cases | 27 | 1.00 | 0.96 |
| At capacity (3 investigators) | 15 | 1.00 | 0.54 |
| At capacity (5 investigators) | 25 | 1.00 | 0.89 |
| All candidates, actionable + watch list | 62 | 0.45 | 1.00 |

The one planted hospital on the watch list (P104) has 2 upcoded claims in 23 medical admissions, which
is within the normal range. The 5-hospital ring is recovered as one network and 90% of flagged claims are
injected ones. As with the US, these numbers measure recovery of scenarios the dataset injected itself.

Diagnosis-package mismatch and empanelment checks fire 0 times here because the generator copies each
claim's diagnosis from the package master and draws packages only from each hospital's empanelled
specialties; `backend/tests/test_rules_in.py` covers them with positive and negative cases
(`python -m unittest discover -s backend/tests -t .`). Typical stays per package and the ICU, short-stay
and camp thresholds are prototype assumptions, and 5 of the 45 package rates are estimates; briefs say so
wherever a case relies on them.

## Honest limits

- All data is synthetic.
- AuditNext costs and starting accuracies are assumptions; no comparison experiment has been run.
- The regulatory pages and policies are short summaries written for this prototype.
- The audit log's signing key is stored on the same machine as the data, and the document scanner is
  keyword-based. Both are one layer of defence, not a guarantee.
- No Final medical judgment is made by the AI.

## What production would add

Single sign on in place of local accounts; the signing key in a vault and the audit log in write-once
storage; a managed database in place of CSV files and SQLite; encryption at rest; real record intake per
case; scheduled pipeline runs with alerting; and validation on audited SIU outcomes.
