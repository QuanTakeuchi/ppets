"""PPETS validation suite: one repeatable command, one JSON/text report.
Written for RU-06 (HS3); checks V03, V06, V08 and V11 updated at HS5 to the
HS4 contract (SeedSequence seeds, 3-column CSV, fixed defects). The RU-06
results stay in evidence/validation/; this version writes to evidence/hs5/validation/.

    python validation/run_validation.py

Each check answers a single question about the *current* implementation and
records pass/fail plus the measured detail. Failures are reported, never
swallowed; the process exits non-zero if any check fails so a CI job or a
supervisor re-run cannot misread a red result as green.

Output: evidence/hs5/validation/validation_report.{json,txt}, plus
heatmap_render.png and gui_main_window.png in the same folder (Qt
screenshots, see V09/V10).
"""

from __future__ import annotations

import csv
import importlib.util
import io
import os
import subprocess
import sys
import time
import traceback

# Prefer the native Qt platform plugin (real fonts -> readable screenshots); fall back to
# offscreen only on a machine with no display server (e.g. headless Linux CI).
if sys.platform != "win32" and sys.platform != "darwin" and not (
    os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from _common import REPO, history_signature, provenance, sha256_of, write_json  # noqa: E402

from ppets.analysis import HeatmapData, ParamRange, ThresholdAnalyzer  # noqa: E402
from ppets.analysis.threshold_analyzer import replicate_seed  # noqa: E402
from ppets.simulation import CellularAutomatonEngine, SimulationConfig  # noqa: E402

RESULTS: list[dict] = []
# Kept apart from evidence/validation/ so a re-run never overwrites the RU-06 record.
EVIDENCE = REPO / "evidence" / "hs5" / "validation"
# HS6: `--out evidence/hs6/validation` keeps a later run from overwriting the HS5 record.
if "--out" in sys.argv:
    EVIDENCE = REPO / sys.argv[sys.argv.index("--out") + 1]
EVIDENCE.mkdir(parents=True, exist_ok=True)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def check(check_id: str, name: str):
    """Decorator: run the function, capture pass/fail, detail and timing."""

    def wrap(fn):
        t0 = time.perf_counter()
        try:
            detail = fn()
            passed = True
        except AssertionError as exc:
            detail, passed = f"ASSERTION FAILED: {exc}", False
        except Exception as exc:  # a crash is a failed check, not a skipped one
            detail, passed = f"ERROR: {exc.__class__.__name__}: {exc}\n{traceback.format_exc()}", False
        RESULTS.append({
            "id": check_id, "name": name, "passed": passed,
            "seconds": round(time.perf_counter() - t0, 2), "detail": detail,
        })
        print(f"[{'PASS' if passed else 'FAIL'}] {check_id} {name} ({RESULTS[-1]['seconds']}s)", flush=True)
        return fn

    return wrap


# --------------------------------------------------------------------------- V01
@check("V01", "Config validation rejects bad input; dict round-trip is lossless")
def _():
    SimulationConfig()  # defaults valid
    bad = [
        dict(width=1), dict(prey_density=-0.1), dict(predator_repro_rate=1.5),
        dict(prey_density=0.8, predator_density=0.3), dict(prey_death_threshold=9),
        dict(starvation_rate=0),
    ]
    for kw in bad:
        try:
            SimulationConfig(**kw)
        except ValueError:
            continue
        raise AssertionError(f"accepted invalid config {kw}")
    cfg = SimulationConfig(width=12, height=9, seed=5, toroidal=False)
    assert SimulationConfig.from_dict(cfg.to_dict()).to_dict() == cfg.to_dict()
    return f"{len(bad)} invalid configs rejected; to_dict/from_dict round-trip equal"


# --------------------------------------------------------------------------- V02
@check("V02", "Same seed -> identical history in one process (NFR02)")
def _():
    sigs = []
    for _run in range(3):
        e = CellularAutomatonEngine(SimulationConfig(width=30, height=30, seed=42))
        for _ in range(100):
            e.step()
        sigs.append(sha256_of(history_signature(e)))
    assert len(set(sigs)) == 1, sigs
    return f"3 runs x 100 generations, 30x30, seed 42 -> one signature {sigs[0][:16]}"


# --------------------------------------------------------------------------- V03
@check("V03", "Determinism holds across separate interpreters and PYTHONHASHSEED values")
def _():
    prints = {}
    for hs in ("0", "1", "12345", "random"):
        env = dict(os.environ, PYTHONHASHSEED=hs)
        out = subprocess.run(
            [sys.executable, str(REPO / "validation" / "_worker.py"), "fingerprint"],
            capture_output=True, text=True, env=env, cwd=REPO, check=True,
        ).stdout.strip()
        prints[hs] = out
    assert len(set(prints.values())) == 1, prints
    return f"4 fresh interpreters (PYTHONHASHSEED=0,1,12345,random) -> identical fingerprint {next(iter(prints.values()))[:16]}"


# --------------------------------------------------------------------------- V04
@check("V04", "Different seeds give different trajectories (determinism is not a constant)")
def _():
    sigs = set()
    for seed in range(1, 6):
        e = CellularAutomatonEngine(SimulationConfig(width=30, height=30, seed=seed))
        for _ in range(40):
            e.step()
        sigs.add(sha256_of(history_signature(e)))
    assert len(sigs) == 5, f"only {len(sigs)} distinct histories from 5 seeds"
    return "5 seeds -> 5 distinct histories"


# --------------------------------------------------------------------------- V05
@check("V05", "Grid invariants hold every generation (state codes, counts, hunger, eaten buffer)")
def _():
    configs = [
        SimulationConfig(width=25, height=25, seed=3),
        SimulationConfig(width=25, height=25, seed=3, toroidal=False),
        SimulationConfig(width=20, height=20, seed=8, prey_density=0.5, predator_density=0.4),
    ]
    steps = 0
    for cfg in configs:
        e = CellularAutomatonEngine(cfg)
        for _ in range(60):
            s = e.step()
            steps += 1
            st = e.grid.state
            assert set(map(int, set(st.flatten().tolist()))) <= {0, 1, 2}, "illegal state code"
            prey, pred = e.grid.counts()
            assert (prey, pred) == (s.prey_count, s.predator_count), "stats != grid"
            assert prey + pred <= cfg.width * cfg.height
            assert (e.grid.hunger >= 0).all(), "negative hunger"
            assert not e.grid.eaten.any(), "eaten buffer not cleared after swap"
            if s.is_extinct():
                break
    return f"{steps} generations across 3 configs (toroidal, bounded, dense) — no invariant violated"


# --------------------------------------------------------------------------- V06
@check("V06", "Headless CSV pipeline (main.py): schema, ranges, byte-identical to the committed reference")
def _():
    out = subprocess.run([sys.executable, "main.py"], cwd=REPO, capture_output=True, text=True, check=True).stdout
    rows = list(csv.reader(io.StringIO(out)))
    assert rows[0] == ["generation", "prey_count", "predator_count"], rows[0]
    body = [r for r in rows[1:] if len(r) == 3]
    gens = [int(r[0]) for r in body]
    assert gens == list(range(len(body))), "generations not contiguous from 0"
    assert all(int(r[1]) >= 0 and int(r[2]) >= 0 for r in body)
    ref = (REPO / "evidence" / "hs5" / "main_expected.txt").read_text(encoding="utf-8").replace("\r\n", "\n")
    same = ref == out.replace("\r\n", "\n")
    assert same, "main.py output differs from evidence/hs5/main_expected.txt"
    return f"{len(body)} rows, schema+ranges ok; output byte-identical to evidence/hs5/main_expected.txt"


# --------------------------------------------------------------------------- V07
@check("V07", "ThresholdAnalyzer output structure, probability bounds, progress and cancel contract")
def _():
    base = SimulationConfig(width=15, height=15)
    a = ParamRange("predator_density", 0.05, 0.25, 0.05)   # 5 values
    b = ParamRange("predator_repro_rate", 0.10, 0.20, 0.05)  # 3 values
    seen = []
    ta = ThresholdAnalyzer(a, b, replicates=4, base_config=base, max_generations=60)
    res = ta.run_sweep(on_progress=seen.append)
    assert res.complete
    assert (len(res.extinction_prob), len(res.extinction_prob[0])) == (5, 3)
    assert res.param_a_values == a.values() and res.param_b_values == b.values()
    assert seen == sorted(seen) and abs(seen[-1] - 1.0) < 1e-12 and len(seen) == 15
    for i in range(5):
        for j in range(3):
            e, pr, pd = (res.extinction_prob[i][j], res.prey_extinction_prob[i][j],
                         res.predator_extinction_prob[i][j])
            assert 0.0 <= e <= 1.0
            assert max(pr, pd) - 1e-12 <= e <= min(1.0, pr + pd) + 1e-12, (i, j, e, pr, pd)
            assert abs(e * 4 - round(e * 4)) < 1e-9, "not a multiple of 1/replicates"
    # cancel contract
    ta2 = ThresholdAnalyzer(a, b, replicates=1, base_config=base, max_generations=5)
    n = []
    def stop_after_two(_f):
        n.append(1)
        if len(n) == 2:
            ta2.cancel()
    part = ta2.run_sweep(on_progress=stop_after_two)
    assert part.complete is False and len(n) == 2
    return "5x3 matrix, 60 runs; bounds + species invariant + 1/replicates granularity + progress/cancel contract ok"


# --------------------------------------------------------------------------- V08
@check("V08", "ThresholdAnalyzer agrees run-for-run with the standalone experiments/sweep.py path")
def _():
    spec = importlib.util.spec_from_file_location("sweep_script", REPO / "experiments" / "sweep.py")
    sweep = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sweep)  # defines run_one/BASE; main() is not executed
    pds = ParamRange("predator_density", 0.06, 0.36, 0.15).values()        # 0.06, 0.21, 0.36
    prs = ParamRange("predator_repro_rate", 0.04, 0.20, 0.08).values()     # 0.04, 0.12, 0.20
    reps = 3
    master = 2026
    ta = ThresholdAnalyzer(
        ParamRange("predator_density", pds[0], pds[-1], 0.15),
        ParamRange("predator_repro_rate", prs[0], prs[-1], 0.08),
        replicates=reps, base_config=SimulationConfig(**sweep.BASE, seed=master), max_generations=sweep.MAX_GEN,
    )
    res = ta.run_sweep()
    assert res.master_seed == master
    mismatches, compared = [], 0
    for i, pd in enumerate(pds):
        for j, pr in enumerate(prs):
            # Since HS4 the analyzer seeds each run from SeedSequence(master, (i, j, rep)).
            theirs = [sweep.run_one(pd, pr, replicate_seed(master, i, j, r))[0] for r in range(reps)]
            exp_ext = sum(o != "coexistence" for o in theirs) / reps
            compared += 1
            if abs(res.extinction_prob[i][j] - exp_ext) > 1e-12:
                mismatches.append((pd, pr, res.extinction_prob[i][j], exp_ext))
    assert not mismatches, mismatches
    return (f"{compared} cells x {reps} replicates identical (master seed {master}). NOTE: both paths call the same "
            "engine, so this validates the analyzer's seeding/aggregation, not the engine itself.")


