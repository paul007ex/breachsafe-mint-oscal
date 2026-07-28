# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Extension discovery: name -> enricher that refines the IR from producer facts.

Source and extension are orthogonal (ADR-0008). A ``--from`` *adapter* turns a
source document into the neutral IR; an *extension* is an opt-in enricher that runs
*after* the adapter and refines that IR using producer-declared facts carried in the
same document (e.g. the ``breachsafe:v1:*`` CycloneDX properties). Keeping them apart
means ``--from cbom`` stays vendor-neutral while ``--extension breachsafe`` adds the
BreachSAFE cross-check without a bespoke source.

Extensions are discovered through the ``mint_oscal.extensions`` entry-point group, so
a third party ships an enricher as its own distribution without editing this package
(ADR-0004: agnostic core, ports & adapters). ``breachsafe`` is bundled here as a
convenience and is always available even from a source checkout.

An enricher is a pure ``Callable[..., tuple[list[Finding], Subject]]`` with the
signature ``enrich(findings, subject, *, document)``: it reads the raw source
``document`` for producer facts, returns a (possibly refined) findings list and
subject, and never logs, prints, or exits.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from mint_oscal._registry import discover, resolve
from mint_oscal.ir import Finding, Subject

Extension = Callable[..., tuple[list[Finding], Subject]]

_ENTRY_POINT_GROUP = "mint_oscal.extensions"
# Bundled fallbacks: name -> "module:callable". Entry-point extensions still win.
_BUILTINS = {
    "breachsafe": "mint_oscal.extensions.breachsafe:enrich",
}


def get_extension(name: str) -> Extension:
    """Return the enricher registered under ``name``.

    Entry-point extensions win; the bundled ``breachsafe`` enricher is the fallback so
    it resolves even before the package is installed.

    Raises:
        KeyError: if no extension is registered under ``name``.
    """
    return cast(
        "Extension",
        resolve(_ENTRY_POINT_GROUP, _BUILTINS, name, "extension", available_extensions()),
    )


def available_extensions() -> set[str]:
    """Return the names of all discoverable enrichers."""
    return discover(_ENTRY_POINT_GROUP, _BUILTINS)


def apply_extensions(
    findings: list[Finding],
    subject: Subject,
    names: list[str],
    *,
    document: dict[str, Any],
) -> tuple[list[Finding], Subject]:
    """Apply each named enricher, in the order given, to the IR.

    Each enricher receives the output of the previous one, so extensions compose. An
    enricher is pure and returns a new findings list and subject; applying the same
    enricher twice is idempotent for ``breachsafe`` (it overwrites its own provenance
    verdict rather than accumulating), so a repeated ``--extension`` does no harm.

    Raises:
        KeyError: if any name has no registered extension.
    """
    for name in names:
        enrich = get_extension(name)
        findings, subject = enrich(findings, subject, document=document)
    return findings, subject


__all__ = [
    "Extension",
    "apply_extensions",
    "available_extensions",
    "get_extension",
]
