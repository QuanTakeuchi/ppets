# HS6 / RU-12 final-test plan (written before the final runs)

Written 2026-11-21, after a 120-run pilot of the new well-mixed mode (described
below) and before any of the studies or analyses in this file were run. Rules
are not edited after results are seen; changes go under "Deviations".

Source of the questions: the RU-11 feedback as recorded in the student's Week 12
handoff worksheet (Nov 17): RQ2 needs the well-mixed baseline (FR12); the
estimator choice needs a justification that does not assume its own answer, and
the estimators belong in production; the two extinction pathways need to be
reported separately.

## Code under test

The HS6 change set under `ppets/`, as one bundle (decision D-HS5-1: the HS5-05
and HS5-07 fixes ride with the estimator change):

- `SimulationConfig.mixing` = `"spatial"` (default, unchanged) or `"well_mixed"`.
  In well-mixed mode each cell's 8 Moore neighbours are replaced by 8 distinct
  cells drawn uniformly from the rest of the grid, once per cell per generation.
  Every rule, parameter, density level, replicate count, horizon and seed rule is
  the same. Only partner choice changes.
- `ppets.analysis.estimate_threshold` (log-log default, model-free, logit) and
  `pathway_table`, moved from `validation/ru09_analyze.py`.
- Type checks in `SimulationConfig.validate()` (HS5-07) and the half-installed
  PyQt6 guard in `ppets/__init__.py` (HS5-05).

This changes the `ppets/` fingerprint, so `ru09_studies.py` refuses to run (by
design). F0 below shows that the change leaves the spatial model's output
unchanged.

## Pilot (seen before this plan)

120 well-mixed runs (10 seeds × 6 densities from 0.002 to 0.06, at 30×30 and
75×75): every run went extinct within 150 generations, almost always prey first.
The plan therefore adds low-density levels: with the standard levels alone, the
well-mixed curve would be flat at 1 and give no d\*.

## Questions and rules

| ID | Question | Data | Rule |
| --- | --- | --- | --- |
| F0 | Does the HS6 code change the spatial model? | Regenerate published studies `L20_s4011` and `L30_s4001` with the HS6 code | Pass if both CSVs are byte-identical to the committed files (sha256 equal to their manifests). |
| F1 | RQ2: does spatial structure change d\*? (FR12) | New well-mixed studies with the HS4 protocol (18 levels 0.06-0.40, 30 replicates, 150 generations): `WM30_s4001`, `WM30_s4002` (30×30) and `WM75_s4014` (75×75). They reuse the master seeds of the spatial studies, so each run starts from the same initial grid as its spatial twin. Low-density extension: `WMlow30_s4061` (0.002-0.020, step 0.002) and `WMlow75_s4062` (0.001-0.010, step 0.001), 30 replicates. | Report d\* (log-log and model-free) per mode and size, and spatial minus well-mixed with a bootstrap interval. If the well-mixed curve never falls below 0.5 in the tested range, its d\* is reported as "below the lowest tested density" with that bound, and the difference as a lower bound. Paired check: share of spatial-surviving runs whose well-mixed twin went extinct. |
| F2 | Is the log-log choice robust when log-log is NOT the true curve? (feedback on RU-09 Q2b) | Simulated studies at the 18 HS4 levels. Truths: (a) the fitted logistic curve, (b) the fitted cloglog curve (opposite asymmetry), (c) the isotonic (PAVA) curve of the pooled 30×30 data, with no parametric shape. 200 studies per truth at 30 and at 150 replicates per level, 200 bootstrap draws each. | Descriptive, with one pre-set reading: the log-log estimator is "robust" if its 95% interval covers the true d\* in at least 90% of studies under truth (c) at both replicate counts. Otherwise the model-free estimator is reported as the headline beside it. |
| F2b | Real-data coverage, no assumed truth | The five independent 30×30 studies | For each study: does its log-log 95% interval contain the log-log d\* of the other four pooled? Descriptive. |
| F3 | Extinction pathways separately | All spatial studies, plus F1 | Per density: P(predators first), P(prey first), P(extinct), each with a Wilson 95% interval, from `ppets.analysis.pathway_table`. Check: the counts add up at every level. No shared threshold is claimed for the two pathways. |
| F4 | Reproduction-rate table re-estimated with log-log (consistency check from the handoff) | `r05_s4021`, `r30_s4022`, pooled L30 | Report log-log, model-free and logit side by side. Descriptive. |
| F5 | Final suite | Whole repository | `pytest` all pass, `run_validation.py` 12/12, `hs5_verify_evidence.py` all files match, reference run matches. |

## Interpretation

As in RU-09, each limitation is labelled **system failed**, **model property** or
**evidence incomplete**. Well-mixed results describe this model with random
partner choice; they are not a claim about real populations.

## Deviations

Recorded 2026-11-21 after the runs. No rule above was edited.

1. **Code did not match the F1 rule at first.** The first version of
   `hs6_analyze.py` tested "every well-mixed run extinct" instead of the plan's
   "the curve never falls below 0.5". Four of 2,220 well-mixed runs survived (at
   densities 0.001-0.003), so the first run crashed in the difference branch.
   The condition was corrected to the plan's wording before any result was
   read. Outcome: no crossing at either size; the difference is reported as a
   lower bound, as planned.
2. **F2 rule not met.** Log-log coverage under the isotonic truth was 80.5% (30
   replicates) and 45.5% (150), below the pre-set 90%. As the rule says, the
   model-free estimate is reported as the headline from HS6 on, with log-log
   beside it. The software default (`DEFAULT_METHOD = "loglog"`) is not changed
   in this checkpoint; `estimate_threshold` returns both. Whether to switch the
   default is put to the student (decision D-HS6-1).
3. **Pathway crossings not reported.** `hs6_analyze.py` also records where each
   pathway's isotonic curve reaches 0.5. P(predators first) is not monotone in
   density (prey-first takes over at high density), so an isotonic fit of it is
   not meaningful. The values stay in the JSON for completeness and are not
   cited, in line with "no shared threshold is claimed".
4. **Well-mixed horizon.** Some low-density well-mixed runs went extinct as late
   as generation 150, so the four survivors may be censored. This strengthens,
   not weakens, the "no crossing" result.
