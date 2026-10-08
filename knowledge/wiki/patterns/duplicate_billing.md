---
type: pattern
id: duplicate_billing
title: Duplicate billing
policy: POL-001
---
# Duplicate billing

## Definition
The same service for the same member is billed more than once without a corrected-claim or repeat-procedure indicator.

## Detection signals
- Rule R1: same member, provider, code and amount within 3 days
- Rule R4: units above the per-day limit for the code

## Policy basis
- POL-001 Duplicate claim submission (`knowledge/sources/policies/POL-001.md`)
- Public basis: CMS Medicare Claims Processing Manual (duplicate claim edits); CMS NCCI Medically Unlikely Edits

## Known innocent explanations
- Corrected resubmission after a clearinghouse rejection, where the original was never paid
- A procedure legitimately repeated on the same day and billed with a repeat-procedure modifier
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
10 closed cases: 0 confirmed, 7 cleared, 3 inconclusive.
<!-- /auto -->

## Cases
<!-- auto:cases -->
- [[INV017]] | [[P058]] (Internal Medicine) | **cleared** | closed 2025-04-02
- [[INV024]] | [[P271]] (Behavioral Health) | **cleared** | closed 2025-05-24
- [[INV008]] | [[P220]] (Physical Therapy) | **inconclusive** | closed 2025-06-10
- [[INV029]] | [[P195]] (DME Supplier) | **cleared** | closed 2025-06-18
- [[INV007]] | [[P221]] (Family Medicine) | **inconclusive** | closed 2025-06-19
- [[INV020]] | [[P037]] (Internal Medicine) | **cleared** | closed 2025-06-22
- [[INV032]] | [[P021]] (Behavioral Health) | **inconclusive** | closed 2025-07-04
- [[INV023]] | [[P294]] (Internal Medicine) | **cleared** | closed 2025-07-10
- [[INV026]] | [[P266]] (Internal Medicine) | **cleared** | closed 2025-09-10
- [[INV022]] | [[P216]] (Family Medicine) | **cleared** | closed 2025-11-01
<!-- /auto -->
