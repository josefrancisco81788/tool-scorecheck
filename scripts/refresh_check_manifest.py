#!/usr/bin/env python3
"""Rewrite checks/approved/MANIFEST.sha256 from the check files already there.

Human use only, after an intentional edit to an approved check.
Does not move drafts and does not decide whether a check is correct.

Stdlib only. Run from the project root with no flags:

    python scripts/refresh_check_manifest.py
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path.cwd()
APPROVED = ROOT / "checks" / "approved"
MANIFEST = APPROVED / "MANIFEST.sha256"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def main() -> int:
    if len(sys.argv) != 1:
        print("Run exactly: python scripts/refresh_check_manifest.py", file=sys.stderr)
        print("Do not add flags or parameters.", file=sys.stderr)
        return 1
    if not APPROVED.is_dir():
        print("Run this from the project root (checks/approved must exist).", file=sys.stderr)
        return 1

    files = sorted(p for p in APPROVED.glob("*.md") if p.is_file())
    if not files:
        print("No approved check files. Nothing to hash.", file=sys.stderr)
        return 1

    lines = [f"{sha256(path)}  {path.relative_to(ROOT).as_posix()}" for path in files]
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Manifest refreshed for {len(files)} check file(s).")
    print("This does not mean the checks are correct. Commit checks/approved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
