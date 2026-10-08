---
type: data
id: data_providers
title: Data: providers
written_by: code
---
# Data: providers

> Reference page written by code from the pipeline. Rebuilt on every change; do not edit by hand.

## What it is
One row per provider that bills the plan.

## Where it comes from
Synthetic, written by `data/generate_data.py` with a fixed seed. Names are invented; cities and coordinates are real Texas locations.

## Size
- 300 rows in `data/raw/providers.csv`.

## Fields
- `provider_id`: Unique provider identifier (P + 3 digits)
- `name`: Invented display name
- `specialty`: Used to compare a provider with same-specialty peers
- `facility_id`: Home facility
- `owner_id`: Owning entity; links to [[data_ownership]]
- `city`: Home city
- `lat`: Latitude of the home facility
- `lon`: Longitude of the home facility

## Used by
- The models and the network analysis; see [[system_models]].
- See also [[system_architecture]].
