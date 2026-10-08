"""India reference tables for the PM-JAY rules (data/india/reference/).

PACKAGES     Health Benefit Package master: code, name, specialty, package type, base rate, implant
             add-on, ICD-10 and an ASSUMED typical length of stay. 40 rates were read from NHA / State
             Health Agency lists (HBP 2.0, HBP 2022 for dialysis); 5 are estimates (rate_source column).
WARD_RATES   HBP 2.0 per-day medical rates by ward: general, HDU, ICU, ICU with ventilator.
Incentives   HBP 2.2 manual: entry-level NABH +10%, full NABH +15%, metro (X-tier city) +10%,
             teaching hospital +10%, applied to the procedure price only, not to implants.
"""
import pandas as pd

from backend import region

REF = region.REGIONS["in"].reference
PACKAGES = pd.read_csv(REF / "package_master.csv", dtype={"package_code": str}).set_index("package_code")
WARD_RATES = pd.read_csv(REF / "ward_rates.csv").set_index("ward_type").per_day_rate_inr.to_dict()
NABH = {"none": 1.0, "entry": 1.10, "full": 1.15}
METRO, TEACHING = 1.10, 1.10
HIGH_WARDS = ("icu", "icu_ventilator")
PER_DAY = ("medical_per_day", "neonatal_per_day")
# Conditions usually treated as outpatients: fever, acute gastroenteritis, urinary tract infection.
# Short admissions for them are the official PM-JAY "OPD to IPD conversion" trigger; the list is ours.
OPD_TREATABLE = {"MG001A": "acute febrile illness", "MG009A": "acute gastroenteritis", "MG021A": "urinary tract infection"}
FEMALE_ONLY = {"SO010": "hysterectomy", "SO057": "caesarean delivery"}
# Health Ministry audit guidance: hysterectomy in a woman under 35 is reviewed before payment.
AGE_AUDIT = {"SO010": 35}

SOURCE = (f"{(PACKAGES.rate_source == 'verified').sum()} package rates from NHA HBP 2.0 / HBP 2022 lists and "
          f"{(PACKAGES.rate_source != 'verified').sum()} estimated; ward rates from HBP 2.0; "
          "typical length of stay per package is assumed, not published")


def entitled_amount(claims, prov):
    """Package price a hospital is entitled to claim, from the package master and its own tier and accreditation."""
    p = prov.set_index("provider_id")
    mult = (p.nabh_status.map(NABH).fillna(1.0) * p.city_tier.eq("X").map({True: METRO, False: 1.0})
            * p.teaching.eq(1).map({True: TEACHING, False: 1.0}))
    pk = PACKAGES.reindex(claims.procedure_code)
    per_day = claims.claim_type.isin(PER_DAY).values
    days = claims.los_days.clip(lower=1).values
    rate = pd.Series(claims.ward_type.map(WARD_RATES).values, index=claims.index).where(
        claims.claim_type.eq("medical_per_day"), pk.base_rate_inr.values)
    proc = rate.where(~per_day, rate * days)
    return (proc * claims.provider_id.map(mult).values + pk.implant_addon_inr.fillna(0).values).round(0)
