---
type: pattern
id: overlapping_admission
title: Overlapping admissions
policy: POL-IN-008
---
# Overlapping admissions

## Definition
A beneficiary is claimed as an inpatient at two hospitals at the same time.

## Detection signals
- Rule IN1: admitted while an inpatient at another hospital, with an overlap of 24 hours or more

## Policy basis
- POL-IN-008 One beneficiary, one admission at a time (`knowledge/india/sources/policies/POL-IN-008.md`)
- Public basis: CAG Report 11 of 2023 (claims with overlapping admissions)

## Known innocent explanations
- A transfer where the first hospital recorded the discharge late
- A data-entry error in the discharge date, corrected at audit
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
2 closed cases: 0 confirmed, 2 cleared, 0 inconclusive.
<!-- /auto -->

## Cases
<!-- auto:cases -->
- [[INV017]] | [[P260]] (Orthopaedic Hospital) | **cleared** | closed 2025-04-27
- [[INV024]] | [[P005]] (Multispecialty Hospital) | **cleared** | closed 2025-06-05
<!-- /auto -->
