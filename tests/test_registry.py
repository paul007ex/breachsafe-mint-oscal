# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Contract tests for the governed OSCAL registry."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from mint_oscal.cli import main
from mint_oscal.registry import RegistryError, load_registry, lock_registry, verify_lock


def _catalog(uuid: str, control_ids: list[str]) -> dict[str, object]:
    return {
        "catalog": {
            "uuid": uuid,
            "metadata": {
                "title": "Fixture Catalog",
                "last-modified": "2026-08-24",
                "version": "1.0",
                "oscal-version": "1.2.1",
            },
            "groups": [
                {
                    "id": "security",
                    "title": "Security",
                    "controls": [
                        {
                            "id": control_id,
                            "title": control_id,
                            "parts": [
                                {"id": f"{control_id}_smt", "name": "statement", "prose": "Fixture"}
                            ],
                        }
                        for control_id in control_ids
                    ],
                }
            ],
        }
    }


def _registry(tmp_path: Path, *, control_id: str = "qts-04") -> Path:
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(
        json.dumps(_catalog("11111111-1111-4111-8111-111111111111", [control_id])), encoding="utf-8"
    )
    digest = hashlib.sha256(catalog_path.read_bytes()).hexdigest()
    document = {
        "schema": "breachsafe.registry/v1",
        "registry-version": "0.4.0",
        "metadata": {
            "title": "Fixture Registry",
            "version": "0.4.0",
            "last-modified": "2026-08-24",
            "oscal-version": "1.2.1",
        },
        "defaults": {"catalog": "fixture", "profile": "fixture-profile", "pack": "fixture-pack"},
        "catalogs": [
            {
                "id": "fixture",
                "kind": "catalog",
                "uuid": "11111111-1111-4111-8111-111111111111",
                "title": "Fixture Catalog",
                "authority": "BreachSAFE",
                "document-version": "1.0",
                "oscal-version": "1.2.1",
                "href": "catalog.json",
                "source": {
                    "uri": "https://example.invalid/catalog.json",
                    "sha256": digest,
                    "license": "PolyForm-Noncommercial-1.0.0",
                    "retrieved-at": "2026-08-24",
                },
                "compatibility": {"trestle": "ready", "oscal-cli": "ready", "status": "ready"},
                "review": {"status": "approved", "owner": "test", "reviewed-at": "2026-08-24"},
            }
        ],
        "profiles": [
            {
                "id": "fixture-profile",
                "kind": "profile",
                "title": "Fixture Profile",
                "version": "0.1.0",
                "catalog": "fixture",
                "oscal-version": "1.2.1",
                "imports": [
                    {"href": "catalog.json", "include-controls": [{"with-ids": [control_id]}]}
                ],
                "review": {"status": "approved", "owner": "test", "reviewed-at": "2026-08-24"},
            }
        ],
        "packs": [
            {
                "id": "fixture-pack",
                "kind": "breachsafe-pack",
                "title": "Fixture Pack",
                "framework": "fixture",
                "catalog": "fixture",
                "profile": "fixture-profile",
                "version": "0.1.0",
                "status": "approved",
            }
        ],
        "objectives": [
            {
                "id": "fixture-objective",
                "kind": "governed-objective",
                "title": "Fixture Objective",
                "version": "0.1.0",
                "status": "approved",
                "profiles": ["fixture-profile"],
                "review": {"status": "approved", "owner": "test", "reviewed-at": "2026-08-24"},
                "constraints": {},
            }
        ],
        "crosswalks": [],
    }
    registry_path = tmp_path / "registry.yaml"
    registry_path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return registry_path


def test_valid_registry_loads_and_lists_catalog(tmp_path: Path) -> None:
    registry = load_registry(_registry(tmp_path))
    assert [entry.id for entry in registry.catalogs] == ["fixture"]


