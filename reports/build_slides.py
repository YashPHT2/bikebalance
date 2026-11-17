"""Build the presentation deck (PPTX) from result tables and figures.
    python reports/build_slides.py
"""
import json
from pathlib import Path

import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
T, F = ROOT / "reports" / "tables", ROOT / "reports" / "figures"
OUT = ROOT / "deliverables" / "BikeBalance_Presentation_Group12.pptx"

NAVY, ORANGE, GREY, LIGHT, GREEN, RED = (RGBColor(0x1F, 0x3A, 0x5F), RGBColor(0xE0, 0x7A, 0x2F),
                                         RGBColor(0x55, 0x60, 0x6E), RGBColor(0xF3, 0xF6, 0xF9),
                                         RGBColor(0x2A, 0x9D, 0x55), RGBColor(0xC0, 0x39, 0x2B))
A = json.loads((T / "data_audit.json").read_text())
E = json.loads((T / "eda_summary.json").read_text())
H6 = json.loads((T / "h6_result.json").read_text())
M = pd.read_csv(T / "model_metrics.csv")
HF = pd.read_csv(T / "hypothesis_forecast_tests.csv")
HT = HF[HF["split"] == "test"].set_index("hypothesis")
HS = pd.read_csv(T / "hypothesis_simulation_tests.csv").set_index("scenario")
S = pd.read_csv(T / "simulation_summary.csv")


def mae(m, f):
    return float(M[(M.model == m) & (M.features == f) & (M.split == "test")]["MAE"].iloc[0])


prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
W, H = prs.slide_width, prs.slide_height
N = [0]


def text(slide, x, y, w, h, s, size=18, bold=False, color=GREY, align=PP_ALIGN.LEFT):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    lines = s if isinstance(s, list) else [s]
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        bullet = isinstance(s, list)
        parts = line.split("**")
        if bullet:
            r0 = p.add_run()
            r0.text = "•  "
            r0.font.size, r0.font.color.rgb = Pt(size), ORANGE
        for j, part in enumerate(parts):
            r = p.add_run()
            r.text = part
            r.font.size, r.font.bold = Pt(size), bold or j % 2 == 1
            r.font.color.rgb = NAVY if (j % 2 == 1 and not bold) else color
            r.font.name = "Calibri"
        p.alignment = align
        p.space_after = Pt(8 if bullet else 2)
    return tb


def slide(title, subtitle=None):
    s = prs.slides.add_slide(BLANK)
    N[0] += 1
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, Inches(0.12))
    bar.fill.solid(); bar.fill.fore_color.rgb = ORANGE; bar.line.fill.background()
    text(s, 0.6, 0.35, 12, 0.8, title, 30, True, NAVY)
    if subtitle:
        text(s, 0.6, 1.05, 12, 0.5, subtitle, 15, False, GREY)
    text(s, 0.6, 7.0, 9, 0.4, "BikeBalance  |  ADS Group 12  |  BML Munjal University", 10, False, GREY)
    text(s, 12.2, 7.0, 0.8, 0.4, str(N[0]), 10, False, GREY, PP_ALIGN.RIGHT)
    return s


def img(s, name, x, y, w=None, h=None):
    kw = {}
    if w: kw["width"] = Inches(w)
    if h: kw["height"] = Inches(h)
    return s.shapes.add_picture(str(F / f"{name}.png"), Inches(x), Inches(y), **kw)


def card(s, x, y, w, h, big, small, color=NAVY):
    b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    b.fill.solid(); b.fill.fore_color.rgb = LIGHT; b.line.color.rgb = RGBColor(0xD5, 0xDE, 0xE8)
    b.adjustments[0] = 0.08
    text(s, x + 0.15, y + 0.12, w - 0.3, h * 0.55, big, 28, True, color, PP_ALIGN.CENTER)
    text(s, x + 0.15, y + h * 0.55, w - 0.3, h * 0.45, small, 12, False, GREY, PP_ALIGN.CENTER)


def table(s, df, x, y, w, h, size=12, verdict_col=None, widths=None):
    shp = s.shapes.add_table(len(df) + 1, len(df.columns), Inches(x), Inches(y), Inches(w), Inches(h))
    t = shp.table
    for j, c in enumerate(df.columns):
        cell = t.cell(0, j); cell.text = str(c)
        cell.fill.solid(); cell.fill.fore_color.rgb = NAVY
        for p in cell.text_frame.paragraphs:
            for r in p.runs:
                r.font.size, r.font.bold, r.font.color.rgb = Pt(size), True, RGBColor(255, 255, 255)
    for i, row in enumerate(df.itertuples(index=False), 1):
        for j, v in enumerate(row):
            cell = t.cell(i, j); cell.text = str(v)
            cell.fill.solid(); cell.fill.fore_color.rgb = LIGHT if i % 2 else RGBColor(255, 255, 255)
            for p in cell.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size, r.font.color.rgb = Pt(size), GREY
                    if verdict_col is not None and j == verdict_col:
                        r.font.bold = True
                        r.font.color.rgb = GREEN if str(v).startswith("Supported") else (
                            ORANGE if str(v).startswith("Partial") else RED)
    if widths:
        for j, cw in enumerate(widths):
            t.columns[j].width = Inches(cw)
    return t


