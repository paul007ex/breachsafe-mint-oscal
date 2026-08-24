# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Canonical branding constants: single source of truth for name, version, and URLs.

Mirrors the BreachSAFE QuReddy ``_branding`` module so the two tools' ``--version``
banners and ``--help`` headers stay visually consistent. The version is read from the
installed package metadata, never hardcoded, so a release bump cannot drift from the
banner (the failure this module exists to prevent).

``--`` (double hyphen) is used in the banner instead of an em-dash to match the shared
house style across the BreachSAFE CLIs.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

PROJECT_NAME = "BreachSAFE Mint-OSCAL"
PROJECT_URL = "https://www.breachsafe.io"
# One-line description, used in the CLI help header. Single source so the strings
# on the root and subcommands can't drift.
DESCRIPTION = "mint NIST OSCAL documents from security-scanner findings"

try:
    PROJECT_VERSION = version("breachsafe-mint-oscal")
except PackageNotFoundError:  # running from a source tree that was never installed
    PROJECT_VERSION = "0+unknown"

# Emitted by ``mint-oscal --version`` / ``-V``. Single line, branded.
VERSION_BANNER = f"{PROJECT_NAME} {PROJECT_VERSION} -- {PROJECT_URL}"
