"""Analyse the RU-09 questions (evidence/ru09/ANALYSIS_PLAN.md).

    python validation/ru09_analyze.py

Reads evidence/hs4/studies/ and evidence/ru09/studies/, writes
evidence/ru09/ru09_results.json. Figures: validation/ru09_figures.py.
Production code is not changed; link functions other than the logit live here
until the estimator decision (HS4 D3) is taken.
"""

from __future__ import annotations

import csv
import json
import math
import time

import numpy as np
from scipy.stats import chi2, norm

import hs4_analyze
from hs4_analyze import crossing
from hs4_common import EVIDENCE as HS4, REPO, dump, read_runs_csv, write_manifest

from ppets.analysis import fit_threshold, wilson_interval

OUT = REPO / "evidence" / "ru09"
HS4_STUDIES = HS4 / "studies"
NEW = OUT / "studies"
LN2 = math.log(2)

LINKS = {
    "logit": dict(cdf=lambda e: 1 / (1 + np.exp(-e)), pdf=lambda e: np.exp(-e) / (1 + np.exp(-e)) ** 2, eta50=0.0),
    "probit": dict(cdf=norm.cdf, pdf=norm.pdf, eta50=0.0),
    # cloglog approaches 1 quickly and 0 slowly; loglog is its mirror image.
    "cloglog": dict(cdf=lambda e: 1 - np.exp(-np.exp(e)), pdf=lambda e: np.exp(e - np.exp(e)), eta50=math.log(LN2)),
    "loglog": dict(cdf=lambda e: np.exp(-np.exp(-e)), pdf=lambda e: np.exp(-e - np.exp(-e)), eta50=-math.log(LN2)),
}


def glm(x, k, n, link, max_iter=200):
    """Binomial GLM on grouped counts by Fisher scoring. Returns (b0, b1) or None."""
    L = LINKS[link]
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


def d_star(b, link):
    return (LINKS[link]["eta50"] - b[0]) / b[1]


def prob(b, x, link):
    return np.clip(LINKS[link]["cdf"](np.clip(b[0] + b[1] * x, -30, 30)), 1e-10, 1 - 1e-10)


def pearson(x, k, n, b, link):
    pf = prob(b, x, link)
    return float(np.sum((k - n * pf) ** 2 / (n * pf * (1 - pf))))


def logloss(x, k, n, b, link):
    pf = prob(b, x, link)
    return float(-np.sum(k * np.log(pf) + (n - k) * np.log(1 - pf)) / n.sum())


def grouped(rows, key=lambda r: r["extinct"]):
    lv = sorted({round(r["a_value"], 6) for r in rows})
    n = np.array([sum(1 for r in rows if round(r["a_value"], 6) == l) for l in lv], dtype=float)
    k = np.array([sum(1 for r in rows if round(r["a_value"], 6) == l and key(r)) for l in lv], dtype=float)
    return np.array(lv), k, n


def crossing_grouped(x, k, n):
    """hs4_analyze.crossing on grouped counts (same isotonic rule, expanded to runs)."""
    xx = np.repeat(x, n.astype(int))
    yy = np.concatenate([np.r_[np.ones(int(a)), np.zeros(int(b - a))] for a, b in zip(k, n)])
    return crossing(xx, yy)


def boot_counts(rng, k, n):
    return rng.binomial(n.astype(int), k / n).astype(float)


def estimate(x, k, n, seed, links=("logit", "loglog"), n_boot=1000):
    """Point estimates and stratified-bootstrap intervals, plus the replicate draws."""
    rng = np.random.default_rng(seed)
    out, draws = {}, {m: [] for m in (*links, "model_free")}
    fits = {m: glm(x, k, n, m) for m in links}
    for _ in range(n_boot):
        kb = boot_counts(rng, k, n)
        for m in links:
            b = glm(x, kb, n, m)
            if b is not None and b[1] > 0:
                draws[m].append(d_star(b, m))
        c = crossing_grouped(x, kb, n)
        if c is not None:
            draws["model_free"].append(c)
    for m in links:
        out[m] = dict(d_star=d_star(fits[m], m), slope=fits[m][1], chi2=pearson(x, k, n, fits[m], m),
                      p=float(chi2.sf(pearson(x, k, n, fits[m], m), len(x) - 2)),
                      ci=[float(np.percentile(draws[m], q)) for q in (2.5, 97.5)], boot_valid=len(draws[m]))
    out["model_free"] = dict(d_star=crossing_grouped(x, k, n),
                             ci=[float(np.percentile(draws["model_free"], q)) for q in (2.5, 97.5)],
                             boot_valid=len(draws["model_free"]))
    return out, {m: np.array(v) for m, v in draws.items()}


