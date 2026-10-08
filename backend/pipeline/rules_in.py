"""India (PM-JAY) claim rules. Same output as rules.py: one row per (claim, rule) with a plain-English detail.

A claim is a hospital admission or day-care session billed against a Health Benefit Package, so these
rules police the admission, the beneficiary and the hospital rather than the procedure-code line. They
follow the triggers in the NHA anti-fraud guidebook and audit manual and the validations the CAG audit
(Report 11 of 2023) found missing. Every hit is a lead for audit, never a finding of fraud.
"""
import pandas as pd
from scipy.stats import binom

from backend.region import inr

from . import reference_in as ref
from .common import load

RULES = {
    "overlapping_admission": "IN1 overlapping admission",
    "duplicate_package": "IN2 duplicate package",
    "claim_after_death": "IN3 claim after recorded death",
    "package_mismatch": "IN4a package mismatch",
    "age_audit": "IN4b age audit trigger",
    "ward_upcoding": "IN5 ICU/ventilator rate drift",
    "long_stay": "IN6a stay above assumed package norm",
    "opd_to_ipd": "IN6b OPD-to-IPD short stays",
    "suspicious_identity": "IN7 suspicious beneficiary identity",
    "duplicate_document": "IN8 document reused across beneficiaries",
    "bed_overrun": "IN9a admissions above bed strength",
    "not_empanelled": "IN9b billing outside empanelment",
    "camp_cluster": "IN10 camp-style surgical cluster",
}
SOURCE = {
    "overlapping_admission": "claims.csv: member_id, provider_id, service_datetime, discharge_datetime, claim_type",
    "duplicate_package": "claims.csv: member_id, provider_id, procedure_code, service_datetime",
    "claim_after_death": "claims.csv service_datetime; members.csv death_date",
    "package_mismatch": "claims.csv: procedure_code, diagnosis_icd10, billed_amount; members.csv gender; package_master.csv; providers.csv tier, NABH, teaching",
    "age_audit": "claims.csv procedure_code; members.csv age, gender",
    "ward_upcoding": "claims.csv: ward_type, claim_type, service_datetime, provider_id",
    "long_stay": "claims.csv los_days; package_master.csv typical_los_days_assumed",
    "opd_to_ipd": "claims.csv: procedure_code, los_days, service_datetime",
    "suspicious_identity": "members.csv: card_created_date, mobile_token; claims.csv service_datetime",
    "duplicate_document": "claims.csv: document_hash, member_id",
    "bed_overrun": "claims.csv service_datetime; providers.csv beds",
    "not_empanelled": "claims.csv specialty; providers.csv empanelled_specialties, empanelment_date",
    "camp_cluster": "claims.csv: referred_by_agent_id, procedure_code, service_datetime; members.csv village_code",
}
PLACEHOLDER_MOBILES = {"9999999999", "8888888888"}  # typed against lakhs of cards (CAG); data quality, not a flag alone
WARD = {"icu": "ICU", "icu_ventilator": "ICU with ventilator"}


def _rows(ids, rule, details):
    return pd.DataFrame({"claim_id": list(ids), "rule": rule, "detail": list(details)})


def _dt(x):
    return x.strftime("%d %b %Y %H:%M")


