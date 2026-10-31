"""Pilot replicate study — how trustworthy is a 3-replicate heatmap cell?

    python validation/pilot_study.py [--replicates 100] [--workers 14]

Reads the 3-replicate baseline matrix produced by experiments/sweep.py
(experiments/output/heatmap_matrix.csv), picks cells that the 3-replicate run
placed at p̂ = 0, 1/3, 2/3 and 1, then re-runs each cell with many more seeded
replicates (to a 300-generation horizon) so we can quantify:

  * the sampling uncertainty of a 3-replicate cell (Wilson 95% CI at n=3 vs n=N),
  * horizon sensitivity: how extinction probability changes with run length
    (the 150-generation "coexistence" label is right-censored),
  * whether the placeholder PopulationStats.extinction_risk heuristic, read
    at generation 20, actually separates eventual extinctions from survivors.

Seeds follow the same hash((pd, pr, rep)) rule as ThresholdAnalyzer and
sweep.py, so replicates 0..2 here are *exactly* the runs behind the 3-replicate
estimate: the comparison is like-for-like, not a fresh draw.

Outputs (evidence/validation/): pilot_replicates.csv, pilot_summary.csv,
pilot_summary.json.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor

from _common import EVIDENCE, REPO, provenance, wilson_interval, write_json

from ppets.simulation import CellularAutomatonEngine, SimulationConfig

GRID = 30            # matches experiments/sweep.py BASE
HORIZONS = (50, 100, 150, 300)
RISK_AT = 20


def run_one(job):
    pd, pr, rep = job
    seed = hash((pd, pr, rep)) % (2**31)
    cfg = SimulationConfig(
        width=GRID, height=GRID, prey_density=0.30, predator_density=pd,
        prey_repro_rate=0.20, predator_repro_rate=pr, prey_death_threshold=3,
        starvation_rate=3, seed=seed,
    )
    eng = CellularAutomatonEngine(cfg)
    risk20 = None
    ext_gen, outcome = None, "survived"
    for _ in range(max(HORIZONS)):
        s = eng.step()
        if s.generation == RISK_AT:
            risk20 = s.extinction_risk
        if s.is_extinct():
            ext_gen = s.generation
            outcome = "prey_extinct" if s.prey_count == 0 else "predator_extinct"
            break
    return dict(predator_density=pd, predator_repro_rate=pr, replicate=rep, seed=seed,
                outcome=outcome, extinction_generation=ext_gen, risk_at_20=risk20)


def pick_cells(matrix_csv):
    rows = []
    with open(matrix_csv, newline="") as f:
        for r in csv.DictReader(f):
            rows.append((float(r["predator_density"]), float(r["predator_repro_rate"]),
                         float(r["extinction_probability"])))
    picked = []
    for target in (0.0, 1 / 3, 2 / 3, 1.0):
        matches = [r for r in rows if abs(r[2] - target) < 1e-6]
        matches.sort(key=lambda r: (r[0], r[1]))
        if not matches:
            continue
        # take two spread-out representatives (first and middle) for each level
        chosen = {matches[0], matches[len(matches) // 2]}
        picked += [(pd, pr, target) for pd, pr, _ in sorted(chosen)]
    return picked


def auc(pos, neg):
    """P(score_pos > score_neg) + 0.5 P(tie) — Mann-Whitney AUC."""
    if not pos or not neg:
        return None
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--replicates", type=int, default=100)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument("--matrix", default=str(REPO / "experiments" / "output" / "heatmap_matrix.csv"))
    args = ap.parse_args()

    cells = pick_cells(args.matrix)
    jobs = [(pd, pr, rep) for pd, pr, _ in cells for rep in range(args.replicates)]
    print(f"{len(cells)} cells x {args.replicates} replicates = {len(jobs)} runs on {args.workers} workers", flush=True)

    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(run_one, jobs, chunksize=4))
    wall = time.perf_counter() - t0
    print(f"done in {wall:.1f}s", flush=True)

    fields = list(results[0].keys())
    with open(EVIDENCE / "pilot_replicates.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(results)

    summary = []
    for pd, pr, est3 in cells:
        reps = [r for r in results if r["predator_density"] == pd and r["predator_repro_rate"] == pr]
        n = len(reps)
        entry = dict(predator_density=pd, predator_repro_rate=pr, n=n, p_hat_n3_from_baseline=round(est3, 4))
        first3 = [r for r in reps if r["replicate"] < 3]
        k3 = sum(r["extinction_generation"] is not None and r["extinction_generation"] <= 150 for r in first3)
        lo3, hi3 = wilson_interval(k3, 3)
        entry.update(k3=k3, ci3_low=round(lo3, 3), ci3_high=round(hi3, 3))
        for h in HORIZONS:
            k = sum(r["extinction_generation"] is not None and r["extinction_generation"] <= h for r in reps)
            lo, hi = wilson_interval(k, n)
            entry[f"p_by_gen{h}"] = round(k / n, 4)
            if h == 150:
                entry.update(k150=k, ci_low=round(lo, 3), ci_high=round(hi, 3))
        entry["prey_extinct_by_300"] = sum(r["outcome"] == "prey_extinct" for r in reps)
        entry["predator_extinct_by_300"] = sum(r["outcome"] == "predator_extinct" for r in reps)
        ext_gens = sorted(r["extinction_generation"] for r in reps if r["extinction_generation"] is not None)
        entry["median_extinction_generation"] = ext_gens[len(ext_gens) // 2] if ext_gens else None
        summary.append(entry)

    with open(EVIDENCE / "pilot_summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)

    # Heuristic skill: among runs still alive at gen 20, does risk@20 rank eventual
    # extinction-by-150 above survival?
    alive20 = [r for r in results if r["risk_at_20"] is not None]
    pos = [r["risk_at_20"] for r in alive20
           if r["extinction_generation"] is not None and r["extinction_generation"] <= 150]
    neg = [r["risk_at_20"] for r in alive20
           if not (r["extinction_generation"] is not None and r["extinction_generation"] <= 150)]
    payload = dict(
        provenance=provenance(), replicates_per_cell=args.replicates, grid=GRID, horizons=HORIZONS,
        wall_seconds=round(wall, 1), workers=args.workers, total_runs=len(results), cells=summary,
        extinction_risk_heuristic=dict(
            evaluated_at_generation=RISK_AT, runs_alive_at_20=len(alive20),
            eventual_extinct=len(pos), eventual_survived=len(neg),
            auc=None if auc(pos, neg) is None else round(auc(pos, neg), 3),
            mean_risk_extinct=round(sum(pos) / len(pos), 3) if pos else None,
            mean_risk_survived=round(sum(neg) / len(neg), 3) if neg else None,
        ),
    )
    write_json(EVIDENCE / "pilot_summary.json", payload)
    for e in summary:
        print(f"pd={e['predator_density']:.2f} pr={e['predator_repro_rate']:.2f}  n3={e['p_hat_n3_from_baseline']:.2f} "
              f"CI3=[{e['ci3_low']},{e['ci3_high']}]  p150={e['p_by_gen150']:.2f} CI=[{e['ci_low']},{e['ci_high']}]  "
              f"gen50/100/150/300={e['p_by_gen50']}/{e['p_by_gen100']}/{e['p_by_gen150']}/{e['p_by_gen300']}")
    print("risk heuristic:", payload["extinction_risk_heuristic"])


if __name__ == "__main__":
    main()
