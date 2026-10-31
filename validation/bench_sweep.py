"""Throughput benchmark — answers "is a UC03 sweep feasible?" (RL-02 / KI-02).

    python validation/bench_sweep.py

Measures, on this machine only:
  1. engine step latency vs grid size, against the NFR01 100 ms budget;
  2. whole-run cost (150 generations) of the sweep workload at 30x30;
  3. serial vs process-pool wall time for an identical 64-run job list
     (the same seed rule as ThresholdAnalyzer, so results are comparable);
  4. a projection table for realistic sweep sizes.

Timings are wall-clock on a single machine/day and are only meaningful as a
ratio or an order of magnitude — see the package's limitations section.

Outputs (evidence/validation/): bench_results.json, bench_step_latency.csv,
bench_parallel.csv.
"""

from __future__ import annotations

import csv
import os
import statistics
import time
from concurrent.futures import ProcessPoolExecutor

from _common import EVIDENCE, provenance, write_json
from _worker import run_replicate

from ppets.simulation import CellularAutomatonEngine, SimulationConfig

GRID_SIZES = (10, 20, 30, 50, 75, 100)
NFR01_BUDGET_MS = 100.0


def step_latency(size: int, steps: int = 30, repeats: int = 3) -> dict:
    per_step = []
    for r in range(repeats):
        e = CellularAutomatonEngine(SimulationConfig(width=size, height=size, seed=100 + r))
        for _ in range(steps):
            t = time.perf_counter()
            s = e.step()
            per_step.append((time.perf_counter() - t) * 1000.0)
            if s.is_extinct():
                break
    per_step.sort()
    return dict(grid=size, samples=len(per_step), median_ms=round(statistics.median(per_step), 2),
                p95_ms=round(per_step[int(0.95 * (len(per_step) - 1))], 2),
                max_ms=round(per_step[-1], 2))


def job_list(width=30, max_gen=150):
    pds = (0.06, 0.14, 0.24, 0.36)
    prs = (0.04, 0.10, 0.16, 0.20)
    return [(width, pd, pr, rep, max_gen) for pd in pds for pr in prs for rep in range(4)]


def main():
    print("1/3 step latency vs grid size", flush=True)
    latency = [step_latency(n) for n in GRID_SIZES]
    for row in latency:
        row["within_nfr01_budget"] = row["p95_ms"] <= NFR01_BUDGET_MS
        print("  ", row, flush=True)
    with open(EVIDENCE / "bench_step_latency.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(latency[0].keys()))
        w.writeheader()
        w.writerows(latency)

    jobs = job_list()
    print(f"2/3 serial baseline: {len(jobs)} runs at 30x30, 150 generations", flush=True)
    t0 = time.perf_counter()
    serial_out = [run_replicate(j) for j in jobs]
    serial_s = time.perf_counter() - t0
    per_run = serial_s / len(jobs)
    print(f"   serial {serial_s:.1f}s  ({per_run:.2f}s/run)", flush=True)

    par_rows = [dict(workers=1, seconds=round(serial_s, 2), speedup=1.0, identical_results=True)]
    max_workers = os.cpu_count() or 2
    for w in sorted({2, 4, 8, max_workers}):
        if w > max_workers:
            continue
        t = time.perf_counter()
        with ProcessPoolExecutor(max_workers=w) as pool:
            out = list(pool.map(run_replicate, jobs, chunksize=2))
        dt = time.perf_counter() - t
        par_rows.append(dict(workers=w, seconds=round(dt, 2), speedup=round(serial_s / dt, 2),
                             identical_results=(out == serial_out)))
        print("  ", par_rows[-1], flush=True)
    with open(EVIDENCE / "bench_parallel.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(par_rows[0].keys()))
        w.writeheader()
        w.writerows(par_rows)

    best = max(par_rows, key=lambda r: r["speedup"])
    # Per-run cost scales ~ grid area; calibrate from measured 30x30 per-run cost.
    projections = []
    for label, cells, reps, grid in (
        ("sweep.py baseline (20x10 cells, 3 reps, 30x30)", 200, 3, 30),
        ("demo sweep (10x10 cells, 10 reps, 30x30)", 100, 10, 30),
        ("uncertainty-aware (10x10 cells, 30 reps, 30x30)", 100, 30, 30),
        ("full-size default grid (10x10 cells, 30 reps, 50x50)", 100, 30, 50),
    ):
        runs = cells * reps
        serial_est = runs * per_run * (grid / 30) ** 2
        projections.append(dict(scenario=label, runs=runs, serial_minutes=round(serial_est / 60, 1),
                                parallel_minutes=round(serial_est / best["speedup"] / 60, 1)))

    write_json(EVIDENCE / "bench_results.json", dict(
        provenance=provenance(), cpu_count=os.cpu_count(), nfr01_budget_ms=NFR01_BUDGET_MS,
        step_latency=latency, serial_seconds_64_runs=round(serial_s, 2),
        seconds_per_run_30x30_150gen=round(per_run, 2), parallel=par_rows,
        best_speedup=best, projections=projections,
        caveat="single machine, single day, wall-clock; per-run cost scaled by grid area for non-30x30 rows",
    ))
    for p in projections:
        print(p)


if __name__ == "__main__":
    main()
