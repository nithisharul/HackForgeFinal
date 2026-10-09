---
type: pattern
id: excessive_utilization
title: Excessive utilisation
policy: POL-IN-011
---
# Excessive utilisation

## Definition
Admissions, stay lengths or amounts far above hospitals of the same type without a documented reason.

## Detection signals
- Rule IN6a: stay more than twice the typical stay assumed for the package plus 3 days (an assumption, not a published PM-JAY norm)
- Anomaly model: Isolation Forest score with drivers such as admissions per beneficiary or total paid

## Policy basis
- POL-IN-011 Utilisation and length-of-stay review (`knowledge/india/sources/policies/POL-IN-011.md`)
- Public basis: NHA Field Investigation and Medical Audit Manual (2020): stay not matching the package; typical stays here are assumed, not published

## Known innocent explanations
- A high-volume dialysis or eye centre with normal use per beneficiary
- A complicated case with a documented reason for a long stay
<!-- auto:learned -->
<!-- /auto -->

## Detected by
- [[R4]] | R4 Unit limit (MUE)
- What to request from the provider: [[runbook_evidence]]

## Regulatory background
- [[REG-PIM]] | Medicare Program Integrity Manual
- [[REG-NCCI]] | CMS National Correct Coding Initiative (NCCI)

## Lessons from closed cases
<!-- auto:lessons -->
<!-- /auto -->

## Notes from sources
<!-- auto:notes -->
<!-- /auto -->

## Precedent summary
<!-- auto:summary -->
8 closed cases: 1 confirmed, 7 cleared, 0 inconclusive.
<!-- /auto -->

## Cases
<!-- auto:cases -->
- [[INV009]] | [[P259]] (Government Medical College) | **cleared** | closed 2025-04-13
- [[INV010]] | [[P184]] (Government Medical College) | **cleared** | closed 2025-04-22
- [[INV037]] | [[P136]] (Community Health Centre) | **confirmed** | closed 2025-04-22
- [[INV026]] | [[P055]] (Eye Hospital) | **cleared** | closed 2025-06-04
- [[INV013]] | [[P247]] (Dialysis Centre) | **cleared** | closed 2025-06-22
- [[INV021]] | [[P154]] (Nursing Home) | **cleared** | closed 2025-06-23
- [[INV011]] | [[P170]] (Eye Hospital) | **cleared** | closed 2025-07-06
- [[INV012]] | [[P193]] (Eye Hospital) | **cleared** | closed 2025-10-07
<!-- /auto -->
