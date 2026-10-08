"""
ClaimShield Nexus - India region synthetic data generator (PM-JAY style).

Every record written by this script is SYNTHETIC. No real beneficiary, hospital,
owner, agent or card operator appears anywhere. Hospital and owner names use
coined words so they do not match real institutions. Realism comes from public
reference anchors only (see README.md in this folder for sources):

  * Packages   - Ayushman Bharat PM-JAY Health Benefit Package codes and rates.
                 Rows marked rate_source = "verified" were read from an NHA or
                 State Health Agency publication (HBP 2.0 / HBP 2022). Rows marked
                 "approximate" use a real package-level code whose rate could not
                 be read from a primary source; the rate is an estimate.
  * Ward rates - HBP 2.0 per-day medical rates: ward 1,800, HDU 2,700,
                 ICU 3,600, ICU with ventilator 4,500.
  * Incentives - HBP 2.2: entry NABH +10%, full NABH +15%, metro +10%,
                 teaching +10%, on procedure price only (not implants).
  * Geography  - real Indian cities and districts with approximate coordinates;
                 state weights follow PM-JAY admissions reported to Parliament.
  * Case mix   - haemodialysis about 14% of treatments, fever about 4%,
                 gastroenteritis about 3%, animal bites about 3% (NHA AR 2024-25).
  * Hospitals  - about 80% have 50 beds or fewer, 90% have 100 or fewer.
  * Fraud      - shapes follow CAG Report 11 of 2023 and documented cases.
                 Typical length of stay per package is ASSUMED (not published).

Usage:  python generate_data_in.py        (needs numpy and pandas)
Output: ./raw/*.csv and ./reference/package_master.csv next to this file.
Fixed seed, so output is reproducible.
"""
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 2026
rng = np.random.default_rng(SEED)
HERE = Path(__file__).resolve().parent
OUT, REF = HERE / "raw", HERE / "reference"

START = pd.Timestamp("2025-10-01")
END = pd.Timestamp("2026-09-30")
N_HOSP, N_BENE, N_OWNERS = 300, 26000, 70

# ---------------------------------------------------------------- anchors ---
# city: (district, state, lat, lon, tier X/Y/Z, weight). Coordinates approximate.
CITIES = {
    "Lucknow": ("Lucknow", "Uttar Pradesh", 26.85, 80.95, "Y", 5), "Prayagraj": ("Prayagraj", "Uttar Pradesh", 25.44, 81.85, "Y", 3),
    "Azamgarh": ("Azamgarh", "Uttar Pradesh", 26.07, 83.19, "Z", 2), "Amroha": ("Amroha", "Uttar Pradesh", 28.90, 78.47, "Z", 1.5),
    "Bhopal": ("Bhopal", "Madhya Pradesh", 23.26, 77.41, "Y", 4), "Balaghat": ("Balaghat", "Madhya Pradesh", 21.81, 80.19, "Z", 2),
    "Sidhi": ("Sidhi", "Madhya Pradesh", 24.42, 81.88, "Z", 1.5), "Ahmedabad": ("Ahmedabad", "Gujarat", 23.02, 72.57, "X", 5),
    "Bhavnagar": ("Bhavnagar", "Gujarat", 21.76, 72.15, "Y", 2.5), "Raipur": ("Raipur", "Chhattisgarh", 21.25, 81.63, "Y", 5),
    "Jagdalpur": ("Bastar", "Chhattisgarh", 19.08, 82.02, "Z", 2.5), "Kochi": ("Ernakulam", "Kerala", 9.93, 76.27, "Y", 4),
    "Kozhikode": ("Kozhikode", "Kerala", 11.26, 75.78, "Y", 3.5), "Chennai": ("Chennai", "Tamil Nadu", 13.08, 80.27, "X", 6),
    "Madurai": ("Madurai", "Tamil Nadu", 9.93, 78.12, "Y", 5), "Bengaluru": ("Bengaluru Urban", "Karnataka", 12.97, 77.59, "X", 6),
    "Kalaburagi": ("Kalaburagi", "Karnataka", 17.33, 76.83, "Y", 5), "Mumbai": ("Mumbai Suburban", "Maharashtra", 19.08, 72.88, "X", 2),
    "Nagpur": ("Nagpur", "Maharashtra", 21.15, 79.09, "Y", 1.5), "Jaipur": ("Jaipur", "Rajasthan", 26.91, 75.79, "Y", 4.5),
    "Barmer": ("Barmer", "Rajasthan", 25.75, 71.39, "Z", 2.5), "Ranchi": ("Ranchi", "Jharkhand", 23.34, 85.31, "Y", 1.7),
    "Dumka": ("Dumka", "Jharkhand", 24.27, 87.25, "Z", 0.8), "Patna": ("Patna", "Bihar", 25.59, 85.14, "Y", 1.4),
    "Purnia": ("Purnia", "Bihar", 25.78, 87.47, "Z", 0.7), "Gurugram": ("Gurugram", "Haryana", 28.46, 77.03, "Y", 1.4),
    "Hisar": ("Hisar", "Haryana", 29.15, 75.72, "Z", 1.2), "Ludhiana": ("Ludhiana", "Punjab", 30.90, 75.85, "Y", 1.6),
    "Bathinda": ("Bathinda", "Punjab", 30.21, 74.95, "Z", 1.1), "Guwahati": ("Kamrup Metropolitan", "Assam", 26.14, 91.74, "Y", 1.0),
    "Dibrugarh": ("Dibrugarh", "Assam", 27.47, 94.91, "Z", 0.6),
}
WARD_RATE = {"general": 1800, "hdu": 2700, "icu": 3600, "icu_ventilator": 4500}

