"""
Cell hierarchy — LLD §4 (Cell State Transition Logic) + class diagram
(Cell / PreyCell / PredatorCell).

DEVIATION FLAG (see README "Design Deviations" #1):
The class diagram models Cell/PreyCell/PredatorCell as stateful objects
with their own energy/hunger fields. Instantiating one Python object per
grid cell every generation would be memory- and CPU-heavy for a grid
that's meant to scale (NFR01). Instead:

  - Grid stores primitive state codes in a NumPy array (int8).
  - A parallel NumPy array on Grid stores predator hunger counters.
  - These classes hold the *rule logic* (update/reproduce/die), operating
    on a given (x, y) coordinate against the Grid/read-write buffers,
    rather than each wrapping a persistent per-cell object.

This keeps the extensibility point from NFR06 (new species = new Cell
subclass registered in CellularAutomatonEngine.RULES) without paying for
millions of live Python objects on a large grid.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import IntEnum


class CellState(IntEnum):
    EMPTY = 0
    PREY = 1
    PREDATOR = 2


class Cell(ABC):
    """Abstract base — encapsulates one species' per-step rule."""

    state: CellState

    @abstractmethod
    def update(self, x: int, y: int, grid: "Grid", write: "np.ndarray") -> None:
        """
        Apply this cell's transition rule for position (x, y), reading
        from `grid` (current generation) and writing the outcome into
        `write` (next-generation buffer). Must not mutate `grid` itself —
        that's what makes double-buffering safe (LLD §3/§5).
        """
        raise NotImplementedError


class PreyCell(Cell):
    state = CellState.PREY

    def update(self, x, y, grid, write) -> None:
        # A predator elsewhere in this generation may have already
        # claimed this cell as its meal (see PredatorCell.update /
        # Grid.eaten). That must win regardless of processing order,
        # otherwise a prey cell could "resurrect" after being eaten
        # depending on shuffle order.
        if grid.eaten[y, x]:
            write[y, x] = CellState.EMPTY
            return

        predator_neighbors = grid.count_neighbors(x, y, CellState.PREDATOR)

        if predator_neighbors >= grid.config.prey_death_threshold:
            write[y, x] = CellState.EMPTY
            return

        write[y, x] = CellState.PREY

        # Attempt reproduction into a random empty neighbor.
        if grid.config.rng.random() < grid.config.prey_repro_rate:
            target = grid.random_empty_neighbor(x, y, write)
            if target is not None:
                tx, ty = target
                write[ty, tx] = CellState.PREY


class PredatorCell(Cell):
    state = CellState.PREDATOR

    def update(self, x, y, grid, write) -> None:
        # Only neighbors not already claimed by another predator this
        # generation are valid prey (see Grid.eaten).
        prey_neighbors = [
            (px, py) for (px, py) in grid.prey_neighbor_coords(x, y)
            if not grid.eaten[py, px]
        ]

        if prey_neighbors:
            idx = grid.config.rng.integers(len(prey_neighbors))
            px, py = prey_neighbors[idx]
            grid.eaten[py, px] = True
            write[py, px] = CellState.EMPTY
            grid.hunger[y, x] = 0
        else:
            grid.hunger[y, x] += 1

        if grid.hunger[y, x] > grid.config.starvation_rate:
            write[y, x] = CellState.EMPTY
            grid.hunger[y, x] = 0
            return

        write[y, x] = CellState.PREDATOR

        if grid.config.rng.random() < grid.config.predator_repro_rate:
            target = grid.random_empty_neighbor(x, y, write)
            if target is not None:
                tx, ty = target
                write[ty, tx] = CellState.PREDATOR
                grid.hunger[ty, tx] = 0
