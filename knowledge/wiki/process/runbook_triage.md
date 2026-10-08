---
type: process
id: runbook_triage
title: Runbook: triage by confidence tier
written_by: code
---
# Runbook: triage by confidence tier

> Reference page written by code from the pipeline. Rebuilt on every change; do not edit by hand.

## Purpose
What an investigator does with a case, depending on its confidence tier.

## The three tiers
- **Fast-track** (confidence 0.70 or above). Fast-track to SIU with audit trail. Owner: SIU lead. Open the case now, request records (see [[runbook_evidence]]), and record a verdict when the review ends.
- **Review** (confidence 0.35 to 0.70). Assign to an investigator for review. Owner: SIU investigator. Read the brief and the cited precedents first; check each innocent explanation on the pattern page before requesting records.
- **Not enough evidence** (below 0.35). Not enough evidence: monitor, do not open a case. Owner: Program integrity analyst. No case is opened. The provider stays in monitoring and is re-scored on the next run.

## Order of work
- Work the queue from the top; it is ordered by priority, defined in [[system_scoring]].
- The capacity line shows how many cases the team can take: 5 open cases per investigator.
- A case in a network is reviewed with the network page open; a verdict on one member changes the others.

## Rules that always apply
- The system proposes; a named person decides.
- Never tell a provider they were flagged by a model; requests cite the claims and the policy.
- When the evidence is thin, record `inconclusive`, not a guess.
- Next step: [[runbook_verdict]].