def package_mismatch(c, prov):
    """IN4a: an unknown package code, a diagnosis outside the package's ICD-10 category, a female-only package
    for a man, or an amount above what the hospital's tier and accreditation entitle it to. ICD-10 is compared
    by category (first three characters), so a more specific code such as J18.0 fits a J18.9 package."""
    pk = ref.PACKAGES.reindex(c.procedure_code)
    known = pk.icd10.notna().values
    out = []
    m = ~known
    out.append(_rows(c.claim_id[m], "package_mismatch", [f"Package code {code} is not in the package master" for code in c.procedure_code[m]]))
    dx = c.diagnosis_icd10.fillna("").astype(str).str.strip().str.upper()
    pkg_dx = pk.icd10.fillna("").astype(str).str.upper()
    m = known & (dx != "").values & (dx.str[:3].values != pkg_dx.str[:3].values)
    out.append(_rows(c.claim_id[m], "package_mismatch", [
        f"Diagnosis {d} is outside the ICD-10 category of package {code} ({e})"
        for d, code, e in zip(dx[m], c.procedure_code[m], pkg_dx.values[m])]))
    m = c.procedure_code.isin(ref.FEMALE_ONLY) & c.gender.eq("M")
    out.append(_rows(c.claim_id[m], "package_mismatch", [
        f"Package {code} ({ref.FEMALE_ONLY[code]}) billed for a male beneficiary" for code in c.procedure_code[m]]))
    entitled = ref.entitled_amount(c, prov)
    m = c.billed_amount > entitled + 1
    basis = pk.rate_source.map({"verified": "a published HBP rate"}).fillna("an ESTIMATED package rate, not a verified HBP rate")
    out.append(_rows(c.claim_id[m], "package_mismatch", [
        f"Claimed {inr(b)} for {code}; the hospital's tier and accreditation entitle it to {inr(e)}, using {r}"
        for b, code, e, r in zip(c.billed_amount[m], c.procedure_code[m], entitled[m], basis.values[m])]))
    return out


def ward_drift(c):
    """IN5: ICU or ventilator billed for far more of a hospital's medical per-day admissions than across all
    hospitals. Monthly: 35% or more in a month with 8+ such admissions. Whole period: a binomial test against
    the all-hospital rate, significant after a Bonferroni correction for the hospitals tested (30+ admissions),
    which catches drift at hospitals too small to reach 8 a month. The 35%, 8 and 30 are prototype choices;
    PM-JAY publishes no threshold for this trigger."""
    md = c[c.claim_type == "medical_per_day"].copy()
    if md.empty:
        return []
    md["month"] = md.service_datetime.dt.strftime("%Y-%m")
    md["high"] = md.ward_type.isin(ref.HIGH_WARDS).astype(float)
    peer = md.high.mean()
    sh = md.groupby(["provider_id", "month"]).high.agg(n="size", share="mean").reset_index()
    hit = md.merge(sh[(sh.n >= 8) & (sh.share >= 0.35)], on=["provider_id", "month"])
    hit = hit[hit.high == 1]
    out = [_rows(hit.claim_id, "ward_upcoding", [
        f"{WARD[w]} rate billed; ICU or ventilator was {s:.0%} of "
        f"medical admissions in {mo} vs {peer:.0%} for all hospitals" for w, s, mo in zip(hit.ward_type, hit.share, hit.month)])]
    yr = md.groupby("provider_id").high.agg(n="size", k="sum")
    yr = yr[yr.n >= 30]
    if len(yr) and 0 < peer < 1:
        yr["p"] = binom.sf(yr.k - 1, yr.n, peer)
        sig = yr[yr.p < 0.05 / len(yr)]
        hit = md[md.provider_id.isin(sig.index) & (md.high == 1)]
        out.append(_rows(hit.claim_id, "ward_upcoding", [
            f"{WARD[w]} rate billed; ICU or ventilator was {sig.k[pid] / sig.n[pid]:.0%} of this hospital's "
            f"{sig.n[pid]:.0f} medical admissions over the period vs {peer:.0%} for all hospitals (binomial p = {sig.p[pid]:.0e})"
            for w, pid in zip(hit.ward_type, hit.provider_id)]))
    return out


def empanelment(c, prov):
    """IN9b: a package specialty the hospital is not empanelled for, or an admission before its empanelment date.
    Names are compared ignoring case and spacing. A hospital with no specialty list, or a claim with no specialty,
    is skipped: missing registry data is not a violation."""
    P = prov.set_index("provider_id")
    norm = lambda v: " ".join(str(v).split()).casefold()  # noqa: E731
    lists = P.empanelled_specialties.dropna().map(lambda v: {norm(x) for x in str(v).split("|") if x.strip()})
    lists = lists[lists.map(len) > 0]
    outside = pd.Series([pid in lists.index and pd.notna(sp) and norm(sp) not in lists[pid]
                         for sp, pid in zip(c.specialty, c.provider_id)], index=c.index, dtype=bool)
    start = c.provider_id.map(P.empanelment_date)
    early = (c.service_datetime < start).fillna(False).astype(bool)
    return [
        _rows(c.claim_id[outside], "not_empanelled", [f"{sp} package at a hospital not empanelled for {sp}" for sp in c.specialty[outside]]),
        _rows(c.claim_id[early], "not_empanelled", [
            f"Admitted {_dt(a)}, before the hospital's empanelment on {e:%d %b %Y}" for a, e in zip(c.service_datetime[early], start[early])]),
    ]


