"""E1 correctness evidence (EXPERIMENT_PLAN.md).

    python validation/hs4_correctness.py

1. Full pytest suite with coverage    -> pytest_full.txt, coverage_report.txt
2. The 8 defect reproducers against the hs3-baseline code (temporary git
   worktree); each must FAIL there      -> defects_on_hs3_baseline.txt
3. Serial vs parallel equivalence of one study (run-by-run comparison)
                                        -> serial_vs_parallel.json
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from hs4_common import EVIDENCE, REPO, WORKERS, dump, write_manifest

from ppets.analysis import ParamRange, ThresholdAnalyzer
from ppets.simulation import SimulationConfig


def sh(args, cwd=REPO):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def suite():
    t0 = time.perf_counter()
    r = sh([sys.executable, "-m", "coverage", "run", "--source=ppets", "-m", "pytest", "-v", "-p", "no:cacheprovider"])
    out = EVIDENCE / "pytest_full.txt"
    out.write_text(r.stdout + r.stderr, encoding="utf-8")
    write_manifest(out, script="validation/hs4_correctness.py", wall_seconds=time.perf_counter() - t0,
                   params={"command": "coverage run --source=ppets -m pytest -v"}, extra={"exit_code": r.returncode})
    cov = sh([sys.executable, "-m", "coverage", "report", "-m"])
    (EVIDENCE / "coverage_report.txt").write_text(cov.stdout, encoding="utf-8")
    print(r.stdout.strip().splitlines()[-1])
    print(cov.stdout.strip().splitlines()[-1])


def defects_on_baseline():
    t0 = time.perf_counter()
    wt = Path(tempfile.mkdtemp(prefix="hs3wt_")) / "wt"
    sh(["git", "worktree", "add", "-q", "--detach", str(wt), "hs3-baseline"])
    try:
        shutil.copy(REPO / "tests" / "test_known_defects.py", wt / "tests" / "test_known_defects.py")
        r = sh([sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-rf", "--tb=line",
                "tests/test_known_defects.py"], cwd=wt)
    finally:
        sh(["git", "worktree", "remove", "--force", str(wt)])
    out = EVIDENCE / "defects_on_hs3_baseline.txt"
    out.write_text(r.stdout + r.stderr, encoding="utf-8")
    write_manifest(out, script="validation/hs4_correctness.py", wall_seconds=time.perf_counter() - t0,
                   params={"code_under_test": "tag hs3-baseline", "tests": "current tests/test_known_defects.py"},
                   extra={"exit_code": r.returncode})
    print(r.stdout.strip().splitlines()[-1])


def serial_vs_parallel():
    def make(workers):
        return ThresholdAnalyzer(
            ParamRange("predator_density", 0.16, 0.36, 0.04), ParamRange("predator_repro_rate", 0.15, 0.15, 0.01),
            replicates=10, base_config=SimulationConfig(width=30, height=30, seed=4051), workers=workers)
    t0 = time.perf_counter()
    s = make(1).run_sweep()
    ts = time.perf_counter() - t0
    t0 = time.perf_counter()
    p = make(WORKERS).run_sweep()
    tp = time.perf_counter() - t0
    key = lambda r: (r.a_value, r.replicate, r.seed, r.extinct, r.prey_extinct, r.predator_extinct,
                     r.extinction_generation, r.generations_run)
    mismatches = sum(key(a) != key(b) for a, b in zip(s.runs, p.runs))
    res = dict(runs=len(s.runs), mismatching_runs=mismatches, identical=mismatches == 0 and len(s.runs) == len(p.runs),
               serial_seconds=round(ts, 1), parallel_seconds=round(tp, 1), workers=WORKERS,
               extinction_prob_serial=s.extinction_prob, extinction_prob_parallel=p.extinction_prob)
    out = EVIDENCE / "serial_vs_parallel.json"
    dump(out, res)
    write_manifest(out, script="validation/hs4_correctness.py", wall_seconds=ts + tp,
                   params={"master_seed": 4051, "levels": "0.16-0.36 step 0.04", "replicates": 10, "grid": 30})
    print("serial vs parallel identical:", res["identical"], f"({ts:.0f}s vs {tp:.0f}s)")


if __name__ == "__main__":
    suite()
    defects_on_baseline()
    serial_vs_parallel()
