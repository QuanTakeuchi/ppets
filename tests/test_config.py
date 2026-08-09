"""
Tests for SimulationConfig.validate() (LLD §2.3) — the exact same
validation ConfigPanel reuses live for TC3 (Invalid Parameter Entry),
so these cases double as coverage for that UI behavior.
"""

from __future__ import annotations

import pytest

from ppets.simulation import SimulationConfig


def test_defaults_are_valid():
    config = SimulationConfig()
    assert config.width == 50
    assert config.rng is not None


@pytest.mark.parametrize(
    "overrides",
    [
        {"width": 1},
        {"height": 1},
        {"prey_density": 1.5},
        {"predator_density": -0.1},
        {"prey_repro_rate": 1.5},
        {"predator_repro_rate": -0.5},
        {"prey_death_threshold": 9},
        {"prey_death_threshold": -1},
        {"starvation_rate": 0},
    ],
)
def test_rejects_out_of_range_fields(overrides):
    with pytest.raises(ValueError):
        SimulationConfig(**overrides)


def test_rejects_combined_density_over_one():
    with pytest.raises(ValueError, match=r"prey_density \+ predator_density"):
        SimulationConfig(prey_density=0.7, predator_density=0.6)


def test_error_message_lists_every_offending_field():
    """A single invalid submission can fail more than one rule at once
    (e.g. TC3's density example); the panel needs every message, not
    just the first, to show the user everything to fix in one pass."""
    with pytest.raises(ValueError) as exc_info:
        SimulationConfig(width=1, prey_density=2.0)
    message = str(exc_info.value)
    assert "width and height" in message
    assert "prey_density" in message


def test_seed_reproducibility_across_instances():
    """NFR02: identical seeds must yield identical RNG draws."""
    a = SimulationConfig(seed=123)
    b = SimulationConfig(seed=123)
    assert list(a.rng.integers(0, 1000, size=10)) == list(b.rng.integers(0, 1000, size=10))


def test_to_dict_from_dict_round_trip():
    original = SimulationConfig(width=20, height=25, seed=7)
    restored = SimulationConfig.from_dict(original.to_dict())
    assert restored.width == 20
    assert restored.height == 25
    assert restored.seed == 7
