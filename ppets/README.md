# PPETS — CA Engine Core

Implements LLD §2–§5: `SimulationConfig`, `Grid`, the `Cell` state-transition
rules, and `CellularAutomatonEngine.step()`. Also implements LLD §3
(Visualization, Module 2) and the Controller layer from §1.1, so the engine
can be watched running live instead of only read as a CSV trace.

## Structure

```
ppets/
  simulation/
    config.py   SimulationConfig — validated params + centralized RNG
    cell.py     CellState enum, Cell/PreyCell/PredatorCell rule logic
    grid.py     Grid — NumPy-backed state array, Moore neighborhood, double buffer
    engine.py   CellularAutomatonEngine — step() loop, extinction check
    stats.py    PopulationStats value object
  controller.py SimulationController — Controller layer (LLD §1.1): owns the
                engine + QTimer run loop, extinction/performance auto-pause
  ui/
    config_panel.py       ConfigPanel — parameter form, reuses SimulationConfig
                           .validate() live rather than reimplementing rules
    playback_controls.py  PlaybackControls — Start/Pause/Resume/Step/Reset + speed
    grid_view.py           GridView — QGraphicsScene/QImage grid renderer (LLD §3.1)
    chart_view.py          ChartView — pyqtgraph live prey/predator chart (LLD §3.2)
    stats_panel.py         StatsPanel — live generation/prey/predator/extinction_risk
    main_window.py         MainWindow — assembles the views, wires controller signals
main.py         manual headless CSV smoke-test runner (engine only)
run_ui.py       launches the PyQt6 visualization (`python run_ui.py`)
```

## Visualization scope (this pass)

Implements UC01/UC02 (test cases TC1–TC6): configure a run, watch the grid
and live population chart update generation-by-generation, pause/resume/step/
reset, and get auto-paused with a banner on extinction or on sustained NFR01
budget violations (5 consecutive generations over 100ms — matches the
CA engine's already-documented non-full-vectorization, see deviation #2
below; large grids legitimately trigger this rather than it being a bug).

**Out of scope for this pass** (separate LLD modules, not yet built):
Module 3 (ThresholdAnalyzer parameter sweep + HeatmapView, UC03) and Module 4
(ScenarioManager save/load, CSV/PDF ReportExporter, UC04/FR09).

**Seed echo (NFR02 / TC1 step 4):** if the seed field is left blank,
`ConfigPanel` generates a concrete seed itself (rather than passing `None`
through) so every run stays reproducible, and echoes the resolved value back
into the field once Start is clicked.

## Design deviations from the LLD as written (flagging per your request)

**1. Cell objects vs. array-backed state.**
The class diagram gives `Cell`/`PreyCell`/`PredatorCell` their own fields
(energy, hunger) as if one object lived per grid cell. I kept the class
hierarchy (so it still reads like the diagram, and new species just add a
class + a `RULES` entry — NFR06), but the actual per-cell *state* lives in
`Grid.state` (NumPy int8 array) and `Grid.hunger` (parallel int16 array),
not on individual Python objects. Instantiating one object per cell every
generation on a large grid would be needlessly slow/memory-heavy. If your
grading rubric needs literal per-cell objects with their own `energy`
field, tell me and I'll switch this back — it's a straightforward swap.

**2. Vectorization vs. the literal step() pseudocode.**
NFR01 calls for "NumPy vectorized grid updates instead of Python loops,"
but LLD §4/§5's pseudocode is inherently per-cell (shuffle order, evaluate
one cell at a time into a write buffer). Those two goals are in tension —
true full vectorization can't easily do per-cell random neighbor selection
for reproduction/predation. I implemented the literal per-cell shuffled
version (matches §4/§5 exactly, easy to reason about and extend), using
NumPy only for storage and bulk neighbor-counting. It's only vectorized
over live cells, not the whole grid, each generation. If simulation speed
becomes a real bottleneck on large grids, the neighbor-counting step is
the piece most easily rewritten with convolution — happy to do that as a
later optimization pass rather than now.

**3. Predation conflict resolution.**
Two predators can't both claim the same prey cell in the same generation —
resolved via a per-generation `Grid.eaten` marker array so the outcome
doesn't depend on shuffle order. This isn't spelled out in the LLD
pseudocode; flagging it as an implementation detail I added.

**4. `extinction_risk`.**
Field exists per the class diagram, but its real formula is a
`ThresholdAnalyzer` concern (Analysis subsystem, not yet built). Current
implementation is a labeled placeholder heuristic — replace when that
subsystem lands.

## Try it

```
pip install -r requirements.txt
python main.py       # headless CSV trace of the engine
python run_ui.py      # live GUI: configure, watch the grid + chart, pause/step/reset
pytest -v              # 29 tests: config validation, cell rules, controller state machine
```

`main.py` prints a CSV-style trace of generation, prey_count, predator_count,
extinction_risk, and stops early if either species hits zero. `run_ui.py`
opens the PyQt6 window described above.

## Tests

```
tests/
  test_config.py       SimulationConfig.validate() edge cases (the same rules TC3 exercises live)
  test_engine.py        Cell rules (death threshold, starvation, reproduction, predation-conflict
                        resolution), toroidal vs. fixed boundary, extinction, seed reproducibility
  test_controller.py     SimulationController start/pause/resume/step/reset + extinction auto-pause
```

`test_engine.py`'s prey-rule tests call `PreyCell.update()` directly instead
of going through a full `engine.step()` — a predator adjacent to prey attacks
it via a separate mechanism (direct predation), which would otherwise
confound a test specifically about the `prey_death_threshold` count check.
The predator-conflict test does go through a full `engine.step()`, since
that's genuinely testing the multi-cell interaction (`Grid.eaten`), not a
single rule in isolation.
