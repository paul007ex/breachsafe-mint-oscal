# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Tests for governed registry workspace and Catalog creation."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from mint_oscal.governance.registry import RegistryError, load_registry, verify_lock
from mint_oscal.governance.registry_builder import CatalogSource, add_catalog, init_registry

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "registry"
CATALOG = FIXTURE / "catalogs" / "nist-800-53r5" / "catalog.json"


def _copy_fixture(tmp_path: Path) -> Path:
    target = tmp_path / "policy"
    shutil.copytree(FIXTURE, target)
    (target / "registry.lock.json").unlink(missing_ok=True)
    return target


def test_init_creates_workspace_without_fabricating_policy(tmp_path: Path) -> None:
    root = init_registry(tmp_path / "policy")
    assert root.is_dir()
    assert (root / "catalogs").is_dir()
    assert not (root / "registry.yaml").exists()


def test_add_catalog_copies_provenance_and_lock(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)
    destination = add_catalog(
        root,
        CatalogSource(
            catalog_id="nist-copy",
            source_file=CATALOG,
            source_uri="https://github.com/usnistgov/oscal-content",
            release="v1.5.0",
            license_name="NIST",
            authority="NIST",
        ),
    )
    assert destination.is_file()
    registry = load_registry(root)
    assert {entry.id for entry in registry.catalogs} == {
        "nist-800-53r5",
        "nist-copy",
        "scf-qts-2026-2",
    }
    verify_lock(root)


def test_add_catalog_rejects_duplicate_without_mutating_registry(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)
    original = (root / "registry.yaml").read_bytes()
    with pytest.raises(RegistryError, match="already exists"):
        add_catalog(
            root,
            CatalogSource(
                catalog_id="nist-800-53r5",
                source_file=CATALOG,
                source_uri="https://example.invalid/catalog",
                release="test",
                license_name="NIST",
                authority="NIST",
            ),
        )
    assert (root / "registry.yaml").read_bytes() == original
