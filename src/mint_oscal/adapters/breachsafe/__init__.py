# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""BreachSAFE-specific adapters that overlay the vendor-neutral core (ADR-0008).

Everything under this package reads a BreachSAFE-branded input signal; the
vendor-neutral adapters in the parent package know nothing about it. This split
keeps ``adapters/cbom.py`` a pure CycloneDX -> IR translator and confines all
``breachsafe:v1`` knowledge here, so the whole subtree is promotable to a separate
distribution through the existing ``mint_oscal.adapters`` entry-point group without
touching the core.
"""

from __future__ import annotations
