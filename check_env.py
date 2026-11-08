"""
Preflight check: is this environment able to run PPETS? (HS5)

    python check_env.py

Run it right after `pip install`. It does not import `ppets`, so it still
works when a broken install would make `import ppets` itself crash, and it
turns each problem found during the HS5 reproducibility pass into a one-line
diagnosis and fix. Exit status: 0 = ready, 1 = something must be fixed.
Warnings (exit 0) are conditions that worked here but have caused trouble.
"""

from __future__ import annotations

import importlib
import importlib.metadata as md
import os
import platform
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
MIN_PYTHON = (3, 11)
TESTED_PYTHON = "3.14.4 (full suite, lock file); 3.11.9 (full suite, requirements.txt)"
# import name -> distribution name, and whether the core suite needs it
PACKAGES = [
    ("numpy", "numpy", True),
    ("PyQt6", "PyQt6", True),
    ("pyqtgraph", "pyqtgraph", True),
    ("scipy", "scipy", True),
    ("pytest", "pytest", True),
    ("coverage", "coverage", True),
    ("matplotlib", "matplotlib", False),
]
# A deep checkout path is the first failure seen in the HS5 clean pass:
# PyQt6's longest installed file adds ~150 characters to the venv path.
PYQT6_DEEPEST = 150
WINDOWS_MAX_PATH = 260

results: list[tuple[str, str, str]] = []  # (level, check, message)


def ok(check, msg=""):
    results.append(("PASS", check, msg))


def warn(check, msg):
    results.append(("WARN", check, msg))


def fail(check, msg):
    results.append(("FAIL", check, msg))


def locked_versions() -> dict[str, str]:
    pins = {}
    lock = REPO / "requirements-lock.txt"
    if lock.is_file():
        for line in lock.read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if "==" in line:
                name, ver = line.split("==", 1)
                pins[name.strip().lower().replace("_", "-")] = ver.strip()
    return pins


def check_python():
    v = sys.version_info
    label = platform.python_version()
    if (v.major, v.minor) < MIN_PYTHON:
        fail("python", f"{label} is older than {MIN_PYTHON[0]}.{MIN_PYTHON[1]}; install Python 3.11 or newer (tested: {TESTED_PYTHON})")
    else:
        ok("python", f"{label} ({sys.executable})")
    if sys.prefix == sys.base_prefix:
        warn("virtualenv", "not running inside a virtual environment; the README setup uses .venv so installs do not mix with system packages")
    else:
        ok("virtualenv", sys.prefix)


def check_path():
    path = str(REPO)
    if sys.platform == "win32":
        venv_guess = len(path) + len(r"\.venv\Lib\site-packages") + PYQT6_DEEPEST
        long_paths = None
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\FileSystem") as key:
                long_paths = winreg.QueryValueEx(key, "LongPathsEnabled")[0] == 1
        except OSError:
            pass
        if venv_guess >= WINDOWS_MAX_PATH and not long_paths:
            fail("path length", f"checkout path is {len(path)} characters; PyQt6 files in .venv would need ~{venv_guess} "
                                f"(> {WINDOWS_MAX_PATH}). Clone to a short path such as C:\\src\\ppets, or ask an "
                                "administrator to enable Windows long paths")
        else:
            ok("path length", f"{len(path)} characters" + (" (long paths enabled)" if long_paths else ""))
    else:
        ok("path length", f"{len(path)} characters")
    if "onedrive" in path.lower() or "dropbox" in path.lower():
        warn("synced folder", "repository is inside a cloud-synced folder; sync can lock files in experiments/output/ and evidence/. "
                              "A plain local folder is safer for long runs")


def check_packages():
    pins = locked_versions()
    for mod, dist, required in PACKAGES:
        try:
            version = md.version(dist)
        except md.PackageNotFoundError:
            (fail if required else warn)(mod, "not installed: pip install -r requirements.txt"
                                         if required else "not installed (only needed for figures): pip install -r requirements-optional.txt")
            continue
        try:
            module = importlib.import_module(mod)
        except Exception as exc:  # noqa: BLE001 - report any import failure
            fail(mod, f"{version} installed but import fails: {exc.__class__.__name__}: {exc}")
            continue
        if mod == "PyQt6" and getattr(module, "__file__", None) is None:
            fail(mod, "PyQt6 is only partly installed (package has no __init__ file); this makes `import ppets` crash with "
                      "TypeError. Usually caused by the path-length failure: pip uninstall -y PyQt6 PyQt6-Qt6 PyQt6-sip, "
                      "fix the path, reinstall")
            continue
        pinned = pins.get(dist.lower())
        if pinned and pinned != version:
            warn(mod, f"{version} (lock file has {pinned}; fine for running PPETS, but install "
                      "requirements-lock.txt for an exact reproduction of the evidence)")
        else:
            ok(mod, version)


def check_qt():
    """Import QtWidgets and build a QApplication in a child process, so a DLL crash cannot take this script down."""
    if any(r[1] == "PyQt6" and r[0] == "FAIL" for r in results):
        return
    env = dict(os.environ)
    headless = sys.platform.startswith("linux") and not (env.get("DISPLAY") or env.get("WAYLAND_DISPLAY"))
    if headless:
        env.setdefault("QT_QPA_PLATFORM", "offscreen")
    code = ("import sys; sys.path.insert(0, %r); import ppets; from PyQt6.QtWidgets import QApplication; "
            "app = QApplication([]); print(app.platformName())") % str(REPO)
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=60)
    if proc.returncode != 0:
        last = (proc.stderr.strip().splitlines() or ["(no message)"])[-1]
        fail("Qt platform", f"QApplication could not start: {last}. Headless machine: set QT_QPA_PLATFORM=offscreen")
    else:
        ok("Qt platform", proc.stdout.strip() + (" (offscreen, set automatically: no display)" if headless else ""))


def check_repo():
    for rel in ("ppets", "tests", "configs/default.json", "evidence/hs5/main_expected.txt"):
        if not (REPO / rel).exists():
            fail("repository files", f"{rel} is missing; is this a complete clone?")
            return
    ok("repository files", "ppets/, tests/, configs/, evidence/hs5/ present")
    try:
        tags = subprocess.run(["git", "tag", "--list"], cwd=REPO, capture_output=True, text=True, timeout=20).stdout.split()
    except (OSError, subprocess.TimeoutExpired):
        warn("git", "git not found; provenance fields in evidence files will read 'unavailable'")
        return
    if "hs4-evidence" not in tags:
        warn("git", "tag hs4-evidence not present (a zip download or shallow clone); only needed to re-run the RU-09 studies")
    else:
        ok("git", "tags present: " + ", ".join(sorted(t for t in tags if t.startswith("hs"))))


def main() -> int:
    check_python()
    check_path()
    check_packages()
    check_qt()
    check_repo()
    width = max(len(r[1]) for r in results)
    for level, check, msg in results:
        print(f"{level}  {check:<{width}}  {msg}")
    failed = sum(r[0] == "FAIL" for r in results)
    warned = sum(r[0] == "WARN" for r in results)
    print(f"\n{'NOT READY' if failed else 'READY'}: {failed} failed, {warned} warnings")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
