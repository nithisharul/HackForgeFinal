# Final integration

Branch `feature/india-pmjay-methodology` now holds the team's finished work as one US + India application.
Features were ported selectively from the source branches; no branch was merged wholesale and no other
branch was changed.

## What came from where

| Feature | Source | Notes |
|---|---|---|
| PrecedentGuard: contradiction handling, evidence-compatible network bonus, 730-day half-life, revocation, `guard_eval` experiment | `updated-frontend` a524aa5 | Added here: a per-precedent explanation (accepted / reduced / set aside / revoked), queue rank with and without a precedent, revoked verdicts marked on wiki pages |
| Theme toggle, header sign-in, toasts, redesigned case page, queue / network / Second Brain polish | `updated-frontend` fa38ff5 | Merged three-way with RingShield; the India queue, watch-list divider, overview on region switch, hospital names and ₹ formatting are unchanged |
| Clinical record audit (synthetic EHR, badge-access and lab notes; engine; route; card) | `feature/clinical-audit-rag` up to 06da704 | Rewritten for safety, see below |
| AuditNext verification ranking | `feature/clinical-audit-rag` 0de52bd | Region-aware; real expected information gain; prior from the case's confidence; catalog numbers labelled as assumptions |
| Per-pattern US investigation playbooks ("action recommendation") | `Nithi_Base` c119233 | Returned as structured data and labelled as a fixed template; folded under the AuditNext ranking |
| Investigator sign-in for every write | already on this branch (same change as `Nithi_Base` 9f7607e) | Also guards the new revoke endpoint |
| RingShield, India PM-JAY region, FHIR export, Cloudflare deploy | this branch | Unchanged |

### Clinical audit safety fixes

The source engine fell back to another case's note when a case had none (any impossible-timing case got
CASE-P209's log), defaulted `discrepancy_found` to true when the note or model was missing, filled in a
fixed date, and cited statutes the record did not support. Now:

- a record is read only for the case named by its file, from its region's folder (`data/clinical_notes/us/`);
  case ids are validated and the path cannot leave that folder
- no record means `unavailable`; a record that does not name the case's provider, or whose date has no
  claims for that provider, means `insufficient_evidence`; only deterministic checks can produce
  `discrepancy_found`
- the response keeps document facts (as written), deterministic checks and the model's reading apart; the
  model's reading is labelled unverified, can never change the status, and keeps only quotes found
  verbatim in the record; timeouts, malformed JSON and an offline server are reported as such
- records are treated as untrusted data in the prompt; no statutes or CMS citations are generated
- India always shows `unavailable`: the notes are US records and are not PM-JAY evidence
- read-only: nothing writes to claims, verdicts or the Second Brain

Of the three synthetic notes only `CASE-P209` matches a case (Dr. Hannah Hayes, impossible timing). Its log is
dated 2026-03-14, a day with no P209 claims in the claims data, so the audit reports
`insufficient_evidence`: the record states a conflict, but nothing ties it to a claim in this case.
`CASE-P104` and `CASE-P164` have no US case; they serve as fixtures for the visit-level and bundling checks.
The original datasets were not changed.

## Architecture

```
frontend (React + Vite)  ──/api──▶  FastAPI (backend/app)  ──▶  store: per-region cases, scores, graph
                                           │                       │
                                           │                       ├─ brain/confidence + retrieve  (PrecedentGuard)
                                           │                       ├─ brain/wiki                    (Second Brain, per region)
                                           │                       ├─ brain/clinical_audit          (US records, checks)
                                           │                       ├─ brain/auditnext               (verification ranking)
                                           │                       └─ pipeline/ringshield           (network robustness)
                                           └─ brain/llm: chat / chat_json / status   → Second Brain provider (LLM_*)
                                                         clinical_status / clinical_json → local Ollama (CLINICAL_LLM_*)
Cloudflare Worker (cloudflare/) serves frontend/dist and forwards /api/* to the laptop through a quick tunnel.
```

New API routes: `GET /cases/{id}/clinical-audit`, `GET /cases/{id}/audit-plan`,
`GET /precedents/{id}/influence`, `POST /precedents/{id}/revoke` (signed-in investigator). See `docs/api_contract.md`.
No new Python or npm dependencies.

## Run it

```
pip install -r backend/requirements.txt            # Python 3.11+ (pinned versions match the saved models)
uvicorn backend.app.main:app --reload               # API on http://127.0.0.1:8000
cd frontend && npm install && npm run dev           # dashboard on http://localhost:5173
python -m backend.app.auth add "Investigator Name"  # once, to enable writes; restart the API
```

