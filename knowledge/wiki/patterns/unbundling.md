---
type: pattern
id: unbundling
title: Unbundling
policy: POL-004
---
# Unbundling

## Definition
A component service is billed separately alongside the comprehensive service that already includes it.

## Detection signals
- Rule R3: a column-2 code billed with its column-1 code for the same member, provider and date

## Policy basis
- POL-004 Bundled services and component codes (`knowledge/sources/policies/POL-004.md`)
- Public basis: CMS National Correct Coding Initiative (NCCI) Procedure-to-Procedure edits and Policy Manual

## Known innocent explanations
- Tests drawn on separate dates that appear same-day because of a date-of-service entry error
- An edit pair that allows a modifier, billed with a supported modifier
<!-- auto:learned -->
<!-- /auto -->

## Detected by
- [[R3]] | R3 Bundling edit pair (PTP)
- What to request from the provider: [[runbook_evidence]]

## Regulatory background
- [[REG-NCCI]] | CMS National Correct Coding Initiative (NCCI)
- [[REG-FCA]] | False Claims Act

## Lessons from closed cases
<!-- auto:lessons -->
<!-- /auto -->

## Notes from sources
<!-- auto:notes -->
<!-- /auto -->

## Precedent summary
<!-- auto:summary -->
1 closed cases: 1 confirmed, 0 cleared, 0 inconclusive.
<!-- /auto -->

## Cases
<!-- auto:cases -->
- [[INV001]] | [[P210]] (Laboratory) | **confirmed** | closed 2025-08-05
<!-- /auto -->
