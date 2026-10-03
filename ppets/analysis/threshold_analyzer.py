"""
ThresholdAnalyzer / HeatmapData — LLD §4.1 (Module 3: Analysis)

Implementation-baseline skeleton only (Hard Stop 3). The LLD's runSweep()
pseudocode parallelizes jobs across a multiprocessing.Pool so the CPU-bound
engine loop isn't serialised behind the GIL; that optimization is deferred
to a later sprint (see KNOWN_ISSUES.md) until the sequential path below is
correctness-tested. Module 3 was flagged "not yet built" in the HS2 Design
Review (ppets/README.md); this is the first implementation pass.

Each heatmap cell is itself the uncertainty-aware part of the "uncertainty-
aware threshold study": it's a Monte-Carlo estimate of extinction
probability over `replicates` seeded runs, not a single deterministic
outcome, so its sampling noise is a function of `replicates`.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, Optional

from ..simulation import CellularAutomatonEngine, SimulationConfig

# LLD §4.1: "if len(jobs) * replicates > 10000: emitWarning(...)"
SWEEP_WARNING_THRESHOLD = 10_000


@dataclass(frozen=True)
class ParamRange:
    """One sweep axis: an inclusive [start, stop] range stepped by `step`."""

    name: str
    start: float
    stop: float
    step: float

    def values(self) -> list[float]:
        if self.step <= 0:
            raise ValueError(f"ParamRange.step must be > 0, got {self.step}")
        if self.stop < self.start:
            raise ValueError(f"ParamRange.stop ({self.stop}) must be >= start ({self.start})")
        n_steps = int(round((self.stop - self.start) / self.step))
        return [round(self.start + i * self.step, 10) for i in range(n_steps + 1)]


@dataclass
class HeatmapData:
    """LLD §4.1: "2D float matrix of extinction probability in [0,1] plus
    axis metadata." Extended here with the per-species breakdown
    `_experiment_sweep.py` (the standalone GRAD 695 report script) already
    computes by hand, so ThresholdAnalyzer can eventually replace it."""

    extinction_prob: list[list[float]]
    prey_extinction_prob: list[list[float]]
    predator_extinction_prob: list[list[float]]
    param_a_name: str
    param_b_name: str
    param_a_values: list[float]
    param_b_values: list[float]
    complete: bool = True  # False when run_sweep() was cancelled mid-sweep (UC03 alt. flow)


class ThresholdAnalyzer:
    """LLD §4.1. Members here match the LLD class diagram's member table:
    paramRanges (param_a/param_b), replicates, results, run_sweep(),
    get_heatmap()."""

    def __init__(
        self,
        param_a: ParamRange,
        param_b: ParamRange,
        replicates: int,
        base_config: SimulationConfig,
        max_generations: int = 150,
        on_warning: Optional[Callable[[str], None]] = None,
    ) -> None:
        if replicates < 1:
            raise ValueError(f"replicates must be >= 1, got {replicates}")
        if max_generations < 1:
            raise ValueError(f"max_generations must be >= 1, got {max_generations}")

        self.param_a = param_a
        self.param_b = param_b
        self.replicates = replicates
        self.base_config = base_config
        self.max_generations = max_generations
        self.results: Optional[HeatmapData] = None
        self._cancelled = False

        n_jobs = len(param_a.values()) * len(param_b.values()) * replicates
        if n_jobs > SWEEP_WARNING_THRESHOLD and on_warning is not None:
            on_warning(
                f"Sweep may take a long time: {n_jobs} runs "
                f"({len(param_a.values())}x{len(param_b.values())} cells "
                f"x {replicates} replicates)."
            )

    def cancel(self) -> None:
        """UC03 Alternate Flow: user cancels mid-sweep. get_heatmap() then
        returns a partial HeatmapData (complete=False) covering only the
        cells finished before cancellation."""
        self._cancelled = True

    def run_sweep(self, on_progress: Optional[Callable[[float], None]] = None) -> HeatmapData:
        a_values = self.param_a.values()
        b_values = self.param_b.values()
        total_cells = len(a_values) * len(b_values)

        ext = [[0.0] * len(b_values) for _ in a_values]
        prey_ext = [[0.0] * len(b_values) for _ in a_values]
        pred_ext = [[0.0] * len(b_values) for _ in a_values]

        completed = 0
        complete = True
        for i, a_val in enumerate(a_values):
            if self._cancelled:
                complete = False
                break
            for j, b_val in enumerate(b_values):
                if self._cancelled:
                    complete = False
                    break
                ext[i][j], prey_ext[i][j], pred_ext[i][j] = self._run_cell(a_val, b_val)
                completed += 1
                if on_progress is not None:
                    on_progress(completed / total_cells)

        self.results = HeatmapData(
            extinction_prob=ext,
            prey_extinction_prob=prey_ext,
            predator_extinction_prob=pred_ext,
            param_a_name=self.param_a.name,
            param_b_name=self.param_b.name,
            param_a_values=a_values,
            param_b_values=b_values,
            complete=complete,
        )
        return self.results

    def get_heatmap(self) -> Optional[HeatmapData]:
        return self.results

    def _run_cell(self, a_val: float, b_val: float) -> tuple[float, float, float]:
        n_extinct = n_prey_extinct = n_pred_extinct = 0
        overrides = {self.param_a.name: a_val, self.param_b.name: b_val}
        for rep in range(self.replicates):
            seed = hash((a_val, b_val, rep)) % (2**31)
            cfg = replace(self.base_config, seed=seed, **overrides)
            engine = CellularAutomatonEngine(cfg)
            for _ in range(self.max_generations):
                stats = engine.step()
                if stats.is_extinct():
                    break
            final = engine.history[-1]
            if final.is_extinct():
                n_extinct += 1
                if final.prey_count == 0:
                    n_prey_extinct += 1
                if final.predator_count == 0:
                    n_pred_extinct += 1
        return (
            n_extinct / self.replicates,
            n_prey_extinct / self.replicates,
            n_pred_extinct / self.replicates,
        )
