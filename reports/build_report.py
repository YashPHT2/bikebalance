"""Build the final project report (DOCX + PDF) following the BMU ADS template.

All numbers are read from reports/tables/*.csv|json so the report always matches the code.
    python reports/build_report.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "reports" / "tables"
FIG = ROOT / "reports" / "figures"
OUT = ROOT / "deliverables"
OUT.mkdir(exist_ok=True)

TITLE = "BikeBalance: Smart Bicycle Redistribution System"
MEMBERS = [("Sahil Yadav", "240624"), ("Shorya", "240643"),
           ("Yash Kumar Sharma", "240698"), ("Tejas Duggal", "240672")]
REPO_URL = "https://github.com/<your-org>/bikebalance"  # TODO: replace after pushing

# ------------------------------------------------------------------ data
R = {
    "audit": json.loads((T / "data_audit.json").read_text()),
    "eda": json.loads((T / "eda_summary.json").read_text()),
    "metrics": pd.read_csv(T / "model_metrics.csv"),
    "tuning": pd.read_csv(T / "tuning_results.csv"),
    "hypf": pd.read_csv(T / "hypothesis_forecast_tests.csv"),
    "h6": json.loads((T / "h6_result.json").read_text()),
    "sim": pd.read_csv(T / "simulation_summary.csv"),
    "hyps": pd.read_csv(T / "hypothesis_simulation_tests.csv"),
    "peak": json.loads((T / "peak_hours.json").read_text()),
    "shap": pd.read_csv(T / "shap_importance.csv", index_col=0).iloc[:, 0],
    "drift": pd.read_csv(T / "drift_psi.csv"),
    "best": json.loads((T / "best_params.json").read_text()),
}

# ------------------------------------------------------------------ helpers
doc = Document()
st = doc.styles["Normal"]
st.font.name = "Times New Roman"
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
st.font.size = Pt(12)
st.paragraph_format.space_after = Pt(6)
st.paragraph_format.line_spacing = 1.3
for s in doc.sections:
    s.left_margin = s.right_margin = Cm(2.5)
    s.top_margin = s.bottom_margin = Cm(2.3)

FIGS, TABS = [], []


def add_page_number(section):
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    for t, txt in (("begin", None), (None, "PAGE"), ("end", None)):
        if t:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), t)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = txt
        run._r.append(el)


add_page_number(doc.sections[0])


def para(text="", bold=False, italic=False, size=None, align=None, after=None, style=None):
    p = doc.add_paragraph(style=style)
    _runs(p, text, bold, italic, size)
    if align == "c":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "j" or align is None:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    return p


def _runs(p, text, bold=False, italic=False, size=None):
    """Support **bold** inline markup."""
    parts = text.split("**")
    for i, part in enumerate(parts):
        if not part:
            continue
        r = p.add_run(part)
        r.bold = bold or (i % 2 == 1)
        r.italic = italic
        if size:
            r.font.size = Pt(size)


def bullets(items, style="List Bullet"):
    for it in items:
        p = doc.add_paragraph(style=style)
        _runs(p, it)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_after = Pt(2)


def chapter(title):
    doc.add_page_break()
    h = doc.add_heading(title, level=1)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for r in h.runs:
        r.font.name = "Times New Roman"
        r.font.size = Pt(16)
        r.font.color.rgb = RGBColor(0, 0, 0)


def h2(title):
    h = doc.add_heading(title, level=2)
    for r in h.runs:
        r.font.name = "Times New Roman"
        r.font.size = Pt(13)
        r.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)


def h3(title):
    h = doc.add_heading(title, level=3)
    for r in h.runs:
        r.font.name = "Times New Roman"
        r.font.size = Pt(12)
        r.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)


def figure(name, caption, width=15.5):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(FIG / f"{name}.png"), width=Cm(width))
    n = len(FIGS) + 1
    FIGS.append(caption)
    c = para(f"Figure {n}: {caption}", italic=True, size=10, align="c", after=10)
    return n


def table(df, caption, widths=None, fmt=None, size=9):
    n = len(TABS) + 1
    TABS.append(caption)
    para(f"Table {n}: {caption}", bold=True, size=10, align="c", after=2)
    t = doc.add_table(rows=1, cols=len(df.columns))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, c in enumerate(df.columns):
        cell = t.rows[0].cells[i]
        cell.text = ""
        r = cell.paragraphs[0].add_run(str(c))
        r.bold = True
        r.font.size = Pt(size)
        sh = OxmlElement("w:shd")
        sh.set(qn("w:fill"), "D9E2F3")
        cell._tc.get_or_add_tcPr().append(sh)
    for _, row in df.iterrows():
        cells = t.add_row().cells
        for i, v in enumerate(row):
            if fmt and isinstance(v, float):
                v = fmt.format(v)
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(str(v))
            r.font.size = Pt(size)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return n


def f3(x):
    return f"{x:.3f}"


def pct(x, d=1):
    return f"{100 * x:.{d}f}%"


def pfmt(p):
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


# ------------------------------------------------------------------ derived numbers
A, E, M = R["audit"], R["eda"], R["metrics"]
mt = M[M["split"] == "test"].copy()
mv = M[M["split"] == "val"].copy()


def mae(model, feats, split="test"):
    d = M[(M["model"] == model) & (M["features"] == feats) & (M["split"] == split)]
    return float(d["MAE"].iloc[0])


def rmse(model, feats, split="test"):
    d = M[(M["model"] == model) & (M["features"] == feats) & (M["split"] == split)]
    return float(d["RMSE"].iloc[0])


HF = R["hypf"]
HT = HF[HF["split"] == "test"].set_index("hypothesis")
HV = HF[HF["split"] == "val"].set_index("hypothesis")


def supported(h):
    r = HT.loc[h]
    return bool(r["wilcoxon_p"] < 0.05 and r["ci95_low"] > 0)


HS = R["hyps"].set_index("scenario")
n_h3 = int(((HS["H3_wilcoxon_p"] < 0.05) & (HS["H3_unmet_reduction_vs_HA"] > 0)).sum())
n_h7 = int(((HS["H7_wilcoxon_p"] < 0.05) & (HS["H7_gain_peak_pp"] > HS["H7_gain_offpeak_pp"])).sum())
n_sc = len(HS)
H6 = R["h6"]
h6_ok = H6["ci95"][0] > 0.5 and H6["wilcoxon_p_share_gt_50"] < 0.05
SIM = R["sim"]
ref_sc = "cap15_B25"
sref = SIM[SIM["scenario"] == ref_sc].set_index("policy")
best_model = mt.sort_values("MAE").iloc[0]
SSOT_ROWS = A["ssot_rows"]

exec(open(Path(__file__).with_name("report_text.py"), encoding="utf-8").read())

# ------------------------------------------------------------------ save
docx_path = OUT / "BikeBalance_Final_Report_Group12.docx"
doc.save(docx_path)
print("saved", docx_path)
if "--pdf" in sys.argv:
    import win32com.client
    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    d = word.Documents.Open(str(docx_path))
    d.Fields.Update()
    d.TablesOfContents(1).Update() if d.TablesOfContents.Count else None
    d.SaveAs(str(OUT / "BikeBalance_Final_Report_Group12.pdf"), FileFormat=17)
    d.Close(False)
    word.Quit()
    print("saved PDF")
