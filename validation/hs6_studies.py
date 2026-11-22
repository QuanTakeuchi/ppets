"""HS6 / RU-12 final studies (evidence/hs6/ANALYSIS_PLAN.md, F0 and F1).

    python validation/hs6_studies.py            # everything (about 15 min, 15 workers)
    python validation/hs6_studies.py F0         # regenerate two published spatial studies
    python validation/hs6_studies.py WM30_s4001 # one well-mixed study by name

Same protocol as hs4_studies.py and ru09_studies.py; the only difference in the
well-mixed studies is SimulationConfig.mixing = "well_mixed". They reuse the
spatial studies' master seeds, so each run starts from the same initial grid as
its spatial twin. Studies whose CSV already exists are skipped.
Outputs: evidence/hs6/studies/ (CSV + manifest each) and evidence/hs6/f0_regeneration.json.
"""

from __future__ import annotations

import json
import sys
import time

import hs4_common
from hs4_common import DENSITY, MAX_GEN, PROTOCOL, REPLICATES, WORKERS, sha256_file, write_manifest, write_runs_csv

from ppets.analysis import ParamRange, ThresholdAnalyzer
from ppets.simulation import SimulationConfig

EVIDENCE = hs4_common.REPO / "evidence" / "hs6"
OUT = EVIDENCE / "studies"
OUT.mkdir(parents=True, exist_ok=True)

# name, grid size, master seed, density axis, mixing
STUDIES = (
    ("WM30_s4001", 30, 4001, DENSITY, "well_mixed"),
    ("WM30_s4002", 30, 4002, DENSITY, "well_mixed"),
    ("WM75_s4014", 75, 4014, DENSITY, "well_mixed"),
    ("WMlow30_s4061", 30, 4061, dict(start=0.002, stop=0.020, step=0.002), "well_mixed"),
    ("WMlow75_s4062", 75, 4062, dict(start=0.001, stop=0.010, step=0.001), "well_mixed"),
)
# Published spatial studies regenerated with the HS6 code (F0).
REGENERATE = (("L20_s4011", 20, 4011), ("L30_s4001", 30, 4001))


def sweep(size: int, seed: int, density: dict, mixing: str):
    base = SimulationConfig(**{**PROTOCOL, "width": size, "height": size, "seed": seed, "mixing": mixing})
    repro = PROTOCOL["predator_repro_rate"]
    ta = ThresholdAnalyzer(
        param_a=ParamRange("predator_density", **density),
        param_b=ParamRange("predator_repro_rate", start=repro, stop=repro, step=0.01),
        replicates=REPLICATES, base_config=base, max_generations=MAX_GEN, workers=WORKERS,
    )
    t0 = time.perf_counter()
    res = ta.run_sweep()
    assert res.complete
    return base, res, time.perf_counter() - t0


def run_study(name, size, seed, density, mixing) -> None:
    out = OUT / f"{name}.runs.csv"
    if out.exists():
        print(f"skip {name} (exists)", flush=True)
        return
    base, res, wall = sweep(size, seed, density, mixing)
    write_runs_csv(out, res.runs)
    write_manifest(out, script="validation/hs6_studies.py", wall_seconds=wall,
                   params={"name": name, "seed": seed, "size": size, "mixing": mixing, "max_gen": MAX_GEN,
                           "density": density, "reps": REPLICATES, "base_config": base.to_dict(),
                           "workers": WORKERS, "runs": len(res.runs), "question": "F1"})
    print(f"{name}: {len(res.runs)} runs in {wall:.0f}s", flush=True)


def regenerate() -> None:
    """F0: the HS6 code must reproduce published spatial studies byte for byte."""
    tmp = EVIDENCE / "regen"
    tmp.mkdir(exist_ok=True)
    rows = []
    for name, size, seed in REGENERATE:
        published = hs4_common.EVIDENCE / "studies" / f"{name}.runs.csv"
        manifest = json.loads(published.with_suffix(".csv.manifest.json").read_text(encoding="utf-8"))
        _, res, wall = sweep(size, seed, DENSITY, "spatial")
        out = tmp / f"{name}.runs.csv"
        write_runs_csv(out, res.runs)
        new = sha256_file(out)
        rows.append(dict(study=name, runs=len(res.runs), manifest_sha256=manifest["output_sha256"],
                         committed_file_sha256=sha256_file(published), regenerated_sha256=new,
                         identical=new == manifest["output_sha256"], wall_seconds=round(wall, 1)))
        out.unlink()  # the comparison is the evidence; the copy would duplicate the committed file
        print(f"F0 {name}: {'identical' if rows[-1]['identical'] else 'DIFFERENT'}", flush=True)
    tmp.rmdir()
    path = EVIDENCE / "f0_regeneration.json"
    hs4_common.dump(path, dict(question="F0", rule="byte-identical to the published CSV", studies=rows,
                               passed=all(r["identical"] for r in rows), code=hs4_common.code_state()))
    write_manifest(path, script="validation/hs6_studies.py", wall_seconds=sum(r["wall_seconds"] for r in rows),
                   params={"regenerated": [r[0] for r in REGENERATE], "workers": WORKERS})


if __name__ == "__main__":
    names = set(sys.argv[1:])
    if not names or "F0" in names:
        regenerate()
    for name, size, seed, density, mixing in STUDIES:
        if not names or name in names:
            run_study(name, size, seed, density, mixing)
