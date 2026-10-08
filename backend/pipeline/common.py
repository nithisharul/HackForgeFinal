from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
KNOW = ROOT / "knowledge"
MODELS = ROOT / "backend" / "models"


def load(name):
    df = pd.read_csv(RAW / f"{name}.csv", dtype={"procedure_code": str})
    if "service_datetime" in df:
        df["service_datetime"] = pd.to_datetime(df["service_datetime"])
    return df


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(a))
