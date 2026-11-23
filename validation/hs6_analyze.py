"""Analyse the HS6 / RU-12 final tests (evidence/hs6/ANALYSIS_PLAN.md, F1-F4).

    python validation/hs6_analyze.py

Reads evidence/hs4/studies/, evidence/ru09/studies/ and evidence/hs6/studies/,
writes evidence/hs6/hs6_results.json. Every estimate comes from the production
code (ppets.analysis), not from a copy in this script.
"""

from __future__ import annotations

import math
import multiprocessing as mp
import time

import numpy as np

from hs4_common import EVIDENCE as HS4, REPO, WORKERS, dump, read_runs_csv, write_manifest

from ppets.analysis import (estimate_threshold, fit_link, group_counts, link_d_star, link_prob, model_free_d_star,
                            pava, pathway_table, wilson_interval)

OUT = REPO / "evidence" / "hs6"
FOLDERS = (HS4 / "studies", REPO / "evidence" / "ru09" / "studies", OUT / "studies")
L30 = [f"L30_s{s}" for s in range(4001, 4006)]


def study(name):
    for f in FOLDERS:
        p = f / f"{name}.runs.csv"
        if p.exists():
            return read_runs_csv(p)
    raise FileNotFoundError(name)


def rows_of(names):
    return [r for nm in names for r in study(nm)]


def xy(rows):
    return [r["a_value"] for r in rows], [int(r["extinct"]) for r in rows]


def est_dict(e):
    return {m: dict(status=v.status, d_star=v.d_star, ci=list(v.ci) if v.ci else None, boot_valid=v.boot_valid,
                    slope=v.slope) for m, v in e.items()}


# ---- F1: spatial vs well-mixed ------------------------------------------------------

def draws(x, y, method, n_boot, seed):
    lv, k, n = group_counts(x, y)
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n_boot):
        kb = rng.binomial(n.astype(int), k / n).astype(float)
        if method == "model_free":
            c = model_free_d_star(lv, kb, n)
        else:
            b = fit_link(lv, kb, n, method)
            c = link_d_star(b, method) if b is not None and b[1] > 0 else None
        out.append(c)
    return np.array([np.nan if c is None else c for c in out])


def f1(R):
    groups = {
        30: dict(spatial=L30, well_mixed=["WM30_s4001", "WM30_s4002"], low="WMlow30_s4061"),
        75: dict(spatial=["L75_s4014", "L75_s4017"], well_mixed=["WM75_s4014"], low="WMlow75_s4062"),
    }
    res = {}
    for L, g in groups.items():
        sp = rows_of(g["spatial"])
        wm = rows_of(g["well_mixed"])
        low = study(g["low"])
        wm_all = wm + low
        e_sp = estimate_threshold(*xy(sp), seed=1000 + L)
        e_wm = estimate_threshold(*xy(wm_all), seed=2000 + L)
        lv, k, n = group_counts(*xy(wm_all))
        lv0, k0, n0 = group_counts(*xy([r for r in wm_all if r["extinction_generation"] != 0]))
        levels = [dict(density=float(a), n=int(c), extinct=int(b), p=float(b / c), wilson=list(wilson_interval(int(b), int(c))))
                  for a, b, c in zip(lv, k, n)]
        all_ext = bool(np.all(k == n))
        # Plan F1: if P(extinct) never falls to 0.5 in the tested range there is no crossing.
        no_crossing = bool(np.all(k / n > 0.5))
        entry = dict(spatial_studies=g["spatial"], well_mixed_studies=g["well_mixed"] + [g["low"]],
                     spatial_runs=len(sp), well_mixed_runs=len(wm_all), spatial=est_dict(e_sp), well_mixed=est_dict(e_wm),
                     well_mixed_levels=levels, well_mixed_all_extinct=all_ext, well_mixed_no_crossing=no_crossing,
                     well_mixed_survivors=int((n - k).sum()), well_mixed_min_p=float((k / n).min()),
                     well_mixed_extinct_at_generation_0=sum(r["extinction_generation"] == 0 for r in wm_all),
                     well_mixed_all_extinct_excluding_generation_0=bool(np.all(k0 == n0)),
                     well_mixed_lowest_density=float(lv.min()),
                     well_mixed_max_extinction_generation=max(r["extinction_generation"] for r in wm_all if r["extinct"]),
                     well_mixed_median_extinction_generation=float(np.median([r["extinction_generation"] for r in wm_all if r["extinct"]])),
                     well_mixed_prey_first=sum(r["prey_extinct"] and not r["predator_extinct"] for r in wm_all),
                     well_mixed_predator_first=sum(r["predator_extinct"] and not r["prey_extinct"] for r in wm_all))
        if no_crossing:
            # No crossing in range: d*_wm < lowest density, so the difference is bounded below.
            for m in ("loglog", "model_free"):
                entry[f"difference_{m}"] = dict(kind="lower bound", value=e_sp[m].d_star - float(lv.min()),
                                                ci_low_bound=e_sp[m].ci[0] - float(lv.min()),
                                                text=f"d*_spatial - d*_well_mixed > {e_sp[m].d_star - float(lv.min()):.3f}")
        else:
            for m in ("loglog", "model_free"):
                a = draws(*xy(sp), m, 1000, 3000 + L)
                b = draws(*xy(wm_all), m, 1000, 4000 + L)
                d = a - b
                d = d[~np.isnan(d)]
                entry[f"difference_{m}"] = dict(kind="estimate", value=(e_sp[m].d_star or np.nan) - (e_wm[m].d_star or np.nan),
                                                ci=[float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))], draws=len(d))
        # Paired twins: same master seed, density and replicate => same initial grid.
        pairs = []
        for nm in g["well_mixed"]:
            twin = nm.replace("WM", "L")
            sp_rows = {(round(r["a_value"], 6), r["replicate"]): r for r in study(twin)}
            for r in study(nm):
                s = sp_rows[(round(r["a_value"], 6), r["replicate"])]
                assert s["seed"] == r["seed"], "twins must share seeds"
                pairs.append((s["extinct"], r["extinct"]))
        sp_surv = [p for p in pairs if not p[0]]
        entry["paired"] = dict(pairs=len(pairs), spatial_survived=len(sp_surv),
                               of_those_well_mixed_extinct=sum(p[1] for p in sp_surv),
                               spatial_extinct_well_mixed_survived=sum(p[0] and not p[1] for p in pairs))
        res[L] = entry
    R["F1"] = res