# code: (name, specialty, group, type, base_rate, implant, typical_los[assumed], icd10, rate_source, hbp_version)
V20, V22, APX = ("verified", "HBP 2.0"), ("verified", "HBP 2022"), ("approximate", "HBP 2.0 code, estimated rate")
PKG = {
    # ---- general medicine, per-day (verified HBP 2.0) ----
    "MG001A": ("Acute febrile illness", "General Medicine", "MED", "medical_per_day", 1800, 0, 3, "R50.9", *V20),
    "MG003A": ("Malaria", "General Medicine", "MED", "medical_per_day", 1800, 0, 4, "B54", *V20),
    "MG004A": ("Dengue fever", "General Medicine", "MED", "medical_per_day", 1800, 0, 4, "A90", *V20),
    "MG006A": ("Enteric fever", "General Medicine", "MED", "medical_per_day", 1800, 0, 5, "A01.0", *V20),
    "MG009A": ("Acute gastroenteritis with moderate dehydration", "General Medicine", "MED", "medical_per_day", 1800, 0, 3, "A09", *V20),
    "MG016A": ("Pneumonia", "General Medicine", "MED", "medical_per_day", 1800, 0, 5, "J18.9", *V20),
    "MG017A": ("Severe pneumonia", "General Medicine", "MED", "medical_per_day", 1800, 0, 7, "J18.9", *V20),
    "MG021A": ("Urinary tract infection", "General Medicine", "MED", "medical_per_day", 1800, 0, 4, "N39.0", *V20),
    "MG029A": ("Acute exacerbation of COPD", "General Medicine", "MED", "medical_per_day", 1800, 0, 5, "J44.1", *V20),
    "MG038A": ("Congestive heart failure", "General Medicine", "MED", "medical_per_day", 1800, 0, 6, "I50.0", *V20),
    "MG045A": ("AKI / renal failure", "General Medicine", "MED", "medical_per_day", 1800, 0, 6, "N17.9", *V20),
    "MG049C": ("Acute ischemic stroke", "General Medicine", "MED", "medical_per_day", 1800, 0, 7, "I63.9", *V20),
    "MG059A": ("Diabetic ketoacidosis", "General Medicine", "MED", "medical_per_day", 1800, 0, 5, "E10.1", *V20),
    "MG064A": ("Severe anemia", "General Medicine", "MED", "medical_per_day", 1800, 0, 4, "D64.9", *V20),
    "MG070A": ("Snake bite", "General Medicine", "MED", "medical_per_day", 1800, 0, 5, "T63.0", *V20),
    "MG071A": ("Acute organophosphorus poisoning", "General Medicine", "MED", "medical_per_day", 1800, 0, 6, "T60.0", *V20),
    # ---- dialysis and emergency room (day care) ----
    "MG072D": ("Chronic haemodialysis (per session)", "General Medicine", "DIAL", "daycare", 2000, 0, 0, "N18.5", *V22),
    "ER003A": ("Animal bites (excluding snake bite)", "Emergency Room Packages", "ER", "daycare", 1700, 0, 0, "W54", *V20),
    "ER001A": ("Laceration - suturing / dressing", "Emergency Room Packages", "ER", "daycare", 2000, 0, 0, "T14.1", *V20),
    # ---- general surgery (verified HBP 2.0, Punjab SHA annexure) ----
    "SG017A": ("Appendicectomy - open", "General Surgery", "SURG", "surgical", 11000, 0, 3, "K35.8", *V20),
    "SG039C": ("Cholecystectomy - laparoscopic", "General Surgery", "SURG", "surgical", 22800, 0, 3, "K80.2", *V20),
    "SG050A": ("Groin hernia repair - inguinal - open", "General Surgery", "SURG", "surgical", 14200, 0, 3, "K40.9", *V20),
    "SG051B": ("Hernia - ventral - umbilical", "General Surgery", "SURG", "surgical", 17400, 0, 3, "K42.9", *V20),
    "SG032A": ("Haemorrhoidectomy - without stapler", "General Surgery", "SURG", "surgical", 15000, 0, 2, "K64.9", *V20),
    # ---- orthopaedics (verified HBP 2.0) ----
    "SB010A": ("Fixation of diaphyseal fracture - long bone - ORIF", "Orthopaedics", "ORTHO", "surgical", 14900, 0, 5, "S72.3", *V20),
    "SB019B": ("Fracture neck femur - dynamic hip screw", "Orthopaedics", "ORTHO", "surgical", 15800, 0, 6, "S72.1", *V20),
    "SB014A": ("Fracture both bones forearm - ORIF", "Orthopaedics", "ORTHO", "surgical", 12700, 0, 3, "S52.4", *V20),
    "SB020A": ("Ankle fracture - ORIF", "Orthopaedics", "ORTHO", "surgical", 14000, 0, 4, "S82.6", *V20),
    "SB039": ("Total knee replacement (primary)", "Orthopaedics", "ORTHO", "surgical", 80000, 0, 6, "M17.9", *APX),
    # ---- cardiology (verified HBP 2.0) ----
    "MC011A": ("PTCA, inclusive of diagnostic angiogram", "Cardiology", "CARD", "surgical", 40600, 31600, 3, "I25.1", *V20),
    "MC015A": ("Permanent pacemaker - single chamber", "Cardiology", "CARD", "surgical", 24500, 45000, 3, "I44.2", *V20),
    "MC020A": ("Systemic thrombolysis (for MI)", "Cardiology", "CARD", "surgical", 17900, 0, 4, "I21.9", *V20),
    "MC001B": ("Left heart catheterization", "Cardiology", "CARD", "surgical", 5000, 0, 1, "I25.1", *V20),
    # ---- ophthalmology ----
    "SE020": ("Cataract surgery - phaco with foldable IOL", "Ophthalmology", "EYE", "daycare", 7500, 0, 0, "H25.9", *APX),
    "SE027B": ("Glaucoma surgery (trabeculectomy)", "Ophthalmology", "EYE", "surgical", 11000, 0, 1, "H40.1", *V20),
    # ---- obstetrics and gynaecology ----
    "SO010": ("Hysterectomy - abdominal", "Obstetrics & Gynaecology", "OBGY", "surgical", 20000, 0, 5, "D25.9", *APX),
    "SO057": ("Caesarean delivery", "Obstetrics & Gynaecology", "OBGY", "surgical", 11500, 0, 4, "O82", *APX),
    # ---- oncology (verified HBP 2.0, per cycle) ----
    "MO001I": ("Chemotherapy CA breast - carboplatin + paclitaxel", "Medical Oncology", "ONC", "daycare", 14900, 0, 0, "C50.9", *V20),
    "MO001L": ("Chemotherapy CA breast - cyclophosphamide + adriamycin", "Medical Oncology", "ONC", "daycare", 4500, 0, 0, "C50.9", *V20),
    "MO003G": ("Chemotherapy CA ovary - carboplatin + paclitaxel", "Medical Oncology", "ONC", "daycare", 14700, 0, 0, "C56", *V20),
    "MO006B": ("Chemotherapy cervical cancer - cisplatin", "Medical Oncology", "ONC", "daycare", 2200, 0, 0, "C53.9", *V20),
    # ---- neonatal, burns, ENT ----
    "MN002A": ("Special neonatal care package (per day)", "Neo-natal Care", "NEO", "neonatal_per_day", 3000, 0, 5, "P07.3", *V20),
    "MN003A": ("Intensive neonatal care package (per day)", "Neo-natal Care", "NEO", "neonatal_per_day", 5000, 0, 8, "P22.0", *V20),
    "BM001B": ("Thermal burns - up to 40% TBSA", "Burns Management", "BURN", "surgical", 40000, 0, 10, "T30.2", *V20),
    "SL016": ("Tonsillectomy", "ENT", "ENT", "surgical", 7500, 0, 1, "J35.0", *APX),
}
COLS = ["procedure_name", "specialty", "group", "package_type", "base_rate_inr", "implant_addon_inr",
        "typical_los_days_assumed", "icd10", "rate_source", "hbp_version"]
pkg = pd.DataFrame.from_dict(PKG, orient="index", columns=COLS).rename_axis("package_code").reset_index()
GROUP_CODES = {g: d.package_code.values for g, d in pkg.groupby("group")}
GROUP_W = {"MED": [9, 3, 4, 4, 8, 6, 2, 4, 4, 3, 2, 2, 2, 3, 2, 1], "ER": [4, 1], "SURG": [3, 4, 4, 2, 2],
           "ORTHO": [4, 3, 3, 3, 1], "CARD": [6, 1, 2, 2], "EYE": [12, 1], "OBGY": [2, 8], "ONC": [3, 3, 2, 3]}
P = pkg.set_index("package_code")

