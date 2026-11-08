"""Figures for the HS5 package (needs `pip install -r requirements-optional.txt`).

    python validation/hs5_figures.py

fig1_execution_paths.png  entry points -> ppets/ -> outputs (RUNBOOK section 1)
fig2_clean_pass_matrix.png every step of the four clean passes, pass/fail
Passes 1-2 are transcribed from the manual logs in evidence/hs5/ (they ran
before the automation existed); passes 3-4 are read from clean_run_*.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
HS5 = REPO / "evidence" / "hs5"
FIG = HS5 / "figures"
FIG.mkdir(parents=True, exist_ok=True)

GREEN, RED, GREY, AMBER, INK = "#3A7D44", "#B23A3A", "#BDBDBD", "#D9B44A", "#1F1F1F"


def box(ax, x, y, w, h, text, fill, size=8.5, weight="normal"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=fill, ec=INK, lw=0.8))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, weight=weight, color=INK)


def arrow(ax, a, b):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=10, lw=0.9, color=INK))


def fig1():
    fig, ax = plt.subplots(figsize=(10, 5.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.6)
    ax.axis("off")
    ax.text(0.95, 5.35, "Entry points", ha="center", fontsize=10, weight="bold")
    ax.text(4.9, 5.35, "ppets/  (frozen, fingerprint 0c61dd14fdaad6a8)", ha="center", fontsize=10, weight="bold")
    ax.text(8.85, 5.35, "Outputs", ha="center", fontsize=10, weight="bold")
    ax.add_patch(FancyBboxPatch((2.75, 0.35), 4.3, 4.8, boxstyle="round,pad=0.02,rounding_size=0.1",
                                fc="#F3F7F3", ec=GREEN, lw=1.2, ls="--"))
    ent = {"cli": (4.3, "main.py\n--config / flags"), "gui": (3.2, "run_ui.py\nGUI form"),
           "stud": (2.1, "validation/\n*_studies.py"), "an": (0.8, "validation/\n*_analyze.py")}
    for _k, (y, t) in ent.items():
        box(ax, 0.1, y - 0.1, 1.7, 0.8, t, "#E8F0E9")
    box(ax, 3.0, 3.9, 1.8, 0.8, "SimulationConfig\nvalidate + seeded RNG", "white")
    box(ax, 5.1, 3.9, 1.8, 0.8, "Engine\nstep loop", "white")
    box(ax, 3.0, 2.8, 1.8, 0.8, "Controller\nQTimer, auto-pause", "white")
    box(ax, 3.0, 1.7, 1.8, 0.8, "ThresholdAnalyzer\nPool + SeedSequence", "white")
    box(ax, 5.1, 0.6, 1.8, 0.8, "estimates.py\nWilson CI, d* fit", "white")
    outs = {"csv": (4.3, "CSV trace\nstdout / --output"), "win": (3.2, "GUI window"),
            "runs": (2.1, "*.runs.csv\n+ manifest"), "res": (0.8, "*_results.json\nfigures")}
    for _k, (y, t) in outs.items():
        box(ax, 8.0, y - 0.1, 1.8, 0.8, t, "#FFF7E0")
    arrow(ax, (1.8, 4.6), (3.0, 4.3))
    arrow(ax, (1.8, 3.5), (3.0, 3.2))
    arrow(ax, (3.9, 3.6), (3.9, 3.9))
    arrow(ax, (1.8, 2.4), (3.0, 2.1))
    arrow(ax, (4.8, 4.3), (5.1, 4.3))
    arrow(ax, (4.8, 2.1), (5.6, 3.9))
    arrow(ax, (6.9, 4.4), (8.0, 4.6))
    arrow(ax, (4.8, 3.2), (8.0, 3.5))
    arrow(ax, (4.8, 1.95), (8.0, 2.3))
    arrow(ax, (8.0, 2.05), (1.8, 1.05))
    arrow(ax, (1.8, 1.0), (5.1, 1.0))
    arrow(ax, (6.9, 1.0), (8.0, 1.1))
    ax.text(5.0, 0.05, "Every path goes through SimulationConfig: one validation point, one seeded generator. "
                       "check_env.py runs before any of them.", ha="center", fontsize=8.5, style="italic", color="#595959")
    fig.tight_layout()
    fig.savefig(FIG / "fig1_execution_paths.png", dpi=200)
    plt.close(fig)


STEPS = ["Get code (clone)", "Create venv", "pip install", "Preflight (check_env.py)",
         "main.py = reference output", "Bad input -> exit 2, no traceback", "Evidence matches manifests",
         "pytest", "Validation suite 12/12", "Determinism = host", "Regenerate published study"]


def auto_pass(label):
    data = json.loads((HS5 / f"clean_run_{label}.json").read_text(encoding="utf-8"))
    by = {s["step"]: s for s in data["steps"]}

    def find(prefix, exclude="\0"):
        hits = [s for name, s in by.items() if name.startswith(prefix) and exclude not in name]
        if not hits:
            return ("n/a", "not run")
        good = all(h["ok"] for h in hits)
        return ("pass" if good else "fail", "; ".join(h["detail"] for h in hits)[:60])

    return [find("git clone"), find("python -m venv"), find("pip install"), find("python check_env.py"),
            find("python main.py", exclude="--width"),
            find("python main.py --width 1"), find("evidence files match"), find("python -m pytest"),
            find("python validation/run_validation.py"), find("determinism fingerprint"),
            find("regenerate published study")], data


MANUAL = {
    "1  public main\ndeep path, 3.14": [("pass", ""), ("pass", ""), ("fail", "OSError: path too long"),
                                         ("n/a", "did not exist"), ("fail", "TypeError at import"), ("n/a", ""),
                                         ("n/a", ""), ("fail", "pytest not installed"), ("fail", "TypeError at import"),
                                         ("n/a", ""), ("n/a", "")],
    "2  public main\nshort path, 3.14": [("pass", ""), ("pass", ""), ("pass", ""), ("n/a", "did not exist"),
                                          ("fail", "schema differs from documented trace"), ("n/a", ""), ("n/a", ""),
                                          ("fail", "0 tests: scipy missing"), ("fail", "8/12"), ("n/a", ""), ("n/a", "")],
}


def fig2():
    cols = dict(MANUAL)
    p3, _ = auto_pass("py314")
    p4, _ = auto_pass("py311")
    cols["3  hardened\nlock file, 3.14"] = p3
    cols["4  hardened\nunpinned, 3.11"] = p4
    colour = {"pass": GREEN, "fail": RED, "n/a": GREY}
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    ax.set_xlim(0, len(cols))
    ax.set_ylim(0, len(STEPS))
    ax.invert_yaxis()
    for j, (_name, results) in enumerate(cols.items()):
        for i, (state, _detail) in enumerate(results):
            ax.add_patch(plt.Rectangle((j + 0.05, i + 0.08), 0.9, 0.84, color=colour[state]))
            ax.text(j + 0.5, i + 0.5, {"pass": "PASS", "fail": "FAIL", "n/a": "—"}[state],
                    ha="center", va="center", fontsize=8.5, color="white" if state != "n/a" else INK, weight="bold")
    ax.set_xticks([j + 0.5 for j in range(len(cols))])
    ax.set_xticklabels(list(cols), fontsize=8.5)
    ax.xaxis.tick_top()
    ax.set_yticks([i + 0.5 for i in range(len(STEPS))])
    ax.set_yticklabels(STEPS, fontsize=8.5)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    fig.text(0.5, 0.01, "Grey: step not run (did not exist yet, or a previous step failed). "
                        "Passes 1–2: evidence/hs5/manual_pass*.log; 3–4: clean_run_py314/py311.json.",
             ha="center", fontsize=8, style="italic", color="#595959")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(FIG / "fig2_clean_pass_matrix.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    fig1()
    fig2()
    print("wrote", *(p.name for p in sorted(FIG.glob("*.png"))))
