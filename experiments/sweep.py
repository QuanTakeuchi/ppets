"""
Standalone research-experiment script for the GRAD 695 final report.

NOT part of the PPETS application itself. As of Hard Stop 3, Module 3
(ThresholdAnalyzer/HeatmapView, ppets/analysis/) exists as an
implementation-baseline skeleton — see KNOWN_ISSUES.md for why this script
hasn't been switched over to it yet. This script drives the
CellularAutomatonEngine headlessly, exactly as main.py does, but sweeps two
ecological parameters across many seeded replicate runs to produce a real
extinction/coexistence dataset for the report's Results & Analysis chapter.

Outputs (repo-relative, gitignored — see "Artifact storage conventions" in
the root README):
  sweep_results.csv   one row per (predator_density, predator_repro_rate, replicate)
  heatmap_matrix.csv  aggregated extinction probability grid
  curve_*.csv         generation-by-generation trace for 3 representative runs
"""

import csv
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from ppets.simulation import CellularAutomatonEngine, SimulationConfig

OUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUT_DIR, exist_ok=True)

GRID = 30
MAX_GEN = 150
REPLICATES = 3

# Fixed baseline ecological parameters (LLD §2 defaults / SRS FR03 ranges).
BASE = dict(
    width=GRID, height=GRID,
    prey_density=0.30,
    prey_repro_rate=0.20,
    prey_death_threshold=3,
    starvation_rate=3,
)

# Sweep axes: initial predator density (X) vs predator reproduction rate (Y).
# These two parameters directly control predation pressure on the prey
# population and are the pair most directly tied to the project's research
# question (Simulating Extinction Thresholds in Predator-Prey Systems).
PRED_DENSITY_VALUES = [round(0.02 + 0.02 * i, 2) for i in range(20)]   # 0.02 .. 0.40
PRED_REPRO_VALUES = [round(0.02 + 0.02 * i, 2) for i in range(10)]     # 0.02 .. 0.20


def run_one(pred_density, pred_repro, seed):
    cfg = SimulationConfig(
        predator_density=pred_density,
        predator_repro_rate=pred_repro,
        seed=seed,
        **BASE,
    )
    engine = CellularAutomatonEngine(cfg)
    outcome = "coexistence"
    ext_gen = None
    for _ in range(MAX_GEN):
        stats = engine.step()
        if stats.is_extinct():
            ext_gen = stats.generation
            outcome = "prey_extinct" if stats.prey_count == 0 else "predator_extinct"
            break
    final = engine.history[-1]
    return outcome, ext_gen, final.prey_count, final.predator_count, engine.generation


def main():
    t_start = time.perf_counter()
    rows = []
    total = len(PRED_DENSITY_VALUES) * len(PRED_REPRO_VALUES) * REPLICATES
    done = 0
    for pd in PRED_DENSITY_VALUES:
        for pr in PRED_REPRO_VALUES:
            for rep in range(REPLICATES):
                seed = hash((pd, pr, rep)) % (2**31)
                outcome, ext_gen, prey_final, pred_final, gens_run = run_one(pd, pr, seed)
                rows.append([pd, pr, rep, seed, outcome, ext_gen, prey_final, pred_final, gens_run])
                done += 1
        print(f"predator_density={pd} done ({done}/{total}, {time.perf_counter()-t_start:.1f}s elapsed)", flush=True)

    with open(os.path.join(OUT_DIR, "sweep_results.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["predator_density", "predator_repro_rate", "replicate", "seed",
                     "outcome", "extinction_generation", "prey_final", "predator_final", "generations_run"])
        w.writerows(rows)

    # Aggregate: extinction probability (either species) per (pd, pr) cell.
    grid_out = {}
    for pd in PRED_DENSITY_VALUES:
        for pr in PRED_REPRO_VALUES:
            cell_rows = [r for r in rows if r[0] == pd and r[1] == pr]
            n_ext = sum(1 for r in cell_rows if r[4] != "coexistence")
            n_prey_ext = sum(1 for r in cell_rows if r[4] == "prey_extinct")
            n_pred_ext = sum(1 for r in cell_rows if r[4] == "predator_extinct")
            grid_out[(pd, pr)] = (n_ext / len(cell_rows), n_prey_ext / len(cell_rows), n_pred_ext / len(cell_rows))

    with open(os.path.join(OUT_DIR, "heatmap_matrix.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["predator_density", "predator_repro_rate", "extinction_probability",
                     "prey_extinction_probability", "predator_extinction_probability"])
        for pd in PRED_DENSITY_VALUES:
            for pr in PRED_REPRO_VALUES:
                p_ext, p_prey, p_pred = grid_out[(pd, pr)]
                w.writerow([pd, pr, p_ext, p_prey, p_pred])

    print(f"Sweep complete in {time.perf_counter()-t_start:.1f}s. {total} runs.")

    # --- Representative curves: coexistence, prey-extinction, predator-extinction ---
    def trace_run(pd, pr, seed, fname):
        cfg = SimulationConfig(predator_density=pd, predator_repro_rate=pr, seed=seed, **BASE)
        engine = CellularAutomatonEngine(cfg)
        for _ in range(MAX_GEN):
            engine.step()
            if engine.is_extinct():
                break
        with open(os.path.join(OUT_DIR, fname), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["generation", "prey_count", "predator_count", "extinction_risk"])
            for s in engine.history:
                w.writerow([s.generation, s.prey_count, s.predator_count, s.extinction_risk])
        return engine.generation

    # Pick illustrative parameter points based on the sweep results themselves.
    coexist_pt = min(grid_out.items(), key=lambda kv: kv[1][0])[0]         # lowest extinction prob
    prey_ext_pt = max(
        ((k, v[1]) for k, v in grid_out.items()), key=lambda kv: kv[1]
    )[0]                                                                    # highest prey-extinction prob
    pred_ext_pt = max(
        ((k, v[2]) for k, v in grid_out.items()), key=lambda kv: kv[1]
    )[0]                                                                    # highest predator-extinction prob

    trace_run(coexist_pt[0], coexist_pt[1], 42, "curve_coexistence.csv")
    trace_run(prey_ext_pt[0], prey_ext_pt[1], 7, "curve_prey_extinct.csv")
    trace_run(pred_ext_pt[0], pred_ext_pt[1], 99, "curve_predator_extinct.csv")

    with open(os.path.join(OUT_DIR, "representative_points.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "predator_density", "predator_repro_rate"])
        w.writerow(["coexistence", *coexist_pt])
        w.writerow(["prey_extinct", *prey_ext_pt])
        w.writerow(["predator_extinct", *pred_ext_pt])

    print("Representative points:", coexist_pt, prey_ext_pt, pred_ext_pt)


if __name__ == "__main__":
    main()
