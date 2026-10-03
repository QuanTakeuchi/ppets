"""
HeatmapView — LLD §3.3 (Visualization / HeatmapView)

UI-shell skeleton only (Hard Stop 3): renders a ThresholdAnalyzer.HeatmapData
as a 2D colour-mapped grid via pyqtgraph.ImageView, with axis labels bound
to the swept parameter names (FR07). Not yet wired into MainWindow or
PlaybackControls — there is no "Run Sweep" button yet. That integration,
plus the incremental redraw during a running sweep (UC03's alternate flow),
is next-sprint work; see KNOWN_ISSUES.md.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from ..analysis import HeatmapData


class HeatmapView(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # A plain ImageView's getView() returns a bare ViewBox (no
        # setLabel()) — pass an explicit PlotItem so axis labels work.
        self._image_view = pg.ImageView(parent=self, view=pg.PlotItem())
        self._image_view.ui.roiBtn.hide()
        self._image_view.ui.menuBtn.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._image_view)

    def set_heatmap(self, data: HeatmapData) -> None:
        """Consumes ThresholdAnalyzer.HeatmapData (LLD §4.1) and renders it.
        Axis labels follow the swept parameter names so the view is
        self-describing regardless of which two parameters were chosen."""
        matrix = np.asarray(data.extinction_prob, dtype=np.float64)
        self._image_view.setImage(
            matrix,
            levels=(0.0, 1.0),
            autoRange=True,
        )
        view = self._image_view.getView()
        view.setLabel("bottom", data.param_a_name)
        view.setLabel("left", data.param_b_name)

    def clear(self) -> None:
        self._image_view.clear()
