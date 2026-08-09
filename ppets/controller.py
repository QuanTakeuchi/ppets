"""
SimulationController — LLD §1.1 (Controller layer)

Mediates View <-> Model: owns the CellularAutomatonEngine instance and
the run loop (a QTimer driving engine.step() at a user-selected rate),
per the layered architecture ("Controller ... mediates View <-> Model,
owns run loop and history"). No engine/model logic lives here — this
class only decides *when* to call step() and republishes the results
as Qt signals for the Presentation layer to consume.

Auto-pause behavior (UC02 Alternate/Exception Flows, TC5/TC6):
  - Extinction: pauses and emits extinction_detected(stats).
  - Performance: if a single step() takes longer than the NFR01 100ms
    budget for 5 consecutive generations, pauses and emits
    performance_warning(elapsed_ms). Resume still works afterward (the
    LLD explicitly allows the user to "resume at their own risk").
"""

from __future__ import annotations

import time
from typing import Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from .simulation import CellularAutomatonEngine, PopulationStats, SimulationConfig

PERF_BUDGET_MS = 100.0
PERF_STREAK_LIMIT = 5
DEFAULT_INTERVAL_MS = 200


class SimulationController(QObject):
    simulation_started = pyqtSignal(object)  # SimulationConfig
    generation_advanced = pyqtSignal(object)  # PopulationStats
    extinction_detected = pyqtSignal(object)  # PopulationStats
    performance_warning = pyqtSignal(float)  # elapsed_ms
    reset_done = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.engine: Optional[CellularAutomatonEngine] = None
        self.config: Optional[SimulationConfig] = None
        self._slow_streak = 0

        self._timer = QTimer(self)
        self._timer.setInterval(DEFAULT_INTERVAL_MS)
        self._timer.timeout.connect(self._on_tick)

    @property
    def is_running(self) -> bool:
        return self._timer.isActive()

    def start(self, config: SimulationConfig) -> None:
        self.config = config
        self.engine = CellularAutomatonEngine(config)
        self._slow_streak = 0
        # Timer starts before the signal fires so listeners that check
        # is_running (e.g. MainWindow refreshing button state) see the
        # post-start state, not a momentary in-between state.
        self._timer.start()
        self.simulation_started.emit(config)

    def pause(self) -> None:
        self._timer.stop()

    def resume(self) -> None:
        if self.engine is not None:
            self._timer.start()

    def step_once(self) -> None:
        if self.engine is not None:
            self._on_tick()

    def reset(self) -> None:
        self._timer.stop()
        self.engine = None
        self.config = None
        self._slow_streak = 0
        self.reset_done.emit()

    def set_speed(self, interval_ms: int) -> None:
        was_running = self._timer.isActive()
        self._timer.setInterval(interval_ms)
        if was_running:
            self._timer.start()

    def _on_tick(self) -> None:
        if self.engine is None:
            return

        start = time.perf_counter()
        stats = self.engine.step()
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        if elapsed_ms > PERF_BUDGET_MS:
            self._slow_streak += 1
        else:
            self._slow_streak = 0

        if self._slow_streak >= PERF_STREAK_LIMIT:
            self.pause()
            self._slow_streak = 0
            self.performance_warning.emit(elapsed_ms)
            return

        self.generation_advanced.emit(stats)

        if stats.is_extinct():
            self.pause()
            self.extinction_detected.emit(stats)
