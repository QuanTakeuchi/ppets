"""HS5 reproducibility pass, automated: follow the README from scratch in a
throwaway copy and record every step.

    python validation/hs5_clean_run.py                       # current working tree, lock file, this Python
    python validation/hs5_clean_run.py --python py:3.11 --requirements requirements.txt --label py311
    python validation/hs5_clean_run.py --source https://github.com/QuanTakeuchi/ppets.git --label github

Steps, each timed, each pass/fail:
  1. get the code: `git clone` of the source (for the working tree, the clone
     is overlaid with uncommitted and new files, except the RL-01 Word files)
  2. create a venv with the chosen interpreter, pip install the requirements file
  3. python check_env.py
  4. python main.py, and main.py --config configs/default.json, each compared
     with evidence/hs5/main_expected.txt
  5. python validation/hs5_verify_evidence.py (committed evidence vs manifests)
     and python -m pytest -q (QT_QPA_PLATFORM=offscreen, so no window opens)
  6. determinism fingerprint (validation/_worker.py) equals the host interpreter's
  7. python validation/ru09_studies.py --check-fingerprint (informational: it
     passes only where ppets/ matches the RU-09 evidence)
  8. optional (--validation): python validation/run_validation.py
  9. optional (--study hs4:NAME, repeatable): delete that published study CSV
     in the copy, regenerate it, and compare its hash with the manifest

The copy lives under a short temporary path (Windows MAX_PATH, see FP-01) and
is deleted afterwards unless --keep. Needs network access for pip.
Output: evidence/hs5/clean_run_<label>.json and .log
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "evidence" / "hs5"
# Untracked deliverables that must never travel with the code (RISK_LOG RL-01).
RL01 = {"PPETS_Final_Project_Report.docx",
        "Simulating Extinction thresholds in predator HLD.docx",
        "Simulating Extinction thresholds in predator SRS.docx"}


def short_tmp() -> Path:
    base = Path(os.environ.get("PPETS_CLEAN_BASE") or tempfile.gettempdir())
    return Path(tempfile.mkdtemp(prefix="pp5_", dir=base))


def resolve_python(spec: str) -> list[str]:
    if spec.startswith("py:"):
        return ["py", "-" + spec[3:]]
    return [spec]


HOME = str(Path.home())


def redact(text: str) -> str:
    """The repository is public: keep the user's home directory out of committed logs."""
    return text.replace(HOME, "~").replace(HOME.replace("\\", "/"), "~").replace(HOME.replace("\\", "\\\\"), "~")


class Recorder:
    def __init__(self, log_path: Path):
        self.steps: list[dict] = []
        self._log = log_path.open("w", encoding="utf-8", newline="\n")

    def write(self, text: str) -> None:
        self._log.write(redact(text))
        self._log.flush()

    def close(self) -> None:
        self._log.close()

    def run(self, name, cmd, cwd, env=None, check_output=None, timeout=1800, informational=False):
        t0 = time.perf_counter()
        self.write(f"\n###{time.strftime('%Y-%m-%d %H:%M:%S')}  {name}\n$ {' '.join(map(str, cmd))}\n")
        try:
            env = {**(env or os.environ), "PYTHONIOENCODING": "utf-8"}
            proc = subprocess.run(list(map(str, cmd)), cwd=cwd, env=env, capture_output=True,
                                  text=True, timeout=timeout, encoding="utf-8", errors="replace")
            code, out, err = proc.returncode, proc.stdout, proc.stderr
        except (OSError, subprocess.TimeoutExpired) as exc:
            code, out, err = -1, "", f"{exc.__class__.__name__}: {exc}"
        self.write(out[-6000:] + ("\n[stderr]\n" + err[-4000:] if err.strip() else "") + f"\n[exit {code}]\n")
        good = code == 0
        detail = ""
        if check_output is not None and good:
            good, detail = check_output(out)
        if not detail:
            lines = [ln for ln in (out + "\n" + err).splitlines() if ln.strip()]
            detail = lines[-1][:300] if lines else ""
        detail = redact(detail)
        step = dict(step=name, ok=good, exit=code, seconds=round(time.perf_counter() - t0, 1), detail=detail)
        if informational:
            step["informational"] = True
        self.steps.append(step)
        print(("PASS " if good else ("INFO " if informational else "FAIL ")) + f"{name} ({step['seconds']} s) {detail}")
        return good, out