# 1 Title -----------------------------------------------------------------
s = prs.slides.add_slide(BLANK); N[0] += 1
bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, H); bg.fill.solid(); bg.fill.fore_color.rgb = NAVY
bg.line.fill.background()
acc = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(3.55), Inches(1.6), Inches(0.08))
acc.fill.solid(); acc.fill.fore_color.rgb = ORANGE; acc.line.fill.background()
text(s, 0.8, 1.5, 11, 1.2, "BikeBalance", 54, True, RGBColor(255, 255, 255))
text(s, 0.8, 2.6, 11, 0.8, "Smart Bicycle Redistribution System", 28, False, RGBColor(0xDD, 0xE6, 0xF0))
text(s, 0.8, 3.9, 11, 0.6, "Forecasting next-hour station demand and turning it into transfer decisions - LA Metro Bike Share 2024",
     16, False, RGBColor(0xDD, 0xE6, 0xF0))
text(s, 0.8, 5.0, 12, 1.2, ["Sahil Yadav (240624)   Shorya (240643)   Yash Kumar Sharma (240698)   Tejas Duggal (240672)"],
     14, False, RGBColor(255, 255, 255))
text(s, 0.8, 6.3, 12, 0.5, "Advanced Data Science (CSE3105)  |  Group 12  |  BML Munjal University  |  November 2026",
     13, False, RGBColor(0xB8, 0xC7, 0xD9))
s.shapes.add_picture(str(ROOT / "reports" / "assets" / "bml_logo.png"), Inches(11.2), Inches(0.6), height=Inches(1.4))

# 2 Problem ---------------------------------------------------------------
s = slide("The problem: bikes are in the wrong place", "B - Business question (BADIR)")
text(s, 0.6, 1.7, 6.4, 5, [
    "**Stakeholder:** bike-share operations manager",
    "**Decision:** which stations to replenish before the next hour, under a limited truck budget",
    f"Flows are one-directional: **{E['stations_net_negative']}** stations were net sources in Jan-Aug",
    "Empty dock = lost rental; unnecessary move = wasted crew time",
    "**KPIs:** unmet demand, coverage (served / demand), bikes moved, bike-km"], 17)
img(s, "fig09_net_flow", 7.2, 1.6, w=5.6)

# 3 Hypotheses ------------------------------------------------------------
s = slide("Research questions and hypotheses", "A - Analysis plan, pre-registered at the pre-submission viva")
hyp = pd.DataFrame([
    ("H1", "Hour and weekday features beat a station-only baseline"),
    ("H2", "Forecast-time weather helps beyond calendar + past demand"),
    ("H3", "Forecast-based transfers reduce unmet demand vs historical-average transfers"),
    ("H4", "Past-departure lags help beyond station, calendar, weather"),
    ("H5", "Tree ensembles beat Linear Regression on the same features"),
    ("H6", "Top 20% of stations (ranked on train) carry > 50% of later departures"),
    ("H7", "Forecast transfers give larger coverage gains at peak than off-peak"),
], columns=["", "Hypothesis"])
table(s, hyp, 0.6, 1.7, 12.1, 4.2, 15, widths=[1.0, 11.1])
text(s, 0.6, 6.15, 12, 0.7, "Supported only if one-sided paired test p < 0.05 on the untouched test period AND 95% bootstrap CI excludes 0.",
     14, False, NAVY)

# 4 Data ------------------------------------------------------------------
s = slide("Data and single source of truth", "D - Data: Hugging Face mirror of official LA Metro open data")
card(s, 0.6, 1.7, 2.9, 1.3, f"{A['raw_trips']:,}", "trips x 14 columns (2024)")
card(s, 3.7, 1.7, 2.9, 1.3, "226 + 26", "stations + recovered IDs")
card(s, 6.8, 1.7, 2.9, 1.3, "8,784", "hourly weather rows")
card(s, 9.9, 1.7, 2.9, 1.3, f"{A['ssot_rows']/1e6:.2f}M", "station-hours x 25 (SSOT v1.0)", ORANGE)
text(s, 0.6, 3.3, 12.2, 3.6, [
    f"**{A['unmatched_origin_trips_vs_raw_registry']:,} trips** started at IDs missing from the registry -> **recovered 26 stations** from median trip coordinates (flagged, nothing dropped)",
    "Weather duplicate 2024-11-03 01:00 and gap 2024-03-10 02:00 = **DST transitions** -> weather is local time; averaged / interpolated",
    "Assertions: 519,235 departures conserved after aggregation; many-to-one joins; row counts unchanged",
    "Zero-fill only inside each station's active window; imputers fitted on training data only",
    "Unit flag: 'wind m/s' mean 11.8, max 53.6 - looks like km/h (does not affect tree models)"], 16)