# hospital type: (share, sector, beds lo-hi, group weights)
HTYPE = {
    "Nursing Home": (0.34, "private", (10, 35), {"MED": .52, "SURG": .20, "OBGY": .15, "ER": .13}),
    "Multispecialty Hospital": (0.10, "private", (40, 160), {"MED": .36, "SURG": .16, "ORTHO": .10, "OBGY": .09, "ER": .07,
                                                             "DIAL": .14, "CARD": .04, "ENT": .02, "NEO": .02}),
    "Eye Hospital": (0.05, "private", (8, 30), {"EYE": 1.0}),
    "Dialysis Centre": (0.04, "private", (8, 25), {"DIAL": .96, "MED": .04}),
    "Orthopaedic Hospital": (0.04, "private", (15, 60), {"ORTHO": .88, "MED": .12}),
    "Heart Institute": (0.02, "private", (40, 150), {"CARD": .72, "MED": .28}),
    "Cancer Centre": (0.02, "private", (30, 120), {"ONC": .88, "MED": .12}),
    "Community Health Centre": (0.27, "public", (20, 40), {"MED": .68, "ER": .22, "OBGY": .10}),
    "District Hospital": (0.09, "public", (100, 320), {"MED": .40, "SURG": .13, "OBGY": .13, "ER": .10, "ORTHO": .07,
                                                        "NEO": .05, "DIAL": .08, "EYE": .03, "BURN": .01}),
    "Government Medical College": (0.03, "public", (450, 950), {"MED": .30, "SURG": .12, "OBGY": .10, "ER": .06, "ORTHO": .08,
                                                                 "NEO": .05, "DIAL": .10, "CARD": .06, "ONC": .08, "EYE": .03,
                                                                 "BURN": .01, "ENT": .01}),
}
COINED = ["Zentara", "Velora", "Mirava", "Ondira", "Kelvane", "Sorinda", "Tavora", "Ekanta", "Navira", "Prayana",
          "Olvira", "Samvedra", "Ishvara", "Daruna", "Ketaya", "Lumora", "Avanta", "Rivaan", "Yantara", "Udayam",
          "Hridaya", "Niramay", "Sukhada", "Varenya", "Tejora", "Ambara", "Charvi", "Devanta", "Jivanta", "Shubhra"]


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(a))


city_names = list(CITIES)
city_w = np.array([CITIES[c][5] for c in city_names], dtype=float)
city_w /= city_w.sum()
C = pd.DataFrame.from_dict(CITIES, orient="index", columns=["district", "state", "lat", "lon", "tier", "w"])

# -------------------------------------------------------------- hospitals ---
types = list(HTYPE)
type_w = np.array([HTYPE[t][0] for t in types])
h_type = rng.choice(types, N_HOSP, p=type_w / type_w.sum())
h_city = np.concatenate([city_names, rng.choice(city_names, N_HOSP - len(city_names), p=city_w)])
rng.shuffle(h_city)
gmc_slots = np.where(h_type == "Government Medical College")[0]
big = [c for c in city_names if C.at[c, "tier"] != "Z"]
h_city[gmc_slots] = rng.choice(big, len(gmc_slots), replace=False)

beds = np.array([int(rng.integers(*HTYPE[t][2])) for t in h_type])
sector = np.array([HTYPE[t][1] for t in h_type])
nabh = np.where(beds < 40, rng.choice(["none", "entry"], N_HOSP, p=[.93, .07]),
                rng.choice(["none", "entry", "full"], N_HOSP, p=[.62, .23, .15]))
hosp = pd.DataFrame({
    "hospital_id": [f"H{i:03d}" for i in range(1, N_HOSP + 1)],
    "name": [f"{rng.choice(COINED)} {t}, {c}" for t, c in zip(h_type, h_city)],
    "hospital_type": h_type, "sector": sector, "city": h_city,
    "district": C.district[h_city].values, "state": C.state[h_city].values, "city_tier": C.tier[h_city].values,
    "lat": np.round(C.lat[h_city].values + rng.normal(0, 0.03, N_HOSP), 4),
    "lon": np.round(C.lon[h_city].values + rng.normal(0, 0.03, N_HOSP), 4),
    "beds": beds, "nabh_status": nabh,
    "teaching": (h_type == "Government Medical College").astype(int),
    "empanelled_specialties": ["|".join(sorted({P.specialty[GROUP_CODES[g][0]] for g in HTYPE[t][3]})) for t in h_type],
    "empanelment_date": (pd.Timestamp("2018-10-01") + pd.to_timedelta(rng.integers(0, 2300, N_HOSP), unit="D")).date,
    "owner_id": [f"O{i:03d}" if s == "private" else "GOV" for i, s in zip(rng.integers(1, N_OWNERS + 1, N_HOSP), sector)],
    "role": "normal",
}).set_index("hospital_id", drop=False)
hosp["price_mult"] = (hosp.nabh_status.map({"none": 1.0, "entry": 1.10, "full": 1.15})
                      * np.where(hosp.city_tier == "X", 1.10, 1.0) * np.where(hosp.teaching == 1, 1.10, 1.0))
# monthly claims scale with beds; day-care heavy types turn over faster
turn = hosp.hospital_type.map({"Dialysis Centre": 2.6, "Eye Hospital": 1.0, "Cancer Centre": 0.55}).fillna(0.17)
hosp["monthly_rate"] = hosp.beds * turn * rng.lognormal(0, 0.35, N_HOSP)

# ---------------------------------------------------------- beneficiaries ---
fam_size = rng.choice([1, 2, 3, 4, 5, 6, 7], N_BENE, p=[.10, .16, .20, .22, .16, .10, .06])
fam_id, mob, i = [], [], 0
while len(fam_id) < N_BENE:
    i += 1
    k = fam_size[len(fam_id)]
    fam_id += [f"FAM{i:06d}"] * k
    mob += [f"MOB{i:06d}"] * k
fam_id, mob = np.array(fam_id[:N_BENE]), np.array(mob[:N_BENE], dtype=object)
_, fam_idx = np.unique(fam_id, return_inverse=True)
b_city = rng.choice(city_names, fam_idx.max() + 1, p=city_w)[fam_idx]      # a family lives in one place
b_vil = rng.integers(1, 41, fam_idx.max() + 1)[fam_idx]
# innocent look-alike: placeholder numbers typed at enrolment (CAG found lakhs of these)
ph = rng.random(N_BENE)
mob[ph < 0.020] = "9999999999"
mob[(ph >= 0.020) & (ph < 0.026)] = "8888888888"
age = np.clip(np.where(rng.random(N_BENE) < 0.50, rng.normal(58, 11, N_BENE), rng.normal(30, 13, N_BENE)), 1, 95).astype(int)
bene = pd.DataFrame({
    "beneficiary_id": [f"B{i:06d}" for i in range(1, N_BENE + 1)],
    "family_id": fam_id, "age": age, "gender": rng.choice(["F", "M"], N_BENE, p=[.49, .51]),
    "state": C.state[b_city].values, "district": C.district[b_city].values, "city": b_city,
    "village_code": [f"VIL-{c[:3].upper()}-{v:02d}" for c, v in zip(b_city, b_vil)],
    "mobile_token": mob,
    "card_created_date": (pd.Timestamp("2018-10-01") + pd.to_timedelta(rng.integers(0, 2540, N_BENE), unit="D")).date,
    "card_operator_id": [f"OP-{c[:3].upper()}-{v:02d}" for c, v in zip(b_city, rng.integers(1, 13, N_BENE))],
    "death_date": "",
}).set_index("beneficiary_id", drop=False)
bene_by_city = {c: g.beneficiary_id.values for c, g in bene.groupby("city")}
women_by_city = {c: g.beneficiary_id.values for c, g in bene[(bene.gender == "F") & bene.age.between(18, 75)].groupby("city")}
old_by_city = {c: g.beneficiary_id.values for c, g in bene[bene.age >= 50].groupby("city")}
extra_bene = []

