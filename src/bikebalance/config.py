"""Central configuration: paths, temporal splits, seeds."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROC = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
TABLES = REPORTS / "tables"
MODELS = ROOT / "models"

for _p in (DATA_RAW, DATA_PROC, FIGURES, TABLES, MODELS):
    _p.mkdir(parents=True, exist_ok=True)

HF_REPO = "Krupa1420/la-metro-bikeshare-2024"
RAW_FILES = ["trips.csv", "stations.csv", "weather.csv"]

SSOT_VERSION = "v1.0"
SSOT_PATH = DATA_PROC / f"ssot_station_hour_{SSOT_VERSION}.parquet"
STATIONS_PATH = DATA_PROC / f"stations_registry_{SSOT_VERSION}.csv"
AUDIT_PATH = TABLES / "data_audit.json"
PREDICTIONS_PATH = DATA_PROC / "predictions_val_test.parquet"

# Temporal split (all stations split by time, never by station)
TRAIN_END = "2024-08-31 23:00:00"   # Jan-Aug
VAL_END = "2024-10-31 23:00:00"     # Sep-Oct
# test = Nov-Dec

SEED = 42
TZ = "America/Los_Angeles"
