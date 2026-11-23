"""Hard Stop 6 (RU-12) final tests.

1. The production estimators (ppets.analysis.estimate_threshold) regenerate the
   published RU-09 values from the committed run files, exactly.
2. The pathway table adds up: predator-first + prey-first + both = extinct.
3. Well-mixed mode (FR12) changes partner choice only: partners ignore
   position, are distinct, exclude the cell itself, and the spatial path is
   untouched (same history as before the change).
4. SimulationConfig type checks (HS5-07) and the half-installed PyQt6 guard (HS5-05).
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "validation"))

from hs4_common import read_runs_csv  # noqa: E402

from ppets.analysis import (DEFAULT_METHOD, estimate_threshold, fit_threshold, model_free_d_star,  # noqa: E402
                            pathway_table, wilson_interval)
from ppets.simulation import CellularAutomatonEngine, SimulationConfig  # noqa: E402
from ppets.simulation.grid import Grid  # noqa: E402

RU09 = json.loads((REPO / "evidence/ru09/ru09_results.json").read_text(encoding="utf-8"))


def _rows(names):
    rows = []
    for nm in names:
        for folder in ("evidence/hs4/studies", "evidence/ru09/studies"):
            p = REPO / folder / f"{nm}.runs.csv"
            if p.exists():
                rows += read_runs_csv(p)
    return rows


L30 = [f"L30_s{s}" for s in range(4001, 4006)]


# ---- 1. estimator regression -------------------------------------------------

def test_default_method_is_loglog():
    assert DEFAULT_METHOD == "loglog"


@pytest.mark.parametrize("size,names", [(30, L30), (20, ["L20_s4011"]), (75, ["L75_s4014", "L75_s4017"])])
def test_production_estimators_reproduce_published_values(size, names):
    rows = _rows(names)
    est = estimate_threshold([r["a_value"] for r in rows], [int(r["extinct"]) for r in rows], seed=1000 + size)
    pub = RU09["Q1"]["sizes"][str(size)]
    for m in ("loglog", "model_free", "logit"):
        assert est[m].status == "ok"
        assert est[m].d_star == pytest.approx(pub[m]["d_star"], abs=1e-12)
        assert list(est[m].ci) == pytest.approx(pub[m]["ci"], abs=1e-12)


def test_headline_numbers_as_reported():
    rows = _rows(L30)
    est = estimate_threshold([r["a_value"] for r in rows], [int(r["extinct"]) for r in rows], seed=1030)
    assert round(est["loglog"].d_star, 3) == 0.241
    assert [round(c, 3) for c in est["loglog"].ci] == [0.236, 0.245]
    assert round(est["model_free"].d_star, 3) == 0.236
    assert round(est["logit"].d_star, 3) == 0.250


def test_logit_link_agrees_with_hs4_per_run_fit():
    """The grouped logit and the HS4 per-run IRLS fit maximise the same likelihood."""
    rows = _rows(L30)
    x, y = [r["a_value"] for r in rows], [int(r["extinct"]) for r in rows]
    assert estimate_threshold(x, y, methods=("logit",), n_boot=0)["logit"].d_star == pytest.approx(
        fit_threshold(x, y, n_boot=0).d_star, abs=1e-6)


def test_estimator_recovers_a_known_loglog_curve():
    x = np.round(np.arange(0.06, 0.401, 0.02), 2)
    b0, b1 = -6.0, 24.0
    truth = (-np.log(np.log(2)) - b0) / b1
    p = np.exp(-np.exp(-(b0 + b1 * x)))
    k = np.random.default_rng(5).binomial(2000, p)
    xs = np.repeat(x, 2000)
    ys = np.concatenate([np.r_[np.ones(a), np.zeros(2000 - a)] for a in k])
    est = estimate_threshold(xs, ys, methods=("loglog",), n_boot=200, seed=1)["loglog"]
    assert est.d_star == pytest.approx(truth, abs=0.003)
    assert est.ci[0] <= truth <= est.ci[1]


def test_constant_outcome_is_reported_not_fitted():
    est = estimate_threshold([0.1, 0.2, 0.3] * 5, [0] * 15)
    assert all(e.status == "constant" and e.d_star is None for e in est.values())


def test_model_free_none_when_curve_never_reaches_half():
    assert model_free_d_star(np.array([0.1, 0.2]), np.array([0.0, 1.0]), np.array([10.0, 10.0])) is None


def test_unknown_method_rejected():
    with pytest.raises(ValueError):
        estimate_threshold([0.1, 0.2], [0, 1], methods=("probit",))


# ---- 2. pathways --------------------------------------------------------------

def test_pathways_add_up_to_overall_extinction_on_published_runs():
    rows = _rows(L30)
    table = pathway_table([r["a_value"] for r in rows], [r["prey_extinct"] for r in rows],
                          [r["predator_extinct"] for r in rows])
    assert sum(t.n for t in table) == 2700
    for t in table:
        assert t.predator_first + t.prey_first + t.both_same_step == t.extinct
        assert t.p_predator_first + t.p_prey_first <= t.p_extinct + 1e-12
        assert t.ci_prey_first == wilson_interval(t.prey_first, t.n)
    # Totals match the RU-09 Q3 counts.
    q3 = RU09["Q3"]["L30"]
    assert sum(t.predator_first for t in table) == q3["predator_first"]
    assert sum(t.prey_first for t in table) == q3["prey_first"]
    assert sum(t.extinct for t in table) == q3["extinct"]


# ---- 3. well-mixed mode ---------------------------------------------------------

def test_spatial_partners_are_the_moore_neighbourhood():
    g = Grid(SimulationConfig(width=10, height=10, seed=1))
    assert sorted(g._neighbor_coords(5, 5)) == sorted((5 + dx, 5 + dy) for dx in (-1, 0, 1)
                                                      for dy in (-1, 0, 1) if (dx, dy) != (0, 0))


def test_well_mixed_partners_distinct_exclude_self_and_stable_within_a_generation():
    g = Grid(SimulationConfig(width=10, height=10, seed=1, mixing="well_mixed"))
    p = g._neighbor_coords(4, 4)
    assert len(p) == 8 and len(set(p)) == 8 and (4, 4) not in p
    assert g._neighbor_coords(4, 4) == p            # same set for death check and reproduction
    g.swap_from(g.new_write_buffer())
    assert g._neighbor_coords(4, 4) != p            # redrawn next generation (P(equal) ~ 1e-12)


def test_well_mixed_partner_choice_ignores_position():
    """Partner offsets from the focal cell are uniform over the grid, not local.
    Spatial: every partner is within distance 1. Well-mixed: the share within
    distance 1 is about 8/99, and each other cell is chosen about equally often."""
    W = 10
    g = Grid(SimulationConfig(width=W, height=W, seed=7, mixing="well_mixed"))
    hits = np.zeros(W * W)
    near = total = 0
    for _ in range(3000):
        g._partners.clear()
        for (px, py) in g._neighbor_coords(0, 0):
            hits[py * W + px] += 1
            total += 1
            dx, dy = min(px, W - px), min(py, W - py)
            near += max(dx, dy) <= 1
    assert hits[0] == 0
    assert near / total == pytest.approx(8 / 99, abs=0.01)
    others = hits[1:]
    expected = total / 99
    chi2 = float(np.sum((others - expected) ** 2 / expected))
    assert chi2 < 160   # df = 98; the 0.999 quantile is about 147


def test_spatial_mode_unchanged_by_the_hs6_code():
    """Reference run (evidence/hs5/main_expected.txt) still matches with the default mixing."""
    out = subprocess.run([sys.executable, "main.py"], cwd=REPO, capture_output=True, text=True, check=True).stdout
    expected = (REPO / "evidence/hs5/main_expected.txt").read_text(encoding="utf-8")
    assert out.replace("\r\n", "\n") == expected.replace("\r\n", "\n")


def test_well_mixed_run_is_seed_deterministic():
    def hist(seed):
        e = CellularAutomatonEngine(SimulationConfig(width=20, height=20, predator_density=0.02,
                                                     seed=seed, mixing="well_mixed"))
        for _ in range(15):
            e.step()
        return [(s.prey_count, s.predator_count) for s in e.history]
    assert hist(3) == hist(3)
    assert hist(3) != hist(4)


def test_mixing_round_trips_and_is_validated():
    cfg = SimulationConfig(width=12, height=12, seed=2, mixing="well_mixed")
    assert SimulationConfig.from_dict(cfg.to_dict()).mixing == "well_mixed"
    with pytest.raises(ValueError, match="mixing"):
        SimulationConfig(mixing="random")


# ---- 4. HS5 carry-overs -------------------------------------------------------------

@pytest.mark.parametrize("field,value", [("width", 30.5), ("height", "30"), ("starvation_rate", 2.0),
                                         ("prey_density", "0.3"), ("toroidal", 1), ("seed", 1.5), ("width", True)])
def test_config_rejects_wrong_types(field, value):
    with pytest.raises(ValueError, match=field):
        SimulationConfig(**{field: value})


def test_config_accepts_numpy_numbers():
    cfg = SimulationConfig(width=np.int64(20), height=np.int64(20), prey_density=np.float64(0.3), seed=np.int64(5))
    assert cfg.width == 20


def test_half_installed_pyqt6_does_not_break_import(tmp_path):
    """FP-02: a half-installed PyQt6 imports as a namespace package whose
    __file__ is None. Simulated with a stub module in a fresh interpreter."""
    code = ("import sys, types; m = types.ModuleType('PyQt6'); m.__file__ = None; sys.modules['PyQt6'] = m; "
            "import ppets.simulation, ppets.analysis; print('ok')")
    import os
    env = {**os.environ, "PYTHONPATH": str(REPO)}
    r = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "ok"
