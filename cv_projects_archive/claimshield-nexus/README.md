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
```

If the saved models fail to load, your scikit-learn version differs from the pinned one; run with `--retrain`.

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

Reset the demo by deleting `knowledge/wiki/cases/CASE-*.md`, `knowledge/wiki/sources/*`, `knowledge/wiki/notes/*` and `knowledge/sources/documents/*`, then running `python -m backend.pipeline.run_all`.

## Results on the injected scenarios

See `data/processed/metrics.json`. All 25 injected FWA providers are in the 34-case queue, and the
6-provider ring is recovered exactly as one network. These numbers measure recovery of scenarios we
injected ourselves; they are not evidence of performance on real claims.

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
