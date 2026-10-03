# Sprint Reflection — Hard Stop 3 (Implementation Baseline, Assignment RU-05)

**Period:** Sep 27 – Oct 3, 2026 prep (due Oct 11, 2026)

## What was completed

- Stood up `ppets/analysis/` as the Module 3 skeleton explicitly flagged
  "not yet built" in the HS2 Design Review: `ParamRange`, `HeatmapData`,
  and a real (if sequential) `ThresholdAnalyzer.run_sweep()` /
  `cancel()` / `get_heatmap()`, matching the LLD §4.1 class diagram and
  algorithm rather than inventing an interface from scratch.
- Added the matching UI shell, `HeatmapView` (LLD §3.3), rendering a
  `HeatmapData` via `pyqtgraph` — deliberately not wired into
  `MainWindow` yet.
- 11 new tests (40 total, all passing). A real bug — `HeatmapView`'s
  axis-label call failing because `pyqtgraph.ImageView`'s default
  `ViewBox` has no `setLabel()` — was caught by the test suite on the
  first run, before it was ever tagged or shipped.
- Fixed a genuine reproducibility defect: `experiments/sweep.py` (moved
  from the repo-root `_experiment_sweep.py`) had a hardcoded,
  session-specific absolute output path that would not have worked on a
  different machine; it now writes to a repo-relative, gitignored
  directory.
- Established the repo's engineering conventions (branching, tagging,
  artifact storage) and *applied* them this same checkpoint rather than
  leaving them as aspirational text.
- Captured smoke-test evidence in `evidence/`: full pytest run (40/40),
  coverage report (62% on `ppets/`), headless `main.py` CSV trace, and an
  offscreen Qt construction check for the GUI layer.
- Tagged the baseline (`hs3-baseline`) on `main` after merging the work
  in on a short-lived feature branch.

## What is blocked

Nothing is blocked on an external dependency or decision. The scope
choices below were made deliberately by the student, not forced by a
blocker.

## What was deliberately deferred, and why

- **UI wiring** (a "Run Sweep" control, incremental heatmap redraw):
  doing this before `ThresholdAnalyzer`'s algorithm had test coverage
  would mean debugging two new, interacting layers at once. Sequencing:
  algorithm correct and tested first, UI integration next.
- **`multiprocessing` parallelization**: the LLD's pseudocode
  parallelizes `runSweep()`; implementing that correctly (worker-process
  RNG independence, pickling `SimulationConfig`, exception propagation
  from worker processes) is real complexity that changes performance,
  not the behavior under test — so it's deferred past the sequential
  version's test suite, and tracked as a new risk (RISK_LOG.md RL-02)
  rather than silently dropped.
- **Relocating the stray deliverable `.docx` files out of the code
  repo** (KI-01/RL-01): touches files outside this checkpoint's scope
  that the student may be actively using elsewhere; flagged rather than
  acted on unilaterally.

## Lessons learned

- The LLD already specified Module 3's interface in enough detail
  (member table + pseudocode) that building the skeleton directly
  against it — rather than guessing — surfaced the axis-label bug
  through a test immediately, not through a manual GUI click-through
  days later. A concrete payoff from HS2's design-review discipline.
- "Baseline" and "fully built" are different bars, and the assignment's
  own wording ("smallest demonstrable technical path," "placeholder
  model") matches what got built: a correctness-tested sequential core
  with explicitly stubbed UI and parallelization layers, each one logged
  rather than hidden.

## Next sprint target (toward Hard Stop 4, due Oct 25, 2026)

1. Wire `ThresholdAnalyzer`/`HeatmapView` into `MainWindow` behind a
   "Run Sweep" control (closes KI-03).
2. Benchmark the sequential sweep against a realistic grid (reusing
   `experiments/sweep.py`'s parameter ranges) to decide whether
   multiprocessing (KI-02/RL-02) is actually necessary before building it.
3. Replace `PopulationStats.extinction_risk`'s placeholder heuristic with
   a `ThresholdAnalyzer`-derived metric (KI-04).
4. Revisit RL-01 (stray deliverable docs in the repo) with the student
   before Hard Stop 4 submission prep begins.