# ---- F2: coverage when log-log is not the truth ---------------------------------------

def _f2_sim(job):
    truth_name, x, p_true, d_true, reps, sim, seed = job
    rng = np.random.default_rng([seed, sim])
    n = np.full_like(x, reps, dtype=float)
    k = rng.binomial(reps, p_true).astype(float)
    out = {}
    for m in ("loglog", "logit", "model_free"):
        if m == "model_free":
            est = model_free_d_star(x, k, n)
        else:
            b = fit_link(x, k, n, m)
            est = link_d_star(b, m) if b is not None and b[1] > 0 else None
        pts = []
        for _ in range(200):
            kb = rng.binomial(n.astype(int), k / n).astype(float)
            if m == "model_free":
                c = model_free_d_star(x, kb, n)
            else:
                bb = fit_link(x, kb, n, m)
                c = link_d_star(bb, m) if bb is not None and bb[1] > 0 else None
            if c is not None:
                pts.append(c)
        if est is None or len(pts) < 100:
            out[m] = None
        else:
            lo, hi = np.percentile(pts, [2.5, 97.5])
            out[m] = (est, lo, hi)
    return truth_name, reps, out


def f2(R):
    x, k, n = group_counts(*xy(rows_of(L30)))
    truths = {}
    for link in ("logit", "cloglog"):
        b = fit_link(x, k, n, link)
        truths[f"fitted {link}"] = (link_prob(b, x, link), link_d_star(b, link))
    iso = np.clip(np.array(pava(k / n, n)), 0.0, 1.0)
    truths["isotonic (no shape)"] = (iso, model_free_d_star(x, iso * 150, np.full_like(x, 150.0)))
    jobs = [(name, x, p, d, reps, sim, 6000 + i) for i, (name, (p, d)) in enumerate(truths.items())
            for reps in (30, 150) for sim in range(200)]
    with mp.get_context("spawn").Pool(WORKERS) as pool:
        results = pool.map(_f2_sim, jobs, chunksize=4)
    table = {}
    for name, (p, d) in truths.items():
        table[name] = dict(true_d_star=float(d), by_replicates={})
        for reps in (30, 150):
            cell = {}
            for m in ("loglog", "logit", "model_free"):
                got = [o[m] for t, r, o in results if t == name and r == reps and o[m] is not None]
                est = np.array([g[0] for g in got])
                cover = np.array([g[1] <= d <= g[2] for g in got])
                cell[m] = dict(valid=len(got), coverage=float(cover.mean()),
                               coverage_wilson=list(wilson_interval(int(cover.sum()), len(got))),
                               bias=float(est.mean() - d), rmse=float(np.sqrt(np.mean((est - d) ** 2))),
                               half_width=float(np.mean([(g[2] - g[1]) / 2 for g in got])))
            table[name]["by_replicates"][reps] = cell
    iso_ok = all(table["isotonic (no shape)"]["by_replicates"][r]["loglog"]["coverage"] >= 0.90 for r in (30, 150))
    R["F2"] = dict(truths=table, simulations_per_cell=200, bootstrap_per_simulation=200,
                   rule="log-log robust if coverage >= 0.90 under the isotonic truth at both replicate counts",
                   loglog_robust=bool(iso_ok),
                   note="Under the isotonic truth the true d* is defined by linear interpolation, the same rule the "
                        "model-free estimator uses, which favours that estimator.")


