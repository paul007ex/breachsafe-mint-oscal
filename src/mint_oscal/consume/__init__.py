# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: Apache-2.0
"""Consume OSCAL inputs (profiles, catalogs) that parameterize emitters.

Emitters generate OSCAL; the consume path reads it. A profile supplies
operational-defined parameters (ODPs / set-parameters); a catalog supplies
control text. Both are program inputs an emitter may need but must not invent.
"""

from __future__ import annotations

__all__: list[str] = []
