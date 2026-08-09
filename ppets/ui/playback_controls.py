"""
PlaybackControls — UC02 (TC4): Start/Pause/Resume/Step/Reset + speed.

Button enable/disable state is driven entirely by MainWindow via
set_start_enabled()/set_run_state() rather than internal logic, since
"is a run valid to start" (ConfigPanel validity) and "is a run active"
(SimulationController state) are both owned elsewhere.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget

from ..controller import DEFAULT_INTERVAL_MS

MIN_INTERVAL_MS = 20
MAX_INTERVAL_MS = 1000


class PlaybackControls(QWidget):
    start_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    resume_clicked = pyqtSignal()
    step_clicked = pyqtSignal()
    reset_clicked = pyqtSignal()
    speed_changed = pyqtSignal(int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.start_button = QPushButton("Start")
        self.pause_button = QPushButton("Pause")
        self.resume_button = QPushButton("Resume")
        self.step_button = QPushButton("Step")
        self.reset_button = QPushButton("Reset")

        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(MIN_INTERVAL_MS, MAX_INTERVAL_MS)
        self.speed_slider.setValue(DEFAULT_INTERVAL_MS)
        self.speed_slider.setInvertedAppearance(True)  # right = faster
        self.speed_label = QLabel(f"{DEFAULT_INTERVAL_MS} ms/generation")

        buttons = QHBoxLayout()
        for button in (
            self.start_button,
            self.pause_button,
            self.resume_button,
            self.step_button,
            self.reset_button,
        ):
            buttons.addWidget(button)

        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel("Speed:"))
        speed_row.addWidget(self.speed_slider)
        speed_row.addWidget(self.speed_label)

        layout = QVBoxLayout(self)
        layout.addLayout(buttons)
        layout.addLayout(speed_row)

        self.start_button.clicked.connect(self.start_clicked)
        self.pause_button.clicked.connect(self.pause_clicked)
        self.resume_button.clicked.connect(self.resume_clicked)
        self.step_button.clicked.connect(self.step_clicked)
        self.reset_button.clicked.connect(self.reset_clicked)
        self.speed_slider.valueChanged.connect(self._on_speed_changed)

        self.set_start_enabled(False)
        self.set_run_state(has_run=False, running=False)

    def _on_speed_changed(self, value: int) -> None:
        self.speed_label.setText(f"{value} ms/generation")
        self.speed_changed.emit(value)

    def set_start_enabled(self, enabled: bool) -> None:
        self.start_button.setEnabled(enabled)

    def set_run_state(self, has_run: bool, running: bool) -> None:
        self.pause_button.setEnabled(has_run and running)
        self.resume_button.setEnabled(has_run and not running)
        self.step_button.setEnabled(has_run and not running)
        self.reset_button.setEnabled(has_run)
