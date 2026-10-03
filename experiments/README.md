# experiments/

Ad-hoc, standalone research scripts that drive `ppets.simulation` headlessly
to produce a dataset for the write-up (e.g. the GRAD 695 final report's
Results & Analysis chapter) — not part of the PPETS application itself, and
not interactive. Application code lives in `ppets/`; its tests live in
`tests/`.

Each script writes its own CSV/figure output into `experiments/output/`
(gitignored, regenerated on demand — never commit generated data here).

| Script | Produces |
| --- | --- |
| `sweep.py` | `sweep_results.csv`, `heatmap_matrix.csv`, three `curve_*.csv` traces — an extinction-probability sweep over predator density x predator reproduction rate. |

Run from the repository root with the project's own `requirements.txt`
installed:

```bash
python experiments/sweep.py
```
