"""H6 concentration test, SHAP explanations, drift check and results figures."""
from __future__ import annotations

import json

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from . import config as C

BLUE, ORANGE, GREEN, RED, GREY = "#2a6f97", "#e07a2f", "#3a9d5d", "#c0392b", "#8a99a8"


def _save(fig, name):
    fig.tight_layout()
    fig.savefig(C.FIGURES / f"{name}.png", dpi=160)
    plt.close(fig)


def h6():
    df = pd.read_parquet(C.SSOT_PATH, columns=["station_id", "date", "departures", "split"])
    tr = df[df["split"] == "train"]
    rank = tr.groupby("station_id")["departures"].sum().sort_values(ascending=False)
    k = int(np.ceil(0.2 * len(rank)))
    top = set(rank.index[:k])
    later = df[df["split"] != "train"]
    later_test = df[df["split"] == "test"]
    daily = later.assign(top=later["station_id"].isin(top)).groupby(["date", "top"])["departures"].sum().unstack()
    share_daily = daily[True] / daily.sum(axis=1)
    rng = np.random.default_rng(C.SEED)
    d_top, d_all = daily[True].values, daily.sum(axis=1).values
    idx = rng.integers(0, len(d_top), (5000, len(d_top)))
    boots = d_top[idx].sum(1) / d_all[idx].sum(1)
    share = later["departures"][later["station_id"].isin(top)].sum() / later["departures"].sum()
    share_test = later_test["departures"][later_test["station_id"].isin(top)].sum() / later_test["departures"].sum()
    t = stats.wilcoxon(share_daily - 0.5, alternative="greater")
    res = {
        "stations_ranked_on_train": int(len(rank)), "top20_k": k,
        "top20_share_train": float(rank.iloc[:k].sum() / rank.sum()),
        "top20_share_later_SepDec": float(share),
        "top20_share_test_NovDec": float(share_test),
        "ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
        "days_share_above_50pct": int((share_daily > 0.5).sum()), "days": int(len(share_daily)),
        "wilcoxon_p_share_gt_50": float(t.pvalue),
        "top_station_ids": [int(x) for x in rank.index[:k]],
    }
    (C.TABLES / "h6_result.json").write_text(json.dumps(res, indent=2))
    return res


def shap_explain(n=20000):
    import shap
    from .features import build_features, load_ssot

    bundle = joblib.load(C.MODELS / "lgbm_scwl.joblib")
    model, feats = bundle["model"], bundle["features"]
    df = build_features(load_ssot())
    te = df[df["split"] == "test"].sample(n, random_state=C.SEED)
    ex = shap.TreeExplainer(model)
    sv = ex.shap_values(te[feats])
    shap.summary_plot(sv, te[feats], show=False, max_display=15)
    plt.title("SHAP summary - LightGBM (SCWL), test sample (log-rate scale)")
    plt.gcf().set_size_inches(9, 6.5)
    plt.tight_layout()
    plt.savefig(C.FIGURES / "fig14_shap_summary.png", dpi=160)
    plt.close()
    imp = pd.Series(np.abs(sv).mean(0), index=feats).sort_values(ascending=False)
    imp.rename("mean_abs_shap").to_csv(C.TABLES / "shap_importance.csv")

    # drift monitoring: PSI of key features train vs test
    tr = df[df["split"] == "train"]
    rows = []
    for c in ["lag_1", "roll_24", "w_temp_c", "w_precip_mm", "hour_of_day", "station_mean"]:
        a, b = tr[c].dropna(), df.loc[df["split"] == "test", c].dropna()
        qs = np.unique(np.quantile(a, np.linspace(0, 1, 11)))
        if len(qs) < 3:
            qs = np.unique(np.concatenate([[a.min() - 1e-9], [a.mean()], [a.max() + 1e-9]]))
        pa = np.histogram(np.clip(a, qs[0], qs[-1]), qs)[0] / len(a) + 1e-6
        pb = np.histogram(np.clip(b, qs[0], qs[-1]), qs)[0] / len(b) + 1e-6
        psi = float(np.sum((pb - pa) * np.log(pb / pa)))
        rows.append({"feature": c, "PSI": psi, "train_mean": a.mean(), "test_mean": b.mean(),
                     "status": "stable" if psi < 0.1 else ("moderate" if psi < 0.25 else "major")})
    pd.DataFrame(rows).to_csv(C.TABLES / "drift_psi.csv", index=False)
    return imp


