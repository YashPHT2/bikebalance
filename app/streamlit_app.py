"""BikeBalance live demo (Streamlit).

Run:  streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from bikebalance import config as C  # noqa: E402
from bikebalance.simulation import haversine_matrix, plan_transfers  # noqa: E402

st.set_page_config(page_title="BikeBalance", page_icon=":bike:", layout="wide")


@st.cache_data
def load():
    preds = pd.read_parquet(C.PREDICTIONS_PATH)
    reg = pd.read_csv(C.STATIONS_PATH)
    metrics = pd.read_csv(C.TABLES / "model_metrics.csv")
    hyp_f = pd.read_csv(C.TABLES / "hypothesis_forecast_tests.csv")
    sim_s = pd.read_csv(C.TABLES / "simulation_summary.csv")
    hyp_s = pd.read_csv(C.TABLES / "hypothesis_simulation_tests.csv")
    h6 = json.loads((C.TABLES / "h6_result.json").read_text())
    audit = json.loads(C.AUDIT_PATH.read_text())
    return preds, reg, metrics, hyp_f, sim_s, hyp_s, h6, audit


preds, reg, metrics, hyp_f, sim_s, hyp_s, h6, audit = load()
names = reg.set_index("station_id")["station_name"].to_dict()

st.sidebar.title("BikeBalance")
st.sidebar.caption("Smart Bicycle Redistribution System · ADS Group 12")
page = st.sidebar.radio("View", ["Operations planner", "Forecast explorer", "Model comparison",
                                 "Hypotheses H1-H7", "Data & SSOT"])

# ---------------------------------------------------------------- planner
if page == "Operations planner":
    st.title("Next-hour replenishment planner")
    st.caption("Pick an hour in the hold-out test period. The model forecasts departures for every "
               "station; set current stock and truck budget, and BikeBalance recommends transfers.")
    test = preds[preds["split"] == "test"]
    c1, c2, c3, c4 = st.columns(4)
    day = c1.date_input("Date", value=pd.Timestamp("2024-11-14").date(),
                        min_value=pd.Timestamp("2024-11-01").date(), max_value=pd.Timestamp("2024-12-31").date())
    hr = c2.slider("Hour", 0, 23, 8)
    budget = c3.slider("Truck budget (bikes)", 0, 100, 25, step=5)
    cap = c4.slider("Dock capacity", 8, 40, 15)
    c5, c6 = st.columns(2)
    stock_mode = c5.selectbox("Current stock assumption", ["Random (seeded)", "All half-full", "Busy stations empty"])
    model_col = c6.selectbox("Forecast source", ["pred_LGBM_SCWL", "pred_HA_shw", "pred_RF_SCWL", "pred_LR_SCWL"],
                             format_func=lambda c: {"pred_LGBM_SCWL": "LightGBM (best)", "pred_HA_shw": "Historical average",
                                                    "pred_RF_SCWL": "Random Forest", "pred_LR_SCWL": "Linear Regression"}[c])
    t = pd.Timestamp(day) + pd.Timedelta(hours=hr)
    cur = test[test["hour"] == t].copy()
    if cur.empty:
        st.warning("No data for this hour.")
        st.stop()
    cur = cur.merge(reg[["station_id", "station_name", "lat", "lon"]], on="station_id", how="left").dropna(subset=["lat"])
    rng = np.random.default_rng(int(t.timestamp()) % 10_000)
    if stock_mode == "Random (seeded)":
        inv = rng.integers(0, cap + 1, len(cur))
    elif stock_mode == "All half-full":
        inv = np.full(len(cur), cap // 2)
    else:
        inv = np.full(len(cur), cap // 2)
        inv[np.argsort(-cur[model_col].values)[:15]] = 0
    f = cur[model_col].values
    target = np.minimum(cap, np.ceil(f + np.sqrt(f))).astype(int)
    dist = haversine_matrix(cur["lat"].values, cur["lon"].values)
    moves, new_inv = plan_transfers(inv.astype(int), target, np.full(len(cur), cap), budget, dist)
    cur["stock_before"], cur["target"], cur["stock_after"] = inv, target, new_inv
    cur["forecast"] = f.round(2)
    cur["at_risk_before"] = np.maximum(cur["departures"] - cur["stock_before"], 0)
    cur["at_risk_after"] = np.maximum(cur["departures"] - cur["stock_after"], 0)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Forecast departures (system)", f"{f.sum():.0f}", f"actual {cur['departures'].sum()}")
    k2.metric("Bikes moved", int(sum(m[2] for m in moves)), f"{sum(m[2]*m[3] for m in moves):.1f} bike-km")
    k3.metric("Stations below target", int((inv < target).sum()),
              f"{int((new_inv < target).sum()) - int((inv < target).sum())} with plan", delta_color="inverse")
    k4.metric("Realised trips lost (no bike)", int(cur["at_risk_before"].sum()),
              f"{int(cur['at_risk_after'].sum() - cur['at_risk_before'].sum())} with plan", delta_color="inverse")

    cur["status"] = np.where(cur["stock_after"] > cur["stock_before"], "Receives bikes",
                    np.where(cur["stock_after"] < cur["stock_before"], "Donates bikes", "No change"))
    m1, m2 = st.columns([3, 1])
    region = m1.radio("Map area", ["All", "DTLA", "Westside", "North Hollywood"], horizontal=True)
    tiles = m2.toggle("Street basemap (needs internet)", value=False)
    cur = cur.merge(reg[["station_id", "region"]], on="station_id", how="left", suffixes=("", "_r"))
    view = cur if region == "All" else cur[cur["region"] == region]
    kw = dict(color="status", size=np.maximum(view["forecast"], 0.2) * 6, hover_name="station_name",
              hover_data={"forecast": True, "stock_before": True, "stock_after": True, "departures": True,
                          "lat": False, "lon": False},
              color_discrete_map={"Receives bikes": "#2a9d55", "Donates bikes": "#e07a2f", "No change": "#7f8c9a"},
              height=540)
    if tiles:
        fig = px.scatter_map(view, lat="lat", lon="lon", zoom=10.3 if region == "All" else 12.5,
                             map_style="carto-positron", **kw)
        line_trace = go.Scattermap
    else:
        fig = px.scatter(view, x="lon", y="lat", **kw)
        fig.update_yaxes(scaleanchor="x", scaleratio=1.21, showgrid=False, title=None, showticklabels=False)
        fig.update_xaxes(showgrid=False, title=None, showticklabels=False)
        fig.update_layout(plot_bgcolor="#eef2f5")
        line_trace = None
    sid = cur["station_id"].values
    pos = cur.set_index("station_id")[["lat", "lon"]]
    keep = set(view["station_id"])
    for d, r, n, km in moves:
        if sid[d] not in keep and sid[r] not in keep:
            continue
        a, b = pos.loc[sid[d]], pos.loc[sid[r]]
        if line_trace is not None:
            fig.add_trace(line_trace(lat=[a.lat, b.lat], lon=[a.lon, b.lon], mode="lines",
                                     line=dict(width=1 + n, color="#2a6f97"), showlegend=False,
                                     hoverinfo="text", text=f"{n} bikes"))
        else:
            fig.add_annotation(x=b.lon, y=b.lat, ax=a.lon, ay=a.lat, xref="x", yref="y", axref="x", ayref="y",
                               showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=1 + n * 0.6,
                               arrowcolor="#2a6f97", opacity=0.8)
    fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), legend=dict(orientation="h", y=1.06, title=None))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Recommended transfers")
    if moves:
        mv = pd.DataFrame([(sid[d], names.get(sid[d], sid[d]), sid[r], names.get(sid[r], sid[r]), n, round(km, 2))
                           for d, r, n, km in moves],
                          columns=["from_id", "from_station", "to_id", "to_station", "bikes", "km"])
        st.dataframe(mv, use_container_width=True, hide_index=True)
        st.download_button("Download plan (CSV)", mv.to_csv(index=False), f"transfer_plan_{t:%Y%m%d_%H}.csv")
    else:
        st.info("No transfers needed (or budget is 0).")
    with st.expander("Station table"):
        st.dataframe(cur[["station_id", "station_name", "forecast", "departures", "stock_before", "target",
                          "stock_after"]].sort_values("forecast", ascending=False), hide_index=True,
                     use_container_width=True)

# ---------------------------------------------------------------- forecast explorer
elif page == "Forecast explorer":
    st.title("Forecast explorer")
    vol = preds.groupby("station_id")["departures"].sum().sort_values(ascending=False)
    opts = list(vol.index)
    s = st.selectbox("Station", opts, format_func=lambda x: f"{x} · {names.get(x, '')} ({vol[x]} trips)")
    split = st.radio("Period", ["test", "val"], horizontal=True,
                     format_func=lambda x: {"test": "Test (Nov-Dec)", "val": "Validation (Sep-Oct)"}[x])
    d = preds[(preds["station_id"] == s) & (preds["split"] == split)].sort_values("hour")
    rng_d = st.slider("Days shown", 2, 30, 7)
    d = d[d["hour"] < d["hour"].min() + pd.Timedelta(days=rng_d)]
    cols = st.multiselect("Models", ["pred_LGBM_SCWL", "pred_RF_SCWL", "pred_LR_SCWL", "pred_HA_shw"],
                          default=["pred_LGBM_SCWL", "pred_HA_shw"])
    fig = go.Figure()
    fig.add_bar(x=d["hour"], y=d["departures"], name="Actual", marker_color="#c9d6e3")
    for c in cols:
        fig.add_scatter(x=d["hour"], y=d[c], name=c.replace("pred_", ""), mode="lines")
    fig.update_layout(height=430, yaxis_title="Departures / hour", margin=dict(t=10))
    st.plotly_chart(fig, use_container_width=True)
    full = preds[(preds["station_id"] == s) & (preds["split"] == split)]
    st.dataframe(pd.DataFrame({c.replace("pred_", ""): {"MAE": (full[c] - full["departures"]).abs().mean(),
                                                         "RMSE": np.sqrt(((full[c] - full["departures"]) ** 2).mean())}
                               for c in ["pred_LGBM_SCWL", "pred_RF_SCWL", "pred_LR_SCWL", "pred_HA_shw", "pred_HA_station"]}).T.round(4))

# ---------------------------------------------------------------- model comparison
elif page == "Model comparison":
    st.title("Model comparison (temporal hold-out)")
    m = metrics.copy()
    m["label"] = m["model"] + np.where(m["features"] != "-", " · " + m["features"], "")
    split = st.radio("Split", ["test", "val"], horizontal=True)
    mm = m[m["split"] == split].sort_values("MAE")
    st.plotly_chart(px.bar(mm, x="MAE", y="label", orientation="h", text=mm["MAE"].round(4),
                           height=420), use_container_width=True)
    st.dataframe(mm[["label", "MAE", "RMSE", "Bias", "R2"]].round(4), hide_index=True, use_container_width=True)
    shap_png = C.FIGURES / "fig14_shap_summary.png"
    if shap_png.exists():
        st.subheader("SHAP explanation of LightGBM (SCWL)")
        st.image(str(shap_png))
    st.caption("Feature sets: S = station only, C = calendar, W = weather lagged 1h, L = past-departure lags.")

# ---------------------------------------------------------------- hypotheses
elif page == "Hypotheses H1-H7":
    st.title("Hypothesis results")
    ht = hyp_f[hyp_f["split"] == "test"].copy()
    ht["verdict"] = np.where((ht["wilcoxon_p"] < 0.05) & (ht["ci95_low"] > 0), "Supported", "Not supported")
    st.subheader("Forecasting hypotheses (test, daily-blocked Wilcoxon + bootstrap CI)")
    st.dataframe(ht[["hypothesis", "description", "mae_base", "mae_new", "mae_reduction_pct", "ci95_low",
                     "ci95_high", "days_improved", "days", "wilcoxon_p", "verdict"]].round(4),
                 hide_index=True, use_container_width=True)
    st.subheader("H6 · Station concentration")
    st.write(h6)
    st.subheader("H3 / H7 · Simulation")
    st.dataframe(hyp_s.round(4), hide_index=True, use_container_width=True)
    sc = st.selectbox("Scenario", sorted(sim_s["scenario"].unique()))
    ss = sim_s[sim_s["scenario"] == sc]
    st.plotly_chart(px.bar(ss, x="policy", y=["coverage_peak", "coverage_offpeak"], barmode="group",
                           range_y=[ss[["coverage_peak", "coverage_offpeak"]].min().min() - 0.02, 1.0],
                           height=380), use_container_width=True)
    st.dataframe(ss.round(4), hide_index=True, use_container_width=True)

# ---------------------------------------------------------------- data
else:
    st.title("Data integration & SSOT")
    c = st.columns(4)
    c[0].metric("Raw trips", f"{audit['raw_trips']:,}")
    c[1].metric("SSOT station-hours", f"{audit['ssot_rows']:,}")
    c[2].metric("Stations (after recovery)", audit["ssot_stations"])
    c[3].metric("Recovered station IDs", audit["stations_recovered_from_trips"])
    st.json(audit, expanded=False)
    for f in sorted(C.FIGURES.glob("fig0*.png")) + sorted(C.FIGURES.glob("fig10*.png")):
        st.image(str(f), caption=f.stem)

