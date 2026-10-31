"""RU-09 sweeps (Q1 and Q4 in evidence/ru09/ANALYSIS_PLAN.md).

    python validation/ru09_studies.py             # all studies (about 40 min, 15 workers)
    python validation/ru09_studies.py L75_s4014   # one study by name
    python validation/ru09_studies.py trajectory  # the Q4 trajectory study only

Same protocol as hs4_studies.py; outputs go to evidence/ru09/studies/. Studies
whose CSV already exists are skipped, so an interrupted run resumes.
"""

from __future__ import annotations

import csv
import hashlib
import multiprocessing as mp
import sys
import time

import numpy as np

import hs4_common
from _common import git
from hs4_common import DENSITY, MAX_GEN, PROTOCOL, REPLICATES, WORKERS, write_manifest, write_runs_csv

from ppets.analysis import ParamRange, ThresholdAnalyzer
from ppets.simulation import CellularAutomatonEngine, SimulationConfig

EVIDENCE = hs4_common.REPO / "evidence" / "ru09"
OUT = EVIDENCE / "studies"
OUT.mkdir(parents=True, exist_ok=True)
FROZEN_FINGERPRINT = "0c61dd14fdaad6a8"

STUDIES = (("L50_s4016", 50, 4016), ("L75_s4014", 75, 4014), ("L75_s4017", 75, 4017), ("L100_s4015", 100, 4015))

TRAJECTORY_SIZES = (20, 30, 50, 75)
TRAJECTORY_DENSITIES = (0.20, 0.25, 0.30)
TRAJECTORY_REPS = 30
TRAJECTORY_GENS = 70
TRAJECTORY_MASTER = 4050


def frozen_fingerprint() -> str:
    """The manifests' ppets/ fingerprint, computed against hs3-baseline so it gives
    the same value before and after the HS4 changes are committed."""
    base = "19b0b7e"
    changed = git("diff", base, "--name-only", "--diff-filter=d", "--", "ppets").splitlines()
    added = set(git("diff", base, "--name-only", "--diff-filter=A", "--", "ppets").splitlines())
    added.update(git("ls-files", "--others", "--exclude-standard", "ppets").splitlines())
    tracked = [p for p in changed if p not in added]
    h = hashlib.sha256(git("diff", base, "--", *tracked).encode() if tracked else b"")
    for rel in sorted(added):
        p = hs4_common.REPO / rel
        if p.is_file():
            h.update(rel.encode())
            # The manifests hashed LF text; a Windows checkout may give CRLF.
            h.update(p.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:16]


def run_study(name: str, size: int, seed: int, density: dict = DENSITY) -> None:
    out = OUT / f"{name}.runs.csv"
    if out.exists():
        print(f"skip {name} (exists)", flush=True)
        return
    base = SimulationConfig(**{**PROTOCOL, "width": size, "height": size, "seed": seed})
    repro = PROTOCOL["predator_repro_rate"]
    ta = ThresholdAnalyzer(
        param_a=ParamRange("predator_density", **density),
        param_b=ParamRange("predator_repro_rate", start=repro, stop=repro, step=0.01),
        replicates=REPLICATES, base_config=base, max_generations=MAX_GEN, workers=WORKERS,
    )
    t0 = time.perf_counter()
    res = ta.run_sweep()
    wall = time.perf_counter() - t0
    assert res.complete
    write_runs_csv(out, res.runs)
    write_manifest(out, script="validation/ru09_studies.py", wall_seconds=wall,
                   params={"name": name, "seed": seed, "size": size, "repro": repro, "max_gen": MAX_GEN,
                           "density": density, "reps": REPLICATES, "base_config": base.to_dict(),
                           "workers": WORKERS, "runs": len(res.runs), "question": "Q7" if size == 150 else "Q1"})
    print(f"{name}: {len(res.runs)} runs in {wall:.0f}s", flush=True)


def _trajectory_run(job):
    i, j, rep, size, density = job
    seed = int(np.random.SeedSequence(entropy=TRAJECTORY_MASTER, spawn_key=(i, j, rep)).generate_state(1)[0])
    cfg = {**PROTOCOL, "width": size, "height": size, "predator_density": density, "seed": seed}
    engine = CellularAutomatonEngine(SimulationConfig.from_dict(cfg))
    s = engine.history[0]
    min_pred, min_prey, gen_min_pred = s.predator_count, s.prey_count, 0
    while s.generation < TRAJECTORY_GENS and not s.is_extinct():
        s = engine.step()
        if s.predator_count < min_pred:
            min_pred, gen_min_pred = s.predator_count, s.generation
        min_prey = min(min_prey, s.prey_count)
    return dict(size=size, density=density, replicate=rep, seed=seed, min_predators=min_pred,
                min_prey=min_prey, generation_of_min_predators=gen_min_pred, extinct=s.is_extinct(),
                prey_extinct=s.prey_count == 0, predator_extinct=s.predator_count == 0,
                generation_end=s.generation)


def run_trajectory() -> None:
    out = OUT / "trajectory_s4050.csv"
    if out.exists():
        print("skip trajectory (exists)", flush=True)
        return
    jobs = [(i, j, rep, size, d) for i, size in enumerate(TRAJECTORY_SIZES)
            for j, d in enumerate(TRAJECTORY_DENSITIES) for rep in range(TRAJECTORY_REPS)]
    t0 = time.perf_counter()
    with mp.get_context("spawn").Pool(WORKERS) as pool:
        rows = pool.map(_trajectory_run, jobs, chunksize=4)
    wall = time.perf_counter() - t0
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    write_manifest(out, script="validation/ru09_studies.py", wall_seconds=wall,
                   params={"master_seed": TRAJECTORY_MASTER, "sizes": TRAJECTORY_SIZES,
                           "densities": TRAJECTORY_DENSITIES, "reps": TRAJECTORY_REPS,
                           "generations": TRAJECTORY_GENS, "protocol": PROTOCOL,
                           "workers": WORKERS, "runs": len(rows), "question": "Q4"})
    print(f"trajectory: {len(rows)} runs in {wall:.0f}s", flush=True)


if __name__ == "__main__":
    current = frozen_fingerprint()
    if "--check-fingerprint" in sys.argv:
        print(current, "matches" if current == FROZEN_FINGERPRINT else f"differs from {FROZEN_FINGERPRINT}")
        sys.exit(current != FROZEN_FINGERPRINT)
    if current != FROZEN_FINGERPRINT:
        sys.exit(f"ppets/ fingerprint {current} != frozen {FROZEN_FINGERPRINT}; refusing to run")
    names = set(sys.argv[1:])
    if not names or "trajectory" in names:
        run_trajectory()
    for name, size, seed in STUDIES:
        if not names or name in names:
            run_study(name, size, seed)
    if not names or "L150_s4018" in names:
        run_study("L150_s4018", 150, 4018, density=dict(start=0.30, stop=0.50, step=0.02))
