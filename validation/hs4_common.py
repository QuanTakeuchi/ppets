"""Shared helpers for the Hard Stop 4 (RU-08) evidence scripts.

Run from the repository root, e.g. `python validation/hs4_studies.py`.
Outputs go to evidence/hs4/. Every output file has a sibling *.manifest.json
recording how it was produced: code state (commit plus a hash of uncommitted
changes), interpreter and package versions, machine, parameters, master
seeds, and wall time (FR16-style provenance).
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import sys
import time
from dataclasses import asdict
from pathlib import Path

from _common import REPO, git, write_json

EVIDENCE = REPO / "evidence" / "hs4"
EVIDENCE.mkdir(parents=True, exist_ok=True)

WORKERS = max(1, (os.cpu_count() or 2) - 1)

PROTOCOL = dict(
    width=30, height=30, prey_density=0.30, prey_repro_rate=0.20,
    predator_repro_rate=0.15, prey_death_threshold=3, starvation_rate=3, toroidal=True,
)
DENSITY = dict(start=0.06, stop=0.40, step=0.02)
REPLICATES = 30
MAX_GEN = 150


def code_state() -> dict:
    # Fingerprint the code that determines results (ppets/) only, so editing
    # evidence scripts does not change it.
    diff = git("diff", "HEAD", "--", "ppets")
    untracked = git("ls-files", "--others", "--exclude-standard", "ppets")
    h = hashlib.sha256(diff.encode())
    for rel in sorted(untracked.splitlines()):
        p = REPO / rel
        if p.is_file():
            h.update(rel.encode())
            h.update(p.read_bytes())
    return {
        "git_commit": git("rev-parse", "--short", "HEAD"),
        "uncommitted_changes_in_ppets": bool(diff.strip() or untracked.strip()),
        "ppets_tree_sha256": h.hexdigest()[:16],
    }


def environment() -> dict:
    import numpy
    return {
        "python": platform.python_version(),
        "numpy": numpy.__version__,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "logical_cpus": os.cpu_count(),
    }


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def write_manifest(out: Path, *, script: str, params: dict, wall_seconds: float, extra=None) -> None:
    write_json(out.with_suffix(out.suffix + ".manifest.json"), {
        "output": out.name,
        "output_sha256": sha256_file(out),
        "script": script,
        "command": f"python {script} " + " ".join(sys.argv[1:]),
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "wall_seconds": round(wall_seconds, 1),
        "code": code_state(),
        "environment": environment(),
        "params": params,
        **(extra or {}),
    })


def write_runs_csv(path: Path, runs) -> None:
    fields = list(asdict(runs[0]).keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in runs:
            w.writerow(asdict(r))


def read_runs_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["a_value"] = float(r["a_value"])
        r["b_value"] = float(r["b_value"])
        r["replicate"] = int(r["replicate"])
        r["extinct"] = r["extinct"] == "True"
        r["prey_extinct"] = r["prey_extinct"] == "True"
        r["predator_extinct"] = r["predator_extinct"] == "True"
        r["extinction_generation"] = int(r["extinction_generation"]) if r["extinction_generation"] else None
        r["generations_run"] = int(r["generations_run"])
    return rows


def dump(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
