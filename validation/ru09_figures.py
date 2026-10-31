"""RU-09 figures, read from evidence/ru09/ru09_results.json.

    python validation/ru09_figures.py

Writes evidence/ru09/figures/. The palette passes validate_palette.js in light
mode; identity is also carried by marker shape and line style for print.
"""

from __future__ import annotations

import json

import numpy as np

from hs4_common import REPO

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = REPO / "evidence" / "ru09"
FIG = OUT / "figures"
FIG.mkdir(exist_ok=True)
R = json.loads((OUT / "ru09_results.json").read_text(encoding="utf-8"))

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"

plt.rcParams.update({
    "font.family": "Calibri", "font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
    "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.7,
    "axes.axisbelow": True, "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
    "figure.facecolor": "white", "axes.facecolor": "white",
})


def fig_d_star_vs_size():
    S = {int(k): v for k, v in R["Q1"]["sizes"].items()}
    P = R["Q7"]["prospective_L150"]
    S[150] = dict(logit=P["logit"], model_free=P["model_free"], loglog=dict(d_star=P["measured"], ci=P["ci"]))
    Ls = sorted(S)
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.set_xscale("log")
    series = (("logit", "Logistic", BLUE, "o", 0.97), ("loglog", "Log-log", ORANGE, "s", 1.0),
              ("model_free", "Model-free", AQUA, "D", 1.03))
    for key, label, col, mk, off in series:
        xs = [L * off for L in Ls]
        ys = [S[L][key]["d_star"] for L in Ls]
        lo = [S[L][key]["d_star"] - S[L][key]["ci"][0] for L in Ls]
        hi = [S[L][key]["ci"][1] - S[L][key]["d_star"] for L in Ls]
        ax.errorbar(xs, ys, yerr=[lo, hi], color=col, marker=mk, ms=5.5, lw=1.8, capsize=2.5, elinewidth=1,
                    label=f"{label}, bootstrap 95% CI")
    g = np.geomspace(20, 150, 200)
    ax.plot(g, 0.3396540394823453 - 2.644556258189115 / g, color=MUTED, ls=":", lw=1.4,
            label="HS4 fit a + b/L (from L ≤ 50)")
    ax.plot(g, R["Q2"]["links"]["loglog"]["d_star"] + R["Q7"]["ln_coefficient_predicted"] * np.log(g / 30), color=INK,
            ls="--", lw=1.2, label="Refuge prediction (from L = 30 only)")
    ax.set_xticks(Ls)
    ax.set_xticklabels([str(L) for L in Ls])
    ax.minorticks_off()
    ax.set_xlabel("Grid side L (toroidal, L × L; log scale)")
    ax.set_ylabel("d* (initial predator density at P = 0.5)")
    ax.set_title("d* keeps rising with grid size")
    ax.legend(fontsize=8.5, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIG / "fig1_d_star_vs_size.png", dpi=200)
    plt.close(fig)


def fig_estimator_misfit():
    C = R["Q2"]["curve"]
    x = np.array([c["density"] for c in C])
    n = np.array([c["n"] for c in C], dtype=float)
    k = np.array([c["k"] for c in C], dtype=float)
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 3.6), gridspec_kw=dict(width_ratios=[1.15, 1]))
    a.scatter(x, k / n, s=26, color=INK, zorder=3, label="Observed (n = 150 per level)")
    a.plot(x, np.array([c["logit"] for c in C]) / n, color=BLUE, lw=1.8, label="Logistic")
    a.plot(x, np.array([c["loglog"] for c in C]) / n, color=ORANGE, lw=1.8, ls="--", label="Log-log")
    a.axhline(0.5, color=MUTED, lw=0.7, ls=":")
    a.set_xlabel("Initial predator density")
    a.set_ylabel("P(extinction by generation 150)")
    a.set_title("Curve shape")
    a.legend(fontsize=8.5, loc="upper left")
    b.axhline(0, color=MUTED, lw=0.8)
    b.plot(x, k - np.array([c["logit"] for c in C]), color=BLUE, marker="o", ms=5, lw=1.4, label="Logistic")
    b.plot(x, k - np.array([c["loglog"] for c in C]), color=ORANGE, marker="s", ms=5, lw=1.4, ls="--", label="Log-log")
    b.set_xlabel("Initial predator density")
    b.set_ylabel("Observed − expected extinctions")
    b.set_title("Where the logistic errs")
    b.legend(fontsize=8.5, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIG / "fig3_estimator_misfit.png", dpi=200)
    plt.close(fig)


