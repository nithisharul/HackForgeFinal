"""
ClaimShield Nexus - synthetic data generator.

Every record written by this script is SYNTHETIC. No real patient, member,
provider, or facility appears anywhere. Realism comes from public reference
anchors only:

  * Procedure codes   - real CPT/HCPCS code numbers (office visits 99211-99215,
                        common lab, imaging, therapy, DME and ambulance codes).
  * Prices            - APPROXIMATE national Medicare fee schedule rates per
                        code (see FEE below). Replace with exact current values
                        if you need them to be checkable to the cent.
  * Visit-level mix   - APPROXIMATE Medicare distribution of established-patient
                        office visits (levels 3 and 4 dominate).
  * Geography         - real Texas cities with real coordinates, so
                        impossible-travel distances are true distances.

Usage:  python generate_data.py        (needs numpy and pandas)
Output: ./raw/*.csv next to this file. Fixed seed, so output is reproducible.
"""
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
rng = np.random.default_rng(SEED)
OUT = Path(__file__).resolve().parent / "raw"

START = pd.Timestamp("2025-10-01")
END = pd.Timestamp("2026-09-30")
N_PROVIDERS, N_MEMBERS, N_FACILITIES, N_OWNERS = 300, 5000, 40, 60

# ---------------------------------------------------------------- anchors ---
# city: (lat, lon, population weight) - real coordinates
CITIES = {
    "Houston": (29.7604, -95.3698, 0.26),
    "Dallas": (32.7767, -96.7970, 0.18),
    "San Antonio": (29.4241, -98.4936, 0.16),
    "Austin": (30.2672, -97.7431, 0.13),
    "Fort Worth": (32.7555, -97.3308, 0.11),
    "El Paso": (31.7619, -106.4850, 0.07),
    "Corpus Christi": (27.8006, -97.3964, 0.05),
    "Lubbock": (33.5779, -101.8552, 0.04),
}

# code: approximate national Medicare rate in USD (approximations, not exact)
FEE = {
    "99211": 24, "99212": 57, "99213": 92, "99214": 130, "99215": 183,  # office visits
    "99349": 128, "99350": 180,            # home visits
    "36415": 9,                            # venipuncture
    "80048": 8.5, "80053": 10.5,           # basic / comprehensive metabolic panel
    "85025": 7.8, "83036": 9.7,            # CBC, HbA1c
    "71046": 35, "73560": 33, "93000": 15, # chest x-ray, knee x-ray, ECG
    "97110": 30,                           # therapeutic exercise, per 15 min
    "90834": 105, "90837": 155,            # psychotherapy 45 / 60 min
    "E0601": 55, "E1390": 75, "A4253": 8,  # CPAP rental, O2 concentrator, test strips
    "A0428": 270, "A0429": 430,            # ambulance BLS non-emergency / emergency
}

EM_CODES = ["99211", "99212", "99213", "99214", "99215"]
EM_BASE = [0.02, 0.05, 0.38, 0.47, 0.08]  # approximate Medicare level mix

# specialty: (share of providers, claim_type)
SPECIALTIES = {
    "Family Medicine": (0.25, "professional"),
    "Internal Medicine": (0.20, "professional"),
    "Cardiology": (0.08, "professional"),
    "Orthopedics": (0.07, "professional"),
    "Behavioral Health": (0.10, "behavioral_health"),
    "Physical Therapy": (0.08, "professional"),
    "Laboratory": (0.07, "laboratory"),
    "Home Health": (0.06, "home_health"),
    "DME Supplier": (0.05, "dme"),
    "Ambulance": (0.04, "ambulance"),
}
EM_SPECS = ["Family Medicine", "Internal Medicine", "Cardiology", "Orthopedics"]
NON_EM = {
    "Behavioral Health": (["90834", "90837"], [0.55, 0.45]),
    "Physical Therapy": (["97110"], [1.0]),
    "Laboratory": (["80053", "80048", "85025", "83036", "36415"], [0.30, 0.20, 0.25, 0.15, 0.10]),
    "Home Health": (["99349", "99350"], [0.70, 0.30]),
    "DME Supplier": (["E0601", "E1390", "A4253"], [0.50, 0.30, 0.20]),
    "Ambulance": (["A0429", "A0428"], [0.60, 0.40]),
}
ADDON = {  # extra line billed alongside ~25% of office visits
    "Family Medicine": ["36415", "93000", "71046"],
    "Internal Medicine": ["36415", "93000", "71046"],
    "Cardiology": ["93000"],
    "Orthopedics": ["73560"],
}

