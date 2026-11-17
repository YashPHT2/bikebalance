"""Forecasting experiments for H1, H2, H4, H5 (and H6 ranking check).

Protocol: tune on validation (Sep-Oct) using models fit on train (Jan-Aug);
refit the selected configuration on train+val and score once on test (Nov-Dec).
Nested feature-set comparisons use the same learner (LightGBM) so that only the
feature group changes (controlled comparison). Runs are tracked in MLflow.
"""
from __future__ import annotations

import json
import time

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from . import config as C
from .features import FEATURE_SETS, build_features, impute_apply, impute_fit, load_ssot
from .stats import metrics, paired_test

try:
    import mlflow
    mlflow.set_tracking_uri("sqlite:///" + str(C.ROOT / "mlflow.db").replace("\\", "/"))
    mlflow.set_experiment("BikeBalance-forecasting")
except Exception:  # pragma: no cover
    mlflow = None

LGB_GRID = [
    {"num_leaves": 31, "learning_rate": 0.05, "min_child_samples": 100, "objective": "poisson"},
    {"num_leaves": 63, "learning_rate": 0.05, "min_child_samples": 100, "objective": "poisson"},
    {"num_leaves": 127, "learning_rate": 0.05, "min_child_samples": 200, "objective": "poisson"},
    {"num_leaves": 63, "learning_rate": 0.05, "min_child_samples": 100, "objective": "regression"},
]
LGB_BASE = {"feature_fraction": 0.8, "bagging_fraction": 0.8, "bagging_freq": 1,
            "verbose": -1, "seed": C.SEED, "n_jobs": -1}


def _log(run_name: str, params: dict, mets: dict, tags: dict | None = None):
    if mlflow is None:
        return
    with mlflow.start_run(run_name=run_name):
        mlflow.log_params({k: str(v)[:250] for k, v in params.items()})
        mlflow.log_metrics({k: float(v) for k, v in mets.items() if np.isfinite(v)})
        if tags:
            mlflow.set_tags(tags)


def fit_lgb(Xtr, ytr, Xva=None, yva=None, params=None, n_estimators=2000):
    p = {**LGB_BASE, **(params or {})}
    model = lgb.LGBMRegressor(n_estimators=n_estimators, **p)
    if Xva is not None:
        model.fit(Xtr, ytr, eval_set=[(Xva, yva)], eval_metric="l1",
                  callbacks=[lgb.early_stopping(100, verbose=False)])
    else:
        model.fit(Xtr, ytr)
    return model


def hist_avg_tables(train: pd.DataFrame):
    """Historical-average baselines fit on training rows only."""
    s = train.groupby("station_id")["departures"].mean().rename("ha_station")
    shw = train.groupby(["station_id", "hour_of_day", "is_weekend"])["departures"].mean().rename("ha_shw")
    return s, shw


