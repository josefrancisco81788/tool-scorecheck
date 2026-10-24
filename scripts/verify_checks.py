#!/usr/bin/env python3
"""Confirm checks/approved still matches MANIFEST.sha256.

Stdlib only. Run from the project root with no flags:

    python scripts/verify_checks.py
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
        print("Run exactly: python scripts/verify_checks.py", file=sys.stderr)
        print("Do not add flags or parameters.", file=sys.stderr)
        return 1
    if not MANIFEST.exists():
        print("No checks/approved/MANIFEST.sha256. Checks are not locked.", file=sys.stderr)
        return 1

    expected: dict[str, str] = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        digest, rel = line.split("  ", 1)
        expected[rel] = digest

    actual = {
        path.relative_to(ROOT).as_posix(): sha256(path)
        for path in sorted(APPROVED.glob("*.md"))
        if path.is_file()
    }

    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    mismatched = sorted(
        key for key in expected.keys() & actual.keys() if expected[key] != actual[key]
    )

    if missing or extra or mismatched:
        if missing:
            print("Missing: " + ", ".join(missing), file=sys.stderr)
        if extra:
            print("Unexpected: " + ", ".join(extra), file=sys.stderr)
        if mismatched:
            print("Hash mismatch: " + ", ".join(mismatched), file=sys.stderr)
        print("Approved checks changed. Stop and ask the user.", file=sys.stderr)
        return 1

    print(f"Locked checks verified ({len(actual)} file(s)).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