def get_code(rec: Recorder, source: str, dest: Path) -> bool:
    if source == "worktree":
        good, _ = rec.run("git clone (local repository, committed state)", ["git", "clone", "-q", "--no-hardlinks", REPO, dest], cwd=dest.parent)
        if not good:
            return False
        listing = subprocess.run(["git", "ls-files", "-mo", "--exclude-standard", "-z"], cwd=REPO,
                                 capture_output=True, text=True, check=True).stdout
        deleted = set(subprocess.run(["git", "ls-files", "-d", "-z"], cwd=REPO,
                                     capture_output=True, text=True, check=True).stdout.split("\0"))
        copied = 0
        for rel in filter(None, listing.split("\0")):
            if rel in RL01 or rel in deleted:
                continue
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / rel, target)
            copied += 1
        rec.steps.append(dict(step="overlay uncommitted working-tree files", ok=True, exit=0, seconds=0.0,
                              detail=f"{copied} files copied; RL-01 Word files excluded"))
        print(f"PASS overlay uncommitted working-tree files ({copied} files)")
        return True
    good, _ = rec.run(f"git clone {source}", ["git", "clone", "-q", source, dest], cwd=dest.parent)
    return good


STUDY_SCRIPTS = {"hs4": ("validation/hs4_studies.py", "evidence/hs4/studies"),
                 "ru09": ("validation/ru09_studies.py", "evidence/ru09/studies")}


