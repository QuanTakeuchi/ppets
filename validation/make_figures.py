"""Regenerate the RU-06 package figures from the committed evidence files.

    pip install matplotlib        # validation-only dependency, not in requirements.txt
    python validation/make_figures.py [--out DIR]

Reads evidence/validation/*.csv|json (written by pilot_study.py, bench_sweep.py,
experiments/sweep.py, run_validation.py) and writes fig1..fig5 PNGs.
Default output: evidence/validation/figures/.
"""

from __future__ import annotations

import argparse
import csv
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch

from _common import EVIDENCE, REPO

BLUE, ORANGE, GREY, GREEN, RED, INK = "#2a6f97", "#c8553d", "#8a8f98", "#3a7d44", "#b23a48", "#222222"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": GREY, "axes.labelcolor": INK, "text.color": INK,
                     "xtick.color": INK, "ytick.color": INK, "figure.dpi": 150})


def load_pilot():
    return json.load(open(EVIDENCE / "pilot_summary.json"))


def fig1_baseline_heatmap(out):
    rows = list(csv.DictReader(open(REPO / "experiments" / "output" / "heatmap_matrix.csv")))
    pds = sorted({float(r["predator_density"]) for r in rows})
    prs = sorted({float(r["predator_repro_rate"]) for r in rows})
    m = np.zeros((len(prs), len(pds)))
    for r in rows:
        m[prs.index(float(r["predator_repro_rate"])), pds.index(float(r["predator_density"]))] = float(r["extinction_probability"])
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    im = ax.imshow(m, origin="lower", aspect="auto", cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(0, len(pds), 2), [f"{v:.2f}" for v in pds[::2]])
    ax.set_yticks(range(0, len(prs), 2), [f"{v:.2f}" for v in prs[::2]])
    ax.set_xlabel("initial predator density")
    ax.set_ylabel("predator reproduction rate")
    ax.set_title("Baseline sweep: P(extinction within 150 generations), 3 replicates per cell", fontsize=10, loc="left")
    cb = fig.colorbar(im, ax=ax)
    cb.set_label("estimated probability (steps of 1/3)")
    fig.tight_layout()
    fig.savefig(out / "fig1_baseline_heatmap.png")
    plt.close(fig)


def fig2_ci(out):
    cells = load_pilot()["cells"]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    y = np.arange(len(cells))
    for i, c in enumerate(cells):
        p3 = c["k3"] / 3
        ax.plot([c["ci3_low"], c["ci3_high"]], [i + 0.17] * 2, color=ORANGE, lw=2.5, solid_capstyle="round")
        ax.plot(p3, i + 0.17, "o", color=ORANGE, ms=7, mec="white", mew=1.5)
        ax.plot([c["ci_low"], c["ci_high"]], [i - 0.17] * 2, color=BLUE, lw=2.5, solid_capstyle="round")
        ax.plot(c["p_by_gen150"], i - 0.17, "o", color=BLUE, ms=7, mec="white", mew=1.5)
    ax.set_yticks(y, [f"density {c['predator_density']:.2f}, repro {c['predator_repro_rate']:.2f}" for c in cells])
    ax.set_xlim(-0.03, 1.03)
    ax.set_xlabel("P(extinction within 150 generations), with Wilson 95% interval")
    ax.invert_yaxis()
    ax.plot([], [], "o-", color=ORANGE, label="3 replicates (as in baseline sweep)")
    ax.plot([], [], "o-", color=BLUE, label=f"{load_pilot()['replicates_per_cell']} replicates (includes those 3)")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, frameon=False, fontsize=9)
    ax.grid(axis="x", color="#e5e5e5", lw=0.6)
    fig.tight_layout()
    fig.savefig(out / "fig2_replicate_uncertainty.png")
    plt.close(fig)


def fig3_horizon(out):
    """Cumulative extinction fraction vs generation, one line per pilot cell
    (from the per-replicate CSV, so the full 0-300 range is resolved)."""
    from collections import defaultdict
    cells = defaultdict(list)
    for r in csv.DictReader(open(EVIDENCE / "pilot_replicates.csv")):
        g = r["extinction_generation"]
        cells[(r["predator_density"], r["predator_repro_rate"])].append(int(g) if g else None)
    xs = np.arange(0, 301)
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    for key, gens in sorted(cells.items()):
        arr = np.array([g for g in gens if g is not None])
        ys = [(arr <= x).sum() / len(gens) for x in xs]
        ax.plot(xs, ys, color=BLUE, lw=1.6, alpha=0.85)
    ax.axvline(150, color=GREY, ls="--", lw=1)
    ax.text(153, 0.03, "sweep horizon (150)", color=GREY, fontsize=8)
    ax.set_xlabel("generation")
    ax.set_ylabel("fraction of 100 replicates extinct by then")
    ax.set_ylim(-0.02, 1.02)
    ax.grid(color="#e5e5e5", lw=0.6)
    ax.set_title("Extinction is an early event: curves are flat long before the horizon (one line per cell)", fontsize=10, loc="left")
    fig.tight_layout()
    fig.savefig(out / "fig3_horizon_sensitivity.png")
    plt.close(fig)


