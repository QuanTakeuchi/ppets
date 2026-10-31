"""Independent checks on the RU-09 link-function fits in validation/ru09_analyze.py."""

import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "validation"))

import ru09_analyze as ra  # noqa: E402

from ppets.analysis import fit_threshold  # noqa: E402

X = np.round(np.arange(0.06, 0.401, 0.02), 2)
N = np.full_like(X, 150.0)


def counts(link, b, seed=3):
    return np.random.default_rng(seed).binomial(150, ra.prob(b, X, link)).astype(float)


@pytest.mark.parametrize("link", sorted(ra.LINKS))
def test_glm_matches_direct_likelihood_maximum(link):
    k = counts(link, (-4.4, 20.0))
    b = ra.glm(X, k, N, link)

    def nll(t):
        p = ra.prob(t, X, link)
        return -np.sum(k * np.log(p) + (N - k) * np.log(1 - p))

    direct = minimize(nll, np.array(b) * 1.1, method="Nelder-Mead",
                      options=dict(xatol=1e-7, fatol=1e-9, maxiter=20000)).x
    assert b == pytest.approx(tuple(direct), rel=1e-3)


@pytest.mark.parametrize("link", sorted(ra.LINKS))
def test_d_star_is_where_the_curve_is_one_half(link):
    b = (-4.4, 20.0)
    assert ra.prob(b, np.array([ra.d_star(b, link)]), link)[0] == pytest.approx(0.5)


def test_loglog_rises_slowly_near_one_and_cloglog_is_its_mirror():
    e = np.array([-1.5, 0.0, 1.5])
    assert ra.LINKS["loglog"]["cdf"](e) == pytest.approx(1 - ra.LINKS["cloglog"]["cdf"](-e))


def test_logit_agrees_with_production_estimator():
    k = counts("logit", (-7.4, 29.5))
    xx = np.repeat(X, 150)
    yy = np.concatenate([np.r_[np.ones(int(a)), np.zeros(150 - int(a))] for a in k])
    assert ra.d_star(ra.glm(X, k, N, "logit"), "logit") == pytest.approx(fit_threshold(xx, yy, n_boot=0).d_star, abs=1e-6)


def test_glm_recovers_known_threshold_for_each_link():
    for link in ra.LINKS:
        b = (-4.4, 20.0)
        k = ra.prob(b, X, link) * N  # expected counts, no noise
        assert ra.d_star(ra.glm(X, k, N, link), link) == pytest.approx(ra.d_star(b, link), abs=1e-6)