FIRST = ["Maria", "James", "Priya", "David", "Elena", "Samuel", "Aisha", "Robert", "Linh", "Carlos",
         "Hannah", "Omar", "Grace", "Victor", "Nadia", "Thomas", "Ines", "Kevin", "Rosa", "Daniel"]
LAST = ["Alvarez", "Brooks", "Chen", "Delgado", "Ellis", "Foster", "Gupta", "Hayes", "Ibarra", "Jensen",
        "Khan", "Lopez", "Morris", "Nguyen", "Ortiz", "Patel", "Quinn", "Reyes", "Shah", "Turner"]
WORDS = ["Lone Star", "Bluebonnet", "Gulf Coast", "Hill Country", "Red River", "Alamo", "Pecos",
         "Brazos", "Trinity", "Panhandle", "Mesquite", "Live Oak", "Rio", "Prairie", "Cypress"]
OWNER_SUFFIX = ["Medical Group", "Health Partners", "Care Holdings", "Physicians LLC"]
ORG_SUFFIX = {"Laboratory": "Diagnostics Lab", "Ambulance": "EMS", "DME Supplier": "Medical Supply",
              "Home Health": "Home Care"}


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(a))


# ------------------------------------------------------- reference tables ---
city_names = list(CITIES)
city_w = np.array([CITIES[c][2] for c in city_names])
city_w = city_w / city_w.sum()

# facilities (every city gets at least one)
fac_city = np.concatenate([city_names, rng.choice(city_names, N_FACILITIES - len(city_names), p=city_w)])
fac_type = rng.choice(["Clinic", "Medical Office", "Hospital Outpatient", "Diagnostic Center"],
                      N_FACILITIES, p=[0.4, 0.3, 0.2, 0.1])
fac = pd.DataFrame({
    "facility_id": [f"F{i:03d}" for i in range(1, N_FACILITIES + 1)],
    "name": [f"{c} {rng.choice(WORDS)} {t}" for c, t in zip(fac_city, fac_type)],
    "type": fac_type,
    "city": fac_city,
    "lat": [round(CITIES[c][0] + rng.normal(0, 0.04), 4) for c in fac_city],
    "lon": [round(CITIES[c][1] + rng.normal(0, 0.04), 4) for c in fac_city],
    "owner_id": [f"O{i:03d}" for i in rng.integers(1, N_OWNERS + 1, N_FACILITIES)],
}).set_index("facility_id", drop=False)

# members
m_age = np.clip(np.where(rng.random(N_MEMBERS) < 0.45, rng.normal(72, 8, N_MEMBERS),
                         rng.normal(42, 14, N_MEMBERS)), 18, 97).astype(int)
members = pd.DataFrame({
    "member_id": [f"M{i:05d}" for i in range(1, N_MEMBERS + 1)],
    "age": m_age,
    "gender": rng.choice(["F", "M"], N_MEMBERS, p=[0.54, 0.46]),
    "city": rng.choice(city_names, N_MEMBERS, p=city_w),
})
members["chronic_flag"] = (rng.random(N_MEMBERS) < 0.2 + 0.4 * (members.age > 65)).astype(int)
members_by_city, weight_by_city = {}, {}
for c, g in members.groupby("city"):
    members_by_city[c] = g.member_id.values
    w = 1 + 2 * g.chronic_flag.values  # chronic members are seen more often
    weight_by_city[c] = w / w.sum()

# providers
spec_names = list(SPECIALTIES)
spec_w = np.array([SPECIALTIES[s][0] for s in spec_names])
p_spec = rng.choice(spec_names, N_PROVIDERS, p=spec_w / spec_w.sum())
p_fac = rng.choice(fac.facility_id.values, N_PROVIDERS)


def provider_name(spec):
    if spec in ORG_SUFFIX:
        return f"{rng.choice(WORDS)} {ORG_SUFFIX[spec]}"
    return f"Dr. {rng.choice(FIRST)} {rng.choice(LAST)}"


