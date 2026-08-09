"""
Tests for the CA transition rules (LLD §4) and step() loop (LLD §5).

Every grid here is built at 0% initial density so Grid.randomize()
leaves every cell EMPTY, then individual cells are placed by hand —
this makes each rule's edge case deterministic and independent of the
RNG, instead of asserting on a randomly-seeded population.
"""

from __future__ import annotations

import numpy as np

from ppets.simulation import CellularAutomatonEngine, CellState, Grid, PopulationStats, SimulationConfig
from ppets.simulation.cell import PreyCell


def make_engine(**overrides) -> CellularAutomatonEngine:
    defaults = dict(
        width=7,
        height=7,
        prey_density=0.0,
        predator_density=0.0,
        prey_repro_rate=0.0,
        predator_repro_rate=0.0,
        prey_death_threshold=3,
        starvation_rate=3,
        seed=1,
    )
    defaults.update(overrides)
    engine = CellularAutomatonEngine(SimulationConfig(**defaults))
    assert engine.grid.counts() == (0, 0), "expected a blank grid to place cells on"
    return engine


def make_grid(**overrides) -> Grid:
    """Bare Grid (no engine) for tests that call a Cell rule directly,
    bypassing engine.step()'s dispatch to every species at once."""
    defaults = dict(width=7, height=7, prey_density=0.0, predator_density=0.0, seed=1)
    defaults.update(overrides)
    grid = Grid(SimulationConfig(**defaults))
    grid.randomize()  # 0% density leaves every cell EMPTY
    return grid


class TestPreyRules:
    """
    Calls PreyCell.update() directly rather than going through a full
    engine.step(): a predator adjacent to prey attacks it immediately
    via a *separate* mechanism (PredatorCell's own prey-hunting), which
    would otherwise confound a test that's specifically about the
    prey_death_threshold count-based check.
    """

    def test_prey_survives_below_death_threshold(self):
        grid = make_grid(prey_death_threshold=3)
        grid.state[3, 3] = CellState.PREY
        grid.state[2, 2] = CellState.PREDATOR
        grid.state[2, 4] = CellState.PREDATOR  # only 2 predator neighbors, threshold is 3
        write = grid.new_write_buffer()

        PreyCell().update(3, 3, grid, write)

        assert write[3, 3] == CellState.PREY

    def test_prey_dies_at_death_threshold(self):
        grid = make_grid(prey_death_threshold=3)
        grid.state[3, 3] = CellState.PREY
        for y, x in [(2, 2), (2, 3), (2, 4)]:  # 3 predator neighbors == threshold
            grid.state[y, x] = CellState.PREDATOR
        write = grid.new_write_buffer()

        PreyCell().update(3, 3, grid, write)

        assert write[3, 3] == CellState.EMPTY

    def test_prey_reproduces_when_rate_is_certain(self):
        grid = make_grid(prey_repro_rate=1.0, prey_death_threshold=8)
        grid.state[3, 3] = CellState.PREY
        write = grid.new_write_buffer()

        PreyCell().update(3, 3, grid, write)

        neighborhood = write[2:5, 2:5]
        assert np.count_nonzero(neighborhood == CellState.PREY) == 2  # original + one offspring


class TestPredatorRules:
    def test_predator_eats_adjacent_prey_and_resets_hunger(self):
        engine = make_engine(starvation_rate=3)
        engine.grid.state[3, 3] = CellState.PREDATOR
        engine.grid.state[3, 4] = CellState.PREY
        engine.grid.hunger[3, 3] = 2

        engine.step()

        assert engine.grid.state[3, 4] == CellState.EMPTY  # prey eaten
        assert engine.grid.state[3, 3] == CellState.PREDATOR
        assert engine.grid.hunger[3, 3] == 0

    def test_predator_starves_past_the_starvation_rate(self):
        engine = make_engine(starvation_rate=2)
        engine.grid.state[3, 3] = CellState.PREDATOR
        engine.grid.hunger[3, 3] = 2  # already at the limit, no prey nearby this generation

        engine.step()

        assert engine.grid.state[3, 3] == CellState.EMPTY

    def test_two_predators_cannot_eat_the_same_prey(self):
        """Edge case flagged in the engine's own README as an
        implementation detail beyond the literal LLD pseudocode."""
        engine = make_engine(starvation_rate=5)
        engine.grid.state[3, 3] = CellState.PREY
        engine.grid.state[2, 3] = CellState.PREDATOR
        engine.grid.state[4, 3] = CellState.PREDATOR

        engine.step()

        assert engine.grid.state[3, 3] == CellState.EMPTY  # prey eaten exactly once
        fed = int(engine.grid.hunger[2, 3] == 0) + int(engine.grid.hunger[4, 3] == 0)
        assert fed == 1, "exactly one predator should get credit for the kill"


class TestToroidalBoundary:
    def test_wraps_around_when_toroidal(self):
        engine = make_engine(width=3, height=3, toroidal=True)
        engine.grid.state[2, 2] = CellState.PREDATOR  # bottom-right corner

        assert engine.grid.count_neighbors(0, 0, CellState.PREDATOR) == 1

    def test_does_not_wrap_when_fixed_boundary(self):
        engine = make_engine(width=3, height=3, toroidal=False)
        engine.grid.state[2, 2] = CellState.PREDATOR

        assert engine.grid.count_neighbors(0, 0, CellState.PREDATOR) == 0


class TestExtinctionAndReproducibility:
    def test_is_extinct_true_when_either_species_hits_zero(self):
        assert PopulationStats(generation=5, prey_count=0, predator_count=10).is_extinct()
        assert PopulationStats(generation=5, prey_count=10, predator_count=0).is_extinct()
        assert not PopulationStats(generation=5, prey_count=1, predator_count=1).is_extinct()

    def test_same_seed_produces_identical_trajectories(self):
        """NFR02, exercised end-to-end through a full run rather than
        just the RNG in isolation (see test_config.py)."""
        config_kwargs = dict(width=15, height=15, seed=42)
        engine_a = CellularAutomatonEngine(SimulationConfig(**config_kwargs))
        engine_b = CellularAutomatonEngine(SimulationConfig(**config_kwargs))

        for _ in range(15):
            stats_a = engine_a.step()
            stats_b = engine_b.step()
            assert stats_a.prey_count == stats_b.prey_count
            assert stats_a.predator_count == stats_b.predator_count
