"""Shared helpers for the RU-06 early-validation scripts.

Everything in validation/ is run from the repository root, e.g.
    python validation/run_validation.py
and writes machine-readable output into evidence/validation/ so every number
quoted in the Hard Stop 3 (RU-06) package can be regenerated, not transcribed.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "evidence" / "validation"
EVIDENCE.mkdir(parents=True, exist_ok=True)

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def git(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args], cwd=REPO, capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception as exc:  # git missing / not a repo
        return f"unavailable ({exc.__class__.__name__})"


def provenance() -> dict:
    """Where and on what code a result was produced (data provenance)."""
    dirty = git("status", "--porcelain", "--untracked-files=no")
    return {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "git_commit": git("rev-parse", "--short", "HEAD"),
        "git_tracked_tree_dirty": bool(dirty) if not dirty.startswith("unavail") else None,
        "python": platform.python_version(),
        "platform": platform.platform(),
    }


def sha256_of(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def history_signature(engine) -> list[tuple[int, int, int]]:
    return [(s.generation, s.prey_count, s.predator_count) for s in engine.history]


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (95% by default)."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
