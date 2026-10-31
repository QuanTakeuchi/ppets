"""
Executable reproducers for defects found during Hard Stop 3 (RU-06) early
validation. Each test asserts the CORRECT behaviour and is marked
`xfail(strict=True)`:

  * today the defect is real, the assertion fails, pytest reports "xfailed"
    and the suite stays green;
  * the day someone fixes the defect, the test XPASSes, strict mode turns
    that into a failure, and the fixer is forced to delete the marker (and
    close the matching KNOWN_ISSUES.md entry).

IDs match KNOWN_ISSUES.md. None of these tests changes production code.

Hard Stop 4: all eight defects were fixed; their markers were removed
so the tests now guard against regression. The DEF-03 test was rewritten (see
its comment) and the DEF-04 spy gained a `generation` attribute, which the
fixed analyzer reads when recording the extinction generation.
"""

from __future__ import annotations

import math

import pytest

from ppets.analysis import HeatmapData, ParamRange, ThresholdAnalyzer
from ppets.analysis import threshold_analyzer as ta_module
from ppets.simulation import SimulationConfig

SMALL = dict(width=10, height=10)


def small_analyzer(**kw):
    args = dict(
        param_a=ParamRange("predator_density", 0.10, 0.30, 0.10),
        param_b=ParamRange("predator_repro_rate", 0.10, 0.20, 0.10),
        replicates=1,
        base_config=SimulationConfig(**SMALL),
        max_generations=5,
    )
    args.update(kw)
    return ThresholdAnalyzer(**args)


def test_def01_cancelled_sweep_marks_unfinished_cells():
    ta = small_analyzer()
    count = []

    def stop_after_first(_f):
        count.append(1)
        ta.cancel()

    res = ta.run_sweep(on_progress=stop_after_first)
    assert res.complete is False
    assert math.isnan(res.extinction_prob[-1][-1])  # never computed -> must not read as 0.0


def test_def02_sweep_can_be_rerun_after_cancel():
    ta = small_analyzer()
    ta.cancel()
    ta.run_sweep()
    again = ta.run_sweep()
    assert again.complete is True


def test_def03_invalid_axis_rejected_before_any_run(monkeypatch):
    # HS4 correction: the HS3 version of this test was xfail(raises=ValueError),
    # which would have stayed "xfailed" even after the fix, because the fixed
    # code also raises ValueError (just earlier). It now asserts the fix
    # directly: the error comes from the constructor and no run is started.
    started = []
    monkeypatch.setattr(ta_module, "_simulate", lambda job: started.append(job), raising=False)
    with pytest.raises(ValueError, match="invalid"):
        small_analyzer(
            param_a=ParamRange("predator_density", 0.60, 0.90, 0.10),
            base_config=SimulationConfig(width=10, height=10, prey_density=0.30),
        )
    assert started == []


def test_def04_master_seed_changes_replicate_seeds(monkeypatch):
    def seeds_used(base_seed):
        used = []

        class Spy:
            def __init__(self, cfg):
                used.append(cfg.seed)
                self.history = [type("S", (), {"is_extinct": lambda s: True, "prey_count": 0, "predator_count": 1, "generation": 1})()]

            def step(self):
                return self.history[-1]

        monkeypatch.setattr(ta_module, "CellularAutomatonEngine", Spy)
        small_analyzer(base_config=SimulationConfig(seed=base_seed, **SMALL)).run_sweep()
        return used

    assert seeds_used(1) != seeds_used(999)


def test_def05_heatmap_axes_use_parameter_values(qapp):
    data = HeatmapData(
        extinction_prob=[[0.1, 0.4], [0.6, 0.9]], prey_extinction_prob=[[0] * 2] * 2,
        predator_extinction_prob=[[0] * 2] * 2, param_a_name="predator_density",
        param_b_name="predator_repro_rate", param_a_values=[0.05, 0.10], param_b_values=[0.10, 0.20],
    )
    # Read the number out inside a helper so no Qt object stays referenced by
    # the failing test's traceback (a retained widget outliving QApplication
    # segfaults the interpreter at shutdown).
    right = _image_right_edge(data)
    assert right <= 0.15 + 1e-9, f"image spans 0..{right} (indices), not 0.05..0.10"


def _image_right_edge(data):
    from ppets.ui.heatmap_view import HeatmapView

    view = HeatmapView()
    view.set_heatmap(data)
    item = view._image_view.getImageItem()
    right = item.mapRectToParent(item.boundingRect()).right()
    view.deleteLater()
    return right


def test_def06_duplicate_axis_name_rejected():
    with pytest.raises(ValueError):
        small_analyzer(
            param_a=ParamRange("predator_density", 0.1, 0.2, 0.1),
            param_b=ParamRange("predator_density", 0.1, 0.3, 0.1),
        )


def test_def07_unknown_parameter_name_rejected_with_validation_error():
    with pytest.raises(ValueError):
        small_analyzer(param_a=ParamRange("nonsense", 0.0, 1.0, 0.5))


def test_def08_param_range_never_exceeds_stop():
    values = ParamRange("predator_density", 0.0, 0.5, 0.3).values()
    assert max(values) <= 0.5 + 1e-9, values
