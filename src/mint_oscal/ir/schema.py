# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Load and validate a document against the ``mint.ir.v1`` JSON Schema.

The IR is normally built in-process by an adapter (see ``mint_oscal.adapters``).
``load_ir`` is the alternate path: rehydrate an IR from a serialized
``mint.ir.v1`` document (for example one emitted by an out-of-process adapter),
validating it against ``mint.ir.v1.schema.json`` first.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mint_oscal.ir.model import IR

SCHEMA_PATH = Path(__file__).with_name("mint.ir.v1.schema.json")


def load_ir(doc: dict[str, Any]) -> IR:
    """Validate ``doc`` against ``mint.ir.v1`` and build an :class:`IR`.

    Not yet implemented: deserialization of the IR wire format is a P1 item once a
    second (out-of-process) adapter exists. See ADR-0004 (agnostic core) and
    UC-INGEST.

    Raises:
        NotImplementedError: always, until the IR wire format lands.
    """
    raise NotImplementedError(
        "load_ir: mint.ir.v1 deserialization is not implemented yet (ADR-0004, UC-INGEST)"
    )


def validate(doc: dict[str, Any]) -> list[str]:
    """Return schema-validation problems for ``doc``, empty if it conforms.

    Not yet implemented: pending selection of a bundled JSON Schema validator (a
    ``dev``-only dependency vs. a runtime one). See ADR-0004.

    Raises:
        NotImplementedError: always, until a validator is wired in.
    """
    raise NotImplementedError(
        "validate: mint.ir.v1 schema validation is not implemented yet (ADR-0004)"
    )