def study(name):
    for folder in (NEW, HS4_STUDIES):
        p = folder / f"{name}.runs.csv"
        if p.exists():
            return read_runs_csv(p)
    return None


def parametric_gof_p(x, n, b, link, observed, rng, draws=1000):
    """Goodness-of-fit p by parametric bootstrap: sparse tails make chi-square rough."""
    hits, valid = 0, 0
    pf = prob(b, x, link)
    for _ in range(draws):
        ks = rng.binomial(n.astype(int), pf).astype(float)
        bs = glm(x, ks, n, link)
        if bs is None:
            continue
        valid += 1
        hits += pearson(x, ks, n, bs, link) >= observed
    return (hits + 1) / (valid + 1)


def q2(R):
    seeds = range(4001, 4006)
    per = {s: study(f"L30_s{s}") for s in seeds}
    rows = [r for s in seeds for r in per[s]]
    x, k, n = grouped(rows)
    # Hold-out: 540 independent runs, outcome taken at generation 150.
    hx, hk, hn = grouped(study("H300_s4031"),
                         key=lambda r: r["extinct"] and r["extinction_generation"] <= 150)
    rng = np.random.default_rng(909)
    mf = crossing_grouped(x, k, n)
    table = {}
    for m in LINKS:
        b = glm(x, k, n, m)
        c = pearson(x, k, n, b, m)
        loso = []
        for s in seeds:
            tr = [r for t in seeds if t != s for r in per[t]]
            tx, tk, tn = grouped(tr)
            vx, vk, vn = grouped(per[s])
            loso.append(logloss(vx, vk, vn, glm(tx, tk, tn, m), m))
        table[m] = dict(d_star=d_star(b, m), slope=b[1], intercept=b[0], chi2=c, df=len(x) - 2,
                        p_chi2=float(chi2.sf(c, len(x) - 2)),
                        p_parametric=parametric_gof_p(x, n, b, m, c, rng),
                        holdout_logloss=logloss(hx, hk, hn, b, m), loso_logloss=float(np.mean(loso)),
                        diff_from_model_free=abs(d_star(b, m) - mf),
                        d3_met=bool(chi2.sf(c, len(x) - 2) > 0.05 and abs(d_star(b, m) - mf) <= 0.005))
    chk = fit_threshold(np.repeat(x, n.astype(int)),
                        np.concatenate([np.r_[np.ones(int(a)), np.zeros(int(c_ - a))] for a, c_ in zip(k, n)]), n_boot=0)
    best = min(LINKS, key=lambda m: table[m]["chi2"])
    # Sensitivity of the holdout comparison: per-level expected counts per link.
    curve = [dict(density=float(xx), k=int(kk), n=int(nn), **{m: float(prob(glm(x, k, n, m), np.array([xx]), m)[0] * nn)
                                                               for m in LINKS})
             for xx, kk, nn in zip(x, k, n)]
    # Post-hoc: the loglog chi-square is unusually small, so test the fitted curves
    # on data they never saw, without refitting (df = levels, nothing estimated).
    frozen = {}
    for m in LINKS:
        b = glm(x, k, n, m)
        c = pearson(hx, hk, hn, b, m)
        frozen[m] = dict(chi2=c, df=len(hx), p=float(chi2.sf(c, len(hx))))
    # Lower-tail probability of the observed fit under a correct model.
    b = glm(x, k, n, "loglog")
    sims = []
    for _ in range(2000):
        ks = rng.binomial(n.astype(int), prob(b, x, "loglog")).astype(float)
        sims.append(pearson(x, ks, n, glm(x, ks, n, "loglog"), "loglog"))
    too_good = (np.sum(np.array(sims) <= table["loglog"]["chi2"]) + 1) / (len(sims) + 1)
    R["Q2"] = dict(links=table, best_by_chi2=best, model_free=mf,
                   logit_matches_production=abs(table["logit"]["d_star"] - chk.d_star) < 1e-6,
                   holdout_study="H300_s4031", curve=curve, frozen_on_holdout=frozen,
                   loglog_lower_tail_p=float(too_good),
                   holdout_counts=[dict(density=float(a), k=int(b_), n=int(c_)) for a, b_, c_ in zip(hx, hk, hn)])
    return x, n, best