# 5 EDA -------------------------------------------------------------------
s = slide("What the data shows", "I - Insights from EDA")
img(s, "fig03_hourly_profile", 0.4, 1.5, w=6.3)
img(s, "fig05_weather_effect", 6.8, 1.5, w=6.2)
text(s, 0.6, 5.0, 12.2, 2, [
    "Commuter double peak on weekdays, single midday peak on weekends (Kruskal-Wallis p < 0.001)",
    f"Rain hours: **{E['dep_dry_vs_rain'][1]:.0f}** vs **{E['dep_dry_vs_rain'][0]:.0f}** departures/h - but only {E['rain_hours_daytime']} daytime rain hours all year",
    f"84% of station-hours are zero; strong memory: ACF lag-1 {E['acf_busiest']['lag1']:.2f}, lag-24 {E['acf_busiest']['lag24']:.2f}, lag-168 {E['acf_busiest']['lag168']:.2f}"], 15)

# 6 Method ----------------------------------------------------------------
s = slide("Method: controlled comparisons on a strict time split")
img(s, "fig00_workflow", 0.4, 1.2, w=12.5)
text(s, 0.6, 5.6, 12.2, 1.4, [
    "Train Jan-Aug | tune on Sep-Oct | test once on Nov-Dec - all stations split by time",
    "Feature groups S (station), C (calendar), W (weather at h-1), L (lags) - each hypothesis adds exactly one group",
    "Daily-blocked Wilcoxon + day-block bootstrap CI (61 test days)"], 15)

# 7 Models ----------------------------------------------------------------
s = slide("Forecast accuracy", "HA vs Linear Regression vs Random Forest vs LightGBM")
img(s, "fig11_model_mae", 0.4, 1.5, w=8.2)
card(s, 8.9, 1.6, 3.9, 1.5, f"{mae('LGBM','SCL'):.3f}", "best test MAE (LightGBM, S+C+L)", ORANGE)
card(s, 8.9, 3.3, 3.9, 1.5, f"-{100*(1-mae('LGBM','SCL')/mae('HA_shw','-')):.0f}%", "MAE vs historical-average baseline")
text(s, 8.9, 5.0, 4.0, 1.9, ["Poisson objective, 127 leaves, early stopping",
                             "Recent demand is the key signal"], 14)

# 8 Hypotheses forecasting -------------------------------------------------
s = slide("Hypothesis results - forecasting (test period)")
rows = []
for h, lab in (("H1", "H1 calendar"), ("H2", "H2 weather"), ("H4", "H4 lags"), ("H5b", "H5 LGBM vs LR"), ("H5a", "H5 RF vs LR")):
    r = HT.loc[h]
    ok = r["wilcoxon_p"] < 0.05 and r["ci95_low"] > 0
    rows.append((lab, f"{r['mae_base']:.4f}", f"{r['mae_new']:.4f}", f"{r['mae_reduction_pct']:+.1f}%",
                 f"{int(r['days_improved'])}/61", "< 0.001" if r["wilcoxon_p"] < 0.001 else f"{r['wilcoxon_p']:.3f}",
                 "Supported" if ok else "Not supported"))
table(s, pd.DataFrame(rows, columns=["Test", "MAE base", "MAE new", "Improvement", "Days better", "p", "Verdict"]),
      0.6, 1.5, 12.1, 3.2, 15, verdict_col=6)
text(s, 0.6, 5.0, 12.2, 2, [
    "**H2 rejected:** once last hour's demand is known, weather adds nothing - rain already shows up in the lags; rain is rare; temperature drifts seasonally (PSI 0.25)",
    "**Lags (H4)** improved every one of the 61 test days - the single most valuable information"], 15)

# 9 H6 --------------------------------------------------------------------
s = slide("H6: demand is concentrated - and stable")
img(s, "fig04_station_lorenz", 0.6, 1.4, h=5.3)
card(s, 7.3, 1.7, 5.4, 1.5, f"{100*H6['top20_share_later_SepDec']:.1f}%", "of Sep-Dec departures from the 49 stations ranked top-20% on Jan-Aug", ORANGE)
card(s, 7.3, 3.4, 5.4, 1.5, f"{H6['days_share_above_50pct']}/{H6['days']}", "days with share above 50%")
text(s, 7.3, 5.2, 5.5, 1.6, [f"95% CI [{100*H6['ci95'][0]:.1f}%, {100*H6['ci95'][1]:.1f}%], p < 0.001 -> **Supported**",
                             "Use as a fixed priority list for crews"], 15)

