"""Trip-level redistribution simulation for H3 and H7 (test period Nov-Dec).

Assumptions (stated, varied in scenarios):
* Every station has the same dock capacity `cap`; the fleet starts at `fill` x cap.
* At the start of each hour the operator may move at most `budget` bikes in total.
  Transfers are instantaneous (truck already positioned) and paired with the
  nearest donor station that has surplus.
* Target stock at a station for hour h = min(cap, ceil(f + z*sqrt(f))) where f is the
  policy's demand estimate for that hour (same rule for every policy).
* Demand = realised departures (observed trips are a lower bound of true demand).
  Within a station-hour trips are served in start-time order while bikes remain.
  A served trip returns its bike at its end station / end hour; if that dock is full
  the bike goes to the nearest station with a free dock (counted as a blocked return).

Policies: none (no transfers), HA (historical station x hour x weekend average),
forecast (LightGBM SCWL), oracle (perfect foresight; upper bound).
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
from scipy import stats

from . import config as C

POLICY_COL = {"HA": "pred_HA_shw", "forecast": "pred_LGBM_SCWL", "oracle": "departures"}
SCENARIOS = [
    {"name": f"cap{cap}_B{b}", "cap": cap, "budget": b, "fill": 0.5}
    for cap in (15, 25) for b in (10, 25, 50)
]
Z = 1.0


def haversine_matrix(lat, lon):
    lat, lon = np.radians(lat), np.radians(lon)
    dlat = lat[:, None] - lat[None, :]
    dlon = lon[:, None] - lon[None, :]
    a = np.sin(dlat / 2) ** 2 + np.cos(lat[:, None]) * np.cos(lat[None, :]) * np.sin(dlon / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(a))


def peak_hours_from_train() -> list[int]:
    df = pd.read_parquet(C.SSOT_PATH, columns=["hour", "hour_of_day", "departures", "split"])
    tr = df[df["split"] == "train"]
    prof = tr.groupby(["hour", "hour_of_day"])["departures"].sum().groupby("hour_of_day").mean()
    thr = prof.quantile(0.75)
    peak = sorted(int(h) for h in prof.index[prof >= thr])
    return peak


def plan_transfers(inv, target, cap, budget, dist):
    """Greedy nearest-donor pairing. Returns list of (from, to, n, km) and new inventory."""
    inv = inv.copy()
    deficit = np.maximum(target - inv, 0)
    surplus = np.maximum(inv - target, 0)
    moves, left = [], budget
    for r in np.argsort(-deficit, kind="stable"):
        if left <= 0 or deficit[r] <= 0:
            break
        need = min(deficit[r], cap[r] - inv[r], left)
        if need <= 0:
            continue
        donors = np.where(surplus > 0)[0]
        if donors.size == 0:
            break
        for d in donors[np.argsort(dist[r, donors])]:
            take = min(surplus[d], need)
            if take <= 0:
                continue
            surplus[d] -= take
            inv[d] -= take
            inv[r] += take
            need -= take
            left -= take
            moves.append((int(d), int(r), int(take), float(dist[r, d])))
            if need <= 0:
                break
    return moves, inv


def load_inputs():
    preds = pd.read_parquet(C.PREDICTIONS_PATH)
    preds = preds[preds["split"] == "test"]
    reg = pd.read_csv(C.STATIONS_PATH)
    stations = np.array(sorted(pd.read_parquet(C.SSOT_PATH, columns=["station_id"])["station_id"].unique()))
    sidx = {s: i for i, s in enumerate(stations)}
    hours = pd.date_range("2024-11-01 00:00", "2024-12-31 23:00", freq="h")
    hidx = {h: i for i, h in enumerate(hours)}
    trips = pd.read_csv(C.DATA_RAW / "trips.csv", parse_dates=["start_time", "end_time"],
                        usecols=["trip_id", "start_time", "end_time", "start_station", "end_station"])
    trips = trips[trips["start_time"] >= hours[0]].sort_values("start_time")
    trips["h"] = trips["start_time"].dt.floor("h").map(hidx)
    trips["eh"] = trips["end_time"].dt.floor("h").map(hidx).fillna(-1).astype(int)
    trips["s"] = trips["start_station"].map(sidx)
    trips["e"] = trips["end_station"].map(sidx)
    trips["rank"] = trips.groupby(["h", "s"]).cumcount()
    fc = {}
    for pol, col in POLICY_COL.items():
        m = np.zeros((len(hours), len(stations)))
        hi = preds["hour"].map(hidx).values
        si = preds["station_id"].map(sidx).values
        m[hi, si] = preds[col].values
        fc[pol] = m
    r = reg.set_index("station_id").reindex(stations)
    lat = r["lat"].fillna(r["lat"].median()).values
    lon = r["lon"].fillna(r["lon"].median()).values
    dist = haversine_matrix(lat, lon)
    return stations, hours, trips, fc, dist


def simulate(policy, sc, stations, hours, trips, fc, dist, record_moves=False):
    N, H = len(stations), len(hours)
    cap = np.full(N, sc["cap"])
    inv = np.floor(cap * sc["fill"]).astype(int)
    arr_sched = np.zeros((H + 1, N), dtype=int)
    by_hour = {h: g for h, g in trips.groupby("h")}
    rows, moves_log = [], []
    nearest = np.argsort(dist, axis=1)
    for h in range(H):
        moved = km = 0
        if policy != "none":
            f = fc[policy][h]
            target = np.minimum(cap, np.ceil(f + Z * np.sqrt(f))).astype(int)
            moves, inv = plan_transfers(inv, target, cap, sc["budget"], dist)
            moved = sum(m[2] for m in moves)
            km = sum(m[2] * m[3] for m in moves)
            if record_moves:
                moves_log += [(h, *m) for m in moves]
        dem = np.zeros(N, int)
        srv = np.zeros(N, int)
        g = by_hour.get(h)
        if g is not None:
            served = g["rank"].values < inv[g["s"].values]
            np.add.at(dem, g["s"].values, 1)
            np.add.at(srv, g["s"].values[served], 1)
            inv -= srv
            gs = g[served & (g["eh"].values >= 0)]
            np.add.at(arr_sched, (np.maximum(gs["eh"].values, h), gs["e"].values), 1)
        # arrivals at end of hour with dock-capacity overflow handling
        inv += arr_sched[h]
        blocked = 0
        over = np.where(inv > cap)[0]
        for s in over:
            extra = inv[s] - cap[s]
            inv[s] = cap[s]
            blocked += extra
            for nb in nearest[s][1:]:
                space = cap[nb] - inv[nb]
                if space > 0:
                    put = min(space, extra)
                    inv[nb] += put
                    extra -= put
                    if extra == 0:
                        break
        rows.append((h, int(dem.sum()), int(srv.sum()), moved, km, blocked,
                     int((inv == 0).sum())))
    out = pd.DataFrame(rows, columns=["h", "demand", "served", "moved", "km", "blocked", "empty_stations"])
    out["hour"] = hours[out["h"]]
    out["policy"], out["scenario"] = policy, sc["name"]
    return (out, moves_log) if record_moves else out


def run():
    stations, hours, trips, fc, dist = load_inputs()
    peak = peak_hours_from_train()
    (C.TABLES / "peak_hours.json").write_text(json.dumps({"peak_hours": peak,
        "rule": "hours of day with mean training system departures >= 75th percentile"}))
    allres = []
    for sc in SCENARIOS:
        for pol in ("none", "HA", "forecast", "oracle"):
            r = simulate(pol, sc, stations, hours, trips, fc, dist)
            allres.append(r)
            u = r["demand"].sum() - r["served"].sum()
            print(f"{sc['name']:12s} {pol:8s} coverage {r['served'].sum()/r['demand'].sum():.4f} "
                  f"unmet {u:6d} moved {r['moved'].sum():6d}")
    sim = pd.concat(allres, ignore_index=True)
    sim["unmet"] = sim["demand"] - sim["served"]
    sim["date"] = sim["hour"].dt.normalize()
    sim["peak"] = sim["hour"].dt.hour.isin(peak)
    sim.to_parquet(C.DATA_PROC / "simulation_hourly.parquet", index=False)

    # scenario summary
    summ = sim.groupby(["scenario", "policy"]).agg(
        demand=("demand", "sum"), served=("served", "sum"), unmet=("unmet", "sum"),
        bikes_moved=("moved", "sum"), bike_km=("km", "sum"), blocked_returns=("blocked", "sum"),
        mean_empty_stations=("empty_stations", "mean")).reset_index()
    summ["coverage"] = summ["served"] / summ["demand"]
    for part, mask in (("peak", sim["peak"]), ("offpeak", ~sim["peak"])):
        g = sim[mask].groupby(["scenario", "policy"])[["served", "demand"]].sum()
        summ = summ.merge((g["served"] / g["demand"]).rename(f"coverage_{part}").reset_index(),
                          on=["scenario", "policy"])
    summ["unmet_per_bike_moved"] = np.nan
    summ.to_csv(C.TABLES / "simulation_summary.csv", index=False)

    # H3 and H7 per scenario (daily paired tests, 61 days)
    tests = []
    for sc in SCENARIOS:
        s = sim[sim["scenario"] == sc["name"]]
        d = s.groupby(["date", "policy"])[["unmet"]].sum().unstack("policy")["unmet"]
        diff = d["HA"] - d["forecast"]
        w = stats.wilcoxon(diff, alternative="greater") if (diff != 0).any() else None
        # H7: coverage gain forecast - HA, peak vs off-peak, per day
        cov = s.groupby(["date", "peak", "policy"])[["served", "demand"]].sum()
        cov = (cov["served"] / cov["demand"]).unstack("policy")
        gain = (cov["forecast"] - cov["HA"]).unstack("peak")
        gain_none = (cov["forecast"] - cov["none"]).unstack("peak")
        g7 = (gain[True] - gain[False]).dropna()
        w7 = stats.wilcoxon(g7, alternative="greater") if (g7 != 0).any() else None
        tot = s.groupby("policy")[["unmet", "demand", "served"]].sum()
        pk = s.groupby(["peak", "policy"])[["served", "demand"]].sum()
        pkc = (pk["served"] / pk["demand"]).unstack("policy")
        tests.append({
            "scenario": sc["name"], "cap": sc["cap"], "budget": sc["budget"],
            "unmet_none": int(tot.loc["none", "unmet"]), "unmet_HA": int(tot.loc["HA", "unmet"]),
            "unmet_forecast": int(tot.loc["forecast", "unmet"]), "unmet_oracle": int(tot.loc["oracle", "unmet"]),
            "H3_unmet_reduction_vs_HA": int(tot.loc["HA", "unmet"] - tot.loc["forecast", "unmet"]),
            "H3_unmet_reduction_pct": float(100 * (tot.loc["HA", "unmet"] - tot.loc["forecast", "unmet"])
                                           / max(tot.loc["HA", "unmet"], 1)),
            "H3_days_better": int((diff > 0).sum()), "H3_days_worse": int((diff < 0).sum()),
            "H3_wilcoxon_p": float(w.pvalue) if w is not None else 1.0,
            "H7_gain_peak_pp": float(100 * (pkc.loc[True, "forecast"] - pkc.loc[True, "HA"])),
            "H7_gain_offpeak_pp": float(100 * (pkc.loc[False, "forecast"] - pkc.loc[False, "HA"])),
            "H7_gain_vs_none_peak_pp": float(100 * (pkc.loc[True, "forecast"] - pkc.loc[True, "none"])),
            "H7_gain_vs_none_offpeak_pp": float(100 * (pkc.loc[False, "forecast"] - pkc.loc[False, "none"])),
            "H7_days_peak_gain_larger": int((g7 > 0).sum()),
            "H7_wilcoxon_p": float(w7.pvalue) if w7 is not None else 1.0,
        })
    tests = pd.DataFrame(tests)
    tests.to_csv(C.TABLES / "hypothesis_simulation_tests.csv", index=False)
    return summ, tests


if __name__ == "__main__":
    s, t = run()
    pd.set_option("display.width", 250)
    print(s.to_string())
    print(t.T.to_string())
