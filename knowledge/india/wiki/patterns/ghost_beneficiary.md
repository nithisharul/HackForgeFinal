---
type: pattern
id: ghost_beneficiary
title: Ghost or impersonated beneficiaries
policy: POL-IN-004
---
# Ghost or impersonated beneficiaries

## Definition
Claims for beneficiaries whose identity is doubtful: cards created days before a claim, or mobile numbers shared far beyond one household.

## Detection signals
- Rule IN7: beneficiary card created 7 days or less before admission
- Rule IN7: mobile number registered to more beneficiaries than a household
- Anomaly model: share of new cards far above hospital-type peers

## Policy basis
- POL-IN-004 Beneficiary identity verification (`knowledge/india/sources/policies/POL-IN-004.md`)
- Public basis: CAG Report 11 of 2023 (lakhs of beneficiaries on one placeholder mobile number); NHA Anti-Fraud Framework Practitioners' Guidebook (2020)

## Known innocent explanations
- A newly eligible family enrolled at the hospital help desk on the day of an emergency
- A placeholder mobile number typed at enrolment, which is a data-quality issue rather than a flag on its own
<!-- auto:learned -->
<!-- /auto -->

## Lessons from closed cases
<!-- auto:lessons -->
<!-- /auto -->

## Notes from sources
<!-- auto:notes -->
<!-- /auto -->

## Precedent summary
<!-- auto:summary -->
4 closed cases: 1 confirmed, 3 cleared, 0 inconclusive.
<!-- /auto -->

## Cases
<!-- auto:cases -->
- [[INV030]] | [[P122]] (District Hospital) | **cleared** | closed 2025-04-17
- [[INV029]] | [[P153]] (Heart Institute) | **cleared** | closed 2025-04-27
- [[INV004]] | [[P298]] (Nursing Home) | **confirmed** | closed 2025-05-06
- [[INV016]] | [[P126]] (Nursing Home) | **cleared** | closed 2025-07-18
<!-- /auto -->
