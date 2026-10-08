"""Provider-level anomaly detection: Isolation Forest + isotonic calibration.

The Isolation Forest is unsupervised. Its raw score is then mapped to a
probability with isotonic regression. Calibration needs outcomes; here the
outcomes are the injected synthetic labels (data/raw/ground_truth.csv), standing
in for an audited sample of SIU verdicts. Reported metrics are cross-fitted.

India uses its own features (admissions per bed, ICU share, short stays, new cards, agents and so on),
peer groups by hospital type, and its own model files in backend/models/india/.
"""
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold

from backend import region

FEATS = ["z_claims_per_member", "z_avg_paid", "z_total_paid", "z_level5_share", "z_growth", "n_facilities"]
LABEL = {
    "z_claims_per_member": "claims per member", "z_avg_paid": "average paid per claim",
    "z_total_paid": "total paid", "z_level5_share": "share of level-5 visits",
    "z_growth": "90-day volume growth", "n_facilities": "number of billing facilities",
}
FEATS_IN = ["z_claims_per_member", "z_avg_paid", "z_total_paid", "z_growth", "z_claims_per_bed", "z_peak_per_bed",
            "z_icu_share", "z_short_stay_share", "z_surgical_share", "z_rejected_share", "z_odd_hour_share",
            "z_new_card_share", "z_agent_share", "z_mortality"]
LABEL_IN = {
    "z_claims_per_member": "admissions per beneficiary", "z_avg_paid": "average paid per admission",
    "z_total_paid": "total paid", "z_growth": "90-day volume growth", "z_claims_per_bed": "admissions per bed",
    "z_peak_per_bed": "busiest day's admissions per bed", "z_icu_share": "share of ICU or ventilator stays",
    "z_short_stay_share": "share of 0-1 day medical stays", "z_surgical_share": "share of surgical packages",
    "z_rejected_share": "share of rejected claims", "z_odd_hour_share": "share of pre-authorisations between midnight and 5 am",
    "z_new_card_share": "share of beneficiaries with cards under 30 days old", "z_agent_share": "share of agent-referred admissions",
    "z_mortality": "in-hospital mortality",
}


def features(claims, prov):
    g = claims.groupby("provider_id")
    f = pd.DataFrame({
        "n_claims": g.size(), "n_members": g.member_id.nunique(),
        "total_paid": g.paid_amount.sum(), "avg_paid": g.paid_amount.mean(),
        "n_facilities": g.facility_id.nunique(),
    })
    f["claims_per_member"] = f.n_claims / f.n_members
    em = claims[claims.em_level.notna()]
    f["level5_share"] = (em.em_level == 5).groupby(em.provider_id).mean()
    f["level5_share"] = f.level5_share.fillna(0)
    end = claims.service_datetime.max()
    recent = claims[claims.service_datetime > end - pd.Timedelta(days=90)].groupby("provider_id").size()
    prior = claims[(claims.service_datetime <= end - pd.Timedelta(days=90))
                   & (claims.service_datetime > end - pd.Timedelta(days=180))].groupby("provider_id").size()
    f["growth"] = (recent.reindex(f.index).fillna(0) + 5) / (prior.reindex(f.index).fillna(0) + 5)
    f["specialty"] = prov.set_index("provider_id").specialty
    f["log_paid"] = np.log1p(f.total_paid)
    for src, dst in [("claims_per_member", "z_claims_per_member"), ("avg_paid", "z_avg_paid"),
                     ("log_paid", "z_total_paid"), ("level5_share", "z_level5_share"), ("growth", "z_growth")]:
        grp = f.groupby("specialty")[src]
        f[dst] = ((f[src] - grp.transform("median")) / (grp.transform("std") + 1e-6)).clip(-10, 10).fillna(0)
    return f


