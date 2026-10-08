# API contract

Base URL in development: `http://127.0.0.1:8000/api` (the Vite dev server proxies `/api` to it).
Interactive docs: `http://127.0.0.1:8000/docs`.

Every route takes `region=us|in` (default `us`). Each region reads and writes only its own data,
models and Second Brain; a case or page from one region is a 404 in the other.

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/login` | `{investigator, passcode}` -> `{token, investigator, expires}` (8-hour session) |
| GET | `/auth/session` | Who the bearer token belongs to; 401 if missing, forged or expired |
| GET | `/auth/status` | `{writes_enabled}`: whether an investigator is configured |
| GET | `/queue?horizon=90&investigators=3` | Ranked SIU queue plus the alert funnel summary (horizon is 30, 60 or 90) |
| GET | `/metrics` | Evaluation against injected scenarios and model cross-validation scores |
| GET | `/cases/{case_id}?horizon=90` | Full case: scores, evidence, sample claims, timeline, network, brief |
| GET | `/cases/{case_id}/brief` | The investigation brief only |
| POST | `/cases/{case_id}/verdict/preview` | Show which Second Brain pages would change; writes nothing |
| POST | `/cases/{case_id}/verdict` | Save the investigator's verdict to the Second Brain |
| GET | `/cases/{case_id}/clinical-audit?llm=true` | Read-only audit of the case's own synthetic clinical record: document facts, deterministic checks, status (`discrepancy_found`, `no_discrepancy`, `insufficient_evidence`, `unavailable`) and, if a local model is running, its unverified reading. India: always `unavailable` until Indian records exist |
| GET | `/cases/{case_id}/audit-plan` | AuditNext: verification steps ranked by expected information gain (bits) per hour; prior = the case's confidence score; catalog costs and accuracies are illustrative assumptions. India: `unavailable` |
| GET | `/precedents/{case_id}/influence` | PrecedentGuard: open cases this closed verdict moves, with score, tier and rank with and without it |
| POST | `/precedents/{case_id}/revoke` | `{reason}` -> withdraw a verdict as precedent; the page and log keep the record |
| GET | `/graph/{provider_id}` | Nodes and links around one provider |
| GET | `/graph/{provider_id}/ringshield` | Read-only robustness analysis for the provider's detected network |
| GET | `/wiki` | List of Second Brain pages by type |
| GET | `/wiki/page/{name}` | One page: header fields, markdown body, backlinks |
| GET | `/wiki/lint` | Second Brain health check |
| POST | `/wiki/ask` | `{question}` -> cited answer, pages read |
| POST | `/wiki/notes` | `{question, answer, approved_by}` -> keep an answer as a page |
| POST | `/wiki/sources/preview` | `{title, text}` -> proposed summary, pattern notes and page changes; writes nothing |
| POST | `/wiki/sources` | `{title, text, approved_by, proposal}` -> save the document and update pages |

The four writes (`POST /cases/{id}/verdict`, `/precedents/{id}/revoke`, `/wiki/notes`, `/wiki/sources`) need
`Authorization: Bearer <token>` and record the signed-in investigator; without it they answer 401
(503 when no investigator is configured). Previews, `/wiki/ask` and every GET stay open.

## Verdict body

```json
{ "verdict": "confirmed | cleared | inconclusive",
  "reasoning": "at least 10 characters; becomes precedent",
  "investigator": "name",
  "pattern": "optional: correct the proposed pattern",
  "lesson": "optional: the lesson returned by the preview, sent back so the approved text is saved" }
```

## Queue row

`case_id, provider_id, provider_name, specialty, city, pattern, network, potential_dollars, member_impact,
severity, evidence_strength, confidence, tier (high|medium|low), route, risk_score, priority, horizon_days,
p_horizon, expected_dollars, status (open|confirmed|cleared|inconclusive), rank, in_capacity`

## Scoring

- `risk_score` = 0.35 rules + 0.20 anomaly + 0.20 network + 0.05 BiRank + 0.20 predicted risk at the chosen horizon
- `confidence` = evidence strength + precedent adjustment; high >= 0.70, medium >= 0.35, otherwise low
- PrecedentGuard: contradicting confirmed/cleared verdicts (same pattern, same provider or network) are set aside;
  the +0.25 network bonus needs shared evidence; a precedent's pull halves every 730 days; revoked verdicts are
  never retrieved. `confidence.precedent_effects` explains each one as accepted, reduced or rejected, and
  `brief.revoked_precedents` lists matching revoked verdicts.
- `priority` = 0.30 risk + 0.20 dollars + 0.10 members + 0.15 severity + 0.25 confidence
- `in_capacity` = open, not low tier, and within investigators x 5 cases
