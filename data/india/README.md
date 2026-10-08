# India region static dataset (PM-JAY style)

All data here is SYNTHETIC. No real beneficiary, hospital, owner, agent or card operator appears.
Hospital and owner names use coined words so they do not match real institutions. Cities, districts
and package codes are real; everything attached to them is generated.

Rebuild with `python generate_data_in.py` (fixed seed, same output every time).

## Files

File names and leading columns are the same as the US dataset in `data/raw/`, so the existing
pipeline can load either region. India-only fields follow as extra columns.

| File | Rows | Same columns as US | Extra India columns |
|---|---|---|---|
| `raw/claims.csv` | 75,721 | claim_id, member_id, provider_id, facility_id, service_datetime, claim_type, procedure_code, em_level, units, billed_amount, paid_amount | preauth_datetime, discharge_datetime, los_days, admission_type, specialty, diagnosis_icd10, ward_type, implant_amount, claim_status, discharge_status, portability_flag, referred_by_agent_id, document_hash |
| `raw/providers.csv` | 300 | provider_id, name, specialty, facility_id, owner_id, city, lat, lon | sector, state, district, city_tier, beds, nabh_status, teaching, empanelled_specialties, empanelment_date |
| `raw/facilities.csv` | 300 | facility_id, name, type, city, lat, lon | state, district, beds |
| `raw/members.csv` | 26,303 | member_id, age, gender, city, chronic_flag | family_id, state, district, village_code, mobile_token, card_created_date, card_operator_id, death_date |
| `raw/referrals.csv` | 1,479 | all | none |
| `raw/ownership.csv` | 600 | all | none |
| `raw/investigations.csv` | 40 | all | state |
| `raw/ground_truth.csv` | 300 | all (evaluation only) | none |
| `raw/claim_labels.csv` | 4,659 | all (evaluation only) | none |
| `reference/package_master.csv` | 45 | India only: package code, name, specialty, rate, implant add-on, assumed stay, ICD-10, rate source |  |
| `reference/ward_rates.csv` | 4 | India only: per-day medical rates by ward type |  |

How the US columns are used for India:

- A **provider** is a hospital, and each hospital is its own **facility** (`P001` and `F001` are the same place).
- `specialty` on a provider is the hospital type (Nursing Home, Eye Hospital, District Hospital and so on), which is the peer group.
- A **member** is a PM-JAY beneficiary.
- `service_datetime` is the admission time, `procedure_code` is the package code, `claim_type` is the package type.
- `billed_amount` is the claimed amount and `paid_amount` the approved amount, both in rupees.
- `em_level` is empty: India has no visit-level codes.

Mobile numbers are tokens (`MOB000123`), never real numbers, except the placeholder values
`9999999999` and `8888888888`, which the CAG audit found typed against lakhs of real cards.

## Injected patterns (28 of 300 hospitals)

| Pattern | Hospitals | Claims | What the data shows | Real-world basis |
|---|---|---|---|---|
| `collusive_ring` | 5 | 1,906 | One owner, one agent, one card operator; 95 people from three villages rotated between five Lucknow hospitals; volume grows monthly; circular referrals | Fake-card and agent rings reported in Uttar Pradesh and Gujarat |
| `bed_overrun` | 2 | 1,045 | Pre-authorisations on single days at 4 to 9 times bed strength | Indore 2023: 13-bed eye hospital, 184 pre-authorisations in a day |
| `opd_to_ipd` | 3 | 882 | One-day admissions for fever, gastroenteritis and UTI, whole families on the same day | Official PM-JAY trigger; no published threshold |
| `ghost_beneficiary` | 3 | 303 | Cards created 1 to 6 days before admission by one operator, shared mobile tokens | Himachal, Ahmedabad and Lucknow fake-card cases |
| `unnecessary_procedure` | 3 | 198 | Hysterectomy in women aged 22 to 34 the day after village camps; angioplasty on villagers bussed from one village | Health Ministry audit rule for hysterectomy under 35; Khyati Hospital 2024 |
| `duplicate_document` | 3 | 98 | Same document hash on claims for different beneficiaries | Official PM-JAY trigger |
| `package_upcoding` | 4 | 69 | General-ward medical cases billed at ICU or ventilator rates, rising over time | Official PM-JAY trigger |
| `overlapping_admission` | 3 | 116 | Beneficiary admitted while already an inpatient elsewhere | CAG: 78,396 such claims |
| `claim_after_death` | 2 | 42 | Claims after the beneficiary's recorded death | CAG: 3,903 such paid claims |

Innocent outliers that should be cleared: two government medical colleges running above sanctioned
beds, two high-volume eye hospitals, two dialysis centres with repeat sessions, about 2.6% of
beneficiaries on placeholder mobile numbers, and ordinary hysterectomies in women under 35.

## What is real and what is assumed

| Item | Status | Source |
|---|---|---|
| 40 package codes and rates | Read from published lists (HBP 2.0, and HBP 2022 for dialysis) | NHA HBP 2.0 package master; Punjab and Nagaland State Health Agency lists |
| 5 package rates (cataract, hysterectomy, caesarean, knee replacement, tonsillectomy) | Real package-level code, ESTIMATED rate, marked `approximate` | Codes from a Punjab SHA order; rates not readable |
| Ward rates 1,800 / 2,700 / 3,600 / 4,500 | Published | HBP 2.0 and HBP 2.2 manual |
| NABH, metro and teaching incentives | Published percentages | HBP 2.2 manual |
| State mix of hospitals | Weighted by PM-JAY admissions | Lok Sabha replies, 2025 |
| Dialysis about 14% of treatments (18% here), fever, gastroenteritis, animal bites | Published shares | NHA Annual Report 2024-25, via summaries |
| Women about 49% of admissions (52% here) | Published | NHA Annual Report 2024-25 |
| Typical length of stay per package | ASSUMED | Not published |
| City coordinates and tiers | Approximate, from general knowledge | Not checked against a gazetteer |
| Hospital bed mix (71% at 50 beds or fewer; published figure about 80%) | Approximate | PLOS ONE 2021 |
| Private share of claim value (about 45% here; published about 66%) | NOT calibrated | NHA Annual Report 2024-25 |
| Fraud rates and sizes | Chosen for a demo; real prevalence is lower | See patterns table |

Spot-check package codes and prices against the NHA master before describing the table as official.
The verified rates are HBP 2.0; HBP 2022 rates are higher (for example PTCA 50,800 against 40,600).

## Running the pipeline on this data

```
python -m backend.pipeline.run_all --region in            # score with the saved India models
python -m backend.pipeline.run_all --region in --retrain  # retrain backend/models/india/
```

Outputs go to `data/india/processed/`, models to `backend/models/india/` and the India Second Brain
to `knowledge/india/`; nothing under the US folders is read or written. The India rule pack is
`backend/pipeline/rules_in.py` (overlapping admissions, duplicate packages, claims after death,
package mismatch and age audit, ICU-rate drift, stay above norm, OPD-to-IPD, identity, reused
documents, bed strength and empanelment, camp clusters). On the injected patterns all 28 hospitals
reach the queue; `metrics.json` reports false positives alongside recall.

## Differences from the US dataset

- A claim is an admission or day-care session with a package, diagnosis, ward and length of stay.
- Amounts are rupees. PM-JAY pays the package rate, so there is no billed-versus-paid markup;
  `paid_amount` is lower only where a deduction was applied.
- There is no private-insurer (itemised bill) data in this version.
