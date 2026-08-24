# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Create and update governed registry source files."""

from __future__ import annotations

import contextlib
import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from mint_oscal.governance.registry import RegistryError, load_registry, lock_registry

_CATALOG_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass(frozen=True)
class CatalogSource:
    """Provenance supplied by the registry author for one Catalog import."""

    catalog_id: str
    source_file: Path
    source_uri: str
    release: str
    license_name: str
    authority: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


def init_registry(output: str | Path) -> Path:
    """Create an empty registry workspace; Catalog import creates the YAML contract."""
    root = Path(output).resolve()
    if root.exists() and any(root.iterdir()):
        raise RegistryError(f"registry directory is not empty: {root}")
    (root / "catalogs").mkdir(parents=True, exist_ok=True)
    (root / "packs").mkdir(parents=True, exist_ok=True)
    (root / "generated").mkdir(parents=True, exist_ok=True)
    return root


def _read_catalog(source: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        document = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryError(f"input Catalog is not valid JSON: {exc}") from exc
    catalog = document.get("catalog")
    if not isinstance(catalog, dict):
        raise RegistryError("input is not an OSCAL Catalog document")
    metadata = catalog.get("metadata")
    if not isinstance(metadata, dict):
        raise RegistryError("Catalog metadata is required")
    if not isinstance(catalog.get("uuid"), str):
        raise RegistryError("Catalog UUID is required")
    for field in ("title", "version", "oscal-version"):
        if not isinstance(metadata.get(field), str) or not metadata[field]:
            raise RegistryError(f"Catalog metadata.{field} is required")
    return catalog, metadata


def _load_registry_source(registry_file: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load the mutable registry source and its Catalog collection."""
    document = yaml.safe_load(registry_file.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise RegistryError("registry root must be a YAML mapping")
    catalogs = document.get("catalogs")
    if not isinstance(catalogs, list):
        raise RegistryError("registry catalogs must be a YAML list")
    return document, catalogs


def _catalog_entry(
    source: CatalogSource, catalog: dict[str, Any], metadata: dict[str, Any], path: Path
) -> dict[str, Any]:
    """Build one schema-shaped Catalog metadata entry."""
    return {
        "id": source.catalog_id,
        "kind": "catalog",
        "uuid": catalog["uuid"],
        "title": metadata["title"],
        "authority": source.authority,
        "document-version": metadata["version"],
        "oscal-version": metadata["oscal-version"],
        "href": f"catalogs/{source.catalog_id}/catalog.json",
        "source": {
            "uri": source.source_uri,
            "release": source.release,
            "sha256": _sha256(path),
            "license": source.license_name,
            "retrieved-at": _today(),
        },
        "compatibility": {
            "trestle": "not-evaluated",
            "oscal-cli": "not-evaluated",
            "status": "blocked",
            "reason": "Imported; independent conformance review required.",
        },
        "review": {
            "status": "draft",
            "owner": "registry-import",
            "reviewed-at": _today(),
        },
    }


def _rollback_import(registry_file: Path, original: bytes, destination: Path) -> None:
    """Restore registry bytes and remove a partially copied Catalog."""
    registry_file.write_bytes(original)
    destination.unlink(missing_ok=True)
    with contextlib.suppress(OSError):
        destination.parent.rmdir()


def add_catalog(registry_path: str | Path, source: CatalogSource) -> Path:
    """Copy a Catalog, record provenance, validate the registry, and write its lock."""
    if _CATALOG_ID_PATTERN.fullmatch(source.catalog_id) is None:
        raise RegistryError(f"invalid Catalog ID: {source.catalog_id!r}")
    root = Path(registry_path).resolve()
    registry_file = root / "registry.yaml"
    source_file = source.source_file.resolve()
    if not registry_file.is_file():
        raise RegistryError(f"registry.yaml does not exist: {registry_file}")
    if not source_file.is_file():
        raise RegistryError(f"Catalog file does not exist: {source_file}")
    catalog, metadata = _read_catalog(source_file)
    document, catalogs = _load_registry_source(registry_file)
    if any(item.get("id") == source.catalog_id for item in catalogs):
        raise RegistryError(f"Catalog ID already exists: {source.catalog_id}")
    destination_dir = root / "catalogs" / source.catalog_id
    if destination_dir.exists():
        raise RegistryError(f"Catalog destination already exists: {destination_dir}")
    destination_dir.mkdir(parents=True)
    destination = destination_dir / "catalog.json"
    original_registry = registry_file.read_bytes()
    try:
        shutil.copy2(source_file, destination)
        catalogs.append(_catalog_entry(source, catalog, metadata, destination))
        registry_file.write_text(
            yaml.safe_dump(document, sort_keys=False, allow_unicode=False),
            encoding="utf-8",
        )
        load_registry(root)
        lock_registry(root)
    except OSError, RegistryError, TypeError, ValueError, yaml.YAMLError:
        _rollback_import(registry_file, original_registry, destination)
        raise
    return destination