# ------------------------------------------------------ assign FWA roles ---
def pick(mask, k):
    pool = hosp.index[mask & (hosp.role == "normal")]
    return list(rng.choice(pool, k, replace=False))


def set_role(ids, role):
    hosp.loc[ids, "role"] = role
    return ids


priv = hosp.sector == "private"
general = hosp.hospital_type.isin(["Nursing Home", "Multispecialty Hospital"])
RING_CITY = "Lucknow"
ring = set_role(pick(priv & general, 5), "collusive_ring")
RING_OWNER = f"O{N_OWNERS + 1:03d}"
for col in ["city", "district", "state", "city_tier"]:
    hosp.loc[ring, col] = RING_CITY if col == "city" else {"district": "Lucknow", "state": "Uttar Pradesh", "city_tier": "Y"}[col]
hosp.loc[ring, "lat"] = np.round(C.at[RING_CITY, "lat"] + rng.normal(0, 0.03, 5), 4)
hosp.loc[ring, "lon"] = np.round(C.at[RING_CITY, "lon"] + rng.normal(0, 0.03, 5), 4)
hosp.loc[ring, "owner_id"] = RING_OWNER
hosp.loc[ring, "name"] = [f"{rng.choice(COINED)} {t}, {RING_CITY}" for t in hosp.loc[ring, "hospital_type"]]

ghosts = set_role(pick(priv & general, 3), "ghost_beneficiary")
overlappers = set_role(pick(priv & general, 3), "overlapping_admission")
deathers = set_role(pick(priv & general, 2), "claim_after_death")
upcoders = set_role(pick(priv & (hosp.hospital_type == "Multispecialty Hospital"), 4), "package_upcoding")
converters = set_role(pick(priv & (hosp.hospital_type == "Nursing Home"), 3), "opd_to_ipd")
hyst = set_role(pick(priv & general, 2), "unnecessary_procedure")
camp = set_role(pick(priv & (hosp.hospital_type == "Heart Institute"), 1), "unnecessary_procedure")
overrun = set_role(pick(priv & (hosp.hospital_type == "Eye Hospital") & (hosp.beds <= 20), 1)
                   + pick(priv & (hosp.hospital_type == "Nursing Home") & (hosp.beds <= 20), 1), "bed_overrun")
dupdocs = set_role(pick(priv & (hosp.hospital_type == "Multispecialty Hospital"), 3), "duplicate_document")
# innocent outliers the model should learn to clear
legit_referral = set_role(pick(hosp.hospital_type == "Government Medical College", 2), "legit_referral_centre")
legit_eye = set_role(pick(hosp.hospital_type == "Eye Hospital", 2), "legit_high_volume_eye")
legit_dial = set_role(pick(hosp.hospital_type == "Dialysis Centre", 2), "legit_dialysis_centre")
hosp.loc[legit_referral, "monthly_rate"] *= 1.8   # runs above sanctioned beds, as public teaching hospitals do
hosp.loc[legit_eye, "monthly_rate"] *= 3.5
hosp.loc[legit_dial, "monthly_rate"] *= 1.6

fwa_ids = ring + ghosts + overlappers + deathers + upcoders + converters + hyst + camp + overrun + dupdocs
month_starts = pd.date_range("2025-12-01", "2026-04-01", freq="MS")
fwa_start = {h: month_starts[rng.integers(0, len(month_starts))] for h in fwa_ids}
for h in ring:
    fwa_start[h] = pd.Timestamp("2026-03-01")

