# validation/

Repeatable early-validation suite for Hard Stop 3 / RU-06. Run from the
repository root. Every script writes into `evidence/validation/`.

| Script | Question it answers | Runtime |
| --- | --- | --- |
| `run_validation.py` | 12 pass/fail checks (V01-V12): config, determinism, invariants, CSV pipeline, analyzer contract, analyzer-vs-script agreement, heatmap render, GUI integration, former-defect regression tests, negative control. Updated at HS5 to the HS4 contract; writes to `evidence/hs5/validation/` | ~2 min |
| `env_snapshot.py` | What machine/toolchain produced the evidence; Qt platform probes | seconds |
| `clean_restart.py` | Does a brand-new venv reproduce the results? (needs network) | ~1 min |
| `pilot_study.py` | How uncertain is a 3-replicate cell? Horizon sensitivity; value of the `extinction_risk` heuristic | ~5 min |
| `triple_retest.py` | Selection-free noise estimate from the pilot replicates | seconds |
| `bench_sweep.py` | Step latency vs grid size; serial vs process-pool throughput; projections | ~4 min |
| `make_figures.py` | Figures for the package (needs `pip install matplotlib`) | seconds |

`_common.py` / `_worker.py` are shared helpers (pool worker, Wilson interval, provenance).
Order for a full refresh: `experiments/sweep.py` -> `pilot_study.py` -> `triple_retest.py` -> `bench_sweep.py` -> `run_validation.py` -> `make_figures.py`.

RU-09 (Week 9): `ru09_studies.py` (larger-grid and trajectory studies, about 1 hour, needs the frozen `ppets/` fingerprint), then `ru09_analyze.py` (about 4 min), then `ru09_figures.py`. Plan: `evidence/ru09/ANALYSIS_PLAN.md`.

HS5 (Week 10): `hs5_clean_run.py` repeats the README setup in a throwaway clone and venv and records each step
(`--python py:3.11`, `--requirements requirements.txt`, `--validation`, `--study hs4:L20_s4011` to regenerate a
published study and compare its hash). `hs5_verify_evidence.py` checks every committed result file against its
manifest. Both write to `evidence/hs5/`. Notes: `evidence/hs5/REPRODUCIBILITY_NOTES.md`.
