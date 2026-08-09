"""
ConfigPanel — LLD §2.3 / UC01 (TC1-TC3)

Validation is NOT reimplemented here — every field change attempts to
build a SimulationConfig(**values) and surfaces whatever ValueError
SimulationConfig.validate() raises (already field-labeled, semicolon-
joined). This keeps the Presentation layer from drifting out of sync
with the business rules the Engine layer actually enforces (TC3).

Seed handling (NFR02 / TC1 step 4): if the seed field is left blank, a
concrete seed is generated here (not left as None) so the run is still
fully reproducible; once Start is pressed the resolved value is echoed
back into the field.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..simulation import SimulationConfig


class ConfigPanel(QWidget):
    validity_changed = pyqtSignal(bool)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 2000)
        self.width_spin.setValue(50)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 2000)
        self.height_spin.setValue(50)

        self.toroidal_check = QCheckBox("Toroidal (wrap-around)")
        self.toroidal_check.setChecked(True)

        self.prey_density_spin = self._rate_spin(0.30)
        self.predator_density_spin = self._rate_spin(0.10)
        self.prey_repro_spin = self._rate_spin(0.20)
        self.predator_repro_spin = self._rate_spin(0.15)

        self.prey_death_threshold_spin = QSpinBox()
        self.prey_death_threshold_spin.setRange(-5, 15)
        self.prey_death_threshold_spin.setValue(3)

        self.starvation_rate_spin = QSpinBox()
        self.starvation_rate_spin.setRange(-5, 20)
        self.starvation_rate_spin.setValue(3)

        self.seed_edit = QLineEdit()
        self.seed_edit.setPlaceholderText("auto")

        self.error_label = QLabel()
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("color: #b00020;")

        form = QFormLayout()
        form.addRow("Grid width", self.width_spin)
        form.addRow("Grid height", self.height_spin)
        form.addRow("", self.toroidal_check)
        form.addRow("Prey density", self.prey_density_spin)
        form.addRow("Predator density", self.predator_density_spin)
        form.addRow("Prey repro rate", self.prey_repro_spin)
        form.addRow("Predator repro rate", self.predator_repro_spin)
        form.addRow("Prey death threshold", self.prey_death_threshold_spin)
        form.addRow("Starvation rate", self.starvation_rate_spin)
        form.addRow("Seed (optional)", self.seed_edit)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.error_label)
        layout.addStretch(1)

        self._current_config: Optional[SimulationConfig] = None

        self.width_spin.valueChanged.connect(self._revalidate)
        self.height_spin.valueChanged.connect(self._revalidate)
        self.toroidal_check.stateChanged.connect(self._revalidate)
        self.prey_density_spin.valueChanged.connect(self._revalidate)
        self.predator_density_spin.valueChanged.connect(self._revalidate)
        self.prey_repro_spin.valueChanged.connect(self._revalidate)
        self.predator_repro_spin.valueChanged.connect(self._revalidate)
        self.prey_death_threshold_spin.valueChanged.connect(self._revalidate)
        self.starvation_rate_spin.valueChanged.connect(self._revalidate)
        self.seed_edit.textChanged.connect(self._revalidate)

        self._revalidate()

    @staticmethod
    def _rate_spin(default: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(0.0, 2.0)
        spin.setSingleStep(0.05)
        spin.setDecimals(2)
        spin.setValue(default)
        return spin

    def build_config(self) -> Optional[SimulationConfig]:
        return self._current_config

    def set_locked(self, locked: bool) -> None:
        self.setEnabled(not locked)

    def echo_resolved_seed(self, seed: int) -> None:
        self.seed_edit.setText(str(seed))

    def revalidate(self) -> None:
        self._revalidate()

    def _parse_seed(self) -> int:
        text = self.seed_edit.text().strip()
        if text:
            return int(text)  # may raise ValueError, caught by _revalidate
        return int(np.random.default_rng().integers(0, 2**31 - 1))

    def _revalidate(self, *_args) -> None:
        try:
            seed = self._parse_seed()
        except ValueError:
            self._current_config = None
            self.error_label.setText("Seed must be an integer, or left blank.")
            self.validity_changed.emit(False)
            return

        try:
            config = SimulationConfig(
                width=self.width_spin.value(),
                height=self.height_spin.value(),
                toroidal=self.toroidal_check.isChecked(),
                prey_density=self.prey_density_spin.value(),
                predator_density=self.predator_density_spin.value(),
                prey_repro_rate=self.prey_repro_spin.value(),
                predator_repro_rate=self.predator_repro_spin.value(),
                prey_death_threshold=self.prey_death_threshold_spin.value(),
                starvation_rate=self.starvation_rate_spin.value(),
                seed=seed,
            )
        except ValueError as exc:
            self._current_config = None
            self.error_label.setText(str(exc))
            self.validity_changed.emit(False)
            return

        self._current_config = config
        self.error_label.setText("")
        self.validity_changed.emit(True)
