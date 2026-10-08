"""Provider-level anomaly detection: Isolation Forest + isotonic calibration.

The Isolation Forest is unsupervised. Its raw score is then mapped to a
probability with isotonic regression. Calibration needs outcomes; here the
outcomes are the injected synthetic labels (data/raw/ground_truth.csv), standing
in for an audited sample of SIU verdicts. Reported metrics are cross-fitted.
"""
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold

from .common import MODELS

FEATS = ["z_claims_per_member", "z_avg_paid", "z_total_paid", "z_level5_share", "z_growth", "n_facilities"]
LABEL = {
    "z_claims_per_member": "claims per member", "z_avg_paid": "average paid per claim",
    "z_total_paid": "total paid", "z_level5_share": "share of level-5 visits",
    "z_growth": "90-day volume growth", "n_facilities": "number of billing facilities",
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


def run(claims, prov, labels=None, train=False):
    f = features(claims, prov)
    X = f[FEATS].values
    MODELS.mkdir(parents=True, exist_ok=True)
    mpath, cpath = MODELS / "isolation_forest.joblib", MODELS / "anomaly_calibrator.joblib"
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
        (MODELS / "anomaly_metrics.json").write_text(json.dumps(metrics, indent=2))
    mfile = MODELS / "anomaly_metrics.json"
    metrics = json.loads(mfile.read_text()) if mfile.exists() else {}
    f["p_anomaly"] = joblib.load(cpath).predict(raw)

    z = f[FEATS[:-1]]
    f["drivers"] = [
        "; ".join(f"{LABEL[c]} {v:+.1f} SD vs specialty peers" for c, v in row.sort_values(ascending=False).head(2).items() if v > 1)
        for _, row in z.iterrows()
    ]
    return f.reset_index(), metrics
