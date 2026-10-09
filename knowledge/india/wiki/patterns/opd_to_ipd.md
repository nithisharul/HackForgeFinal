---
type: pattern
id: opd_to_ipd
title: OPD-to-IPD conversion
policy: POL-IN-003
---
# OPD-to-IPD conversion

## Definition
Conditions usually treated as outpatients (fever, gastroenteritis, urinary infection) are admitted for a day or less so that an inpatient package can be claimed.

## Detection signals
- Rule IN6b: 0-1 day stays are half or more of a hospital's fever, gastroenteritis and UTI admissions in a month (a prototype threshold; PM-JAY publishes none)
- Anomaly model: share of 0-1 day medical stays far above hospital-type peers
- Several members of one family admitted on the same day

## Policy basis
- POL-IN-003 Admission criteria for conditions treatable as outpatients (`knowledge/india/sources/policies/POL-IN-003.md`)
- Public basis: NHA anti-fraud triggers (OPD-to-IPD conversion is an official trigger; no threshold is published)

## Known innocent explanations
- Severe dehydration or high fever needing an overnight stay, recorded in the vitals chart
- An outbreak such as dengue driving genuine short admissions in one area
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
6 closed cases: 2 confirmed, 2 cleared, 2 inconclusive.
<!-- /auto -->

## Cases
<!-- auto:cases -->
- [[INV025]] | [[P080]] (Nursing Home) | **cleared** | closed 2025-03-12
- [[INV002]] | [[P024]] (Nursing Home) | **confirmed** | closed 2025-04-10
- [[INV018]] | [[P146]] (Nursing Home) | **cleared** | closed 2025-05-01
- [[INV006]] | [[P156]] (Nursing Home) | **inconclusive** | closed 2025-06-04
- [[INV033]] | [[P016]] (Community Health Centre) | **inconclusive** | closed 2025-06-19
- [[INV039]] | [[P269]] (Community Health Centre) | **confirmed** | closed 2025-11-16
<!-- /auto -->
