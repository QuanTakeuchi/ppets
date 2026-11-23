"""Check that every committed evidence file still matches its manifest (HS5).

    python validation/hs5_verify_evidence.py

Each HS4/RU-09 result file has a sibling <name>.manifest.json whose
`output_sha256` (first 16 hex digits) was taken from the bytes as written.
Git may change line endings on checkout (core.autocrlf), so a file passes if
its bytes match as stored, with CRLF line endings, or with LF line endings;
the report says which. Exit status 1 if any file is missing or altered.
Output: evidence/hs5/evidence_integrity.json
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "evidence" / "hs5" / "evidence_integrity.json"
# HS6: `--out evidence/hs6/evidence_integrity.json` keeps the HS5 record unchanged.
if "--out" in sys.argv:
    OUT = REPO / sys.argv[sys.argv.index("--out") + 1]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def variants(data: bytes) -> dict[str, bytes]:
    lf = data.replace(b"\r\n", b"\n")
    return {"as stored": data, "LF": lf, "CRLF": lf.replace(b"\n", b"\r\n")}


def main() -> int:
    rows = []
    for manifest in sorted((REPO / "evidence").rglob("*.manifest.json")):
        meta = json.loads(manifest.read_text(encoding="utf-8"))
        target = manifest.with_name(meta["output"])
        rel = target.relative_to(REPO).as_posix()
        if not target.is_file():
            rows.append(dict(file=rel, ok=False, how="missing", expected=meta["output_sha256"]))
            continue
        match = next((k for k, v in variants(target.read_bytes()).items() if digest(v) == meta["output_sha256"]), None)
        rows.append(dict(file=rel, ok=match is not None, how=match or "ALTERED", expected=meta["output_sha256"],
                         script=meta.get("script"), ppets_fingerprint=(meta.get("code") or {}).get("ppets_tree_sha256")))
    ok = bool(rows) and all(r["ok"] for r in rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dict(all_ok=ok, checked=len(rows), files=rows), indent=2) + "\n", encoding="utf-8")
    for r in rows:
        print(("PASS " if r["ok"] else "FAIL ") + f"{r['file']} ({r['how']})")
    print(f"{sum(r['ok'] for r in rows)}/{len(rows)} evidence files match their manifests -> {OUT.relative_to(REPO).as_posix()}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
