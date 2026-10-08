---
type: system
id: system_scoring
title: System: scoring and routing
written_by: code
---
# System: scoring and routing

> Reference page written by code from the pipeline. Rebuilt on every change; do not edit by hand.

## Evidence strength
- 0.5 x rule score + 0.2 x anomaly (capped) + 0.4 x network score, plus 0.15 when at least two of the three methods agree. Capped at 1.

## Precedent adjustment
- Confirmed precedent: +0.25 if in the same network, otherwise +0.10 x similarity.
- Cleared precedent: -0.30 if same provider and pattern, otherwise -0.04 x similarity.
- Total adjustment is limited to between -0.35 and +0.30. Up to three most similar closed cases are used.

## Confidence and tier
- Confidence = evidence strength + precedent adjustment.
- 0.70 or above: fast-track. 0.35 or above: review. Below that: not enough evidence. What to do in each: [[runbook_triage]].

## Risk and priority
- Risk = 0.35 x rules + 0.20 x anomaly + 0.20 x network + 0.05 x BiRank + 0.20 x predicted repeat risk.
- Priority = 0.30 x risk + 0.20 x dollars + 0.10 x members affected + 0.15 x severity + 0.25 x confidence.
- Implemented in `backend/brain/confidence.py` and `backend/app/store.py`.
- Models behind the inputs: [[system_models]].