def f2b(R):
    out = {}
    for s in range(4001, 4006):
        own = estimate_threshold(*xy(study(f"L30_s{s}")), methods=("loglog", "model_free"), seed=5000 + s)
        rest = estimate_threshold(*xy(rows_of([n for n in L30 if n != f"L30_s{s}"])), methods=("loglog", "model_free"),
                                  n_boot=0)
        out[f"L30_s{s}"] = {m: dict(d_star=own[m].d_star, ci=list(own[m].ci), others_pooled=rest[m].d_star,
                                    covers=bool(own[m].ci[0] <= rest[m].d_star <= own[m].ci[1]))
                            for m in ("loglog", "model_free")}
    R["F2b"] = dict(studies=out, covered={m: sum(v[m]["covers"] for v in out.values()) for m in ("loglog", "model_free")})


# ---- F3: pathways -------------------------------------------------------------------------

def f3(R):
    groups = {"L20": ["L20_s4011"], "L30": L30, "L40": ["L40_s4012"], "L50": ["L50_s4013", "L50_s4016"],
              "L75": ["L75_s4014", "L75_s4017"], "L100": ["L100_s4015"], "L150": ["L150_s4018"],
              "repro 0.05": ["r05_s4021"], "repro 0.30": ["r30_s4022"],
              "well-mixed L30": ["WMlow30_s4061", "WM30_s4001", "WM30_s4002"],
              "well-mixed L75": ["WMlow75_s4062", "WM75_s4014"]}
    out = {}
    for name, names in groups.items():
        rows = rows_of(names)
        t = pathway_table([r["a_value"] for r in rows], [r["prey_extinct"] for r in rows],
                          [r["predator_extinct"] for r in rows])
        sums_ok = all(v.predator_first + v.prey_first + v.both_same_step == v.extinct for v in t)
        x = [r["a_value"] for r in rows]
        pf = estimate_threshold(x, [int(r["predator_extinct"] and not r["prey_extinct"]) for r in rows],
                                methods=("model_free",), n_boot=0)["model_free"]
        qf = estimate_threshold(x, [int(r["prey_extinct"] and not r["predator_extinct"]) for r in rows],
                                methods=("model_free",), n_boot=0)["model_free"]
        out[name] = dict(runs=len(rows), sums_ok=sums_ok,
                         totals=dict(extinct=sum(v.extinct for v in t), predator_first=sum(v.predator_first for v in t),
                                     prey_first=sum(v.prey_first for v in t), both=sum(v.both_same_step for v in t)),
                         predator_first_reaches_half_at=pf.d_star, prey_first_reaches_half_at=qf.d_star,
                         max_p_predator_first=max(v.p_predator_first for v in t),
                         max_p_prey_first=max(v.p_prey_first for v in t),
                         levels=[dict(density=v.value, n=v.n, extinct=v.extinct, predator_first=v.predator_first,
                                      prey_first=v.prey_first, both=v.both_same_step, p_extinct=v.p_extinct,
                                      ci_extinct=list(v.ci_extinct), p_predator_first=v.p_predator_first,
                                      ci_predator_first=list(v.ci_predator_first), p_prey_first=v.p_prey_first,
                                      ci_prey_first=list(v.ci_prey_first)) for v in t])
    R["F3"] = dict(groups=out, all_sums_ok=all(v["sums_ok"] for v in out.values()))


# ---- F4: reproduction rate with log-log ------------------------------------------------------

def f4(R):
    out = {}
    for name, names, seed in (("repro 0.05", ["r05_s4021"], 2005), ("repro 0.15 (L30 pooled)", L30, 1030),
                              ("repro 0.30", ["r30_s4022"], 2030)):
        rows = rows_of(names)
        out[name] = dict(runs=len(rows), **est_dict(estimate_threshold(*xy(rows), seed=seed)))
    R["F4"] = out


def main():
    t0 = time.perf_counter()
    R = {"generated_by": "validation/hs6_analyze.py", "plan": "evidence/hs6/ANALYSIS_PLAN.md"}
    f1(R)
    print("F1 done", flush=True)
    f3(R)
    f4(R)
    f2b(R)
    print("F2b/F3/F4 done", flush=True)
    f2(R)
    print("F2 done", flush=True)
    path = OUT / "hs6_results.json"
    dump(path, R)
    write_manifest(path, script="validation/hs6_analyze.py", wall_seconds=time.perf_counter() - t0,
                   params={"bootstrap": 1000, "f2_simulations": 200, "f2_bootstrap": 200,
                           "seeds": "1000+L, 2000+L, 3000+L, 4000+L, 5000+study, 6000+truth"})
    print("done", round(time.perf_counter() - t0), "s")


if __name__ == "__main__":
    main()
