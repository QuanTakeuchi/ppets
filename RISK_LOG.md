# Risk and Issue Log

| ID | Risk | Severity | Mitigation | Owner | Status |
| --- | --- | --- | --- | --- | --- |
| RL-01 | Deliverable documents (Final Project Report, HLD/SRS `.docx`) sitting untracked inside the code repository could be lost (not backed up by git) or accidentally swept into a code commit, bloating history with large binaries. | Medium | Relocate to the course `ResearchMethodology/` folder tree (where equivalent copies already live) once confirmed safe to move; until then, never `git add -A` in this repo — stage files by name only (already this project's practice). | Student | Open |
| RL-02 | `ThresholdAnalyzer.run_sweep()`'s sequential execution could make a realistic UC03 sweep (the grid sizes `experiments/sweep.py` already uses: 20x10x3 = 600 full engine runs) too slow to be usable once wired into the GUI, risking an NFR01-adjacent perceived-performance complaint. | Medium | Parallelize with `multiprocessing.Pool` per the literal LLD §4.1 pseudocode before wiring the "Run Sweep" button into the UI (KI-02); benchmark first using `experiments/sweep.py` timing as a baseline. | Student | Open, planned next sprint |
| RL-03 | Scope creep: Module 3 is approved Fall 2026 scope, but Module 4 (`ScenarioManager`/`ReportExporter`) and historical-case-study auto-fit are not, and are easy to start "just one small piece of" under deadline pressure. | Low | Keep HS2's frozen requirement set (FR01–FR16/NFR01–NFR12) as the only in-scope backlog; anything else goes in this log as a future risk, not code. | Student | Monitored, no action needed yet |
| RL-04 | Hard Stop 3 due Oct 11, 2026 — 8 days from this checkpoint's start (Oct 3). Remaining Module 3 integration work (UI wiring, parallelization, `extinction_risk` hookup) is explicitly deferred past this checkpoint, so Hard Stop 4 (Oct 25) carries that load plus whatever its own assignment adds. | Medium | Reflected explicitly in SPRINT_REFLECTION.md's next-sprint plan rather than silently assumed; revisit load at HS4 kickoff. | Student | Open, scheduling risk |
| RL-05 | No CI pipeline runs `pytest` automatically on push — "`main` is always green" is currently an unenforced convention, not a guarantee. | Low | Add a minimal CI workflow (`pytest` on push to `main`) as early HS4 work if time allows; until then, treat it as manual discipline, not a safety net. | Student | Open, tracked |

---

## Reviewed at Hard Stop 3 / RU-06 (2026-10-10)

Changes to existing rows (evidence in `evidence/validation/`):

- **RL-02 (sweep too slow) - now measured, not guessed.** The 600-run baseline sweep took 710.9 s serial (1.18 s/run at 30x30).
  A 64-run job list ran 5.4x faster on a 16-logical-core process pool with identical results. Projection for an
  uncertainty-aware 10x10-cell, 30-replicate sweep at 30x30: ~58 min serial, ~11 min parallel. Still **Open, Medium -> High for the midpoint demo**: the GUI cannot run an honest sweep in demo time without parallelism and coarse axes.
- **RL-04 (schedule)**: RU-06 consumed the benchmark/validation work that was planned for HS4 kickoff; the HS4 list is
  unchanged otherwise. Stays Open.

New rows:

| ID | Risk | Severity | Mitigation | Owner | Status |
| --- | --- | --- | --- | --- | --- |
| RL-06 | **Statistical adequacy.** A 3-replicate heatmap cell has granularity 1/3 and a Wilson 95% interval up to [0.06, 0.79]. In the selection-free re-test, 14 of 33 disjoint triples for a cell with true p ~ 0.36 were more than 0.25 away from the 100-replicate estimate, and triples ranged 0.0-1.0. Any threshold drawn from 3-replicate cells is noise-limited. | High | Default >= 30 replicates for reported results; show a per-cell Wilson interval or replicate count in `HeatmapData`/`HeatmapView`; keep 3 only for smoke tests. | Student | Open - decide at supervisor meeting |
| RL-07 | **Claim scope.** The detected "threshold" is an *early, transient predator die-off* (predator extinctions are 195 of the 227 extinctions in the baseline sweep and 258 of 270 in the pilot; every pilot extinction happens by generation 48, median 21) controlled mainly by initial predator density, almost independent of predator reproduction rate in the swept range. Describing it as a long-run extinction threshold of an ecosystem would overclaim. | High | Word results as "initial-condition threshold for early predator die-off in this CA at 30x30, toroidal, 150 generations"; extend the pilot to other grid sizes/boundary modes before generalising. | Student | Open |
| RL-08 | **Seed rule fragility** (DEF-04/DEF-09): per-run seeds come from builtin `hash()` of a float tuple; behaviour across Python versions is not guaranteed and no master seed exists. | Medium | Switch to `SeedSequence.spawn` when `ThresholdAnalyzer` is parallelised; re-baseline and record the old->new mapping. | Student | Open |
| RL-09 | **Evidence is single-machine.** All timings come from one Windows 11 / 16-logical-core / Python 3.14.4 machine under an OneDrive-synced path; nothing was run on a second machine or OS. Numbers are indicative, not portable. | Low | Treat timings as order-of-magnitude; re-run `validation/bench_sweep.py` on the demo machine before the midpoint review. | Student | Open |

---

## Reviewed at Hard Stop 4 / RU-08 (2026-10-24)

Evidence: `evidence/hs4/hs4_results.json`, `benchmark.json` (each with a manifest).

Changes to existing rows:

- **RL-02 (sweep too slow) — mitigated.** `ThresholdAnalyzer(workers=N)` runs a Pool; 540-run studies took 28–225 s with 15 workers; projection for 3,000 runs in `benchmark.json`.
- **RL-06 (statistical adequacy) — mitigated for d\*.** At 30 replicates per level the d\* bootstrap half-width is about 0.009 (E3); five independent studies agree (E4). Per-cell heatmap display still needs ≥ 30 per cell.
- **RL-07 (claim scope) — confirmed and widened.** d\* depends on grid size (E5) and on predator reproduction rate above 0.20 (E6). Claim must be stated per setting (decisions D1, D2 in the HS4 package).
- **RL-08 (seed fragility) — closed.** SeedSequence seeding; old and new seeding agree statistically (E8).
- **RL-10 (Must requirements unbuilt)** — FR10, FR11, FR14 earned in code; FR12 and FR16 (in production) remain.

New rows:

| ID | Risk | Severity | Mitigation | Owner | Status |
| --- | --- | --- | --- | --- | --- |
| RL-12 | **Estimator misspecification.** The logistic curve fails a goodness-of-fit test on the pooled 30×30 data (Pearson p ≈ 0.007) and its d\* sits about 0.013 above a model-free estimate; its interval covers replicate noise only. | High | Report model-free d\* beside logistic; test an asymmetric (cloglog) link (B3). | Student | Open |
| RL-13 | **Finite-size dependence.** d\* rises from about 0.21 (20×20) to 0.29 (50×50) with no evidence yet of convergence; any single-size d\* is a property of that size. | High | FR13 never cut; add L = 75 (and 100 if feasible) (B2). | Student | Open |
| RL-14 | **Uncommitted evidence base.** HS4 results were produced from an uncommitted working tree (fingerprint recorded in every manifest). | Medium | Commit and tag `hs4-evidence` (B1) before submission. | Student | Open |

---

## Reviewed at Week 9 / RU-09 (2026-10-31)

Evidence: `evidence/ru09/ru09_results.json`.

- **RL-07 (claim scope) — widened.** "Extinction" is two failure modes; prey-first is 87% at reproduction rate 0.30 and 16% at the default.
- **RL-12 (estimator misspecification) — quantified, not closed.** Log-log meets the HS4 D3 rule; cloglog is the worst fit, so the HS4 B3 proposal is withdrawn. The application still uses logistic.
- **RL-13 (finite-size dependence) — confirmed, still High.** d\* rises through L = 150 (0.384, log-log); the D1 trigger was not met; the 1/L fit failed; a prospective scaling prediction was refuted.
- **RL-14 (uncommitted evidence) — closed.** HS4 and RU-09 work committed by file name on branch `ru09-results` and tagged `hs4-evidence`; `python validation/ru09_studies.py --check-fingerprint` confirms the tag holds the evidenced `ppets/` code. Not yet merged to `main` or pushed.