def features_in(claims, prov, members):
    """India: one row per hospital, z-scored against hospitals of the same type."""
    P = prov.set_index("provider_id")
    g = claims.groupby("provider_id")
    f = pd.DataFrame({
        "n_claims": g.size(), "n_members": g.member_id.nunique(),
        "total_paid": g.paid_amount.sum(), "avg_paid": g.paid_amount.mean(),
        "n_facilities": g.facility_id.nunique(),
    })
    f["claims_per_member"] = f.n_claims / f.n_members
    end = claims.service_datetime.max()
    recent = claims[claims.service_datetime > end - pd.Timedelta(days=90)].groupby("provider_id").size()
    prior = claims[(claims.service_datetime <= end - pd.Timedelta(days=90))
                   & (claims.service_datetime > end - pd.Timedelta(days=180))].groupby("provider_id").size()
    f["growth"] = (recent.reindex(f.index).fillna(0) + 5) / (prior.reindex(f.index).fillna(0) + 5)
    beds = P.beds.reindex(f.index)
    f["claims_per_bed"] = f.n_claims / beds
    f["peak_per_bed"] = claims.groupby(["provider_id", claims.service_datetime.dt.normalize()]).size().groupby(level=0).max() / beds
    med = claims[claims.claim_type == "medical_per_day"]
    f["icu_share"] = med.ward_type.isin(["icu", "icu_ventilator"]).groupby(med.provider_id).mean()
    f["short_stay_share"] = (med.los_days <= 1).groupby(med.provider_id).mean()
    f["surgical_share"] = (claims.claim_type == "surgical").groupby(claims.provider_id).mean()
    f["rejected_share"] = (claims.claim_status == "rejected").groupby(claims.provider_id).mean()
    f["odd_hour_share"] = (claims.preauth_datetime.dt.hour < 5).groupby(claims.provider_id).mean()
    card = claims.member_id.map(members.set_index("member_id").card_created_date)
    f["new_card_share"] = ((claims.service_datetime - card).dt.days < 30).groupby(claims.provider_id).mean()
    f["agent_share"] = claims.referred_by_agent_id.notna().groupby(claims.provider_id).mean()
    f["mortality"] = (claims.discharge_status == "death").groupby(claims.provider_id).mean()
    f = f.fillna(0)
    f["specialty"] = P.specialty
    f["log_paid"] = np.log1p(f.total_paid)
    for src in ["claims_per_member", "avg_paid", "log_paid", "growth", "claims_per_bed", "peak_per_bed", "icu_share",
                "short_stay_share", "surgical_share", "rejected_share", "odd_hour_share", "new_card_share",
                "agent_share", "mortality"]:
        dst = "z_total_paid" if src == "log_paid" else f"z_{src}"
        grp = f.groupby("specialty")[src]
        f[dst] = ((f[src] - grp.transform("median")) / (grp.transform("std") + 1e-6)).clip(-10, 10).fillna(0)
    return f


def run(claims, prov, labels=None, train=False, members=None):
    india = region.current().code == "in"
    f = features_in(claims, prov, members) if india else features(claims, prov)
    feats, label = (FEATS_IN, LABEL_IN) if india else (FEATS, LABEL)
    X = f[feats].values
    models = region.current().models
    models.mkdir(parents=True, exist_ok=True)
    mpath, cpath = models / "isolation_forest.joblib", models / "anomaly_calibrator.joblib"
    metrics = {}
    if train or not mpath.exists():
        joblib.dump(IsolationForest(n_estimators=300, random_state=0).fit(X), mpath)
    raw = -joblib.load(mpath).score_samples(X)
    f["anomaly_raw"] = raw

    if (train or not cpath.exists()) and labels is not None:
        y = labels.set_index("provider_id").is_fwa.reindex(f.index).values
        oof = np.zeros(len(y))
        for tr, te in StratifiedKFold(5, shuffle=True, random_state=0).split(raw, y):
            oof[te] = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(raw[tr], y[tr]).predict(raw[te])
        metrics = {"anomaly_auc": round(float(roc_auc_score(y, raw)), 3),
                   "anomaly_brier_calibrated_cv": round(float(brier_score_loss(y, oof)), 4),
                   "anomaly_brier_base_rate": round(float(brier_score_loss(y, np.full(len(y), y.mean()))), 4)}
        joblib.dump(IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(raw, y), cpath)
        (models / "anomaly_metrics.json").write_text(json.dumps(metrics, indent=2))
    mfile = models / "anomaly_metrics.json"
    metrics = json.loads(mfile.read_text()) if mfile.exists() else {}
    f["p_anomaly"] = joblib.load(cpath).predict(raw)

    z = f[feats if india else FEATS[:-1]]
    peers = "hospital-type peers" if india else "specialty peers"
    f["drivers"] = [
        "; ".join(f"{label[c]} {v:+.1f} SD vs {peers}" for c, v in row.sort_values(ascending=False).head(2).items() if v > 1)
        for _, row in z.iterrows()
    ]
    return f.reset_index(), metrics