# 10 Simulation -----------------------------------------------------------
ref = S[S.scenario == "cap15_B25"].set_index("policy")
s = slide("H3 / H7: does forecasting improve rebalancing?", "Trip-level simulation, Nov-Dec, fleet conserved, 6 capacity x budget scenarios")
img(s, "fig16_simulation", 0.3, 1.5, w=8.4)
table(s, pd.DataFrame([(p, f"{100*ref.loc[p,'coverage']:.1f}%", f"{int(ref.loc[p,'unmet']):,}", f"{int(ref.loc[p,'bikes_moved']):,}")
                       for p in ("none", "HA", "forecast", "oracle")], columns=["Policy", "Coverage", "Unmet", "Moved"]),
      8.9, 1.6, 4.1, 2.2, 13)
n3 = int(((HS["H3_wilcoxon_p"] < 0.05)).sum())
n7 = int(((HS["H7_wilcoxon_p"] < 0.05) & (HS["H7_gain_peak_pp"] > HS["H7_gain_offpeak_pp"])).sum())
text(s, 8.9, 4.0, 4.2, 3, [f"Forecast < HA unmet in **6/6** scenarios, with fewer bikes moved",
                           f"Significant in **{n3}/6** (tight budget / capacity) -> **H3 partially supported**",
                           f"Peak > off-peak gain significant in {n7}/6 -> **H7 not supported**"], 13)

# 11 SHAP -----------------------------------------------------------------
s = slide("Why the model predicts what it does (SHAP)")
img(s, "fig14_shap_summary", 0.5, 1.2, h=5.6)
text(s, 8.3, 1.6, 4.6, 5, ["**Hour of day** dominates", "Then weekly rolling mean, station level and **arrivals in the last hour**",
                           "Weather features rank low - consistent with H2", "Drift monitoring: PSI weekly; retrain if PSI > 0.25 or MAE +10%"], 16)

# 12 Demo -----------------------------------------------------------------
s = slide("Live demo: BikeBalance planner", "Streamlit app - runs locally, in Docker, or hosted on Modal")
img(s, "fig17_app_planner", 0.5, 1.5, h=5.2)
text(s, 8.2, 1.7, 4.8, 5, ["Pick an hour, stock scenario, truck budget, capacity",
                           "Model forecasts every station; planner pairs deficits with **nearest donors**",
                           "Map + downloadable transfer list", "Forecast explorer, model comparison, hypotheses, data audit",
                           "MLflow tracking, pytest data contracts, Dockerfile"], 15)

# 13 Conclusions ------------------------------------------------------------
s = slide("Conclusions and recommendations", "R - Recommendations")
verd = pd.DataFrame([("H1", "Supported"), ("H2", "Not supported"), ("H3", "Partially supported"), ("H4", "Supported"),
                     ("H5", "Supported"), ("H6", "Supported"), ("H7", "Not supported")], columns=["", "Verdict"])
table(s, verd, 0.6, 1.6, 3.6, 4.2, 15, verdict_col=1, widths=[0.9, 2.7])
text(s, 4.7, 1.6, 8.2, 5.2, [
    "Deploy LightGBM with station + calendar + **lag** features; skip weather at a 1-hour horizon",
    "Rebalance with target = forecast + 1 SD; prioritise the **49 high-volume stations**",
    "Forecast planning never lost to historical averages and **moves fewer bikes**; biggest value when trucks are scarce",
    "Next: real dock inventories (GBFS), multi-hour look-ahead + routing, probabilistic forecasts, field A/B pilot",
    "Limitations: simulated inventory/capacity; censored demand; one year, one city"], 16)

# 14 Team + thanks -------------------------------------------------------------
s = slide("Team contributions")
team = pd.DataFrame([
    ("Sahil Yadav", "240624", "Business analysis, KPIs, BADIR, EDA"),
    ("Shorya", "240643", "Data integration, ETL & audit, SSOT"),
    ("Yash Kumar Sharma", "240698", "Features, forecasting models, H1/H2/H4/H5, SHAP, MLflow"),
    ("Tejas Duggal", "240672", "Simulation & validation, H3/H6/H7, demo, deployment"),
], columns=["Member", "ID", "Lead responsibility"])
table(s, team, 0.6, 1.6, 12.1, 2.6, 16, widths=[3.2, 1.6, 7.3])
text(s, 0.6, 4.8, 12.1, 1.2, "Thank you - questions?", 36, True, NAVY, PP_ALIGN.CENTER)
text(s, 0.6, 5.9, 12.1, 0.6, "Code: public GitHub repository  |  Data: huggingface.co/datasets/Krupa1420/la-metro-bikeshare-2024",
     13, False, GREY, PP_ALIGN.CENTER)

prs.save(OUT)
print("saved", OUT, "slides:", N[0])
