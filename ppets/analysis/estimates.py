"""
Statistical estimates for sweep results (FR10, FR11). numpy only, so no
new dependency enters the lock file (RU-07 adjustment A6).

wilson_interval   Wilson 95% score interval for a binomial proportion (FR11).
fit_threshold     Logistic regression of the binary extinction outcome on one
                  parameter; d* is the value where P(extinct) = 0.5 (FR10),
                  reported with a delta-method interval and a stratified
                  bootstrap interval.

Edge cases are reported, not hidden: if the outcome is constant, or the two
outcomes are perfectly separated along x, the maximum-likelihood fit does not
exist and `status` says so, with the bracket that contains the transition.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np

Z95 = 1.959963984540054


def wilson_interval(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    """Wilson score interval for k successes in n trials."""
    if n <= 0:
        raise ValueError(f"n must be > 0, got {n}")
    if not 0 <= k <= n:
        raise ValueError(f"k must be within 0..n, got k={k}, n={n}")
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


@dataclass
class ThresholdFit:
    status: str                      # "ok", "constant", "separated", "not_converged"
    n: int
    d_star: Optional[float] = None
    slope: Optional[float] = None    # b1: steepness of the transition, per unit x
    intercept: Optional[float] = None
    ci_delta: Optional[tuple[float, float]] = None
    ci_boot: Optional[tuple[float, float]] = None
    boot_valid: int = 0              # bootstrap refits that produced a usable d*
    bracket: Optional[tuple[float, float]] = None  # for status "separated"
    deviance: Optional[float] = None
    levels: list = field(default_factory=list)     # (x, n, k, p_obs, p_fit) per level


def _irls(x: np.ndarray, y: np.ndarray, max_iter: int = 100, tol: float = 1e-10):
    X = np.column_stack([np.ones_like(x), x])
    beta = np.zeros(2)
    for _ in range(max_iter):
        eta = np.clip(X @ beta, -35, 35)
        p = 1 / (1 + np.exp(-eta))
        w = p * (1 - p)
        H = X.T @ (X * w[:, None])
        try:
            step = np.linalg.solve(H, X.T @ (y - p))
        except np.linalg.LinAlgError:
            return None, None
        beta = beta + step
        if np.max(np.abs(step)) < tol:
            eta = np.clip(X @ beta, -35, 35)
            p = 1 / (1 + np.exp(-eta))
            H = X.T @ (X * (p * (1 - p))[:, None])
            return beta, np.linalg.inv(H)
    return None, None


def _separation(x: np.ndarray, y: np.ndarray) -> Optional[tuple[float, float]]:
    """Return the bracket if y is perfectly separated along x, else None."""
    x0, x1 = x[y == 0], x[y == 1]
    if x0.max() <= x1.min():  # complete or quasi-complete separation
        return float(x0.max()), float(x1.min())
    if x1.max() <= x0.min():
        return float(x1.max()), float(x0.min())
    return None


def fit_threshold(x: Sequence[float], y: Sequence[int], n_boot: int = 1000,
                  seed: int = 0) -> ThresholdFit:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.shape != y.shape or x.ndim != 1 or len(x) == 0:
        raise ValueError("x and y must be non-empty 1-D sequences of equal length")
    if not np.isin(y, (0.0, 1.0)).all():
        raise ValueError("y must contain only 0/1 outcomes")

    levels_x = np.unique(x)
    def level_table(beta=None):
        out = []
        for lx in levels_x:
            m = x == lx
            k, n = int(y[m].sum()), int(m.sum())
            pf = None if beta is None else float(1 / (1 + math.exp(-(beta[0] + beta[1] * lx))))
            out.append((float(lx), n, k, k / n, pf))
        return out

    if y.min() == y.max():
        return ThresholdFit("constant", len(x), levels=level_table())
    bracket = _separation(x, y)
    if bracket is not None:
        return ThresholdFit("separated", len(x), bracket=bracket, levels=level_table())

    beta, cov = _irls(x, y)
    if beta is None or beta[1] == 0:
        return ThresholdFit("not_converged", len(x), levels=level_table())
    b0, b1 = beta
    d = -b0 / b1
    g = np.array([-1 / b1, b0 / b1 ** 2])
    se = math.sqrt(float(g @ cov @ g))
    p = 1 / (1 + np.exp(-(b0 + b1 * x)))
    dev = float(-2 * np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))

    # Stratified bootstrap: resample runs within each x level, refit.
    rng = np.random.default_rng(seed)
    idx_by_level = [np.flatnonzero(x == lx) for lx in levels_x]
    boots = []
    for _ in range(n_boot):
        idx = np.concatenate([rng.choice(ix, size=len(ix), replace=True) for ix in idx_by_level])
        xb, yb = x[idx], y[idx]
        if yb.min() == yb.max() or _separation(xb, yb) is not None:
            continue
        bb, _ = _irls(xb, yb)
        if bb is not None and bb[1] != 0:
            boots.append(-bb[0] / bb[1])
    ci_boot = None
    if len(boots) >= max(20, n_boot // 2):
        ci_boot = (float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5)))

    return ThresholdFit(
        "ok", len(x), d_star=float(d), slope=float(b1), intercept=float(b0),
        ci_delta=(d - Z95 * se, d + Z95 * se), ci_boot=ci_boot, boot_valid=len(boots),
        deviance=dev, levels=level_table(beta),
    )


def fit_threshold_from_runs(runs, param: str = "a", **kw) -> ThresholdFit:
    """Convenience: fit d* against the a- or b-axis value of HeatmapData.runs."""
    attr = "a_value" if param == "a" else "b_value"
    return fit_threshold([getattr(r, attr) for r in runs], [int(r.extinct) for r in runs], **kw)
