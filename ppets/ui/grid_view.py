"""
GridView — LLD §3.1 (Visualization / GridView)

Renders Grid.state via a single QImage built from a NumPy buffer, set
on one QGraphicsPixmapItem in a QGraphicsScene — deliberately NOT one
QGraphicsItem per cell, which the LLD calls out as a NFR01 (100ms/gen)
violation risk at 100x100+ grids.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap, QResizeEvent
from PyQt6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsView, QVBoxLayout, QWidget

# Conservation-themed palette matching the LLD's colour mapping.
_COLOR_LUT = np.array(
    [
        [235, 235, 235],  # EMPTY
        [46, 139, 87],  # PREY - green
        [255, 152, 0],  # PREDATOR - amber
    ],
    dtype=np.uint8,
)

CELL_PX = 8  # on-screen pixels per grid cell, before view scaling


class GridView(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self._view = QGraphicsView(self._scene, self)
        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        # QImage doesn't copy the buffer it wraps — must keep this
        # array alive for as long as the image/pixmap derived from it.
        self._buffer: Optional[np.ndarray] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)

    def render_state(self, state: np.ndarray) -> None:
        height, width = state.shape
        self._buffer = np.ascontiguousarray(_COLOR_LUT[state])

        image = QImage(
            self._buffer.data,
            width,
            height,
            self._buffer.strides[0],
            QImage.Format.Format_RGB888,
        )
        scaled = image.scaled(
            width * CELL_PX,
            height * CELL_PX,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        pixmap = QPixmap.fromImage(scaled)

        is_new = self._pixmap_item is None
        if is_new:
            self._pixmap_item = self._scene.addPixmap(pixmap)
        else:
            self._pixmap_item.setPixmap(pixmap)

        self._scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
        if is_new:
            self._fit()

    def clear(self) -> None:
        self._scene.clear()
        self._pixmap_item = None
        self._buffer = None

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._fit()

    def _fit(self) -> None:
        if self._pixmap_item is not None:
            self._view.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
