"""
Hard Stop 4 tests: the hardened ThresholdAnalyzer (parallel execution,
SeedSequence seeding, Wilson intervals, run records) and the FR10 threshold
estimator, including the failure cases and edge cases they must handle.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from ppets.analysis import (
    ParamRange, ThresholdAnalyzer, fit_threshold, fit_threshold_from_runs, replicate_seed,
    wilson_interval,
)
from ppets.simulation import SimulationConfig


def analyzer(seed=7, workers=1, reps=3, **kw):
    args = dict(
        param_a=ParamRange("predator_density", 0.10, 0.30, 0.10),
        param_b=ParamRange("predator_repro_rate", 0.10, 0.20, 0.10),
        replicates=reps,
        base_config=SimulationConfig(width=12, height=12, seed=seed),
        max_generations=20,
        workers=workers,
    )
    args.update(kw)
    return ThresholdAnalyzer(**args)


# --- Wilson interval (FR11) -------------------------------------------------

@pytest.mark.parametrize("k,n,lo,hi", [
    (0, 30, 0.0, 0.1135),     # published Wilson values, 4 d.p.
    (5, 10, 0.2366, 0.7634),
    (10, 10, 0.7225, 1.0),
    (1, 3, 0.0615, 0.7923),
])
def test_wilson_known_values(k, n, lo, hi):
    got = wilson_interval(k, n)
    assert got[0] == pytest.approx(lo, abs=1e-4)
    assert got[1] == pytest.approx(hi, abs=1e-4)


def test_wilson_matches_scipy():
    stats = pytest.importorskip("scipy.stats")
    for n in (1, 3, 4, 10, 30, 100):
        for k in range(n + 1):
            ref = stats.binomtest(k, n).proportion_ci(confidence_level=0.95, method="wilson")
            got = wilson_interval(k, n)
            assert got[0] == pytest.approx(ref.low, abs=1e-12)
            assert got[1] == pytest.approx(ref.high, abs=1e-12)


@pytest.mark.parametrize("k,n", [(-1, 3), (4, 3), (0, 0)])
def test_wilson_rejects_invalid_counts(k, n):
    with pytest.raises(ValueError):
        wilson_interval(k, n)


# --- Threshold estimate (FR10) ---------------------------------------------

def synthetic(d_star=0.25, slope=40.0, levels=np.arange(0.10, 0.41, 0.02), n=200, seed=1):
    rng = np.random.default_rng(seed)
    x = np.repeat(levels, n)
    p = 1 / (1 + np.exp(-slope * (x - d_star)))
    return x, (rng.random(len(x)) < p).astype(int)


def test_fit_recovers_known_threshold():
    x, y = synthetic()
    fit = fit_threshold(x, y, n_boot=200)
    assert fit.status == "ok"
    assert fit.d_star == pytest.approx(0.25, abs=0.01)
    assert fit.ci_delta[0] < 0.25 < fit.ci_delta[1]
    assert fit.ci_boot[0] < 0.25 < fit.ci_boot[1]
    assert fit.slope == pytest.approx(40, rel=0.15)


def test_fit_interval_shrinks_with_more_data():
    w = []
    for n in (20, 200):
        f = fit_threshold(*synthetic(n=n), n_boot=0)
        w.append(f.ci_delta[1] - f.ci_delta[0])
    assert w[1] < w[0] / 2


def test_fit_reports_constant_outcome():
    fit = fit_threshold([0.1, 0.2, 0.3], [0, 0, 0])
    assert fit.status == "constant" and fit.d_star is None


def test_fit_reports_quasi_separation():
    # Mixed outcomes at one level only: the MLE slope is infinite (found by the
    # HS4 end-to-end test at 6 replicates, which IRLS reported as not converged).
    fit = fit_threshold([0.05] * 6 + [0.15] * 6 + [0.25] * 6, [0] * 6 + [0, 1] * 3 + [1] * 6)
    assert fit.status == "separated" and fit.bracket == (0.15, 0.15)


def test_fit_reports_perfect_separation_with_bracket():
    fit = fit_threshold([0.1, 0.1, 0.2, 0.3, 0.3], [0, 0, 0, 1, 1])
    assert fit.status == "separated"
    assert fit.bracket == (0.2, 0.3)


@pytest.mark.parametrize("x,y", [([], []), ([0.1, 0.2], [0, 2]), ([0.1], [0, 1])])
def test_fit_rejects_bad_input(x, y):
    with pytest.raises(ValueError):
        fit_threshold(x, y)


# --- Hardened analyzer ------------------------------------------------------

def test_parallel_matches_serial_exactly():
    serial = analyzer(workers=1).run_sweep()
    parallel = analyzer(workers=2).run_sweep()
    assert serial.extinction_prob == parallel.extinction_prob
    assert [(r.seed, r.extinct, r.extinction_generation) for r in serial.runs] == \
           [(r.seed, r.extinct, r.extinction_generation) for r in parallel.runs]


def test_same_master_seed_reproduces_and_different_seed_differs():
    a = analyzer(seed=7).run_sweep()
    b = analyzer(seed=7).run_sweep()
    c = analyzer(seed=8).run_sweep()
    assert [r.seed for r in a.runs] == [r.seed for r in b.runs]
    assert a.extinction_prob == b.extinction_prob
    assert set(r.seed for r in a.runs).isdisjoint(r.seed for r in c.runs)


def test_replicate_seeds_unique_within_study():
    seeds = {replicate_seed(1, i, j, r) for i in range(10) for j in range(10) for r in range(30)}
    assert len(seeds) == 3000


def test_unseeded_study_records_master_seed_that_reproduces_it():
    first = analyzer(seed=None).run_sweep()
    assert first.master_seed is not None
    again = analyzer(seed=first.master_seed).run_sweep()
    assert first.extinction_prob == again.extinction_prob


def test_counts_intervals_and_run_records_are_consistent():
    res = analyzer(reps=4).run_sweep()
    assert res.complete
    assert len(res.runs) == 3 * 2 * 4
    for i in range(3):
        for j in range(2):
            assert res.n_runs[i][j] == 4
            assert res.extinction_prob[i][j] == res.n_extinct[i][j] / 4
            assert res.ci_low[i][j] <= res.extinction_prob[i][j] <= res.ci_high[i][j]


def test_parallel_cancel_leaves_nan_not_zero():
    ta = analyzer(workers=2, reps=2)
    res = ta.run_sweep(on_progress=lambda f: ta.cancel())
    assert res.complete is False
    assert any(math.isnan(v) for row in res.extinction_prob for v in row)
    finished = sum(not math.isnan(v) for row in res.extinction_prob for v in row)
    assert len(res.runs) == finished * 2  # records only for completed cells


def test_integer_axis_values_are_cast():
    res = analyzer(param_b=ParamRange("width", 10, 12, 2), reps=1).run_sweep()
    assert res.complete and res.param_b_values == [10, 12]


@pytest.mark.parametrize("name", ["seed", "toroidal", "rng"])
def test_non_sweepable_fields_rejected(name):
    with pytest.raises(ValueError, match="non-sweepable"):
        analyzer(param_a=ParamRange(name, 0, 1, 1))


def test_zero_predator_density_counts_as_extinct_at_generation_zero():
    # Documented semantics: a run that starts without predators is "extinct"
    # at generation 0. Sweeps that include density 0 must be read with this.
    res = analyzer(param_a=ParamRange("predator_density", 0.0, 0.0, 0.1), reps=2).run_sweep()
    assert all(r.extinct and r.extinction_generation == 0 for r in res.runs)


def test_fit_from_runs_end_to_end():
    res = analyzer(param_a=ParamRange("predator_density", 0.05, 0.45, 0.10),
                   param_b=ParamRange("predator_repro_rate", 0.15, 0.15, 0.1), reps=6).run_sweep()
    fit = fit_threshold_from_runs(res.runs, n_boot=50)
    # At 6 replicates the transition is often (quasi-)separated; the fit must
    # say so rather than fail to converge.
    assert fit.status in {"ok", "separated", "constant"}
    assert fit.n == len(res.runs)


# --- GUI corrections (DEF-10, FR14) -----------------------------------------

def test_stats_panel_has_no_extinction_risk_row(qapp):
    from ppets.ui.stats_panel import StatsPanel
    panel = StatsPanel()
    labels = [panel.layout().itemAt(i).widget().text() for i in range(panel.layout().count())
              if panel.layout().itemAt(i).widget() is not None]
    panel.deleteLater()
    assert not any("risk" in t.lower() for t in labels)


def test_main_window_shows_scope_statement(qapp):
    from ppets.ui.main_window import SCOPE_STATEMENT, MainWindow
    w = MainWindow()
    text, hidden = w.scope_label.text(), w.scope_label.isHidden()
    w.deleteLater()
    assert text == SCOPE_STATEMENT and not hidden
    assert "not forecasts" in text


def test_heatmap_view_accepts_nan_and_single_value_axis(qapp):
    from ppets.analysis import HeatmapData
    from ppets.ui.heatmap_view import HeatmapView
    data = HeatmapData([[0.2], [math.nan]], [[0.0], [math.nan]], [[0.2], [math.nan]],
                       "predator_density", "predator_repro_rate", [0.1, 0.2], [0.15], complete=False)
    v = HeatmapView()
    v.set_heatmap(data)
    v.deleteLater()
