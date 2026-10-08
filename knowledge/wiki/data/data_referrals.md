---
type: data
id: data_referrals
title: Data: referrals
written_by: code
---
# Data: referrals

> Reference page written by code from the pipeline. Rebuilt on every change; do not edit by hand.

## What it is
One row each time a provider refers a member to another provider. Used to find closed referral loops.

## Where it comes from
Synthetic, written by `data/generate_data.py` with a fixed seed.

## Size
- 9,393 rows in `data/raw/referrals.csv`.

## Fields
- `referral_id`: Unique referral identifier
- `from_provider_id`: Provider who referred
- `to_provider_id`: Provider who received the referral
- `member_id`: Member referred
- `referral_date`: Date of the referral

## Used by
- The models and the network analysis; see [[system_models]].
- See also [[system_architecture]].
