# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""``--help`` epilog colorization by line shape (pattern ported from the QuReddy CLI).

Keeps the ``mint-oscal`` help output visually consistent with ``qureddy`` -- the same
brand palette, driven by one pattern-matching pass over the plain epilog text -- without
taking a dependency on the click/typer machinery QuReddy uses. Honors ``NO_COLOR``
(https://no-color.org). The palette: section headers bold cyan, ``# comments`` dim,
command lines bold green (the "type this" action), leading exit codes colored by
severity, and ENVIRONMENT variable names bold magenta.
"""

from __future__ import annotations

import os
import re

_SECTION = re.compile(r"^[A-Z][A-Z /]*:$")
_COMMENT = re.compile(r"^(\s*)(#.*)$")
_COMMAND = re.compile(r"^(\s*)((?:mint-oscal|qureddy)\b.*)$")
_EXIT_CODE = re.compile(r"^(\d+)(\s+)(.*)$")
_ENV_VAR = re.compile(r"^([A-Z][A-Z0-9_]*)(\s{2,})(.*)$")


def _style(text: str, code: str) -> str:
    """Wrap ``text`` in an ANSI SGR sequence."""
    return f"\033[{code}m{text}\033[0m"


def _exit_code_color(code: str) -> str:
    """Color an exit code by severity: 0 green, >=70 red (internal), else yellow (routine)."""
    if code == "0":
        return "32"
    if int(code) >= 70:
        return "31"
    return "33"


def colorize_help(text: str) -> str:
    """Return ``text`` colored by line shape, or unchanged when ``NO_COLOR`` is set."""
    if "NO_COLOR" in os.environ:
        return text
    out: list[str] = []
    for line in text.split("\n"):
        if _SECTION.match(line):
            out.append(_style(line, "1;36"))
        elif (m := _COMMENT.match(line)) is not None:
            out.append(m.group(1) + _style(m.group(2), "2"))
        elif (m := _COMMAND.match(line)) is not None:
            out.append(m.group(1) + _style(m.group(2), "1;32"))
        elif (m := _EXIT_CODE.match(line)) is not None:
            code, gap, rest = m.groups()
            out.append(_style(code, f"1;{_exit_code_color(code)}") + gap + rest)
        elif (m := _ENV_VAR.match(line)) is not None:
            name, gap, rest = m.groups()
            out.append(_style(name, "1;35") + gap + rest)
        else:
            out.append(line)
    return "\n".join(out)
