"""HS6 demo (DEMO_SCRIPT.md steps 3 and 4), about 10 seconds.

    python validation/hs6_demo.py

Step 3: re-estimate d* at 30x30 from the 2,700 recorded runs with the
production code, and compare with the published values.
Step 4: take one run that survived on the spatial grid (study L30_s4001,
density 0.20), rerun it from the same seed, then rerun the same starting grid
with well-mixed partner choice.
"""

from __future__ import annotations

import hs4_common
from hs4_common import PROTOCOL, read_runs_csv

from ppets.analysis import estimate_threshold
from ppets.simulation import CellularAutomatonEngine, SimulationConfig

STUDIES = hs4_common.EVIDENCE / "studies"


def step3() -> None:
    rows = [r for s in range(4001, 4006) for r in read_runs_csv(STUDIES / f"L30_s{s}.runs.csv")]
    est = estimate_threshold([r["a_value"] for r in rows], [int(r["extinct"]) for r in rows], seed=1030)
    print(f"Step 3: {len(rows):,} recorded runs at 30x30")
    for m, label in (("model_free", "model-free (headline)"), ("loglog", "log-log"), ("logit", "logistic (HS4)")):
        e = est[m]
        print(f"  {label:<22} d* = {e.d_star:.3f}  95% CI [{e.ci[0]:.3f}, {e.ci[1]:.3f}]")
    print("  published (report Table 19): 0.236 [0.231, 0.246]; 0.241 [0.236, 0.245]; 0.250 [0.246, 0.254]")


def run(seed: int, density: float, mixing: str):
    cfg = SimulationConfig(**{**PROTOCOL, "predator_density": density, "seed": seed, "mixing": mixing})
    eng = CellularAutomatonEngine(cfg)
    start = eng.history[0]
    s = start
    while s.generation < 150 and not s.is_extinct():
        s = eng.step()
    if s.prey_count == 0:
        outcome = f"prey wiped out at generation {s.generation}"
    elif s.predator_count == 0:
        outcome = f"predators died out at generation {s.generation}"
    else:
        outcome = f"both species alive at generation 150 (prey {s.prey_count}, predators {s.predator_count})"
    return start, outcome


def step4() -> None:
    row = next(r for r in read_runs_csv(STUDIES / "L30_s4001.runs.csv")
               if abs(r["a_value"] - 0.20) < 1e-9 and not r["extinct"])
    print(f"\nStep 4: study L30_s4001, density 0.20, replicate {row['replicate']}, seed {row['seed']}")
    for mixing in ("spatial", "well_mixed"):
        start, outcome = run(int(row["seed"]), 0.20, mixing)
        print(f"  {mixing:<10} start: prey {start.prey_count}, predators {start.predator_count} -> {outcome}")
    print("  Same starting grid; only partner choice differs (report Section 6.8).")


if __name__ == "__main__":
    step3()
    step4()
