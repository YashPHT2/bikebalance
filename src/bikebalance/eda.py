"""Exploratory data analysis: figures + summary tables for the report."""
from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

from . import config as C

sns.set_theme(style="whitegrid", context="notebook")
BLUE, ORANGE, GREEN, RED = "#2a6f97", "#e07a2f", "#3a9d5d", "#c0392b"


def _save(fig, name):
    fig.tight_layout()
    fig.savefig(C.FIGURES / f"{name}.png", dpi=160)
    plt.close(fig)


def run():
    df = pd.read_parquet(C.SSOT_PATH)
    trips = pd.read_csv(C.DATA_RAW / "trips.csv", parse_dates=["start_time"])
    summary = {}

    # 1 daily departures over the year with split shading
    daily = df.groupby("date")["departures"].sum()
    fig, ax = plt.subplots(figsize=(11, 3.8))
    ax.plot(daily.index, daily.values, color=BLUE, lw=1)
    ax.plot(daily.index, daily.rolling(7, center=True).mean(), color=ORANGE, lw=2, label="7-day mean")
    for lo, hi, lab, c in (("2024-01-01", "2024-08-31", "Train", "#dbe9f6"),
                           ("2024-09-01", "2024-10-31", "Validation", "#fdebd3"),
                           ("2024-11-01", "2024-12-31", "Test", "#dcf1e2")):
        ax.axvspan(pd.Timestamp(lo), pd.Timestamp(hi) + pd.Timedelta(days=1), color=c, alpha=.7, zorder=0)
        ax.text(pd.Timestamp(lo) + pd.Timedelta(days=3), daily.max() * .97, lab, fontsize=9)
    ax.set(title="Daily departures, 2024 (temporal split shaded)", ylabel="Trips per day")
    ax.legend(loc="lower left")
    _save(fig, "fig01_daily_departures")
    summary["daily_mean"] = float(daily.mean())
    summary["daily_max"] = [str(daily.idxmax().date()), int(daily.max())]
    summary["daily_min"] = [str(daily.idxmin().date()), int(daily.min())]

    # 2 hour x weekday heatmap
    sys_hour = df.groupby("hour").agg(dep=("departures", "sum"), hod=("hour_of_day", "first"),
                                      dow=("dow", "first"))
    hm = sys_hour.pivot_table(index="dow", columns="hod", values="dep", aggfunc="mean")
    hm.index = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    fig, ax = plt.subplots(figsize=(11, 3.6))
    sns.heatmap(hm, cmap="YlGnBu", ax=ax, cbar_kws={"label": "Mean departures / hour"})
    ax.set(title="System departures by hour of day and weekday", xlabel="Hour of day", ylabel="")
    _save(fig, "fig02_hour_weekday_heatmap")

    # 3 hourly profile weekday vs weekend
    prof = sys_hour.assign(we=sys_hour["dow"] >= 5).groupby(["we", "hod"])["dep"].mean().unstack(0)
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    ax.plot(prof.index, prof[False], marker="o", ms=3, color=BLUE, label="Weekday")
    ax.plot(prof.index, prof[True], marker="o", ms=3, color=ORANGE, label="Weekend")
    ax.set(title="Mean hourly departures: weekday vs weekend", xlabel="Hour of day",
           ylabel="Departures / hour (system)", xticks=range(0, 24, 2))
    ax.legend()
    _save(fig, "fig03_hourly_profile")
    t = stats.kruskal(*[g["dep"].values for _, g in sys_hour.groupby("hod")])
    summary["kruskal_hour_of_day"] = {"H": float(t.statistic), "p": float(t.pvalue)}

    # 4 station concentration (Lorenz) on training data
    tr = df[df["split"] == "train"]
    st = tr.groupby("station_id")["departures"].sum().sort_values(ascending=False)
    cum = st.cumsum() / st.sum()
    x = np.arange(1, len(st) + 1) / len(st)
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    ax.plot(x, cum.values, color=BLUE, lw=2)
    ax.plot([0, 1], [0, 1], "--", color="grey")
    k = int(np.ceil(0.2 * len(st)))
    ax.axvline(0.2, color=ORANGE, ls=":")
    ax.axhline(cum.iloc[k - 1], color=ORANGE, ls=":")
    ax.set(title="Station concentration (train, Jan-Aug)", xlabel="Share of stations (ranked)",
           ylabel="Cumulative share of departures")
    ax.text(0.23, cum.iloc[k - 1] - 0.08, f"Top 20% = {cum.iloc[k-1]:.1%}", color=ORANGE)
    _save(fig, "fig04_station_lorenz")
    summary["top20_share_train"] = float(cum.iloc[k - 1])

    # 5 departures vs weather
    sh = df.groupby("hour").agg(dep=("departures", "sum"), temp=("temp_c", "first"),
                                precip=("precip_mm", "first"), hod=("hour_of_day", "first"))
    day = sh[(sh["hod"] >= 7) & (sh["hod"] <= 20)]
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    tb = pd.cut(day["temp"], bins=np.arange(4, 40, 3))
    g = day.groupby(tb, observed=True)["dep"].mean()
    axes[0].bar([f"{i.left:.0f}-{i.right:.0f}" for i in g.index], g.values, color=BLUE)
    axes[0].set(title="Daytime (07-20h) departures vs temperature", xlabel="Temperature (C)",
                ylabel="Mean departures / hour")
    axes[0].tick_params(axis="x", rotation=45)
    rain = day["precip"] > 0
    axes[1].bar(["Dry", "Rain"], [day.loc[~rain, "dep"].mean(), day.loc[rain, "dep"].mean()],
                color=[GREEN, RED])
    axes[1].set(title=f"Rain vs dry hours (n rain = {rain.sum()})", ylabel="Mean departures / hour")
    _save(fig, "fig05_weather_effect")
    mw = stats.mannwhitneyu(day.loc[~rain, "dep"], day.loc[rain, "dep"], alternative="greater")
    summary["rain_hours_daytime"] = int(rain.sum())
    summary["dep_dry_vs_rain"] = [float(day.loc[~rain, "dep"].mean()), float(day.loc[rain, "dep"].mean())]
    summary["mannwhitney_dry_gt_rain_p"] = float(mw.pvalue)
    summary["spearman_temp_dep_daytime"] = float(stats.spearmanr(day["temp"], day["dep"]).statistic)

    # 6 distribution of station-hour departures
    fig, ax = plt.subplots(figsize=(7, 3.8))
    vc = df["departures"].clip(upper=10).value_counts().sort_index()
    ax.bar([str(i) if i < 10 else "10+" for i in vc.index], vc.values / vc.sum(), color=BLUE)
    ax.set(title="Distribution of station-hour departures (target)", xlabel="Departures in hour",
           ylabel="Share of station-hours")
    _save(fig, "fig06_target_distribution")
    summary["target_mean"] = float(df["departures"].mean())
    summary["target_var"] = float(df["departures"].var())
    summary["zero_share"] = float((df["departures"] == 0).mean())

    # 7 autocorrelation of a busy station
    top = st.index[0]
    s = df[df["station_id"] == top].set_index("hour")["departures"]
    lags = range(1, 170)
    ac = [s.autocorr(l) for l in lags]
    fig, ax = plt.subplots(figsize=(9, 3.4))
    ax.bar(lags, ac, color=BLUE, width=0.8)
    for l in (24, 168):
        ax.axvline(l, color=ORANGE, ls=":")
    ax.set(title=f"Autocorrelation of hourly departures, busiest station {top}", xlabel="Lag (hours)",
           ylabel="ACF")
    _save(fig, "fig07_acf")
    summary["acf_busiest"] = {"station": int(top), "lag1": float(ac[0]), "lag24": float(ac[23]),
                              "lag168": float(ac[167])}

    # 8 region & user mix
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.6))
    reg = df.groupby("region")["departures"].sum().sort_values()
    axes[0].barh(reg.index, reg.values, color=BLUE)
    axes[0].set(title="Departures by region")
    pt = trips["passholder_type"].value_counts()
    axes[1].barh(pt.index, pt.values, color=GREEN)
    axes[1].set(title="Pass-holder type")
    bt = trips["bike_type"].str.title().value_counts()
    axes[2].bar(bt.index, bt.values, color=ORANGE)
    axes[2].set(title="Bike type")
    _save(fig, "fig08_mix")
    summary["regions"] = reg.astype(int).to_dict()
    summary["passholder"] = pt.astype(int).to_dict()
    summary["bike_type"] = bt.astype(int).to_dict()
    summary["duration_median_min"] = float(trips["duration_minutes"].median())

    # 9 net flow imbalance by station (arrivals - departures), train
    nf = tr.groupby("station_id")[["departures", "arrivals"]].sum()
    nf["net"] = nf["arrivals"] - nf["departures"]
    nf = nf.sort_values("net")
    sel = pd.concat([nf.head(10), nf.tail(10)])
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(sel.index.astype(str), sel["net"], color=[RED if v < 0 else GREEN for v in sel["net"]])
    ax.set(title="Net flow (arrivals - departures), Jan-Aug: 10 most draining / filling stations",
           xlabel="Net bikes", ylabel="Station")
    _save(fig, "fig09_net_flow")
    summary["stations_net_negative"] = int((nf["net"] < 0).sum())

    # 10 station map
    reg_df = pd.read_csv(C.STATIONS_PATH)
    vol = df.groupby("station_id")["departures"].sum()
    reg_df["vol"] = reg_df["station_id"].map(vol).fillna(0)
    reg_df = reg_df.dropna(subset=["lat"])
    reg_df = reg_df[(reg_df["lat"] > 33) & (reg_df["lon"] < -117)]
    fig, ax = plt.subplots(figsize=(7, 6))
    for r, c in zip(sorted(reg_df["region"].unique()), [BLUE, ORANGE, GREEN, RED, "grey"]):
        d = reg_df[reg_df["region"] == r]
        ax.scatter(d["lon"], d["lat"], s=5 + d["vol"] / 60, alpha=.6, color=c, label=r)
    rec = reg_df[reg_df["recovered"] == 1]
    ax.scatter(rec["lon"], rec["lat"], s=40, facecolors="none", edgecolors="k", label="Recovered ID")
    ax.set(title="Stations sized by 2024 departures", xlabel="Longitude", ylabel="Latitude")
    ax.legend(fontsize=8, markerscale=.5)
    _save(fig, "fig10_station_map")

    (C.TABLES / "eda_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), indent=1, default=str))
