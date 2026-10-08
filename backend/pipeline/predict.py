"""30/60/90-day risk of repeat or escalating FWA.

Rolling-window design: at each monthly snapshot date T, features describe the
provider's previous 90 days (volume, flags, velocity). The target is whether the
provider gets 3 or more rule flags in the next 30, 60 or 90 days. Targets come
from the rule engine, never from the injected ground-truth labels.
"""
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import GroupKFold, cross_val_predict

from .common import MODELS

HORIZONS = [30, 60, 90]
FEATS = ["n90", "n30", "paid90", "flags90", "flags30", "flagged_paid90", "flag_rate90", "level5_share90",
         "n_facilities90", "volume_velocity", "flag_velocity", "prior_confirmed"]


def snapshot(claims, T, providers, prior):
    c = claims[(claims.service_datetime < T) & (claims.service_datetime >= T - pd.Timedelta(days=90))]
    r = c[c.service_datetime >= T - pd.Timedelta(days=30)]
    g, gr = c.groupby("provider_id"), r.groupby("provider_id")
    f = pd.DataFrame({
        "n90": g.size(), "paid90": g.paid_amount.sum(), "flags90": g.flagged.sum(),
        "flagged_paid90": g.flagged_paid.sum(), "level5_share90": g.is5.mean(),
        "n_facilities90": g.facility_id.nunique(),
    }).reindex(providers).fillna(0)
    f["n30"] = gr.size().reindex(providers).fillna(0)
    f["flags30"] = gr.flagged.sum().reindex(providers).fillna(0)
    f["flag_rate90"] = f.flags90 / (f.n90 + 1)
    f["volume_velocity"] = (3 * f.n30 + 3) / (f.n90 + 3)      # >1 means the last 30 days ran hotter
    f["flag_velocity"] = (3 * f.flags30 + 1) / (f.flags90 + 1)
    f["prior_confirmed"] = f.index.isin(prior).astype(int)
    return f[FEATS]


def run(claims, flags, inv, train=False):
    claims = claims.copy()
    claims["flagged"] = claims.claim_id.isin(flags.claim_id).astype(int)
    claims["flagged_paid"] = claims.paid_amount * claims.flagged
    claims["is5"] = (claims.em_level == 5).astype(float)
    providers = sorted(claims.provider_id.unique())
    prior = set(inv[inv.verdict == "confirmed"].provider_id)
    end = claims.service_datetime.max().normalize() + pd.Timedelta(days=1)
    MODELS.mkdir(parents=True, exist_ok=True)
    mfile = MODELS / "risk_metrics.json"

    if train or not all((MODELS / f"risk_{h}d.joblib").exists() for h in HORIZONS):
        snaps = [T for T in pd.date_range(claims.service_datetime.min().normalize() + pd.Timedelta(days=90),
                                           end - pd.Timedelta(days=90), freq="MS")]
        X = pd.concat([snapshot(claims, T, providers, prior).assign(T=T) for T in snaps])
        groups = X.index.values
        metrics = {"training_snapshots": [str(t.date()) for t in snaps], "training_rows": int(len(X))}
        for h in HORIZONS:
            y = np.concatenate([
                (claims[(claims.service_datetime >= T) & (claims.service_datetime < T + pd.Timedelta(days=h))]
                 .groupby("provider_id").flagged.sum().reindex(providers).fillna(0) >= 3).astype(int).values
                for T in snaps])
            model = GradientBoostingClassifier(n_estimators=150, max_depth=3, learning_rate=0.05, random_state=0)
            oof = cross_val_predict(model, X[FEATS], y, groups=groups, cv=GroupKFold(5), method="predict_proba")[:, 1]
            metrics[f"{h}d"] = {"positives": int(y.sum()), "auc_cv": round(float(roc_auc_score(y, oof)), 3),
                                "avg_precision_cv": round(float(average_precision_score(y, oof)), 3)}
            joblib.dump(model.fit(X[FEATS], y), MODELS / f"risk_{h}d.joblib")
        mfile.write_text(json.dumps(metrics, indent=2))

    now = snapshot(claims, end, providers, prior)
    out = pd.DataFrame({"provider_id": providers})
    for h in HORIZONS:
        out[f"p{h}"] = joblib.load(MODELS / f"risk_{h}d.joblib").predict_proba(now[FEATS])[:, 1]
    out[["p30", "p60", "p90"]] = np.maximum.accumulate(out[["p30", "p60", "p90"]].values, axis=1).round(4)
    out["volume_velocity"] = now.volume_velocity.values.round(2)
    out["flag_velocity"] = now.flag_velocity.values.round(2)
    return out, json.loads(mfile.read_text())
