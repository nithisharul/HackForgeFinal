---
type: pattern
id: impossible_timing
title: Impossible timing or travel
policy: POL-003
---
# Impossible timing or travel

## Definition
One rendering provider bills services at locations too far apart to reach in the time between them, suggesting services not rendered as billed.

## Detection signals
- Rule R2: same provider at two facilities 100+ km apart within 60 minutes
- Anomaly model: more billing facilities than specialty peers

## Policy basis
- POL-003 Place and time of service integrity (`knowledge/sources/policies/POL-003.md`)
- Public basis: CMS place-of-service code set; CMS telehealth billing guidance

## Known innocent explanations
- Telehealth visits billed with the wrong place of service
- A group billing identifier used by more than one clinician
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
10 closed cases: 2 confirmed, 5 cleared, 3 inconclusive.
<!-- /auto -->

## Cases
<!-- auto:cases -->
- [[INV016]] | [[P194]] (Ambulance) | **cleared** | closed 2025-03-24
- [[INV006]] | [[P001]] (Family Medicine) | **inconclusive** | closed 2025-03-30
- [[INV002]] | [[P219]] (Internal Medicine) | **confirmed** | closed 2025-04-01
- [[INV014]] | [[P244]] (DME Supplier) | **cleared** | closed 2025-04-07
- [[INV021]] | [[P190]] (Internal Medicine) | **cleared** | closed 2025-05-13
- [[INV015]] | [[P026]] (DME Supplier) | **cleared** | closed 2025-07-07
- [[INV030]] | [[P122]] (DME Supplier) | **cleared** | closed 2025-07-11
- [[INV033]] | [[P256]] (Behavioral Health) | **inconclusive** | closed 2025-08-21
- [[INV037]] | [[P142]] (Internal Medicine) | **inconclusive** | closed 2025-09-02
- [[INV039]] | [[P076]] (Laboratory) | **confirmed** | closed 2025-10-24
<!-- /auto -->
