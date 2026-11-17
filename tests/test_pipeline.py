"""Data-contract and logic tests. Run: pytest -q"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from bikebalance import config as C  # noqa: E402
from bikebalance.simulation import plan_transfers  # noqa: E402

needs_ssot = pytest.mark.skipif(not C.SSOT_PATH.exists(), reason="run the pipeline first")


@needs_ssot
def test_ssot_conserves_trips_and_is_unique():
    df = pd.read_parquet(C.SSOT_PATH, columns=["station_id", "hour", "departures", "split"])
    assert df["departures"].sum() == 519_235
    assert not df.duplicated(["station_id", "hour"]).any()


@needs_ssot
def test_temporal_split_is_ordered():
    df = pd.read_parquet(C.SSOT_PATH, columns=["hour", "split"])
    assert df.loc[df.split == "train", "hour"].max() < df.loc[df.split == "val", "hour"].min()
    assert df.loc[df.split == "val", "hour"].max() < df.loc[df.split == "test", "hour"].min()


@needs_ssot
def test_lag_features_do_not_leak():
    from bikebalance.features import build_features
    df = pd.read_parquet(C.SSOT_PATH)
    s = df[df.station_id == df.station_id.iloc[0]].copy()
    f = build_features(s.assign(split=s["split"]))
    assert (f["lag_1"].iloc[1:].values == f["departures"].iloc[:-1].values).all()


def test_plan_transfers_respects_budget_and_conserves_bikes():
    inv = np.array([10, 0, 0, 5])
    target = np.array([2, 4, 4, 5])
    dist = np.array([[0, 1, 2, 3], [1, 0, 1, 2], [2, 1, 0, 1], [3, 2, 1, 0]], float)
    moves, new = plan_transfers(inv, target, np.full(4, 15), 5, dist)
    assert new.sum() == inv.sum()
    assert sum(m[2] for m in moves) == 5
    assert (new >= 0).all()
