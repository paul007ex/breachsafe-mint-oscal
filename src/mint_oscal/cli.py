# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""CLI: turn a security-tool report into an OSCAL document.

NIST ``oscal-cli``-aligned shape -- the OSCAL model is the first token, the verb
second::

    mint-oscal poam generate --from qureddy scan.json
    cat scan.json | mint-oscal poam generate --from cbom -

Source is selected explicitly (``--from``); adapters (prowler, ocsf, ...) register
through the ``mint_oscal.adapters`` entry-point group without touching the CLI.
Source and extension are orthogonal (ADR-0008): ``--from`` picks a vendor-neutral
adapter, while the repeatable ``--extension`` runs opt-in enrichers (e.g. ``breachsafe``)
on the derived IR — registered through the ``mint_oscal.extensions`` entry-point group.

The CLI is the only boundary that logs and exits: it reads input (a file path, or
STDIN when the report argument is ``-``), configures structured logging to STDERR so
STDOUT stays a pure OSCAL data channel, and converts the domain errors raised by the
pure core into clean one-line diagnostics plus a non-zero exit code -- never a
traceback.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mint_oscal import convert
from mint_oscal.adapters import available_adapters, get_adapter
from mint_oscal.emitters import available_models
from mint_oscal.extensions import apply_extensions, available_extensions
from mint_oscal.ir import IR
from mint_oscal.logging import configure_logging, get_logger
from mint_oscal.render import render
from mint_oscal.validate import oscal_cli_available, semantic_errors

# Human-facing display names for a source id (used in the POA&M title); falls back to the
# raw source so a newly registered adapter still reads sensibly without a code change here.
_SOURCE_DISPLAY = {"cbom": "CBOM", "qureddy": "QuReddy"}


def _build_parser() -> argparse.ArgumentParser:
    """Build the ``mint-oscal <model> generate ...`` argument parser."""
    parser = argparse.ArgumentParser(prog="mint-oscal")
    models = parser.add_subparsers(dest="model", required=True)
    sources = sorted(available_adapters())
    extensions = sorted(available_extensions())
    for model in available_models():
        model_parser = models.add_parser(model, help=f"OSCAL {model}")
        verbs = model_parser.add_subparsers(dest="verb", required=True)
        generate = verbs.add_parser("generate", help=f"generate an OSCAL {model}")
        generate.add_argument("--from", dest="source", choices=sources, required=True)
        generate.add_argument(
            "--extension",
            dest="extensions",
            action="append",
            default=[],
            choices=extensions,
            metavar="NAME",
            help=(
                "run an opt-in enricher on the IR after the source adapter; repeatable "
                "(e.g. --extension breachsafe). Source and extension are orthogonal: "
                "--from stays vendor-neutral, --extension adds producer cross-checks"
            ),
        )
        generate.add_argument(
            "report",
            help="path to the source report JSON, or '-' to read it from STDIN",
        )
        generate.add_argument(
            "--to",
            dest="fmt",
            default="json",
            type=str.lower,
            choices=("json", "xml", "yaml"),
            metavar="FORMAT",
            help="output encoding: JSON|XML|YAML (default JSON; xml/yaml require oscal-cli)",
        )
        generate.add_argument("--validate", action="store_true", help="check internal integrity")
        generate.add_argument(
            "-v",
            "--verbose",
            dest="verbose",
            action="count",
            default=0,
            help="increase log verbosity (-v INFO, -vv DEBUG); logs go to STDERR",
        )
        generate.add_argument(
            "-q",
            "--quiet",
            dest="quiet",
            action="store_true",
            help="suppress warnings and below (only errors are logged)",
        )
        generate.add_argument(
            "--json-logs",
            dest="json_logs",
            action="store_true",
            help="emit logs as newline-delimited JSON instead of console text",
        )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point: read a source report, emit an OSCAL document to STDOUT.

    STDOUT carries only the minted OSCAL document; all diagnostics go to STDERR via
    structured logging. Domain errors from the pure core are mapped to non-zero exit
    codes without leaking a traceback: input/OS errors and malformed/garbage input
    exit ``2``; not-yet-implemented paths (stub emitters, XML/YAML render) exit ``3``.
    """
    args = _build_parser().parse_args(argv)
    configure_logging(verbosity=args.verbose, json_logs=args.json_logs, quiet=args.quiet)
    log = get_logger("mint_oscal.cli")

    try:
        raw = (
            sys.stdin.read()
            if args.report == "-"
            else Path(args.report).read_text(encoding="utf-8")
        )
        document = json.loads(raw)
        try:
            adapter = get_adapter(args.source)
        except KeyError:
            log.error("unknown_source", source=args.source)
            return 2
        try:
            findings, subject = adapter(document)
            # Extensions are orthogonal to the source (ADR-0008): the adapter yields the
            # vendor-neutral IR, then each opt-in enricher refines it from producer facts in
            # the same document. An enricher fault surfaces through this boundary as a clean
            # non-zero, never a traceback.
            findings, subject = apply_extensions(
                findings, subject, args.extensions, document=document
            )
        except Exception as exc:  # any adapter: unshaped/malformed input, surfaced not leaked
            log.error("malformed_input", source=args.source, error=str(exc))
            return 2
        ir = IR(findings=tuple(findings), subject=subject, source=args.source)
        oscal = convert(ir, shape=args.model, source=_SOURCE_DISPLAY.get(args.source, args.source))

        if args.validate:
            problems = semantic_errors(oscal)
            if problems:
                for problem in problems:
                    log.error("semantic_error", problem=problem)
                return 1
            oracle = oscal_cli_available()
            note = (
                f"authoritative NIST check available: {oracle} validate"
                if oracle
                else "run NIST oscal-cli for authoritative schema conformance"
            )
            log.info(
                "semantic_checks_passed",
                scope="uuid/ref/ns integrity -- NOT NIST schema validation",
                note=note,
            )

        sys.stdout.write(render(oscal, fmt=args.fmt))
        sys.stdout.write("\n")
        return 0
    except (FileNotFoundError, OSError) as exc:
        log.error("input_error", report=args.report, error=str(exc))
        return 2
    except json.JSONDecodeError as exc:
        log.error("invalid_json", report=args.report, error=str(exc))
        return 2
    except KeyError as exc:
        log.error("unknown_selector", model=args.model, error=str(exc))
        return 2
    except NotImplementedError as exc:
        log.error("not_implemented", model=args.model, fmt=args.fmt, error=str(exc))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