def test_registry_cli_list_and_validate(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    registry = _registry(tmp_path)
    assert main(["registry", "validate", "--registry", str(registry)]) == 0
    assert main(["registry", "list", "--registry", str(registry)]) == 0
    output = capsys.readouterr().out
    assert "Valid active registry" in output
    assert "fixture\tcatalog\t1.0\t1.2.1\tready" in output


def test_digest_mismatch_fails_closed(tmp_path: Path) -> None:
    registry_path = _registry(tmp_path)
    document = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    document["catalogs"][0]["source"]["sha256"] = "0" * 64
    registry_path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    with pytest.raises(RegistryError, match="digest mismatch"):
        load_registry(registry_path)


def test_unknown_control_fails_closed(tmp_path: Path) -> None:
    registry_path = _registry(tmp_path, control_id="qts-04")
    document = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    document["profiles"][0]["imports"][0]["include-controls"][0]["with-ids"] = ["qts-99"]
    registry_path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    with pytest.raises(RegistryError, match="unknown controls"):
        load_registry(registry_path)


def test_unknown_field_fails_schema(tmp_path: Path) -> None:
    registry_path = _registry(tmp_path)
    document = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    document["unexpected"] = True
    registry_path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    with pytest.raises(RegistryError, match="schema validation failed"):
        load_registry(registry_path)


def test_lock_is_deterministic_and_verifiable(tmp_path: Path) -> None:
    registry_path = _registry(tmp_path)
    first = lock_registry(registry_path, tmp_path / "lock-a.json")
    second = lock_registry(registry_path, tmp_path / "lock-b.json")
    assert first.read_bytes() == second.read_bytes()
    assert verify_lock(registry_path, first) == first


def test_lock_ignores_yaml_comments_and_formatting(tmp_path: Path) -> None:
    registry_path = _registry(tmp_path)
    lock = lock_registry(registry_path)
    document = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    registry_path.write_text(
        "# Formatting-only comment.\n" + yaml.safe_dump(document, sort_keys=True),
        encoding="utf-8",
    )

    assert verify_lock(registry_path, lock) == lock


def test_lock_rejects_semantic_registry_change(tmp_path: Path) -> None:
    registry_path = _registry(tmp_path)
    lock = lock_registry(registry_path)
    document = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    document["metadata"]["title"] = "Changed Registry"
    registry_path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    with pytest.raises(RegistryError, match="lock mismatch"):
        verify_lock(registry_path, lock)


def test_lock_mismatch_fails_closed(tmp_path: Path) -> None:
    registry_path = _registry(tmp_path)
    lock = lock_registry(registry_path)
    lock.write_text(lock.read_text(encoding="utf-8").replace("0.4.0", "0.4.1"), encoding="utf-8")
    with pytest.raises(RegistryError, match="lock mismatch"):
        verify_lock(registry_path)


def test_custom_registry_filename_is_used_for_lock_source(tmp_path: Path) -> None:
    registry_path = _registry(tmp_path)
    custom_path = tmp_path / "governed-registry.yaml"
    custom_path.write_bytes(registry_path.read_bytes())
    lock = lock_registry(custom_path)
    assert verify_lock(custom_path, lock) == lock


def test_lock_rejects_noncanonical_json_bytes(tmp_path: Path) -> None:
    registry_path = _registry(tmp_path)
    lock = lock_registry(registry_path)
    lock.write_text(json.dumps(json.loads(lock.read_text(encoding="utf-8"))), encoding="utf-8")
    with pytest.raises(RegistryError, match="lock mismatch"):
        verify_lock(registry_path, lock)


@pytest.mark.parametrize("field", ["catalog", "profile", "pack"])
def test_invalid_default_reference_fails(tmp_path: Path, field: str) -> None:
    path = _registry(tmp_path)
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["defaults"][field] = "missing"
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    with pytest.raises(RegistryError, match="not registered"):
        load_registry(path)


@pytest.mark.parametrize("collection", ["catalogs", "profiles", "packs", "objectives"])
def test_duplicate_registry_ids_fail(tmp_path: Path, collection: str) -> None:
    path = _registry(tmp_path)
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document[collection].append(document[collection][0].copy())
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    with pytest.raises(RegistryError, match="duplicate"):
        load_registry(path)
