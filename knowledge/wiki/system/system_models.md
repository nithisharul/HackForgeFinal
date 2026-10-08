---
type: system
id: system_models
title: System: models
written_by: code
---
# System: models

> Reference page written by code from the pipeline. Rebuilt on every change; do not edit by hand.

## Anomaly model
- Isolation Forest, 300 trees, on provider features expressed relative to same-specialty peers.
- An isotonic calibrator turns the raw score into a probability.
- AUC 0.79 against the injected scenarios.

## Network analysis
- Providers are linked when they share far more members than chance would give (lift of 3 or more and at least 15 shared members).
- Leiden community detection groups linked providers; groups of 3 or more become a network page.
- Referral loops are found from [[data_referrals]]; shared ownership from [[data_ownership]].
- BiRank spreads risk from flagged providers through shared members.

## Prediction model
- Three gradient boosting classifiers, one each for 30, 60 and 90 days.
- Target: the provider receives 3 or more rule flags in the horizon. It predicts repeat detection, not proven fraud.
- 30d: cross-validated AUC 0.89 on 76 positive examples.
- 60d: cross-validated AUC 0.88 on 103 positive examples.
- 90d: cross-validated AUC 0.88 on 119 positive examples.

## What the LLM does and does not do
- It writes: the lesson from a verdict, document summaries, pattern notes, new-pattern proposals, answers to questions, and the brief summary.
- It does not score, rank or decide. Any LLM text containing an ID or dollar figure not in its input is discarded.
- Saved models are in `backend/models/`. How scores combine: [[system_scoring]].
