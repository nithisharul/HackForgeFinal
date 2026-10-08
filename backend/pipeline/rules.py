"""Claim-level rules. Returns one row per (claim, rule) with a plain-English detail."""
import pandas as pd

from .common import PROC, haversine_km, load
from .reference import MUE_LIMITS, PTP_EDITS

RULES = {
    "duplicate_billing": "R1 duplicate claim",
    "impossible_timing": "R2 impossible travel",
    "unbundling": "R3 bundling edit pair (PTP)",
    "mue_exceeded": "R4 unit limit (MUE)",
    "upcoding": "R5 visit-level drift",
}


def run(claims, fac):
    out = []
    c = claims.sort_values(["provider_id", "service_datetime"]).reset_index(drop=True)

    # R1 duplicate billing: same member, provider, code and amount within 3 days
    key = ["member_id", "provider_id", "procedure_code", "billed_amount"]
    gap = c.service_datetime - c.groupby(key).service_datetime.shift()
    hit = c[gap <= pd.Timedelta(days=3)]
    mins = gap[hit.index].dt.total_seconds() / 60
    out.append(pd.DataFrame({
        "claim_id": hit.claim_id.values, "rule": "duplicate_billing",
        "detail": [f"Same member, code and amount billed {m:.0f} min earlier" if m < 1440
                   else f"Same member, code and amount billed {m / 1440:.0f} day(s) earlier" for m in mins],
    }))

    # R2 impossible timing: same provider at two facilities 100+ km apart within 60 min
    f = fac.set_index("facility_id")
    lat, lon = c.facility_id.map(f.lat), c.facility_id.map(f.lon)
    g = c.groupby("provider_id")
    prev_fac, prev_id = g.facility_id.shift(), g.claim_id.shift()
    gap_min = (c.service_datetime - g.service_datetime.shift()).dt.total_seconds() / 60
    dist = haversine_km(lat, lon, lat.groupby(c.provider_id).shift(), lon.groupby(c.provider_id).shift())
    m = prev_fac.notna() & (prev_fac != c.facility_id) & (gap_min <= 60) & (dist > 100)
    detail = [f"Billed at {a} and {b}, {d:.0f} km apart, within {t:.0f} min"
              for a, b, d, t in zip(prev_fac[m], c.facility_id[m], dist[m], gap_min[m])]
    for ids in (c.claim_id[m], prev_id[m]):
        out.append(pd.DataFrame({"claim_id": ids.values, "rule": "impossible_timing", "detail": detail}))

    # R3 unbundling: column-2 code billed with its column-1 code, same member/provider/date
    c["service_date"] = c.service_datetime.dt.date
    k = ["member_id", "provider_id", "service_date"]
    used = set(c.procedure_code.unique())
    edits = pd.DataFrame([e for e in PTP_EDITS if e[0] in used and e[1] in used], columns=["col1", "col2", "ind"])
    g = c[k + ["claim_id", "procedure_code"]]
    j = g.merge(g, on=k, suffixes=("_1", "_2"))
    j = j[j.procedure_code_1 != j.procedure_code_2].merge(
        edits, left_on=["procedure_code_1", "procedure_code_2"], right_on=["col1", "col2"])
    how = {0: "never separately payable", 1: "payable only with a supported modifier"}
    out.append(pd.DataFrame({
        "claim_id": j.claim_id_2.values, "rule": "unbundling",
        "detail": [f"{b} billed with {a} on the same date; {b} is included in {a}"
                   + (f" ({how[i]})" if i in how else "") for a, b, i in zip(j.col1, j.col2, j.ind)],
    }))

    # R4 unit limit: units for one member/provider/code/date above the limit
    lim = c.procedure_code.map(MUE_LIMITS)
    cum = c.groupby(k + ["procedure_code"]).units.cumsum()
    hit = c[cum > lim]
    out.append(pd.DataFrame({
        "claim_id": hit.claim_id.values, "rule": "mue_exceeded",
        "detail": [f"{u} units of {code} for one member on one date; limit is {int(l)}"
                   for u, code, l in zip(cum[hit.index], hit.procedure_code, lim[hit.index])],
    }))

    # R5 upcoding: level-5 share of office visits >= 35% in a month with 10+ visits
    em = c[c.em_level.notna()].copy()
    em["month"] = em.service_datetime.dt.strftime("%Y-%m")
    em["is5"] = (em.em_level == 5).astype(float)
    peer = em.is5.mean()
    s = em.groupby(["provider_id", "month"]).is5.agg(n="size", share="mean").reset_index()
    hit = em.merge(s[(s.n >= 10) & (s.share >= 0.35)], on=["provider_id", "month"])
    hit = hit[hit.em_level == 5]
    out.append(pd.DataFrame({
        "claim_id": hit.claim_id.values, "rule": "upcoding",
        "detail": [f"Level 5 was {sh:.0%} of office visits in {mo} vs {peer:.0%} for all providers"
                   for sh, mo in zip(hit.share, hit.month)],
    }))

    flags = pd.concat(out, ignore_index=True).drop_duplicates(["claim_id", "rule"])
    cols = ["claim_id", "provider_id", "member_id", "facility_id", "procedure_code",
            "paid_amount", "billed_amount", "service_datetime"]
    return flags.merge(claims[cols], on="claim_id")


if __name__ == "__main__":
    flags = run(load("claims"), load("facilities"))
    PROC.mkdir(parents=True, exist_ok=True)
    flags.to_csv(PROC / "claim_flags.csv", index=False)
    print(flags.rule.value_counts().to_string())