def q2b(R, x, best):
    b = (R["Q2"]["links"][best]["intercept"], R["Q2"]["links"][best]["slope"])
    truth = d_star(b, best)
    pf = prob(b, x, best)
    rng = np.random.default_rng(910)
    res = {}
    for reps in (30, 150):
        n = np.full_like(x, reps, dtype=float)
        rows = {m: dict(hit=0, width=[], est=[]) for m in ("logit", "model_free", best)}
        for _ in range(200):
            k = rng.binomial(reps, pf).astype(float)
            for m in rows:
                pts = []
                est = crossing_grouped(x, k, n) if m == "model_free" else None
                if m != "model_free":
                    bb = glm(x, k, n, m)
                    est = d_star(bb, m) if bb else None
                for _ in range(200):
                    kb = boot_counts(rng, k, n)
                    if m == "model_free":
                        c = crossing_grouped(x, kb, n)
                    else:
                        bb = glm(x, kb, n, m)
                        c = d_star(bb, m) if bb and bb[1] > 0 else None
                    if c is not None:
                        pts.append(c)
                if est is None or len(pts) < 100:
                    continue
                lo, hi = np.percentile(pts, [2.5, 97.5])
                rows[m]["hit"] += lo <= truth <= hi
                rows[m]["width"].append(hi - lo)
                rows[m]["est"].append(est)
        res[reps] = {m: dict(coverage=v["hit"] / 200, bias=float(np.mean(v["est"]) - truth),
                             rmse=float(np.sqrt(np.mean((np.array(v["est"]) - truth) ** 2))),
                             half_width=float(np.mean(v["width"]) / 2)) for m, v in rows.items()}
    R["Q2b"] = dict(truth_link=best, truth_d_star=truth, simulations=200, boot_per_sim=200, results=res,
                    note="Coverage is conditional on the fitted best link being the true curve.")


def pooled_by_size():
    """Every study at the default repro rate, grouped by grid size."""
    groups = {20: ["L20_s4011"], 30: [f"L30_s{s}" for s in range(4001, 4006)],
              40: ["L40_s4012"], 50: ["L50_s4013", "L50_s4016"],
              75: ["L75_s4014", "L75_s4017"], 100: ["L100_s4015"]}
    out = {}
    for L, names in groups.items():
        rows = [r for nm in names if (s := study(nm)) for r in s]
        if rows:
            out[L] = (rows, [nm for nm in names if study(nm)])
    return out


def q1(R):
    sizes = pooled_by_size()
    res, draws = {}, {}
    for L, (rows, names) in sizes.items():
        x, k, n = grouped(rows)
        est, dr = estimate(x, k, n, seed=1000 + L)
        res[L] = dict(studies=names, runs=len(rows), **est,
                      p_at_max_density=float(k[-1] / n[-1]), width_10_90_logit=2 * math.log(9) / est["logit"]["slope"])
        draws[L] = dr
    out = dict(sizes=res)
    if 50 in draws and 75 in draws and len(sizes[50][1]) == 2 and len(sizes[75][1]) == 2:
        comp = {}
        for m in ("logit", "loglog", "model_free"):
            size = min(len(draws[50][m]), len(draws[75][m]))
            d = draws[75][m][:size] - draws[50][m][:size]
            diff = res[75][m]["d_star"] - res[50][m]["d_star"]
            ci = [float(np.percentile(d, q)) for q in (2.5, 97.5)]
            spans = ci[0] < 0.01 <= ci[1] or ci[0] < -0.01 <= ci[1]
            comp[m] = dict(diff=diff, ci=ci,
                           verdict="not resolved" if spans else ("converged" if abs(diff) < 0.01 else "not converged"))
        out["D1_75_vs_50"] = comp
    frozen = dict(a=0.3396540394823453, b=-2.644556258189115)
    out["frozen_1_over_L"] = {}
    for L in (75, 100):
        if L in res:
            pred = frozen["a"] + frozen["b"] / L
            ci = res[L]["logit"]["ci"]
            out["frozen_1_over_L"][L] = dict(predicted=pred, measured=res[L]["logit"]["d_star"], ci=ci,
                                             inside=bool(ci[0] <= pred <= ci[1]))
    # Per-seed agreement at sizes with two studies (between-seed spread beyond L = 30).
    out["two_seed_checks"] = {}
    for L in (50, 75):
        names = sizes.get(L, (None, []))[1]
        if len(names) == 2:
            vals = {}
            for nm in names:
                x, k, n = grouped(study(nm))
                b = glm(x, k, n, "logit")
                vals[nm] = d_star(b, "logit")
            out["two_seed_checks"][L] = vals
    R["Q1"] = out


