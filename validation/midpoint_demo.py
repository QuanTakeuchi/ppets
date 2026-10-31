"""RU-07 midpoint demo: the strongest implemented path, shown as it is.

Steps (each prints PASS/FAIL or numbers; nothing is mocked):
  1. seeded engine run twice -> identical histories (NFR02)
  2. LIVE mini-sweep through ThresholdAnalyzer (60 runs, ~1-2 min)
  3. Wilson 95% intervals for those cells. NOTE: computed HERE, in the demo;
     production HeatmapData does not carry them yet (FR11 not implemented).
  4. precomputed 600-run baseline sweep (evidence/validation) summarised by
     initial predator density, with n per row.
Writes evidence/midpoint/demo_output.json. Run from the repo root.
"""
import csv, json, math, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ppets.simulation import CellularAutomatonEngine, SimulationConfig
from ppets.analysis.threshold_analyzer import ThresholdAnalyzer, ParamRange

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "evidence", "midpoint"); os.makedirs(OUT, exist_ok=True)

def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)

def history(seed):
    e = CellularAutomatonEngine(SimulationConfig(width=30, height=30, seed=seed))
    for _ in range(60):
        e.step()
    return [(s.prey_count, s.predator_count) for s in e.history]

res = {}
print("1. Determinism (seed 42, 60 generations, run twice)")
a, b = history(42), history(42)
res["determinism_pass"] = a == b
print("   identical histories:", a == b, "| seed 43 differs:", history(43) != a)

print("2. Live mini-sweep via ThresholdAnalyzer")
REPS = 4
az = ThresholdAnalyzer(ParamRange("predator_density", 0.12, 0.28, 0.04),
                       ParamRange("predator_repro_rate", 0.10, 0.30, 0.10),
                       REPS, SimulationConfig(width=30, height=30, prey_density=0.30), 150)
t0 = time.time(); hm = az.run_sweep(); dt = time.time() - t0
print(f"   {len(hm.param_a_values)}x{len(hm.param_b_values)} cells x {REPS} reps = "
      f"{len(hm.param_a_values)*len(hm.param_b_values)*REPS} runs in {dt:.0f}s, complete={hm.complete}")
print("3. Cell estimates with Wilson 95% (demo-side calculation)")
cells = []
print("   density  repro   p_ext  [lo, hi]  n")
for i, a_v in enumerate(hm.param_a_values):
    for j, b_v in enumerate(hm.param_b_values):
        p = hm.extinction_prob[i][j]; k = round(p * REPS); lo, hi = wilson(k, REPS)
        cells.append(dict(density=a_v, repro=b_v, p=p, lo=lo, hi=hi, n=REPS))
        print(f"   {a_v:.2f}    {b_v:.2f}   {p:.2f}   [{lo:.2f}, {hi:.2f}]  {REPS}")
res["live_sweep"] = dict(seconds=round(dt, 1), cells=cells, complete=hm.complete)
print(f"   widest interval: {max(c['hi']-c['lo'] for c in cells):.2f} -> a threshold cannot be placed at n={REPS}")

print("4. Precomputed 600-run baseline sweep (710.9 s serial), by initial predator density")
rows = list(csv.DictReader(open(os.path.join(ROOT, "evidence", "validation", "baseline_sweep_results.csv"))))
by = {}
for r in rows:
    by.setdefault(float(r["predator_density"]), []).append(r["outcome"] != "coexistence")
base = []
for d in sorted(by):
    k, n = sum(by[d]), len(by[d]); lo, hi = wilson(k, n)
    base.append(dict(density=d, p=k / n, lo=lo, hi=hi, n=n))
for r in base[::3]:
    print(f"   density {r['density']:.2f}: p_ext {r['p']:.2f} [{r['lo']:.2f}, {r['hi']:.2f}] n={r['n']}")
res["baseline_by_density"] = base
json.dump(res, open(os.path.join(OUT, "demo_output.json"), "w"), indent=1)
