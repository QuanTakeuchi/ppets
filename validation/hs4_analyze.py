"""Analyse the HS4 studies against the thresholds in EXPERIMENT_PLAN.md.

    python validation/hs4_analyze.py

Reads evidence/hs4/studies/*.runs.csv (and the HS3 baseline for E8), writes
evidence/hs4/hs4_results.json (every number the package quotes, with a
pass/fail verdict per experiment) and the figures in evidence/hs4/figures/.
"""

from __future__ import annotations

import csv
import math
import time

import numpy as np

from hs4_common import EVIDENCE, REPO, dump, read_runs_csv, write_manifest

from ppets.analysis import fit_threshold, wilson_interval

STUDIES = EVIDENCE / "studies"
FIG = EVIDENCE / "figures"
FIG.mkdir(exist_ok=True)
TOL = 0.02  # pre-set tolerance in density units (EXPERIMENT_PLAN.md)


def load(name, horizon=None):
    rows = read_runs_csv(STUDIES / f"{name}.runs.csv")
    x = np.array([r["a_value"] for r in rows])
    if horizon is None:
        y = np.array([int(r["extinct"]) for r in rows])
    else:
        y = np.array([int(r["extinct"] and r["extinction_generation"] <= horizon) for r in rows])
    return rows, x, y


def summarise(fit):
    d = dict(status=fit.status, n=fit.n, d_star=fit.d_star, slope=fit.slope,
             ci_boot=fit.ci_boot, ci_delta=fit.ci_delta, boot_valid=fit.boot_valid,
             bracket=fit.bracket)
    if fit.ci_boot:
        d["half_width_boot"] = (fit.ci_boot[1] - fit.ci_boot[0]) / 2
        d["se_boot"] = (fit.ci_boot[1] - fit.ci_boot[0]) / (2 * 1.959964)
    if fit.ci_delta:
        d["half_width_delta"] = (fit.ci_delta[1] - fit.ci_delta[0]) / 2
    return d


def pava(y, w):
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
    return [v for v, _, n in blocks for _ in range(n)]


def crossing(x, y):
    """Model-free d*: where the isotonic fit of per-level proportions first
    reaches 0.5, by linear interpolation between levels. None if it never does."""
    lv = np.unique(x)
    p = [y[x == l].mean() for l in lv]
    q = pava(p, [int((x == l).sum()) for l in lv])
    for k in range(1, len(lv)):
        if q[k - 1] < 0.5 <= q[k]:
            return float(lv[k - 1] + (0.5 - q[k - 1]) * (lv[k] - lv[k - 1]) / (q[k] - q[k - 1]))
    return None


def crossing_ci(x, y, n_boot=1000, seed=0):
    rng = np.random.default_rng(seed)
    idx = [np.flatnonzero(x == l) for l in np.unique(x)]
    b = []
    for _ in range(n_boot):
        j = np.concatenate([rng.choice(i, size=len(i)) for i in idx])
        c = crossing(x[j], y[j])
        if c is not None:
            b.append(c)
    return crossing(x, y), [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))]


def contains(ci, v):
    return ci is not None and ci[0] <= v <= ci[1]