def run(claims, prov, members):
    mem = members.set_index("member_id")
    P = prov.set_index("provider_id")
    c = claims.copy()
    for col in ("age", "gender", "death_date", "card_created_date", "mobile_token", "village_code"):
        c[col] = c.member_id.map(mem[col])
    out = []

    # IN1 overlapping admission: admitted while already an inpatient at another hospital, overlap of 24 h or more
    ip = c[c.claim_type != "daycare"].sort_values(["member_id", "service_datetime"])
    g = ip.groupby("member_id")
    prev_id, prev_prov, prev_adm, prev_dis = (g[k].shift() for k in ("claim_id", "provider_id", "service_datetime", "discharge_datetime"))
    hours = (prev_dis - ip.service_datetime).dt.total_seconds() / 3600
    m = prev_prov.notna() & (prev_prov != ip.provider_id) & (hours >= 24)
    out.append(_rows(ip.claim_id[m], "overlapping_admission", [
        f"Admitted {_dt(a)} while an inpatient at {pp} under {pc} (admitted {_dt(pa)}, discharged {_dt(pd_)}); stays overlap by {h:.0f} h"
        for a, pp, pc, pa, pd_, h in zip(ip.service_datetime[m], prev_prov[m], prev_id[m], prev_adm[m], prev_dis[m], hours[m])]))

    # IN2 duplicate package: same inpatient package for the same beneficiary at the same hospital within 7 days
    s = c[c.claim_type != "daycare"].sort_values(["member_id", "procedure_code", "service_datetime"])
    g = s.groupby(["member_id", "procedure_code"])
    prev_id, prev_prov = g.claim_id.shift(), g.provider_id.shift()
    days = (s.service_datetime - g.service_datetime.shift()).dt.total_seconds() / 86400
    m = (prev_prov == s.provider_id) & (days <= 7)
    out.append(_rows(s.claim_id[m], "duplicate_package", [
        f"Package {code} billed again {d:.1f} days after {pc} for the same beneficiary at the same hospital"
        for code, d, pc in zip(s.procedure_code[m], days[m], prev_id[m])]))

    # IN3 claim after recorded death
    m = c.death_date.notna() & (c.service_datetime.dt.normalize() > c.death_date)
    out.append(_rows(c.claim_id[m], "claim_after_death", [
        f"Admitted {_dt(a)}, {(a.normalize() - d).days} days after the beneficiary's recorded death on {d:%d %b %Y}"
        for a, d in zip(c.service_datetime[m], c.death_date[m])]))

    # IN4a package mismatch, IN4b age audit trigger, IN5 ICU/ventilator drift
    out += package_mismatch(c, prov)
    lim = c.procedure_code.map(ref.AGE_AUDIT)
    m = lim.notna() & c.gender.eq("F") & (c.age < lim)
    out.append(_rows(c.claim_id[m], "age_audit", [
        f"{ref.PACKAGES.procedure_name[code]} for a woman aged {a:.0f}; under {l:.0f} is a mandatory audit trigger"
        for code, a, l in zip(c.procedure_code[m], c.age[m], lim[m])]))
    out += ward_drift(c)

    # IN6a stay above the assumed norm: more than twice the typical stay assumed for the package, plus 3 days
    typ = ref.PACKAGES.typical_los_days_assumed.reindex(c.procedure_code).values
    m = c.claim_type.isin(ref.PER_DAY).values & (typ > 0) & (c.los_days.values > 2 * typ + 3)
    out.append(_rows(c.claim_id[m], "long_stay", [
        f"{los} days billed for {code}; the typical stay assumed by this prototype is {t:.0f} days "
        "(PM-JAY publishes no length-of-stay norm)" for los, code, t in zip(c.los_days[m], c.procedure_code[m], typ[m])]))

    # IN6b OPD-to-IPD: 0-1 day admissions are >= 50% of a hospital's fever / gastroenteritis / UTI admissions in a month with 8+
    o = c[c.procedure_code.isin(ref.OPD_TREATABLE)].copy()
    o["month"] = o.service_datetime.dt.strftime("%Y-%m")
    o["short"] = (o.los_days <= 1).astype(float)
    peer = o.short.mean()
    sh = o.groupby(["provider_id", "month"]).short.agg(n="size", share="mean").reset_index()
    hit = o.merge(sh[(sh.n >= 8) & (sh.share >= 0.5)], on=["provider_id", "month"])
    hit = hit[hit.short == 1]
    out.append(_rows(hit.claim_id, "opd_to_ipd", [
        f"{los}-day admission for {ref.OPD_TREATABLE[code]}; such stays were {s:.0%} of these admissions in {mo} vs {peer:.0%} for all hospitals"
        for los, code, s, mo in zip(hit.los_days, hit.procedure_code, hit.share, hit.month)]))

    # IN7 suspicious identity: card created a week or less before admission, or a mobile shared by more beneficiaries than a household
    age = (c.service_datetime.dt.normalize() - c.card_created_date).dt.days
    m = age.between(0, 7)
    out.append(_rows(c.claim_id[m], "suspicious_identity", [
        f"Beneficiary card created {d:%d %b %Y}, {n} days before this admission" for d, n in zip(c.card_created_date[m], age[m])]))
    real = members[~members.mobile_token.isin(PLACEHOLDER_MOBILES)]
    per_mobile = real.groupby("mobile_token").member_id.nunique()
    n_mob = c.mobile_token.map(per_mobile)
    m, household = n_mob > 10, per_mobile[per_mobile <= 10].max()
    out.append(_rows(c.claim_id[m], "suspicious_identity", [
        f"Mobile {t} is registered to {n:.0f} beneficiaries; households here have at most {household}"
        for t, n in zip(c.mobile_token[m], n_mob[m])]))

    # IN8 document reused: the same document hash on claims for different beneficiaries
    n_mem = c.groupby("document_hash").member_id.transform("nunique")
    m = c.document_hash.notna() & (n_mem >= 2)
    out.append(_rows(c.claim_id[m], "duplicate_document", [
        f"Document {h} also attached to claims for {n - 1} other beneficiar{'y' if n == 2 else 'ies'}"
        for h, n in zip(c.document_hash[m], n_mem[m])]))

    # IN9a bed strength: admissions on one day above the hospital's sanctioned beds
    day = c.service_datetime.dt.normalize()
    per_day = c.groupby([c.provider_id, day]).claim_id.transform("size")
    beds = c.provider_id.map(P.beds)
    m = per_day > beds
    out.append(_rows(c.claim_id[m], "bed_overrun", [
        f"{n} admissions on {d:%d %b %Y} at a hospital with {b} beds" for n, d, b in zip(per_day[m], day[m], beds[m])]))

    # IN9b empanelment
    out += empanelment(c, prov)

    # IN10 camp cluster: 3+ agent-referred surgeries for one package from one village, same hospital, same week
    s = c[c.referred_by_agent_id.notna() & (c.claim_type == "surgical")].copy()
    s["week"] = s.service_datetime.dt.to_period("W").dt.start_time
    k = ["provider_id", "referred_by_agent_id", "village_code", "procedure_code", "week"]
    s["n"] = s.groupby(k).claim_id.transform("size")
    s = s[s.n >= 3]
    out.append(_rows(s.claim_id, "camp_cluster", [
        f"{n} {ref.PACKAGES.procedure_name.get(code, code)} admissions from village {v} referred by agent {a} in the week of {w:%d %b %Y}"
        for n, code, v, a, w in zip(s.n, s.procedure_code, s.village_code, s.referred_by_agent_id, s.week)]))

    flags = pd.concat(out, ignore_index=True).drop_duplicates(["claim_id", "rule"])
    cols = ["claim_id", "provider_id", "member_id", "facility_id", "procedure_code",
            "paid_amount", "billed_amount", "service_datetime"]
    return flags.merge(claims[cols], on="claim_id")



if __name__ == "__main__":
    from backend import region
    with region.use("in"):
        flags = run(load("claims"), load("providers"), load("members"))
        print(flags.rule.value_counts().to_string())
