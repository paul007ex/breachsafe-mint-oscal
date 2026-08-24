# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Fail when a registry lock is stale or cannot be reproduced."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from mint_oscal.governance.registry import RegistryError, lock_registry, verify_lock


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True, help="registry workspace")
    return parser


def main() -> int:
    """Regenerate a temporary lock and compare it with the committed lock."""
    args = _parser().parse_args()
    registry = args.registry.resolve()
    lock = registry / "registry.lock.json"
    try:
        verify_lock(registry, lock)
        with tempfile.TemporaryDirectory(prefix="mint-oscal-registry-") as directory:
            regenerated = lock_registry(registry, Path(directory) / "registry.lock.json")
            if regenerated.read_bytes() != lock.read_bytes():
                raise RegistryError(f"registry lock is not byte-stable: {lock}")
    except RegistryError as exc:
        print(f"registry drift: {exc}")
        return 1
    print(f"registry reproducibility OK: {registry}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