prov = pd.DataFrame({
    "provider_id": [f"P{i:03d}" for i in range(1, N_PROVIDERS + 1)],
    "name": [provider_name(s) for s in p_spec],
    "specialty": p_spec,
    "facility_id": p_fac,
    "owner_id": [f"O{i:03d}" for i in rng.integers(1, N_OWNERS + 1, N_PROVIDERS)],
    "monthly_rate": rng.lognormal(np.log(15), 0.5, N_PROVIDERS),
    "charge_mult": rng.uniform(1.4, 2.4, N_PROVIDERS),
    "role": "normal",
}).set_index("provider_id", drop=False)

# ------------------------------------------------------ assign FWA roles ---
def pick(specs, k):
    pool = prov.index[prov.specialty.isin(specs) & (prov.role == "normal")]
    return list(rng.choice(pool, k, replace=False))


def set_role(ids, role):
    prov.loc[ids, "role"] = role
    return ids


ring = []
for spec, k in [("Family Medicine", 2), ("Laboratory", 1), ("DME Supplier", 1),
                ("Physical Therapy", 1), ("Cardiology", 1)]:
    ring += set_role(pick([spec], k), "collusive_ring")
RING_OWNER = f"O{N_OWNERS + 1:03d}"
houston_fac = fac.index[fac.city == "Houston"].values
prov.loc[ring, "facility_id"] = rng.choice(houston_fac, len(ring))
prov.loc[ring, "owner_id"] = RING_OWNER

upcoders = set_role(pick(EM_SPECS, 6), "upcoding")
timers = set_role(pick(EM_SPECS + ["Behavioral Health"], 4), "impossible_timing")
unbundlers = set_role(pick(["Laboratory"], 3), "unbundling")
dupers = set_role(pick([s for s in spec_names if s != "Laboratory"], 6), "duplicate_billing")
legit_volume = set_role(pick(EM_SPECS + ["Laboratory"], 3), "legit_high_volume")
legit_freq = set_role(pick(["Home Health", "Physical Therapy"], 2), "legit_high_frequency")
prov.loc[legit_volume, "monthly_rate"] *= 4
prov.loc[legit_freq, "monthly_rate"] *= 2.5

prov["city"] = prov.facility_id.map(fac.city)
prov["lat"] = prov.facility_id.map(fac.lat)
prov["lon"] = prov.facility_id.map(fac.lon)

fwa_ids = ring + upcoders + timers + unbundlers + dupers
month_starts = pd.date_range("2025-12-01", "2026-04-01", freq="MS")
fwa_start = {pid: month_starts[rng.integers(0, len(month_starts))] for pid in fwa_ids}
for pid in ring:
    fwa_start[pid] = pd.Timestamp("2026-03-01")

# ------------------------------------------------------- claim machinery ---
bdays = pd.bdate_range(START, END)


def rand_dt(n, lo=START, hi=END):
    days = bdays[(bdays >= lo) & (bdays <= hi)]
    return days[rng.integers(0, len(days), n)] + pd.to_timedelta(rng.integers(8 * 60, 17 * 60, n), unit="m")


def draw_codes(spec, n):
    if spec in EM_SPECS:
        return rng.choice(EM_CODES, n, p=EM_BASE)
    codes, p = NON_EM[spec]
    return rng.choice(codes, n, p=p)


def make_rows(pid, mem, dts, codes, pattern="", facility=None):
    codes = np.asarray(codes)
    units = np.ones(len(codes), dtype=int)
    pt = codes == "97110"
    units[pt] = rng.integers(1, 5, pt.sum())
    return pd.DataFrame({
        "member_id": np.asarray(mem), "provider_id": pid,
        "facility_id": facility or prov.at[pid, "facility_id"],
        "service_datetime": dts, "procedure_code": codes, "units": units, "_pattern": pattern,
    })


def price(df):
    fee = df.procedure_code.map(FEE).values * df.units.values
    mult = df.provider_id.map(prov.charge_mult).values
    df["billed_amount"] = np.round(fee * mult * rng.normal(1, 0.02, len(df)), 2)
    df["paid_amount"] = np.round(fee * rng.uniform(0.78, 1.0, len(df)), 2)
    return df


