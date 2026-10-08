---
type: pattern
id: package_upcoding
title: Package upcoding and mismatch
policy: POL-IN-007
---
# Package upcoding and mismatch

## Definition
A higher-paying package, ward or rate is claimed than the diagnosis, patient or hospital supports: ICU rates for general-ward care, a package that does not fit the diagnosis or sex, or incentives the hospital is not entitled to.

## Detection signals
- Rule IN5: ICU or ventilator share of medical admissions far above all hospitals in a month or over the whole period (prototype thresholds)
- Rule IN4a: diagnosis or sex the package does not fit, or an amount above the hospital's entitled rate
- Anomaly model: ICU share far above hospital-type peers

## Policy basis
- POL-IN-007 Package, ward and rate selection (`knowledge/india/sources/policies/POL-IN-007.md`)
- Public basis: NHA Anti-Fraud Framework Practitioners' Guidebook (2020) on upcoding penalties; HBP 2.0 and HBP 2.2 package, ward and incentive rates (5 of the 45 package rates used here are estimates, not verified HBP rates)

## Known innocent explanations
- A hospital with a genuine critical-care unit taking referred sick patients, supported by ICU registers
- A new NABH accreditation not yet updated in the hospital registry
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
3 closed cases: 0 confirmed, 0 cleared, 3 inconclusive.
<!-- /auto -->

## Cases
<!-- auto:cases -->
- [[INV032]] | [[P223]] (Community Health Centre) | **inconclusive** | closed 2025-02-12
- [[INV008]] | [[P292]] (Multispecialty Hospital) | **inconclusive** | closed 2025-06-20
- [[INV034]] | [[P095]] (Community Health Centre) | **inconclusive** | closed 2025-06-24
<!-- /auto -->
