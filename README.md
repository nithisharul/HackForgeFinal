# ClaimShield Nexus: the SIU's Second Brain

Finds suspicious claims and coordinated provider networks in synthetic payer data, predicts
30/60/90-day repeat risk, ranks cases for the Special Investigations Unit, and writes an
evidence-backed brief. Every investigator verdict is saved to a linked markdown wiki and
becomes precedent for the next case.

All data is synthetic. The system produces leads for human review; it never decides fraud.

## Run it

Two terminals, both starting in this folder. Python 3.11+ and Node 18+.

```
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The data, model outputs, trained models and wiki are already in the
package, so nothing needs to be generated or trained first.

To rebuild from scratch:

```
python data/generate_data.py                  # regenerate the synthetic CSVs
python -m backend.pipeline.run_all            # re-score with the saved models
python -m backend.pipeline.run_all --retrain  # retrain and overwrite backend/models/
python -m backend.pipeline.run_all --region in [--retrain]   # the India region (see below)
```

If the saved models fail to load, your scikit-learn version differs from the pinned one; run with `--retrain`.

## Sign-in for writes

Reading, previews and questions are open. Saving a verdict, a kept answer or a source document needs a
signed-in investigator; the server checks every write, so requests sent straight to the API or tunnel
are refused too, and the signed-in name is what gets recorded. Investigators live only in the
git-ignored `.env` (a signing key and PBKDF2 passcode hashes), never in the frontend or Cloudflare:

```
python -m backend.app.auth add "Investigator Name"   # prompts for a passcode (12+ characters); restart the API
```

With no investigator configured every write is refused. Sessions last 8 hours; 5 wrong passcodes lock
that name for 5 minutes.

## Deploy (Cloudflare, free plan)

`cloudflare/` holds a Worker that serves the React build and forwards `/api/*` to the API on the host
machine through a Cloudflare quick tunnel. `cd cloudflare && npm install && npm run deploy` publishes the
site; with the API running on port 8000, `npm run go-live` opens the tunnel (keep it running). Some
campus and office networks block Cloudflare tunnels. `cloudflare/Dockerfile` builds the API image for
Cloudflare Containers (Workers Paid plan) or any Docker host.

## Connect a free LLM (optional, recommended for the demo)

Copy `.env.example` to `.env`, fill in one option, and restart the API. Any OpenAI-compatible
provider works: Groq or Google Gemini on their free tiers, or Ollama running locally with no key.
The Second Brain tab shows whether an LLM is connected. Without one, everything still runs from
templates and keyword lookup.

## How it works

| Step | Method | File |
|---|---|---|
| Claim rules | Duplicates, impossible travel, bundling edit pairs, unit limits, visit-level drift | `backend/pipeline/rules.py`, `reference.py` |
| Provider anomaly | Isolation Forest on peer-normalised features, isotonic calibration to a probability | `backend/pipeline/anomaly.py` |
| Network | Provider-member bipartite graph, Leiden communities, referral cycles, BiRank | `backend/pipeline/graph.py` |
| Prediction | Gradient boosting on rolling 90-day windows with velocity features, one model per horizon | `backend/pipeline/predict.py` |
| Second Brain | Linked markdown wiki: ingest, query, lint; any OpenAI-compatible LLM | `backend/brain/wiki.py`, `retrieve.py`, `llm.py` |
| Confidence | Evidence strength plus precedent adjustment, three routing tiers | `backend/brain/confidence.py` |
| Brief | Structured evidence; every ID, code and dollar figure checked against the data | `backend/brain/brief.py` |

## The Second Brain

`knowledge/` follows the LLM-wiki pattern: raw `sources/` that are never edited, a `wiki/` of linked
pages (`patterns/`, `providers/`, `cases/`, `index.md`, `log.md`), and `SCHEMA.md` with the conventions.

- **Ingest a verdict:** an investigator records a verdict, previews the page changes, and approves. The LLM
  writes the reusable lesson; a case page is created and the pattern, provider and network pages, the index
  and the log are updated.
- **Ingest a document:** paste a policy, bulletin or audit memo. The LLM reads it, writes a summary page and
  proposes one-line notes for each pattern it affects. Nothing is saved until a named person approves.
- **Query:** ask a question. The LLM reads the index, chooses pages, reads them and answers with
  `[[citations]]`. Citations to pages that do not exist are removed. A good answer can be kept as a page.
- **Query inside a case:** each brief reads the index, the pattern page, the most similar closed cases,
  the network page and the provider page, and cites them.
- **Lint:** finds broken links, orphan pages and patterns where most cases were cleared.

What the LLM writes: case lessons, document summaries and pattern notes, answers, and the brief summary.
What stays deterministic: page layout, links, the index, the log, and every number. LLM text that contains
an ID or dollar figure not found in its input is discarded.

## Demo script (2 minutes)

1. Queue: 80,452 claims become 846 raw alerts, then 34 cases in three tiers. Change investigators to move the capacity line.
2. Open **P081** (network N01). Confidence is medium. Show the network graph, the closed referral loop and the cited precedents.
3. Record "confirmed" with a reason, preview the Second Brain changes, approve.
4. Back in the queue, P250, P263 and P274 have moved from Review to Fast-track, citing CASE-P081 as precedent.
5. Second Brain tab: the new case page, the updated pattern and network pages, and the change log.
6. Ask "What have we learned about referral rings?" and show the cited answer. Then add a source document and approve the proposed updates.

Reset the demo for both regions by restoring the committed Second Brain, which removes demo verdicts,
notes, sources and learned patterns and keeps the seeded investigation history, then restart the API:

```
git restore knowledge && git clean -fd knowledge
```

## Results on the injected scenarios

See `data/processed/metrics.json`. All 25 injected FWA providers are in the 34-case queue, and the
6-provider ring is recovered exactly as one network. These numbers measure recovery of scenarios we
injected ourselves; they are not evidence of performance on real claims.

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

- Fee amounts and the visit-level mix are approximations, not looked-up Medicare values.
- The bundling rule uses 500 official CMS NCCI pairs (Practitioner PTP v32.3, file 1 only) plus 137 pairs
  derived from the codes' own definitions. The derived pairs, which include the lab-panel pair that fires
  in the demo, are not from the CMS table and their modifier indicators are unknown.
- Unit limits are the official CMS practitioner MUE values effective 2026-10-01, except three equipment
  codes that keep illustrative limits. Put the complete CMS files in `data/reference/` to replace both tables.
- Policies in `knowledge/sources/policies/` were written for this prototype, not copied from a payer.
- Isotonic calibration uses the injected labels as a stand-in for audited SIU outcomes.
- The prediction model's target is future rule flags, so it predicts repeat detection, not proven fraud.
- The LLM paths were tested against a local stand-in server, not against a live provider.
- No clinical records are used and no medical-necessity judgment is made.
