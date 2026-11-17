"""Paired statistical comparisons on temporally blocked (daily) errors."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from . import config as C


def daily_abs_err(df: pd.DataFrame, pred_col: str, y: str = "departures") -> pd.Series:
    e = (df[pred_col] - df[y]).abs()
    return e.groupby(df["date"]).mean()


def paired_test(df: pd.DataFrame, base_col: str, new_col: str, y: str = "departures",
                n_boot: int = 2000) -> dict:
    """H: new model has lower MAE than base. Daily-blocked Wilcoxon (one-sided) and
    day-block bootstrap CI for the MAE difference (base - new; >0 = improvement)."""
    a = daily_abs_err(df, base_col, y)
    b = daily_abs_err(df, new_col, y)
    d = (a - b).values
    rng = np.random.default_rng(C.SEED)
    idx = rng.integers(0, len(d), size=(n_boot, len(d)))
    boots = d[idx].mean(axis=1)
    w = stats.wilcoxon(d, alternative="greater") if np.any(d != 0) else None
    mae_a = float((df[base_col] - df[y]).abs().mean())
    mae_b = float((df[new_col] - df[y]).abs().mean())
    return {
        "base": base_col, "new": new_col,
        "mae_base": mae_a, "mae_new": mae_b,
        "mae_reduction": mae_a - mae_b,
        "mae_reduction_pct": 100 * (mae_a - mae_b) / mae_a,
        "ci95_low": float(np.percentile(boots, 2.5)),
        "ci95_high": float(np.percentile(boots, 97.5)),
        "days": int(len(d)),
        "days_improved": int((d > 0).sum()),
        "wilcoxon_p": float(w.pvalue) if w is not None else 1.0,
    }


def metrics(y_true, y_pred) -> dict:
    y_true = np.asarray(y_true, float)
    y_pred = np.asarray(y_pred, float)
    err = y_pred - y_true
    return {
        "MAE": float(np.mean(np.abs(err))),
        "RMSE": float(np.sqrt(np.mean(err ** 2))),
        "Bias": float(np.mean(err)),
        "R2": float(1 - np.sum(err ** 2) / np.sum((y_true - y_true.mean()) ** 2)),
    }
