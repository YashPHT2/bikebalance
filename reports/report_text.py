# Report body. Executed by build_report.py (shares its namespace: doc, R, helpers, numbers).
# flake8: noqa
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

# ================================================================== TITLE PAGE
para("Project Report", bold=True, size=16, align="c", after=2)
para("Advanced Data Science", bold=True, size=20, align="c", after=2)
para("CSE3105", bold=True, size=16, align="c", after=14)
para(TITLE, bold=True, size=22, align="c", after=10)
para("By", bold=True, italic=True, size=14, align="c", after=14)
for name, eid in MEMBERS:
    para(name, bold=True, italic=True, size=12, align="c", after=0)
    para(eid, italic=True, size=12, align="c", after=4)
para("Group 12", italic=True, size=12, align="c", after=10)
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.add_run().add_picture(str(ROOT / "reports" / "assets" / "bml_logo.png"), width=Cm(4))
para("School of Engineering and Technology", bold=True, size=14, align="c", after=0)
para("BML Munjal University", bold=True, size=14, align="c", after=0)
para("November 2026", bold=True, size=14, align="c", after=0)

# ================================================================== DECLARATION
chapter("Declaration by the Candidates")
para(f'We hereby declare that the project entitled "**{TITLE}**" has been carried out to fulfil the '
     "partial requirements for completion of the course **Advanced Data Science** offered in the 5th "
     "Semester of the Bachelor of Technology (B.Tech) program in the Department of Computer Science and "
     "Engineering during AY-2026-27 (odd semester). This experimental work has been carried out by us and "
     "submitted to the course instructor. Due acknowledgments have been made in the text of the project to "
     "all other materials used. This project has been prepared in full compliance with the requirements and "
     "constraints of the prescribed curriculum.")
para("")
for name, eid in MEMBERS:
    para(f"{name} ({eid})            Signature: ____________________", align="l", after=10)
para("")
para("**Place:** BML Munjal University", align="l")
para("**Date:** ______ November, 2026", align="l")

# ================================================================== ACKNOWLEDGEMENT
chapter("ACKNOWLEDGEMENT")
para("We express our sincere gratitude to our course instructor for Advanced Data Science (CSE3105) for the "
     "guidance, structured milestones and critical feedback during the pre-submission viva, which sharpened "
     "our hypotheses and validation design. We thank the Department of Computer Science and Engineering and "
     "the School of Engineering and Technology, BML Munjal University, for providing the academic environment "
     "and computing resources for this work.")
para("We acknowledge Los Angeles Metro Bike Share for publishing its trip data openly, and the maintainers of "
     "the Hugging Face dataset used in this study. We are also grateful to the developers of the open-source "
     "Python ecosystem (pandas, scikit-learn, LightGBM, SHAP, MLflow, Streamlit) on which BikeBalance is built. "
     "Finally, we thank our classmates and families for their encouragement throughout the semester.")

# ================================================================== ABSTRACT
chapter("ABSTRACT")
abstract_par = doc.add_paragraph()  # filled after results (placeholder object)
ABSTRACT_SLOT = abstract_par

# ================================================================== TOC
chapter("TABLE OF CONTENTS")
p = doc.add_paragraph()
run = p.add_run()
for t, txt in (("begin", None), (None, 'TOC \\o "1-1" \\h \\z \\u'), ("separate", None), ("end", None)):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    if t:
        el = OxmlElement("w:fldChar"); el.set(qn("w:fldCharType"), t)
    else:
        el = OxmlElement("w:instrText"); el.set(qn("xml:space"), "preserve"); el.text = txt
    run._r.append(el)
para("(Right-click and choose 'Update Field' in MS Word if page numbers are not shown.)", italic=True, size=9)
LOF_SLOT = None

# ================================================================== LISTS (filled at end)
chapter("LIST OF FIGURES")
LOF_ANCHOR = doc.add_paragraph()
h = doc.add_heading("LIST OF TABLES", level=1); h.alignment = WD_ALIGN_PARAGRAPH.CENTER
for r in h.runs:
    r.font.name = "Times New Roman"; r.font.size = Pt(16); r.font.color.rgb = __import__("docx").shared.RGBColor(0, 0, 0)
LOT_ANCHOR = doc.add_paragraph()
h = doc.add_heading("LIST OF ABBREVIATIONS", level=1); h.alignment = WD_ALIGN_PARAGRAPH.CENTER
for r in h.runs:
    r.font.name = "Times New Roman"; r.font.size = Pt(16); r.font.color.rgb = __import__("docx").shared.RGBColor(0, 0, 0)
abbr = [("ADS", "Advanced Data Science"), ("BADIR", "Business question, Analysis plan, Data collection, Insights, Recommendations"),
        ("BSS", "Bike-Sharing System"), ("CI", "Confidence Interval"), ("DST", "Daylight Saving Time"),
        ("EDA", "Exploratory Data Analysis"), ("ETL", "Extract, Transform, Load"), ("GBM", "Gradient Boosting Machine"),
        ("HA", "Historical Average"), ("KPI", "Key Performance Indicator"), ("LGBM", "LightGBM (Light Gradient Boosting Machine)"),
        ("LR", "Linear Regression"), ("MAE", "Mean Absolute Error"), ("MLOps", "Machine Learning Operations"),
        ("PSI", "Population Stability Index"), ("RF", "Random Forest"), ("RMSE", "Root Mean Squared Error"),
        ("SHAP", "SHapley Additive exPlanations"), ("SSOT", "Single Source of Truth"),
        ("S / C / W / L", "Feature groups: Station, Calendar, Weather, Lags")]
table(pd.DataFrame(abbr, columns=["Abbreviation", "Full form"]), "Abbreviations used in this report", widths=[3.5, 12])
TABS.pop()  # do not number the abbreviation table

# ================================================================== CH1
chapter("CHAPTER 1: INTRODUCTION")
h2("1.1 Background and context")
para("Public bike-sharing systems (BSS) have become part of urban mobility in hundreds of cities. Users pick up "
     "a bicycle at one dock and return it at another, which makes the system flexible but also makes it "
     "unbalanced: commuting and leisure flows systematically drain some stations and fill others [1], [2]. "
     "When a station is empty a customer cannot start a trip; when it is full a customer cannot return a bike. "
     "Operators therefore run trucks or cargo bikes that move bicycles between stations, a costly activity that "
     "is only useful if bikes are moved to where they will actually be needed [3], [4].")
para("Los Angeles Metro Bike Share operates roughly 250 stations in Downtown Los Angeles (DTLA), the Westside "
     "(Santa Monica/Venice) and North Hollywood, and publishes anonymised trip records each quarter [6]. In 2024 "
     f"the system recorded **{A['raw_trips']:,} trips**, an average of {E['daily_mean']:.0f} per day.")
h2("1.2 Domain overview")
para("Bike-share operations sit at the intersection of demand forecasting (how many rentals will each station "
     "see in the next hour?) and inventory/repositioning optimisation (given the forecast and the current stock, "
     "which transfers should be made under a limited truck budget?). The forecasting problem is a sparse count "
     "time series problem with strong daily and weekly seasonality, weather sensitivity and large heterogeneity "
     "across stations [5], [7]. The repositioning problem is a constrained allocation/vehicle-routing problem [3], [4].")
h2("1.3 Motivation and significance")
para("Every empty dock at a busy hour is a lost trip and a dissatisfied customer, while every unnecessary "
     "transfer wastes fuel and crew time. Historical averages are the usual planning baseline in small "
     "operations; the question we study is whether data-driven, forecast-based planning measurably improves "
     "service under the same operational budget, and which information (calendar, weather, recent demand) "
     "actually matters.")
h2("1.4 Stakeholders and beneficiaries")
bullets(["**Primary stakeholder - bike-share operations manager:** decides which stations to replenish before "
         "the next hour and how to use the truck budget.",
         "**Riders:** benefit from higher bike availability at the time and place they need it.",
         "**Transit agency / city:** better service levels support mode shift and justify public subsidy.",
         "**Field crews:** receive a concrete, prioritised transfer list instead of ad-hoc decisions."])
h2("1.5 Objectives")
bullets(["Integrate trips, stations and weather into a single, versioned, audited station-hour table (SSOT).",
         "Characterise demand patterns through exploratory data analysis.",
         "Forecast next-hour departures per station and quantify the value of calendar, weather and lag features.",
         "Compare a historical-average baseline, Linear Regression, Random Forest and gradient boosting (LightGBM).",
         "Evaluate forecast-based transfers against historical-average transfers in a trip-level simulation.",
         "Deliver a working decision-support demo, with experiment tracking, explanations and a container image."])
