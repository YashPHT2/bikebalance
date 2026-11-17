"""Run the full BikeBalance pipeline end to end.

    python run_pipeline.py            # full run (~20-30 min on a laptop)
    python run_pipeline.py --fast     # smaller tuning grid / RF sample
    python run_pipeline.py --from forecasting   # resume from a stage
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from bikebalance import eda, etl, evaluate, forecasting, simulation  # noqa: E402

STAGES = [
    ("etl", lambda fast: etl.build_ssot()),
    ("eda", lambda fast: eda.run()),
    ("forecasting", lambda fast: forecasting.run(fast=fast)),
    ("simulation", lambda fast: simulation.run()),
    ("evaluate", lambda fast: evaluate.run()),
]

if __name__ == "__main__":
    fast = "--fast" in sys.argv
    start = sys.argv[sys.argv.index("--from") + 1] if "--from" in sys.argv else STAGES[0][0]
    names = [s for s, _ in STAGES]
    t0 = time.time()
    for name, fn in STAGES[names.index(start):]:
        print(f"\n===== {name} =====")
        fn(fast)
        print(f"[{time.time() - t0:.0f}s] {name} complete")