# --------------------------------------------------------------------------- V09
@check("V09", "HeatmapView renders an analyzer-produced matrix (screenshot saved)")
def _():
    from PyQt6.QtWidgets import QApplication
    from ppets.ui.heatmap_view import HeatmapView

    app = QApplication.instance() or QApplication([])
    ta = ThresholdAnalyzer(
        ParamRange("predator_density", 0.04, 0.40, 0.04),
        ParamRange("predator_repro_rate", 0.04, 0.20, 0.04),
        replicates=3, base_config=SimulationConfig(width=20, height=20), max_generations=80,
    )
    res = ta.run_sweep()
    view = HeatmapView()
    view.resize(640, 480)
    view.set_heatmap(res)
    view.show()
    app.processEvents()
    shown = view._image_view.getImageItem().image
    import numpy as np
    assert shown.shape == (len(res.param_a_values), len(res.param_b_values)), shown.shape
    assert np.allclose(shown, np.asarray(res.extinction_prob)), "rendered image != HeatmapData"
    pix = view.grab()
    png = EVIDENCE / "heatmap_render.png"
    assert pix.save(str(png)), "could not write screenshot"
    img = pix.toImage()
    colours = {img.pixel(x, y) for x in range(0, img.width(), 7) for y in range(0, img.height(), 7)}
    assert len(colours) > 5, "screenshot looks blank"
    return (f"[Qt platform: {app.platformName()}] image array {shown.shape} equals HeatmapData matrix; screenshot {png.name} "
            f"({img.width()}x{img.height()}, {len(colours)} sampled colours). "
            "Axes are placed in parameter units since the DEF-05 fix (HS4).")