h2("1.6 Scope")
para("The study covers all LA Metro Bike Share trips that started in calendar year 2024 together with hourly "
     "weather. The forecast horizon is one hour ahead at station level. Because the public data contain no "
     "historical dock inventories, capacities or costs, the redistribution component is evaluated through a "
     "simulation under explicitly stated and varied assumptions; we do not claim real monetary savings.")
h2("1.7 Expected outcomes")
bullets(["A reproducible pipeline (ETL -> EDA -> models -> simulation) in a public repository.",
         "Statistical verdicts on seven pre-registered hypotheses (H1-H7).",
         "An interactive Streamlit planner that turns forecasts into transfer recommendations."])

# ================================================================== CH2
chapter("CHAPTER 2: PROBLEM STATEMENT AND OBJECTIVES")
h2("2.1 Description of the problem")
para("Bike availability is uneven in space and time. During the morning peak DTLA office areas receive bikes "
     "while residential areas drain; in the evening the pattern reverses; at the beach the weekend dominates. "
     f"In the training period {E['stations_net_negative']} stations had more departures than arrivals, i.e. they "
     "were net sources that must be refilled by the operator. Without good next-hour forecasts the operator "
     "either reacts too late (empty stations) or moves bikes where they are not needed (wasted effort).")
h2("2.2 Business challenge")
para("The operations manager has a limited number of bikes that can be moved per hour. The challenge is to "
     "decide, at the start of each hour, which stations to replenish and from where, maximising the share of "
     "demand that can be served (coverage) for a given transfer effort.")
h2("2.3 Problem statement")
para("**Given** the 2024 LA Metro Bike Share trips, station registry and hourly weather, **build** a validated "
     "station-level next-hour departure forecaster using only information available at forecast time, and "
     "**evaluate** whether transfer decisions based on it reduce unmet demand compared with decisions based on "
     "historical averages under identical inventory, capacity and budget assumptions.", align="j")
h2("2.4 Research questions")
bullets(["RQ1: Which information groups (calendar, weather, recent demand) improve next-hour station forecasts?",
         "RQ2: Do tree ensembles outperform a linear model on the same features?",
         "RQ3: How concentrated is demand across stations, and is the ranking stable over time?",
         "RQ4: Do forecast-based transfers reduce unmet demand, and are the gains larger at peak hours?"])
h2("2.5 Hypotheses")
hyp_tbl = pd.DataFrame([
    ("H1", "Hour and weekday features improve forecasts beyond a station-only baseline.", "LGBM S vs LGBM SC, test MAE"),
    ("H2", "Forecast-time-available weather improves forecasts beyond calendar and past demand.", "LGBM SCL vs SCWL"),
    ("H3", "Forecast-based transfers reduce simulated unmet demand versus historical-average transfers.", "Simulation, unmet trips"),
    ("H4", "Past-departure lags improve forecasts beyond station, calendar and available weather.", "LGBM SCW vs SCWL"),
    ("H5", "Tree ensembles achieve lower forecast error than Linear Regression with the same features.", "LR vs RF / LGBM (SCWL)"),
    ("H6", "The busiest 20% of stations, ranked on training data, account for over 50% of later departures.", "Share Sep-Dec"),
    ("H7", "Forecast-based transfers yield greater coverage gains in peak hours than off-peak hours.", "Simulation, coverage"),
], columns=["ID", "Hypothesis", "Test"])
table(hyp_tbl, "Pre-registered hypotheses and how each is tested", widths=[1.2, 10, 4.5])
para("Each hypothesis is stated directionally (alternative hypothesis); the null is 'no improvement'. A "
     "hypothesis is marked **supported** only if the one-sided paired test is significant at alpha = 0.05 on "
     "the untouched test period **and** the 95% bootstrap confidence interval of the effect excludes zero.")
h2("2.6 BADIR framework and its application")
badir = pd.DataFrame([
    ("B - Business question", "Which stations should be replenished before the next hour, and does forecasting help?",
     "Decision, KPI definitions: unmet demand, coverage, bikes moved, bike-km"),
    ("A - Analysis plan", "H1-H7 with controlled, nested comparisons and a frozen temporal split",
     "Hypothesis table, feature-group design, test protocol"),
    ("D - Data collection", "Hugging Face mirror of official data; audited ETL into a station-hour SSOT",
     f"SSOT {SSOT_ROWS:,} rows x {A['ssot_columns']} columns, audit log"),
    ("I - Insights", "EDA + HA, LR, RF, LightGBM forecasting; SHAP; trip-level simulation",
     "Model comparison, hypothesis verdicts, explanations"),
    ("R - Recommendations", "Constrained transfer plan for the next hour; deployment via Streamlit/Docker",
     "Planner demo, policy recommendations, monitoring plan"),
], columns=["Stage", "What we did", "Output"])
table(badir, "Application of the BADIR framework", widths=[3.6, 7, 5.4])
h2("2.7 Expected outcomes and impact")
para("A validated forecaster and an evidence-based answer to whether forecast-driven repositioning pays off. "
     "For the operator the deliverable is a ranked transfer list each hour; for the analytics team it is a "
     "reproducible pipeline with tracked experiments and drift monitoring.")

# ================================================================== CH3
chapter("CHAPTER 3: DATASET DESCRIPTION")
h2("3.1 Overview")
para("The study uses the 2024 release of LA Metro Bike Share open data as packaged on Hugging Face [8], which "
     "mirrors the official trip files published by Metro [6] and adds a station registry and an hourly weather "
     "table. Three tables were integrated: trips (one row per rental), stations (one row per dock station) and "
     "weather (one row per hour).")
h2("3.2 Data sources and acquisition")
bullets([f"**Trips, stations, weather:** huggingface.co/datasets/Krupa1420/la-metro-bikeshare-2024 [8], "
         "downloaded programmatically with huggingface_hub (etl.download_raw) so that the pipeline is fully reproducible.",
         "**Original trip source:** bikeshare.metro.net/about/data [6].",
         "**Calendar:** US federal holidays 2024 plus Christmas Eve and New Year's Eve, coded in the ETL."])
h2("3.3 Size, variables and time period")
size_tbl = pd.DataFrame([
    ("trips", f"{A['raw_trips']:,}", A["raw_trip_columns"], "2024-01-01 00:10 to 2024-12-31 23:47"),
    ("stations", A["raw_stations"][0], A["raw_stations"][1], "static registry"),
    ("weather", f"{A['raw_weather'][0]:,}", A["raw_weather"][1], "hourly, 2024-01-01 00:00 to 2024-12-31 23:00"),
    ("SSOT (integrated)", f"{A['ssot_rows']:,}", A["ssot_columns"], f"{A['ssot_stations']} stations x active hours"),
], columns=["Table", "Rows", "Columns", "Coverage"])
table(size_tbl, "Raw and integrated dataset sizes", widths=[3.5, 3, 2, 7.5])
para("The final integrated dataset contains close to two million station-hour observations and 25 variables, "
     "comfortably above the course minimum for size and integration of multiple sources.")
