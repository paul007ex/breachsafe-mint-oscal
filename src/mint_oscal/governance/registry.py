# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Governed OSCAL Catalog/Profile registry loading and validation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from operator import itemgetter
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker


class RegistryError(ValueError):
    """Raised when a registry is malformed or fails a semantic integrity check."""


@dataclass(frozen=True)
class CatalogEntry:
    """Validated Catalog metadata exposed to CLI consumers."""

    id: str
    kind: str
    title: str
    uuid: str
    document_version: str
    oscal_version: str
    href: str
    source_uri: str
    sha256: str
    license: str
    compatibility: str
    status: str


@dataclass(frozen=True)
class Registry:
    """Validated registry document and its source directory."""

    root: Path
    registry_file: Path
    document: dict[str, Any]

    @property
    def catalogs(self) -> tuple[CatalogEntry, ...]:
        """Return Catalogs in deterministic ID order."""
        entries = [
            CatalogEntry(
                id=item["id"],
                kind=item["kind"],
                title=item["title"],
                uuid=item["uuid"],
                document_version=item["document-version"],
                oscal_version=item["oscal-version"],
                href=item["href"],
                source_uri=item["source"]["uri"],
                sha256=item["source"]["sha256"],
                license=item["source"]["license"],
                compatibility=item["compatibility"]["status"],
                status=item["review"]["status"],
            )
            for item in self.document["catalogs"]
        ]
        return tuple(sorted(entries, key=lambda item: item.id))


