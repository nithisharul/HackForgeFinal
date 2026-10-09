---
type: data
id: data_members
title: Data: members
written_by: code
---
# Data: members

> Reference page written by code from the pipeline. Rebuilt on every change; do not edit by hand.

## What it is
One row per plan member (patient).

## Where it comes from
Synthetic, written by `data/generate_data.py` with a fixed seed. No real person is represented.

## Size
- 5,000 rows in `data/raw/members.csv`.

## Fields
- `member_id`: Unique member identifier (M + 5 digits)
- `age`: Age in years
- `gender`: F or M
- `city`: Home city
- `chronic_flag`: 1 if the member has a chronic condition and so uses more care

## Used by
- The models and the network analysis; see [[system_models]].
- See also [[system_architecture]].
