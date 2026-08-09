"""
PopulationStats — LLD §2 class diagram (Simulation Engine subsystem).

DEVIATION FLAG (see README "Design Deviations" #2):
`extinction_risk` is listed as a field but the LLD doesn't pin down its
formula — that derivation belongs to the Analysis subsystem's
ThresholdAnalyzer (LLD §6), which isn't in scope for this CA-core pass.
For now this is a simple, clearly-labeled placeholder heuristic so the
field exists and behaves sanely; swap in the real ThresholdAnalyzer
metric once that subsystem is built.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PopulationStats:
    generation: int
    prey_count: int
    predator_count: int

    @property
    def extinction_risk(self) -> float:
        """
        Placeholder heuristic (NOT the final metric): 1.0 if either
        species is already gone, otherwise inverse of the smaller
        population's share of total, scaled to (0.0, 1.0).
        """
        if self.prey_count == 0 or self.predator_count == 0:
            return 1.0
        total = self.prey_count + self.predator_count
        smaller = min(self.prey_count, self.predator_count)
        return round(1.0 - (smaller / total) * 2, 4) if total else 1.0

    def is_extinct(self) -> bool:
        return self.prey_count == 0 or self.predator_count == 0

    def to_csv_row(self) -> str:
        return f"{self.generation},{self.prey_count},{self.predator_count},{self.extinction_risk}"

    @staticmethod
    def csv_header() -> str:
        return "generation,prey_count,predator_count,extinction_risk"