def main():
    t0 = time.perf_counter()
    R = {"generated_by": "validation/hs4_analyze.py", "tolerance": TOL}
    fits = {}

    # ---- E3/E4: five independent L30 studies --------------------------------
    seeds = range(4001, 4006)
    xs, ys, per = [], [], {}
    for s in seeds:
        _, x, y = load(f"L30_s{s}")
        f = fit_threshold(x, y, n_boot=1000, seed=s)
        fits[f"L30_s{s}"] = f
        per[s] = summarise(f)
        xs.append(x)
        ys.append(y)
    X, Y = np.concatenate(xs), np.concatenate(ys)
    pooled = fit_threshold(X, Y, n_boot=1000, seed=1)
    fits["L30_pooled"] = pooled
    R["E4"] = {"studies": per, "pooled": summarise(pooled)}
    d_vals = [per[s]["d_star"] for s in seeds]
    se_vals = [per[s]["se_boot"] for s in seeds]
    covered = sum(contains(per[s]["ci_boot"], pooled.d_star) for s in seeds)
    sd_between = float(np.std(d_vals, ddof=1))
    R["E4"].update(between_study_sd=sd_between, mean_within_se=float(np.mean(se_vals)),
                   ratio=sd_between / float(np.mean(se_vals)), studies_covering_pooled=covered,
                   pass_=bool(covered >= 4 and sd_between <= 1.5 * np.mean(se_vals)))

    # Level table for the pooled data (150 replicates per level).
    levels = []
    for lx in np.unique(X):
        m = X == lx
        k, n = int(Y[m].sum()), int(m.sum())
        lo, hi = wilson_interval(k, n)
        levels.append(dict(density=float(lx), n=n, k=k, p=k / n, lo=lo, hi=hi))
    R["E4"]["pooled_levels"] = levels

    # Goodness of fit of the logistic shape (diagnostic added after the results
    # were seen; no pre-set threshold). Pearson chi-square over levels, df = levels - 2.
    from scipy.stats import chi2
    chi, rows_gof = 0.0, []
    for lx, l in zip(np.unique(X), levels):
        pf = 1 / (1 + math.exp(-(pooled.intercept + pooled.slope * lx)))
        e = pf * l["n"]
        chi += (l["k"] - e) ** 2 / (l["n"] * pf * (1 - pf))
        rows_gof.append(dict(density=float(lx), observed=l["k"], expected=round(e, 1)))
    # Model-free check of d* (post-hoc, added after the lack of fit was seen):
    # isotonic regression + interpolated 0.5 crossing, stratified bootstrap.
    mf = {}
    for name, (xx, yy) in {"L30_pooled": (X, Y), **{f"L30_s{s}": (xs[k], ys[k]) for k, s in enumerate(seeds)}}.items():
        d, c = crossing_ci(xx, yy, seed=7)
        mf[name] = dict(d_star=d, ci=c, logistic=fits[name].d_star)
    R["model_free"] = dict(note="post-hoc sensitivity check, not a pre-set threshold", estimates=mf)

    R["E4"]["goodness_of_fit"] = dict(pearson_chi2=chi, df=len(levels) - 2,
                                      p_value=float(chi2.sf(chi, len(levels) - 2)), levels=rows_gof,
                                      note="post-hoc diagnostic, not a pre-set threshold")

    # ---- E3: precision vs replicate count (subsample the pooled 150) ---------
    rng = np.random.default_rng(2026)
    idx_by_level = [np.flatnonzero(X == lx) for lx in np.unique(X)]
    e3 = []
    for n in (3, 5, 10, 30, 60, 150):
        draws = 1 if n == 150 else 40
        ds, hws, fails = [], [], 0
        for _ in range(draws):
            idx = np.concatenate([rng.choice(ix, size=n, replace=False) for ix in idx_by_level])
            f = fit_threshold(X[idx], Y[idx], n_boot=300, seed=int(rng.integers(1 << 30)))
            if f.status != "ok" or f.ci_boot is None:
                fails += 1
                continue
            ds.append(f.d_star)
            hws.append((f.ci_boot[1] - f.ci_boot[0]) / 2)
        e3.append(dict(n=n, draws=draws, fit_failures=fails,
                       d_star_mean=float(np.mean(ds)) if ds else None,
                       d_star_sd=float(np.std(ds, ddof=1)) if len(ds) > 1 else None,
                       d_star_range=[float(min(ds)), float(max(ds))] if ds else None,
                       half_width_median=float(np.median(hws)) if hws else None))
    hw30 = next(r for r in e3 if r["n"] == 30)["half_width_median"]
    R["E3"] = {"by_n": e3, "half_width_at_30": hw30, "pass_": bool(hw30 is not None and hw30 <= TOL)}

    # ---- E5: finite size ----------------------------------------------------
    ref = pooled.d_star
    e5 = {"L30_reference": "pooled five L30 studies", "sizes": {}}
    ok = True
    for L, s in ((20, 4011), (40, 4012), (50, 4013)):
        _, x, y = load(f"L{L}_s{s}")
        f = fit_threshold(x, y, n_boot=1000, seed=s)
        fits[f"L{L}"] = f
        d = summarise(f)
        d["diff_from_L30"] = (f.d_star - ref) if f.d_star is not None else None
        ok &= d["diff_from_L30"] is not None and abs(d["diff_from_L30"]) < TOL
        e5["sizes"][L] = d
    e5["sizes"][30] = summarise(pooled)
    e5["pass_"] = bool(ok)
    # Post-hoc: least-squares fit d*(L) = a + b / L over the four sizes (no
    # interval; four points). Describes the trend; it is not evidence of a limit.
    Ls = np.array([20, 30, 40, 50], dtype=float)
    ds = np.array([e5["sizes"][int(L)]["d_star"] for L in Ls])
    b_, a_ = np.polyfit(1 / Ls, ds, 1)
    e5["finite_size_fit"] = dict(a=float(a_), b=float(b_), max_abs_residual=float(np.max(np.abs(ds - (a_ + b_ / Ls)))),
                                 note="post-hoc, 4 points, no interval; extrapolation to large L is not supported")
    R["E5"] = e5

    # ---- E6: reproduction-rate ablation -------------------------------------
    e6, ok = {"settings": {}}, True
    for r, s in ((0.05, 4021), (0.30, 4022)):
        _, x, y = load(f"r{int(r*100):02d}_s{s}")
        f = fit_threshold(x, y, n_boot=1000, seed=s)
        fits[f"r{r}"] = f
        d = summarise(f)
        d["diff_from_r015"] = (f.d_star - ref) if f.d_star is not None else None
        ok &= d["diff_from_r015"] is not None and abs(d["diff_from_r015"]) < TOL
        e6["settings"][r] = d
    e6["settings"][0.15] = summarise(pooled)
    e6["pass_"] = bool(ok)
    R["E6"] = e6
    for name, (stem, L) in {"L20": ("L20_s4011", 20), "L40": ("L40_s4012", 40), "L50": ("L50_s4013", 50),
                            "r0.05": ("r05_s4021", None), "r0.3": ("r30_s4022", None)}.items():
        _, xx, yy = load(stem)
        d, c = crossing_ci(xx, yy, seed=7)
        R["model_free"]["estimates"][name] = dict(d_star=d, ci=c, logistic=fits[name].d_star)

    # ---- E7: horizon ---------------------------------------------------------
    rows, x, y300 = load("H300_s4031")
    _, _, y150 = load("H300_s4031", horizon=150)
    f300 = fit_threshold(x, y300, n_boot=1000, seed=4031)
    f150 = fit_threshold(x, y150, n_boot=1000, seed=4031)
    fits["H300"], fits["H150"] = f300, f150
    late = sum(1 for r in rows if r["extinct"] and r["extinction_generation"] > 150)
    gens = [r["extinction_generation"] for r in rows if r["extinct"]]
    R["E7"] = dict(d150=summarise(f150), d300=summarise(f300),
                   diff=f300.d_star - f150.d_star, late_extinctions=late, runs=len(rows),
                   late_fraction=late / len(rows), max_extinction_generation=max(gens),
                   median_extinction_generation=float(np.median(gens)),
                   pass_=bool(abs(f300.d_star - f150.d_star) < TOL and late / len(rows) <= 0.01))

    # Extinction timing and which species, pooled L30.
    all_rows = [r for s in seeds for r in read_runs_csv(STUDIES / f"L30_s{s}.runs.csv")]
    ext = [r for r in all_rows if r["extinct"]]
    R["timing"] = dict(
        runs=len(all_rows), extinct=len(ext),
        predator_only=sum(r["predator_extinct"] and not r["prey_extinct"] for r in ext),
        prey_only=sum(r["prey_extinct"] and not r["predator_extinct"] for r in ext),
        both=sum(r["prey_extinct"] and r["predator_extinct"] for r in ext),
        median_generation=float(np.median([r["extinction_generation"] for r in ext])),
        p95_generation=float(np.percentile([r["extinction_generation"] for r in ext], 95)),
        max_generation=max(r["extinction_generation"] for r in ext),
    )

    # ---- E8: old (hash) vs new (SeedSequence) seeding -----------------------
    from scipy.stats import fisher_exact
    old = list(csv.DictReader(open(REPO / "evidence/validation/baseline_sweep_results.csv")))
    xo = np.array([float(r["predator_density"]) for r in old])
    yo = np.array([int(r["outcome"] != "coexistence") for r in old])
    _, xn, yn = load("hs3design_s4041")
    xn = np.round(xn, 2)
    fo = fit_threshold(xo, yo, n_boot=1000, seed=1)
    fn = fit_threshold(xn, yn, n_boot=1000, seed=2)
    fits["E8_old"], fits["E8_new"] = fo, fn
    rows8, sig = [], 0
    for d in np.unique(xo):
        ko, no = int(yo[xo == d].sum()), int((xo == d).sum())
        kn, nn = int(yn[xn == d].sum()), int((xn == d).sum())
        p = fisher_exact([[ko, no - ko], [kn, nn - kn]])[1]
        sig += p < 0.05
        rows8.append(dict(density=float(d), old=f"{ko}/{no}", new=f"{kn}/{nn}", fisher_p=float(p)))
    overlap = fo.ci_boot and fn.ci_boot and fo.ci_boot[0] <= fn.ci_boot[1] and fn.ci_boot[0] <= fo.ci_boot[1]
    R["E8"] = dict(levels=rows8, significant_levels=int(sig), old=summarise(fo), new=summarise(fn),
                   intervals_overlap=bool(overlap), pass_=bool(sig <= 2 and overlap))

    dump(EVIDENCE / "hs4_results.json", R)
    figures(R, fits, X, Y, all_rows)
    write_manifest(EVIDENCE / "hs4_results.json", script="validation/hs4_analyze.py",
                   wall_seconds=time.perf_counter() - t0, params={"tolerance": TOL, "bootstrap": 1000})
    for k in ("E3", "E4", "E5", "E6", "E7", "E8"):
        print(k, "PASS" if R[k]["pass_"] else "FAIL")