def _schema_path() -> Path:
    return Path(__file__).resolve().parents[1] / "schemas" / "breachsafe.registry.v1.schema.json"


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RegistryError(f"cannot read registry {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise RegistryError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise RegistryError("registry root must be a YAML mapping")
    return loaded


def _normalize_state(document: dict[str, Any]) -> dict[str, Any]:
    """Treat legacy registries without a lifecycle state as active."""
    if "registry-state" not in document:
        document["registry-state"] = "active"
    return document


def _schema_validate(document: dict[str, Any]) -> None:
    schema = json.loads(_schema_path().read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(document),
        key=lambda error: list(error.path),
    )
    if errors:
        details = "; ".join(
            f"{'.'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
            for error in errors[:8]
        )
        raise RegistryError(f"registry schema validation failed: {details}")


def _catalog_controls(document: object) -> set[str]:
    controls: set[str] = set()
    if isinstance(document, dict):
        if isinstance(document.get("id"), str) and (
            isinstance(document.get("parts"), list) or isinstance(document.get("controls"), list)
        ):
            controls.add(document["id"])
        for value in document.values():
            controls.update(_catalog_controls(value))
    elif isinstance(document, list):
        for value in document:
            controls.update(_catalog_controls(value))
    return controls


def _catalog_path(root: Path, href: str) -> Path:
    path = Path(href)
    return path if path.is_absolute() else (root / path).resolve()


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise RegistryError(f"cannot read Catalog {path}: {exc}") from exc
    return digest.hexdigest()


def _load_catalog_controls(root: Path, catalogs: list[dict[str, Any]]) -> dict[str, set[str]]:
    """Verify pinned Catalog files and return their discovered control IDs."""
    catalog_controls: dict[str, set[str]] = {}
    for entry in catalogs:
        path = _catalog_path(root, entry["href"])
        if not path.is_file():
            raise RegistryError(f"Catalog {entry['id']!r} does not exist: {path}")
        actual_digest = _digest(path)
        if actual_digest != entry["source"]["sha256"]:
            raise RegistryError(
                f"Catalog {entry['id']!r} digest mismatch: expected "
                f"{entry['source']['sha256']}, got {actual_digest}"
            )
        try:
            catalog_document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RegistryError(f"Catalog {entry['id']!r} is not valid JSON: {exc}") from exc
        catalog = catalog_document.get("catalog")
        if not isinstance(catalog, dict):
            raise RegistryError(f"Catalog {entry['id']!r} lacks an OSCAL catalog root")
        if catalog.get("uuid") != entry["uuid"]:
            raise RegistryError(f"Catalog {entry['id']!r} UUID does not match its registry pin")
        catalog_controls[entry["id"]] = _catalog_controls(catalog)
    return catalog_controls


def _validate_unique_ids(document: dict[str, Any]) -> tuple[list[str], set[str], set[str]]:
    """Validate collection identifiers and return profile/catalog/pack IDs."""
    catalogs = document["catalogs"]
    catalog_ids = [item["id"] for item in catalogs]
    if len(catalog_ids) != len(set(catalog_ids)):
        raise RegistryError("duplicate Catalog ID")
    profile_ids_list = [profile["id"] for profile in document["profiles"]]
    if len(profile_ids_list) != len(set(profile_ids_list)):
        raise RegistryError("duplicate Profile ID")
    pack_ids = [pack["id"] for pack in document["packs"]]
    if len(pack_ids) != len(set(pack_ids)):
        raise RegistryError("duplicate pack ID")
    objective_ids = [objective["id"] for objective in document["objectives"]]
    if len(objective_ids) != len(set(objective_ids)):
        raise RegistryError("duplicate objective ID")
    return profile_ids_list, set(catalog_ids), set(pack_ids)


def _validate_defaults(
    document: dict[str, Any], profile_ids: set[str], catalog_ids: set[str], pack_ids: set[str]
) -> None:
    """Ensure configured defaults refer to registered entries."""
    if document["defaults"]["catalog"] not in catalog_ids:
        raise RegistryError("default Catalog is not registered")
    if document["defaults"]["profile"] not in profile_ids:
        raise RegistryError("default Profile is not registered")
    if document["defaults"]["pack"] not in pack_ids:
        raise RegistryError("default pack is not registered")


def _validate_profiles(
    document: dict[str, Any], catalog_ids: set[str], catalog_controls: dict[str, set[str]]
) -> None:
    """Ensure profiles resolve to Catalogs and only select declared controls."""
    catalogs = document["catalogs"]
    for profile in document["profiles"]:
        if profile["catalog"] not in catalog_ids:
            raise RegistryError(f"Profile {profile['id']!r} references an unknown Catalog")
        expected_href = next(
            catalog["href"] for catalog in catalogs if catalog["id"] == profile["catalog"]
        )
        for import_entry in profile["imports"]:
            if import_entry["href"] != expected_href:
                raise RegistryError(
                    f"Profile {profile['id']!r} import href does not match its Catalog"
                )
            for selection in import_entry.get("include-controls", []):
                unknown = set(selection["with-ids"]) - catalog_controls[profile["catalog"]]
                if unknown:
                    raise RegistryError(
                        f"Profile {profile['id']!r} references unknown controls: {sorted(unknown)}"
                    )


def _validate_packs_and_objectives(
    document: dict[str, Any], catalog_ids: set[str], profile_ids: set[str]
) -> None:
    """Ensure packs and governed objectives resolve to registered dependencies."""
    for pack in document["packs"]:
        if pack["catalog"] not in catalog_ids:
            raise RegistryError(f"Pack {pack['id']!r} references an unknown Catalog")
        if pack["profile"] not in profile_ids:
            raise RegistryError(f"Pack {pack['id']!r} references an unknown Profile")

    for objective in document["objectives"]:
        unknown_profiles = set(objective["profiles"]) - profile_ids
        if unknown_profiles:
            raise RegistryError(
                f"Objective {objective['id']!r} references unknown Profiles: "
                f"{sorted(unknown_profiles)}"
            )


def _semantic_validate(root: Path, document: dict[str, Any]) -> None:
    """Apply cross-document registry integrity checks after schema validation."""
    profile_ids_list, catalog_ids, pack_ids = _validate_unique_ids(document)
    catalog_controls = _load_catalog_controls(root, document["catalogs"])
    profile_ids = set(profile_ids_list)
    if document["registry-state"] == "active":
        _validate_defaults(document, profile_ids, catalog_ids, pack_ids)
    _validate_profiles(document, catalog_ids, catalog_controls)
    _validate_packs_and_objectives(document, catalog_ids, profile_ids)


def load_registry(path: str | Path = "policy") -> Registry:
    """Load, schema-validate, and semantically validate a registry directory."""
    root = Path(path).resolve()
    if root.is_file():
        registry_file = root
        root = root.parent
    else:
        registry_file = root / "registry.yaml"
    document = _normalize_state(_read_yaml(registry_file))
    _schema_validate(document)
    _semantic_validate(root, document)
    return Registry(root=root, registry_file=registry_file, document=document)


def _canonical_lock(registry: Registry) -> dict[str, Any]:
    """Build the deterministic integrity projection for a validated registry."""
    profiles: dict[str, dict[str, Any]] = {}
    for profile in sorted(registry.document["profiles"], key=itemgetter("id")):
        ids = [
            control_id
            for import_entry in profile["imports"]
            for selection in import_entry["include-controls"]
            for control_id in selection["with-ids"]
        ]
        profiles[profile["id"]] = {
            "catalog": profile["catalog"],
            "control_ids": sorted(ids),
            "source_sha256": hashlib.sha256(
                json.dumps(profile, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
        }
    catalogs = {
        entry.id: {
            "oscal_version": entry.oscal_version,
            "sha256": entry.sha256,
            "uuid": entry.uuid,
        }
        for entry in registry.catalogs
    }
    return {
        "schema": "breachsafe.registry.lock/v1",
        "registry_version": registry.document["registry-version"],
        "source_sha256": hashlib.sha256(registry.registry_file.read_bytes()).hexdigest(),
        "resolver_version": "mint-oscal/0.2",
        "catalogs": catalogs,
        "profiles": profiles,
    }


def lock_registry(path: str | Path = "policy", output: str | Path | None = None) -> Path:
    """Write a canonical registry lock and return its path."""
    registry = load_registry(path)
    target = Path(output) if output else registry.root / "registry.lock.json"
    target = target.resolve()
    target.write_text(
        json.dumps(_canonical_lock(registry), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def verify_lock(path: str | Path = "policy", lock: str | Path | None = None) -> Path:
    """Verify that the lock bytes match the current validated registry."""
    registry = load_registry(path)
    target = Path(lock) if lock else registry.root / "registry.lock.json"
    target = target.resolve()
    try:
        actual = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryError(f"cannot read registry lock {target}: {exc}") from exc
    expected = json.dumps(_canonical_lock(registry), indent=2, sort_keys=True) + "\n"
    if actual != json.loads(expected) or target.read_bytes() != expected.encode("utf-8"):
        raise RegistryError(f"registry lock mismatch: {target}")
    return target
