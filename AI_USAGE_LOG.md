# AI Usage Log — Hard Stop 3 (Implementation Baseline)

Full history (HS1–HS2) is logged in the HS1 Proposal Package and HS2
Design Review Package's own AI logs; this entry covers HS3 only, in the
same format established there.

## Disclosure principles (carried forward from HS1/HS2)

No supervisor ruling on HU/course AI-disclosure policy format has been
received as of this checkpoint; these principles remain the operating
default:

- **Transparency over minimisation.** Every AI-produced artifact is
  listed, including drafting work a reader could not detect from the
  output alone.
- **Human ownership of decisions.** Which module gets built first, which
  design deviations are accepted, and which risks get escalated are the
  student's decisions; the AI proposes, the student disposes.
- **Verification before use.** No number in this log (test count,
  coverage percentage) enters it unless it was regenerated from a
  committed script, on this machine, during this session.

## Log of AI-assisted work, this checkpoint

| Period | AI contribution | Verification | Appears in |
| --- | --- | --- | --- |
| Oct 3, 2026 | Claude Code (Claude Sonnet 5) read the LLD's Module 3 spec (§4.1 `ThresholdAnalyzer`, §3.3 `HeatmapView`) directly from `PPETS_LLD.docx`, implemented `ppets/analysis/` and `ppets/ui/heatmap_view.py` against it, wrote 11 new tests, fixed the `_experiment_sweep.py` reproducibility defect (relocated to `experiments/sweep.py`), and drafted `README.md` / `ARCHITECTURE.md` / `CHANGELOG.md` / `KNOWN_ISSUES.md` / `RISK_LOG.md` / `SPRINT_REFLECTION.md` and this log. | 40/40 tests passed (29 pre-existing + 11 new); coverage independently re-measured (62% on `ppets/`); every class/method name checked against the LLD §4.1 member table during implementation. | `ppets_ca_engine_core` repository, tag `hs3-baseline`; `HS3_Implementation_Baseline_Package` |

## Resolved disclosure items (previously open; confirmed by the student Oct 3, 2026)

- `PPETS_LLD_rewritten.docx` / `PPETS_Test_Cases_rewritten.docx` (the Aug
  11–12 `rewrite_docx.py` paraphraser outputs): confirmed never submitted
  for credit anywhere; no disclosure entry needed for them.
- Supervisor has still not given a ruling on HU/course AI-disclosure
  policy format; no change to the principles above is needed.
- May–Aug 2026 original documents (charter/SRS/HLD/LLD/test cases) and
  the original `ppets/simulation` engine: HS2's own AI log already
  states "No AI usage" for that period; treated as settled, not
  re-litigated here.

## Student declaration

I confirm that this log is complete to the best of my knowledge, that I
have reviewed and take responsibility for every file this checkpoint
added or changed, and that I can explain the reasoning behind the
`ThresholdAnalyzer` skeleton's design and every deferred-scope decision
recorded in `SPRINT_REFLECTION.md`.

Signature: ______________________________          Date: ______________


---

# AI Usage Log — Hard Stop 3 / RU-06 (Early Implementation Validation)

Same format and principles as the entries above (transparency over
minimisation, human ownership of decisions, verification before use).

| Period | AI contribution | Verification | Appears in |
| --- | --- | --- | --- |
| Oct 10, 2026 | Claude Code (Claude Sonnet 5.5) read the HS1/HS2/RU-05 packages and the repository source; wrote the `validation/` scripts (`run_validation.py`, `pilot_study.py`, `triple_retest.py`, `bench_sweep.py`, `env_snapshot.py`, `clean_restart.py`, `make_figures.py`) and `tests/test_known_defects.py`; ran them; drafted `ENVIRONMENT.md`, `VALIDATION_MEMO.md`, the RU-06 additions to `KNOWN_ISSUES.md` / `RISK_LOG.md` / `CHANGELOG.md` / `README.md`, `requirements-lock.txt`, and the RU-06 package document. No production code under `ppets/` was modified. | Every figure in the package is read from a committed evidence file produced by the scripts on this machine on this date; each defect reproducer was re-run with xfail disabled to confirm it fails for the stated reason (not a test typo); the suite was re-run after the last change (40 passed, 8 xfailed); a negative control (V12) shows the determinism checks can fail. | `ppets_ca_engine_core` (`validation/`, `evidence/validation/`, repo-root docs); `HS3_Early_Implementation_Validation_Package` |

