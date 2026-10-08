---
type: data
id: data_claims
title: Data: claims
written_by: code
---
# Data: claims

> Reference page written by code from the pipeline. Rebuilt on every change; do not edit by hand.

## What it is
One row per billed service line. This is the main input to every rule and model.

## Where it comes from
Synthetic, written by `data/generate_data.py` with a fixed seed. Procedure code numbers are real CPT/HCPCS codes; prices approximate national Medicare fee schedule rates.

## Size
- 80,452 rows in `data/raw/claims.csv`.

## Fields
- `claim_id`: Unique claim line identifier (C + 6 digits)
- `member_id`: The patient the service was billed for; links to [[data_members]]
- `provider_id`: The rendering provider who billed; links to [[data_providers]]
- `facility_id`: Where the service was billed as delivered; links to [[data_facilities]]
- `service_datetime`: Date and time of service
- `claim_type`: professional, laboratory, dme (equipment), home_health, ambulance or behavioral_health
- `procedure_code`: CPT/HCPCS code for the service
- `em_level`: Office-visit level 1 to 5 for codes 99211-99215; empty for other codes
- `units`: Number of units billed on the line
- `billed_amount`: Amount the provider charged
- `paid_amount`: Amount the plan paid; used for dollar exposure

## Used by
- [[R1]] | R1 Duplicate claim
- [[R2]] | R2 Impossible travel
- [[R3]] | R3 Bundling edit pair (PTP)
- [[R4]] | R4 Unit limit (MUE)
- [[R5]] | R5 Visit-level drift
- See also [[system_architecture]].
