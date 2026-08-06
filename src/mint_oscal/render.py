# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Serialize an emitted OSCAL document to a target format.

JSON and YAML are the supported encodings, both produced natively. OSCAL YAML is the JSON
data model in YAML syntax, so dumping the same document mint emits as JSON yields valid OSCAL
YAML (verified against oscal-cli 3.2.0, including the YAML 1.1 ``no``/``yes`` boolean and
timestamp-like scalar traps).
"""

from __future__ import annotations

import json
from typing import Any

import yaml


class _OscalYamlDumper(yaml.SafeDumper):
    """A ``SafeDumper`` that never emits YAML anchors/aliases.

    An OSCAL document is data serialized as a tree, and mint may reuse a child mapping (for
    example a shared subject) in more than one place. The default dumper would collapse a
    repeated node into a YAML anchor/alias; that is legal YAML but a surprising OSCAL encoding,
    so force full expansion to keep the YAML an alias-free mirror of the JSON.
    """

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
        # ``sort_keys=False`` preserves mint's deterministic insertion order; a very large
        # ``width`` disables line-wrapping so output is byte-stable and long scalars round-trip
        # exactly. ``SafeDumper`` quotes any scalar that would otherwise resolve to a non-string
        # (``no``/``yes``/``007``/a timestamp), keeping every OSCAL string a string.
        return yaml.dump(
            document,
            Dumper=_OscalYamlDumper,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
            width=1 << 30,
        )
    raise ValueError(f"unknown output format {fmt!r}; expected one of: json, yaml")
