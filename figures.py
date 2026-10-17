"""Two figures for the gap statement (light mode, print)."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("out")

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASE = "#c3c2b7"
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"  # blue, orange, aqua (validated, adjacent order)
REST = "#d9d8d2"  # neutral "everything else"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 8.5,
    "axes.edgecolor": BASE,
    "axes.labelcolor": INK2,
    "xtick.color": MUTED,
    "ytick.color": INK,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
})


def style(ax):
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(BASE)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", length=0)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def inside_label(ax, x_left, width, y, text, fill, min_width):
    if width < min_width:
        return
    lum = {S1: 0.19, S2: 0.30, S3: 0.32}.get(fill, 0.7)
    color = "#ffffff" if lum < 0.25 else INK
    ax.text(x_left + width / 2, y, text, ha="center", va="center", fontsize=7.5, color=color)


# ---------- Figure 1 ----------
rows = json.load(open(OUT / "partA_leaderboard_localization.json", encoding="utf-8"))
rows = sorted(rows, key=lambda r: r["resolved"])  # best at top after barh
labels = [r["system"].replace(" (new)", "") for r in rows]
loc = [(r["wrong_file"] + r["no_patch"]) / 3 for r in rows]
patch = [r["right_file_failed"] / 3 for r in rows]
res = [r["resolved"] / 3 for r in rows]

fig, ax = plt.subplots(figsize=(6.6, 3.7))
y = range(len(rows))
h = 0.62
ax.barh(y, loc, height=h, color=S1, edgecolor=SURFACE, linewidth=1.6, label="Gold file not edited")
ax.barh(y, patch, left=loc, height=h, color=S2, edgecolor=SURFACE, linewidth=1.6, label="Gold file edited, tests fail")
ax.barh(y, res, left=[a + b for a, b in zip(loc, patch)], height=h, color=S3, edgecolor=SURFACE, linewidth=1.6, label="Resolved")
for i in y:
    inside_label(ax, 0, loc[i], i, f"{loc[i]:.0f}%", S1, 8)
    inside_label(ax, loc[i], patch[i], i, f"{patch[i]:.0f}%", S2, 8)
    inside_label(ax, loc[i] + patch[i], res[i], i, f"{res[i]:.0f}%", S3, 8)
ax.set_yticks(list(y))
ax.set_yticklabels(labels)
ax.set_xlim(0, 100)
ax.set_xticks([0, 25, 50, 75, 100])
ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
ax.set_xlabel("Share of the 300 SWE-bench Lite issues")
style(ax)
ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, frameon=False, fontsize=7.5,
          handlelength=1.0, handleheight=1.0, columnspacing=1.2, labelcolor=INK2)
fig.suptitle("Outcome of each issue, by whether the final patch edits the gold file(s)",
             x=0.01, ha="left", fontsize=9.5, color=INK, y=0.985)
fig.subplots_adjust(left=0.31, right=0.97, top=0.86, bottom=0.13)
fig.savefig(OUT / "fig1_localization_outcomes.png", dpi=220)
plt.close(fig)

# ---------- Figure 2 ----------
s = json.load(open(OUT / "partC_agentless_summary.json", encoding="utf-8"))
n_miss = s["gold_never_reached_repair"]["n"]
res_miss = s["gold_never_reached_repair"]["resolved"]
tok_share = s["share_total_tokens_on_gold_never_reached_repair"] * 100
bars = [
    ("Issues (n = 300)", n_miss / 300 * 100),
    (f"LLM tokens spent ({s['all']['tok_total_sum'] / 1e6:.1f}M)", tok_share),
    (f"Issues resolved (n = {s['all']['resolved']})", res_miss / s["all"]["resolved"] * 100),
]
fig, ax = plt.subplots(figsize=(6.6, 2.1))
yy = list(range(len(bars)))[::-1]
for yi, (lab, v) in zip(yy, bars):
    ax.barh(yi, v, height=0.56, color=S1, edgecolor=SURFACE, linewidth=1.6)
    ax.barh(yi, 100 - v, left=v, height=0.56, color=REST, edgecolor=SURFACE, linewidth=1.6)
    txt = f"{v:.1f}%"
    if v >= 9:
        ax.text(v / 2, yi, txt, ha="center", va="center", fontsize=7.5, color="#ffffff")
    else:
        ax.text(v + 1.2, yi, txt, ha="left", va="center", fontsize=7.5, color=INK)
ax.set_yticks(yy)
ax.set_yticklabels([b[0] for b in bars])
ax.set_xlim(0, 100)
ax.set_xticks([0, 25, 50, 75, 100])
ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
style(ax)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=S1, label="Gold file never reached the repair stage"),
                   Patch(color=REST, label="Gold file reached the repair stage")],
          loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False, fontsize=7.5,
          handlelength=1.0, handleheight=1.0, labelcolor=INK2)
fig.suptitle("Agentless 1.5 + GPT-4o: issues lost at localization still consume repair tokens",
             x=0.01, ha="left", fontsize=9.5, color=INK, y=0.975)
fig.subplots_adjust(left=0.27, right=0.97, top=0.76, bottom=0.12)
fig.savefig(OUT / "fig2_agentless_token_waste.png", dpi=220)
plt.close(fig)
print("ok")
