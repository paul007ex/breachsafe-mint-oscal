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
from mint_oscal._branding import (
    DESCRIPTION,
    PROJECT_NAME,
    PROJECT_URL,
    PROJECT_VERSION,
    VERSION_BANNER,
)
from mint_oscal._help import colorize_help
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

# Human-facing OSCAL-model blurbs and the set of stub emitters (they raise
# NotImplementedError), so `--help` can label planned models honestly. Falls back to the
# raw model name for a model registered without a blurb here.
_MODEL_BLURB = {
    "poam": "POA&M (Plan of Action & Milestones)",
    "ar": "Assessment Results",
    "component-definition": "Component Definition",
}
_PLANNED_MODELS = {"ar", "component-definition"}


def _root_epilog() -> str:
    """Brand epilog for `mint-oscal --help`: quick start + where to go next."""
    return colorize_help(
        "QUICK START:\n\n"
        "# CBOM on disk -> OSCAL POA&M (JSON on stdout).\n"
        "mint-oscal poam generate --from cbom scan.cbom.json\n\n"
        "# Pipe a QuReddy scan straight through (the flagship pipe).\n"
        "qureddy scan tls example.com --format cbom | mint-oscal poam generate --from cbom -\n\n"
        "# Add the BreachSAFE producer cross-check, then validate.\n"
        "mint-oscal poam generate --from cbom scan.cbom.json --extension breachsafe --validate\n\n"
        "MORE HELP:\n\n"
        "mint-oscal <model> generate --help   # full options, examples, exit codes\n"
        "mint-oscal --version                 # show version\n\n"
        f"Project: {PROJECT_URL}"
    )


def _generate_epilog() -> str:
    """Brand epilog for `mint-oscal <model> generate --help`: examples, exit codes, environment."""
    return colorize_help(
        "EXAMPLES:\n\n"
        "# Most common: a CBOM file -> POA&M JSON.\n"
        "mint-oscal poam generate --from cbom scan.cbom.json\n\n"
        "# Read the report from STDIN.\n"
        "qureddy scan tls example.com --format cbom | mint-oscal poam generate --from cbom -\n\n"
        "# Producer cross-check + semantic validation.\n"
        "mint-oscal poam generate --from cbom scan.cbom.json --extension breachsafe --validate\n\n"
        "# XML output (requires oscal-cli on PATH).\n"
        "mint-oscal poam generate --from cbom scan.cbom.json --to xml\n\n"
        "EXIT CODES:\n\n"
        "0   OSCAL document minted\n"
        "1   --validate found a semantic problem\n"
        "2   input error, or malformed / unrecognized source report\n"
        "3   requested output needs a local dependency (oscal-cli for xml/yaml)\n\n"
        "ENVIRONMENT:\n\n"
        "NO_COLOR   Disable ANSI color in --help (https://no-color.org).\n\n"
        f"Project: {PROJECT_URL}"
    )


def _build_parser() -> tuple[argparse.ArgumentParser, dict[str, argparse.ArgumentParser]]:
    """Build the parser, returning it plus the per-model subparsers (for no-verb help).

    Subparsers are ``required=False`` so a bare ``mint-oscal`` or ``mint-oscal <model>``
    prints help (exit 0) instead of erroring; :func:`main` dispatches the missing levels.
    """
    parser = argparse.ArgumentParser(
        prog="mint-oscal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=f"{PROJECT_NAME} {PROJECT_VERSION} -- {DESCRIPTION}.",
        epilog=_root_epilog(),
    )
    parser.add_argument("-V", "--version", action="version", version=VERSION_BANNER)
    models = parser.add_subparsers(dest="model", required=False, metavar="<model>")
    sources = sorted(available_adapters())
    extensions = sorted(available_extensions())
    model_parsers: dict[str, argparse.ArgumentParser] = {}
    for model in available_models():
        blurb = _MODEL_BLURB.get(model, model)
        planned = model in _PLANNED_MODELS
        note = "  (planned; not yet implemented)" if planned else ""
        model_parser = models.add_parser(
            model,
            help=f"generate an OSCAL {blurb}" + (" (planned)" if planned else ""),
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description=f"Generate an OSCAL {blurb} from a source report.{note}",
        )
        model_parsers[model] = model_parser
        verbs = model_parser.add_subparsers(dest="verb", required=False, metavar="<verb>")
        generate = verbs.add_parser(
            "generate",
            help=f"generate an OSCAL {blurb}",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description=f"Generate an OSCAL {blurb} from a source report.{note}",
            epilog=_generate_epilog(),
        )
        generate.add_argument(
            "report",
            help="path to the source report JSON, or '-' to read it from STDIN",
        )
        generate.add_argument(
            "--from",
            dest="source",
            choices=sources,
            required=True,
            metavar="SOURCE",
            help=f"source adapter to parse the report: {', '.join(sources)}",
        )
        generate.add_argument(
            "--extension",
            dest="extensions",
            action="append",
            default=[],
            choices=extensions,
            metavar="NAME",
            help=(
                "opt-in IR enricher, repeatable (e.g. breachsafe). Orthogonal to --from, "
                "which stays vendor-neutral; adds producer cross-checks"
            ),
        )
        generate.add_argument(
            "--to",
            dest="fmt",
            default="json",
            type=str.lower,
            choices=("json", "xml", "yaml"),
            metavar="FORMAT",
            help="output encoding: json (default), xml, yaml (xml/yaml require oscal-cli)",
        )
        generate.add_argument(
            "--validate",
            action="store_true",
            help=(
                "run in-process Layer-2 semantic checks (uuid/ref/ns integrity, OSCAL "
                "structural + BreachSAFE domain vocab). Not authoritative NIST schema "
                "validation; run oscal-cli for that. Exit 1 on any problem"
            ),
        )
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
    return parser, model_parsers


def main(argv: list[str] | None = None) -> int:
    """Entry point: read a source report, emit an OSCAL document to STDOUT.

    STDOUT carries only the minted OSCAL document; all diagnostics go to STDERR via
    structured logging. Domain errors from the pure core are mapped to non-zero exit
    codes without leaking a traceback: input/OS errors and malformed/garbage input
    exit ``2``; not-yet-implemented paths (stub emitters, XML/YAML render) exit ``3``.
    """
    if argv is None:
        argv = sys.argv[1:]
    parser, model_parsers = _build_parser()
    # No arguments, an incomplete invocation (a model with no verb), or the bare `help`
    # word all print the relevant help to STDOUT and exit 0 -- running the tool with nothing
    # to do shows what it can do; it is not treated as an error.
    if not argv or argv[0] == "help":
        parser.print_help()
        return 0
    args = parser.parse_args(argv)
    if args.model is None:
        parser.print_help()
        return 0
    if getattr(args, "verb", None) is None:
        model_parsers[args.model].print_help()
        return 0
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
        # Surfaced at -v (INFO); STDOUT stays a pure OSCAL channel. Gives `-v/-vv` real output
        # (a run summary + the applied extensions) instead of leaving the flags as no-ops.
        log.info(
            "minted_document",
            model=args.model,
            source=args.source,
            subject=subject.id,
            findings=len(ir.findings),
            extensions=args.extensions,
        )

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
            # --validate is an explicit request, so its result must be visible at the
            # default level (WARNING) -- not INFO, which is suppressed -- so the user
            # actually sees the outcome AND the "not authoritative" caveat. `-q` still
            # silences it (it raises the floor to ERROR).
            log.warning(
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
