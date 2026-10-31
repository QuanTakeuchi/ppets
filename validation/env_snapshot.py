"""Environment snapshot + toolchain assumption checks (RU-06 task 3).

    python validation/env_snapshot.py

Records exactly what the evidence in evidence/validation/ was produced on, and
probes the assumptions the project silently relies on: dependency versions,
file-system write access, the Qt platform plugin (native vs offscreen), and
whether the repository lives on a cloud-synced path.

Output: evidence/validation/environment.json
"""

from __future__ import annotations

import importlib
import json
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

from _common import EVIDENCE, REPO, git, provenance, write_json

PACKAGES = ["numpy", "PyQt6", "pyqtgraph", "pytest", "coverage", "matplotlib"]


def version_of(name: str) -> str | None:
    try:
        from importlib import metadata
        return metadata.version(name)
    except Exception:
        return None


def writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path, delete=True):
            pass
        return True
    except OSError:
        return False


def qt_platform_probe(platform_name: str | None) -> dict:
    """Start a throwaway interpreter and try to build MainWindow on the given
    Qt platform plugin. A child process isolates any native crash."""
    code = (
        "import sys; sys.path.insert(0, r'%s')\n"
        "from PyQt6.QtWidgets import QApplication\n"
        "app = QApplication([])\n"
        "from ppets.ui.main_window import MainWindow\n"
        "w = MainWindow(); w.show(); app.processEvents()\n"
        "print(app.platformName(), w.isVisible())\n" % REPO
    )
    env = dict(os.environ)
    env.pop("QT_QPA_PLATFORM", None)
    if platform_name:
        env["QT_QPA_PLATFORM"] = platform_name
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=120)
    return dict(requested=platform_name or "(default)", returncode=p.returncode,
                stdout=p.stdout.strip(), stderr=p.stderr.strip()[-300:])


def main() -> None:
    req = (REPO / "requirements.txt").read_text().split()
    snapshot = dict(
        provenance=provenance(),
        machine=dict(os=platform.platform(), machine=platform.machine(), cpu_count=os.cpu_count(),
                     python=sys.version.split()[0], python_impl=platform.python_implementation(),
                     python_executable=sys.executable),
        declared_requirements=req,
        requirements_pinned=any(any(op in r for op in ("==", ">=", "~=", "<=")) for r in req),
        installed_versions={p: version_of(p) for p in PACKAGES},
        undeclared_but_used=[p for p in ("matplotlib",) if version_of(p)],
        filesystem=dict(
            repo_path=str(REPO),
            repo_path_length=len(str(REPO)),
            repo_under_onedrive="onedrive" in str(REPO).lower(),
            evidence_dir_writable=writable(EVIDENCE),
            experiments_output_writable=writable(REPO / "experiments" / "output"),
        ),
        env_vars={k: os.environ.get(k) for k in ("QT_QPA_PLATFORM", "PYTHONHASHSEED", "VIRTUAL_ENV")},
        in_virtualenv=sys.prefix != getattr(sys, "base_prefix", sys.prefix),
        git=dict(commit=git("rev-parse", "HEAD"), branch=git("rev-parse", "--abbrev-ref", "HEAD"),
                 tags_at_head=git("tag", "--points-at", "HEAD")),
        qt_probes=[qt_platform_probe(None), qt_platform_probe("offscreen")],
    )
    write_json(EVIDENCE / "environment.json", snapshot)
    print(json.dumps({k: snapshot[k] for k in ("machine", "installed_versions", "requirements_pinned",
                                               "in_virtualenv", "qt_probes")}, indent=2))


if __name__ == "__main__":
    main()
