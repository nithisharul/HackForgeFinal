---
type: data
id: data_ownership
title: Data: ownership
written_by: code
---
# Data: ownership

> Reference page written by code from the pipeline. Rebuilt on every change; do not edit by hand.

## What it is
Which owner controls which provider or facility. Used to measure how much of a network shares one owner.

## Where it comes from
Synthetic, written by `data/generate_data.py` with a fixed seed.

## Size
- 340 rows in `data/raw/ownership.csv`.

## Fields
- `owner_id`: Unique owner identifier (O + 3 digits)
- `owner_name`: Invented company name
- `entity_type`: provider or facility
- `entity_id`: The provider or facility owned

## Used by
- The models and the network analysis; see [[system_models]].
- See also [[system_architecture]].
