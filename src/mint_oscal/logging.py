# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Structured logging for the CLI boundary (#11).

Logs go to STDERR via ``structlog`` so that STDOUT stays a pure OSCAL data channel
(a minted document can be piped straight into another tool). This module is imported
only by the CLI: the agnostic core (adapters, emitters, render) never logs, prints,
or exits -- they raise domain errors and the CLI decides how to surface them.

Rendering honors the terminal: a human-readable, colorized console renderer when
STDERR is a TTY (and ``NO_COLOR`` is unset), a machine-readable JSON renderer when
``--json-logs`` is requested. Timestamps are ISO-8601 UTC.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, TextIO

import structlog
from structlog.typing import FilteringBoundLogger

# Public alias for the bound logger type get_logger returns, so callers annotate against
# mint_oscal.logging instead of reaching into structlog's typing module.
BoundLog = FilteringBoundLogger


def configure_logging(
    *,
    verbosity: int = 0,
    json_logs: bool = False,
    quiet: bool = False,
    stream: TextIO | None = None,
) -> None:
    """Configure ``structlog`` to emit to STDERR (keeping STDOUT pure).

    Args:
        verbosity: ``-v`` count; 0 -> WARNING, 1 -> INFO, 2+ -> DEBUG.
        json_logs: emit newline-delimited JSON instead of the console renderer.
        quiet: raise the threshold to ERROR, suppressing warnings and below.
        stream: sink for log lines; defaults to ``sys.stderr``. Injectable for tests.
    """
    if quiet:
        level = logging.ERROR
    else:
        level = (logging.WARNING, logging.INFO, logging.DEBUG)[min(verbosity, 2)]
    out: TextIO = stream or sys.stderr
    procs: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]
    if json_logs:
        procs.append(structlog.processors.JSONRenderer())
    else:
        color = getattr(out, "isatty", bool)() and "NO_COLOR" not in os.environ
        procs.append(structlog.dev.ConsoleRenderer(colors=color))
    structlog.configure(
        processors=procs,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=out),
        cache_logger_on_first_use=False,
    )


def get_logger(name: str) -> FilteringBoundLogger:
    """Return a bound structlog logger for ``name`` (e.g. ``"mint_oscal.cli"``)."""
    logger: FilteringBoundLogger = structlog.get_logger(name)
    return logger