# ------------------------------------------------------------ base claims ---
frames = []
for pid, p in prov.iterrows():
    n = max(20, rng.poisson(p.monthly_rate * 12))
    if p.role == "legit_high_frequency":
        panel_n = max(8, n // 14)          # few members, many visits each (documented program)
    elif p.role == "legit_high_volume":
        panel_n = max(15, n // 3)          # regional referral centre: big panel, normal per-member use
    else:
        panel_n = max(15, int(n / rng.uniform(2, 5)))
    pool = members_by_city[p.city]
    panel = rng.choice(pool, min(panel_n, len(pool)), replace=False, p=weight_by_city[p.city])
    mem, dts = rng.choice(panel, n), rand_dt(n)
    frames.append(make_rows(pid, mem, dts, draw_codes(p.specialty, n)))
    if p.specialty in ADDON:
        k = rng.random(n) < 0.25
        frames.append(make_rows(pid, mem[k], dts[k], rng.choice(ADDON[p.specialty], k.sum())))
claims = pd.concat(frames, ignore_index=True)

# --- pattern 1: upcoding that escalates month by month ---------------------
for pid in upcoders:
    s = fwa_start[pid]
    idx = claims.index[(claims.provider_id == pid) & claims.procedure_code.isin(EM_CODES)
                       & (claims.service_datetime >= s)]
    frac = (claims.loc[idx, "service_datetime"] - s) / (END - s)
    hit = idx[rng.random(len(idx)) < (0.15 + 0.70 * frac.values)]
    new = rng.choice(["99214", "99215"], len(hit), p=[0.35, 0.65])
    raised = new > claims.loc[hit, "procedure_code"].values
    claims.loc[hit, "procedure_code"] = new
    claims.loc[hit[raised], "_pattern"] = "upcoding"

claims = price(claims)
extra = []

# --- pattern 2: duplicate billing ------------------------------------------
for pid in dupers:
    src = claims[(claims.provider_id == pid) & (claims.service_datetime >= fwa_start[pid])]
    dup = src.sample(frac=0.20, random_state=int(rng.integers(1_000_000))).copy()
    fast = rng.random(len(dup)) < 0.5
    delta = np.where(fast, rng.integers(2, 20, len(dup)), rng.integers(1, 4, len(dup)) * 1440)
    dup["service_datetime"] = dup.service_datetime + pd.to_timedelta(delta, unit="m")
    dup["_pattern"] = "duplicate_billing"
    extra.append(dup)

# --- pattern 3: impossible timing (two facilities 150+ km apart) -----------
for pid in timers:
    home = prov.at[pid, "facility_id"]
    dist = haversine_km(fac.at[home, "lat"], fac.at[home, "lon"], fac.lat.values, fac.lon.values)
    far = rng.choice(fac.facility_id.values[dist > 150])
    n = int(rng.integers(20, 36))
    t = rand_dt(n, lo=fwa_start[pid])
    spec = prov.at[pid, "specialty"]
    a = make_rows(pid, rng.choice(members_by_city[prov.at[pid, "city"]], n), t,
                  draw_codes(spec, n), "impossible_timing")
    b = make_rows(pid, rng.choice(members_by_city[fac.at[far, "city"]], n),
                  t + pd.to_timedelta(rng.integers(5, 31, n), unit="m"),
                  draw_codes(spec, n), "impossible_timing", facility=far)
    extra += [price(a), price(b)]

# --- pattern 4: unbundling (basic panel billed on top of comprehensive) ----
for pid in unbundlers:
    src = claims[(claims.provider_id == pid) & (claims.procedure_code == "80053")
                 & (claims.service_datetime >= fwa_start[pid])]
    add = src[rng.random(len(src)) < 0.5].copy()
    add["procedure_code"] = "80048"
    add["_pattern"] = "unbundling"
    extra.append(price(add))

# --- pattern 5: collusive ring (shared owner, members, circular referrals) -
ring_pool = rng.choice(members_by_city["Houston"], 70, replace=False)
ring_refs = []
for i, pid in enumerate(ring):
    for k, ms in enumerate(pd.date_range(fwa_start[pid], END, freq="MS")):
        n = 25 + 12 * k  # volume grows every month
        rows = make_rows(pid, rng.choice(ring_pool, n), rand_dt(n, ms, min(ms + pd.offsets.MonthEnd(0), END)),
                         draw_codes(prov.at[pid, "specialty"], n), "collusive_ring")
        extra.append(price(rows))
        sent = rows[rng.random(n) < 0.5]
        ring_refs.append(pd.DataFrame({
            "from_provider_id": pid, "to_provider_id": ring[(i + 1) % len(ring)],
            "member_id": sent.member_id.values, "referral_date": sent.service_datetime.dt.date.values,
        }))

claims = pd.concat([claims] + extra, ignore_index=True).sort_values("service_datetime").reset_index(drop=True)
claims.insert(0, "claim_id", [f"C{i:06d}" for i in range(1, len(claims) + 1)])
claims["claim_type"] = claims.provider_id.map(prov.specialty).map(lambda s: SPECIALTIES[s][1])
claims["em_level"] = claims.procedure_code.map({c: i + 1 for i, c in enumerate(EM_CODES)}).astype("Int64")

# -------------------------------------------------------------- referrals ---
targets_by_city = {c: g.index.values for c, g in
                   prov[~prov.specialty.isin(["Family Medicine", "Internal Medicine"])].groupby("city")}
ref_frames = []
visits = claims[(claims._pattern == "") & claims.procedure_code.isin(EM_CODES)]
for pid, g in visits.groupby("provider_id"):
    opts = targets_by_city.get(prov.at[pid, "city"], np.array([]))
    opts = opts[opts != pid]
    if len(opts) == 0:
        continue
    preferred = rng.choice(opts, min(len(opts), int(rng.integers(3, 9))), replace=False)
    sent = g[rng.random(len(g)) < 0.20]
    ref_frames.append(pd.DataFrame({
        "from_provider_id": pid, "to_provider_id": rng.choice(preferred, len(sent)),
        "member_id": sent.member_id.values, "referral_date": sent.service_datetime.dt.date.values,
    }))
referrals = pd.concat(ref_frames + ring_refs, ignore_index=True).sort_values("referral_date").reset_index(drop=True)
referrals.insert(0, "referral_id", [f"R{i:05d}" for i in range(1, len(referrals) + 1)])

# -------------------------------------------------------------- ownership ---
owner_names = [f"{w} {s}" for w in WORDS for s in OWNER_SUFFIX]
owner_names = list(rng.permutation(owner_names)[:N_OWNERS]) + ["Gulfline Health Holdings LLC"]
owner_name = {f"O{i:03d}": n for i, n in enumerate(owner_names, start=1)}
ownership = pd.concat([
    pd.DataFrame({"owner_id": prov.owner_id.values, "entity_type": "provider", "entity_id": prov.provider_id.values}),
    pd.DataFrame({"owner_id": fac.owner_id.values, "entity_type": "facility", "entity_id": fac.facility_id.values}),
], ignore_index=True)
ownership.insert(1, "owner_name", ownership.owner_id.map(owner_name))

# ---------------------------------------- past investigations (precedents) ---
REASON = {
    ("duplicate_billing", "confirmed"): "Same member, procedure and amount resubmitted within days with no corrected-claim indicator. Provider could not produce separate encounter notes. Overpayment recovered.",
    ("duplicate_billing", "cleared"): "Repeat claims were corrected resubmissions after a clearinghouse rejection; the originals were never paid.",
    ("upcoding", "confirmed"): "Share of level 4-5 visits rose far above specialty peers. Sampled charts supported level 3 at most.",
    ("upcoding", "cleared"): "High visit levels explained by a documented complex, multi-condition patient panel. Sampled charts supported the levels billed.",
    ("impossible_timing", "confirmed"): "Services billed at two sites over 150 km apart within minutes. Provider was physically present at only one; second-site services were not rendered as billed.",
    ("impossible_timing", "cleared"): "Second-site claims were telehealth visits billed with the wrong place of service. Provider corrected the claims.",
    ("unbundling", "confirmed"): "Component panel billed alongside the comprehensive panel for the same draw. Bundling edit applies; overpayment recovered.",
    ("unbundling", "cleared"): "Tests were ordered and drawn on separate dates; a date-of-service entry error made them appear same-day.",
    ("collusive_ring", "confirmed"): "Commonly owned providers cross-referred the same small member group with no clinical rationale in the records. Referred services lacked orders.",
    ("collusive_ring", "cleared"): "Shared ownership reflects a legitimate multi-specialty group. Referrals matched documented care plans.",
    ("excessive_utilization", "confirmed"): "Visits per member far above peers and not supported by plans of care. Services exceeded medical necessity.",
    ("excessive_utilization", "cleared"): "Volume far above peers, but provider is a regional referral centre or runs a documented high-intensity program. Services were supported by orders and notes.",
}
INCONCLUSIVE = "Records request only partially fulfilled. Evidence insufficient to confirm or clear. Provider placed on monitoring."
ALL_PATTERNS = sorted({k[0] for k in REASON})

cases = []
prior = rng.choice(fwa_ids, 8, replace=False)  # FWA providers with a history: supports "repeat FWA"
for i, pid in enumerate(prior):
    cases.append((pid, prov.at[pid, "role"], "confirmed" if i < 5 else "inconclusive"))
for pid in legit_volume + legit_freq[:1]:       # cleared outliers = negative precedents
    cases.append((pid, "excessive_utilization", "cleared"))
normal_ids = rng.choice(prov.index[prov.role == "normal"], 28, replace=False)
for i, pid in enumerate(normal_ids):
    verdict = "cleared" if i < 19 else ("inconclusive" if i < 25 else "confirmed")
    spec = prov.at[pid, "specialty"]
    allowed = [x for x in ALL_PATTERNS if x != "collusive_ring"
               and (x != "upcoding" or spec in EM_SPECS) and (x != "unbundling" or spec == "Laboratory")]
    cases.append((pid, rng.choice(allowed), verdict))

inv_rows = []
for n, (pid, pattern, verdict) in enumerate(cases, start=1):
    opened = pd.Timestamp("2025-01-01") + pd.Timedelta(days=int(rng.integers(0, 270)))
    closed = opened + pd.Timedelta(days=int(rng.integers(20, 76)))
    exposure = float(np.round(rng.lognormal(np.log(18000), 0.8), 2))
    inv_rows.append({
        "case_id": f"INV{n:03d}", "provider_id": pid, "specialty": prov.at[pid, "specialty"],
        "pattern": pattern, "verdict": verdict,
        "reasoning": INCONCLUSIVE if verdict == "inconclusive" else REASON[(pattern, verdict)],
        "exposure_amount": exposure,
        "recovered_amount": round(exposure * rng.uniform(0.4, 0.9), 2) if verdict == "confirmed" else 0.0,
        "opened_date": opened.date(), "closed_date": closed.date(),
    })
investigations = pd.DataFrame(inv_rows).sort_values("closed_date").reset_index(drop=True)

# ----------------------------------------------------------- ground truth ---
NOTE = {
    "legit_high_volume": "Legitimate regional referral centre: very high volume, normal use per member. Should be cleared.",
    "legit_high_frequency": "Legitimate documented high-intensity program: many visits per member. Should be cleared.",
}
ground_truth = pd.DataFrame({
    "provider_id": prov.provider_id.values,
    "is_fwa": prov.provider_id.isin(fwa_ids).astype(int).values,
    "pattern": prov.role.values,
    "start_date": [fwa_start[p].date() if p in fwa_start else "" for p in prov.provider_id],
    "note": prov.role.map(NOTE).fillna("").values,
})
claim_labels = claims.loc[claims._pattern != "", ["claim_id", "_pattern"]].rename(columns={"_pattern": "injected_pattern"})

# ------------------------------------------------------------------ write ---
OUT.mkdir(parents=True, exist_ok=True)
claims_out = claims[["claim_id", "member_id", "provider_id", "facility_id", "service_datetime", "claim_type",
                     "procedure_code", "em_level", "units", "billed_amount", "paid_amount"]].copy()
claims_out["service_datetime"] = claims_out.service_datetime.dt.strftime("%Y-%m-%d %H:%M")
tables = {
    "providers": prov[["provider_id", "name", "specialty", "facility_id", "owner_id", "city", "lat", "lon"]],
    "facilities": fac[["facility_id", "name", "type", "city", "lat", "lon"]],
    "members": members,
    "claims": claims_out,
    "referrals": referrals,
    "ownership": ownership,
    "investigations": investigations,
    "ground_truth": ground_truth,     # evaluation only - never use as a model feature
    "claim_labels": claim_labels,     # evaluation only - never use as a model feature
}
for name, df in tables.items():
    df.to_csv(OUT / f"{name}.csv", index=False)
    print(f"{name:15s} {len(df):>7,} rows")
print(f"\nFWA providers: {len(fwa_ids)} of {N_PROVIDERS} | injected claims: {len(claim_labels):,} of {len(claims):,}")
print(claim_labels.injected_pattern.value_counts().to_string())
print(f"\nWritten to {OUT}")
