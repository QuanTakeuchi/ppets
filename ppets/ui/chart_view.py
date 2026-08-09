"""
ChartView — LLD §3.2 (Visualization / ChartView)

Live predator/prey line chart via PyQtGraph (chosen over Matplotlib in
the LLD specifically for redraw performance inside a Qt event loop,
NFR01). Keeps a bounded ring buffer of the last N=2000 PopulationStats
to cap memory on long runs; full history for export lives elsewhere
(SimulationController/engine.history), not here.
"""

from __future__ import annotations

from collections import deque
from typing import Optional

import pyqtgraph as pg
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from ..simulation import PopulationStats

MAX_POINTS = 2000

_PREY_COLOR = (46, 139, 87)
_PREDATOR_COLOR = (255, 152, 0)


class ChartView(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._generations: deque[int] = deque(maxlen=MAX_POINTS)
        self._prey_counts: deque[int] = deque(maxlen=MAX_POINTS)
        self._predator_counts: deque[int] = deque(maxlen=MAX_POINTS)

        self._plot = pg.PlotWidget(parent=self)
        self._plot.setBackground("w")
        self._plot.setLabel("left", "Population")
        self._plot.setLabel("bottom", "Generation")
        self._plot.addLegend()

        self._prey_curve = self._plot.plot([], [], pen=pg.mkPen(_PREY_COLOR, width=2), name="Prey")
        self._predator_curve = self._plot.plot(
            [], [], pen=pg.mkPen(_PREDATOR_COLOR, width=2), name="Predator"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._plot)

    def add_point(self, stats: PopulationStats) -> None:
        self._generations.append(stats.generation)
        self._prey_counts.append(stats.prey_count)
        self._predator_counts.append(stats.predator_count)

        self._prey_curve.setData(list(self._generations), list(self._prey_counts))
        self._predator_curve.setData(list(self._generations), list(self._predator_counts))

    def clear(self) -> None:
        self._generations.clear()
        self._prey_counts.clear()
        self._predator_counts.clear()
        self._prey_curve.setData([], [])
        self._predator_curve.setData([], [])