Not done by the AI (student actions outstanding): the supervisor meeting and
its decision record; reading and approving the findings; signing the
declaration below.

## Student declaration

I confirm that this log is complete to the best of my knowledge, that I
have reviewed and take responsibility for every file this checkpoint
added or changed, and that I can explain the validation methods, the
defects found, and the interpretation recorded in `VALIDATION_MEMO.md`.

Signature: ______________________________          Date: ______________


---

# AI Usage Log — Hard Stop 4 / RU-08 (Midpoint Technical Evidence Review)

Same principles as above. Full log, including AI outputs that were wrong and
how each was caught: section 1 of `PPETS_HS4_Midpoint_Technical_Evidence_Review.docx`.

| Period | AI contribution | Verification | Appears in |
| --- | --- | --- | --- |
| Oct 24, 2026 | Claude Code (Claude Opus 5.5) rewrote `ppets/analysis/threshold_analyzer.py`, added `ppets/analysis/estimates.py`, fixed `HeatmapView` axes, removed `extinction_risk`, added the FR14 scope statement; wrote `tests/test_hs4_analysis.py` and edited the defect tests and one HS3 test; drafted the HS4 question and pass/fail thresholds (`evidence/hs4/EXPERIMENT_PLAN.md`, before any run); wrote `validation/hs4_*.py`; ran E1–E8; drafted the package and these log updates. | 79 tests pass; defect reproducers fail on `hs3-baseline` for their stated reasons; serial = parallel run by run; Wilson interval checked against scipy; d\* estimator checked on synthetic data; every reported number read from evidence files with manifests. | `ppets/`, `tests/`, `validation/hs4_*.py`, `evidence/hs4/`, HS4 package |

Corrected AI errors this checkpoint (details in the package, section 1.4): the
HS3 DEF-03 reproducer could never detect its fix; a rewritten test failed for the
wrong reason; extinct-at-start runs were stepped once; quasi-separation was not
detected; one weak test assertion; manifests fingerprinted the wrong files.

Not done by the AI: the commit and tag; reviewing and approving the thresholds,
decisions D1–D5 and the interpretation; signing below.

## Student declaration

Signature: ______________________________          Date: ______________


---

# AI Usage Log — Week 9 / RU-09 (Results and Limitations Memo)

Same principles as above. Full log, including AI outputs that were wrong: section 1
of `PPETS_RU09_Results_and_Limitations_Memo.docx`.

| Period | AI contribution | Verification | Appears in |
| --- | --- | --- | --- |
| Oct 31, 2026 | Claude Code (Claude Opus 5.5) wrote the analysis plan before the runs; wrote `validation/ru09_*.py` and `tests/test_ru09_analysis.py`; ran the L = 50, 75, 100 and 150 studies and the trajectory study; proposed the spatial-refuge scaling hypothesis; drafted the memo, figures and these log updates. No `ppets/` code changed. | 90 tests pass; link fits checked against scipy and the production estimator; studies refuse to run on a different `ppets/` fingerprint; every number in the memo is read from evidence files; the scaling hypothesis was tested prospectively and refuted. | `validation/`, `tests/`, `evidence/ru09/`, RU-09 package |

Corrected AI errors this checkpoint (details in the package, section 1.2): cloglog
proposal; "horizon is safe" overgeneralised; precision reported as if it were
accuracy; first reading of the log-log fit; a weak pre-set Q4 statistic; a scaling law refuted at L = 150; a fingerprint check that failed on a clean
checkout because it hashed raw line endings (found by that test, fixed before
the tag was final).

Claude Code also made the `hs4-evidence` commit and tag, at the student's request.