def run(fast: bool = False) -> dict:
    t0 = time.time()
    df = build_features(load_ssot())
    cols_all = sorted({c for fs in FEATURE_SETS.values() for c in fs})
    meta = ["station_id", "hour", "date", "split", "departures", "arrivals", "dow", "is_weekend", "region"]
    df = df[list(dict.fromkeys(meta + cols_all))]
    for c in cols_all:
        if c not in ("hour_of_day", "dow", "is_weekend"):
            df[c] = df[c].astype("float32")
    import gc; gc.collect()
    med = impute_fit(df, cols_all)
    tr, va, te = (df[df["split"] == s].copy() for s in ("train", "val", "test"))
    trva = pd.concat([tr, va])
    y = "departures"
    results, tuning = [], []

    # ---------- baselines ----------
    for fit_df, score_dfs in ((tr, [va]), (trva, [te])):
        s, shw = hist_avg_tables(fit_df)
        for sd in score_dfs:
            sd["pred_HA_station"] = sd["station_id"].map(s).fillna(fit_df[y].mean())
            sd["pred_HA_shw"] = sd.set_index(["station_id", "hour_of_day", "is_weekend"]).index.map(shw)
            sd["pred_HA_shw"] = sd["pred_HA_shw"].fillna(sd["pred_HA_station"])
    for name in ("HA_station", "HA_shw"):
        for split, sd in (("val", va), ("test", te)):
            m = metrics(sd[y], sd[f"pred_{name}"])
            results.append({"model": name, "features": "-", "split": split, **m})
            _log(f"{name}-{split}", {"model": name}, m, {"split": split})

    # ---------- LightGBM per feature set (H1, H2, H4) ----------
    best_params = {}
    for fs_name, feats in FEATURE_SETS.items():
        best = None
        grid = LGB_GRID[:1] if fast else LGB_GRID
        for gp in grid:
            m = fit_lgb(tr[feats], tr[y], va[feats], va[y], gp)
            pv = np.clip(m.predict(va[feats]), 0, None)
            mv = metrics(va[y], pv)
            tuning.append({"features": fs_name, **gp, "best_iter": m.best_iteration_, **mv})
            _log(f"LGBM-{fs_name}-tune", {**gp, "features": fs_name, "best_iter": m.best_iteration_},
                 mv, {"stage": "tuning"})
            if best is None or mv["MAE"] < best[0]["MAE"]:
                best = (mv, gp, m.best_iteration_, pv)
        mv, gp, it, pv = best
        best_params[fs_name] = {**gp, "n_estimators": int(it)}
        va[f"pred_LGBM_{fs_name}"] = pv
        results.append({"model": "LGBM", "features": fs_name, "split": "val", **mv})
        final = fit_lgb(trva[feats], trva[y], params=gp, n_estimators=max(int(it * 1.1), 50))
        te[f"pred_LGBM_{fs_name}"] = np.clip(final.predict(te[feats]), 0, None)
        mt = metrics(te[y], te[f"pred_LGBM_{fs_name}"])
        results.append({"model": "LGBM", "features": fs_name, "split": "test", **mt})
        _log(f"LGBM-{fs_name}-test", {**gp, "features": fs_name}, mt, {"stage": "test"})
        if fs_name == "SCWL":
            joblib.dump({"model": final, "features": feats, "impute": med}, C.MODELS / "lgbm_scwl.joblib")
        print(f"[{time.time()-t0:6.0f}s] LGBM {fs_name}: val MAE {mv['MAE']:.4f} test MAE {mt['MAE']:.4f}")

    # ---------- H5: LR and RF on the same full feature set ----------
    feats = FEATURE_SETS["SCWL"]
    Xtr, Xva, Xte, Xtrva = (impute_apply(d[feats], med) for d in (tr, va, te, trva))
    lr = make_pipeline(StandardScaler(), LinearRegression()).fit(Xtr, tr[y])
    va["pred_LR_SCWL"] = np.clip(lr.predict(Xva), 0, None)
    lr = make_pipeline(StandardScaler(), LinearRegression()).fit(Xtrva, trva[y])
    te["pred_LR_SCWL"] = np.clip(lr.predict(Xte), 0, None)
    print(f"[{time.time()-t0:6.0f}s] LR done")

    rng = np.random.default_rng(C.SEED)
    n_sub = 150_000 if fast else 400_000
    rf_grid = [{"max_depth": 14, "min_samples_leaf": 20}, {"max_depth": 20, "min_samples_leaf": 10}]
    best_rf = None
    sub = rng.choice(len(Xtr), size=min(n_sub, len(Xtr)), replace=False)
    for gp in (rf_grid[:1] if fast else rf_grid):
        rf = RandomForestRegressor(n_estimators=100, max_features=0.5, n_jobs=-1,
                                   random_state=C.SEED, **gp)
        rf.fit(Xtr.iloc[sub], tr[y].iloc[sub])
        pv = np.clip(rf.predict(Xva), 0, None)
        mv = metrics(va[y], pv)
        tuning.append({"features": "SCWL", "model": "RF", **gp, **mv})
        _log("RF-SCWL-tune", gp, mv, {"stage": "tuning"})
        if best_rf is None or mv["MAE"] < best_rf[0]["MAE"]:
            best_rf = (mv, gp, pv)
    va["pred_RF_SCWL"] = best_rf[2]
    sub2 = rng.choice(len(Xtrva), size=min(n_sub, len(Xtrva)), replace=False)
    rf = RandomForestRegressor(n_estimators=100, max_features=0.5, n_jobs=-1,
                               random_state=C.SEED, **best_rf[1])
    rf.fit(Xtrva.iloc[sub2], trva[y].iloc[sub2])
    te["pred_RF_SCWL"] = np.clip(rf.predict(Xte), 0, None)
    print(f"[{time.time()-t0:6.0f}s] RF done")
    for name in ("LR", "RF"):
        for split, sd in (("val", va), ("test", te)):
            m = metrics(sd[y], sd[f"pred_{name}_SCWL"])
            results.append({"model": name, "features": "SCWL", "split": split, **m})
            _log(f"{name}-SCWL-{split}", {"model": name, **(best_rf[1] if name == "RF" else {})},
                 m, {"split": split})

    res = pd.DataFrame(results)
    res.to_csv(C.TABLES / "model_metrics.csv", index=False)
    pd.DataFrame(tuning).to_csv(C.TABLES / "tuning_results.csv", index=False)
    (C.TABLES / "best_params.json").write_text(json.dumps({**best_params, "RF": best_rf[1]}, indent=2))

    # ---------- hypothesis tests on test (and val as robustness) ----------
    comps = {
        "H1": ("pred_LGBM_S", "pred_LGBM_SC", "Hour/weekday features vs station-only"),
        "H2": ("pred_LGBM_SCL", "pred_LGBM_SCWL", "Weather vs calendar+past demand"),
        "H4": ("pred_LGBM_SCW", "pred_LGBM_SCWL", "Lags vs station+calendar+weather"),
        "H5a": ("pred_LR_SCWL", "pred_RF_SCWL", "Random Forest vs Linear Regression"),
        "H5b": ("pred_LR_SCWL", "pred_LGBM_SCWL", "LightGBM vs Linear Regression"),
    }
    hyp = []
    for h, (b, n, desc) in comps.items():
        for split, sd in (("val", va), ("test", te)):
            r = paired_test(sd, b, n)
            hyp.append({"hypothesis": h, "description": desc, "split": split, **r})
    hyp = pd.DataFrame(hyp)
    hyp.to_csv(C.TABLES / "hypothesis_forecast_tests.csv", index=False)

    keep = ["station_id", "hour", "date", "split", "departures", "arrivals", "hour_of_day",
            "dow", "is_weekend", "region"] + [c for c in te.columns if c.startswith("pred_")]
    out = pd.concat([va[keep], te[keep]], ignore_index=True)
    out.to_parquet(C.PREDICTIONS_PATH, index=False)
    print(f"done in {time.time()-t0:.0f}s")
    return {"metrics": res, "hypotheses": hyp}


if __name__ == "__main__":
    import sys
    r = run(fast="--fast" in sys.argv)
    pd.set_option("display.width", 200)
    print(r["metrics"].to_string())
    print(r["hypotheses"][["hypothesis", "split", "mae_base", "mae_new", "mae_reduction_pct",
                           "ci95_low", "ci95_high", "days_improved", "wilcoxon_p"]].to_string())
