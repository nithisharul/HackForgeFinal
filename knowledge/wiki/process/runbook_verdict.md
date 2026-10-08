---
type: process
id: runbook_verdict
title: Runbook: recording a verdict
written_by: code
---
# Runbook: recording a verdict

> Reference page written by code from the pipeline. Rebuilt on every change; do not edit by hand.

## Purpose
How a decision is recorded so that it becomes precedent.

## Steps
- Open the case and choose a verdict: `confirmed`, `cleared` or `inconclusive`.
- Write the reason in one or two sentences. State what the records showed, not what the model scored.
- Enter your name and preview. The preview lists every page that will change and the lesson to be saved.
- Approve. A case page is created; the pattern, provider and network pages, the index and the log are updated.

## What each verdict does to later cases
- `confirmed`: similar open cases gain confidence; cases in the same network gain the most.
- `cleared`: similar open cases lose a little confidence; the same provider and pattern loses the most, and the reason is added to the pattern's known innocent explanations.
- `inconclusive`: saved as history; no change to confidence.
- The exact amounts are in [[system_scoring]].

## Corrections
- A wrong verdict is corrected by a named person and logged; pages are never edited silently. See [[runbook_knowledge]].
