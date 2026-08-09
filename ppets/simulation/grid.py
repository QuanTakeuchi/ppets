"""
Grid — LLD §3 (Grid Internal Structure)

Backing store is a 2D NumPy array of int8 state codes (0=empty,
1=prey, 2=predator), as specified. Boundary handling supports both
toroidal (wrap-around, modulo arithmetic) and fixed (clamped) modes
per SimulationConfig.toroidal. Updates go through double-buffering:
callers compute into a fresh "write" array, then call swap_from().
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np

from .cell import CellState
from .config import SimulationConfig

# Moore neighborhood: all 8 surrounding offsets (LLD §6 design decision).
_MOORE_OFFSETS: Tuple[Tuple[int, int], ...] = (
    (-1, -1), (0, -1), (1, -1),
    (-1, 0),           (1, 0),
    (-1, 1),  (0, 1),  (1, 1),
)


class Grid:
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.width = config.width
        self.height = config.height

        self.state = np.zeros((self.height, self.width), dtype=np.int8)
        # Predator-only hunger counter, parallel to `state`.
        self.hunger = np.zeros((self.height, self.width), dtype=np.int16)
        # Reset each generation; marks prey cells already claimed by a
        # predator this step (see cell.py docstring for why this exists).
        self.eaten = np.zeros((self.height, self.width), dtype=bool)

    def randomize(self) -> None:
        """Seed initial population per config densities (LLD §2)."""
        rng = self.config.rng
        draw = rng.random((self.height, self.width))

        prey_cut = self.config.prey_density
        pred_cut = self.config.prey_density + self.config.predator_density

        self.state[:] = CellState.EMPTY
        self.state[draw < prey_cut] = CellState.PREY
        self.state[(draw >= prey_cut) & (draw < pred_cut)] = CellState.PREDATOR
        self.hunger[:] = 0

    def _neighbor_coords(self, x: int, y: int) -> List[Tuple[int, int]]:
        coords = []
        for dx, dy in _MOORE_OFFSETS:
            nx, ny = x + dx, y + dy
            if self.config.toroidal:
                nx %= self.width
                ny %= self.height
                coords.append((nx, ny))
            else:
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    coords.append((nx, ny))
        return coords

    def count_neighbors(self, x: int, y: int, target: CellState) -> int:
        return sum(1 for (nx, ny) in self._neighbor_coords(x, y) if self.state[ny, nx] == target)

    def prey_neighbor_coords(self, x: int, y: int) -> List[Tuple[int, int]]:
        return [(nx, ny) for (nx, ny) in self._neighbor_coords(x, y) if self.state[ny, nx] == CellState.PREY]

    def random_empty_neighbor(self, x: int, y: int, write: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        Used for reproduction targeting. Checks against the WRITE buffer
        (not the read buffer) so a cell that was already claimed by an
        earlier reproduction event this generation isn't double-booked.
        """
        empties = [(nx, ny) for (nx, ny) in self._neighbor_coords(x, y) if write[ny, nx] == CellState.EMPTY]
        if not empties:
            return None
        idx = self.config.rng.integers(len(empties))
        return empties[idx]

    def new_write_buffer(self) -> np.ndarray:
        return np.zeros_like(self.state)

    def swap_from(self, write: np.ndarray) -> None:
        self.state = write
        self.eaten[:] = False

    def counts(self) -> Tuple[int, int]:
        prey = int(np.count_nonzero(self.state == CellState.PREY))
        predator = int(np.count_nonzero(self.state == CellState.PREDATOR))
        return prey, predator
