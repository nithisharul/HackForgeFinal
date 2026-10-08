---
type: data
id: data_investigations
title: Data: investigations
written_by: code
---
# Data: investigations

> Reference page written by code from the pipeline. Rebuilt on every change; do not edit by hand.

## What it is
Historical closed investigations. They seed the case pages and are the first precedents.

## Where it comes from
Synthetic, written by `data/generate_data.py` with a fixed seed. A copy is kept unedited at `knowledge/sources/investigations.csv`.

## Size
- 40 rows in `data/raw/investigations.csv`.

## Fields
- `case_id`: Historical case identifier (INV + 3 digits)
- `provider_id`: Provider investigated
- `specialty`: Provider specialty at the time
- `pattern`: The pattern investigated; one of the pattern pages
- `verdict`: confirmed, cleared or inconclusive
- `reasoning`: The investigator's stated reason
- `exposure_amount`: Dollars in question
- `recovered_amount`: Dollars recovered
- `opened_date`: Date opened
- `closed_date`: Date closed

## Used by
- The models and the network analysis; see [[system_models]].
- See also [[system_architecture]].
