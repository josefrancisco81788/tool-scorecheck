#!/usr/bin/env python3
"""Move checks/draft/*.md into checks/approved/ and rewrite MANIFEST.sha256.

Stdlib only. Run from the project root with no flags:

    python scripts/lock_checks.py
"""

from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path.cwd()
DRAFT = ROOT / "checks" / "draft"
APPROVED = ROOT / "checks" / "approved"
MANIFEST = APPROVED / "MANIFEST.sha256"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def approved_markdown() -> list[Path]:
    return sorted(p for p in APPROVED.glob("*.md") if p.is_file())


def parse_manifest(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        digest, rel = line.split("  ", 1)
        entries[rel] = digest
    return entries


def manifest_matches_disk() -> bool:
    if not MANIFEST.exists():
        return False
    expected = parse_manifest(MANIFEST)
    actual = {p.relative_to(ROOT).as_posix(): sha256(p) for p in approved_markdown()}
    return expected == actual


def write_manifest() -> int:
    lines = []
    for path in approved_markdown():
        rel = path.relative_to(ROOT).as_posix()
        lines.append(f"{sha256(path)}  {rel}")
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)


def main() -> int:
    if len(sys.argv) != 1:
        print("Run exactly: python scripts/lock_checks.py", file=sys.stderr)
        print("Do not add flags or parameters.", file=sys.stderr)
        return 1
    if not DRAFT.is_dir() or not APPROVED.is_dir():
        print(
            "Run this from the project root (checks/draft and checks/approved must exist).",
            file=sys.stderr,
        )
        return 1

    existing = approved_markdown()
    if existing and not manifest_matches_disk():
        print(
            "Approved checks do not match MANIFEST.sha256. Refusing to lock.",
            file=sys.stderr,
        )
        print(
            "A human must repair the evaluation before new checks can be locked.",
            file=sys.stderr,
        )
        return 1

    drafts = sorted(p for p in DRAFT.glob("*.md") if p.is_file())
    if not drafts:
        print("No markdown files in checks/draft. Nothing to lock.", file=sys.stderr)
        return 1

    collisions = [p.name for p in drafts if (APPROVED / p.name).exists()]
    if collisions:
        print(
            "Refusing to overwrite approved checks: " + ", ".join(collisions),
            file=sys.stderr,
        )
        return 1

    for src in drafts:
        shutil.move(str(src), APPROVED / src.name)

    count = write_manifest()
    print(f"Locked {count} check file(s). Manifest: checks/approved/MANIFEST.sha256")
    print("Commit checks/approved before implementation starts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