def figures():
    m = pd.read_csv(C.TABLES / "model_metrics.csv")
    m["label"] = m["model"] + np.where(m["features"] != "-", " " + m["features"], "")
    order = ["HA_station", "HA_shw", "LGBM S", "LGBM SC", "LGBM SCW", "LGBM SCL", "LGBM SCWL",
             "LR SCWL", "RF SCWL"]
    p = m.pivot(index="label", columns="split", values="MAE").reindex(order)
    fig, ax = plt.subplots(figsize=(10, 4.2))
    x = np.arange(len(p))
    ax.bar(x - 0.2, p["val"], 0.4, label="Validation (Sep-Oct)", color=BLUE)
    ax.bar(x + 0.2, p["test"], 0.4, label="Test (Nov-Dec)", color=ORANGE)
    ax.set_xticks(x, p.index, rotation=30, ha="right")
    ax.set(ylabel="MAE (departures / station-hour)", title="Forecast error by model and feature set")
    for i, v in enumerate(p["test"]):
        ax.text(i + 0.2, v, f"{v:.3f}", ha="center", va="bottom", fontsize=7)
    ax.legend()
    _save(fig, "fig11_model_mae")

    pr = pd.read_parquet(C.PREDICTIONS_PATH)
    te = pr[pr["split"] == "test"]
    busiest = te.groupby("station_id")["departures"].sum().idxmax()
    d = te[(te["station_id"] == busiest) & (te["hour"] >= "2024-11-11") & (te["hour"] < "2024-11-18")]
    fig, ax = plt.subplots(figsize=(11, 3.6))
    ax.bar(d["hour"], d["departures"], width=0.035, color="#c9d6e3", label="Actual")
    ax.plot(d["hour"], d["pred_LGBM_SCWL"], color=ORANGE, label="LightGBM SCWL")
    ax.plot(d["hour"], d["pred_HA_shw"], color=GREY, ls="--", label="Historical average")
    ax.set(title=f"Actual vs forecast, station {busiest}, 11-17 Nov 2024", ylabel="Departures / hour")
    ax.legend()
    _save(fig, "fig12_forecast_example")

    sys_ = te.groupby("hour")[["departures", "pred_LGBM_SCWL", "pred_HA_shw"]].sum()
    sys_ = sys_[(sys_.index >= "2024-11-11") & (sys_.index < "2024-11-25")]
    fig, ax = plt.subplots(figsize=(11, 3.4))
    ax.plot(sys_.index, sys_["departures"], color="k", lw=1, label="Actual")
    ax.plot(sys_.index, sys_["pred_LGBM_SCWL"], color=ORANGE, lw=1, label="LightGBM SCWL")
    ax.plot(sys_.index, sys_["pred_HA_shw"], color=GREY, lw=1, ls="--", label="Historical average")
    ax.set(title="System-level hourly departures (sum of station forecasts), 11-24 Nov", ylabel="Departures")
    ax.legend()
    _save(fig, "fig13_system_forecast")

    # residuals by hour of day
    te = te.assign(err=te["pred_LGBM_SCWL"] - te["departures"])
    g = te.groupby("hour_of_day")["err"].agg(lambda e: e.abs().mean())
    g2 = te.assign(e2=(te["pred_HA_shw"] - te["departures"]).abs()).groupby("hour_of_day")["e2"].mean()
    fig, ax = plt.subplots(figsize=(8, 3.4))
    ax.plot(g.index, g.values, marker="o", color=ORANGE, label="LightGBM SCWL")
    ax.plot(g2.index, g2.values, marker="o", color=GREY, label="Historical average")
    ax.set(title="Test MAE by hour of day", xlabel="Hour", ylabel="MAE", xticks=range(0, 24, 2))
    ax.legend()
    _save(fig, "fig15_mae_by_hour")

    s = pd.read_csv(C.TABLES / "simulation_summary.csv")
    t = pd.read_csv(C.TABLES / "hypothesis_simulation_tests.csv")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    pol = ["none", "HA", "forecast", "oracle"]
    cols = {"none": GREY, "HA": BLUE, "forecast": ORANGE, "oracle": GREEN}
    scen = list(t["scenario"])
    x = np.arange(len(scen))
    for i, pname in enumerate(pol):
        v = s[s["policy"] == pname].set_index("scenario").reindex(scen)["unmet"]
        axes[0].bar(x + (i - 1.5) * 0.2, v, 0.2, label=pname, color=cols[pname])
    axes[0].set_xticks(x, scen, rotation=25)
    axes[0].set(title="Simulated unmet demand (Nov-Dec) by policy", ylabel="Trips without a bike")
    axes[0].legend()
    axes[1].bar(x - 0.2, t["H7_gain_peak_pp"], 0.4, color=ORANGE, label="Peak hours")
    axes[1].bar(x + 0.2, t["H7_gain_offpeak_pp"], 0.4, color=BLUE, label="Off-peak hours")
    axes[1].axhline(0, color="k", lw=.8)
    axes[1].set_xticks(x, scen, rotation=25)
    axes[1].set(title="Coverage gain of forecast policy over HA policy", ylabel="Percentage points")
    axes[1].legend()
    _save(fig, "fig16_simulation")


def run():
    r = h6()
    print(json.dumps({k: v for k, v in r.items() if k != "top_station_ids"}, indent=1))
    try:
        print(shap_explain().head(12))
    except Exception as e:  # noqa
        print("SHAP failed:", e)
    figures()


if __name__ == "__main__":
    run()