def q3(R):
    groups = {f"L{L}": rows for L, (rows, _) in pooled_by_size().items()}
    groups["repro 0.05"] = study("r05_s4021")
    groups["repro 0.30"] = study("r30_s4022")
    res = {}
    for name, rows in groups.items():
        ext = [r for r in rows if r["extinct"]]
        pred = [r for r in ext if r["predator_extinct"]]
        prey = [r for r in ext if r["prey_extinct"]]
        per_level = []
        for lv in sorted({round(r["a_value"], 6) for r in rows}):
            at = [r for r in rows if round(r["a_value"], 6) == lv]
            per_level.append(dict(density=lv, n=len(at), predator_first=sum(r["predator_extinct"] for r in at),
                                  prey_first=sum(r["prey_extinct"] for r in at)))
        res[name] = dict(
            runs=len(rows), extinct=len(ext), predator_first=len(pred), prey_first=len(prey),
            both_same_step=sum(r["prey_extinct"] and r["predator_extinct"] for r in ext),
            prey_share=len(prey) / len(ext) if ext else None,
            prey_share_ci=list(wilson_interval(len(prey), len(ext))) if ext else None,
            median_gen_predator=float(np.median([r["extinction_generation"] for r in pred])) if pred else None,
            median_gen_prey=float(np.median([r["extinction_generation"] for r in prey])) if prey else None,
            max_gen=max(r["extinction_generation"] for r in ext) if ext else None,
            extinct_after_gen_75=sum(r["extinction_generation"] > 75 for r in ext),
            extinct_after_gen_100=sum(r["extinction_generation"] > 100 for r in ext),
            per_level=per_level,
        )
        # Pathway-specific d*: density where each pathway alone reaches 0.5, if it does.
        x, kp, n = grouped(rows, key=lambda r: r["predator_extinct"])
        res[name]["predator_only_crossing"] = crossing_grouped(x, kp, n)
        x, kq, n = grouped(rows, key=lambda r: r["prey_extinct"])
        res[name]["prey_only_crossing"] = crossing_grouped(x, kq, n)
    R["Q3"] = res


def q4(R):
    p = NEW / "trajectory_s4050.csv"
    rows = list(csv.DictReader(p.open(encoding="utf-8")))
    cells = {}
    for r in rows:
        cells.setdefault((int(r["size"]), float(r["density"])), []).append(r)
    table = []
    for (L, d), rs in sorted(cells.items()):
        trough = np.array([int(r["min_predators"]) / L ** 2 for r in rs])
        tprey = np.array([int(r["min_prey"]) / L ** 2 for r in rs])
        k = sum(r["extinct"] == "True" for r in rs)
        table.append(dict(size=L, density=d, n=len(rs), p_extinct=k / len(rs),
                          wilson=list(wilson_interval(k, len(rs))),
                          trough_mean=float(trough.mean()), trough_sd=float(trough.std(ddof=1)),
                          trough_count_mean=float(np.mean([int(r["min_predators"]) for r in rs])),
                          prey_trough_mean=float(tprey.mean()), prey_trough_sd=float(tprey.std(ddof=1)),
                          trough_generation_median=float(np.median([int(r["generation_of_min_predators"]) for r in rs])),
                          prey_first=sum(r["prey_extinct"] == "True" for r in rs),
                          predator_first=sum(r["predator_extinct"] == "True" for r in rs)))
    sizes = sorted({t["size"] for t in table})
    dens = sorted({t["density"] for t in table})
    get = lambda L, d: next(t for t in table if t["size"] == L and t["density"] == d)
    sd_falls = {d: all(get(a, d)["trough_sd"] > get(b, d)["trough_sd"] for a, b in zip(sizes, sizes[1:])) for d in dens}
    p_falls = {d: get(sizes[0], d)["p_extinct"] > get(sizes[-1], d)["p_extinct"] for d in (0.25, 0.30)}
    R["Q4"] = dict(table=table, sd_falls_each_step=sd_falls, p_extinct_falls=p_falls,
                   supported=bool(all(sd_falls.values()) and all(p_falls.values())))


