# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Compatibility import for the CBOM adapter.

The implementation lives in :mod:`mint_oscal.ingestion.cbom`; this stable module path
is retained for third-party adapters and the bundled entry point.
"""

from mint_oscal.ingestion.cbom import MalformedCbomError, from_cbom

__all__ = ["MalformedCbomError", "from_cbom"]
