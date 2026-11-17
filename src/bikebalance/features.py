"""Feature engineering on the SSOT. Every feature is available at forecast time t
(start of the target hour): calendar of the target hour, weather observed in the
previous hour, and departures up to the previous hour. Encodings are fit on
training data only."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C

WEATHER_RAW = ["temp_c", "rel_humidity", "precip_mm", "wind_speed_mps", "pressure_hpa", "weather_code"]

STATION_F = ["station_mean", "lat", "lon", "region_code", "recovered"]
CAL_F = ["hour_of_day", "hour_sin", "hour_cos", "dow", "is_weekend", "is_holiday"]
WEATHER_F = ["w_temp_c", "w_rel_humidity", "w_precip_mm", "w_wind_speed_mps", "w_pressure_hpa",
             "w_weather_code", "w_rain_flag", "w_precip_3h"]
LAG_F = ["lag_1", "lag_2", "lag_3", "lag_24", "lag_168", "roll_24", "roll_168", "arr_lag_1"]

FEATURE_SETS = {
    "S": STATION_F,                                   # station-only
    "SC": STATION_F + CAL_F,                          # + calendar
    "SCW": STATION_F + CAL_F + WEATHER_F,             # + available weather
    "SCL": STATION_F + CAL_F + LAG_F,                 # + past demand
    "SCWL": STATION_F + CAL_F + WEATHER_F + LAG_F,    # full
}


def load_ssot() -> pd.DataFrame:
    return pd.read_parquet(C.SSOT_PATH)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["station_id", "hour"]).reset_index(drop=True)
    train = df["split"] == "train"

    # station encodings (train only)
    smean = df[train].groupby("station_id")["departures"].mean()
    df["station_mean"] = df["station_id"].map(smean).fillna(df.loc[train, "departures"].mean())
    regions = sorted(df["region"].astype(str).unique())
    df["region_code"] = df["region"].astype(str).map({r: i for i, r in enumerate(regions)}).astype("int8")

    # calendar
    df["hour_sin"] = np.sin(2 * np.pi * df["hour_of_day"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour_of_day"] / 24)

    # weather observed one hour earlier (forecast-time available)
    w = df[["hour"] + WEATHER_RAW].drop_duplicates("hour").sort_values("hour").set_index("hour")
    wl = w.shift(1)
    wl["rain_flag"] = (wl["precip_mm"] > 0).astype(float)
    wl["precip_3h"] = w["precip_mm"].shift(1).rolling(3, min_periods=1).sum()
    wl.columns = ["w_" + c for c in wl.columns]
    df = df.merge(wl, left_on="hour", right_index=True, how="left", validate="many_to_one")

    # past-departure lags (panel is hour-contiguous within each station's window)
    g = df.groupby("station_id", sort=False)["departures"]
    for k in (1, 2, 3, 24, 168):
        df[f"lag_{k}"] = g.shift(k)
    df["roll_24"] = g.transform(lambda s: s.shift(1).rolling(24, min_periods=1).mean())
    df["roll_168"] = g.transform(lambda s: s.shift(1).rolling(168, min_periods=1).mean())
    df["arr_lag_1"] = df.groupby("station_id", sort=False)["arrivals"].shift(1)
    return df


def impute_fit(df: pd.DataFrame, cols: list[str]) -> dict:
    """Training-only imputation values (station mean for lags, column median otherwise)."""
    train = df[df["split"] == "train"]
    return {c: float(train[c].median()) for c in cols}


def impute_apply(X: pd.DataFrame, med: dict) -> pd.DataFrame:
    X = X.copy()
    for c in X.columns:
        if X[c].isna().any():
            if c.startswith(("lag_", "roll_", "arr_lag")) and "station_mean" in X:
                X[c] = X[c].fillna(X["station_mean"])
            X[c] = X[c].fillna(med.get(c, 0.0))
    return X