h2("3.4 Data dictionary")
dd = pd.DataFrame([
    ("trips", "trip_id", "int", "Unique rental identifier (no duplicates found)"),
    ("trips", "start_time / end_time", "datetime", "Local time (America/Los_Angeles), minute resolution"),
    ("trips", "duration_minutes", "int", "Trip duration; median 15 min, capped at 1,440"),
    ("trips", "start_station / end_station", "int", "Station IDs; join keys to the registry"),
    ("trips", "start/end lat, lon", "float", "Coordinates; 59 start and 11,074 end values missing"),
    ("trips", "bike_id, bike_type", "int / cat", "Bike identifier; Electric or Standard"),
    ("trips", "passholder_type", "cat", "Monthly, Annual, One Day Pass or Walk-Up"),
    ("trips", "trip_route_category", "cat", "One Way or Round Trip"),
    ("stations", "station_id, station_name", "int / str", "Registry key and name"),
    ("stations", "region", "cat", "DTLA, Westside, North Hollywood (1 missing)"),
    ("stations", "lat, lon", "float", "Station coordinates"),
    ("weather", "timestamp", "datetime", "Hourly, local time (DST artefacts present)"),
    ("weather", "temp_c, rel_humidity", "float", "Air temperature (C), relative humidity (%)"),
    ("weather", "precip_mm", "float", "Hourly precipitation (mm)"),
    ("weather", "wind_speed_mps", "float", "Documented as m/s (see 3.5)"),
    ("weather", "pressure_hpa, weather_code", "float", "Sea-level pressure; condition code 1-9"),
    ("SSOT", "departures (target)", "int", "Trips starting at the station in the hour"),
    ("SSOT", "arrivals, dep_electric", "int", "Trips ending at the station; e-bike departures"),
    ("SSOT", "hour_of_day, dow, is_weekend, is_holiday", "int", "Calendar keys of the target hour"),
    ("SSOT", "recovered, region_missing, coords_missing, weather_imputed", "flag", "Data-quality flags kept for audit"),
    ("SSOT", "split", "cat", "train (Jan-Aug), val (Sep-Oct), test (Nov-Dec)"),
], columns=["Table", "Variable", "Type", "Description"])
table(dd, "Data dictionary (raw and integrated variables)", widths=[2, 5.5, 2, 6.5], size=8.5)
h2("3.5 Data quality and authenticity")
para("A scripted audit (reports/tables/data_audit.json) found the following issues, each resolved or flagged:")
bullets([f"**Unmatched station IDs:** {A['unmatched_origin_trips_vs_raw_registry']:,} trips start, and "
         f"{A['unmatched_destination_trips_vs_raw_registry']:,} end, at IDs absent from the 226-row registry. Rather than "
         f"dropping them we **recovered {A['stations_recovered_from_trips']} station IDs** using the median trip "
         "coordinates and assigned the region of the nearest registered station; they are flagged recovered = 1. "
         "ID 3000 (a virtual/no-location station) has no coordinates and is flagged coords_missing.",
         "**Weather time stamps:** one duplicated hour (2024-11-03 01:00) and one missing hour (2024-03-10 02:00). "
         "These are exactly the US daylight-saving transitions, which **confirms that weather is in local time**, "
         "consistent with trip times. The duplicate was averaged; the gap was linearly interpolated (flagged).",
         "**Missing coordinates:** 59 start and 11,074 end coordinates are missing in trips; station coordinates "
         "come from the registry, so the SSOT is unaffected.",
         "**Region:** one registered station lacked a region and was assigned the nearest region (flagged).",
         "**Units:** wind speed has mean 11.8 and maximum 53.6 'm/s', implausible for Los Angeles and more "
         "consistent with km/h. Because tree models are scale-invariant and LR is standardised, the conclusion "
         "is unaffected; we report the field as documented and flag the provenance question.",
         "**Censoring:** completed trips measure served demand only; demand lost at empty stations is not observed."])
para("Authenticity: the trip records are official open data published by LA Metro; row counts reproduced "
     "exactly the figures reported in our pre-submission summary (519,235 trips x 14; 226 x 5; 8,784 x 7).")
h2("3.6 Data integration process")
bullets(["Standardise station IDs to integers; build the augmented registry (226 + recovered = "
         f"{A['stations_registry_final']} IDs).",
         "Floor trip start and end times to the hour; **check that row counts are preserved before aggregation** "
         "(sum of hourly departures = 519,235, asserted in code).",
         "Aggregate departures and arrivals per station-hour.",
         "Create the station-hour grid only inside each station's **active window** (first to last observed "
         "activity) and fill zeros there, so that stations opened or removed mid-year are not padded with false zeros.",
         "Join weather on hour and station attributes on station_id with pandas validate='many_to_one'; assert "
         "the row count is unchanged after each join.",
         "Add calendar fields and the temporal split label; write a versioned Parquet file "
         "ssot_station_hour_v1.0.parquet plus the audit JSON."])
h2("3.7 Final integrated dataset")
para(f"The SSOT has **{A['ssot_rows']:,} rows x {A['ssot_columns']} columns** for {A['ssot_stations']} stations. "
     f"The target is highly sparse: {pct(A['ssot_zero_share'])} of station-hours have zero departures, the mean is "
     f"{E['target_mean']:.3f} and the variance {E['target_var']:.3f} (over-dispersed relative to Poisson). Rows by split: "
     f"train {A['rows_by_split']['train']:,}, validation {A['rows_by_split']['val']:,}, test {A['rows_by_split']['test']:,}.")

# ================================================================== CH4
chapter("CHAPTER 4: LITERATURE REVIEW")
h2("4.1 Bike-sharing systems and demand drivers")
para("Fishman, Washington and Haworth [1] review the bike-share literature and identify convenience, proximity "
     "of docks and availability of bikes as primary determinants of use, with weather and topography as "
     "secondary factors. Faghih-Imani et al. [7] model hourly arrivals and departures at Montreal's BIXI stations "
     "and show strong effects of time of day, weather (temperature, rain), land use and station capacity. Our EDA "
     "reproduces these patterns for Los Angeles.")
h2("4.2 Station-level demand forecasting")
para("Early work used aggregate counts, e.g. the UCI Capital Bikeshare data of Fanaee-T and Gama [5], which "
     "established weather and calendar as key covariates for system-level hourly demand. Station-level "
     "prediction is harder because counts are small and sparse. Li et al. [9] cluster stations and predict "
     "check-outs with gradient boosted regression trees, outperforming historical averages and ARMA; Chen et al. "
     "[10] predict over-demand for dynamic clusters. Gradient boosting [11], in particular LightGBM [12], and "
     "Random Forests [13] are now standard strong baselines for tabular forecasting, while linear regression "
     "provides an interpretable but less flexible reference.")
h2("4.3 Rebalancing and repositioning")
para("Raviv, Tzur and Forma [3] formulate static (overnight) repositioning as a mixed-integer program that "
     "minimises user dissatisfaction plus operating cost. Schuijbroek, Hampshire and van Hoeve [4] combine "
     "service-level requirements derived from queueing models with vehicle routing. O'Mahony and Shmoys [2] "
     "describe the data-driven rebalancing used in production at New York's Citi Bike, where forecasts of "
     "flows drive mid-rush-hour truck routes. These works show that the value of rebalancing depends on the "
     "quality of the demand estimate used to set target inventories.")
h2("4.4 Evaluation practice")
para("Time-series model comparisons should use temporally ordered splits and paired tests that respect "
     "autocorrelation; the Diebold-Mariano framework [14] formalises comparing forecast accuracy on the same "
     "targets. Post-hoc explanation methods such as SHAP [15] make tree ensembles auditable for operators, and "
     "MLOps tools such as MLflow [16] support reproducibility.")
h2("4.5 Comparison and research gaps")
lit = pd.DataFrame([
    ("[5] Fanaee-T & Gama 2014", "Capital Bikeshare (UCI)", "System-level hourly; weather+calendar", "No station level, no decisions"),
    ("[7] Faghih-Imani et al. 2014", "BIXI Montreal", "Mixed models of station flows", "Explanatory, not forecasting"),
    ("[9] Li et al. 2015", "Citi Bike / Capital", "Cluster-level GBRT", "Accuracy only, no decision value"),
    ("[3] Raviv et al. 2013", "Synthetic/Paris", "MIP static repositioning", "Assumes demand is known"),
    ("[4] Schuijbroek et al. 2017", "Boston, Washington", "Service levels + routing", "Demand model simple"),
    ("[2] O'Mahony & Shmoys 2015", "Citi Bike NYC", "Data-driven rebalancing", "Not open, not LA"),
    ("This project", "LA Metro 2024", "Station-hour GBM + trip-level simulation", "Links forecast accuracy to service"),
], columns=["Study", "Data", "Approach", "Gap / limitation"])
table(lit, "Summary of related studies", widths=[3.8, 3.2, 4.5, 4.5], size=8.5)
para("Gaps addressed: (i) few studies use the LA Metro system, which has a distinctive multi-cluster "
     "geography (DTLA, Westside, North Hollywood); (ii) many forecasting papers report accuracy without "
     "quantifying operational value; (iii) feature-group contributions are rarely tested with controlled, "
     "nested comparisons and pre-registered hypotheses.")
h2("4.6 Contribution of this project")
bullets(["An audited, versioned station-hour SSOT for LA Metro 2024 that recovers rather than drops unmatched stations.",
         "Controlled, nested tests of calendar, weather and lag information with temporally blocked statistics.",
         "A trip-level simulation that conserves the fleet and compares policies under identical assumptions.",
         "An operator-facing planner with explanations, tracking and containerised deployment."])

# ================================================================== CH5
chapter("CHAPTER 5: METHODOLOGY")
h2("5.1 Overall workflow")
para("The pipeline is implemented as a Python package (src/bikebalance) and executed end to end by "
     "run_pipeline.py. Figure 1 summarises the flow.")