def fig4_bench(out):
    b = json.load(open(EVIDENCE / "bench_results.json"))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.6, 3.4))
    g = [r["grid"] for r in b["step_latency"]]
    a1.plot(g, [r["median_ms"] for r in b["step_latency"]], "-o", color=BLUE, ms=4, label="median")
    a1.plot(g, [r["p95_ms"] for r in b["step_latency"]], "-o", color=ORANGE, ms=4, label="95th percentile")
    a1.axhline(b["nfr01_budget_ms"], color=RED, ls="--", lw=1)
    a1.text(g[0], b["nfr01_budget_ms"] * 1.05, "NFR01 100 ms budget", color=RED, fontsize=8)
    a1.set_xlabel("grid side length (cells)")
    a1.set_ylabel("engine step latency (ms)")
    a1.legend(frameon=False, fontsize=8, loc="center left")
    a1.grid(color="#e5e5e5", lw=0.6)
    w = [r["workers"] for r in b["parallel"]]
    a2.plot(w, [r["speedup"] for r in b["parallel"]], "-o", color=BLUE, ms=4)
    a2.plot([1, max(w)], [1, max(w)], color=GREY, ls=":", lw=1)
    a2.text(max(w) * 0.55, max(w) * 0.5, "ideal", color=GREY, fontsize=8)
    a2.set_xlabel("worker processes")
    a2.set_ylabel("speedup vs serial (64 runs)")
    a2.grid(color="#e5e5e5", lw=0.6)
    fig.tight_layout()
    fig.savefig(out / "fig4_benchmark.png")
    plt.close(fig)


def fig5_pipeline(out):
    fig, ax = plt.subplots(figsize=(7.6, 3.9))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 52)
    ax.axis("off")

    def box(x, y, w, h, text, colour):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.5",
                                    fc="white", ec=colour, lw=2))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8)

    def arrow(x1, y1, x2, y2, label=None, colour=GREY):
        ax.annotate("", (x2, y2), (x1, y1), arrowprops=dict(arrowstyle="->", color=colour, lw=1.4))
        if label:
            ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 1.8, label, ha="center", fontsize=7, color=colour)

    box(0.5, 21, 16, 10, "SimulationConfig\n(validate, seed)", GREEN)
    box(26, 21, 17, 10, "CellularAutomaton-\nEngine.step()", GREEN)
    box(53, 21, 14, 10, "PopulationStats", GREEN)
    box(77, 38, 22, 9, "main.py\nCSV trace", GREEN)
    box(77, 21, 22, 10, "Controller ->\nMainWindow GUI", GREEN)
    box(70, 3, 14, 10, "Threshold-\nAnalyzer\n.run_sweep()", GREEN)
    box(88, 3, 11.5, 10, "HeatmapData\n-> Heatmap-\nView", "#d09b2c")
    arrow(17.2, 26, 25.3, 26, "V01")
    arrow(43.8, 26, 52.3, 26, "V02-V05")
    arrow(67.8, 30, 76.3, 40, "V06")
    arrow(67.8, 26, 76.3, 26, "V10")
    arrow(64, 20, 72, 14, "V07 V08")
    arrow(84.8, 8, 87.3, 8, "V09")
    ax.text(70, 15.5, "heatmap axes show indices,\nnot values (DEF-05)", fontsize=7, color="#9a6b00")
    ax.text(0.5, 50, "green = executed and checked; amber = executed, with a logged defect", fontsize=8, color=GREY)
    ax.text(0.5, 3, "Not implemented yet: Run-Sweep UI control,\nmultiprocessing, ScenarioManager, ReportExporter,\nhistorical calibration (stretch scope)", fontsize=8, color=GREY)
    fig.tight_layout()
    fig.savefig(out / "fig5_pipeline.png")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(EVIDENCE / "figures"))
    args = ap.parse_args()
    from pathlib import Path
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    fig1_baseline_heatmap(out)
    fig2_ci(out)
    fig3_horizon(out)
    fig4_bench(out)
    fig5_pipeline(out)
    print("wrote", sorted(p.name for p in out.glob("fig*.png")))


if __name__ == "__main__":
    main()
