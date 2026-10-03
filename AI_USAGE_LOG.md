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
