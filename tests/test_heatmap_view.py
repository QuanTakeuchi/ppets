"""
Smoke test for the HeatmapView UI-shell skeleton (LLD §3.3). Only checks
that it accepts a HeatmapData and renders without error — it isn't wired
into MainWindow yet, so there's no end-to-end UC03 flow to test here.
"""

from __future__ import annotations

from ppets.analysis import HeatmapData
from ppets.ui.heatmap_view import HeatmapView


def make_heatmap_data() -> HeatmapData:
    return HeatmapData(
        extinction_prob=[[0.1, 0.4], [0.6, 0.9]],
        prey_extinction_prob=[[0.1, 0.3], [0.5, 0.7]],
        predator_extinction_prob=[[0.0, 0.1], [0.1, 0.2]],
        param_a_name="predator_density",
        param_b_name="predator_repro_rate",
        param_a_values=[0.05, 0.10],
        param_b_values=[0.10, 0.20],
    )


def test_set_heatmap_renders_without_error(qapp):
    view = HeatmapView()
    view.set_heatmap(make_heatmap_data())


def test_clear_after_set_heatmap(qapp):
    view = HeatmapView()
    view.set_heatmap(make_heatmap_data())
    view.clear()