def regenerate_study(rec: Recorder, py: Path, dest: Path, spec: str) -> None:
    """Strongest check available: the published CSV is rebuilt from nothing but its seed and must hash the same."""
    group, _, name = spec.partition(":")
    script, folder = STUDY_SCRIPTS[group]
    csv_name = "trajectory_s4050.csv" if name == "trajectory" else f"{name}.runs.csv"
    target = dest / folder / csv_name
    meta = json.loads((target.parent / (csv_name + ".manifest.json")).read_text(encoding="utf-8"))
    target.unlink()

    def compare(_out):
        if not target.is_file():
            return False, "no CSV written"
        lf = target.read_bytes().replace(b"\r\n", b"\n")
        got = {hashlib.sha256(b).hexdigest()[:16] for b in (lf, lf.replace(b"\n", b"\r\n"))}
        return meta["output_sha256"] in got, f"sha256 {meta['output_sha256']} " + ("reproduced" if meta["output_sha256"] in got else "NOT reproduced")

    rec.run(f"regenerate published study {spec} ({meta.get('params', {}).get('runs')} runs)",
            [py, script, name], cwd=dest, check_output=compare, timeout=7200)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--source", default="worktree", help="'worktree' (default) or a git URL/path to clone")
    ap.add_argument("--python", default=sys.executable, help="interpreter for the venv; 'py:3.11' uses the Windows launcher")
    ap.add_argument("--requirements", default="requirements-lock.txt")
    ap.add_argument("--label", default=None, help="suffix for the evidence file names")
    ap.add_argument("--validation", action="store_true", help="also run validation/run_validation.py (~2 min)")
    ap.add_argument("--study", action="append", default=[], metavar="hs4:NAME|ru09:NAME",
                    help="delete a published study CSV in the copy, regenerate it from its seed, compare with the manifest hash")
    ap.add_argument("--keep", action="store_true", help="keep the temporary copy for inspection")
    args = ap.parse_args()

    label = args.label or f"py{sys.version_info.major}{sys.version_info.minor}"
    OUT.mkdir(parents=True, exist_ok=True)
    rec = Recorder(OUT / f"clean_run_{label}.log")
    base = short_tmp()
    dest = base / "r"
    expected = (REPO / "evidence" / "hs5" / "main_expected.txt").read_text(encoding="utf-8").replace("\r\n", "\n")
    started = time.strftime("%Y-%m-%d %H:%M:%S %z")
    freeze: list[str] = []
    try:
        if get_code(rec, args.source, dest):
            commit = subprocess.run(["git", "log", "--oneline", "-1"], cwd=dest, capture_output=True, text=True).stdout.strip()
            rec.run("python -m venv .venv", [*resolve_python(args.python), "-m", "venv", ".venv"], cwd=dest)
            py = dest / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
            installed, _ = rec.run(f"pip install -r {args.requirements}",
                                   [py, "-m", "pip", "install", "-q", "--disable-pip-version-check", "-r", args.requirements], cwd=dest)
            if installed:
                freeze = subprocess.run([py, "-m", "pip", "freeze"], capture_output=True, text=True).stdout.split()
                rec.run("python check_env.py", [py, "check_env.py"], cwd=dest)
                same = lambda out: (out.replace("\r\n", "\n") == expected,
                                    f"{len(out.splitlines())} lines, " + ("identical to" if out.replace("\r\n", "\n") == expected else "DIFFERS from")
                                    + " evidence/hs5/main_expected.txt")
                rec.run("python main.py", [py, "main.py"], cwd=dest, check_output=same)
                rec.run("python main.py --config configs/default.json", [py, "main.py", "--config", "configs/default.json"], cwd=dest, check_output=same)
                rec.run("python main.py --width 1 (must exit 2, no traceback)", [py, "-c",
                        "import subprocess,sys; p=subprocess.run([sys.executable,'main.py','--width','1'],capture_output=True,text=True); "
                        "print(p.stderr.strip()); sys.exit(0 if p.returncode==2 and 'Traceback' not in p.stderr else 1)"], cwd=dest)
                rec.run("evidence files match their manifests", [py, "validation/hs5_verify_evidence.py"], cwd=dest)
                env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
                rec.run("python -m pytest -q", [py, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=dest, env=env)
                host = subprocess.run([sys.executable, str(REPO / "validation" / "_worker.py"), "fingerprint"],
                                      capture_output=True, text=True).stdout.strip()
                rec.run("determinism fingerprint == host interpreter", [py, "validation/_worker.py", "fingerprint"], cwd=dest,
                        check_output=lambda out: (bool(host) and out.strip() == host, f"{out.strip()[:16]} vs host {host[:16]}"))
                rec.run("ru09_studies.py --check-fingerprint", [py, "validation/ru09_studies.py", "--check-fingerprint"],
                        cwd=dest, informational=True)
                if args.validation:
                    rec.run("python validation/run_validation.py", [py, "validation/run_validation.py"], cwd=dest, timeout=1800)
                for spec in args.study:
                    regenerate_study(rec, py, dest, spec)
        else:
            commit = None
    finally:
        rec.close()
        if args.keep:
            print("kept:", dest)
        else:
            shutil.rmtree(base, ignore_errors=True)

    required = [s for s in rec.steps if not s.get("informational")]
    all_ok = bool(required) and all(s["ok"] for s in required)
    report = dict(
        script="validation/hs5_clean_run.py", started=started, finished=time.strftime("%Y-%m-%d %H:%M:%S %z"),
        source=args.source, source_commit=commit, requirements=args.requirements, python_spec=args.python,
        host=dict(python=platform.python_version(), platform=platform.platform(), machine=platform.machine(),
                  cpus=os.cpu_count()),
        copy_path_length=len(str(dest)), all_required_ok=all_ok, steps=rec.steps, venv_pip_freeze=freeze,
    )
    (OUT / f"clean_run_{label}.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(("ALL REQUIRED STEPS PASSED" if all_ok else "SOME REQUIRED STEPS FAILED") + f" -> evidence/hs5/clean_run_{label}.json")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
