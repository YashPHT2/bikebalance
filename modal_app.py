"""Host the BikeBalance Streamlit demo on Modal.

    modal serve modal_app.py     # temporary dev URL (live reload)
    modal deploy modal_app.py    # persistent URL for the evaluation
"""
import shlex
import subprocess

import modal

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("pandas>=2.2", "numpy", "pyarrow", "scipy", "plotly>=5.20", "streamlit>=1.35",
                 "scikit-learn", "lightgbm", "joblib")
    .add_local_dir("src", "/app/src")
    .add_local_dir("app", "/app/app")
    .add_local_file("data/processed/predictions_val_test.parquet",
                    "/app/data/processed/predictions_val_test.parquet")
    .add_local_file("data/processed/stations_registry_v1.0.csv",
                    "/app/data/processed/stations_registry_v1.0.csv")
    .add_local_dir("reports/tables", "/app/reports/tables")
    .add_local_dir("reports/figures", "/app/reports/figures")
)

app = modal.App("bikebalance-demo", image=image)


@app.function(timeout=3600, scaledown_window=1200, min_containers=0)
@modal.concurrent(max_inputs=50)
@modal.web_server(8501, startup_timeout=180)
def streamlit():
    cmd = ("streamlit run /app/app/streamlit_app.py --server.port 8501 --server.address 0.0.0.0 "
           "--server.enableCORS=false --server.enableXsrfProtection=false --server.headless true")
    subprocess.Popen(shlex.split(cmd), cwd="/app")
