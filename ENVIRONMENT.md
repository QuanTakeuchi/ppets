# Environment Notes

What the current evidence was produced on, what the project assumes, and what
has actually been checked. Source of truth: `evidence/validation/environment.json`
(regenerate with `python validation/env_snapshot.py`).

## Reference environment (2026-10-10)

| Item | Value |
| --- | --- |
| OS | Windows 11 Home 10.0.26200 (AMD64), 16 logical CPUs |
| Python | CPython 3.14.4, system install, **not** a virtualenv |
| numpy / PyQt6 (Qt) / pyqtgraph | 2.5.1 / 6.11.0 (Qt 6.11.0) / 0.14.0 |
| pytest / coverage | 9.1.1 / 7.16.2 |
| matplotlib | 3.11.1 - validation figures only, deliberately *not* in `requirements.txt` |
| Repository path | under a OneDrive-synced folder (`...\OneDrive\Documents\HU\...`) |
| Network | needed only for `pip install`; PPETS itself has no network or API dependency |

## What works

- Headless engine, `main.py`, `ThresholdAnalyzer.run_sweep()` (sequential), `HeatmapView` rendering, and the
  `MainWindow` + controller path all run on the native Windows Qt platform and on `offscreen`.
- A brand-new venv built from `requirements.txt` passes the whole suite and reproduces `evidence/main_smoke_test.txt`
  byte-for-byte (`evidence/validation/clean_restart.json`). It resolved numpy 2.5.3 rather than 2.5.1; results were identical.
- Determinism holds across interpreters and `PYTHONHASHSEED` values (check V03).

## What is partial or unverified

- **Only one machine and OS.** No Linux/macOS run, no second Windows machine.
- **No manual GUI session.** Widgets are constructed, driven programmatically and screenshotted; no one clicked through UC01-UC03.
- **No Run-Sweep control in the UI.** The sweep path is reachable only from code/scripts (KI-03).
- **`requirements.txt` is unpinned.** Use `requirements-lock.txt` for exact reproduction (DEF-12).
- **Seeds depend on CPython's tuple `hash()`** (DEF-09); stable on 3.14.4, not a documented guarantee.
- **Headless CI** would need `QT_QPA_PLATFORM=offscreen`; `validation/run_validation.py` sets it automatically only on Linux without a display.
  Offscreen screenshots have no fonts (labels render as boxes), which is why the committed screenshots use the native platform.
- **OneDrive path**: sync locks or path length could in principle interfere with `experiments/output/` and `.coverage`; no problem was observed (the evidence/ and output/ directories were writable and the 600-run sweep wrote cleanly), but it is an environmental risk the demo machine does not need.

## Reproduce from a clean restart

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements-lock.txt        # or requirements.txt for "latest compatible"
python -m pytest -q                          # 40 passed, 8 xfailed
python validation/run_validation.py          # 12 checks -> evidence/validation/validation_report.txt
python validation/clean_restart.py           # automated version of the above in a throwaway venv
```

Slow, optional (minutes): `python experiments/sweep.py` (~12 min), then
`python validation/pilot_study.py` (~5 min on 14 workers), `python validation/triple_retest.py`,
`python validation/bench_sweep.py` (~4 min), `pip install matplotlib && python validation/make_figures.py`.
