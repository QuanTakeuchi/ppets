"""
SimulationConfig — LLD §2 (SimulationConfig Data Structure Detail)

Holds every tunable parameter for a simulation run, with validation
rules and default values as specified in the LLD. Also owns the
centralized RandomGenerator (LLD §6 Key Design Decisions: "all
randomness routed through a single RandomGenerator instance") so
that a run is fully reproducible from its seed (NFR02).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional
import numpy as np


@dataclass
class SimulationConfig:
    # --- Grid geometry ---
    width: int = 50
    height: int = 50
    toroidal: bool = True  # wrap-around grid (LLD §6 default)

    # --- Initial population densities ---
    prey_density: float = 0.30       # fraction of cells seeded as prey
    predator_density: float = 0.10   # fraction of cells seeded as predator

    # --- CA rule parameters (LLD §4 Cell State Transition Logic) ---
    prey_repro_rate: float = 0.20        # probability prey reproduces per step
    predator_repro_rate: float = 0.15    # probability predator reproduces per step
    prey_death_threshold: int = 3        # predator neighbors >= this => prey dies
    starvation_rate: int = 3             # generations without eating before predator dies

    # --- Reproducibility (NFR02) ---
    seed: Optional[int] = None

    def __post_init__(self) -> None:
        self.validate()
        # Centralized RNG — every stochastic decision in the engine
        # should draw from this instance, never from a bare np.random call.
        self._rng = np.random.default_rng(self.seed)

    @property
    def rng(self) -> np.random.Generator:
        return self._rng

    def validate(self) -> None:
        errors = []

        if self.width < 2 or self.height < 2:
            errors.append("width and height must both be >= 2")

        for name, val in (
            ("prey_density", self.prey_density),
            ("predator_density", self.predator_density),
            ("prey_repro_rate", self.prey_repro_rate),
            ("predator_repro_rate", self.predator_repro_rate),
        ):
            if not (0.0 <= val <= 1.0):
                errors.append(f"{name} must be within 0.0-1.0, got {val}")

        if self.prey_density + self.predator_density > 1.0:
            errors.append(
                "prey_density + predator_density must not exceed 1.0 "
                f"(got {self.prey_density + self.predator_density})"
            )

        if not (0 <= self.prey_death_threshold <= 8):
            errors.append("prey_death_threshold must be within 0-8 (Moore neighborhood size)")

        if self.starvation_rate < 1:
            errors.append("starvation_rate must be >= 1")

        if errors:
            raise ValueError("Invalid SimulationConfig: " + "; ".join(errors))

    def to_dict(self) -> dict:
        """Serialization shape used by ScenarioManager (LLD §7)."""
        d = asdict(self)
        d.pop("_rng", None)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "SimulationConfig":
        data = {k: v for k, v in data.items() if k != "_rng"}
        return cls(**data)
