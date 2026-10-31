"""E2 performance evidence (EXPERIMENT_PLAN.md). Run on an otherwise idle machine.

    python validation/hs4_benchmark.py

1. Engine step latency vs grid size (NFR01: 100 ms), with the log-log slope
   of median step time against cell count (expected about 1 for O(L^2)).
2. Worker scaling: one fixed 96-run job at 30x30 with 1..15 workers; the
   results must be identical at every worker count.
3. cProfile of one 150-generation run at 30x30.
4. Projection for a 3,000-run study (RU-07 adjustment A2).
Outputs: benchmark.json, benchmark_profile.txt, figures/fig_e2_benchmark.png.
"""

from __future__ import annotations

import cProfile
import io
import pstats
import statistics
import time

import numpy as np

from hs4_common import EVIDENCE, WORKERS, dump, write_manifest

from ppets.analysis import ParamRange, ThresholdAnalyzer
from ppets.simulation import CellularAutomatonEngine, SimulationConfig

SIZES = (10, 20, 30, 50, 75, 100)
WORKER_COUNTS = sorted({1, 2, 4, 8, 12, WORKERS})


def step_latency():
    rows = []
    for L in SIZES:
        ms = []
        for seed in (1, 2, 3):
            e = CellularAutomatonEngine(SimulationConfig(width=L, height=L, predator_density=0.10, seed=seed))
            for _ in range(30):
                t0 = time.perf_counter()
                e.step()
                ms.append((time.perf_counter() - t0) * 1000)
                if e.is_extinct():
                    break
        ms.sort()
        rows.append(dict(size=L, steps=len(ms), median_ms=statistics.median(ms),
                         p95_ms=ms[int(0.95 * (len(ms) - 1))], max_ms=ms[-1], within_nfr01=ms[int(0.95 * (len(ms) - 1))] <= 100))
    cells = np.log([r["size"] ** 2 for r in rows])
    slope = float(np.polyfit(cells, np.log([r["median_ms"] for r in rows]), 1)[0])
    return rows, slope


def scaling():
    def job(w):
        return ThresholdAnalyzer(ParamRange("predator_density", 0.20, 0.34, 0.02),
                                 ParamRange("predator_repro_rate", 0.15, 0.15, 0.01), replicates=12,
                                 base_config=SimulationConfig(width=30, height=30, seed=4061), workers=w)
    rows, ref = [], None
    for w in WORKER_COUNTS:
        t0 = time.perf_counter()
        res = job(w).run_sweep()
        wall = time.perf_counter() - t0
        sig = [(r.seed, r.extinct, r.extinction_generation) for r in res.runs]
        ref = ref or sig
        rows.append(dict(workers=w, runs=len(res.runs), wall_seconds=round(wall, 2),
                         identical_to_serial=sig == ref))
    base = rows[0]["wall_seconds"]
    for r in rows:
        r["speedup"] = round(base / r["wall_seconds"], 2)
        r["efficiency"] = round(r["speedup"] / r["workers"], 2)
    return rows


def pool_startup():
    """Cost of starting the worker pool, measured as a 1-run sweep (HS4-06)."""
    out = {}
    for w in (1, WORKERS):
        times = []
        for _ in range(3):
            ta = ThresholdAnalyzer(ParamRange("predator_density", 0.10, 0.10, 0.01),
                                   ParamRange("predator_repro_rate", 0.15, 0.15, 0.01), replicates=1,
                                   base_config=SimulationConfig(width=10, height=10, seed=1),
                                   max_generations=5, workers=w)
            t0 = time.perf_counter()
            ta.run_sweep()
            times.append(time.perf_counter() - t0)
        out[f"workers_{w}_seconds_median"] = round(statistics.median(times), 3)
    return out


def profile():
    e = CellularAutomatonEngine(SimulationConfig(width=30, height=30, predator_density=0.10, seed=7))
    pr = cProfile.Profile()
    pr.enable()
    for _ in range(150):
        e.step()
    pr.disable()
    buf = io.StringIO()
    pstats.Stats(pr, stream=buf).sort_stats("tottime").print_stats(12)
    return buf.getvalue(), e.generation


def main():
    t0 = time.perf_counter()
    lat, slope = step_latency()
    print("latency done; slope", round(slope, 2))
    sc = scaling()
    print("scaling done:", [(r["workers"], r["wall_seconds"]) for r in sc])
    startup = pool_startup()
    print("pool startup:", startup)
    prof, gens = profile()
    (EVIDENCE / "benchmark_profile.txt").write_text(f"One 30x30 run, {gens} generations, sorted by own time\n\n" + prof,
                                                   encoding="utf-8")
    best = min(sc, key=lambda r: r["wall_seconds"])
    per_run = best["wall_seconds"] / best["runs"]
    proj = dict(runs=3000, workers=best["workers"], seconds_per_run=round(per_run, 3),
                projected_minutes=round(3000 * per_run / 60, 1),
                serial_projected_minutes=round(3000 * sc[0]["wall_seconds"] / sc[0]["runs"] / 60, 1),
                pass_=3000 * per_run / 60 <= 15,
                note="Job sits in the transition band (densities 0.20-0.34), where run lengths vary most.")
    res = dict(step_latency=lat, step_time_vs_cells_loglog_slope=slope, scaling=sc, projection_3000=proj,
               pool_startup=startup)
    out = EVIDENCE / "benchmark.json"
    dump(out, res)
    write_manifest(out, script="validation/hs4_benchmark.py", wall_seconds=time.perf_counter() - t0,
                   params={"sizes": SIZES, "worker_counts": WORKER_COUNTS, "scaling_job": "8 densities x 12 reps, 30x30, seed 4061"})
    fig(res)
    print("projection:", proj)


def fig(res):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    f, (a, b) = plt.subplots(1, 2, figsize=(10, 3.8))
    lat = res["step_latency"]
    a.plot([r["size"] for r in lat], [r["median_ms"] for r in lat], "o-", label="median")
    a.plot([r["size"] for r in lat], [r["p95_ms"] for r in lat], "s--", label="p95")
    a.axhline(100, color="#c8553d", ls=":", label="NFR01 budget 100 ms")
    a.set_xscale("log"); a.set_yscale("log")
    a.set_xlabel("grid side L"); a.set_ylabel("ms per generation")
    a.set_title(f"Step latency (slope vs L² = {res['step_time_vs_cells_loglog_slope']:.2f})")
    a.legend(fontsize=8)
    sc = res["scaling"]
    b.plot([r["workers"] for r in sc], [r["speedup"] for r in sc], "o-", label="measured")
    b.plot([1, sc[-1]["workers"]], [1, sc[-1]["workers"]], ":", color="grey", label="ideal")
    b.set_xlabel("worker processes"); b.set_ylabel("speed-up vs 1 worker")
    b.set_title("Sweep scaling (96 runs, 30×30)")
    b.legend(fontsize=8)
    f.tight_layout()
    f.savefig(EVIDENCE / "figures" / "fig_e2_benchmark.png", dpi=150)


if __name__ == "__main__":
    main()
