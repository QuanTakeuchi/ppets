"""
MainWindow — LLD §1.1 Presentation layer assembly.

The only file that imports both the Controller and the individual
views; every other UI module is wired together here rather than
talking to each other directly, keeping the MVC boundary intact.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QMainWindow, QSplitter, QVBoxLayout, QWidget

from ..controller import SimulationController
from ..simulation import PopulationStats, SimulationConfig
from .chart_view import ChartView
from .config_panel import ConfigPanel
from .grid_view import GridView
from .playback_controls import PlaybackControls
from .stats_panel import StatsPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PPETS - Predator-Prey Extinction Threshold Simulator")
        self.resize(1100, 700)

        self.controller = SimulationController(self)
        self.config_panel = ConfigPanel()
        self.playback_controls = PlaybackControls()
        self.grid_view = GridView()
        self.chart_view = ChartView()
        self.stats_panel = StatsPanel()

        self.banner_label = QLabel()
        self.banner_label.setWordWrap(True)
        self.banner_label.setStyleSheet("background-color: #fff3cd; color: #664d03; padding: 6px;")
        self.banner_label.hide()

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(self.config_panel)
        left_layout.addWidget(self.playback_controls)
        left_layout.addStretch(1)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(self.banner_label)
        right_layout.addWidget(self.grid_view, 3)
        right_layout.addWidget(self.chart_view, 2)
        right_layout.addWidget(self.stats_panel)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)

        self._wire_signals()

    def _wire_signals(self) -> None:
        self.config_panel.validity_changed.connect(self._on_validity_changed)

        self.playback_controls.start_clicked.connect(self._on_start_clicked)
        self.playback_controls.pause_clicked.connect(self._on_pause_clicked)
        self.playback_controls.resume_clicked.connect(self._on_resume_clicked)
        self.playback_controls.step_clicked.connect(self.controller.step_once)
        self.playback_controls.reset_clicked.connect(self.controller.reset)
        self.playback_controls.speed_changed.connect(self.controller.set_speed)

        self.controller.simulation_started.connect(self._on_simulation_started)
        self.controller.generation_advanced.connect(self._on_generation_advanced)
        self.controller.extinction_detected.connect(self._on_extinction_detected)
        self.controller.performance_warning.connect(self._on_performance_warning)
        self.controller.reset_done.connect(self._on_reset_done)

    def _on_validity_changed(self, valid: bool) -> None:
        self.playback_controls.set_start_enabled(valid and self.controller.engine is None)

    def _on_start_clicked(self) -> None:
        config = self.config_panel.build_config()
        if config is None:
            return
        self.banner_label.hide()
        self.controller.start(config)

    def _on_pause_clicked(self) -> None:
        self.controller.pause()
        self._refresh_run_state()

    def _on_resume_clicked(self) -> None:
        self.controller.resume()
        self._refresh_run_state()

    def _on_simulation_started(self, config: SimulationConfig) -> None:
        self.config_panel.echo_resolved_seed(config.seed)
        self.config_panel.set_locked(True)
        self.playback_controls.set_start_enabled(False)
        self._refresh_run_state()

    def _on_generation_advanced(self, stats: PopulationStats) -> None:
        self.grid_view.render_state(self.controller.engine.grid.state)
        self.chart_view.add_point(stats)
        self.stats_panel.update_stats(stats)

    def _on_extinction_detected(self, stats: PopulationStats) -> None:
        species = "Prey" if stats.prey_count == 0 else "Predator"
        self.banner_label.setText(
            f"Extinction: {species} population reached zero at generation "
            f"{stats.generation}. Simulation paused."
        )
        self.banner_label.show()
        self._refresh_run_state()

    def _on_performance_warning(self, elapsed_ms: float) -> None:
        self.banner_label.setText(
            f"Performance warning: a generation took {elapsed_ms:.0f}ms, above the "
            "100ms budget, for 5 consecutive generations. Simulation paused - "
            "consider reducing grid size, or resume anyway."
        )
        self.banner_label.show()
        self._refresh_run_state()

    def _on_reset_done(self) -> None:
        self.config_panel.set_locked(False)
        self.grid_view.clear()
        self.chart_view.clear()
        self.stats_panel.clear()
        self.banner_label.hide()
        self._refresh_run_state()

    def _refresh_run_state(self) -> None:
        has_run = self.controller.engine is not None
        self.playback_controls.set_run_state(has_run=has_run, running=self.controller.is_running)
        if not has_run:
            self.config_panel.revalidate()
