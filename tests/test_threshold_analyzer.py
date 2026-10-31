"""
Tests for the Module 3 implementation-baseline skeleton (LLD §4.1):
ParamRange, HeatmapData, ThresholdAnalyzer.run_sweep()/get_heatmap()/cancel().

Grids here are tiny (5x5, <=4 generations) purely to keep the smoke-test
suite fast — correctness of the underlying engine is already covered by
test_engine.py; these tests only check the sweep/aggregation logic itself.
"""

from __future__ import annotations

from ppets.analysis import HeatmapData, ParamRange, ThresholdAnalyzer
from ppets.simulation import SimulationConfig


def make_base_config(**overrides) -> SimulationConfig:
    defaults = dict(
        width=5,
        height=5,
        prey_density=0.3,
        predator_density=0.1,
        prey_repro_rate=0.2,
        predator_repro_rate=0.15,
        prey_death_threshold=3,
        starvation_rate=3,
    )
    defaults.update(overrides)
    return SimulationConfig(**defaults)


def test_param_range_values_inclusive():
    r = ParamRange(name="predator_density", start=0.1, stop=0.3, step=0.1)
    assert r.values() == [0.1, 0.2, 0.3]


def test_param_range_single_value_when_start_equals_stop():
    r = ParamRange(name="predator_density", start=0.1, stop=0.1, step=0.05)
    assert r.values() == [0.1]


def test_param_range_rejects_non_positive_step():
    r = ParamRange(name="x", start=0.0, stop=1.0, step=0.0)
    try:
        r.values()
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_run_sweep_produces_full_heatmap_grid():
    param_a = ParamRange(name="predator_density", start=0.05, stop=0.10, step=0.05)
    param_b = ParamRange(name="predator_repro_rate", start=0.10, stop=0.20, step=0.10)
    analyzer = ThresholdAnalyzer(
        param_a=param_a,
        param_b=param_b,
        replicates=2,
        base_config=make_base_config(),
        max_generations=4,
    )

    result = analyzer.run_sweep()

    assert isinstance(result, HeatmapData)
    assert result.complete is True
    assert len(result.extinction_prob) == 2  # len(param_a.values())
    assert all(len(row) == 2 for row in result.extinction_prob)  # len(param_b.values())
    for row in result.extinction_prob:
        for value in row:
            assert 0.0 <= value <= 1.0
    assert analyzer.get_heatmap() is result


def test_run_sweep_reports_progress():
    param_a = ParamRange(name="predator_density", start=0.05, stop=0.10, step=0.05)
    param_b = ParamRange(name="predator_repro_rate", start=0.10, stop=0.10, step=0.05)
    analyzer = ThresholdAnalyzer(
        param_a=param_a,
        param_b=param_b,
        replicates=1,
        base_config=make_base_config(),
        max_generations=3,
    )

    progress_values = []
    analyzer.run_sweep(on_progress=progress_values.append)

    assert progress_values == [0.5, 1.0]


def test_cancel_mid_sweep_yields_partial_heatmap():
    param_a = ParamRange(name="predator_density", start=0.05, stop=0.20, step=0.05)
    param_b = ParamRange(name="predator_repro_rate", start=0.10, stop=0.10, step=0.05)
    analyzer = ThresholdAnalyzer(
        param_a=param_a,
        param_b=param_b,
        replicates=1,
        base_config=make_base_config(),
        max_generations=2,
    )

    def cancel_after_first(progress: float) -> None:
        if progress >= 0.25:
            analyzer.cancel()

    result = analyzer.run_sweep(on_progress=cancel_after_first)

    assert result.complete is False
    assert analyzer.get_heatmap() is result


def test_large_sweep_triggers_warning_callback():
    param_a = ParamRange(name="predator_density", start=0.01, stop=1.00, step=0.01)
    param_b = ParamRange(name="predator_repro_rate", start=0.01, stop=1.00, step=0.01)

    warnings = []
    ThresholdAnalyzer(
        param_a=param_a,
        param_b=param_b,
        replicates=10,
        # prey_density=0 keeps every cell valid now that the analyzer checks
        # prey + predator density <= 1 for each cell at construction (DEF-03).
        base_config=make_base_config(prey_density=0.0),
        on_warning=warnings.append,
    )

    assert len(warnings) == 1
    assert "long time" in warnings[0]


def test_small_sweep_does_not_trigger_warning_callback():
    param_a = ParamRange(name="predator_density", start=0.05, stop=0.10, step=0.05)
    param_b = ParamRange(name="predator_repro_rate", start=0.10, stop=0.10, step=0.05)

    warnings = []
    ThresholdAnalyzer(
        param_a=param_a,
        param_b=param_b,
        replicates=1,
        base_config=make_base_config(),
        on_warning=warnings.append,
    )

    assert warnings == []


def test_replicates_must_be_positive():
    param_a = ParamRange(name="predator_density", start=0.05, stop=0.10, step=0.05)
    param_b = ParamRange(name="predator_repro_rate", start=0.10, stop=0.10, step=0.05)
    try:
        ThresholdAnalyzer(param_a=param_a, param_b=param_b, replicates=0, base_config=make_base_config())
        assert False, "expected ValueError"
    except ValueError:
        pass