Local models (optional, never downloaded automatically; settings in `.env`, see `.env.example`):

```
ollama pull gemma3:4b      # Second Brain: LLM_BASE_URL=http://localhost:11434/v1, LLM_MODEL=gemma3:4b
ollama pull llama3.2       # clinical audit: CLINICAL_LLM_MODEL=llama3.2 (default), CLINICAL_LLM_BASE_URL=http://127.0.0.1:11434
ollama serve
```

Without Ollama the Second Brain uses templates and the clinical card shows "AI reading offline" with the
deterministic checks still in place.

Deploy: `cd cloudflare && npm run deploy` (site), then with the API on port 8000 `npm run go-live` (tunnel).

## Demos

- **US**: queue → open **CASE-P081** (network N01), record a verdict, see P250 / P263 / P274 re-ranked.
- **India**: switch to India (the overview returns), queue shows actionable cases, then the watch list; open **CASE-P203** or **CASE-P059**.
- **RingShield**: on any N01 member (US P081, India P059) the robustness panel sits under the network graph.
- **PrecedentGuard**: open a closed case (US **CASE-P263**) or a Second Brain case page (e.g. **INV005**). The
  card lists the open cases the verdict moves, with confidence, tier and rank with and without it. Sign in,
  revoke with a reason; scores and ranks return to the "without" values and affected cases list the
  verdict under "Revoked precedents". Experiment: `python -m backend.brain.guard_eval --region us`.
- **Clinical audit**: US **CASE-P209** shows the badge log, the checks (provider matches, no claims on the
  log's date, presence conflict stated in the record) and the `insufficient_evidence` status; any other case
  shows `unavailable`; India shows `unavailable`.
- **AuditNext**: on US cases the recommended action box ranks the next verification step; the fixed
  playbook is folded underneath.

Reset demo writes: `git restore knowledge && git clean -fd knowledge` (removes all uncommitted wiki changes,
including ones you may want to keep).

## Test results (2026-10-09)

- Backend: `python -m unittest discover -s backend/tests -t .` — 70 tests, all passing (Python 3.13 with the
  pinned requirements). New: PrecedentGuard explanations and revocation through the API (on a throwaway
  copy of the Second Brain), clinical audit (record matching, no borrowing, India, path validation, a fake
  Ollama server for valid, malformed, slow and offline replies), AuditNext.
- Baseline outputs: rule, anomaly, network and prediction signals, risk scores and horizon probabilities
  are identical before and after integration in both regions (34 US and 62 India cases). Confidence moves
  slightly because old seeded precedents now decay; tier counts are unchanged
  (US 13 / 9 / 11, India 16 / 10 / 35).
- `guard_eval` (20 trials × 3 wrong verdicts), guard off → on: US legit escalations 0.05 → 0, contradictions
  flagged 0/50 → 50/50, fraud demotions 0 → 1.5 per trial, preserved promotions 4/4; India legit
  escalations 0.90 → 0.80, contradictions flagged 0/103 → 103/103, fraud demotions 0 → 0.
- Frontend: `npm run build` passes. Headless Chrome against a local build: no horizontal scroll on the India
  queue at 1280, 1440 and 1920 px or on mobile (390 px); overview returns on each region switch; one FHIR
  button, one header sign-in, one theme toggle; theme persists across reloads; sign-in, revoke, verdict and
  sign-out each raise one toast; revocation restored every affected score and rank; the verdict was recorded
  under the signed-in name; unauthenticated revoke, unauthenticated wiki note and a forged-token verdict
  returned 401; no JS exceptions.

## Limitations

- The public API is the laptop behind a Cloudflare quick tunnel: not persistent hosting. On 2026-10-09 this
  network reset connections to `api.trycloudflare.com`, so no tunnel could connect and the deployed site
  showed "API offline"; run `npm run go-live` again from a network that allows Cloudflare tunnels.
- Local Llama 3.2 / Gemma inference was not run: Ollama is not installed on the integration machine. The
  model paths were tested against a stand-in server only.
- Contradiction handling sets both verdicts aside until an investigator revokes the wrong one, which in the
  US experiment demotes about 1.5 true-fraud cases per trial; revocation is the remedy.
- PrecedentGuard only sees the top 3 retrieved precedents, so a contradicting verdict outside them is not
  detected.
- AuditNext's costs and accuracies are illustrative assumptions, and its prior is a routing score, not a
  calibrated probability; treat the ranking as an aid.
- The US playbook references are pointers to verify, not legal advice; the clinical notes are synthetic.
- No Indian clinical records exist yet, so the India clinical audit is always unavailable.