figure("fig00_workflow", "BikeBalance pipeline and its mapping to the BADIR framework")
h2("5.2 Data collection and integration")
para("Raw files are downloaded from Hugging Face by etl.download_raw and integrated by etl.build_ssot as "
     "described in Section 3.6. Integrity checks are executed as assertions, so the pipeline fails loudly if "
     "a join duplicates rows or if any trip is lost during aggregation. The SSOT and the augmented station "
     "registry are written with a version suffix (v1.0) to keep downstream results traceable.")
h2("5.3 Pre-processing and cleaning")
bullets(["DST artefacts in weather: duplicate hour averaged, missing hour interpolated (weather_imputed flag).",
         "Unmatched stations recovered from trip coordinates (recovered flag); no trips dropped.",
         "Zero-filling restricted to each station's active window to avoid inflating zeros.",
         "Imputation values for linear and random-forest models (median, station mean for lag features at "
         "window starts) are **fitted on training data only**; LightGBM handles missing lags natively."])
h2("5.4 Exploratory data analysis")
para("EDA (src/bikebalance/eda.py) examines temporal patterns, weather effects, station concentration, "
     "target distribution, autocorrelation, user mix and net flows. Non-parametric tests (Kruskal-Wallis for "
     "hour-of-day differences, Mann-Whitney U for rain vs dry hours, Spearman correlation for temperature) are "
     "used because hourly counts are skewed. Results are reported in Chapter 7.")
h2("5.5 Feature engineering")
para("The forecast is issued at time t, the start of target hour h, and predicts departures during h. Only "
     "information known at t is used. Features are organised in four groups so that each hypothesis is a "
     "controlled comparison that adds exactly one group:")
feat = pd.DataFrame([
    ("S - Station", "station_mean (training-period mean departures), lat, lon, region_code, recovered flag", "5"),
    ("C - Calendar", "hour_of_day, sin/cos(hour), day of week, is_weekend, is_holiday (of target hour)", "6"),
    ("W - Weather", "temperature, humidity, precipitation, wind, pressure, weather code observed at h-1; "
                    "rain flag; 3-hour precipitation sum", "8"),
    ("L - Lags", "departures at h-1, h-2, h-3, h-24, h-168; rolling 24 h and 168 h means; arrivals at h-1", "8"),
], columns=["Group", "Features", "#"])
table(feat, "Feature groups (all available at forecast time)", widths=[3, 11.5, 1.2])
para("Feature sets: S, SC, SCW, SCL and SCWL (all 27 features). Month is deliberately excluded because the "
     "test months never appear in training. Weather is lagged by one hour to represent the latest observation "
     "available to a dispatcher; using same-hour observed weather would leak information.")
h2("5.6 Models")
bullets(["**Historical average (HA):** (a) station mean; (b) station x hour-of-day x weekend mean. HA(b) is the "
         "operational baseline used by the HA transfer policy.",
         "**Linear Regression (LR):** ordinary least squares on standardised SCWL features.",
         "**Random Forest (RF):** 100 trees, max_features = 0.5, depth and leaf size tuned on validation; trained "
         "on a random 400,000-row sample of the training data for tractability.",
         "**LightGBM (gradient boosting):** Poisson or L2 objective, number of leaves and minimum child samples "
         "tuned on validation, early stopping on validation MAE; then refitted on train+validation with the "
         "selected number of iterations (x1.1) and scored once on the test period."])
para("The Poisson objective models log E[y|x] = f(x), which suits non-negative, over-dispersed counts. All "
     "predictions are clipped at zero.")
h2("5.7 Validation and evaluation design")
para("Temporal split for all stations: **train January-August, validation September-October, test "
     "November-December**. Validation is used for model selection; the test period is touched once. Metrics:")
para("MAE = (1/n) sum |y_i - y_hat_i|,     RMSE = sqrt((1/n) sum (y_i - y_hat_i)^2)", align="c", italic=True)
para("For each hypothesis the absolute errors of the two competing models are averaged per day, giving 61 "
     "paired daily values on the test period. This blocking absorbs within-day autocorrelation and is the "
     "daily analogue of the Diebold-Mariano comparison [14]. We report the one-sided Wilcoxon signed-rank test "
     "and a day-block bootstrap (2,000 resamples) 95% CI of the MAE reduction. The same tests are repeated on "
     "the validation period as a robustness check.")
h2("5.8 H6: station concentration")
para("Stations are ranked by total training departures; the top 20% (rounded up) are frozen. We compute their "
     "share of departures in the later periods (Sep-Dec), a daily-block bootstrap CI, and a one-sided Wilcoxon "
     "test that the daily share exceeds 50%.")
h2("5.9 Redistribution simulation (H3, H7)")
para("Because no inventory data exist, policies are compared in a trip-level simulation over the test period "
     "(1,464 hours, all stations), using the same realised trips for every policy:")
bullets(["Initial stock = 50% of capacity at every station; uniform capacity of 15 or 25 docks (scenarios).",
         "At the start of each hour the operator may move at most B bikes (B = 10, 25, 50). Target stock is "
         "min(cap, ceil(f + sqrt(f))) where f is the policy's demand estimate for the hour, i.e. the expected "
         "demand plus roughly one Poisson standard deviation. Receivers with the largest deficit are served "
         "first from the nearest donor with surplus (haversine distance); bike-km is recorded.",
         "Trips are served in start-time order while bikes remain; an unserved trip is **unmet demand**. A served "
         "trip returns its bike at its end station and hour; if the dock is full the bike is placed at the nearest "
         "station with space (blocked return). The fleet is therefore conserved.",
         "Policies: no transfers, **HA** (station x hour x weekend average), **forecast** (LightGBM SCWL) and an "
         "**oracle** with perfect foresight (upper bound).",
         f"Peak hours are frozen on training data as hours of day whose mean system departures are at or above the "
         f"75th percentile: {', '.join(str(h) for h in R['peak']['peak_hours'])}."])
para("KPIs: unmet demand, coverage = served / demand (overall, peak, off-peak), bikes moved, bike-km and blocked "
     "returns. H3 is tested with a one-sided Wilcoxon test on daily unmet demand (HA minus forecast); H7 with a "
     "one-sided Wilcoxon test on the daily difference between the peak and off-peak coverage gains.")
h2("5.10 Explainability, tracking and monitoring")
para("SHAP TreeExplainer values [15] are computed for 20,000 test rows of the final LightGBM model. All tuning "
     "and final runs, simulation scenarios and the model artefact are logged to MLflow [16]. Distribution drift "
     "between training and test is monitored with the Population Stability Index (PSI) on key features "
     "(PSI < 0.1 stable, 0.1-0.25 moderate, > 0.25 major).")
h2("5.11 Assumptions and limitations of the method")
bullets(["Observed trips are censored demand; true demand at empty stations is higher than recorded.",
         "Capacities, initial stocks, budgets and instantaneous transfers are assumptions, varied across six scenarios.",
         "Arrivals in the simulation follow realised destinations; demand is not re-routed to neighbouring stations.",
         "Random Forest is trained on a sample, which slightly favours the boosted model in run time but not in data."])

# ================================================================== CH6
chapter("CHAPTER 6: TECHNOLOGY STACK")
tech = pd.DataFrame([
    ("Programming language", "Python 3.10"),
    ("Development environment", "VS Code / Jupyter, Git and GitHub, Windows 11 and Linux container"),
    ("Data processing", "pandas 2.2, NumPy 2.2, PyArrow (Parquet)"),
    ("Statistics", "SciPy (Wilcoxon, Mann-Whitney U, Kruskal-Wallis, Spearman), bootstrap in NumPy"),
    ("Machine learning", "scikit-learn 1.6 (Linear Regression, Random Forest, pipelines), LightGBM 4.7"),
    ("Explainability", "SHAP (TreeExplainer)"),
    ("Experiment tracking", "MLflow (SQLite backend store)"),
    ("Visualisation", "Matplotlib, Seaborn, Plotly"),
    ("User interface", "Streamlit web app with Plotly maps (carto-positron tiles)"),
    ("Data storage", "CSV (raw), versioned Parquet SSOT, JSON audit and result tables"),
    ("Deployment", "Docker image (python:3.10-slim) serving Streamlit on port 8501"),
    ("Testing", "pytest data-contract tests (trip conservation, unique keys, split order, no lag leakage)"),
    ("Hardware", "Laptop, 16 logical cores, 16 GB RAM; full pipeline runs in about 20-30 minutes"),
], columns=["Component", "Technology"])
table(tech, "Technology stack", widths=[4.5, 11.5])
para("Repository layout: src/bikebalance (config, etl, features, forecasting, stats, simulation, evaluate, "
     "track), app/streamlit_app.py, tests/, reports/ (figures, tables, report builder), Dockerfile, "
     "requirements.txt and run_pipeline.py.")

