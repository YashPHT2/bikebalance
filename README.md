# BikeBalance: Smart Bicycle Redistribution System

ADS (CSE3105) end-term project, **Group 12**, BML Munjal University:
Sahil Yadav (240624), Shorya (240643), Yash Kumar Sharma (240698), Tejas Duggal (240672).

A bike-share operations manager has to decide which stations to replenish before the next hour.
BikeBalance does three things:

* forecasts next-hour departures at every LA Metro Bike Share station;
* checks seven pre-registered hypotheses (H1–H7);
* turns the forecasts into budget-limited transfer plans, evaluated in a simulation that keeps the fleet size fixed.

## Results (test period Nov–Dec 2024)

| | Result |
|---|---|
| Best model | LightGBM with station + calendar + lag features, **MAE 0.278** (about 10% lower than the historical-average baseline at 0.310) |
| H1 calendar features help | **Supported** (−14.9% MAE) |
| H2 weather helps beyond calendar + lags | **Not supported** (+1.2% MAE) |
| H3 forecast transfers reduce unmet demand | **Partially supported**: better in 6/6 scenarios, significant in 3/6 (the tight-budget ones) |
| H4 lag features help | **Supported** (−8.6% MAE, better on 61/61 days) |
| H5 tree ensembles beat Linear Regression | **Supported** (LightGBM −2.2%, Random Forest −1.0%) |
| H6 top 20% of stations carry > 50% of later demand | **Supported** (55.4%, 95% CI 54.8–55.8%) |
| H7 bigger gains at peak hours | **Not supported** (significant in 1/6 scenarios) |

## Repository layout

```
src/bikebalance/   config, etl, features, forecasting, stats, simulation, evaluate, eda, track
app/               Streamlit demo (planner, forecast explorer, model comparison, hypotheses, data audit)
tests/             pytest data-contract tests
reports/           figures/, tables/, build_report.py, build_slides.py
deliverables/      final report (DOCX/PDF) and presentation (PPTX/PDF)
Dockerfile         container serving the demo
modal_app.py       hosted demo on Modal
run_pipeline.py    runs the full pipeline end to end
```

## Reproduce

```bash
pip install -r requirements.txt
python run_pipeline.py            # downloads the data, builds the SSOT, then runs EDA, models, simulation, SHAP (~20 min)
python -m pytest -q tests
python -m bikebalance.track       # run from src/; logs results to mlflow.db
streamlit run app/streamlit_app.py
```

Docker: `docker build -t bikebalance . && docker run -p 8501:8501 bikebalance`
Modal: `modal deploy modal_app.py`
MLflow UI: `mlflow ui --backend-store-uri sqlite:///mlflow.db`

To rebuild the documents: `python reports/build_report.py --pdf` and `python reports/build_slides.py`.

## Data

LA Metro Bike Share 2024 from Hugging Face: [Krupa1420/la-metro-bikeshare-2024](https://huggingface.co/datasets/Krupa1420/la-metro-bikeshare-2024).
The original source is [bikeshare.metro.net/about/data](https://bikeshare.metro.net/about/data/).
Raw data is not committed to this repo; `etl.download_raw()` fetches it.
