"""
CellularAutomatonEngine — LLD §5 (step() Algorithm)

Order of operations per generation, exactly as specified:
  1. Shuffle cell evaluation order (avoid directional bias).
  2. For each cell, apply state-transition rules into a write buffer.
  3. Swap read/write buffers.
  4. Compute PopulationStats from the new grid state.
  5. Increment generation counter.

Extinction is flagged when prey_count == 0 or predator_count == 0
after a step (LLD §5).
"""

from __future__ import annotations

import numpy as np

from .cell import Cell, CellState, PredatorCell, PreyCell
from .config import SimulationConfig
from .grid import Grid
from .stats import PopulationStats


class CellularAutomatonEngine:
    # Registered per-species rule handlers. New species types extend
    # this dict rather than the engine itself (NFR06 extensibility).
    RULES: dict[CellState, Cell] = {
        CellState.PREY: PreyCell(),
        CellState.PREDATOR: PredatorCell(),
    }

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.grid = Grid(config)
        self.grid.randomize()
        self.generation = 0
        self.history: list[PopulationStats] = []
        self.history.append(self._collect_stats())

    def step(self) -> PopulationStats:
        write = self.grid.new_write_buffer()

        ys, xs = np.nonzero(self.grid.state != CellState.EMPTY)
        order = self.config.rng.permutation(len(xs))

        for i in order:
            x, y = int(xs[i]), int(ys[i])
            cell_state = CellState(self.grid.state[y, x])
            rule = self.RULES.get(cell_state)
            if rule is not None:
                rule.update(x, y, self.grid, write)

        self.grid.swap_from(write)
        self.generation += 1

        stats = self._collect_stats()
        self.history.append(stats)
        return stats

    def is_extinct(self) -> bool:
        return self.history[-1].is_extinct()

    def _collect_stats(self) -> PopulationStats:
        prey, predator = self.grid.counts()
        return PopulationStats(
            generation=self.generation,
            prey_count=prey,
            predator_count=predator,
        )
