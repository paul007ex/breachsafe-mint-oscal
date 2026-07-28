# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""The bundled ``default`` policy pack (readiness -> severity, controls, risk prose).

The three YAMLs here are the reviewable, versioned policy the engine consults; they
are read (not imported) via :mod:`importlib.resources`. This module exists only to
make the directory an importable resource package.
"""

from __future__ import annotations
