---
type: pattern
id: duplicate_document
title: Reused documents
policy: POL-IN-006
---
# Reused documents

## Definition
The same document, image or report is attached to claims for different beneficiaries.

## Detection signals
- Rule IN8: the same document hash on claims for different beneficiaries

## Policy basis
- POL-IN-006 Uniqueness of clinical documents and images (`knowledge/india/sources/policies/POL-IN-006.md`)
- Public basis: NHA anti-fraud triggers (the same image or document reused across claims)

## Known innocent explanations
- A blank consent form or template scanned identically for several patients
- A family document such as a ration card legitimately attached for two members
<!-- auto:learned -->
<!-- /auto -->

## Detected by
- No claim rule. Found by the models; see [[system_models]].
- What to request from the provider: [[runbook_evidence]]

## Lessons from closed cases
<!-- auto:lessons -->
<!-- /auto -->

## Notes from sources
<!-- auto:notes -->
<!-- /auto -->

## Precedent summary
<!-- auto:summary -->
3 closed cases: 2 confirmed, 1 cleared, 0 inconclusive.
<!-- /auto -->

## Cases
<!-- auto:cases -->
- [[INV014]] | [[P228]] (Government Medical College) | **cleared** | closed 2025-06-26
- [[INV038]] | [[P103]] (Community Health Centre) | **confirmed** | closed 2025-08-17
- [[INV040]] | [[P232]] (Nursing Home) | **confirmed** | closed 2025-08-17
<!-- /auto -->
