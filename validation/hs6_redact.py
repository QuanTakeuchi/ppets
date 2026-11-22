"""Replace the home directory with ~ in HS6 text logs before they are committed
(the repository is public; KNOWN_ISSUES HS5-04).

    python validation/hs6_redact.py
"""

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOME = str(Path.home())
FILES = ["evidence/hs6/pytest_full.txt", "evidence/hs6/coverage_report.txt", "evidence/hs6/validation_run.log",
         "evidence/hs6/studies_run.log", "evidence/hs6/validation/validation_report.txt"]

for rel in FILES:
    p = REPO / rel
    if not p.exists():
        continue
    t = p.read_text(encoding="utf-8", errors="replace")
    new = t.replace(HOME, "~").replace(HOME.replace("\\", "/"), "~")
    if new != t:
        p.write_text(new, encoding="utf-8")
        print("redacted", rel)
