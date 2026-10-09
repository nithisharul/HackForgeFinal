---
type: pattern
id: bed_overrun
title: Capacity and empanelment violations
policy: POL-IN-002
---
# Capacity and empanelment violations

## Definition
A hospital admits more patients than its sanctioned beds can hold, or bills packages outside the specialties and dates it is empanelled for.

## Detection signals
- Rule IN9a: admissions on one day above bed strength
- Rule IN9b: package specialty not empanelled, or a claim before empanelment
- Anomaly model: busiest day's admissions per bed far above hospital-type peers

## Policy basis
- POL-IN-002 Bed strength and scope of empanelment (`knowledge/india/sources/policies/POL-IN-002.md`)
- Public basis: NHA Field Investigation and Medical Audit Manual (2020): fewer patients on site than shown in TMS; PM-JAY hospital empanelment guidelines

## Known innocent explanations
- A government medical college running above sanctioned beds, recorded in its inpatient register
- Day-care volume such as cataract or dialysis sessions counted against inpatient beds
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
3 closed cases: 1 confirmed, 1 cleared, 1 inconclusive.
<!-- /auto -->

## Cases
<!-- auto:cases -->
- [[INV031]] | [[P204]] (Community Health Centre) | **cleared** | closed 2025-04-20
- [[INV003]] | [[P198]] (Nursing Home) | **confirmed** | closed 2025-08-05
- [[INV035]] | [[P075]] (District Hospital) | **inconclusive** | closed 2025-09-10
<!-- /auto -->
