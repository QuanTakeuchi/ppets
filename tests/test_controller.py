"""
Tests for SimulationController (LLD §1.1 Controller layer): start/
pause/resume/step/reset plumbing and the extinction auto-pause path
(TC5), driven by calling step_once() directly rather than waiting on
a live QTimer, so the tests are fast and deterministic.
"""

from __future__ import annotations

import pytest

from ppets.controller import SimulationController
from ppets.simulation import SimulationConfig


@pytest.fixture
def controller(qapp):
    return SimulationController()


def test_start_creates_engine_and_starts_the_timer(controller):
    controller.start(SimulationConfig(width=10, height=10, seed=1))

    assert controller.engine is not None
    assert controller.is_running


def test_pause_and_resume_toggle_the_timer_only(controller):
    controller.start(SimulationConfig(width=10, height=10, seed=1))

    controller.pause()
    assert not controller.is_running
    assert controller.engine is not None  # pause must not touch the engine/history

    controller.resume()
    assert controller.is_running


def test_step_once_advances_one_generation_without_running(controller):
    controller.start(SimulationConfig(width=10, height=10, seed=1))
    controller.pause()

    controller.step_once()

    assert controller.engine.generation == 1
    assert not controller.is_running  # a manual step doesn't start the timer


def test_reset_drops_the_engine_and_stops_the_timer(controller):
    controller.start(SimulationConfig(width=10, height=10, seed=1))

    controller.reset()

    assert controller.engine is None
    assert not controller.is_running


def test_auto_pauses_and_emits_on_extinction(controller):
    events = []
    controller.extinction_detected.connect(lambda stats: events.append(stats))

    # Engineered to crash the prey population fast: almost no prey,
    # heavy predators, prey can't reproduce, and a single predator
    # neighbor is already lethal.
    config = SimulationConfig(
        width=10,
        height=10,
        prey_density=0.05,
        predator_density=0.5,
        prey_repro_rate=0.0,
        prey_death_threshold=1,
        seed=1,
    )
    controller.start(config)

    for _ in range(200):
        if not controller.is_running:
            break
        controller.step_once()

    assert events, "extinction_detected should have fired within 200 generations"
    assert not controller.is_running
    assert events[0].is_extinct()
