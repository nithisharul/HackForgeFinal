---
type: pattern
id: upcoding
title: Upcoding of visit levels
policy: POL-002
---
# Upcoding of visit levels

## Definition
Office visits are billed at a higher level (99214, 99215) than the documented complexity or time supports.

## Detection signals
- Rule R5: level-5 share of office visits at or above 35% in a month with 10+ visits
- Anomaly model: level-5 share far above specialty peers
- Trend: level mix drifting upward month over month

## Policy basis
- POL-002 Evaluation and management level selection (`knowledge/sources/policies/POL-002.md`)
- Public basis: CMS Evaluation and Management Services Guide; AMA CPT office visit codes 99211-99215

## Known innocent explanations
- A documented complex, multi-condition patient panel that supports high visit levels
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
6 closed cases: 2 confirmed, 2 cleared, 2 inconclusive.
<!-- /auto -->

## Cases
<!-- auto:cases -->
- [[INV040]] | [[P040]] (Internal Medicine) | **confirmed** | closed 2025-02-22
- [[INV003]] | [[P298]] (Family Medicine) | **confirmed** | closed 2025-03-08
- [[INV035]] | [[P119]] (Cardiology) | **inconclusive** | closed 2025-05-24
- [[INV019]] | [[P155]] (Family Medicine) | **cleared** | closed 2025-08-30
- [[INV036]] | [[P093]] (Cardiology) | **inconclusive** | closed 2025-10-13
- [[INV031]] | [[P049]] (Cardiology) | **cleared** | closed 2025-11-21
<!-- /auto -->