# ================================================================== CH7
chapter("CHAPTER 7: EXPERIMENTAL RESULTS AND DISCUSSION")
h2("7.1 Exploratory data analysis")
figure("fig01_daily_departures", "Daily departures in 2024 with the temporal train/validation/test split shaded")
para(f"Daily volume averages {E['daily_mean']:.0f} trips, ranging from {E['daily_min'][1]} ({E['daily_min'][0]}, a rainy "
     f"winter day) to {E['daily_max'][1]:,} ({E['daily_max'][0]}). Volume rises from winter to a May and September-October "
     "peak and falls in December, so the test period (Nov-Dec) is a lower-demand regime than training. This "
     "seasonal shift is why test MAE values are lower than validation MAE for every model: errors scale with volume.")
figure("fig02_hour_weekday_heatmap", "Mean system departures by hour of day and day of week")
figure("fig03_hourly_profile", "Hourly departure profile, weekdays vs weekends", width=12)
para("Weekdays show a commuter double peak (08:00 and 17:00-18:00) while weekends show a single broad midday "
     f"peak. Hour-of-day differences are highly significant (Kruskal-Wallis H = {E['kruskal_hour_of_day']['H']:.0f}, "
     "p < 0.001), which motivates H1.")
figure("fig05_weather_effect", "Daytime departures by temperature band and in rain vs dry hours")
para(f"During daytime hours, departures in rain average {E['dep_dry_vs_rain'][1]:.1f} per hour vs "
     f"{E['dep_dry_vs_rain'][0]:.1f} in dry hours (Mann-Whitney U, p < 0.001) and correlate positively with "
     f"temperature (Spearman rho = {E['spearman_temp_dep_daytime']:.2f}). However only {E['rain_hours_daytime']} daytime "
     "hours in the whole year had rain, so weather information is rare and seasonal, an important context for H2.")
figure("fig04_station_lorenz", "Lorenz curve of station departures (training period)", width=10)
figure("fig06_target_distribution", "Distribution of the target (departures per station-hour)", width=12)
figure("fig07_acf", "Autocorrelation of hourly departures at the busiest station")
para(f"The busiest station (ID {E['acf_busiest']['station']}) shows autocorrelation of "
     f"{E['acf_busiest']['lag1']:.2f} at lag 1, {E['acf_busiest']['lag24']:.2f} at lag 24 and {E['acf_busiest']['lag168']:.2f} "
     "at lag 168 hours, i.e. strong recent, daily and weekly memory, motivating lag features (H4).")
figure("fig08_mix", "Departures by region, pass type and bike type")
figure("fig09_net_flow", "Stations with the largest net outflow (red) and inflow (green), Jan-Aug", width=13)
figure("fig10_station_map", "Station locations sized by 2024 departures; recovered station IDs circled", width=12)
para(f"DTLA accounts for {E['regions']['DTLA']/sum(E['regions'].values()):.0%} of departures and the Westside for "
     f"{E['regions']['Westside']/sum(E['regions'].values()):.0%}. Monthly pass holders make "
     f"{E['passholder']['Monthly Pass']/sum(E['passholder'].values()):.0%} of trips, and electric bikes slightly outnumber "
     "standard bikes. Persistent net outflows at specific stations confirm the operational need for rebalancing.")

h2("7.2 Hyperparameter tuning")
tun = R["tuning"][R["tuning"]["model"].isna()].copy()
tun = tun[["features", "objective", "num_leaves", "min_child_samples", "best_iter", "MAE", "RMSE"]]
tun["num_leaves"] = tun["num_leaves"].astype(int); tun["min_child_samples"] = tun["min_child_samples"].astype(int)
tun["best_iter"] = tun["best_iter"].astype(int)
table(tun.round(4), "LightGBM tuning on the validation period (Sep-Oct); early stopping on MAE",
      widths=[1.6, 2.3, 2, 2.6, 2, 2, 2], size=8.5)
para("The Poisson objective with larger trees (127 leaves, 200 minimum child samples) was selected for every "
     "feature set except S, where the station-only model has almost nothing to learn. For Random Forest, depth "
     f"14 with minimum leaf size 20 was selected (validation MAE {R['tuning'][R['tuning']['model']=='RF']['MAE'].min():.4f}).")

h2("7.3 Model performance")
mm = M.pivot_table(index=["model", "features"], columns="split", values=["MAE", "RMSE", "R2"]).reset_index()
mm.columns = [" ".join(c).strip() for c in mm.columns]
mm = mm[["model", "features", "MAE val", "MAE test", "RMSE val", "RMSE test", "R2 test"]].sort_values("MAE test")
table(mm.round(4), "Forecast accuracy on validation and test (lower MAE/RMSE is better)",
      widths=[2.2, 1.8, 2.2, 2.2, 2.2, 2.2, 2], size=9)
figure("fig11_model_mae", "MAE by model and feature set on validation and test")
para(f"The best test MAE is achieved by **LightGBM with station, calendar and lag features (SCL): "
     f"{mae('LGBM','SCL'):.4f}**, followed by LightGBM SCWL ({mae('LGBM','SCWL'):.4f}), Random Forest "
     f"({mae('RF','SCWL'):.4f}) and Linear Regression ({mae('LR','SCWL'):.4f}). Relative to the operational baseline HA "
     f"(station x hour x weekend, {mae('HA_shw','-'):.4f}) the best model reduces MAE by "
     f"{100*(1-mae('LGBM','SCL')/mae('HA_shw','-')):.1f}% and RMSE by {100*(1-rmse('LGBM','SCL')/rmse('HA_shw','-')):.1f}%. "
     "Note that the HA baseline is itself strong: it encodes the same station-by-hour pattern that the SC model "
     "must learn, and the two are almost tied, so the real gains come from recent-demand information.")
figure("fig12_forecast_example", "Actual vs forecast departures at the busiest station, 11-17 November 2024")
figure("fig13_system_forecast", "System-level sum of station forecasts vs actual, 11-24 November 2024")
figure("fig15_mae_by_hour", "Test MAE by hour of day: LightGBM vs historical average", width=12)
para("Errors are largest in the afternoon and evening peaks, where volume is highest; the gap to the historical "
     "average is also largest there, which is where better forecasts matter operationally.")

h2("7.4 Hypothesis assessment: forecasting (H1, H2, H4, H5)")
hrows = []
for h in ["H1", "H2", "H4", "H5a", "H5b"]:
    r, v = HT.loc[h], HV.loc[h]
    hrows.append((h, r["description"], f"{r['mae_base']:.4f}", f"{r['mae_new']:.4f}",
                  f"{r['mae_reduction_pct']:+.1f}%", f"[{r['ci95_low']:.4f}, {r['ci95_high']:.4f}]",
                  f"{int(r['days_improved'])}/{int(r['days'])}", pfmt(r["wilcoxon_p"]),
                  f"{v['mae_reduction_pct']:+.1f}%", "Supported" if supported(h) else "Not supported"))
table(pd.DataFrame(hrows, columns=["H", "Comparison", "MAE base", "MAE new", "Change", "95% CI (MAE diff)",
                                   "Days better", "p (Wilcoxon)", "Val change", "Verdict"]),
      "Forecasting hypothesis tests on the test period (61 days); validation change shown for robustness",
      widths=[1, 3.6, 1.4, 1.4, 1.3, 2.4, 1.3, 1.4, 1.3, 1.8], size=7.5)
para(f"**H1 - supported.** Adding hour and weekday features to the station-only model reduces test MAE by "
     f"{HT.loc['H1','mae_reduction_pct']:.1f}% and improves the error on {int(HT.loc['H1','days_improved'])} of 61 days.")
para(f"**H2 - not supported.** Adding one-hour-lagged weather to calendar and lag features slightly *increases* "
     f"MAE ({HT.loc['H2','mae_reduction_pct']:+.1f}% on test, {HV.loc['H2','mae_reduction_pct']:+.1f}% on validation); the "
     "CI lies entirely below zero. Explanations: (i) recent lags already absorb the weather signal - if it rains, "
     "departures in the previous hour already dropped; (ii) rain is very rare in LA (115 daytime rain hours, "
     "almost none in the test period); (iii) temperature has a seasonal level shift between training and test "
     f"(PSI = {R['drift'].set_index('feature').loc['w_temp_c','PSI']:.2f}, moderate drift), which tree models cannot "
     "extrapolate. The EDA shows weather matters for demand, but it adds no incremental forecast value at a "
     "one-hour horizon once recent demand is known.")
