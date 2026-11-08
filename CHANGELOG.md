# Changelog

Format loosely follows [Keep a Changelog](https://keepachangelog.com/).
Versions correspond to this project's Hard Stop tags (`hsN-baseline`), not
semantic-version releases.

## [Unreleased — HS5 artifact hardening] — 2026-11-08

No production code under `ppets/` changed (fingerprint `0c61dd14fdaad6a8`).
Proposed tag after student review: `hs5-hardening`.

### Added
- `check_env.py`: preflight check (Python, path length, packages, PyQt6 integrity, Qt platform, repository files).
- `main.py` command line: parameter flags, `--config` JSON, `--generations`, `--output`; exit status 2 with a message on bad input. Default output unchanged.
- `configs/default.json`; `evidence/hs5/main_expected.txt` (current reference trace).
- `tests/test_cli.py` (19 tests). Suite: 109 passed.
- `validation/hs5_clean_run.py` (automated clean-room pass, optional study regeneration), `validation/hs5_verify_evidence.py` (manifest hashes).
- `RUNBOOK.md`, `evidence/README.md`, `evidence/hs5/` (clean-run records, `REPRODUCIBILITY_NOTES.md`), `.github/workflows/ci.yml`, `requirements-optional.txt`.

### Changed
- `README.md` rewritten: prerequisites, setup, run commands with expected output, configuration, data, troubleshooting.
- `requirements.txt` and `requirements-lock.txt`: scipy declared; matplotlib moved to `requirements-optional.txt`.
- `validation/run_validation.py`: V03, V06, V08 and V11 updated to the HS4 contract; writes to `evidence/hs5/validation/`. `validation/_worker.py` fingerprint uses a fixed master seed.
- `ENVIRONMENT.md`, `KNOWN_ISSUES.md`, `RISK_LOG.md`, `AI_USAGE_LOG.md`, `validation/README.md` updated.

## [Unreleased — HS4 evidence review] — 2026-10-24

Committed and tagged `hs4-evidence` (dd9ff6c) on 2026-10-31.

### Added
- `ppets/analysis/estimates.py`: `wilson_interval` (FR11) and `fit_threshold`
  (FR10: logistic d* with stratified-bootstrap and delta-method 95% intervals;
  reports constant outcomes and (quasi-)separation).
- `ThresholdAnalyzer(workers=...)`: multiprocessing Pool execution (LLD §4.1).
- `HeatmapData`: per-cell `n_runs`, `n_extinct`, `ci_low`, `ci_high`,
  `master_seed`, and `runs` (one `RunRecord` per replicate).
- `MainWindow.scope_label`: permanent FR14 scope statement.
- `tests/test_hs4_analysis.py`; `validation/hs4_*.py`; `evidence/hs4/`
  (experiment plan written before the runs, studies, results, figures,
  manifests).

### Changed
- **Seeding rule** (DEF-04/09): per-run seeds now come from
  `SeedSequence(master, spawn_key=(i, j, rep))`. Every number reported before
  HS4 was produced under the old `hash()` rule; E8 compares the two.
- **CSV schema**: `PopulationStats.to_csv_row()` is now
  `generation,prey_count,predator_count` (the `extinction_risk` column is gone),
  so `main.py` output differs from the HS3 evidence by that column.
- Sweep axes are validated at construction; `ParamRange.values()` floors.
- `HeatmapView` axes are in parameter units.

### Removed
- `PopulationStats.extinction_risk` and the GUI "Extinction risk" row (DEF-10).

### Fixed
- DEF-01 to DEF-08 (reproducers now pass; markers removed). Two issues found
  in the new code during HS4 (HS4-01, HS4-02) fixed before any result was
  reported. See `KNOWN_ISSUES.md`.

## [hs3-baseline] — 2026-10-03

### Added
- `ppets/analysis/` (Module 3 skeleton): `ParamRange`, `HeatmapData`,
  `ThresholdAnalyzer` (sequential `run_sweep()`, `cancel()`,
  `get_heatmap()`), per LLD §4.1.
- `ppets/ui/heatmap_view.py`: `HeatmapView` widget skeleton (LLD §3.3),
  not yet wired into `MainWindow`.
- `tests/test_threshold_analyzer.py` (9 tests), `tests/test_heatmap_view.py` (2 tests).
- `experiments/` directory + `experiments/README.md` documenting the
  artifact-storage convention for one-off research scripts.
- Root `README.md`, `ARCHITECTURE.md`, `KNOWN_ISSUES.md`, `RISK_LOG.md`,
  `SPRINT_REFLECTION.md`, `AI_USAGE_LOG.md` — this checkpoint's
  engineering-baseline documentation set.
- `evidence/` — captured pytest, coverage, headless, and offscreen-GUI
  smoke-test output for this checkpoint.
- `coverage` added to `requirements.txt` (previously used ad hoc, undeclared).

### Changed
- `_experiment_sweep.py` moved to `experiments/sweep.py`; `OUT_DIR`
  changed from a session-specific absolute temp path to the
  repo-relative, gitignored `experiments/output/`.

### Fixed
- `HeatmapView` axis labels — `pyqtgraph.ImageView`'s default `ViewBox`
  has no `setLabel()`; now constructed with an explicit `pg.PlotItem()`
  view. Caught by `tests/test_heatmap_view.py` before being tagged.

## [a484847] — 2026-08-09

Initial commit: PPETS simulation engine, controller, UI, and tests
(Modules 1–2 + Controller, 29 tests). See `ppets/README.md` for that
pass's design deviations from the LLD as written.

## [unreleased: hs3-validation] — 2026-10-10 (Hard Stop 3 / RU-06)

No production code under `ppets/` was changed; this checkpoint adds validation
tooling, evidence and documentation only.

### Added
- `validation/` — repeatable early-validation suite: `run_validation.py` (12
  checks V01–V12), `pilot_study.py`, `triple_retest.py`, `bench_sweep.py`,
  `env_snapshot.py`, `clean_restart.py`, `make_figures.py`.
- `tests/test_known_defects.py` — 8 strict-`xfail` reproducers (DEF-01…DEF-08).
  Suite is now 40 passed + 8 xfailed.
- `evidence/validation/` — machine-readable reports, replicate-level CSVs, logs, screenshots, figures.
- `requirements-lock.txt` — exact versions of the working set.
- `ENVIRONMENT.md`, `VALIDATION_MEMO.md`.

### Changed
- `KNOWN_ISSUES.md`, `RISK_LOG.md`, `README.md`, `AI_USAGE_LOG.md` updated with RU-06 findings.

## [unreleased: ru09-results] — 2026-10-31 (Week 9 / RU-09)

No production code under `ppets/` changed (fingerprint `0c61dd14fdaad6a8`).

### Added
- `validation/ru09_studies.py`, `ru09_analyze.py`, `ru09_figures.py`; `evidence/ru09/` (plan written before the runs, studies at L = 50, 75, 100, 150, trajectory study, results, figures).
- `tests/test_ru09_analysis.py`: link-function fits checked against a direct likelihood maximiser and the production estimator. Suite is now 90 passed.

### Changed
- `KNOWN_ISSUES.md`, `RISK_LOG.md`, `AI_USAGE_LOG.md`, `validation/README.md` updated with RU-09 findings.
