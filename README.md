# ClaimShield Nexus: the SIU's Second Brain

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

Open http://localhost:5173, go to the Second Brain tab and create an account in the Access panel. The first
account on a server becomes the admin.

The generated data, pipeline outputs and trained models are in the repository, so nothing has to be
generated or trained first. To rebuild:

```
python data/generate_data.py                  # regenerate the synthetic CSVs
python -m backend.pipeline.run_all            # re-score with the saved models and rebuild the Second Brain pages
python -m backend.pipeline.run_all --retrain  # retrain and overwrite backend/models/
```

Restart the API after a pipeline run. If saved models fail to load, your scikit-learn version differs from
the pinned one; run with `--retrain`.

### Local LLM (optional)

Create `.env` in this folder. The default setup is a local model through Ollama, so no data leaves the machine:

```
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=gemma3:4b
```

Any OpenAI-compatible endpoint works. Without an LLM everything still runs, from templates and keyword lookup.

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

Routes: `/api/security/status`, `/audit`, `/events`, `/reseal`. See the Security panel in the Second Brain tab.

## Demo script

1. **Queue.** 80,452 claims, 846 alerts, 34 cases in three tiers. Change the investigator count to move the capacity line.
2. **Case P081** (network N01). Show the network, the AuditNext plan and the precedents. Sign in as an
   investigator, record "confirmed" with a reason, preview, approve.
3. **Back in the queue**, P250, P263 and P274 have moved from Review to Fast-track, citing CASE-P081.
4. **Second Brain.** The new case page and the change log. Ask "What have we learned about referral rings?"
5. **Add a source document** as a lead. The LLM proposes a new pattern; approve it.
6. **Security.** Paste a document containing "ignore all previous instructions"; it is blocked. Edit a page
   file by hand and refresh; the Security panel names it. Sign in as an investigator and try to approve a
   document; it is refused.
7. **Resilience.** Run the pipeline with a simulated detector failure and show the degraded-mode banner.

Reset between demos: delete `knowledge/wiki/cases/CASE-*.md`, the files in `knowledge/wiki/sources`,
`knowledge/wiki/notes` and `knowledge/sources/documents`, `knowledge/learned_patterns.json`,
`data/processed/recommendations.json` and, for a clean account list, `data/app.db`. Then run
`python -m backend.pipeline.run_all` and restart the API.

## Results on the injected scenarios

All 25 injected providers are in the 34-case queue and the 6-provider ring is recovered as one network.
Details are in `data/processed/metrics.json`. These numbers measure recovery of scenarios we injected
ourselves; they are not evidence of performance on real claims.

## Limits

- All data is synthetic. Prices and the visit-level mix are approximations.
- The bundling table is 500 official CMS NCCI pairs (Practitioner PTP v32.3, file 1) plus 137 pairs derived
  from code definitions; the derived pairs include the lab-panel pair that fires in the demo. Unit limits are
  official CMS practitioner MUE values effective 2026-10-01, except three illustrative equipment limits.
- Calibration uses injected labels in place of audited outcomes. The prediction target is future rule flags,
  not proven fraud.
- Patterns learned from documents have no detection rule yet.
- AuditNext costs and starting accuracies are assumptions; no comparison experiment has been run.
- The regulatory pages and policies are short summaries written for this prototype, not legal advice.
- The audit log's signing key is stored on the same machine as the data, and the document scanner is
  keyword-based. Both are one layer of defence, not a guarantee.
- No medical-necessity judgment is made.

## What production would add

Single sign-on in place of local accounts; the signing key in a vault and the audit log in write-once
storage; a managed database in place of CSV files and SQLite; encryption at rest; real record intake per
case; scheduled pipeline runs with alerting; and validation on audited SIU outcomes.