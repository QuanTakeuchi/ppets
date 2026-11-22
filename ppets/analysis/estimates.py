"""
Statistical estimates for sweep results (FR10, FR11). numpy only, so no
new dependency enters the lock file (RU-07 adjustment A6).

wilson_interval     Wilson 95% score interval for a binomial proportion (FR11).
estimate_threshold  d* (where P(extinct) = 0.5, FR10) by the log-log link
                    (default since Hard Stop 6), the model-free isotonic
                    crossing, and the logistic link, all from one shared
                    bootstrap of the per-level counts. The algorithm is the one
                    behind the RU-09 evidence (validation/ru09_analyze.py), so
                    the published values regenerate exactly (tests/test_hs6_*).
pathway_table       P(predators die out first), P(prey die out first) and
                    P(extinct) per level, each with a Wilson interval.
fit_threshold       The HS4 per-run logistic fit, kept for comparison with the
                    hs4-evidence results (delta-method and bootstrap intervals).

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


# ---------------------------------------------------------------------------
# Hard Stop 6: the estimator decision (HS4 D3, RU-09) moved into production.
# ---------------------------------------------------------------------------

LN2 = math.log(2)


def _logit_cdf(e):
    return 1 / (1 + np.exp(-e))


def _logit_pdf(e):
    return np.exp(-e) / (1 + np.exp(-e)) ** 2


# P(extinct) = cdf(b0 + b1 * x); eta50 = cdf^-1(0.5). log-log rises slowly and
# then saturates fast (the shape seen in every RU-09 study); cloglog mirrors it.
LINKS = {
    "logit": dict(cdf=_logit_cdf, pdf=_logit_pdf, eta50=0.0),
    "loglog": dict(cdf=lambda e: np.exp(-np.exp(-e)), pdf=lambda e: np.exp(-e - np.exp(-e)), eta50=-math.log(LN2)),
    "cloglog": dict(cdf=lambda e: 1 - np.exp(-np.exp(e)), pdf=lambda e: np.exp(e - np.exp(e)), eta50=math.log(LN2)),
}
DEFAULT_METHOD = "loglog"
METHODS = ("loglog", "model_free", "logit", "cloglog")


def group_counts(x: Sequence[float], y: Sequence[int]):
    """Per-level counts: (levels, k extinct, n runs) as float arrays."""
    x = np.round(np.asarray(x, dtype=float), 6)
    y = np.asarray(y, dtype=float)
    if x.shape != y.shape or x.ndim != 1 or len(x) == 0:
        raise ValueError("x and y must be non-empty 1-D sequences of equal length")
    if not np.isin(y, (0.0, 1.0)).all():
        raise ValueError("y must contain only 0/1 outcomes")
    lv = np.unique(x)
    n = np.array([float(np.sum(x == v)) for v in lv])
    k = np.array([float(np.sum(y[x == v])) for v in lv])
    return lv, k, n


def fit_link(x, k, n, link: str = DEFAULT_METHOD, max_iter: int = 200):
    """Binomial GLM on grouped counts by Fisher scoring. Returns (b0, b1) or None."""
    L = LINKS[link]
    x = np.asarray(x, dtype=float)
    X = np.column_stack([np.ones_like(x), x - x.mean()])
    beta = np.array([0.0, 10.0])
    for _ in range(max_iter):
        eta = np.clip(X @ beta, -30, 30)
        mu = np.clip(L["cdf"](eta), 1e-10, 1 - 1e-10)
        d = np.maximum(L["pdf"](eta), 1e-12)
        w = n * d * d / (mu * (1 - mu))
        H = X.T @ (X * w[:, None])
        try:
            step = np.linalg.solve(H, X.T @ ((k - n * mu) * d / (mu * (1 - mu))))
        except np.linalg.LinAlgError:
            return None
        size = float(np.max(np.abs(step)))
        if size > 25:  # damp the first steps
            step = step * 25 / size
        beta = beta + step
        if size < 1e-9:
            return float(beta[0] - beta[1] * x.mean()), float(beta[1])
    return None


def link_d_star(b, link: str) -> float:
    return (LINKS[link]["eta50"] - b[0]) / b[1]


def link_prob(b, x, link: str):
    return np.clip(LINKS[link]["cdf"](np.clip(b[0] + b[1] * np.asarray(x, dtype=float), -30, 30)), 1e-10, 1 - 1e-10)


def pava(y, w) -> list:
    """Weighted isotonic (non-decreasing) regression, pool-adjacent-violators."""
    blocks = [[float(v), float(wt), 1] for v, wt in zip(y, w)]
    i = 0
    while i < len(blocks) - 1:
        if blocks[i][0] > blocks[i + 1][0]:
            a, b = blocks[i], blocks[i + 1]
            wt = a[1] + b[1]
            blocks[i] = [(a[0] * a[1] + b[0] * b[1]) / wt, wt, a[2] + b[2]]
            del blocks[i + 1]
            i = max(i - 1, 0)
        else:
            i += 1
    return [v for v, _, m in blocks for _ in range(m)]


def model_free_d_star(x, k, n) -> Optional[float]:
    """Where the isotonic fit of per-level proportions first reaches 0.5, by
    linear interpolation between levels. None if it never does."""
    q = pava(np.asarray(k) / np.asarray(n), n)
    for j in range(1, len(x)):
        if q[j - 1] < 0.5 <= q[j]:
            return float(x[j - 1] + (0.5 - q[j - 1]) * (x[j] - x[j - 1]) / (q[j] - q[j - 1]))
    return None


@dataclass
class ThresholdEstimate:
    method: str                      # "loglog", "logit", "cloglog" or "model_free"
    status: str                      # "ok", "no_crossing", "not_converged", "constant"
    d_star: Optional[float] = None
    ci: Optional[tuple[float, float]] = None   # percentile bootstrap 95% interval
    boot_valid: int = 0
    intercept: Optional[float] = None
    slope: Optional[float] = None


def estimate_threshold(x: Sequence[float], y: Sequence[int],
                       methods: Sequence[str] = ("loglog", "model_free", "logit"),
                       n_boot: int = 1000, seed: int = 0) -> dict:
    """d* by each method, with a percentile 95% interval from one shared
    bootstrap of the per-level counts (k_b ~ Binomial(n, k/n) at every level,
    equivalent to resampling runs within each level). Returns
    {method: ThresholdEstimate}. With seed = 1000 + grid size this reproduces
    evidence/ru09/ru09_results.json Q1 exactly."""
    for m in methods:
        if m != "model_free" and m not in LINKS:
            raise ValueError(f"Unknown method {m!r}; choose from {', '.join(METHODS)}")
    lv, k, n = group_counts(x, y)
    if k.sum() in (0, n.sum()):
        return {m: ThresholdEstimate(m, "constant") for m in methods}
    links = [m for m in methods if m != "model_free"]
    fits = {m: fit_link(lv, k, n, m) for m in links}
    rng = np.random.default_rng(seed)
    draws = {m: [] for m in methods}
    for _ in range(n_boot):
        kb = rng.binomial(n.astype(int), k / n).astype(float)
        for m in links:
            b = fit_link(lv, kb, n, m)
            if b is not None and b[1] > 0:
                draws[m].append(link_d_star(b, m))
        if "model_free" in methods:
            c = model_free_d_star(lv, kb, n)
            if c is not None:
                draws["model_free"].append(c)

    def ci(m):
        if n_boot == 0 or len(draws[m]) < max(20, n_boot // 2):
            return None
        return (float(np.percentile(draws[m], 2.5)), float(np.percentile(draws[m], 97.5)))

    out = {}
    for m in methods:
        if m == "model_free":
            d = model_free_d_star(lv, k, n)
            out[m] = ThresholdEstimate(m, "ok" if d is not None else "no_crossing", d,
                                       ci(m) if d is not None else None, len(draws[m]))
        else:
            b = fits[m]
            if b is None or b[1] <= 0:
                out[m] = ThresholdEstimate(m, "not_converged", boot_valid=len(draws[m]))
            else:
                out[m] = ThresholdEstimate(m, "ok", float(link_d_star(b, m)), ci(m), len(draws[m]), b[0], b[1])
    return out


def estimate_threshold_from_runs(runs, param: str = "a", **kw) -> dict:
    """estimate_threshold against the a- or b-axis value of HeatmapData.runs."""
    attr = "a_value" if param == "a" else "b_value"
    return estimate_threshold([getattr(r, attr) for r in runs], [int(r.extinct) for r in runs], **kw)


@dataclass
class PathwayLevel:
    value: float
    n: int
    extinct: int
    predator_first: int     # predators reached 0 while prey survived
    prey_first: int         # prey reached 0 while predators survived
    both_same_step: int     # both reached 0 in the same generation
    p_extinct: float
    p_predator_first: float
    p_prey_first: float
    ci_extinct: tuple
    ci_predator_first: tuple
    ci_prey_first: tuple


def pathway_table(x: Sequence[float], prey_extinct: Sequence[bool], predator_extinct: Sequence[bool]) -> list:
    """Per-level extinction split by pathway, each with a Wilson 95% interval.
    predator_first + prey_first + both_same_step == extinct at every level."""
    x = np.round(np.asarray(x, dtype=float), 6)
    prey = np.asarray(prey_extinct, dtype=bool)
    pred = np.asarray(predator_extinct, dtype=bool)
    rows = []
    for v in np.unique(x):
        m = x == v
        nn = int(m.sum())
        pf = int(np.sum(m & pred & ~prey))
        qf = int(np.sum(m & prey & ~pred))
        both = int(np.sum(m & prey & pred))
        ext = pf + qf + both
        rows.append(PathwayLevel(float(v), nn, ext, pf, qf, both, ext / nn, pf / nn, qf / nn,
                                 wilson_interval(ext, nn), wilson_interval(pf, nn), wilson_interval(qf, nn)))
    return rows


def pathway_table_from_runs(runs, param: str = "a") -> list:
    attr = "a_value" if param == "a" else "b_value"
    return pathway_table([getattr(r, attr) for r in runs], [r.prey_extinct for r in runs],
                         [r.predator_extinct for r in runs])
