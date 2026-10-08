---
type: pattern
id: excessive_utilization
title: Excessive utilization
policy: POL-006
---
# Excessive utilization

## Definition
Volume, visits per member or dollars far above specialty peers without a documented reason.

## Detection signals
- Anomaly model: Isolation Forest score with drivers such as claims per member or total paid
- Rule R4: units above the per-day limit

## Policy basis
- POL-006 Utilization review (`knowledge/sources/policies/POL-006.md`)
- Public basis: CMS Medicare Program Integrity Manual (data analysis and medical review), as general background

## Known innocent explanations
- A regional referral centre with a very large panel and normal use per member
- A documented high-intensity program such as intensive rehabilitation or home health
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
11 closed cases: 1 confirmed, 9 cleared, 1 inconclusive.
<!-- /auto -->

## Cases
<!-- auto:cases -->
- [[INV013]] | [[P117]] (Behavioral Health) | **cleared** | closed 2025-03-03
- [[INV025]] | [[P265]] (Family Medicine) | **cleared** | closed 2025-04-01
- [[INV034]] | [[P174]] (Family Medicine) | **inconclusive** | closed 2025-04-20
- [[INV028]] | [[P067]] (Home Health) | **cleared** | closed 2025-07-12
- [[INV012]] | [[P116]] (Physical Therapy) | **cleared** | closed 2025-07-24
- [[INV038]] | [[P057]] (Behavioral Health) | **confirmed** | closed 2025-07-28
- [[INV011]] | [[P136]] (Cardiology) | **cleared** | closed 2025-08-13
- [[INV027]] | [[P113]] (Family Medicine) | **cleared** | closed 2025-08-30
- [[INV018]] | [[P007]] (Behavioral Health) | **cleared** | closed 2025-10-10
- [[INV009]] | [[P134]] (Cardiology) | **cleared** | closed 2025-10-21
- [[INV010]] | [[P131]] (Cardiology) | **cleared** | closed 2025-11-02
<!-- /auto -->
