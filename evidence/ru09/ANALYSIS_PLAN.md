# RU-09 analysis plan (written before any new run or fit below)

Written 2026-10-31, before the new studies were started. Rules taken from the
signed HS4 package are quoted as such. New descriptive analyses carry no
threshold and are labelled descriptive. Any later change goes in "Deviations";
no rule is edited after results are seen.

Production code under `ppets/` is frozen for this checkpoint. Studies must run
at fingerprint `0c61dd14fdaad6a8`, the value in every HS4 manifest.

## Known exposure

The pooled 30×30 curve, its misfit and the composite-outcome counts were already
seen at HS4. Q2 and Q3 therefore use those data with knowledge of the problem,
and only the held-out comparison in Q2 and the new studies are confirmatory.

## Questions and rules

| ID | Question | Data | Rule |
| --- | --- | --- | --- |
| Q1 | Does d\* level off as the grid grows? (HS4 backlog B2) | New: L50_s4016, L75_s4014, L75_s4017, L100_s4015; HS4: L50_s4013. Same protocol as HS4 (18 levels, 30 replicates, 150 generations). | HS4 decision D1: treat as converged if abs(d\*(75) - d\*(50)) < 0.01. Pre-set here: applied to pooled L50 and pooled L75, for the logistic and the model-free estimator. The bootstrap interval of the difference is reported; if it spans 0.01 the verdict is "not resolved". |
| Q1b | Does the HS4 fit d\*(L) = 0.3397 - 2.6446/L predict the larger grids? | As Q1 | The fit is frozen from HS4 (predicts 0.3044 at L75, 0.3132 at L100). Supported if each prediction is inside the logistic 95% interval at that size. |
| Q2 | Which estimator should be reported? (HS4 backlog B3) | Fit: pooled L30 s4001-4005. Hold-out: H300_s4031 outcome at generation 150, unused in the fit. | HS4 decision D3: a link is adopted if Pearson p > 0.05 on the pooled data and it agrees with the model-free d\* within 0.005. Links compared: logit, probit, cloglog, loglog. Held-out log-loss and leave-one-study-out log-loss are reported for each. |
| Q2b | How wrong is the logistic interval if the curve is misspecified? | Simulation from the best link in Q2, 200 synthetic studies at 30 replicates per level and 200 at 150 | Descriptive: coverage of the true d\* by the logistic bootstrap interval and by the model-free interval. |
| Q3 | Is "extinction" one failure mode or several? | All HS4 and new studies | Descriptive: first species to go extinct, by density, grid size and reproduction rate. |
| Q4 | Why does d\* rise with L? | New trajectory study: L = 20, 30, 50, 75; d = 0.20, 0.25, 0.30; 30 replicates; to generation 70 or first extinction; master seed 4050. | Hypothesis: demographic noise. Supported if, at every density, the SD across replicates of the predator trough density (minimum predators / L²) falls at each size step from 20 to 75, and P(extinct) falls with L at d = 0.25 and 0.30. Refuted otherwise. Correlational: it can support the mechanism, not prove it. |
| Q5 | What does a single d\* cost if carried to another setting? | All studies | Descriptive: error rate of the rule "extinct if d >= d\*(L30)" per setting, against that setting's own best rule. |
| Q6 | Are extinct-at-start runs inflating results (HS4-03)? | All studies | Descriptive: count of runs with extinction_generation = 0. |

## Interpretation categories (assignment self-check)

Each limitation is classified as one of: **system failed** (the software does not
do what its requirement says), **model property** (the software is correct and the
model behaves this way), or **evidence incomplete** (not measured yet).

## Deviations

Recorded 2026-10-31 after the Q1-Q6 runs. No rule above was edited.

1. **Backlog order.** HS4 says B2 starts only after B1 (commit and tag). B1 is the
   student's action and is still open; the studies were run anyway because the
   memo is due. Each manifest carries the same ppets/ fingerprint, which is what
   B1's exit test compares.
2. **Early partial analysis.** ru09_analyze.py first ran while the L75 and L100
   studies were still running, on the HS4 data, L50_s4016 and the trajectory study.
   Q1 had not been computed at that point. Q2-Q6 and Q5 settings were re-computed
   on all studies.
3. **Q4 failed as written.** The rule is kept and reported as refuted.
4. **Post-hoc diagnostics, no pre-set rule:** frozen-curve test on the hold-out,
   lower-tail test of the log-log chi-square, extinctions after generations 75
   and 100.

## Q7: prospective test (written after Q1-Q6 were seen, before L = 150 was run)

The results above suggested a new explanation, so the explanation itself is
post-hoc. This test is not: the prediction below is written before the study runs.

**Hypothesis (spatial refuges).** A run ends in extinction only if a species dies
out everywhere at once. If the grid behaves like about L² independent patches,
P(L, d) = P(30, d) ^ ((L/30)²). The log-log curve is the one family closed under
that power: only the intercept moves, by -2 ln(L/30), and the slope stays the same.

**Prediction, using only the pooled 30×30 log-log fit (b1 = 19.9374, d\* = 0.24052):**
d\*(L) = 0.24052 + (2 / 19.9374) ln(L / 30), slope 19.94 at every L.
At L = 150: **d\* = 0.402**. Competing predictions: 0.322 (HS4 1/L fit); about 0.365
if d\* has stopped rising at L = 100.

**Study.** L150_s4018: L = 150, density 0.30-0.50, step 0.02 (11 levels; the axis moves
because the prediction lies near the old upper limit), 30 replicates, otherwise the
HS4 protocol.

**Rule.** Supported if 0.402 is inside the log-log bootstrap 95% interval of the
measured d\*(150) and 19.94 is inside the bootstrap 95% interval of the measured
slope. Refuted otherwise. Reported either way.

## Outcome of Q7

Recorded 2026-10-31 after the L = 150 run. Rule applied as written: **refuted**
(0.402 is outside the measured interval; the slope condition held). The frozen-curve
p-values and own-fit tail checks per size in `ru09_results.json` (Q7) are post-hoc.

B1 was completed later on 2026-10-31 (tag `hs4-evidence`); a clean checkout reproduces the fingerprint.
