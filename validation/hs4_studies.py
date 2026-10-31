"""Hard Stop 4 sweeps (E3-E8 in evidence/hs4/EXPERIMENT_PLAN.md).

    python validation/hs4_studies.py            # all studies (about 30 min, 15 workers)
    python validation/hs4_studies.py L30_s4001  # one study by name

Each study runs ThresholdAnalyzer over predator density (one value on the
second axis) and writes evidence/hs4/studies/<name>.runs.csv plus a manifest.
Studies whose CSV already exists are skipped, so an interrupted run resumes.
"""

from __future__ import annotations

import sys
import time

from hs4_common import DENSITY, EVIDENCE, MAX_GEN, PROTOCOL, REPLICATES, WORKERS, write_manifest, write_runs_csv

from ppets.analysis import ParamRange, ThresholdAnalyzer
from ppets.simulation import SimulationConfig

OUT = EVIDENCE / "studies"
OUT.mkdir(exist_ok=True)


def study(name, seed, *, size=30, repro=0.15, max_gen=MAX_GEN, density=DENSITY,
          b_axis=None, reps=REPLICATES, experiment=""):
    return dict(name=name, seed=seed, size=size, repro=repro, max_gen=max_gen,
                density=density, b_axis=b_axis, reps=reps, experiment=experiment)


STUDIES = (
    [study(f"L30_s{s}", s, experiment="E3/E4") for s in range(4001, 4006)]
    + [study(f"L{L}_s{s}", s, size=L, experiment="E5") for L, s in ((20, 4011), (40, 4012), (50, 4013))]
    + [study(f"r{int(r*100):02d}_s{s}", s, repro=r, experiment="E6") for r, s in ((0.05, 4021), (0.30, 4022))]
    + [study("H300_s4031", 4031, max_gen=300, experiment="E7")]
    # E8: the HS3 design (experiments/sweep.py) under the new seeding.
    + [study("hs3design_s4041", 4041, density=dict(start=0.02, stop=0.40, step=0.02),
             b_axis=dict(start=0.02, stop=0.20, step=0.02), reps=3, experiment="E8")]
)


def run(s: dict) -> None:
    out = OUT / f"{s['name']}.runs.csv"
    if out.exists():
        print(f"skip {s['name']} (exists)")
        return
    base = SimulationConfig(**{**PROTOCOL, "width": s["size"], "height": s["size"],
                               "predator_repro_rate": s["repro"], "seed": s["seed"]})
    b = s["b_axis"] or dict(start=s["repro"], stop=s["repro"], step=0.01)
    ta = ThresholdAnalyzer(
        param_a=ParamRange("predator_density", **s["density"]),
        param_b=ParamRange("predator_repro_rate", **b),
        replicates=s["reps"], base_config=base, max_generations=s["max_gen"], workers=WORKERS,
    )
    t0 = time.perf_counter()
    res = ta.run_sweep()
    wall = time.perf_counter() - t0
    assert res.complete
    write_runs_csv(out, res.runs)
    write_manifest(out, script="validation/hs4_studies.py", wall_seconds=wall,
                   params={**s, "base_config": base.to_dict(), "workers": WORKERS,
                           "runs": len(res.runs)})
    print(f"{s['name']}: {len(res.runs)} runs in {wall:.0f}s", flush=True)


if __name__ == "__main__":
    names = set(sys.argv[1:])
    for s in STUDIES:
        if not names or s["name"] in names:
            run(s)
