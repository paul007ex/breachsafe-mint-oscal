# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Bundled, file-driven crypto classification data for the CBOM adapter.

``crypto-registry.yaml`` and ``readiness-rules.yaml`` are read (not imported) via
:mod:`importlib.resources`. Keeping them as data means adding a PQC algorithm or a
readiness rule is a config edit, not a code change (ADR-0006).
"""

from __future__ import annotations
