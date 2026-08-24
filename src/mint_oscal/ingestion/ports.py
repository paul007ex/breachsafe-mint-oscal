# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Stable ports between untrusted source adapters and the trusted IR core."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from mint_oscal.ir import Finding, Subject


class SourceAdapter(Protocol):
    """Convert one untrusted source document into the neutral IR boundary."""

    def __call__(self, document: dict[str, Any]) -> tuple[list[Finding], Subject]:
        """Return findings and subject for one validated source document."""
        ...


SourceAdapterFn = Callable[[dict[str, Any]], tuple[list[Finding], Subject]]

__all__ = ["SourceAdapter", "SourceAdapterFn"]
