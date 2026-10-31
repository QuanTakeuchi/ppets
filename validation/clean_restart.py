"""Clean-restart reproduction (student self-check: "can you reproduce your own
evidence from a clean restart?").

    python validation/clean_restart.py

Creates a brand-new virtual environment outside the repository, installs ONLY
what requirements.txt declares, then re-runs from scratch:
  1. the pytest suite,
  2. main.py (compared byte-for-byte with evidence/main_smoke_test.txt),
  3. the determinism fingerprint (compared with this interpreter's own).

Needs network access for pip. Output: evidence/validation/clean_restart.json
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path

from _common import EVIDENCE, REPO, provenance, write_json


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=REPO, **kw)


def main() -> int:
    steps = []
    with tempfile.TemporaryDirectory(prefix="ppets_clean_") as tmp:
        venv = Path(tmp) / "venv"
        t0 = time.perf_counter()
        run([sys.executable, "-m", "venv", str(venv)], check=True)
        py = venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        steps.append(dict(step="create venv", ok=True, seconds=round(time.perf_counter() - t0, 1)))

        t0 = time.perf_counter()
        pip = run([str(py), "-m", "pip", "install", "-q", "--disable-pip-version-check", "-r", "requirements.txt"])
        steps.append(dict(step="pip install -r requirements.txt", ok=pip.returncode == 0,
                          seconds=round(time.perf_counter() - t0, 1), detail=pip.stderr.strip()[-300:]))
        if pip.returncode != 0:
            return finish(steps, venv_versions=None)

        freeze = run([str(py), "-m", "pip", "freeze"]).stdout.strip().splitlines()

        t0 = time.perf_counter()
        env_off = {**__import__("os").environ, "QT_QPA_PLATFORM": "offscreen"}
        pt = run([str(py), "-m", "pytest", "-q", "-p", "no:cacheprovider"], env=env_off)
        tail = [ln for ln in pt.stdout.strip().splitlines() if ln.strip()][-1] if pt.stdout.strip() else ""
        steps.append(dict(step="pytest (fresh venv)", ok=pt.returncode == 0,
                          seconds=round(time.perf_counter() - t0, 1), detail=tail))

        main_out = run([str(py), "main.py"]).stdout.replace("\r\n", "\n").strip()
        ref = (REPO / "evidence" / "main_smoke_test.txt").read_text(encoding="utf-8").replace("\r\n", "\n").strip()
        steps.append(dict(step="main.py output == evidence/main_smoke_test.txt", ok=main_out == ref,
                          detail=f"{len(main_out.splitlines())} lines"))

        fp_clean = run([str(py), str(REPO / "validation" / "_worker.py"), "fingerprint"]).stdout.strip()
        fp_host = run([sys.executable, str(REPO / "validation" / "_worker.py"), "fingerprint"]).stdout.strip()
        steps.append(dict(step="determinism fingerprint, fresh venv == host interpreter", ok=bool(fp_clean) and fp_clean == fp_host,
                          detail=f"{fp_clean[:16]} vs {fp_host[:16]}"))
        return finish(steps, venv_versions=freeze)


def finish(steps, venv_versions) -> int:
    ok = all(s["ok"] for s in steps)
    write_json(EVIDENCE / "clean_restart.json", dict(
        provenance=provenance(), all_ok=ok, steps=steps, fresh_venv_pip_freeze=venv_versions))
    for s in steps:
        print(("PASS " if s["ok"] else "FAIL ") + s["step"], "-", s.get("detail", ""))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
