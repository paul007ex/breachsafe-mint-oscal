# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Tests for governed registry workspace and Catalog creation."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml

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


def test_init_creates_valid_bootstrap_registry(tmp_path: Path) -> None:
    root = init_registry(tmp_path / "policy")
    assert root.is_dir()
    assert (root / "catalogs").is_dir()
    assert (root / "packs").is_dir()
    assert (root / "generated").is_dir()
    assert (root / "registry.yaml").is_file()

    registry = load_registry(root)
    assert registry.document["registry-state"] == "bootstrap"
    assert registry.document["catalogs"] == []
    assert registry.document["profiles"] == []
    assert registry.document["packs"] == []


def test_init_then_add_catalog_then_lock_and_verify(tmp_path: Path) -> None:
    root = init_registry(tmp_path / "policy")
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
    assert registry.document["registry-state"] == "bootstrap"
    assert [entry.id for entry in registry.catalogs] == ["nist-copy"]
    assert verify_lock(root, root / "registry.lock.json") == root / "registry.lock.json"


def test_active_registry_requires_defaults(tmp_path: Path) -> None:
    root = init_registry(tmp_path / "policy")
    document = yaml.safe_load((root / "registry.yaml").read_text(encoding="utf-8"))
    document["registry-state"] = "active"
    (root / "registry.yaml").write_text(yaml.safe_dump(document), encoding="utf-8")

    with pytest.raises(RegistryError, match="defaults"):
        load_registry(root)


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


def test_add_catalog_rejects_path_traversal_before_writing(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)
    with pytest.raises(RegistryError, match="invalid Catalog ID"):
        add_catalog(
            root,
            CatalogSource(
                catalog_id="../../escaped/catalog",
                source_file=CATALOG,
                source_uri="https://example.invalid/catalog",
                release="test",
                license_name="NIST",
                authority="NIST",
            ),
        )
    assert not (tmp_path / "escaped").exists()


def test_init_rejects_nonempty_directory(tmp_path: Path) -> None:
    target = tmp_path / "policy"
    target.mkdir()
    (target / "keep.txt").write_text("do not overwrite", encoding="utf-8")

    with pytest.raises(RegistryError, match="not empty"):
        init_registry(target)


@pytest.mark.parametrize(
    ("field", "message"),
    [("metadata", "Catalog metadata"), ("uuid", "Catalog UUID"), ("title", "metadata.title")],
)
def test_add_catalog_rejects_malformed_catalog(tmp_path: Path, field: str, message: str) -> None:
    root = init_registry(tmp_path / "policy")
    source = tmp_path / "bad.json"
    document = {"catalog": {"uuid": "11111111-1111-4111-8111-111111111111", "metadata": {}}}
    if field == "metadata":
        del document["catalog"]["metadata"]
    elif field == "uuid":
        del document["catalog"]["uuid"]
    else:
        document["catalog"]["metadata"] = {"title": "", "version": "1", "oscal-version": "1.2.1"}
    source.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(RegistryError, match=message):
        add_catalog(
            root,
            CatalogSource("bad", source, "https://example.invalid/catalog", "test", "test", "test"),
        )


def test_add_catalog_rolls_back_when_resulting_registry_is_invalid(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)
    document = yaml.safe_load((root / "registry.yaml").read_text(encoding="utf-8"))
    document["registry-state"] = "active"
    del document["defaults"]
    (root / "registry.yaml").write_text(yaml.safe_dump(document), encoding="utf-8")
    original = (root / "registry.yaml").read_bytes()

    with pytest.raises(RegistryError):
        add_catalog(
            root,
            CatalogSource(
                "rollback", CATALOG, "https://example.invalid/catalog", "test", "test", "test"
            ),
        )
    assert (root / "registry.yaml").read_bytes() == original
    assert not (root / "catalogs" / "rollback").exists()
