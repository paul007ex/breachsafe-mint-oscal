# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Serialize an emitted OSCAL document to a target format.

JSON is native and always available. XML and YAML are produced by shelling out to
the external NIST ``oscal-cli`` (converting the native JSON), rather than by
carrying a second serializer in-tree. That boundary is the subject of ADR-0005
(``oscal-cli`` as the format-conversion oracle); see also the ``xml`` optional
dependency group in ``pyproject.toml``.
"""

from __future__ import annotations

import json
from typing import Any

_CLI_FORMATS = ("xml", "yaml")


def render(document: dict[str, Any], *, fmt: str = "json") -> str:
    """Serialize ``document`` to ``fmt`` (``json`` | ``xml`` | ``yaml``).

    JSON is serialized natively. XML/YAML require the external ``oscal-cli`` and are
    not implemented in-process (ADR-0005).

    Raises:
        NotImplementedError: for ``xml``/``yaml`` (delegated to ``oscal-cli``).
        ValueError: for an unknown format.
    """
    if fmt == "json":
        return json.dumps(document, indent=2)
    if fmt in _CLI_FORMATS:
        raise NotImplementedError(
            f"render(fmt={fmt!r}): XML/YAML output is produced by shelling out to the "
            "external NIST oscal-cli, which is not wired in yet (ADR-0005). Install "
            "oscal-cli and use the 'xml' optional-dependency group when this lands."
        )
    raise ValueError(f"unknown output format {fmt!r}; expected one of: json, xml, yaml")
