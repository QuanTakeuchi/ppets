# Changelog

Format loosely follows [Keep a Changelog](https://keepachangelog.com/).
Versions correspond to this project's Hard Stop tags (`hsN-baseline`), not
semantic-version releases.

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