# --------------------------------------------------------------------------- V10
@check("V10", "MainWindow + controller integration drives engine, charts and stats")
def _():
    from PyQt6.QtWidgets import QApplication
    from ppets.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    win = MainWindow()
    win.show()
    got = []
    win.controller.generation_advanced.connect(got.append)
    win.controller.start(SimulationConfig(width=30, height=30, seed=42))
    win.controller.pause()  # stop the wall-clock timer; step deterministically
    for _ in range(25):
        win.controller.step_once()
    app.processEvents()
    assert len(got) == 25 and [s.generation for s in got] == list(range(1, 26))
    assert win.controller.engine.generation == 25
    pix = win.grab()
    png = EVIDENCE / "gui_main_window.png"
    assert pix.save(str(png))
    win.close()
    return f"[Qt platform: {app.platformName()}] 25 controller steps -> 25 generation_advanced signals; window screenshot {png.name}"


# --------------------------------------------------------------------------- V11
@check("V11", "Former defect reproducers DEF-01..08 pass (regression guard since HS4)")
def _():
    p = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_known_defects.py", "-q", "-p", "no:cacheprovider"],
        cwd=REPO, capture_output=True, text=True,
    )
    tail = [ln for ln in p.stdout.strip().splitlines() if ln.strip()][-1]
    assert p.returncode == 0, p.stdout[-800:]
    assert "passed" in tail and "failed" not in tail and "xfail" not in tail and "xpass" not in tail, tail
    return tail