para(f"**H4 - supported.** Past-departure lags reduce test MAE by {HT.loc['H4','mae_reduction_pct']:.1f}% over station, "
     "calendar and weather, improving every one of the 61 test days. This is the single most valuable information group.")
para(f"**H5 - supported.** With identical SCWL features, LightGBM beats Linear Regression by "
     f"{HT.loc['H5b','mae_reduction_pct']:.1f}% (p {pfmt(HT.loc['H5b','wilcoxon_p'])}) and Random Forest beats it by "
     f"{HT.loc['H5a','mae_reduction_pct']:.1f}% (p = {HT.loc['H5a','wilcoxon_p']:.3f}). The margin is modest on test "
     "but larger on validation (about 3.5-5%), indicating that the tree ensembles capture non-linear interactions "
     "(hour x station, lag x hour) that the linear model cannot.")

h2("7.5 Hypothesis assessment: concentration (H6)")
table(pd.DataFrame([
    ("Stations ranked on training data", H6["stations_ranked_on_train"]),
    ("Top 20% (k)", H6["top20_k"]),
    ("Share of departures, training (Jan-Aug)", pct(H6["top20_share_train"])),
    ("Share of departures, later (Sep-Dec)", pct(H6["top20_share_later_SepDec"])),
    ("Share of departures, test (Nov-Dec)", pct(H6["top20_share_test_NovDec"])),
    ("95% day-block bootstrap CI (Sep-Dec)", f"[{pct(H6['ci95'][0])}, {pct(H6['ci95'][1])}]"),
    ("Days with share > 50%", f"{H6['days_share_above_50pct']} / {H6['days']}"),
    ("Wilcoxon p (daily share > 50%)", pfmt(H6["wilcoxon_p_share_gt_50"])),
], columns=["Quantity", "Value"]), "H6 station-concentration test", widths=[9, 6])
para(f"**H6 - {'supported' if h6_ok else 'not supported'}.** The 49 stations ranked busiest on training data carry "
     f"{pct(H6['top20_share_later_SepDec'])} of later departures; the whole CI lies above 50% and the share exceeded "
     f"50% on {H6['days_share_above_50pct']} of {H6['days']} days. The ranking is stable over time, so a fixed "
     "priority list is a reasonable operational starting point, and service-level checks should focus on these stations.")

h2("7.6 Hypothesis assessment: redistribution simulation (H3, H7)")
sref2 = sref.reindex(["none", "HA", "forecast", "oracle"])
stbl = pd.DataFrame({
    "Policy": sref2.index, "Unmet trips": sref2["unmet"].astype(int), "Coverage": sref2["coverage"].map(pct),
    "Coverage peak": sref2["coverage_peak"].map(pct), "Coverage off-peak": sref2["coverage_offpeak"].map(pct),
    "Bikes moved": sref2["bikes_moved"].astype(int), "Bike-km": sref2["bike_km"].round(0).astype(int),
    "Blocked returns": sref2["blocked_returns"].astype(int)})
table(stbl, f"Simulation KPIs, reference scenario ({ref_sc}: 15 docks, 25 bikes/hour), Nov-Dec 2024",
      widths=[1.8, 1.8, 1.8, 2, 2.2, 1.8, 1.6, 2], size=8.5)
h3t = R["hyps"][["scenario", "unmet_none", "unmet_HA", "unmet_forecast", "unmet_oracle", "H3_unmet_reduction_pct",
                 "H3_days_better", "H3_days_worse", "H3_wilcoxon_p"]].copy()
h3t["H3_wilcoxon_p"] = h3t["H3_wilcoxon_p"].map(pfmt)
h3t["H3_unmet_reduction_pct"] = h3t["H3_unmet_reduction_pct"].map(lambda x: f"{x:.1f}%")
h3t.columns = ["Scenario", "Unmet none", "Unmet HA", "Unmet forecast", "Unmet oracle", "Reduction vs HA",
               "Days better", "Days worse", "p"]
table(h3t, "H3: unmet demand by scenario (forecast vs historical-average transfers)",
      widths=[2.2, 1.6, 1.6, 1.8, 1.7, 1.9, 1.5, 1.5, 1.4], size=8)
figure("fig16_simulation", "Left: simulated unmet demand by policy and scenario. Right: coverage gain of the "
                            "forecast policy over the HA policy in peak and off-peak hours")
para(f"**H3 - partially supported.** Forecast-based transfers produce less unmet demand than historical-average "
     f"transfers in **all {n_sc} scenarios** (1.7%-9.4% fewer lost trips) while moving **fewer bikes** "
     f"(e.g. {int(sref.loc['forecast','bikes_moved']):,} vs {int(sref.loc['HA','bikes_moved']):,} in the reference scenario). "
     f"The improvement is statistically significant in {n_h3} of {n_sc} scenarios - those where the truck budget or the "
     "dock capacity is tight (cap15_B10, cap15_B25, cap25_B10). When capacity and budget are generous, both "
     "policies already reach about 97.6% coverage and the remaining gap is not significant. Thus forecast value "
     "is greatest exactly when resources are scarce.")
para(f"Both policies are far better than no rebalancing (e.g. {pct(sref.loc['none','coverage'])} -> "
     f"{pct(sref.loc['forecast','coverage'])} coverage), and the oracle shows the remaining headroom from better "
     "forecasts. With the smallest budget (10 bikes/hour) the oracle is worse than both policies: perfect "
     "foresight of a single hour makes the greedy planner chase spiky one-hour demand and leaves no buffer for "
     "the following hours. This highlights that a multi-hour look-ahead is a natural next step.")
h7t = R["hyps"][["scenario", "H7_gain_peak_pp", "H7_gain_offpeak_pp", "H7_gain_vs_none_peak_pp",
                 "H7_gain_vs_none_offpeak_pp", "H7_days_peak_gain_larger", "H7_wilcoxon_p"]].copy()
h7t["H7_wilcoxon_p"] = h7t["H7_wilcoxon_p"].map(pfmt)
h7t.columns = ["Scenario", "Gain vs HA peak (pp)", "Gain vs HA off-peak (pp)", "Gain vs none peak (pp)",
               "Gain vs none off-peak (pp)", "Days peak > off-peak", "p"]
table(h7t.round(3), "H7: coverage gains in peak vs off-peak hours", widths=[2.2, 2.2, 2.3, 2.2, 2.3, 2.2, 1.6], size=8)
para(f"**H7 - not supported** (significant in {n_h7} of {n_sc} scenarios). Relative to the HA policy, the forecast "
     "policy's coverage gain is larger at peak hours only when the budget is tightest; with larger budgets the "
     "gain is slightly larger off-peak. Interpretation: the HA policy already anticipates the regular commuter "
     "peaks well (they are exactly what an hour-of-day average encodes), so the forecast adds most value in "
     "irregular off-peak situations captured by recent lags. Relative to doing nothing, however, rebalancing "
     "of any kind raises peak coverage more than off-peak coverage (e.g. +14.7 vs +11.8 pp in the reference scenario).")

h2("7.7 Model explainability (SHAP)")
figure("fig14_shap_summary", "SHAP summary of the LightGBM SCWL model on 20,000 test station-hours", width=13)
sh = R["shap"]
para(f"Hour of day dominates (mean |SHAP| = {sh['hour_of_day']:.2f}), followed by the 168-hour rolling mean "
     f"({sh['roll_168']:.2f}), the station's long-run mean ({sh['station_mean']:.2f}) and arrivals in the previous hour "
     f"({sh['arr_lag_1']:.2f}). Weather features rank low (temperature {sh['w_temp_c']:.3f}), consistent with H2. The "
     "importance of recent arrivals is operationally intuitive: bikes that just arrived are quickly re-rented at "
     "busy hubs.")

h2("7.8 Drift monitoring")
dr = R["drift"][["feature", "PSI", "train_mean", "test_mean", "status"]].round(3)
table(dr, "Population Stability Index, training vs test", widths=[3.2, 2, 2.5, 2.5, 2.5])
para("All demand features are stable (PSI < 0.1); temperature shows moderate seasonal drift (0.25). In "
     "production the PSI job would be scheduled weekly, and a PSI above 0.25 or a 10% rise in rolling MAE would "
     "trigger retraining.")

