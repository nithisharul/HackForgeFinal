from pathlib import Path

import numpy as np
import pandas as pd

from backend import region

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
KNOW = ROOT / "knowledge"
MODELS = ROOT / "backend" / "models"
DATES = ("service_datetime", "preauth_datetime", "discharge_datetime", "card_created_date", "death_date",
         "empanelment_date")


def load(name):
    """Read one raw table of the active region (see backend/region.py)."""
    df = pd.read_csv(region.current().raw / f"{name}.csv", dtype={"procedure_code": str})
    for col in DATES:
        if col in df:
            df[col] = pd.to_datetime(df[col])
    return df


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(a))