def q5(R):
    ref = R["Q2"]["links"]["logit"]["d_star"]
    settings = {f"L = {L}": rows for L, (rows, _) in pooled_by_size().items()}
    settings["repro 0.05"] = study("r05_s4021")
    settings["repro 0.30"] = study("r30_s4022")
    settings["hold-out L = 30"] = study("H300_s4031")
    res = {}
    for name, rows in settings.items():
        x, k, n = grouped(rows)
        tp = int(k[x >= ref].sum())
        fp = int((n - k)[x >= ref].sum())
        fn = int(k[x < ref].sum())
        tn = int((n - k)[x < ref].sum())
        errs = [(float(k[x < t].sum() + (n - k)[x >= t].sum()) / n.sum()) for t in x]
        res[name] = dict(tp=tp, fp=fp, fn=fn, tn=tn, error=(fp + fn) / n.sum(), best_own_error=min(errs),
                         best_own_cut=float(x[int(np.argmin(errs))]), excess=(fp + fn) / n.sum() - min(errs))
    R["Q5"] = dict(rule_d_star=ref, settings=res,
                   note="Own best rule is chosen on the same data, so it is optimistic. Error rates depend on the swept range.")


def q6(R):
    total, zero = 0, 0
    names = [p.name for folder in (HS4_STUDIES, NEW) for p in folder.glob("*.runs.csv")]
    for f in (HS4_STUDIES, NEW):
        for p in f.glob("*.runs.csv"):
            rows = read_runs_csv(p)
            total += len(rows)
            zero += sum(r["extinction_generation"] == 0 for r in rows)
    R["Q6"] = dict(studies=len(names), runs=total, extinct_at_generation_0=zero)