def figures(R, fits, X, Y, all_rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Fig 1: pooled curve with Wilson intervals, logistic fit and d* band.
    lv = R["E4"]["pooled_levels"]
    pooled = fits["L30_pooled"]
    fig, ax = plt.subplots(figsize=(7, 4))
    xs = np.array([l["density"] for l in lv])
    ax.errorbar(xs, [l["p"] for l in lv],
                yerr=[[max(0.0, l["p"] - l["lo"]) for l in lv], [max(0.0, l["hi"] - l["p"]) for l in lv]],
                fmt="o", color="#1f4e79", capsize=3, label="observed, Wilson 95% (n = 150 per level)")
    g = np.linspace(xs.min(), xs.max(), 200)
    ax.plot(g, 1 / (1 + np.exp(-(pooled.intercept + pooled.slope * g))), color="#c8553d", label="logistic fit")
    ax.axvspan(*pooled.ci_boot, color="#c8553d", alpha=0.15, label=f"d* = {pooled.d_star:.3f}, 95% CI")
    ax.axhline(0.5, color="grey", lw=0.6, ls=":")
    ax.set_xlabel("initial predator density")
    ax.set_ylabel("P(extinction by generation 150)")
    ax.set_title("E3/E4: pooled 30×30 studies (5 master seeds, 2,700 runs)")
    ax.legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIG / "fig_e4_pooled_curve.png", dpi=150)
    plt.close(fig)

    # Fig 2: precision vs replicate count.
    e3 = [r for r in R["E3"]["by_n"] if r["half_width_median"] is not None]
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    ax.plot([r["n"] for r in e3], [r["half_width_median"] for r in e3], "o-", color="#1f4e79",
            label="median bootstrap 95% half-width of d*")
    ax.axhline(TOL, color="#c8553d", ls="--", label=f"pre-set target ({TOL})")
    for r in R["E3"]["by_n"]:
        if r["fit_failures"]:
            ax.annotate(f"{r['fit_failures']}/{r['draws']} fits failed", (r["n"], TOL * 1.1),
                        fontsize=7, rotation=90, va="bottom", ha="center", color="#7a3b2e")
    ax.set_xscale("log")
    ax.set_xlabel("replicates per density level (18 levels)")
    ax.set_ylabel("half-width (density units)")
    ax.set_title("E3: threshold precision vs replicate count")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "fig_e3_precision.png", dpi=150)
    plt.close(fig)

    # Fig 3: forest plot of d* across conditions.
    rows = [(f"seed {s}", f"L30_s{s}") for s in range(4001, 4006)]
    rows += [("pooled L30", "L30_pooled")]
    rows += [(f"L = {L}", f"L{L}") for L in (20, 40, 50)]
    rows += [("repro 0.05", "r0.05"), ("repro 0.30", "r0.3")]
    rows += [("horizon 150 (paired)", "H150"), ("horizon 300", "H300")]
    rows += [("HS3 design, old seeds", "E8_old"), ("HS3 design, new seeds", "E8_new")]
    mf = R["model_free"]["estimates"]
    fig, ax = plt.subplots(figsize=(7, 5.6))
    for k, (lab, key) in enumerate(rows):
        y = len(rows) - k
        f = fits[key]
        if f.d_star is None:
            continue
        ax.plot(f.ci_boot, [y, y], color="#1f4e79")
        ax.plot(f.d_star, y, "o", color="#c8553d" if "pooled" in lab else "#1f4e79",
                label="logistic d*, bootstrap 95% CI" if k == 0 else None)
        if key in mf:
            m = mf[key]
            ax.plot(m["ci"], [y - 0.3, y - 0.3], color="#888", lw=1)
            ax.plot(m["d_star"], y - 0.3, "o", mfc="white", mec="#555",
                    label="model-free crossing (post-hoc)" if k == 0 else None)
    ax.axvspan(fits["L30_pooled"].d_star - TOL, fits["L30_pooled"].d_star + TOL, color="#e0a526", alpha=0.2,
               label=f"pooled d* ± {TOL} (pre-set tolerance)")
    ax.set_yticks(range(len(rows), 0, -1), [r[0] for r in rows], fontsize=8)
    ax.set_xlabel("d* (initial predator density at P = 0.5), 95% CI")
    ax.set_title("E4–E8: d* across seeds, sizes, settings, horizon, seeding")
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(FIG / "fig_e4_e8_forest.png", dpi=150)
    plt.close(fig)

    # Fig 4: extinction timing (ECDF), pooled L30 and the 300-generation study.
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    g = sorted(r["extinction_generation"] for r in all_rows if r["extinct"])
    ax.step(g, np.arange(1, len(g) + 1) / len(g), where="post", label=f"L30 pooled ({len(g)} extinctions)")
    h = sorted(r["extinction_generation"] for r in read_runs_csv(STUDIES / "H300_s4031.runs.csv") if r["extinct"])
    ax.step(h, np.arange(1, len(h) + 1) / len(h), where="post", label=f"300-generation study ({len(h)})")
    ax.axvline(150, color="grey", ls=":", lw=0.8)
    ax.set_xlabel("generation of extinction")
    ax.set_ylabel("cumulative fraction of extinctions")
    ax.set_title("E7: when do extinctions happen?")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "fig_e7_timing.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
