"""Subprocess/pool worker used by the validation scripts.

Kept in its own importable module so multiprocessing (spawn on Windows) can
pickle the target functions, and so cross-process determinism checks can run
the exact same code in a fresh interpreter with a chosen PYTHONHASHSEED.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from ppets.simulation import CellularAutomatonEngine, SimulationConfig  # noqa: E402


def run_replicate(job: tuple) -> tuple:
    """One seeded engine run. Same seed rule as ThresholdAnalyzer._run_cell and
    experiments/sweep.py: seed = hash((predator_density, predator_repro_rate, rep)).

    job = (width, predator_density, predator_repro_rate, rep, max_generations)
    returns (pd, pr, rep, outcome, extinction_generation, generations_run)
    """
    width, pd, pr, rep, max_gen = job
    seed = hash((pd, pr, rep)) % (2**31)
    cfg = SimulationConfig(
        width=width, height=width, prey_density=0.30, predator_density=pd,
        prey_repro_rate=0.20, predator_repro_rate=pr,
        prey_death_threshold=3, starvation_rate=3, seed=seed,
    )
    engine = CellularAutomatonEngine(cfg)
    outcome, ext_gen = "survived", None
    for _ in range(max_gen):
        stats = engine.step()
        if stats.is_extinct():
            ext_gen = stats.generation
            outcome = "prey_extinct" if stats.prey_count == 0 else "predator_extinct"
            break
    return (pd, pr, rep, outcome, ext_gen, engine.generation)


def determinism_fingerprint() -> str:
    """Fingerprint of one engine history + one tiny analyzer sweep, printed so a
    parent process can compare it across interpreters / PYTHONHASHSEED values."""
    from ppets.analysis import ParamRange, ThresholdAnalyzer

    engine = CellularAutomatonEngine(SimulationConfig(width=30, height=30, seed=42))
    for _ in range(60):
        engine.step()
    hist = [(s.generation, s.prey_count, s.predator_count) for s in engine.history]

    ta = ThresholdAnalyzer(
        ParamRange("predator_density", 0.10, 0.20, 0.10),
        ParamRange("predator_repro_rate", 0.10, 0.20, 0.10),
        replicates=2,
        # A fixed master seed: since HS4 an unseeded sweep draws fresh entropy,
        # which made this fingerprint differ between interpreters (HS5 FP-07).
        base_config=SimulationConfig(width=15, height=15, seed=2026),
        max_generations=40,
    )
    res = ta.run_sweep()
    payload = {"hist": hist, "sweep": res.extinction_prob,
               "seeds": [hash((0.1, 0.1, r)) % (2**31) for r in range(3)]}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "fingerprint":
        print(determinism_fingerprint())
