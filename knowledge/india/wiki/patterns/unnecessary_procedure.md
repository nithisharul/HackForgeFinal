---
type: pattern
id: unnecessary_procedure
title: Unnecessary procedures
policy: POL-IN-005
---
# Unnecessary procedures

## Definition
Surgery without a documented indication, often on patients brought in groups from camps by agents, such as hysterectomy in young women or angioplasty without cardiac history.

## Detection signals
- Rule IN10: 3 or more agent-referred surgeries for one package from one village in one week
- Rule IN4b: hysterectomy for a woman under 35 (mandatory audit trigger)
- Anomaly model: share of agent-referred admissions far above hospital-type peers

## Policy basis
- POL-IN-005 Medical necessity for elective surgery (`knowledge/india/sources/policies/POL-IN-005.md`)
- Public basis: Health Ministry audit guidance on hysterectomy in women under 35; NHA Field Investigation and Medical Audit Manual (2020); the Khyati Hospital case (2024) as background

## Known innocent explanations
- A visiting surgeon's fixed operating days concentrating surgery on certain dates
- Hysterectomy under 35 for a documented indication, confirmed by histopathology
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
6 closed cases: 2 confirmed, 3 cleared, 1 inconclusive.
<!-- /auto -->

## Cases
<!-- auto:cases -->
- [[INV015]] | [[P192]] (Orthopaedic Hospital) | **cleared** | closed 2025-02-14
- [[INV007]] | [[P166]] (Nursing Home) | **inconclusive** | closed 2025-03-30
- [[INV005]] | [[P194]] (Heart Institute) | **confirmed** | closed 2025-07-01
- [[INV019]] | [[P227]] (Heart Institute) | **cleared** | closed 2025-07-08
- [[INV022]] | [[P123]] (Multispecialty Hospital) | **cleared** | closed 2025-08-02
- [[INV001]] | [[P240]] (Multispecialty Hospital) | **confirmed** | closed 2025-09-11
<!-- /auto -->
