# Architecture Notes

> **Status update (HS5, 2026-11-08).** Module 3 is no longer a skeleton: since HS4
> `ThresholdAnalyzer` runs on a process pool with `SeedSequence` seeds and per-cell
> Wilson intervals, and `estimates.py` fits d\*. The GUI still has no Run-Sweep control (KI-03).
> Execution paths and configuration: [RUNBOOK.md](RUNBOOK.md).

## Module map (per `PPETS_LLD.docx`)

| Module | LLD section | Status | Code |
| --- | --- | --- | --- |
| Module 1 — Simulation Engine | §2–§5 | Built (prior pass) | `ppets/simulation/` |
| Controller | §1.1 | Built (prior pass) | `ppets/controller.py` |
| Module 2 — Visualization (Grid/Chart/Playback/Stats) | §3.1/§3.2 | Built (prior pass) | `ppets/ui/{grid_view,chart_view,playback_controls,stats_panel,main_window}.py` |
| Module 3 — Analysis (`ThresholdAnalyzer`) | §4.1 | **Skeleton (new, this checkpoint)** | `ppets/analysis/threshold_analyzer.py` |
| Module 3 — Visualization (`HeatmapView`) | §3.3 | **Skeleton (new, this checkpoint)**, not wired into `MainWindow` | `ppets/ui/heatmap_view.py` |
| Module 4 — `ScenarioManager` / `ReportExporter` | §7 (LLD) | Not started | — |
| `HistoricalCaseStudy` / `autoFit` | §4.2 | Not started (stretch scope per HS1) | — |

## Data flow (current state)

```
SimulationConfig -> CellularAutomatonEngine.step() -> PopulationStats
      |-> (Controller) -> ChartView / GridView / StatsPanel     [live, built]
      |-> (ThresholdAnalyzer.run_sweep(), many seeded runs)
            -> HeatmapData -> HeatmapView                         [render only, built;
                                                                     not triggered by any UI control yet]
```

## What "skeleton" means for Module 3, this checkpoint

**Implemented for real, with test coverage (11 new tests):**
- `ParamRange` — one sweep axis (name, start, stop, step) with inclusive value generation.
- `HeatmapData` — result container matching the LLD §4.1 member table
  (`extinction_prob` matrix + axis metadata), extended with the
  per-species breakdown `experiments/sweep.py` already computes by hand.
- `ThresholdAnalyzer.run_sweep()` — **sequential**, not yet the LLD's
  `multiprocessing.Pool`-parallelized version (see KI-02 in
  `KNOWN_ISSUES.md`), with a progress callback and a cooperative
  `cancel()` that yields a partial `HeatmapData` (`complete=False`),
  matching UC03's alternate "user cancels mid-sweep" flow.
- `HeatmapView` — renders a `HeatmapData` via `pyqtgraph.ImageView`,
  axis labels bound to the swept parameter names (FR07).

**Deliberately not done yet** (see `SPRINT_REFLECTION.md` for why and when):
- A "Run Sweep" UI control wiring `ThresholdAnalyzer` into `MainWindow`/`ConfigPanel`.
- Incremental `HeatmapView` redraw as sweep cells complete.
- `multiprocessing.Pool` parallelization per the literal LLD pseudocode.
- Replacing `experiments/sweep.py`'s hand-rolled sweep with `ThresholdAnalyzer`.
- Wiring `PopulationStats.extinction_risk` (currently a placeholder
  heuristic — see `ppets/README.md`) to a real `ThresholdAnalyzer`-derived metric.

## Design decisions made this checkpoint

1. **Sequential-first sweep.** Correctness before parallelism: running the
   sweep in-process, reusing the already-deterministic, already-tested
   `CellularAutomatonEngine`, means the HS2-documented NFR02 reproducibility
   guarantee carries over directly — no new RNG-across-processes bugs to
   introduce before the simple version has test coverage.
2. **`HeatmapView` uses an explicit `pg.PlotItem()` view.** `pyqtgraph.ImageView`'s
   default `getView()` returns a bare `ViewBox`, which has no `setLabel()` —
   the test suite caught this immediately (`AttributeError` on the first
   test run) before it reached a commit.
3. **`_experiment_sweep.py` relocated to `experiments/sweep.py`.** Its
   `OUT_DIR` was a session-specific absolute temp path that only worked on
   the machine/session that happened to create it — a direct violation of
   this checkpoint's own "a peer can reproduce it" reproducibility bar.
   Fixed to a repo-relative, gitignored `experiments/output/`.
