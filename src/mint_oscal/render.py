# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Serialize an emitted OSCAL document to JSON or YAML."""

from __future__ import annotations

import json
from typing import Any

import yaml


class _OscalYamlDumper(yaml.SafeDumper):
    """Emit alias-free YAML so shared Python mappings remain explicit tree data."""

    def ignore_aliases(self, data: object) -> bool:  # noqa: ARG002 -- always expand
        return True


def render(document: dict[str, Any], *, fmt: str = "json") -> str:
    """Serialize ``document`` to ``fmt`` (``json`` | ``yaml``).

    Raises:
        ValueError: for an unknown format.
    """
    if fmt == "json":
        return json.dumps(document, indent=2)
    if fmt == "yaml":
        return yaml.dump(
            document,
            Dumper=_OscalYamlDumper,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
            width=1 << 30,
        )
    raise ValueError(f"unknown output format {fmt!r}; expected one of: json, yaml")
