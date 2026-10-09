---
type: data
id: data_facilities
title: Data: facilities
written_by: code
---
# Data: facilities

> Reference page written by code from the pipeline. Rebuilt on every change; do not edit by hand.

## What it is
One row per place of service.

## Where it comes from
Synthetic, written by `data/generate_data.py` with a fixed seed. Coordinates are real, so travel distances in [[R2]] are true distances.

## Size
- 40 rows in `data/raw/facilities.csv`.

## Fields
- `facility_id`: Unique facility identifier (F + 3 digits)
- `name`: Invented display name
- `type`: Clinic, Medical Office or Hospital Outpatient
- `city`: City
- `lat`: Latitude
- `lon`: Longitude

## Used by
- [[R2]] | R2 Impossible travel
- See also [[system_architecture]].
