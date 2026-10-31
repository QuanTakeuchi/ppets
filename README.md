# PPETS — Predator-Prey Extinction Threshold Simulator

A 2D cellular-automaton predator-prey simulator with a headless CLI and a
PyQt6 GUI, built for the HU Applied Project research question "Simulating
Extinction Thresholds in Predator-Prey Systems." Scoped throughout as an
**educational simulation with sensitivity/uncertainty reporting** — not a
forecasting tool — per the approved Fall 2026 project scope and the
requirement set frozen at Hard Stop 2 (FR01–FR16 / NFR01–NFR12).

## Quick start

```bash
pip install -r requirements.txt
python main.py          # headless CSV trace of the engine
python run_ui.py         # PyQt6 GUI: configure, watch, pause/step/reset
pytest -v                 # 40 passed + 8 xfailed (known-defect reproducers)
```

Reproduce this checkpoint's coverage and smoke-test evidence (see `evidence/`):

```bash
python -m coverage run --source=ppets -m pytest -q
python -m coverage report -m
```

## Repository structure

```
ppets/
  simulation/    Module 1 — Simulation Engine (LLD §2-5): SimulationConfig,
                 Grid, Cell rules, CellularAutomatonEngine, PopulationStats
  controller.py  Controller (LLD §1.1): Qt run loop, extinction/perf auto-pause
  ui/            Module 2 — Visualization (LLD §3): ConfigPanel, GridView,
                 ChartView, PlaybackControls, StatsPanel, MainWindow
                 + heatmap_view.py (Module 3 UI shell, not yet wired in)
  analysis/      Module 3 — Analysis (LLD §4.1): ThresholdAnalyzer skeleton
tests/           pytest suite, one file per module/concern
experiments/     standalone research scripts, not part of the app — see
                 experiments/README.md
evidence/        smoke-test / coverage output captured for this checkpoint
                 (regenerate with the commands above; don't hand-edit)
main.py          headless CSV entry point
run_ui.py        GUI entry point
```

## Engineering conventions

- **Naming.** snake_case modules/functions, PascalCase classes. Where the
  LLD names a class or method (e.g. `ThresholdAnalyzer`, `runSweep`), the
  code uses that name (snake_cased for methods: `run_sweep`) so the
  traceability back to the design doc stays obvious.
- **Branching.** Trunk-based: `main` is expected to pass `pytest` at every
  commit. A module-sized unit of work gets a short-lived `feature/<name>`
  branch, merged back into `main` with `--no-ff` (so the branch boundary
  stays visible in `git log --graph`), then deleted.
- **Tags.** One annotated tag per Hard Stop submission, named
  `hsN-baseline` (this checkpoint: `hs3-baseline`), so a later sprint can
  diff against exactly what was graded.
- **Artifact storage.**
  - Application code → `ppets/`; its tests → `tests/`.
  - One-off research/report scripts → `experiments/`; their generated
    output is gitignored, never committed (regenerate on demand).
  - Deliverable write-ups (proposal/brief/design-review/report `.docx`)
    belong in the course folder tree one level up
    (`ResearchMethodology/HSx_...Package/`), not in this code repository —
    see `KNOWN_ISSUES.md` KI-01 for a current violation of this rule that's
    flagged but not yet cleaned up.
  - Every quantitative claim made in any submitted package ships with the
    script that regenerated it (established at HS2, continued here via
    `evidence/`).

## Documentation map

- [ARCHITECTURE.md](ARCHITECTURE.md) — module map, what's built vs.
  skeleton, LLD traceability, design decisions made this checkpoint
- [CHANGELOG.md](CHANGELOG.md)
- [KNOWN_ISSUES.md](KNOWN_ISSUES.md)
- [RISK_LOG.md](RISK_LOG.md)
- [SPRINT_REFLECTION.md](SPRINT_REFLECTION.md) — Hard Stop 3
- [AI_USAGE_LOG.md](AI_USAGE_LOG.md)
- [ENVIRONMENT.md](ENVIRONMENT.md) — what the evidence ran on, what is verified vs partial (RU-06)
- [VALIDATION_MEMO.md](VALIDATION_MEMO.md) — technical memo interpreting the RU-06 early evidence
- [validation/README.md](validation/README.md) — the repeatable validation suite
- `requirements-lock.txt` — exact versions behind the evidence
- [ppets/README.md](ppets/README.md) — the Engine/Controller/UI
  implementation notes from the previous pass (design deviations, etc.)

## Current status (RU-06, 2026-10-10)

| Works (checked, repeatable) | Partial / not yet |
| --- | --- |
| Engine, seeded determinism, CSV trace (`main.py`) | No "Run Sweep" control in the GUI (KI-03) |
| GUI run loop: config -> controller -> grid/chart/stats | `HeatmapView` axes show indices, not values (DEF-05) |
| `ThresholdAnalyzer.run_sweep()` (sequential) + `HeatmapView` render | Sweep is serial: ~12 min for the 600-run baseline (RL-02) |
| 12-check validation suite, clean-venv reproduction | `extinction_risk` has no predictive skill (DEF-10) |
| 8 documented defects with executable reproducers | 3-replicate cells are noise-limited (RL-06) |

Run `python validation/run_validation.py` for the full report; interpretation in `VALIDATION_MEMO.md`.

## Tests

```
tests/
  test_config.py            SimulationConfig.validate() edge cases
  test_engine.py             Cell rules, boundary modes, extinction, seed reproducibility
  test_controller.py          SimulationController state machine
  test_threshold_analyzer.py   ThresholdAnalyzer sweep/cancel/warning (new this checkpoint)
  test_heatmap_view.py         HeatmapView render smoke test (new this checkpoint)
  test_known_defects.py        8 strict-xfail reproducers for defects found at RU-06
validation/                    repeatable early-validation scripts (RU-06) -> evidence/validation/
```
