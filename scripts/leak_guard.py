# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Fail if a built distribution ships internal tooling.

Inspects the *namelists* of every wheel (zip) and sdist (tar.gz) in a dist
directory and rejects the build if any archived path contains an internal
tooling marker (``.claude``, ``.agents``, ``scratch``, ``AGENTS.md``,
``mint-proof``, ``.venv``). We read the archive members directly rather than
trusting the source tree, so a path packaged by mistake is still caught.

Usage::

    python scripts/leak_guard.py dist
"""

from __future__ import annotations

import sys
import tarfile
import zipfile
from pathlib import Path

# Case-insensitive substrings that must never appear in a distributed artifact.
FORBIDDEN = (".claude", ".agents", "scratch", "agents.md", "mint-proof", ".venv")


def _members(dist: Path) -> list[tuple[Path, str]]:
    """Return ``(archive, member_name)`` pairs for every wheel/sdist in *dist*."""
    pairs: list[tuple[Path, str]] = []
    for whl in sorted(dist.glob("*.whl")):
        with zipfile.ZipFile(whl) as zf:
            pairs += [(whl, name) for name in zf.namelist()]
    for sdist in sorted(dist.glob("*.tar.gz")):
        with tarfile.open(sdist) as tf:
            pairs += [(sdist, m.name) for m in tf.getmembers()]
    return pairs


def main(argv: list[str] | None = None) -> int:
    """Scan artifacts; return non-zero (and report) on any forbidden path."""
    args = argv if argv is not None else sys.argv[1:]
    dist = Path(args[0]) if args else Path("dist")

    pairs = _members(dist)
    if not pairs:
        print(f"leak-guard: no artifacts found under {dist}/ -- did the build run?")
        return 1

    leaks = [
        (archive.name, name)
        for archive, name in pairs
        for marker in FORBIDDEN
        if marker in name.lower()
    ]
    if leaks:
        print("leak-guard: FORBIDDEN internal-tooling path(s) found in artifacts:")
        for archive, name in leaks:
            print(f"  {archive}: {name}")
        return 1

    archives = sorted({archive.name for archive, _ in pairs})
    print(f"leak-guard: clean -- {len(pairs)} member(s) across {len(archives)} artifact(s):")
    for archive in archives:
        print(f"  {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
