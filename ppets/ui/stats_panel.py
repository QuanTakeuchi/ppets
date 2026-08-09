"""
StatsPanel — LLD §2.4 (PopulationStats) rendered live, per UC02/TC4
step 1: "generation count, prey count, predator count ... update each
generation".
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import QFormLayout, QLabel, QWidget

from ..simulation import PopulationStats


class StatsPanel(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.generation_label = QLabel("0")
        self.prey_label = QLabel("0")
        self.predator_label = QLabel("0")
        self.extinction_risk_label = QLabel("0.0")

        layout = QFormLayout(self)
        layout.addRow("Generation", self.generation_label)
        layout.addRow("Prey count", self.prey_label)
        layout.addRow("Predator count", self.predator_label)
        layout.addRow("Extinction risk", self.extinction_risk_label)

    def update_stats(self, stats: PopulationStats) -> None:
        self.generation_label.setText(str(stats.generation))
        self.prey_label.setText(str(stats.prey_count))
        self.predator_label.setText(str(stats.predator_count))
        self.extinction_risk_label.setText(f"{stats.extinction_risk:.4f}")

    def clear(self) -> None:
        self.generation_label.setText("0")
        self.prey_label.setText("0")
        self.predator_label.setText("0")
        self.extinction_risk_label.setText("0.0")