# ------------------------------------------------------- claim machinery ---
TOTAL_MIN = int((END - START).total_seconds() // 60)


def rand_dt(n, lo=START, hi=END):
    span = max(1, int((hi - lo).total_seconds() // 60))
    hour = rng.choice(24, n, p=np.r_[np.full(8, .015), np.full(10, .07), np.full(6, .03)] / (8 * .015 + 10 * .07 + 6 * .03))
    d = lo.normalize() + pd.to_timedelta(rng.integers(0, max(1, span // 1440), n), unit="D")
    return pd.DatetimeIndex(d) + pd.to_timedelta(hour * 60 + rng.integers(0, 60, n), unit="m")


def draw_codes(htype, n):
    groups, gw = zip(*HTYPE[htype][3].items())
    g = rng.choice(groups, n, p=np.array(gw) / sum(gw))
    out = np.empty(n, dtype=object)
    for grp in sorted(set(g)):
        m = g == grp
        codes = GROUP_CODES[grp]
        w = np.array(GROUP_W.get(grp, np.ones(len(codes))), dtype=float)
        out[m] = rng.choice(codes, m.sum(), p=w / w.sum())
    return out


def make_rows(hid, ben, adm, codes, pattern="", ward=None, los=None, agent=""):
    codes = np.asarray(codes, dtype=object)
    n = len(codes)
    ptype = P.package_type[codes].values
    typ = P.typical_los_days_assumed[codes].values
    if los is None:
        los = np.where(typ > 0, np.maximum(1, rng.poisson(np.maximum(typ - 1, 0.1)) + 1), 0)
    if ward is None:
        ward = np.where(ptype == "medical_per_day",
                        rng.choice(list(WARD_RATE), n, p=[.84, .07, .06, .03]),
                        np.where(ptype == "neonatal_per_day", "nicu", np.where(ptype == "daycare", "daycare", "general")))
    return pd.DataFrame({
        "beneficiary_id": np.asarray(ben), "hospital_id": hid, "admission_datetime": pd.DatetimeIndex(adm),
        "package_code": codes, "ward_type": ward, "los_days": np.asarray(los, dtype=int),
        "referred_by_agent_id": agent, "_pattern": pattern,
    })


def price(df):
    code = df.package_code.values
    ptype, base = P.package_type[code].values, P.base_rate_inr[code].values.astype(float)
    mult = hosp.price_mult[df.hospital_id.values].values
    days = np.maximum(df.los_days.values, 1)
    per_day = np.where(ptype == "medical_per_day", df.ward_type.map(WARD_RATE).fillna(0).values, base)
    proc = np.where(np.isin(ptype, ["medical_per_day", "neonatal_per_day"]), per_day * days, base)
    df["units"] = np.where(np.isin(ptype, ["medical_per_day", "neonatal_per_day"]), days, 1)
    df["implant_amount"] = P.implant_addon_inr[code].values
    df["claimed_amount"] = np.round(proc * mult + df.implant_amount, 0)
    cut = np.where(rng.random(len(df)) < 0.12, rng.uniform(0.05, 0.30, len(df)), 0.0)
    df["approved_amount"] = np.round(df.claimed_amount * (1 - cut), 0)
    return df


# ------------------------------------------------------------ base claims ---
frames = []
for hid, h in hosp.iterrows():
    n = max(25, rng.poisson(h.monthly_rate * 12))
    codes = draw_codes(h.hospital_type, n)
    pool = bene_by_city[h.city]
    ben = rng.choice(pool, n)
    # dialysis is a small pool of repeat patients (two to three sessions a week)
    d = codes == "MG072D"
    if d.any():
        patients = rng.choice(old_by_city[h.city], max(3, int(d.sum() // 110) + 1), replace=False)
        ben[d] = rng.choice(patients, d.sum())
    ob = np.isin(codes, ["SO010", "SO057"])
    ben[ob] = rng.choice(women_by_city[h.city], ob.sum())
    onc = np.isin(codes, GROUP_CODES["ONC"])
    if onc.any():
        ben[onc] = rng.choice(rng.choice(pool, max(4, int(onc.sum() // 6) + 1), replace=False), onc.sum())
    port = rng.random(n) < 0.012     # portability: about 1.2% treated outside the home state
    ben[port & ~d] = rng.choice(bene.beneficiary_id.values, (port & ~d).sum())
    agent = np.where(rng.random(n) < 0.15, [f"AG-{h.city[:3].upper()}-{v:02d}" for v in rng.integers(1, 26, n)], "")
    frames.append(make_rows(hid, ben, rand_dt(n), codes, agent=agent))
claims = pd.concat(frames, ignore_index=True)

# hysterectomy baseline age: median about 44; a quarter under 40 is ordinary practice
m = claims.package_code == "SO010"
young = bene.age[claims.loc[m, "beneficiary_id"]].values < 28
claims = claims.drop(claims.index[m][young]).reset_index(drop=True)

# --- pattern: package upcoding (ward billed as ICU), escalating -------------
for hid in upcoders:
    s = fwa_start[hid]
    idx = claims.index[(claims.hospital_id == hid) & (claims.ward_type == "general")
                       & P.package_type[claims.package_code].eq("medical_per_day").values
                       & (claims.admission_datetime >= s)]
    frac = (claims.loc[idx, "admission_datetime"] - s) / (END - s)
    hit = idx[rng.random(len(idx)) < (0.15 + 0.65 * frac.values)]
    claims.loc[hit, "ward_type"] = rng.choice(["icu", "icu_ventilator"], len(hit), p=[.6, .4])
    claims.loc[hit, "_pattern"] = "package_upcoding"

# a person cannot be an inpatient in two places: drop accidental overlaps from the random draw
claims = claims.sort_values(["beneficiary_id", "admission_datetime"]).reset_index(drop=True)
stay_end = claims.admission_datetime.dt.normalize() + pd.to_timedelta(claims.los_days + 1, unit="D")
prev_end = stay_end.where(claims.los_days > 0).groupby(claims.beneficiary_id).cummax().groupby(claims.beneficiary_id).shift()
claims = claims[~((claims.los_days > 0) & (claims.admission_datetime < prev_end))].reset_index(drop=True)

claims = price(claims)
claims["discharge_status"] = "discharged"

# --- natural deaths in hospital: no genuine claim can follow ----------------
inpt = claims.index[(claims.los_days >= 2) & (claims.package_code != "MG072D")]
died = rng.choice(inpt, int(len(inpt) * 0.006), replace=False)
dd = claims.loc[died].assign(dod=lambda x: x.admission_datetime + pd.to_timedelta(x.los_days, unit="D"))
dd = dd.sort_values("dod").drop_duplicates("beneficiary_id")
dod = dd.set_index("beneficiary_id").dod
later = claims.beneficiary_id.map(dod)
keep = later.isna() | (claims.admission_datetime <= later) | claims.index.isin(dd.index)
claims = claims[keep & ~(later.notna() & ~claims.index.isin(dd.index)
                         & (claims.admission_datetime + pd.to_timedelta(claims.los_days, unit="D") > later))]
claims.loc[claims.index.isin(dd.index), "discharge_status"] = "death"
bene.loc[dod.index, "death_date"] = dod.dt.date.astype(str).values
claims = claims.reset_index(drop=True)
extra = []

# --- pattern: claims after recorded death -----------------------------------
for hid in deathers:
    cand = dod[(dod >= fwa_start[hid]) & (dod <= END - pd.Timedelta(days=20))]
    local = cand[bene.city[cand.index].values == hosp.at[hid, "city"]]
    base = local if len(local) >= 6 else cand
    use = base.sample(min(14, len(base)), random_state=int(rng.integers(1e6))) if len(base) else base
    for b, when in use.items():
        k = int(rng.integers(1, 3))
        adm = when + pd.to_timedelta(rng.integers(5, 90, k), unit="D") + pd.to_timedelta(rng.integers(0, 1440, k), unit="m")
        adm = adm[adm <= END]
        if len(adm):
            extra.append(price(make_rows(hid, [b] * len(adm), adm, draw_codes(hosp.at[hid, "hospital_type"], len(adm)),
                                         "claim_after_death")))

# --- pattern: overlapping admission in a second hospital --------------------
for hid in overlappers:
    city = hosp.at[hid, "city"]
    src = claims[(claims.hospital_id != hid) & (claims.los_days >= 3) & (claims.discharge_status == "discharged")
                 & (hosp.city[claims.hospital_id].values == city) & (claims.admission_datetime >= fwa_start[hid])
                 & ~claims.beneficiary_id.isin(dod.index)]
    src = src.sample(min(len(src), int(rng.integers(28, 45))), random_state=int(rng.integers(1e6)))
    adm = src.admission_datetime + pd.to_timedelta(rng.integers(6, 40, len(src)), unit="h")
    codes = rng.choice(GROUP_CODES["MED"], len(src))
    extra.append(price(make_rows(hid, src.beneficiary_id.values, adm.values, codes, "overlapping_admission",
                                 los=rng.integers(2, 6, len(src)))))

# --- pattern: ghost beneficiaries (fresh cards, one operator, shared phone) -
gb = N_BENE
for hid in ghosts:
    city, n_fake = hosp.at[hid, "city"], int(rng.integers(70, 130))
    op = f"OP-{city[:3].upper()}-{int(rng.integers(13, 16)):02d}"
    adm = rand_dt(n_fake, fwa_start[hid], END)
    ids = [f"B{j:06d}" for j in range(gb + 1, gb + n_fake + 1)]
    gb += n_fake
    grp = rng.integers(0, max(3, n_fake // 25), n_fake)
    extra_bene.append(pd.DataFrame({
        "beneficiary_id": ids, "family_id": [f"FAM9{hid[1:]}{g:02d}" for g in grp],
        "age": rng.integers(19, 70, n_fake), "gender": rng.choice(["F", "M"], n_fake),
        "state": C.at[city, "state"], "district": C.at[city, "district"], "city": city,
        "village_code": [f"VIL-{city[:3].upper()}-{int(v):02d}" for v in rng.choice([41, 42], n_fake)],
        "mobile_token": [f"MOB9{hid[1:]}{g:02d}" for g in grp],
        "card_created_date": (adm - pd.to_timedelta(rng.integers(1, 7, n_fake), unit="D")).date,
        "card_operator_id": op, "death_date": "",
    }))
    codes = rng.choice(np.r_[GROUP_CODES["MED"], GROUP_CODES["SURG"]], n_fake)
    extra.append(price(make_rows(hid, ids, adm, codes, "ghost_beneficiary", agent=f"AG-{city[:3].upper()}-9{hid[-1]}")))

# --- pattern: OPD-to-IPD conversion (one-day admissions for minor illness) --
for hid in converters:
    pool = bene_by_city[hosp.at[hid, "city"]]
    for k, ms in enumerate(pd.date_range(fwa_start[hid], END, freq="MS")):
        n = 18 + 6 * k
        fams = bene.family_id[rng.choice(pool, n // 3)].values     # whole families admitted together
        ben = bene.beneficiary_id[bene.family_id.isin(fams)].values
        ben = rng.choice(ben, n) if len(ben) else rng.choice(pool, n)
        codes = rng.choice(["MG001A", "MG009A", "MG021A"], n, p=[.5, .35, .15])
        extra.append(price(make_rows(hid, ben, rand_dt(n, ms, min(ms + pd.offsets.MonthEnd(0), END)), codes,
                                     "opd_to_ipd", ward=np.full(n, "general"), los=np.ones(n, dtype=int))))

# --- pattern: unnecessary hysterectomy in women under 35, after camps -------
for hid in hyst:
    city = hosp.at[hid, "city"]
    w = bene[(bene.city == city) & (bene.gender == "F") & bene.age.between(22, 34)]
    vil = w.village_code.value_counts().index[:4]
    w = w[w.village_code.isin(vil)].beneficiary_id.values
    camps = rand_dt(int(rng.integers(6, 10)), fwa_start[hid], END)
    for cd in camps:
        n = min(len(w), int(rng.integers(5, 10)))
        adm = cd.normalize() + pd.to_timedelta(1, unit="D") + pd.to_timedelta(rng.integers(7 * 60, 13 * 60, n), unit="m")
        extra.append(price(make_rows(hid, rng.choice(w, n, replace=False), adm, ["SO010"] * n, "unnecessary_procedure",
                                     agent=f"AG-{city[:3].upper()}-8{hid[-1]}")))

# --- pattern: camp-to-cath-lab funnel (villagers bussed in, stents next day) -
for hid in camp:
    city = hosp.at[hid, "city"]
    for cd in rand_dt(int(rng.integers(7, 11)), fwa_start[hid], END):
        v = f"VIL-{city[:3].upper()}-{int(rng.integers(1, 41)):02d}"
        pool = bene[(bene.village_code == v) & (bene.age >= 40)].beneficiary_id.values
        n = min(len(pool), int(rng.integers(6, 12)))
        if n < 3:
            continue
        adm = cd.normalize() + pd.to_timedelta(1, unit="D") + pd.to_timedelta(rng.integers(6 * 60, 12 * 60, n), unit="m")
        extra.append(price(make_rows(hid, rng.choice(pool, n, replace=False), adm, ["MC011A"] * n, "unnecessary_procedure",
                                     agent=f"AG-{city[:3].upper()}-7{hid[-1]}")))

# --- pattern: admissions far above bed strength on burst days ---------------
for hid in overrun:
    h = hosp.loc[hid]
    pool = bene_by_city[h.city]
    for bd in rand_dt(int(rng.integers(5, 9)), fwa_start[hid], END):
        n = int(h.beds * rng.uniform(4, 9))
        adm = bd.normalize() + pd.to_timedelta(rng.integers(8 * 60, 18 * 60, n), unit="m")
        codes = ["SE020"] * n if h.hospital_type == "Eye Hospital" else rng.choice(["MG001A", "MG009A", "MG016A"], n)
        extra.append(price(make_rows(hid, rng.choice(pool, n), adm, codes, "bed_overrun")))

# --- pattern: collusive ring (one owner, agent, operator, shared families) --
RING_AGENT, RING_OP = "AG-LUC-99", "OP-LUC-16"
ring_pool = bene[(bene.city == RING_CITY) & bene.village_code.isin(["VIL-LUC-05", "VIL-LUC-06", "VIL-LUC-07"])]
ring_pool = ring_pool.beneficiary_id.values[:95]
bene.loc[ring_pool, "card_operator_id"] = RING_OP
ring_refs = []
for i, hid in enumerate(ring):
    for k, ms in enumerate(pd.date_range(fwa_start[hid], END, freq="MS")):
        n = 22 + 11 * k   # volume grows every month
        rows = price(make_rows(hid, rng.choice(ring_pool, n), rand_dt(n, ms, min(ms + pd.offsets.MonthEnd(0), END)),
                               draw_codes(hosp.at[hid, "hospital_type"], n), "collusive_ring", agent=RING_AGENT))
        extra.append(rows)
        sent = rows[rng.random(n) < 0.5]
        ring_refs.append(pd.DataFrame({
            "from_hospital_id": hid, "to_hospital_id": ring[(i + 1) % len(ring)],
            "beneficiary_id": sent.beneficiary_id.values, "referral_date": sent.admission_datetime.dt.date.values,
        }))

for e in extra:
    e["discharge_status"] = "discharged"
extra = pd.concat(extra, ignore_index=True)
gone = extra.beneficiary_id.map(dod)      # only the claim_after_death pattern may bill for the dead
extra = extra[gone.isna() | (extra.admission_datetime < gone) | (extra._pattern == "claim_after_death")]
claims = pd.concat([claims, extra], ignore_index=True)
claims = claims[claims.admission_datetime <= END].sort_values("admission_datetime").reset_index(drop=True)
claims.insert(0, "claim_id", [f"IC{i:06d}" for i in range(1, len(claims) + 1)])
bene = pd.concat([bene] + extra_bene, ignore_index=True).set_index("beneficiary_id", drop=False)

# derived fields
n = len(claims)
emergency = rng.random(n) < 0.22        # emergencies are pre-authorised after admission
gap_h = np.where(emergency, rng.uniform(0.5, 6, n), -rng.uniform(1, 30, n))
claims["preauth_datetime"] = claims.admission_datetime + pd.to_timedelta(np.round(gap_h * 60), unit="m")
day = P.package_type[claims.package_code].eq("daycare").values
claims["discharge_datetime"] = np.where(
    day, claims.admission_datetime + pd.to_timedelta(rng.integers(3, 9, n), unit="h"),
    claims.admission_datetime.dt.normalize() + pd.to_timedelta(claims.los_days, unit="D")
    + pd.to_timedelta(rng.integers(10 * 60, 17 * 60, n), unit="m"))
claims["discharge_datetime"] = pd.to_datetime(claims.discharge_datetime)
claims["specialty"] = P.specialty[claims.package_code].values
claims["package_type"] = P.package_type[claims.package_code].values
claims["diagnosis_icd10"] = P.icd10[claims.package_code].values
claims["admission_type"] = np.where(emergency, "emergency", "planned")
claims["portability_flag"] = (bene.state[claims.beneficiary_id].values != hosp.state[claims.hospital_id].values).astype(int)
claims["document_hash"] = [f"DOC{v:010x}" for v in rng.choice(16 ** 10, n, replace=False)]
claims["claim_status"] = rng.choice(["paid", "approved_pending_payment", "rejected"], n, p=[.90, .07, .03])

# --- pattern: duplicate documents reused across claims ----------------------
for hid in dupdocs:
    own = claims.index[(claims.hospital_id == hid) & (claims._pattern == "")]
    old = own[claims.loc[own, "admission_datetime"] < fwa_start[hid]]
    new = own[claims.loc[own, "admission_datetime"] >= fwa_start[hid]]
    if len(old) == 0 or len(new) == 0:
        continue
    hit = new[rng.random(len(new)) < 0.30]
    claims.loc[hit, "document_hash"] = rng.choice(claims.loc[old, "document_hash"].values[:12], len(hit))
    claims.loc[hit, "_pattern"] = "duplicate_document"

# -------------------------------------------------------------- referrals ---
ref_frames = []
low = claims[(claims._pattern == "") & hosp.hospital_type[claims.hospital_id].isin(
    ["Community Health Centre", "Nursing Home"]).values]
higher = {c: g.index.values for c, g in hosp[hosp.hospital_type.isin(
    ["District Hospital", "Government Medical College", "Multispecialty Hospital", "Heart Institute", "Cancer Centre"])].groupby("city")}
for hid, g in low.groupby("hospital_id"):
    opts = higher.get(hosp.at[hid, "city"], np.array([]))
    if len(opts) == 0:
        continue
    sent = g[rng.random(len(g)) < 0.06]
    ref_frames.append(pd.DataFrame({
        "from_hospital_id": hid, "to_hospital_id": rng.choice(opts[:6], len(sent)),
        "beneficiary_id": sent.beneficiary_id.values, "referral_date": sent.admission_datetime.dt.date.values,
    }))
referrals = pd.concat(ref_frames + ring_refs, ignore_index=True).sort_values("referral_date").reset_index(drop=True)
referrals.insert(0, "referral_id", [f"IR{i:05d}" for i in range(1, len(referrals) + 1)])

# -------------------------------------------------------------- ownership ---
SUFFIX = ["Healthcare Pvt Ltd", "Medicare LLP", "Hospitals Pvt Ltd", "Health Trust"]
names = list(rng.permutation([f"{w} {s}" for w in COINED for s in SUFFIX])[:N_OWNERS]) + ["Qorvane Lifecare Holdings Pvt Ltd"]
owner_name = {f"O{i:03d}": nm for i, nm in enumerate(names, start=1)}
owner_name["GOV"] = "State Government"
ownership = pd.DataFrame({"owner_id": hosp.owner_id.values, "owner_name": hosp.owner_id.map(owner_name).values,
                          "entity_type": "hospital", "entity_id": hosp.hospital_id.values})

# ---------------------------------------- past investigations (precedents) ---
REASON = {
    ("ghost_beneficiary", "confirmed"): "Cards were created one to six days before admission by a single operator and shared a handful of mobile numbers. Field visit found the listed households did not exist.",
    ("ghost_beneficiary", "cleared"): "Fresh cards belonged to a newly added eligible group enrolled at a government camp. Beneficiaries were traced and confirmed treatment.",
    ("overlapping_admission", "confirmed"): "Beneficiary was shown as admitted here while an inpatient at another hospital. Indoor register had no entry and the patient denied the second admission.",
    ("overlapping_admission", "cleared"): "Overlap was a documented inter-hospital transfer; the first hospital entered the discharge late.",
    ("claim_after_death", "confirmed"): "Claims were raised for a beneficiary recorded as deceased in an earlier claim. No patient was present; documents were fabricated.",
    ("claim_after_death", "cleared"): "Death was recorded against the wrong family member in the earlier claim. The treated patient was alive and verified at home.",
    ("package_upcoding", "confirmed"): "ICU and ventilator per-day rates were billed for patients nursed in the general ward. ICU register and vitals charts did not support critical care.",
    ("package_upcoding", "cleared"): "Higher ICU share explained by a newly commissioned ICU and referrals from nearby health centres. Records supported critical care.",
    ("opd_to_ipd", "confirmed"): "Large numbers of one-day admissions for fever and gastroenteritis, often whole families on the same day. Beneficiaries said they were seen as outpatients and sent home.",
    ("opd_to_ipd", "cleared"): "Short stays occurred during a documented local outbreak. Admission notes and investigations justified observation.",
    ("unnecessary_procedure", "confirmed"): "Procedures clustered the day after village camps on patients with no supporting investigations. Medical audit found no clinical indication.",
    ("unnecessary_procedure", "cleared"): "Procedure volume reflects a visiting specialist's fixed operating days. Histopathology and prior treatment records supported the indication.",
    ("bed_overrun", "confirmed"): "Pre-authorisations on single days were several times the bed strength. Surprise visit found a small fraction of the claimed patients present.",
    ("bed_overrun", "cleared"): "Day-care procedures were counted as admissions; turnover per bed was consistent with a day-care unit.",
    ("duplicate_document", "confirmed"): "The same discharge summary and investigation images were attached to claims for different beneficiaries.",
    ("duplicate_document", "cleared"): "Duplicate images were a portal upload error corrected by the hospital; originals were produced at audit.",
    ("collusive_ring", "confirmed"): "Commonly owned hospitals rotated the same families between them through one agent and one card operator, with no clinical reason for the referrals.",
    ("collusive_ring", "cleared"): "Shared ownership reflects a legitimate hospital group. Referrals followed a documented step-up care pathway.",
    ("excessive_utilization", "confirmed"): "Claims per bed far above peers and not supported by indoor registers.",
    ("excessive_utilization", "cleared"): "Volume far above peers, but the hospital is a regional referral centre, a high-volume eye unit or a dialysis centre with repeat sessions. Registers supported the claims.",
}
INCONCLUSIVE = "Records only partly produced at audit. Evidence insufficient to confirm or clear. Hospital placed on watch."
PATTERNS = sorted({k[0] for k in REASON})
cases = []
for i, hid in enumerate(rng.choice(fwa_ids, 8, replace=False)):
    cases.append((hid, hosp.at[hid, "role"], "confirmed" if i < 5 else "inconclusive"))
for hid in legit_referral + legit_eye + legit_dial[:1]:
    cases.append((hid, "excessive_utilization", "cleared"))
for i, hid in enumerate(rng.choice(hosp.index[hosp.role == "normal"], 27, replace=False)):
    verdict = "cleared" if i < 18 else ("inconclusive" if i < 23 else "confirmed")
    cases.append((hid, rng.choice([p for p in PATTERNS if p != "collusive_ring"]), verdict))
inv = []
for k, (hid, pattern, verdict) in enumerate(cases, start=1):
    opened = pd.Timestamp("2025-01-01") + pd.Timedelta(days=int(rng.integers(0, 270)))
    exposure = float(np.round(rng.lognormal(np.log(900000), 0.8), 0))
    inv.append({
        "case_id": f"INVIN{k:03d}", "hospital_id": hid, "hospital_type": hosp.at[hid, "hospital_type"],
        "state": hosp.at[hid, "state"], "pattern": pattern, "verdict": verdict,
        "reasoning": INCONCLUSIVE if verdict == "inconclusive" else REASON[(pattern, verdict)],
        "exposure_amount_inr": exposure,
        "recovered_amount_inr": round(exposure * rng.uniform(0.4, 0.9), 0) if verdict == "confirmed" else 0.0,
        "opened_date": opened.date(), "closed_date": (opened + pd.Timedelta(days=int(rng.integers(20, 76)))).date(),
    })
investigations = pd.DataFrame(inv).sort_values("closed_date").reset_index(drop=True)

# ----------------------------------------------------------- ground truth ---
NOTE = {
    "legit_referral_centre": "Government medical college running above sanctioned beds: high volume, genuine. Should be cleared.",
    "legit_high_volume_eye": "High-volume cataract unit with day-care turnover: genuine. Should be cleared.",
    "legit_dialysis_centre": "Dialysis centre: few patients, two to three sessions a week each. Should be cleared.",
}
ground_truth = pd.DataFrame({
    "hospital_id": hosp.hospital_id.values, "is_fwa": hosp.hospital_id.isin(fwa_ids).astype(int).values,
    "pattern": hosp.role.values,
    "start_date": [fwa_start[h].date() if h in fwa_start else "" for h in hosp.hospital_id],
    "note": hosp.role.map(NOTE).fillna("").values,
})
claim_labels = claims.loc[claims._pattern != "", ["claim_id", "_pattern"]].rename(columns={"_pattern": "injected_pattern"})

# ------------------------------------------------------------------ write ---
# Same file names and leading columns as the US dataset in data/raw/, so the existing
# pipeline can read either region. India-only fields follow as extra columns.
OUT.mkdir(parents=True, exist_ok=True)
REF.mkdir(parents=True, exist_ok=True)
fmt = "%Y-%m-%d %H:%M"


def pid(s):   # hospital H001 -> provider P001
    return pd.Series(s).astype(str).str.replace("^H", "P", regex=True).values


def fid(s):   # each hospital is its own facility: H001 -> F001
    return pd.Series(s).astype(str).str.replace("^H", "F", regex=True).values


def mid(s):   # beneficiary B000001 -> member M000001
    return pd.Series(s).astype(str).str.replace("^B", "M", regex=True).values


n_claims = claims.groupby("beneficiary_id").size()
chronic = set(claims.beneficiary_id[claims.package_code.isin(["MG072D", *GROUP_CODES["ONC"]])]) | set(n_claims.index[n_claims >= 6])

providers_out = pd.DataFrame({
    "provider_id": pid(hosp.hospital_id), "name": hosp.name.values, "specialty": hosp.hospital_type.values,
    "facility_id": fid(hosp.hospital_id), "owner_id": hosp.owner_id.values, "city": hosp.city.values,
    "lat": hosp.lat.values, "lon": hosp.lon.values,
    "sector": hosp.sector.values, "state": hosp.state.values, "district": hosp.district.values,
    "city_tier": hosp.city_tier.values, "beds": hosp.beds.values, "nabh_status": hosp.nabh_status.values,
    "teaching": hosp.teaching.values, "empanelled_specialties": hosp.empanelled_specialties.values,
    "empanelment_date": hosp.empanelment_date.values,
})
facilities_out = pd.DataFrame({
    "facility_id": fid(hosp.hospital_id), "name": hosp.name.values, "type": hosp.hospital_type.values,
    "city": hosp.city.values, "lat": hosp.lat.values, "lon": hosp.lon.values,
    "state": hosp.state.values, "district": hosp.district.values, "beds": hosp.beds.values,
})
members_out = pd.DataFrame({
    "member_id": mid(bene.beneficiary_id), "age": bene.age.values, "gender": bene.gender.values, "city": bene.city.values,
    "chronic_flag": bene.beneficiary_id.isin(chronic).astype(int).values,
    "family_id": bene.family_id.values, "state": bene.state.values, "district": bene.district.values,
    "village_code": bene.village_code.values, "mobile_token": bene.mobile_token.values,
    "card_created_date": bene.card_created_date.values, "card_operator_id": bene.card_operator_id.values,
    "death_date": bene.death_date.values,
})
cid = claims.claim_id.str.replace("^IC", "C", regex=True)
claims_out = pd.DataFrame({
    "claim_id": cid, "member_id": mid(claims.beneficiary_id), "provider_id": pid(claims.hospital_id),
    "facility_id": fid(claims.hospital_id), "service_datetime": claims.admission_datetime.dt.strftime(fmt),
    "claim_type": claims.package_type, "procedure_code": claims.package_code, "em_level": "",
    "units": claims.units, "billed_amount": claims.claimed_amount, "paid_amount": claims.approved_amount,
    "preauth_datetime": claims.preauth_datetime.dt.strftime(fmt),
    "discharge_datetime": claims.discharge_datetime.dt.strftime(fmt), "los_days": claims.los_days,
    "admission_type": claims.admission_type, "specialty": claims.specialty, "diagnosis_icd10": claims.diagnosis_icd10,
    "ward_type": claims.ward_type, "implant_amount": claims.implant_amount, "claim_status": claims.claim_status,
    "discharge_status": claims.discharge_status, "portability_flag": claims.portability_flag,
    "referred_by_agent_id": claims.referred_by_agent_id, "document_hash": claims.document_hash,
})
referrals_out = pd.DataFrame({
    "referral_id": referrals.referral_id.str.replace("^IR", "R", regex=True),
    "from_provider_id": pid(referrals.from_hospital_id), "to_provider_id": pid(referrals.to_hospital_id),
    "member_id": mid(referrals.beneficiary_id), "referral_date": referrals.referral_date,
})
ownership_out = pd.concat([
    pd.DataFrame({"owner_id": hosp.owner_id.values, "owner_name": hosp.owner_id.map(owner_name).values,
                  "entity_type": "provider", "entity_id": pid(hosp.hospital_id)}),
    pd.DataFrame({"owner_id": hosp.owner_id.values, "owner_name": hosp.owner_id.map(owner_name).values,
                  "entity_type": "facility", "entity_id": fid(hosp.hospital_id)}),
], ignore_index=True)
investigations_out = pd.DataFrame({
    "case_id": investigations.case_id.str.replace("INVIN", "INV", regex=False), "provider_id": pid(investigations.hospital_id),
    "specialty": investigations.hospital_type, "pattern": investigations.pattern, "verdict": investigations.verdict,
    "reasoning": investigations.reasoning, "exposure_amount": investigations.exposure_amount_inr,
    "recovered_amount": investigations.recovered_amount_inr, "opened_date": investigations.opened_date,
    "closed_date": investigations.closed_date, "state": investigations.state,
})
ground_truth_out = ground_truth.rename(columns={"hospital_id": "provider_id"}).assign(provider_id=lambda d: pid(d.provider_id))
claim_labels_out = claim_labels.assign(claim_id=lambda d: d.claim_id.str.replace("^IC", "C", regex=True))
tables = {
    "providers": providers_out, "facilities": facilities_out, "members": members_out, "claims": claims_out,
    "referrals": referrals_out, "ownership": ownership_out, "investigations": investigations_out,
    "ground_truth": ground_truth_out,     # evaluation only - never use as a model feature
    "claim_labels": claim_labels_out,     # evaluation only - never use as a model feature
}
for old in OUT.glob("*.csv"):
    old.unlink()
for name, df in tables.items():
    df.to_csv(OUT / f"{name}.csv", index=False)
    print(f"{name:15s} {len(df):>7,} rows")
pkg.drop(columns="group").to_csv(REF / "package_master.csv", index=False)
pd.DataFrame({"ward_type": list(WARD_RATE), "per_day_rate_inr": list(WARD_RATE.values()),
              "source": "HBP 2.0 / HBP 2.2 manual"}).to_csv(REF / "ward_rates.csv", index=False)
print(f"\nFWA providers (hospitals): {len(fwa_ids)} of {N_HOSP} | injected claims: {len(claim_labels):,} of {len(claims):,}")
print(claim_labels.injected_pattern.value_counts().to_string())
print(f"Average billed amount: Rs {claims.claimed_amount.mean():,.0f}")
print(f"\nWritten to {OUT}")
