"""
PopulationStats — LLD §2 class diagram (Simulation Engine subsystem).

DEVIATION FLAG (see README "Design Deviations" #2):
the LLD lists an `extinction_risk` field. The placeholder heuristic that
filled it was removed at Hard Stop 4 (DEF-10): it ranked eventual extinction
no better than chance (AUC 0.479, n = 688). As HS2 decided, extinction
probability is only reported where it is meaningful: across replicates of a
sweep cell, with a Wilson interval (ThresholdAnalyzer, FR11).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PopulationStats:
    generation: int
    prey_count: int
    predator_count: int

    def is_extinct(self) -> bool:
        return self.prey_count == 0 or self.predator_count == 0

    def to_csv_row(self) -> str:
        return f"{self.generation},{self.prey_count},{self.predator_count}"

    @staticmethod
    def csv_header() -> str:
        return "generation,prey_count,predator_count"
