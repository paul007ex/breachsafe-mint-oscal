# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Validate the repository's required agent/process contract."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    """Return non-zero when required policy/process markers are absent."""
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    required_claude = ("AGENTS.md", "Review and merge discipline", "Verification")
    required_agents = (
        "CLAUDE.md",
        "## Ten-step loop",
        "## Fast gates",
        "## Handoff",
        "NOT RUN",
        "breachsafe-quality-review",
        "breachsafe-oscal-conformance",
        "breachsafe-release",
    )
    missing = [f"CLAUDE.md: {marker}" for marker in required_claude if marker not in claude]
    missing.extend(f"AGENTS.md: {marker}" for marker in required_agents if marker not in agents)
    if missing:
        print("process contract invalid:")
        print("\n".join(f"- {item}" for item in missing))
        return 1
    print("process contract valid: CLAUDE.md, AGENTS.md, ten-step loop, skills, and NOT RUN rule")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