h2("7.9 Application: BikeBalance planner")
if (FIG / "fig17_app_planner.png").exists():
    figure("fig17_app_planner", "Streamlit operations planner: forecasts, stock and recommended transfers")
para("The Streamlit app (app/streamlit_app.py) exposes five views: an operations planner (choose an hour, stock "
     "assumption, truck budget and capacity; the map shows receivers, donors and transfer lines, with a "
     "downloadable transfer plan), a forecast explorer per station, the model comparison with SHAP, the "
     "hypothesis results, and the data/SSOT audit. It runs locally, in Docker, or hosted on Modal.")

h2("7.10 Key findings and business implications")
bullets([f"Recent demand is the most valuable predictor; a LightGBM model with station, calendar and lag features "
         f"reduces error by {100*(1-mae('LGBM','SCL')/mae('HA_shw','-')):.0f}% versus the historical-average baseline.",
         "Weather, though clearly related to demand, does not improve one-hour-ahead forecasts once recent demand is "
         "known; operators need not buy premium weather feeds for this horizon.",
         "Demand is concentrated and stable: about 20% of stations generate 55% of departures. Prioritise them.",
         "Forecast-based planning never loses to historical averages, moves fewer bikes, and is significantly "
         "better when trucks or docks are scarce - the realistic situation for a small fleet.",
         "Any rebalancing raises coverage from about 83-89% to about 94-98% in simulation, so the decision to rebalance "
         "matters more than the choice of model; the model matters at the margin and under tight budgets."])
h2("7.11 Recommendations and implementation")
bullets(["Deploy LightGBM SCL (or SCWL) behind the planner; refresh forecasts each hour from the live trip feed.",
         "Use the forecast policy with target = expected demand + one standard deviation, and keep budgets focused on "
         "the 49 priority stations.",
         "Collect dock-level inventory snapshots (GBFS feed) to replace simulation assumptions with observed stock.",
         "Monitor MAE and PSI weekly; retrain monthly or on drift."])
h2("7.12 Limitations and uncertainties")
bullets(["Unmet demand is simulated; true lost demand and monetary savings are unobserved.",
         "Capacities, budgets, initial stock and instantaneous transfers are assumptions (varied across 6 scenarios).",
         "The test period (Nov-Dec) has lower volume and almost no rain, limiting conclusions on weather.",
         "Daily blocking reduces but does not fully remove dependence between days; p-values are approximate.",
         "Wind speed units in the source are questionable (Section 3.5)."])

# ================================================================== CH8
chapter("CHAPTER 8: TEAM RESPONSIBILITY AND SELF-CONTRIBUTION MATRIX")
para("Responsibilities follow the division agreed at the pre-submission viva. L = lead, S = support.")
mat = pd.DataFrame([
    ("Problem identification", "L", "S", "S", "S"),
    ("Data collection", "S", "L", "S", "S"),
    ("Data preprocessing", "S", "L", "S", "S"),
    ("Data analysis (EDA)", "L", "S", "S", "S"),
    ("Implementation", "S", "S", "L", "L"),
    ("Testing and validation", "S", "S", "S", "L"),
    ("Results and interpretation", "L", "S", "L", "L"),
    ("Report preparation", "L", "L", "L", "L"),
    ("Presentation", "L", "L", "L", "L"),
], columns=["Project Activity"] + [m[0] for m in MEMBERS])
table(mat, "Team responsibility matrix", widths=[4.4, 2.9, 2.9, 2.9, 2.9])
h2("Individual Contribution")
para(f"**{MEMBERS[0][0]} ({MEMBERS[0][1]}) - Business analysis and EDA:** defined the stakeholder decision and KPIs "
     "(unmet demand, coverage, transfer effort), formulated the BADIR plan and hypotheses, and produced the EDA "
     "(temporal patterns, weather effects, concentration and net-flow analysis).")
para(f"**{MEMBERS[1][0]} ({MEMBERS[1][1]}) - Data integration:** built the ETL and audit, resolved the unmatched "
     "station IDs and DST weather artefacts, designed the versioned station-hour SSOT and its integrity checks.")
para(f"**{MEMBERS[2][0]} ({MEMBERS[2][1]}) - Forecasting:** engineered forecast-time features, implemented and tuned "
     "the HA, LR, RF and LightGBM models, ran the H1/H2/H4/H5 tests, SHAP analysis and MLflow tracking.")
para(f"**{MEMBERS[3][0]} ({MEMBERS[3][1]}) - Simulation and validation:** designed the trip-level redistribution "
     "simulation and scenarios, tested H3/H6/H7, drift monitoring, unit tests, the Streamlit demo and deployment.")

# ================================================================== CH9
chapter("CHAPTER 9: CONCLUSIONS AND FUTURE SCOPE")
h2("9.1 Summary")
para("BikeBalance integrates 519,235 LA Metro Bike Share trips, the station registry and hourly weather into an "
     "audited station-hour SSOT, forecasts next-hour departures at every station, and converts the forecasts into "
     "budget-constrained transfer recommendations evaluated in a fleet-conserving simulation.")
h2("9.2 Major findings and achievement of objectives")
verd = pd.DataFrame([
    ("H1", "Calendar features help", "Supported", f"-{HT.loc['H1','mae_reduction_pct']:.1f}% MAE"),
    ("H2", "Weather helps beyond calendar+lags", "Not supported", f"{-HT.loc['H2','mae_reduction_pct']:+.1f}% MAE (worse)"),
    ("H3", "Forecast transfers reduce unmet demand", "Partially supported", f"better in {n_sc}/{n_sc}, significant in {n_h3}/{n_sc}"),
    ("H4", "Lags help beyond station+calendar+weather", "Supported", f"-{HT.loc['H4','mae_reduction_pct']:.1f}% MAE"),
    ("H5", "Tree ensembles beat LR", "Supported", f"LGBM -{HT.loc['H5b','mae_reduction_pct']:.1f}%, RF -{HT.loc['H5a','mae_reduction_pct']:.1f}%"),
    ("H6", "Top 20% stations > 50% of later trips", "Supported" if h6_ok else "Not supported", pct(H6["top20_share_later_SepDec"])),
    ("H7", "Larger gains at peak hours", "Not supported", f"significant in {n_h7}/{n_sc} scenarios"),
], columns=["H", "Statement", "Verdict", "Evidence"])
table(verd, "Summary of hypothesis verdicts", widths=[1.2, 6.5, 3.5, 4.8])
para("All six objectives in Section 1.5 were met: the SSOT, EDA, forecasting comparison, simulation, demo, "
     "tracking, explanations and container are delivered in the repository.")
h2("9.3 Conclusions")
para("Short-horizon bike-share demand is driven mainly by time of day and recent activity. Gradient boosting with "
     "lag features is the most accurate approach, and its forecasts translate into fewer lost trips with less "
     "repositioning effort than historical averages, especially under tight operating budgets. Negative results "
     "(H2, H7) are informative: they tell the operator where not to invest.")
h2("9.4 Limitations")
para("Results depend on simulated inventory and on observed (censored) trips; one year of data from one city; "
     "transfers are assumed instantaneous; no cost model.")
h2("9.5 Future work")
bullets(["Multi-hour (2-6 h) forecasts and rolling-horizon optimisation with vehicle routing and travel times.",
         "Demand un-censoring using real-time dock availability (GBFS) and probabilistic (quantile) forecasts.",
         "Spatial models (graph neural networks) and event/holiday calendars; multi-year training.",
         "Field pilot with the operator, A/B testing transfer policies, and cost-benefit evaluation."])