# --------------------------------------------------------------------------- V12
@check("V12", "Negative control: unseeded runs diverge, so the V02/V03 equality tests can actually fail")
def _():
    sigs = set()
    for _run in range(3):
        e = CellularAutomatonEngine(SimulationConfig(width=30, height=30, seed=None))
        for _ in range(40):
            e.step()
        sigs.add(sha256_of(history_signature(e)))
    assert len(sigs) > 1, "unseeded runs were identical — determinism checks would be vacuous"
    return f"3 unseeded runs -> {len(sigs)} distinct histories (determinism checks are discriminating)"


def main() -> int:
    passed = sum(r["passed"] for r in RESULTS)
    report = {"provenance": provenance(), "summary": {"passed": passed, "total": len(RESULTS)}, "checks": RESULTS}
    write_json(EVIDENCE / "validation_report.json", report)
    lines = [f"PPETS validation suite — {passed}/{len(RESULTS)} checks passed",
             f"commit {report['provenance']['git_commit']} · Python {report['provenance']['python']} · "
             f"{report['provenance']['generated_at']}", ""]
    for r in RESULTS:
        lines.append(f"{r['id']} [{'PASS' if r['passed'] else 'FAIL'}] {r['name']}  ({r['seconds']}s)")
        lines.append(f"      {r['detail']}")
    (EVIDENCE / "validation_report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:2]))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
