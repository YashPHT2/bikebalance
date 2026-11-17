"""ETL: raw trips/stations/weather -> versioned station-hour SSOT table.

Steps (each with an audit check):
1. Load raw CSVs (download from Hugging Face if missing).
2. Weather: local-time DST artefacts -> duplicate fall-back hour averaged,
   missing spring-forward hour interpolated. Result: one row per wall-clock hour.
3. Station registry: standardise IDs; stations used by trips but absent from the
   registry are recovered from median trip coordinates and flagged.
4. Trips: floor start/end to hour, flag unmatched origins (retained, not dropped).
5. Aggregate departures/arrivals per station-hour; zero-fill only inside each
   station's active window (first..last observed trip).
6. Join weather many-to-one on hour (validated), add calendar features.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import config as C


def download_raw(force: bool = False) -> None:
    from huggingface_hub import hf_hub_download

    for f in C.RAW_FILES:
        if force or not (C.DATA_RAW / f).exists():
            hf_hub_download(C.HF_REPO, f, repo_type="dataset", local_dir=str(C.DATA_RAW))


def load_raw():
    download_raw()
    trips = pd.read_csv(C.DATA_RAW / "trips.csv", parse_dates=["start_time", "end_time"])
    stations = pd.read_csv(C.DATA_RAW / "stations.csv")
    weather = pd.read_csv(C.DATA_RAW / "weather.csv", parse_dates=["timestamp"])
    return trips, stations, weather


def clean_weather(weather: pd.DataFrame, audit: dict) -> pd.DataFrame:
    w = weather.copy()
    dup = w["timestamp"].duplicated(keep=False)
    audit["weather_duplicate_timestamps"] = w.loc[dup, "timestamp"].astype(str).unique().tolist()
    num = [c for c in w.columns if c != "timestamp"]
    w = w.groupby("timestamp", as_index=False)[num].mean()
    w["weather_code"] = w["weather_code"].round()
    full = pd.date_range(w["timestamp"].min(), w["timestamp"].max(), freq="h")
    missing = full.difference(w["timestamp"])
    audit["weather_missing_hours"] = [str(x) for x in missing]
    w = w.set_index("timestamp").reindex(full)
    w["weather_imputed"] = w["temp_c"].isna().astype(int)
    w[num] = w[num].interpolate(limit=3)
    w.index.name = "hour"
    audit["weather_rows_clean"] = int(len(w))
    audit["weather_timezone_inference"] = (
        "Duplicate hour on 2024-11-03 01:00 and missing 2024-03-10 02:00 match US DST "
        "transitions, so weather is in local time (America/Los_Angeles), same as trips."
    )
    return w.reset_index()


def build_station_registry(trips: pd.DataFrame, stations: pd.DataFrame, audit: dict) -> pd.DataFrame:
    s = stations.copy()
    s["station_id"] = s["station_id"].astype(int)
    s["recovered"] = 0
    s["region_missing"] = s["region"].isna().astype(int)
    used = set(trips["start_station"]).union(trips["end_station"])
    missing_ids = sorted(used - set(s["station_id"]))
    # recover coordinates from trip records (median start coords, else end coords)
    a = trips[["start_station", "start_lat", "start_lon"]].rename(
        columns={"start_station": "station_id", "start_lat": "lat", "start_lon": "lon"})
    b = trips[["end_station", "end_lat", "end_lon"]].rename(
        columns={"end_station": "station_id", "end_lat": "lat", "end_lon": "lon"})
    coords = pd.concat([a, b]).dropna()
    coords = coords[coords["station_id"].isin(missing_ids)]
    med = coords.groupby("station_id")[["lat", "lon"]].median()
    rec = pd.DataFrame({"station_id": missing_ids})
    rec = rec.merge(med, left_on="station_id", right_index=True, how="left")
    rec["station_name"] = "Recovered station " + rec["station_id"].astype(str)
    rec["recovered"] = 1
    # assign region by nearest registered station
    reg = s.dropna(subset=["region"])
    def nearest_region(r):
        if pd.isna(r.lat):
            return np.nan
        d = (reg["lat"] - r.lat) ** 2 + (reg["lon"] - r.lon) ** 2
        return reg.loc[d.idxmin(), "region"]
    rec["region"] = rec.apply(nearest_region, axis=1)
    rec["region_missing"] = 1
    # registered station with missing region -> nearest region too
    for i in s.index[s["region"].isna()]:
        d = (reg["lat"] - s.at[i, "lat"]) ** 2 + (reg["lon"] - s.at[i, "lon"]) ** 2
        s.at[i, "region"] = reg.loc[d.idxmin(), "region"]
    out = pd.concat([s, rec], ignore_index=True)
    out["coords_missing"] = out["lat"].isna().astype(int)
    # virtual / non-geographic IDs (e.g. 3000 'Virtual Station') -> region Unknown
    out["region"] = out["region"].fillna("Unknown")
    assert out["station_id"].is_unique, "station registry must be unique"
    audit["stations_registry_raw"] = int(len(stations))
    audit["stations_recovered_from_trips"] = len(missing_ids)
    audit["stations_recovered_ids"] = [int(x) for x in missing_ids]
    audit["stations_registry_final"] = int(len(out))
    return out


def build_ssot() -> pd.DataFrame:
    audit: dict = {"ssot_version": C.SSOT_VERSION}
    trips, stations, weather = load_raw()
    audit["raw_trips"] = int(len(trips))
    audit["raw_trip_columns"] = int(trips.shape[1])
    audit["raw_stations"] = [int(x) for x in stations.shape]
    audit["raw_weather"] = [int(x) for x in weather.shape]
    audit["duplicate_trip_ids"] = int(trips["trip_id"].duplicated().sum())

    unmatched = ~trips["start_station"].isin(stations["station_id"])
    audit["unmatched_origin_trips_vs_raw_registry"] = int(unmatched.sum())
    audit["unmatched_destination_trips_vs_raw_registry"] = int(
        (~trips["end_station"].isin(stations["station_id"])).sum())
    audit["trips_missing_start_coords"] = int(trips["start_lat"].isna().sum())
    audit["trips_missing_end_coords"] = int(trips["end_lat"].isna().sum())

    w = clean_weather(weather, audit)
    reg = build_station_registry(trips, stations, audit)
    reg.to_csv(C.STATIONS_PATH, index=False)

    t = trips.copy()
    t["origin_unmatched_raw"] = unmatched.astype(int)
    t["hour"] = t["start_time"].dt.floor("h")
    t["end_hour"] = t["end_time"].dt.floor("h")
    n_before = len(t)
    dep = t.groupby(["start_station", "hour"]).agg(
        departures=("trip_id", "size"),
        dep_electric=("bike_type", lambda x: int((x == "electric").sum() + (x == "Electric").sum())),
    ).reset_index().rename(columns={"start_station": "station_id"})
    assert dep["departures"].sum() == n_before, "row-count check failed before aggregation"
    arr = t.groupby(["end_station", "end_hour"]).size().rename("arrivals").reset_index()
    arr = arr.rename(columns={"end_station": "station_id", "end_hour": "hour"})

    # active window per station (first..last observed departure or arrival)
    act = pd.concat([dep[["station_id", "hour"]], arr[["station_id", "hour"]]])
    win = act.groupby("station_id")["hour"].agg(["min", "max"])
    hours = pd.date_range("2024-01-01 00:00", "2024-12-31 23:00", freq="h")
    frames = []
    for sid, (lo, hi) in win.iterrows():
        h = hours[(hours >= lo) & (hours <= hi)]
        frames.append(pd.DataFrame({"station_id": sid, "hour": h}))
    panel = pd.concat(frames, ignore_index=True)
    panel = panel.merge(dep, on=["station_id", "hour"], how="left")
    panel = panel.merge(arr, on=["station_id", "hour"], how="left")
    for c in ("departures", "dep_electric", "arrivals"):
        panel[c] = panel[c].fillna(0).astype("int32")
    audit["departures_in_panel"] = int(panel["departures"].sum())
    assert audit["departures_in_panel"] == n_before, "departures lost when building panel"

    n_panel = len(panel)
    panel = panel.merge(w, on="hour", how="left", validate="many_to_one")
    assert len(panel) == n_panel, "weather join changed row count"
    panel = panel.merge(
        reg[["station_id", "lat", "lon", "region", "recovered", "region_missing", "coords_missing"]],
        on="station_id", how="left", validate="many_to_one")
    assert len(panel) == n_panel

    panel = add_calendar(panel)
    panel = panel.sort_values(["station_id", "hour"]).reset_index(drop=True)
    panel["split"] = np.where(panel["hour"] <= C.TRAIN_END, "train",
                              np.where(panel["hour"] <= C.VAL_END, "val", "test"))
    audit["ssot_rows"] = int(len(panel))
    audit["ssot_columns"] = int(panel.shape[1])
    audit["ssot_stations"] = int(panel["station_id"].nunique())
    audit["ssot_zero_share"] = float((panel["departures"] == 0).mean())
    audit["rows_by_split"] = panel["split"].value_counts().to_dict()
    panel.to_parquet(C.SSOT_PATH, index=False)
    C.AUDIT_PATH.write_text(json.dumps(audit, indent=2, default=str))
    return panel


US_HOLIDAYS_2024 = pd.to_datetime([
    "2024-01-01", "2024-01-15", "2024-02-19", "2024-05-27", "2024-06-19", "2024-07-04",
    "2024-09-02", "2024-10-14", "2024-11-11", "2024-11-28", "2024-11-29", "2024-12-24",
    "2024-12-25", "2024-12-31",
])


def add_calendar(df: pd.DataFrame) -> pd.DataFrame:
    h = df["hour"]
    df["hour_of_day"] = h.dt.hour.astype("int8")
    df["dow"] = h.dt.dayofweek.astype("int8")
    df["is_weekend"] = (df["dow"] >= 5).astype("int8")
    df["is_holiday"] = h.dt.normalize().isin(US_HOLIDAYS_2024).astype("int8")
    df["month"] = h.dt.month.astype("int8")
    df["date"] = h.dt.normalize()
    return df


if __name__ == "__main__":
    p = build_ssot()
    print(p.shape)
    print(json.dumps(json.loads(C.AUDIT_PATH.read_text()), indent=1))