def q7(R):
    """Spatial-refuge scaling: every prediction comes from the pooled L = 30 fit alone."""
    L30 = R["Q2"]["links"]["loglog"]
    d30, b1 = L30["d_star"], L30["slope"]
    predict = lambda L: d30 + 2 * math.log(L / 30) / b1
    rng = np.random.default_rng(911)
    table = {}
    for L, (rows, _) in pooled_by_size().items():
        x, k, n = grouped(rows)
        q = R["Q1"]["sizes"][str(L)] if str(L) in R["Q1"]["sizes"] else R["Q1"]["sizes"][L]
        pred = predict(L)
        b = (-b1 * pred - math.log(LN2), b1)  # curve frozen from L = 30, nothing fitted here
        pf = prob(b, x, "loglog")
        obs = pearson(x, k, n, b, "loglog")
        sims = [pearson(x, rng.binomial(n.astype(int), pf).astype(float), n, b, "loglog") for _ in range(2000)]
        # Parametric lower/upper tail for the size's own fit (sparse tails break chi-square).
        own = glm(x, k, n, "loglog")
        own_chi = pearson(x, k, n, own, "loglog")
        sims_own = []
        for _ in range(500):
            ks = rng.binomial(n.astype(int), prob(own, x, "loglog")).astype(float)
            bs = glm(x, ks, n, "loglog")
            if bs is not None:
                sims_own.append(pearson(x, ks, n, bs, "loglog"))
        table[L] = dict(predicted=pred, measured=q["loglog"]["d_star"], ci=q["loglog"]["ci"],
                        inside=bool(q["loglog"]["ci"][0] <= pred <= q["loglog"]["ci"][1]),
                        slope=q["loglog"]["slope"], frozen_chi2=obs, frozen_mc_p=(np.sum(np.array(sims) >= obs) + 1) / 2001,
                        own_fit_upper_p=(np.sum(np.array(sims_own) >= own_chi) + 1) / (len(sims_own) + 1))
    Ls = np.array(sorted(table), dtype=float)
    ds = np.array([table[int(L)]["measured"] for L in Ls])
    c, a = np.polyfit(np.log(Ls), ds, 1)
    b_inv, a_inv = np.polyfit(1 / Ls, ds, 1)
    out = dict(table=table, slope_from_L30=b1, ln_coefficient_predicted=2 / b1,
               ln_coefficient_fitted=float(c), rss_ln=float(np.sum((ds - (a + c * np.log(Ls))) ** 2)),
               rss_inverse=float(np.sum((ds - (a_inv + b_inv / Ls)) ** 2)), note="Post-hoc apart from L = 150.")
    rows = study("L150_s4018")
    if rows:
        x, k, n = grouped(rows)
        rng2 = np.random.default_rng(4018)
        fit = glm(x, k, n, "loglog")
        ds_, sl = [], []
        for _ in range(1000):
            bb = glm(x, boot_counts(rng2, k, n), n, "loglog")
            if bb is not None and bb[1] > 0:
                ds_.append(d_star(bb, "loglog"))
                sl.append(bb[1])
        cid = [float(np.percentile(ds_, q)) for q in (2.5, 97.5)]
        cis = [float(np.percentile(sl, q)) for q in (2.5, 97.5)]
        pred = predict(150)
        est, _ = estimate(x, k, n, seed=1150)
        out["prospective_L150"] = dict(
            runs=len(rows), predicted=pred, measured=d_star(fit, "loglog"), ci=cid, slope=fit[1], slope_ci=cis,
            predicted_slope=b1, supported=bool(cid[0] <= pred <= cid[1] and cis[0] <= b1 <= cis[1]),
            competing_1_over_L=0.3396540394823453 - 2.644556258189115 / 150, logit=est["logit"], model_free=est["model_free"],
            levels=[dict(density=float(a_), k=int(b_), n=int(c_)) for a_, b_, c_ in zip(x, k, n)],
            max_generation=max((r["extinction_generation"] for r in rows if r["extinct"]), default=None),
            prey_first=sum(r["prey_extinct"] for r in rows), predator_first=sum(r["predator_extinct"] for r in rows))
    R["Q7"] = out


def compute_cost(R):
    rows = []
    for f in (HS4_STUDIES, NEW):
        for p in f.glob("*.manifest.json"):
            m = json.loads(p.read_text(encoding="utf-8"))
            rows.append(dict(file=m["output"], wall_seconds=m["wall_seconds"], workers=m["params"].get("workers"),
                             runs=m["params"].get("runs")))
    wall = sum(r["wall_seconds"] for r in rows)
    R["cost"] = dict(studies=len(rows), wall_seconds=wall, runs=sum(r["runs"] or 0 for r in rows),
                     assumed_system_watts=65,
                     estimated_kwh=wall / 3600 * 65 / 1000,
                     note="Wall time is measured; 65 W system draw under load is an assumption, not a measurement.")


def main():
    t0 = time.perf_counter()
    R = {"generated_by": "validation/ru09_analyze.py", "plan": "evidence/ru09/ANALYSIS_PLAN.md"}
    x, n, best = q2(R)
    print("Q2", json.dumps({m: {k: round(v, 4) if isinstance(v, float) else v for k, v in d.items()}
                            for m, d in R["Q2"]["links"].items()}), "mf", R["Q2"]["model_free"], flush=True)
    q1(R)
    q3(R)
    q4(R)
    q5(R)
    q6(R)
    q7(R)
    compute_cost(R)
    q2b(R, x, best)
    dump(OUT / "ru09_results.json", R)
    write_manifest(OUT / "ru09_results.json", script="validation/ru09_analyze.py",
                   wall_seconds=time.perf_counter() - t0, params={"bootstrap": 1000, "seed_base": [909, 910, 1000]})
    print("done", round(time.perf_counter() - t0), "s")


if __name__ == "__main__":
    main()
