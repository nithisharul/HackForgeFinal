---
type: system
id: system_limits
title: System: known limits
written_by: code
---
# System: known limits

> Reference page written by code from the pipeline. Rebuilt on every change; do not edit by hand.

## Data
- All data is synthetic. Results show recovery of scenarios we injected, not performance on real claims.
- 25 of 25 injected providers are in the queue; 1 legitimate outlier(s) are also in it.
- Prices and the visit-level mix are approximations.
- Claims carry no modifiers. The only provider record is one synthetic sample used to show record review.

## Rules and tables
- The bundling table is a subset of the CMS file plus pairs derived from code definitions; see [[R3]].
- Three equipment unit limits are illustrative; see [[R4]].

## Models
- Calibration uses injected labels in place of audited outcomes.
- The prediction target is future rule flags.

## Second Brain
- Policies in `knowledge/sources/policies/` and the regulatory pages are short summaries written for this prototype, not legal advice.
- Patterns learned from documents have no detection rule.
- There is no login; the approver's name is typed, not verified.
- No medical-necessity judgment is made.
- Privacy basis: [[REG-HIPAA]]. Overview: [[system_architecture]].
