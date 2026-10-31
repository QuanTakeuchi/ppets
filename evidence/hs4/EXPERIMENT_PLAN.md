# HS4 experiment plan (written before any HS4 experiment was run)

Written 2026-10-24, before the runs below. Thresholds were set in advance and
are not changed after the results are seen; any later deviation is recorded
in the "Deviations" section at the end, not by editing a threshold.

## Question

**Is the extinction threshold d\* a stable, precisely measurable property of
the PPETS model, or an artefact of replicate noise, seed choice, grid size and
parameter setting? And can it be measured at honest replicate counts in usable
time?**

d\* is the initial predator density at which P(extinction of either species
by generation 150) = 0.5. It is estimated by logistic regression of the binary
outcome on initial predator density (FR10), with a delta-method and a
stratified-bootstrap 95% interval.

Why this question: RU-07 found that 3-replicate cells cannot place a
threshold (RL-06), and that the claimed threshold may be an early transient
controlled by initial density only (RL-07). FR10 (d\* with interval), FR11,
FR13 and NFR07/08/10 all depend on the answer.

## Fixed protocol (unless an experiment says otherwise)

30×30 toroidal grid; prey_density 0.30; prey_repro_rate 0.20;
predator_repro_rate 0.15; prey_death_threshold 3; starvation_rate 3; 150
generations. Predator density axis 0.06–0.40, step 0.02 (18 levels), 30
replicates per level = 540 runs per study. Seeds: `replicate_seed(master, i,
j, rep)` (numpy SeedSequence). 15 worker processes.

## Experiments and pre-set pass/fail thresholds

| ID | Experiment | Master seeds | Pass if |
| --- | --- | --- | --- |
| E1 | Correctness: full pytest suite; the 8 defect reproducers re-run against the `hs3-baseline` code (they must fail there); serial vs 15-worker run of one study | — | all tests pass; all 8 reproducers fail on the baseline for the stated reason; serial and parallel outputs are identical run for run |
| E2 | Performance: step latency vs grid size (10–100); worker scaling 1–16 on a fixed 96-run job; cProfile of one 150-generation run | fixed | a 3,000-run 30×30 study projects to ≤ 15 min on this machine (RU-07 A2 assumption) |
| E3 | Precision vs replicate count: 5 independent studies (L30), pooled to 150 replicates per level, subsampled to n = 3, 5, 10, 30, 60, 150 | 4001–4005 | at n = 30 the d\* 95% interval half-width is ≤ 0.02 (density units) |
| E4 | Between-study reproducibility: d\* from each of the 5 studies in E3 | 4001–4005 | at least 4 of 5 study intervals contain the pooled d\*; between-study SD ≤ 1.5 × the mean within-study standard error |
| E5 | Finite size: same protocol at L = 20, 40, 50 (L = 30 from E3) | 4011–4013 | d\* differs from L = 30 by < 0.02 at every size (otherwise: report the trend, claim is size-specific) |
| E6 | Reproduction-rate ablation: predator_repro_rate 0.05 and 0.30 (0.15 from E3) | 4021–4022 | d\* differs from the 0.15 value by < 0.02 at both settings (tests the RU-07 claim that the reproduction rate does not matter) |
| E7 | Horizon: one study run to 300 generations | 4031 | d\*(300) − d\*(150) < 0.02 and no extinction after generation 150 in more than 1% of runs |
| E8 | Old vs new seeding (comparison baseline): rerun the HS3 600-run design (20 densities × 10 repro rates × 3 reps) under SeedSequence seeding and compare with the HS3 results | 4041 | per-density extinction proportions differ at Fisher p < 0.05 in no more than 2 of 20 densities, and the two d\* intervals overlap |

Intervals: the stratified-bootstrap percentile interval (1,000 resamples) is
primary; the delta-method interval is reported alongside. For E7, d\*(150) is
computed from the same 300-generation runs (extinct by generation 150), so
the comparison is paired. (Clarification added 2026-10-24 while the studies
were running and before any result was inspected.)

A threshold that fails is reported as a failure, with its consequence for the
project plan.

## Deviations

Recorded 2026-10-24 after the runs. No threshold, protocol setting, seed or
study was changed after results were seen.

1. **Analysis script fix (no effect on numbers).** The first analysis run
   crashed while drawing Figure 1: at p = 0 the Wilson lower bound exceeded p
   by a floating-point rounding error, giving a "negative" error bar. Error
   bars are now clipped at 0. `hs4_results.json` was written before the crash
   and its values are unchanged by the fix.
2. **Post-hoc diagnostics added after seeing the results** (not tests; no
   thresholds):
   - Pearson goodness-of-fit of the logistic curve on the pooled 30×30 data,
     added because Figure 1 showed zero extinctions where the curve predicts
     some.
   - A model-free d\* (isotonic regression, interpolated 0.5 crossing, same
     stratified bootstrap), added because the lack of fit could bias the
     logistic d\*.
   - A least-squares fit d\*(L) = a + b/L over the four grid sizes, to
     describe the E5 trend.
   - Pool start-up time (one-run sweep), to check a claim drafted for the
     issue log (HS4-06) before it was relied on.
3. E5 and E6 failed their thresholds. Both are reported as failures; the
   tolerance was not revisited.
