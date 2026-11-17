"""Log all experiment results (metrics, tuning, simulation, artefacts) to MLflow.

    python -m bikebalance.track      then:  mlflow ui --backend-store-uri sqlite:///mlflow.db
"""
import json

import mlflow
import pandas as pd

from . import config as C

URI = "sqlite:///" + str(C.ROOT / "mlflow.db").replace("\\", "/")


def run():
    mlflow.set_tracking_uri(URI)
    mlflow.set_experiment("BikeBalance-forecasting")
    best = json.loads((C.TABLES / "best_params.json").read_text())
    for _, r in pd.read_csv(C.TABLES / "tuning_results.csv").iterrows():
        with mlflow.start_run(run_name=f"tune-{r.get('model', 'LGBM') if pd.notna(r.get('model')) else 'LGBM'}-{r['features']}"):
            mlflow.set_tag("stage", "tuning")
            mlflow.log_params({k: v for k, v in r.items() if k not in ("MAE", "RMSE", "Bias", "R2") and pd.notna(v)})
            mlflow.log_metrics({f"val_{k}": r[k] for k in ("MAE", "RMSE", "Bias", "R2")})
    m = pd.read_csv(C.TABLES / "model_metrics.csv")
    for (model, feats), g in m.groupby(["model", "features"]):
        with mlflow.start_run(run_name=f"final-{model}-{feats}"):
            mlflow.set_tag("stage", "final")
            mlflow.log_params({"model": model, "features": feats,
                               **{k: v for k, v in best.get(feats if model == "LGBM" else model, {}).items()}})
            for _, r in g.iterrows():
                mlflow.log_metrics({f"{r['split']}_{k}": r[k] for k in ("MAE", "RMSE", "Bias", "R2")})
            if model == "LGBM" and feats == "SCWL":
                mlflow.log_artifact(str(C.MODELS / "lgbm_scwl.joblib"))
                mlflow.log_artifact(str(C.FIGURES / "fig14_shap_summary.png"))
    mlflow.set_experiment("BikeBalance-simulation")
    s = pd.read_csv(C.TABLES / "simulation_summary.csv")
    for _, r in s.iterrows():
        with mlflow.start_run(run_name=f"sim-{r['scenario']}-{r['policy']}"):
            mlflow.log_params({"scenario": r["scenario"], "policy": r["policy"]})
            mlflow.log_metrics({k: float(r[k]) for k in ("coverage", "coverage_peak", "coverage_offpeak",
                                                          "unmet", "bikes_moved", "bike_km", "blocked_returns")})
    print("logged to", URI)


if __name__ == "__main__":
    run()