def fig_pathways():
    Q = R["Q3"]
    panels = [k for k in ("L20", "L30", "L50", "L100", "repro 0.05", "repro 0.30") if k in Q]
    titles = {"L20": "L = 20", "L30": "L = 30", "L50": "L = 50", "L100": "L = 100",
              "repro 0.05": "L = 30, repro 0.05", "repro 0.30": "L = 30, repro 0.30"}
    fig, axes = plt.subplots(2, 3, figsize=(7.2, 4.4), sharex=True, sharey=True)
    for ax, key in zip(axes.flat, panels):
        pl = Q[key]["per_level"]
        x = np.array([p["density"] for p in pl])
        n = np.array([p["n"] for p in pl], dtype=float)
        pred = np.array([p["predator_first"] for p in pl]) / n
        prey = np.array([p["prey_first"] for p in pl]) / n
        ax.bar(x, pred, width=0.0165, color=BLUE, label="Predators die out first")
        ax.bar(x, np.maximum(prey - 0.008, 0), width=0.0165, bottom=pred + 0.008, color=ORANGE, hatch="///", edgecolor="white",
               linewidth=0, label="Prey wiped out first")
        ax.set_title(f"{titles[key]}: {100 * Q[key]['prey_share']:.0f}% prey first", fontsize=9.5)
        ax.grid(axis="x", visible=False)
        ax.set_ylim(0, 1.03)
    for ax in axes[1]:
        ax.set_xlabel("Initial predator density")
    for ax in axes[:, 0]:
        ax.set_ylabel("Share of runs")
    h, l = axes.flat[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=2, fontsize=9.5)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIG / "fig4_extinction_pathways.png", dpi=200)
    plt.close(fig)


def fig_failure_path():
    W = {"failed": "#fbe9e2", "model": "#e3eefb", "gap": "#f1f0ec"}
    E = {"failed": ORANGE, "model": BLUE, "gap": MUTED}
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.axis("off")
    ax.grid(False)
    ax.set_xlim(0, 14.4)
    ax.set_ylim(0, 9.2)

    def box(x, y, w, h, title, sub, kind, tag):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05,rounding_size=0.12", fc=W[kind],
                                    ec=E[kind], lw=1.3))
        ax.text(x + 0.15, y + h - 0.32, title, fontsize=9, weight="bold", color=INK, va="center")
        ax.text(x + 0.15, y + h - 0.68, sub, fontsize=7.8, color=MUTED, va="top", linespacing=1.15)
        ax.text(x + w - 0.13, y + 0.2, tag, fontsize=8.2, weight="bold", color=INK, va="center", ha="right")

    def arrow(a, b):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=10, color=MUTED, lw=1))

    box(0.1, 6.5, 4.3, 2.4, "SimulationConfig", "One prey density, toroidal only,\nrepro rate tested at 3 values", "gap", "LIM-5, LIM-4")
    box(5.0, 6.5, 4.3, 2.4, "Grid + CA engine", "d* depends on the finite grid;\nstep over budget at L = 100", "model", "LIM-1, LIM-8")
    box(9.9, 6.5, 4.4, 2.4, "ThresholdAnalyzer", "Stops at first extinction;\n150-generation horizon", "model", "LIM-2, LIM-4")
    box(9.9, 3.45, 4.4, 2.4, "RunRecord / HeatmapData", "Binary \"extinct\" joins two pathways;\nno trajectory is stored", "failed", "LIM-2, LIM-3")
    box(5.0, 3.45, 4.3, 2.4, "estimates.fit_threshold", "Logistic only: biased high, and its\ninterval often misses the true value", "failed", "LIM-3")
    box(0.1, 3.45, 4.3, 2.4, "Reported claim", "Applies to one setting; no analytic,\nwell-mixed or field comparison", "gap", "LIM-6")
    box(5.0, 0.4, 4.3, 2.4, "GUI / HeatmapView", "No sweep button; no interval shown;\nmanifest not in the application", "gap", "LIM-7")
    box(0.1, 0.4, 4.3, 2.4, "Provenance", "Results predate the tag; manifests use\nthe fingerprint; one machine", "failed", "LIM-9, LIM-10")

    arrow((4.48, 7.7), (4.95, 7.7))
    arrow((9.38, 7.7), (9.85, 7.7))
    arrow((12.1, 6.42), (12.1, 5.92))
    arrow((9.85, 4.65), (9.38, 4.65))
    arrow((4.95, 4.65), (4.48, 4.65))
    arrow((7.15, 3.38), (7.15, 2.88))
    arrow((2.25, 2.88), (2.25, 3.38))

    for k, (lab, kind) in enumerate((("Software or process fell short", "failed"), ("Software correct; model or design property", "model"),
                                     ("Not built or not measured yet", "gap"))):
        y = 2.2 - k * 0.72
        ax.add_patch(plt.Rectangle((9.9, y - 0.2), 0.42, 0.4, fc=W[kind], ec=E[kind], lw=1.3))
        ax.text(10.45, y, lab, fontsize=8.2, color=INK, va="center")
    fig.tight_layout(pad=0.2)
    fig.savefig(FIG / "fig2_failure_path.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    fig_d_star_vs_size()
    fig_estimator_misfit()
    fig_pathways()
    fig_failure_path()
    print("figures written to", FIG)
