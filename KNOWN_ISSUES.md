# Known Issues

| ID | Issue | Severity | Status |
| --- | --- | --- | --- |
| KI-01 | Three deliverable `.docx` files (`PPETS_Final_Project_Report.docx`, two "Simulating Extinction..." HLD/SRS drafts) sit untracked in the code repo root instead of the course documents folder. Risk of a large binary report draft getting swept into a code commit, or of being silently lost (not git-tracked anywhere, no backup). | Medium | Open — flagged, not resolved this checkpoint; relocating files outside this task's scope needs the student's own sign-off. See RISK_LOG.md RL-01. |
| KI-02 | `ThresholdAnalyzer.run_sweep()` is sequential, not the LLD §4.1 `multiprocessing.Pool`-parallelized version. Fine for the grid sizes used in tests so far; a realistic UC03 sweep (e.g. `experiments/sweep.py`'s 20x10x3 = 600 full engine runs) will be slow single-threaded. | Low (by design this sprint) | Open — planned next sprint. See RISK_LOG.md RL-02. |
| KI-03 | `HeatmapView` is not wired into `MainWindow` — there is no UI control that triggers `ThresholdAnalyzer.run_sweep()` yet, so UC03 is not end-to-end testable through the GUI. | Medium | Open — next sprint. |
| KI-04 | `PopulationStats.extinction_risk` is still the placeholder heuristic documented in `ppets/README.md`, not a real `ThresholdAnalyzer`-derived metric, even though `ThresholdAnalyzer` now exists. | Low | Open — the two haven't been wired together yet. |
| KI-05 | `experiments/sweep.py` duplicates sweep logic that now also exists in `ThresholdAnalyzer._run_cell()`. Kept separate deliberately this checkpoint — the report script needs curve-tracing output `ThresholdAnalyzer` doesn't produce — but the duplication should collapse once `ThresholdAnalyzer` grows a comparable tracing option. | Low | Open, tracked. |
| KI-06 | This checkpoint's GUI smoke test only verifies widget construction under `QT_QPA_PLATFORM=offscreen` (`evidence/gui_offscreen_smoke_test.txt`) — it does not exercise an actual on-screen run or user interaction, because the dev environment used has no attached display. | Low | Accepted limitation of this checkpoint's environment. |

---

## Added at Hard Stop 3 / RU-06 (early implementation validation, 2026-10-10)

Defects `DEF-01`–`DEF-08` each have an executable reproducer in
`tests/test_known_defects.py` (strict `xfail`: the suite stays green while the
defect exists and fails loudly the day it is fixed, forcing this table to be
updated). Evidence behind every number below: `evidence/validation/`.

| ID | Issue | Severity | Reproducer | Status / workaround |
| --- | --- | --- | --- | --- |
| DEF-01 | Cells not finished when a sweep is cancelled are stored as `0.0`, indistinguishable from "never goes extinct"; a partial heatmap reads as good news. | Medium | `test_def01_*` | Open. Workaround: consult `HeatmapData.complete` and discard partial matrices. Fix: `NaN` for uncomputed cells. |
| DEF-02 | `_cancelled` is never reset, so `run_sweep()` after `cancel()` silently returns an empty, incomplete result. | Medium | `test_def02_*` | Open. Workaround: construct a new `ThresholdAnalyzer` per sweep. |
| DEF-03 | An axis that breaks `prey_density + predator_density <= 1` raises only mid-sweep; earlier cells' results are lost (`results` stays `None`). | Medium | `test_def03_*` | Open. Workaround: pre-check axis maxima. Fix: validate every axis value in `__init__`. |
| DEF-04 | `base_config.seed` is ignored; replicate seeds depend only on `hash((a, b, rep))`, so a study cannot be repeated with an independent master seed (no between-study variance). | Medium | `test_def04_*` | Open. Fix: derive per-run seeds with `numpy.random.SeedSequence(master).spawn(...)`. Changing it re-baselines every previously reported number. |
| DEF-05 | `HeatmapView` axes show array indices (0..N-1), not the swept parameter values (FR07 says axes must be labelled). Labels carry the parameter *names* only. | Medium | `test_def05_*` | Open. Fix: set the image rect/transform from `param_a_values`/`param_b_values`. |
| DEF-06 | Same parameter on both axes is accepted; the second axis silently overwrites the first. | Low | `test_def06_*` | Open. |
| DEF-07 | Unknown parameter name surfaces as a bare `TypeError` from the dataclass constructor on the first cell, not a validation error at construction. | Low | `test_def07_*` | Open. |
| DEF-08 | `ParamRange.values()` uses `round()`, so it can overshoot `stop` (`0.0..0.5 step 0.3` -> `[0.0, 0.3, 0.6]`) and silently drops `stop` when the step does not divide the span. | Low | `test_def08_*` | Open. Workaround: choose steps that divide the span exactly. |
| DEF-09 | Replicate seeds use CPython's builtin tuple `hash`. Verified identical across `PYTHONHASHSEED` values and across a fresh venv on 3.14.4 (checks V03, clean restart), but the algorithm is an implementation detail, not a guaranteed contract across Python versions. | Medium | not testable in one interpreter; documented | Open. Fixed together with DEF-04. |
| DEF-10 | `PopulationStats.extinction_risk` (shown in the GUI as "Extinction risk") has no predictive skill: AUC 0.479 for eventual extinction among runs alive at generation 20 (n=688, 158 later extinct; mean 0.76 for extinct vs 0.82 for surviving runs - slightly inverted). Supersedes the "Low" rating of KI-04. | Medium | `validation/pilot_study.py` -> `pilot_summary.json` | Open. Workaround: do not cite it as a result. Fix: relabel or replace with the `ThresholdAnalyzer` estimate. |
| DEF-11 | Engine step latency at 100x100 exceeds the NFR01 100 ms budget on this machine (p95 109 ms; median 67 ms). Within budget up to 75x75 (p95 51 ms). | Low | `validation/bench_sweep.py` | Open. Documented limit; `Controller` already auto-pauses on 5 slow steps. |
| DEF-12 | `requirements.txt` is unpinned; a fresh install pulled numpy 2.5.3 while the development interpreter had 2.5.1. Outputs were identical, but nothing guarantees that for later releases. | Low | `validation/clean_restart.py` | Mitigated: `requirements-lock.txt` records the working set. |

### Documentation corrections

- `PPETS_HS3_Implementation_Baseline_Package` (RU-05, section 7.3) described the `main.py` trace as a 50x50 run. `main.py` configures a **30x30** grid
  (`main.py:12-13`); the figure was a transcription error. The trace itself is unchanged.
- `main.py`'s module docstring still says a pytest suite "can be added later"; the suite exists (40 tests). Cosmetic, left as is.

### Workarounds recorded

- **Qt widget kept alive by a failing test's traceback segfaults the interpreter at shutdown** (exit 139, summary line lost).
  Seen while writing DEF-05's reproducer; fixed in the test by reading the number out inside a helper and `deleteLater()`-ing the widget.
  Any new test that asserts on Qt objects should do the same.

### Status changes to earlier items

- **KI-06** (GUI only verified offscreen): the native Qt platform plugin (`windows`) was also exercised on this machine
  (`evidence/validation/environment.json`, checks V09/V10 screenshots). Still not a manual click-through; the limitation is reduced, not closed.
- **KI-04**: severity raised to Medium, see DEF-10.

---

## Hard Stop 4 / RU-08 (technical evidence review, 2026-10-24)

Evidence: `evidence/hs4/` (each file has a `.manifest.json`). Production diff:
`evidence/hs4/ppets_changes_vs_hs3-baseline.diff`.

### Closed

| ID | Resolution | Proof |
| --- | --- | --- |
| DEF-01 | Uncomputed cells are `NaN`; run records only for completed cells. | `test_def01_*`, `test_parallel_cancel_leaves_nan_not_zero` |
| DEF-02 | `run_sweep()` resets the cancel flag. | `test_def02_*` |
| DEF-03 | Every cell's config is validated in the constructor. | `test_def03_*` (rewritten: the HS3 version could never detect the fix) |
| DEF-04 | Seeds from `SeedSequence(master, spawn_key=(i, j, rep))`; master = `base_config.seed` or recorded fresh entropy. **Re-baselines every number reported before HS4** (old vs new compared in E8). | `test_def04_*`, `test_same_master_seed_*` |
| DEF-05 | `HeatmapView` places pixels over parameter values. | `test_def05_*` |
| DEF-06 | Duplicate axis rejected. | `test_def06_*` |
| DEF-07 | Unknown / non-sweepable name rejected with `ValueError`. | `test_def07_*`, `test_non_sweepable_fields_rejected` |
| DEF-08 | `ParamRange.values()` floors, never overshoots `stop`. | `test_def08_*` |
| DEF-09 | Closed with DEF-04 (no builtin `hash()`). | — |
| DEF-10 | `extinction_risk` removed from `PopulationStats`, the CSV schema (now `generation,prey_count,predator_count`) and the GUI; FR14 scope statement added. | `test_stats_panel_*`, `test_main_window_shows_scope_statement` |
| KI-02 | `ThresholdAnalyzer` runs on a `multiprocessing` Pool (`workers=`). | `evidence/hs4/serial_vs_parallel.json`, `benchmark.json` |
| KI-04 | Superseded by DEF-10. | — |

All eight reproducers were re-run against the untouched `hs3-baseline` code in a
temporary worktree, where each fails for its stated reason
(`evidence/hs4/defects_on_hs3_baseline.txt`).

### Found and fixed during HS4 (before any result was reported)

| ID | Issue | Fix |
| --- | --- | --- |
| HS4-01 | New analyzer stepped runs that were extinct at generation 0 and recorded extinction at generation 1. | Initial state checked first; `test_zero_predator_density_*`. |
| HS4-02 | Threshold fit reported "not converged" on quasi-separated data (mixed outcomes at one level only). | Separation check uses `<=`; status `separated` with bracket; `test_fit_reports_quasi_separation`. |

### Open

| ID | Issue | Severity | Status |
| --- | --- | --- | --- |
| HS4-03 | A run with no predators (density 0, or a low density on a small grid where seeding places none) counts as "extinct at generation 0". Correct by definition, but it inflates P(extinction) at very low densities on small grids. | Low | Documented; sweeps start at 0.06 on 20×20 and larger. Consider excluding or flagging such runs. |
| HS4-04 | `HeatmapView` does not yet display the per-cell interval or replicate count that `HeatmapData` now carries (FR11 display part). | Medium | Next sprint, with GUI wiring (KI-03). |
| HS4-05 | Run manifests are written by `validation/hs4_common.py`, not by the application (FR16 in production not built). | Medium | Move into `ppets/` with the FR09 export. |
| HS4-06 | Pool start-up (spawn) costs about 0.84 s (one-run sweep, 15 workers, vs 0.003 s serial; `evidence/hs4/benchmark.json`), so `workers > 1` is slower for tiny sweeps. | Low | Default stays `workers=1`; GUI should choose by job size. |
| KI-03 | Sweep still not launchable from `MainWindow`. | Medium | Open. |
| DEF-11 | 100×100 step latency vs NFR01 — re-measured in `evidence/hs4/benchmark.json`. | Low | Open. |
| HS4-07 | Profiling (`evidence/hs4/benchmark_profile.txt`): 44% of a 30×30 run is spent in the neighbour-count generator in `grid.py` (`count_neighbors`). Vectorising neighbour counts (e.g. a numpy roll/convolution) is the obvious speed-up if larger grids (RL-13) become expensive. | Low | Optional, only if B2 cost requires it. |

---

## Week 9 / RU-09 (results and limitations memo, 2026-10-31)

Evidence: `evidence/ru09/`. No `ppets/` code changed. Limitation register: section 4
of `PPETS_RU09_Results_and_Limitations_Memo.docx`.

| ID | Issue | Severity | Status |
| --- | --- | --- | --- |
| RU9-01 | `fit_threshold` still uses a logistic curve only. It is biased high by about 0.009 at 30x30 and its 95% interval covers the true d\* in 47% of simulated studies if the log-log curve is true. | High | Open. Fix: backlog B3. Until then report log-log and model-free values from `validation/ru09_analyze.py`. |
| RU9-02 | `extinct` joins predator-first and prey-first events; `RunRecord` stores no trajectory, and runs stop at the first extinction. | Medium | Open. Backlog B3b. |
| RU9-03 | The 150-generation horizon was only checked at predator reproduction 0.15. At 0.30, 12 extinctions fall after generation 75 and one at generation 150. | Medium | Open. Backlog B4. |
| RU9-04 | The default density axis stops at 0.40, where P(extinct) is only 67% at L = 100. Larger grids need a wider axis. | Low | Open. Choose the axis per grid size. |

HS4-03 checked: 0 extinct-at-start runs in 9,030 runs across all sweeps.

---

## Hard Stop 5 (artifact hardening and reproducibility, 2026-11-08)

Evidence: `evidence/hs5/` (friction log: `REPRODUCIBILITY_NOTES.md`, FP-01 to FP-13).
No `ppets/` code changed (fingerprint `0c61dd14fdaad6a8`).

### Closed

| ID | Resolution | Proof |
| --- | --- | --- |
| HS5-01 | `scipy` was imported by tests and analysis scripts but not declared, so a fresh install ran zero tests (FP-05). Added to `requirements.txt` and the lock file. | `clean_run_py314.json`, `clean_run_py311.json` |
| HS5-02 | `validation/run_validation.py` failed 4/12 on `main` because V03, V06, V08 and V11 still encoded the HS3 contract (FP-06, FP-07), and it overwrote the committed RU-06 evidence (FP-08). Checks updated; output moved to `evidence/hs5/validation/`. | 12/12, `evidence/hs5/validation/validation_report.txt` |
| KI-06 | Partly: the GUI is now exercised on the native platform by V09/V10 and in the walkthrough recording. | — |
| DEF-12 | `requirements-lock.txt` now covers every import, including scipy; drift measured (FP-09). | `clean_run_py311.json` |

### Open

| ID | Issue | Severity | Status |
| --- | --- | --- | --- |
| HS5-03 | No licence file. The repository is public, but nobody may legally reuse the code. | Medium | Student decision (choose a licence, e.g. MIT, or state "all rights reserved"). |
| HS5-04 | Six committed files from HS3 and HS4 contain the Windows user name in file paths: `evidence/pytest_output.txt`, `evidence/validation/pytest_full.txt`, `evidence/validation/environment.json`, `evidence/hs4/pytest_full.txt`, `evidence/hs4/benchmark_profile.txt`, `evidence/hs4/defects_on_hs3_baseline.txt`. New HS5 logs are redacted. | Low | Left as committed (they are already public, and history is not rewritten). |
| HS5-05 | A half-installed PyQt6 makes `import ppets` crash with `TypeError` in `ppets/__init__.py`, even for headless use (FP-02). Detected by `check_env.py`. | Low | Code fix waits for decision D-HS5-1 (it changes the `ppets/` fingerprint). |
| HS5-06 | Only Windows 11 had been run. | Medium | **Closed 2026-11-08:** first CI run green on Ubuntu (3.14 lock, 3.11 unpinned) and Windows (https://github.com/QuanTakeuchi/ppets/actions/runs/42508719825). On Ubuntu the evidence files match their manifests only after line-ending normalisation (they were hashed as CRLF on Windows), which `hs5_verify_evidence.py` handles. macOS remains untested. |
| HS5-07 | `SimulationConfig.validate()` checks ranges but not types (e.g. `width=30.5` reaches the grid). `main.py` now type-checks its input; direct library use does not. | Low | With the next `ppets/` change. |
| HS5-08 | `ppets/README.md` and `VALIDATION_MEMO.md` describe older states (29 tests, `extinction_risk`). `VALIDATION_MEMO.md` now carries a "historical" banner. `ppets/README.md` cannot: any file under `ppets/` is part of the frozen fingerprint, so editing it would block `ru09_studies.py`. | Low | Update with the next `ppets/` change. |

---

## Hard Stop 6 / RU-12 (results freeze, 2026-11-21)

Evidence: `evidence/hs6/` (plan, results and manifests). `ppets/` changed
for the first time since HS4; F0 shows the spatial model's output is unchanged.

### Closed

| ID | Resolution | Proof |
| --- | --- | --- |
| RU9-01 | Production estimator was logistic only and biased. `estimate_threshold` returns model-free, log-log and logistic d*. | `tests/test_hs6_final.py` (published values reproduced exactly) |
| HS5-05 | Half-installed PyQt6 no longer breaks `import ppets`. | `test_half_installed_pyqt6_does_not_break_import` (fails on the old code) |
| HS5-07 | `SimulationConfig.validate()` checks types. | `test_config_rejects_wrong_types` |
| FR12 gap | Well-mixed mode built. | `test_well_mixed_*`; `evidence/hs6/hs6_results.json` F1 |

### New

| ID | Issue | Severity | Status |
| --- | --- | --- | --- |
| HS6-01 | `DEFAULT_METHOD` is log-log, but the F2 stress test (pre-set rule) found log-log intervals unreliable when the true curve is not log-log; the report leads with model-free. A caller who reads only the default gets log-log. | Medium | Decision D-HS6-1 (student/supervisor). `estimate_threshold` returns both. |
| HS6-02 | CI has not run on the HS6 code (not pushed). | Medium | Closes on the first green run after push. |
| HS6-03 | Well-mixed mode is one mean-field variant (8 random partners per generation, partner sets not symmetric). No intermediate interaction range. | Low | Documented (report Section 8.2, LIM-6). |
| HS6-04 | No GUI control for `mixing`; well-mixed runs come from scripts or the API only. | Low | Part of LIM-7 / KI-03. |
| HS5-08 (still open) | `ppets/README.md` still describes the pre-HS4 state. Editing it changes the `ppets/` fingerprint that every HS6 manifest records (`6bb0a813947cbfa0`), so it waits until the HS6 tag exists. | Low | Update in the first commit after `hs6-results-freeze`. |
| HS6-05 | `validation/ru09_studies.py` refuses to run on the HS6 code (fingerprint guard). Regenerating RU-09 studies needs the `hs4-evidence` tag; F0 shows the HS6 code gives identical spatial output. | Low | By design. |
