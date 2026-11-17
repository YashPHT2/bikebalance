"""Draw the pipeline workflow diagram (fig00_workflow.png)."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent / "figures" / "fig00_workflow.png"

boxes = [
    (0.5, 3.0, "Raw data\n(Hugging Face)\ntrips 519k | stations 226\nweather 8,784", "#dbe9f6"),
    (3.1, 3.0, "ETL + audit\nID recovery, DST fix,\nrow-count & m:1 checks", "#dbe9f6"),
    (5.7, 3.0, "SSOT v1.0\nstation-hour table\n1.97M x 25", "#cfe8d6"),
    (8.3, 3.0, "EDA\npatterns, weather,\nconcentration (H6)", "#fdebd3"),
    (3.1, 0.9, "Features (t-available)\nS | C | W(lag 1h) | L", "#fdebd3"),
    (5.7, 0.9, "Models\nHA | LR | RF | LightGBM\ntune on Sep-Oct", "#fdebd3"),
    (8.3, 0.9, "Test Nov-Dec\nMAE/RMSE, Wilcoxon,\nbootstrap (H1,H2,H4,H5)", "#fdebd3"),
    (10.9, 0.9, "Simulation\nHA vs forecast transfers\n(H3, H7)", "#f6d5d5"),
    (10.9, 3.0, "Deploy & monitor\nStreamlit | Docker\nMLflow | SHAP | PSI", "#e5dcf3"),
]
fig, ax = plt.subplots(figsize=(13.5, 4.6))
W, H = 2.2, 1.35
for x, y, t, c in boxes:
    ax.add_patch(FancyBboxPatch((x, y), W, H, boxstyle="round,pad=0.05", fc=c, ec="#33475b", lw=1.2))
    ax.text(x + W / 2, y + H / 2, t, ha="center", va="center", fontsize=8.6)


def arrow(a, b):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=14, lw=1.3, color="#33475b"))


arrow((2.75, 3.67), (3.05, 3.67))
arrow((5.35, 3.67), (5.65, 3.67))
arrow((7.95, 3.67), (8.25, 3.67))
arrow((6.8, 2.95), (4.2, 2.3))
arrow((5.35, 1.57), (5.65, 1.57))
arrow((7.95, 1.57), (8.25, 1.57))
arrow((10.55, 1.57), (10.85, 1.57))
arrow((12.0, 2.3), (12.0, 2.95))
ax.text(0.5, 4.75, "B  Business question  ->  A  Analysis plan (H1-H7)  ->  D  Data  ->  I  Insights  ->  R  Recommendations",
        fontsize=10, color="#1f3a5f", weight="bold")
ax.set_xlim(0.3, 13.3)
ax.set_ylim(0.6, 5.0)
ax.axis("off")
fig.tight_layout()
fig.savefig(OUT, dpi=170)
print(OUT)
