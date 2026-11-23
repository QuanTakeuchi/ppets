"""HS6 figures, read from evidence/hs6/hs6_results.json.

    python validation/hs6_figures.py

Writes evidence/hs6/figures/. Same palette and style as ru09_figures.py (validated
there); identity is also carried by marker shape and line style for print.
"""

from __future__ import annotations

import json

import numpy as np

from hs4_common import REPO

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = REPO / "evidence" / "hs6"
FIG = OUT / "figures"
FIG.mkdir(exist_ok=True)
R = json.loads((OUT / "hs6_results.json").read_text(encoding="utf-8"))

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "font.family": "Calibri", "font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
    "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.7,
    "axes.axisbelow": True, "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
    "figure.facecolor": "white", "axes.facecolor": "white",
})


def _errs(levels, key_p, key_ci):
    x = np.array([lv["density"] for lv in levels])
    p = np.array([lv[key_p] for lv in levels])
    lo = np.clip(p - np.array([lv[key_ci][0] for lv in levels]), 0, None)
    hi = np.clip(np.array([lv[key_ci][1] for lv in levels]) - p, 0, None)
    return x, p, [lo, hi]


def fig_well_mixed():
    groups = R["F3"]["groups"]
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.5), sharey=True)
    for ax, L in zip(axes, (30, 75)):
        f1 = R["F1"][str(L)]
        sp = groups[f"L{L}"]["levels"]
        wm = groups[f"well-mixed L{L}"]["levels"]
        x, p, e = _errs(sp, "p_extinct", "ci_extinct")
        ax.errorbar(x, p, yerr=e, color=BLUE, marker="o", ms=4.5, lw=1.8, capsize=2, elinewidth=0.9,
                    label="Spatial (Moore neighbours)")
        x, p, e = _errs(wm, "p_extinct", "ci_extinct")
        ax.errorbar(x, p, yerr=e, color=ORANGE, marker="s", ms=4.5, lw=1.8, ls="--", capsize=2, elinewidth=0.9,
                    label="Well-mixed (8 random partners)")
        ax.set_xscale("log")
        ax.axhline(0.5, color=MUTED, lw=0.8, ls=":")
        d = f1["spatial"]["model_free"]["d_star"]
        ax.axvline(d, color=BLUE, lw=0.8, ls=":")
        ax.annotate(f"spatial d* = {d:.3f}\n(model-free)", (d, 0.30), xytext=(6, 0), textcoords="offset points", color=INK, fontsize=9)
        ax.set_title(f"{L}×{L} grid")
        ax.set_xlabel("Initial predator density (log scale)")
        ax.set_xticks([0.001, 0.003, 0.01, 0.03, 0.1, 0.3])
        ax.set_xticklabels(["0.001", "0.003", "0.01", "0.03", "0.1", "0.3"])
        ax.set_ylim(-0.03, 1.05)
    axes[0].set_ylabel("P(either species extinct by generation 150)")
    axes[0].legend(loc="center left", bbox_to_anchor=(0.0, 0.72), fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "fig_hs6_well_mixed.png", dpi=200)
    plt.close(fig)


def fig_pathways_by_density():
    lv = R["F3"]["groups"]["L30"]["levels"]
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    for key, ci, label, col, mk, ls in (("p_extinct", "ci_extinct", "Either species (the d* outcome)", INK, "o", "-"),
                                        ("p_predator_first", "ci_predator_first", "Predators die out first", BLUE, "s", "-"),
                                        ("p_prey_first", "ci_prey_first", "Prey wiped out first", ORANGE, "D", "--")):
        x, p, e = _errs(lv, key, ci)
        ax.errorbar(x, p, yerr=e, color=col, marker=mk, ms=4.5, lw=1.8, ls=ls, capsize=2, elinewidth=0.9, label=label)
    ax.axhline(0.5, color=MUTED, lw=0.8, ls=":")
    ax.set_xlabel("Initial predator density")
    ax.set_ylabel("Probability, Wilson 95% CI")
    ax.set_title("30×30, 2,700 runs: the two pathways and their sum")
    ax.legend(loc="upper left", fontsize=9)
    ax.set_ylim(-0.03, 1.05)
    fig.tight_layout()
    fig.savefig(FIG / "fig_hs6_pathways_by_density.png", dpi=200)
    plt.close(fig)


def fig_coverage():
    T = R["F2"]["truths"]
    names = list(T)
    meth = (("loglog", "Log-log", ORANGE, "s"), ("model_free", "Model-free", AQUA, "D"), ("logit", "Logistic", BLUE, "o"))
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.2), sharey=True)
    for ax, reps in zip(axes, ("30", "150")):
        for j, (m, label, col, mk) in enumerate(meth):
            ys = np.arange(len(names)) + (j - 1) * 0.22
            c = [T[n]["by_replicates"][reps][m]["coverage"] for n in names]
            lo = [max(0.0, c[i] - T[n]["by_replicates"][reps][m]["coverage_wilson"][0]) for i, n in enumerate(names)]
            hi = [max(0.0, T[n]["by_replicates"][reps][m]["coverage_wilson"][1] - c[i]) for i, n in enumerate(names)]
            ax.errorbar(c, ys, xerr=[lo, hi], color=col, marker=mk, ms=5, lw=0, elinewidth=1, capsize=2, label=label)
        ax.axvline(0.95, color=MUTED, lw=0.9, ls=":")
        ax.axvline(0.90, color=MUTED, lw=0.6, ls="--")
        ax.set_title(f"{reps} replicates per level")
        ax.set_xlim(-0.02, 1.02)
        ax.set_xlabel("Coverage of the true d*")
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels([f"Truth: {n}" for n in names])
        ax.grid(axis="y", visible=False)
    axes[0].legend(loc="center left", bbox_to_anchor=(0.0, 0.72), fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "fig_hs6_coverage_stress.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    fig_well_mixed()
    fig_pathways_by_density()
    fig_coverage()
    print("figures in", FIG)
