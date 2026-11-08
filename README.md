# PPETS — Predator-Prey Extinction Threshold Simulator

PPETS is a 2D cellular-automaton predator-prey simulator with a headless
command line, a PyQt6 GUI, and a parameter-sweep module that estimates the
initial predator density, d\*, at which a predator-prey system usually goes
extinct, with uncertainty intervals.

It was built for the Harrisburg University Applied Project "Simulating
Extinction Thresholds in Predator-Prey Systems" (Fall 2026). It is an
**educational simulation**, not a forecasting tool: every threshold it
reports belongs to one grid size, boundary mode and parameter setting (see
[What the results mean](#what-the-results-mean)).

- **Status:** Hard Stop 5 (2026-11-08). 109 tests, 12 validation checks and a clean-environment
  run pass on Windows 11 with Python 3.14 and 3.11 ([evidence/hs5/](evidence/hs5/)).
- **Code state of the published results:** tag `hs4-evidence`; `ppets/` fingerprint `0c61dd14fdaad6a8`.
- **Runbook:** [RUNBOOK.md](RUNBOOK.md) covers every execution path, its configuration and expected output.

## Prerequisites

| Need | Version / detail |
| --- | --- |
| Python | 3.11 or newer. Tested: 3.14.4 (lock file) and 3.11.9 (`requirements.txt`), Windows 11. |
| OS | Windows 11 tested. Linux and macOS are expected to work but are untested here; the CI workflow adds Ubuntu once it has run. |
| Hardware | Any 64-bit machine with 2 GB free RAM. The test suite runs in under 1 minute. The full studies used 16 logical CPUs (see RUNBOOK). |
| Disk | About 400 MB for the virtual environment (mostly PyQt6). |
| Network | Only for `pip install`. PPETS calls no external service and needs no account, API key or `.env` file. |
| Display | Needed for the GUI only. Tests and scripts run headless with `QT_QPA_PLATFORM=offscreen`. |
| git | Optional; used to record provenance and to check out the evidence tag. |

## Setup

**Windows: clone to a short path** such as `C:\src\ppets`. PyQt6 installs
files about 150 characters deep inside `.venv`, so a long checkout path breaks
`pip install` unless Windows long paths are enabled (friction point FP-01).

```bash
git clone https://github.com/QuanTakeuchi/ppets.git
cd ppets
python -m venv .venv
```

Activate the environment: `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (Linux/macOS). Then:

```bash
python -m pip install -r requirements-lock.txt
python check_env.py
```

`requirements-lock.txt` pins the exact versions behind the evidence. Use
`requirements.txt` for the latest compatible versions instead, and
`requirements-optional.txt` (matplotlib) only to regenerate figures.

`check_env.py` should end with `READY: 0 failed`. Warnings are advisory. For
example, a repository inside OneDrive or Dropbox gets a warning.

## Run it

| Command | What it does | Expected output | Time |
| --- | --- | --- | --- |
| `python main.py` | One seeded 30×30 run, CSV trace to stdout | 52 lines, header `generation,prey_count,predator_count`, last line `50,592,55`; identical to [evidence/hs5/main_expected.txt](evidence/hs5/main_expected.txt) | < 1 s |
| `python main.py --config configs/default.json` | Same run, parameters from a file | Same as above | < 1 s |
| `python main.py --seed 7 --generations 200 --output trace.csv` | Any parameter from the command line (`python main.py --help`) | `trace.csv` | seconds |
| `python run_ui.py` | GUI: set parameters, Start, Pause, Step, Reset; grid, population chart, live stats | A window; auto-pauses with a banner on extinction | — |
| `python -m pytest -q` | Unit, integration and regression tests | `109 passed` | ~20 s |
| `python validation/run_validation.py` | 12 pass/fail checks (determinism, invariants, CSV, analyzer, GUI) | `12/12 checks passed`, report in `evidence/hs5/validation/` | ~2 min |
| `python validation/hs5_verify_evidence.py` | Committed result files still match their manifests | `24/24 evidence files match` | < 1 s |
| `python validation/hs5_clean_run.py` | The whole setup above, repeated in a throwaway clone and venv | `ALL REQUIRED STEPS PASSED`, `evidence/hs5/clean_run_<label>.json` | ~2 min + pip |

Bad input exits with status 2 and a one-line message, not a traceback:
`python main.py --width 1` prints `main.py: error: Invalid SimulationConfig: width and height must both be >= 2`.

Reproducing the published studies (hours, multi-core) is described in
[RUNBOOK.md §4](RUNBOOK.md#4-reproduce-the-published-results).

## Configuration

All parameters live in `SimulationConfig` ([ppets/simulation/config.py](ppets/simulation/config.py)), which validates them.

| Parameter | Default (`main.py`) | Allowed |
| --- | --- | --- |
| `width`, `height` | 30, 30 | integer ≥ 2 |
| `toroidal` | `true` (edges wrap) | `--fixed-boundary` turns it off |
| `prey_density`, `predator_density` | 0.30, 0.10 | 0–1, sum ≤ 1 |
| `prey_repro_rate`, `predator_repro_rate` | 0.20, 0.15 | 0–1 |
| `prey_death_threshold` | 3 | 0–8 predator neighbours |
| `starvation_rate` | 3 | integer ≥ 1 generations |
| `seed` | 42 | integer; same seed gives the same run |
| `generations` (CLI only) | 50 | 1–100000 |

Precedence: built-in defaults < `--config` file < command-line flags. A
config file is a JSON object of these fields
([configs/default.json](configs/default.json)). Unknown or mistyped keys are
rejected by name.

**Seeds.** A single run is fully determined by its seed. A sweep
(`ThresholdAnalyzer`) derives each replicate's seed from
`SeedSequence(master_seed, spawn_key=(i, j, replicate))`. The master seed is
`base_config.seed`; if that is `None`, fresh entropy is drawn and recorded in
`HeatmapData.master_seed`. Results do not depend on the number of worker
processes.

**Environment variables.** `QT_QPA_PLATFORM=offscreen` runs Qt without a
display (CI, SSH). `PPETS_CLEAN_BASE` sets where `hs5_clean_run.py` makes its
temporary copy. Nothing else is read.

## Data

PPETS uses **no external data**. Every number comes from the simulator, given
the seeds recorded in the evidence manifests. The committed CSV, JSON and PNG
files in `evidence/` are outputs of this repository's own scripts, and each
has a `.manifest.json` with the script, seeds, code fingerprint and versions.
They contain no personal data. Some older pytest and profiling logs show a
local Windows user name inside file paths (KNOWN_ISSUES HS5-04).

The HS2 literature brief profiled GBIF occurrence data for context only. That
data is not an input to PPETS and is not redistributed here.

**Licence:** none has been chosen yet (KNOWN_ISSUES HS5-03). Until one is
added, the code is public to read but not licensed for reuse.

## What the results mean

The RU-09 results put d\* at 0.241 at 30×30 and 0.384 at 150×150 (log-log
fit). It is still rising with grid size, so no single value is "the" threshold.
"Extinction" combines predator-first and prey-first collapse. The
application's built-in estimator, `fit_threshold`, is logistic and biased
high by about 0.009 (KNOWN_ISSUES RU9-01). Details:
`PPETS_RU09_Results_and_Limitations_Memo.docx` (course folder) and
[KNOWN_ISSUES.md](KNOWN_ISSUES.md).

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `pip install` fails with `OSError: [Errno 2] No such file or directory: ...\PyQt6\Qt6\qml\...` and a long-path hint | Windows 260-character path limit | Clone to a short path (`C:\src\ppets`), delete `.venv`, reinstall. Or have an administrator enable long paths. |
| `import ppets` or `python main.py` fails with `TypeError: expected str, bytes or os.PathLike object, not NoneType` in `ppets/__init__.py` | PyQt6 half-installed by the failure above | `python check_env.py` confirms it. Remove `.venv` and reinstall from a short path. |
| `ImportError: DLL load failed while importing QtWidgets` | Another program's Qt DLLs on `PATH` (seen with MiKTeX) | Already handled by `ppets/__init__.py`. Import `ppets` before PyQt6 in your own scripts. |
| `ModuleNotFoundError: No module named 'scipy'` during pytest collection | Installed from a pre-HS5 `requirements.txt` | `python -m pip install -r requirements.txt` again. |
| `pytest: command not found` | venv not activated | Use `python -m pytest`. |
| `qt.qpa.plugin: Could not load the Qt platform plugin "xcb"` (Linux) | No display or missing Qt libraries | `export QT_QPA_PLATFORM=offscreen`. For the GUI, install `libegl1 libxkbcommon0 libfontconfig1`. |
| `ru09_studies.py` refuses to run: fingerprint mismatch | `ppets/` differs from the code behind the RU-09 evidence | `git checkout hs4-evidence` for an exact reproduction. |
| GUI shows "Performance" auto-pause on large grids | Steps above 100 ms for 5 generations (NFR01) at about 100×100 and up | Expected. Use a smaller grid or the headless scripts. |
| Long runs fail with permission errors under OneDrive | Sync client locking files | Move the clone out of the synced folder. |

## Repository map

```
ppets/            the application (frozen at the hs4-evidence fingerprint;
                  its README.md is the August 2026 design note, now historical)
  simulation/     Module 1: SimulationConfig, Grid, cell rules, engine, PopulationStats
  analysis/       Module 3: ThresholdAnalyzer (parallel sweeps), Wilson intervals, d* fit
  ui/             Module 2: GUI widgets and HeatmapView
  controller.py   Qt run loop with extinction/performance auto-pause
main.py           headless CLI          run_ui.py   GUI entry point
check_env.py      preflight check       configs/    example run configuration
tests/            pytest suite (109 tests)
validation/       evidence scripts by hard stop (see validation/README.md)
experiments/      the original GRAD 695 sweep script
evidence/         committed outputs; see evidence/README.md for which folder is which
.github/workflows/ci.yml   smoke test on push (Windows + Ubuntu)
```

Project records: [RUNBOOK.md](RUNBOOK.md) · [ARCHITECTURE.md](ARCHITECTURE.md) ·
[ENVIRONMENT.md](ENVIRONMENT.md) · [KNOWN_ISSUES.md](KNOWN_ISSUES.md) ·
[RISK_LOG.md](RISK_LOG.md) · [CHANGELOG.md](CHANGELOG.md) ·
[AI_USAGE_LOG.md](AI_USAGE_LOG.md) · [VALIDATION_MEMO.md](VALIDATION_MEMO.md) (RU-06) ·
[evidence/hs5/REPRODUCIBILITY_NOTES.md](evidence/hs5/REPRODUCIBILITY_NOTES.md)

## Engineering conventions

- Trunk-based: `main` passes `pytest` at every commit; short-lived `feature/<name>` branches merge with `--no-ff`.
- One annotated tag per graded checkpoint (`hs3-baseline`, `hs4-evidence`).
- Stage files by name; never `git add -A` (three untracked Word files in the root must stay out, RISK_LOG RL-01).
- Every reported number is regenerated by a committed script and written with a manifest; evidence files are never hand-edited.
- Names follow the LLD (`ThresholdAnalyzer`, `run_sweep`), so code traces back to the design.
