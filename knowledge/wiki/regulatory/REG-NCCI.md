---
type: regulatory
id: REG-NCCI
title: CMS National Correct Coding Initiative (NCCI)
written_by: code
---
# CMS National Correct Coding Initiative (NCCI)

> Reference page written by code from the pipeline. Rebuilt on every change; do not edit by hand.

> General background written for this prototype. It is a short summary, not legal advice; verify against the source.

## What it is
CMS publishes two public tables to stop improper coding. Procedure-to-Procedure (PTP) edits list pairs of codes that should not be paid together, with a modifier indicator (0 never, 1 with a supported modifier, 9 not applicable). Medically Unlikely Edits (MUE) give the most units of a code a provider would report for one patient on one day.

## How this system uses it
The PTP pairs drive [[R3]] and the MUE values drive [[R4]].

## Source to verify
- CMS NCCI edit files and the NCCI Policy Manual, published on cms.gov and updated quarterly.

## Linked pages
- [[R3]] | R3 Bundling edit pair (PTP)
- [[R4]] | R4 Unit limit (MUE)
- [[unbundling]] | Unbundling
- [[excessive_utilization]] | Excessive utilization
- [[system_limits]]
