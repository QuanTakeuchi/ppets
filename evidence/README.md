# evidence/

Committed outputs of this repository's own scripts. Each folder belongs to
one checkpoint and stays as it was submitted. Do not hand-edit anything here.
Regenerate with the script named in the file's manifest, or in the table.

| Folder | Checkpoint | Produced by | Status |
| --- | --- | --- | --- |
| `*.txt` in this folder | HS3 baseline, Oct 3 (tag `hs3-baseline`) | pytest, coverage, `main.py`, offscreen GUI smoke test | Historical. `main_smoke_test.txt` has the pre-HS4 four-column schema; the current reference is `hs5/main_expected.txt` |
| `validation/` | HS3 / RU-06, Oct 10 | `validation/run_validation.py` (then), `pilot_study.py`, `bench_sweep.py`, `make_figures.py` | Historical. Its numbers used the pre-HS4 `hash()` seeds |
| `midpoint/` | RU-07, Oct 17 | `validation/midpoint_demo.py` | Historical |
| `hs4/` | HS4 / RU-08, Oct 24 (tag `hs4-evidence`) | `validation/hs4_*.py` | Current for HS4 claims. Every result file has a `.manifest.json` |
| `ru09/` | RU-09, Oct 31 | `validation/ru09_*.py` | Current results (d\* by grid size). Manifests as above |
| `hs5/` | HS5, Nov 8 | `validation/hs5_clean_run.py`, `hs5_verify_evidence.py`, `run_validation.py` (updated) | Reproducibility pass: `REPRODUCIBILITY_NOTES.md` |
| `hs6/` | HS6 / RU-12, Nov 21 | `validation/hs6_*.py`; pytest, `run_validation.py --out`, `hs5_verify_evidence.py --out`, `hs5_clean_run.py` | Final tests and well-mixed studies. Plan and deviations: `hs6/ANALYSIS_PLAN.md`. Produced on the HS6 code (new `ppets/` fingerprint) |

Check that nothing was altered: `python validation/hs5_verify_evidence.py`
compares every file that has a manifest against the SHA-256 recorded when it
was written.