# ================================================================== REFERENCES
chapter("REFERENCES")
refs = [
    'E. Fishman, S. Washington and N. Haworth, "Bike share: A synthesis of the literature," Transport Reviews, vol. 33, no. 2, pp. 148-165, 2013.',
    'E. O\'Mahony and D. B. Shmoys, "Data analysis and optimization for (Citi)Bike sharing," in Proc. 29th AAAI Conf. Artificial Intelligence, 2015, pp. 687-694.',
    'T. Raviv, M. Tzur and I. A. Forma, "Static repositioning in a bike-sharing system: models and solution approaches," EURO J. Transportation and Logistics, vol. 2, no. 3, pp. 187-229, 2013.',
    'J. Schuijbroek, R. C. Hampshire and W.-J. van Hoeve, "Inventory rebalancing and vehicle routing in bike sharing systems," European J. Operational Research, vol. 257, no. 3, pp. 992-1004, 2017.',
    'H. Fanaee-T and J. Gama, "Event labeling combining ensemble detectors and background knowledge," Progress in Artificial Intelligence, vol. 2, no. 2-3, pp. 113-127, 2014.',
    'Los Angeles Metro Bike Share, "Data," [Online]. Available: https://bikeshare.metro.net/about/data/ (accessed Nov. 2026).',
    'A. Faghih-Imani, N. Eluru, A. M. El-Geneidy, M. Rabbat and U. Haq, "How land-use and urban form impact bicycle flows: evidence from the bicycle-sharing system (BIXI) in Montreal," J. Transport Geography, vol. 41, pp. 306-314, 2014.',
    'Krupa1420, "LA Metro Bike-Share 2024," Hugging Face Datasets, 2024. [Online]. Available: https://huggingface.co/datasets/Krupa1420/la-metro-bikeshare-2024',
    'Y. Li, Y. Zheng, H. Zhang and L. Chen, "Traffic prediction in a bike-sharing system," in Proc. 23rd ACM SIGSPATIAL Int. Conf. Advances in Geographic Information Systems, 2015, pp. 1-10.',
    'L. Chen, D. Zhang, L. Wang, D. Yang, X. Ma, S. Li, Z. Wu, G. Pan, T.-M.-T. Nguyen and J. Jakubowicz, "Dynamic cluster-based over-demand prediction in bike sharing systems," in Proc. ACM UbiComp, 2016, pp. 841-852.',
    'J. H. Friedman, "Greedy function approximation: A gradient boosting machine," Annals of Statistics, vol. 29, no. 5, pp. 1189-1232, 2001.',
    'G. Ke, Q. Meng, T. Finley, T. Wang, W. Chen, W. Ma, Q. Ye and T.-Y. Liu, "LightGBM: A highly efficient gradient boosting decision tree," in Advances in Neural Information Processing Systems 30, 2017.',
    'L. Breiman, "Random forests," Machine Learning, vol. 45, no. 1, pp. 5-32, 2001.',
    'F. X. Diebold and R. S. Mariano, "Comparing predictive accuracy," J. Business & Economic Statistics, vol. 13, no. 3, pp. 253-263, 1995.',
    'S. M. Lundberg and S.-I. Lee, "A unified approach to interpreting model predictions," in Advances in Neural Information Processing Systems 30, 2017.',
    'M. Zaharia et al., "Accelerating the machine learning lifecycle with MLflow," IEEE Data Engineering Bulletin, vol. 41, no. 4, pp. 39-45, 2018.',
    'F. Pedregosa et al., "Scikit-learn: Machine learning in Python," J. Machine Learning Research, vol. 12, pp. 2825-2830, 2011.',
    'F. Wilcoxon, "Individual comparisons by ranking methods," Biometrics Bulletin, vol. 1, no. 6, pp. 80-83, 1945.',
]
for i, r in enumerate(refs, 1):
    p = para(f"[{i}] {r}", size=10, after=3)
    p.paragraph_format.left_indent = Cm(0.8)
    p.paragraph_format.first_line_indent = Cm(-0.8)

# ================================================================== APPENDICES
chapter("APPENDICES")
h2("Appendix A: Source code and reproduction")
para(f"Repository: {REPO_URL}")
for line in ["pip install -r requirements.txt", "python run_pipeline.py            # ETL, EDA, models, simulation, evaluation",
             "python -m pytest -q tests", "streamlit run app/streamlit_app.py",
             "docker build -t bikebalance . && docker run -p 8501:8501 bikebalance",
             "modal deploy modal_app.py         # hosted demo", "mlflow ui --backend-store-uri sqlite:///mlflow.db"]:
    p = doc.add_paragraph()
    r = p.add_run(line); r.font.name = "Consolas"; r.font.size = Pt(9)
    p.paragraph_format.space_after = Pt(0)
h2("Appendix B: Data audit log")
aud = [(k, str(v)[:90]) for k, v in A.items() if k not in ("stations_recovered_ids",)]
table(pd.DataFrame(aud, columns=["Check", "Result"]), "Automated data-audit results (data_audit.json)",
      widths=[6, 10], size=8)
h2("Appendix C: SSOT sample")
ss = pd.read_parquet(ROOT / "data" / "processed" / "ssot_station_hour_v1.0.parquet",
                     columns=["station_id", "hour", "departures", "arrivals", "temp_c", "precip_mm", "hour_of_day",
                              "dow", "region", "split"])
smp = ss[ss["departures"] > 0].sample(8, random_state=1).sort_values("hour")
smp["hour"] = smp["hour"].dt.strftime("%Y-%m-%d %H:%M")
table(smp, "Random sample of SSOT rows with departures > 0", size=8)
h2("Appendix D: Full simulation results")
sim_full = SIM[["scenario", "policy", "unmet", "coverage", "coverage_peak", "coverage_offpeak", "bikes_moved",
                "bike_km", "blocked_returns"]].copy()
for c in ("coverage", "coverage_peak", "coverage_offpeak"):
    sim_full[c] = sim_full[c].map(lambda x: f"{100*x:.2f}%")
sim_full["bike_km"] = sim_full["bike_km"].round(0).astype(int)
table(sim_full, "All scenario x policy simulation results", size=7.5)
h2("Appendix E: Additional figures")
if (FIG / "fig18_app_forecast.png").exists():
    figure("fig18_app_forecast", "Streamlit forecast explorer")
para("")
para("END OF REPORT", bold=True, align="c")
para("Add plagiarism report after this page", italic=True, align="c")

# ================================================================== fill abstract and lists
ab = (f"Bike-sharing systems suffer from uneven bicycle availability: commuting and leisure flows empty some "
      f"stations and fill others, causing lost rentals and wasted repositioning effort. BikeBalance supports an "
      f"operations manager who must decide which stations to replenish before the next hour. Using LA Metro Bike "
      f"Share 2024 data ({A['raw_trips']:,} trips, 226 registered stations and 8,784 hourly weather records from Hugging "
      f"Face and the official Metro portal), we built an audited, versioned station-hour single source of truth "
      f"({A['ssot_rows']:,} rows, {A['ssot_stations']} stations), recovering {A['stations_recovered_from_trips']} unregistered "
      f"station IDs and correcting daylight-saving artefacts in the weather data. Following the BADIR framework we "
      f"tested seven pre-registered hypotheses with a strict temporal split (train Jan-Aug, validate Sep-Oct, test "
      f"Nov-Dec), comparing historical averages, Linear Regression, Random Forest and LightGBM with daily-blocked "
      f"Wilcoxon tests and bootstrap confidence intervals. Calendar features (H1, -{HT.loc['H1','mae_reduction_pct']:.1f}% MAE) "
      f"and recent-demand lags (H4, -{HT.loc['H4','mae_reduction_pct']:.1f}%) significantly improved forecasts, and tree "
      f"ensembles beat Linear Regression (H5). Lagged weather did not add value once recent demand was known (H2 "
      f"rejected). The best model, LightGBM, reduced MAE by {100*(1-mae('LGBM','SCL')/mae('HA_shw','-')):.0f}% versus the "
      f"historical-average baseline. The busiest 20% of stations generated {pct(H6['top20_share_later_SepDec'])} of later "
      f"departures (H6). In a fleet-conserving trip-level simulation, forecast-based transfers reduced unmet demand "
      f"versus historical-average transfers in all six capacity/budget scenarios while moving fewer bikes, "
      f"significantly so under tight budgets (H3 partially supported); larger peak-hour gains (H7) were not "
      f"confirmed. The system is delivered as a Python pipeline with MLflow tracking, SHAP explanations, drift "
      f"monitoring and an interactive Streamlit planner deployable via Docker or Modal. We recommend forecast-driven "
      f"rebalancing focused on priority stations, and collecting real dock inventories to validate simulated gains.")
_runs(ABSTRACT_SLOT, ab)
ABSTRACT_SLOT.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
kw = doc.add_paragraph()
ABSTRACT_SLOT._p.addnext(kw._p)
_runs(kw, "**Keywords:** bike sharing, demand forecasting, rebalancing, LightGBM, simulation, hypothesis testing, "
          "BADIR, SHAP, MLOps")


def _insert_list(anchor, items, prefix):
    for i, c in reversed(list(enumerate(items, 1))):
        p = doc.add_paragraph()
        r = p.add_run(f"{prefix} {i}: {c}")
        r.font.size = Pt(10.5)
        p.paragraph_format.space_after = Pt(1)
        anchor._p.addnext(p._p)


_insert_list(LOF_ANCHOR, FIGS, "Figure")
_insert_list(LOT_ANCHOR, TABS, "Table")