Not done by the AI: sharing with the supervisor and revising; approving decisions
D1, D3, D6 and D7; signing below.

## Student declaration

Signature: ______________________________          Date: ______________


---

# AI Usage Log — Hard Stop 5 (Artifact Hardening and Reproducibility Check)

Same principles as above. Full log, including AI outputs that were wrong or
rejected: section 1 of `PPETS_HS5_Artifact_Hardening_Package.docx`.

| Period | AI contribution | Verification | Appears in |
| --- | --- | --- | --- |
| Nov 8, 2026 | Claude Code (Claude Opus 5.5) audited the repository; ran the two manual clean passes from the public repository and logged the friction (FP-01 to FP-13) before fixing anything; wrote `check_env.py`, the `main.py` command line, `configs/default.json`, `tests/test_cli.py`, `validation/hs5_clean_run.py`, `validation/hs5_verify_evidence.py` and the CI workflow; updated `validation/run_validation.py` and `_worker.py`; rewrote `README.md`; wrote `RUNBOOK.md`, `evidence/README.md` and the HS5 notes; updated these logs; drafted the HS5 package. No `ppets/` code changed. | 109 tests pass; 12/12 validation checks; clean runs on Python 3.14 (lock) and 3.11 (unpinned); two published studies regenerated with matching hashes; `main.py` default output byte-identical before and after the CLI rewrite; `ru09_studies.py --check-fingerprint` matches. | Repository root, `validation/`, `tests/`, `evidence/hs5/`, HS5 package |

Corrected AI errors this checkpoint: an edit script aborted midway, and the
old validation suite then ran and overwrote committed RU-06 evidence
(restored from git; this became FP-08); a "historical" banner was added to
`ppets/README.md`, which would have changed the frozen fingerprint (reverted,
fingerprint re-checked); a preflight warning claimed results "matched across
the versions tested" for versions that had not been tested (reworded); a
runtime estimate in the runbook was too high (2.5 h; the manifests sum to
about 1.5 h).

Not done by the AI: the walkthrough recording; choosing a licence (HS5-03);
decision D-HS5-1; the commit, tag and push that start CI; signing below.

## Hard Stop 6 / RU-12 (2026-11-21)

| Period | AI contribution | Verification | Appears in |
| --- | --- | --- | --- |
| Nov 21, 2026 | Claude Code (Claude Opus 5.5), working from the student's Week 12 handoff worksheet: implemented the well-mixed mode, the production estimators and the pathway table in `ppets/` (with the HS5-05/07 fixes, as D-HS5-1 proposed); wrote `tests/test_hs6_final.py`; wrote `evidence/hs6/ANALYSIS_PLAN.md` after a 120-run pilot and before the formal runs; ran the studies, analysis, figures, final test suite, validation, integrity check and a clean-environment pass; revised the report (HS6 package), built the deck, demo and walkthrough scripts; updated these logs. | Estimators reproduce the published RU-09 values to 1e-12; F0: two published studies regenerate byte for byte; 135 tests, 12/12 checks, 31/31 evidence files, clean run passes; the F2 rule, set in advance, was applied even though it went against the chosen estimator. | `ppets/`, `tests/`, `validation/hs6_*`, `evidence/hs6/`, HS6 package |

Corrected AI errors this checkpoint: a first PyQt6-guard test used an empty
folder that did not shadow the installed package, so it tested nothing
(replaced by a stub module; the test now fails on the old code); the first
analysis code tested "all well-mixed runs extinct" instead of the plan's
"never below 0.5" and crashed on four survivors (fixed to the plan's wording
before reading results; logged as deviation 1); re-running the validation and
integrity scripts as written would have overwritten the HS5 record (added
`--out`); a draft abstract claimed log-log "stays close to nominal coverage"
before the stress test had been read, and was wrong (rewritten from the result).

Not done by the AI: the commit, tag and push; decisions D-HS6-1 and SC9; the
walkthrough recording; signing below.

## Student declaration

Signature: ______________________________          Date: ______________
