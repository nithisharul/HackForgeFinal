---
type: pattern
id: duplicate_package
title: Duplicate package claims
policy: POL-IN-010
---
# Duplicate package claims

## Definition
The same inpatient package is claimed again for the same beneficiary at the same hospital within days.

## Detection signals
- Rule IN2: same inpatient package, beneficiary and hospital within 7 days

## Policy basis
- POL-IN-010 One package per episode of care (`knowledge/india/sources/policies/POL-IN-010.md`)
- Public basis: NHA anti-fraud triggers on repeat claims

## Known innocent explanations
- A genuine readmission for a complication, documented with new investigations
- A resubmission after a rejection where the first claim was never paid
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
0 closed cases: 0 confirmed, 0 cleared, 0 inconclusive.
<!-- /auto -->

## Cases
<!-- auto:cases -->
<!-- /auto -->
