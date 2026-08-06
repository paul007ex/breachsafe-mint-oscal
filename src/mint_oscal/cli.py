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
from typing import NoReturn

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
from mint_oscal.logging import BoundLog, configure_logging, get_logger
from mint_oscal.policy import FRAMEWORK_PACKS, set_active_framework
from mint_oscal.render import render
from mint_oscal.validate import oscal_cli_available, semantic_errors

# Exit-code surface (documented in the --help EXIT CODES section). Distinct codes let a caller
# tell a usage mistake (4), bad input (2), a missing local dependency (3), and an internal fault
# (70, BSD sysexits.h EX_SOFTWARE) apart instead of lumping them together.
_EXIT_OK = 0
_EXIT_VALIDATION = 1
_EXIT_INPUT = 2
_EXIT_NOT_IMPLEMENTED = 3
_EXIT_USAGE = 4
_EXIT_INTERNAL = 70


class _UsageParser(argparse.ArgumentParser):
    """ArgumentParser that exits with the usage code (4), distinct from malformed input (2).

    argparse's default ``error()`` exits ``2`` -- the same code mint uses for a malformed
    source report -- so "you invoked the CLI wrong" (a bad ``--from`` choice, a missing
    argument, an unknown flag) would be indistinguishable from "your file was bad". Overriding
    it separates the two. Logging is not configured this early in ``main``, so the diagnostic
    goes straight to STDERR (STDOUT stays a pure OSCAL channel). ``add_subparsers`` defaults its
    ``parser_class`` to ``type(self)``, so every subparser inherits this behavior.
    """

    def error(self, message: str) -> NoReturn:
        """Print usage + a one-line diagnostic to STDERR and exit with the usage code (4)."""
        self.print_usage(sys.stderr)
        self.exit(_EXIT_USAGE, f"{self.prog}: usage error: {message}\n")


# Human-facing display names for a source id (used in the POA&M title); falls back to the
# raw source so a newly registered adapter still reads sensibly without a code change here.
_SOURCE_DISPLAY = {"cbom": "CBOM", "qureddy": "QuReddy"}

# Human-facing OSCAL-model blurbs and the set of stub emitters (they raise
# NotImplementedError), so `--help` can label planned models honestly. Falls back to the
# raw model name for a model registered without a blurb here.
_MODEL_BLURB = {
    "poam": "POA&M (Plan of Action & Milestones)",
    "ar": "Assessment Results",
}
_PLANNED_MODELS = {"ar"}
# Models that have a native Layer-2 validator (a `validate` verb); POA&M is the only one today.
_VALIDATABLE_MODELS = {"poam"}


def _root_epilog() -> str:
    """Brand epilog for `mint-oscal --help`: quick start + where to go next."""
    return colorize_help(
        "QUICK START:\n\n"
        "# CBOM on disk -> OSCAL POA&M (JSON on stdout).\n"
        "mint-oscal poam generate --from cbom scan.cbom.json\n\n"
        "# Pipe a QuReddy scan straight through (the flagship pipe).\n"
        "qureddy scan tls example.com --format cbom | mint-oscal poam generate --from cbom -\n\n"
        "# Validate an existing POA&M (yours or another tool's) -- no oscal-cli / trestle needed.\n"
        "mint-oscal poam validate their-poam.json\n\n"
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
        "0    OSCAL document minted\n"
        "1    --validate found a semantic problem\n"
        "2    input error, or malformed / unrecognized source report\n"
        "3    requested output needs a local dependency (oscal-cli for xml/yaml)\n"
        "4    usage error (bad flag / argument / choice)\n"
        "70   internal error (mint-oscal itself failed; not your input)\n\n"
        "ENVIRONMENT:\n\n"
        "NO_COLOR   Disable ANSI color in --help (https://no-color.org).\n\n"
        f"Project: {PROJECT_URL}"
    )


def _validate_epilog() -> str:
    """Brand epilog for `mint-oscal poam validate --help`: examples, exit codes, the caveat."""
    return colorize_help(
        "EXAMPLES:\n\n"
        "# Validate a POA&M someone else produced -- no oscal-cli or trestle needed.\n"
        "mint-oscal poam validate their-poam.json\n\n"
        "# Validate mint's own output in a pipeline.\n"
        "mint-oscal poam generate --from cbom scan.cbom.json | mint-oscal poam validate -\n\n"
        "EXIT CODES:\n\n"
        "0    valid: no semantic problems found\n"
        "1    invalid: one or more semantic problems (reported on STDERR)\n"
        "2    input error: not valid JSON, or not a POA&M document\n\n"
        "NOTE:\n\n"
        "Pure-Python Layer-2 semantic checks (uuid/ref/ns integrity + OSCAL structural +\n"
        "datatypes + BreachSAFE domain vocab). No oscal-cli or trestle required. Necessary but\n"
        "NOT sufficient for full NIST schema conformance; run oscal-cli for that.\n\n"
        f"Project: {PROJECT_URL}"
    )


def _add_logging_args(parser: argparse.ArgumentParser) -> None:
    """Add the shared -v/-q/--json-logs logging flags (STDERR only) to a verb parser."""
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        action="count",
        default=0,
        help="increase log verbosity (-v INFO, -vv DEBUG); logs go to STDERR",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        dest="quiet",
        action="store_true",
        help="suppress warnings and below (only errors are logged)",
    )
    parser.add_argument(
        "--json-logs",
        dest="json_logs",
        action="store_true",
        help="emit logs as newline-delimited JSON instead of console text",
    )


def _read_source(path: str) -> str:
    """Read the input document from a file path, or from STDIN when ``path`` is ``-``."""
    return sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")


def _build_parser() -> tuple[argparse.ArgumentParser, dict[str, argparse.ArgumentParser]]:
    """Build the parser, returning it plus the per-model subparsers (for no-verb help).

    Subparsers are ``required=False`` so a bare ``mint-oscal`` or ``mint-oscal <model>``
    prints help (exit 0) instead of erroring; :func:`main` dispatches the missing levels.
    """
    parser = _UsageParser(
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
            "--framework",
            dest="framework",
            choices=sorted(FRAMEWORK_PACKS),
            default="scf-qts",
            metavar="FRAMEWORK",
            help=(
                "control framework to map findings to: scf-qts (default, PQC-native SCF "
                "Quantum Security controls) or nist (NIST SP 800-53r5 SC-13/SC-12)"
            ),
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
        _add_logging_args(generate)

        # A `validate` verb for models that have a native Layer-2 validator (POA&M today):
        # take in an *existing* OSCAL document and check it -- pure Python, no oscal-cli/trestle.
        if model in _VALIDATABLE_MODELS:
            validate = verbs.add_parser(
                "validate",
                help=f"validate an existing OSCAL {blurb}",
                formatter_class=argparse.RawDescriptionHelpFormatter,
                description=(
                    f"Validate an existing OSCAL {blurb} document with pure-Python Layer-2 "
                    "semantic checks (uuid/ref/ns integrity, OSCAL structural + datatypes, "
                    "BreachSAFE domain vocab). No oscal-cli or trestle required; necessary but "
                    "not sufficient for full NIST schema conformance. Exit 1 on any problem."
                ),
                epilog=_validate_epilog(),
            )
            validate.add_argument(
                "document",
                help=f"path to the OSCAL {blurb} JSON to validate, or '-' to read it from STDIN",
            )
            _add_logging_args(validate)
    return parser, model_parsers


def _run(args: argparse.Namespace, log: BoundLog) -> int:
    """Read the source report, mint the OSCAL document to STDOUT, and return an exit code.

    The pipeline proper; :func:`main` owns the top-level error-to-exit-code mapping. STDOUT
    carries only the minted OSCAL document.
    """
    # Select the control framework for this run (scf-qts default) before any crosswalk lookup.
    set_active_framework(args.framework)
    document = json.loads(_read_source(args.report))
    try:
        adapter = get_adapter(args.source)
    except KeyError:
        log.error("unknown_source", source=args.source)
        return _EXIT_INPUT
    try:
        findings, subject = adapter(document)
        # Extensions are orthogonal to the source (ADR-0008): the adapter yields the
        # vendor-neutral IR, then each opt-in enricher refines it from producer facts in the
        # same document.
        findings, subject = apply_extensions(findings, subject, args.extensions, document=document)
    except ValueError as exc:
        # Adapters raise a typed domain error (MalformedCbomError/MalformedScanError, both
        # ValueError subclasses) for malformed/unshaped input -> clean exit 2. A non-ValueError
        # escaping here is an internal fault, NOT bad input, so it deliberately propagates to
        # main's internal-error boundary (exit 70) instead of being mislabeled malformed (#70).
        log.error("malformed_input", source=args.source, error=str(exc))
        return _EXIT_INPUT
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
            return _EXIT_VALIDATION
        oracle = oscal_cli_available()
        note = (
            f"authoritative NIST check available: {oracle} validate"
            if oracle
            else "run NIST oscal-cli for authoritative schema conformance"
        )
        # --validate is an explicit request, so its result must be visible at the default level
        # (WARNING) -- not INFO, which is suppressed -- so the user sees the outcome AND the
        # "not authoritative" caveat. `-q` still silences it (it raises the floor to ERROR).
        log.warning(
            "semantic_checks_passed",
            scope="uuid/ref/ns integrity -- NOT NIST schema validation",
            note=note,
        )

    sys.stdout.write(render(oscal, fmt=args.fmt))
    sys.stdout.write("\n")
    return _EXIT_OK


def _validate(args: argparse.Namespace, log: BoundLog) -> int:
    """Validate an existing OSCAL POA&M document (Layer-2 semantic checks); return an exit code.

    The standalone validator: it takes in a document the caller already has (their own, or
    another tool's output) rather than re-checking what mint just minted. Pure Python -- no
    oscal-cli or trestle needed. Exit 1 if any problem, 0 if clean. STDOUT is left empty; the
    verdict and any problems go to STDERR so the exit code is the machine signal.
    """
    document = json.loads(_read_source(args.document))
    # A document that is not a POA&M at all (no plan-of-action-and-milestones root) is the wrong
    # *input*, not a POA&M with a semantic problem -- report it as an input error (exit 2), the
    # same code `generate` uses for bad input, rather than a validation failure (exit 1) (#72).
    if not isinstance(document, dict) or not isinstance(
        document.get("plan-of-action-and-milestones"), dict
    ):
        log.error("not_a_poam", document=args.document)
        return _EXIT_INPUT
    scope = "uuid/ref/ns + OSCAL structural + BreachSAFE domain -- NOT NIST schema validation"
    problems = semantic_errors(document)
    if problems:
        for problem in problems:
            log.error("semantic_error", problem=problem)
        log.warning("invalid", document=args.document, problems=len(problems), scope=scope)
        return _EXIT_VALIDATION
    oracle = oscal_cli_available()
    note = (
        f"authoritative NIST check available: {oracle} validate"
        if oracle
        else "run NIST oscal-cli for authoritative NIST schema conformance"
    )
    log.warning("valid", document=args.document, scope=scope, note=note)
    return _EXIT_OK


def main(argv: list[str] | None = None) -> int:  # noqa: PLR0911 -- error boundary: N domain errors -> exit codes
    """Entry point: read a source report, emit an OSCAL document to STDOUT.

    STDOUT carries only the minted OSCAL document; all diagnostics go to STDERR via
    structured logging. This function is the error boundary: it maps the domain errors the
    pure core raises to distinct exit codes and log events without leaking a traceback --
    input/OS errors and malformed/garbage input exit ``2``; not-yet-implemented paths (stub
    emitters, XML/YAML render) exit ``3``; a usage mistake (bad flag/argument/choice, caught by
    :class:`_UsageParser`) exits ``4``; and any unexpected internal fault exits ``70`` (never
    mislabeled as input). The actual pipeline lives in :func:`_run`.
    """
    if argv is None:
        argv = sys.argv[1:]
    parser, model_parsers = _build_parser()
    # No arguments, an incomplete invocation (a model with no verb), or the bare `help`
    # word all print the relevant help to STDOUT and exit 0 -- running the tool with nothing
    # to do shows what it can do; it is not treated as an error.
    # An explicit help request (the bare `help` word; `--help`/`-h` are handled by argparse
    # itself) prints to STDOUT and exits 0 -- it is the output the user asked for.
    if argv and argv[0] == "help":
        parser.print_help()
        return _EXIT_OK
    # An incomplete invocation (no command, or a model with no verb) is not a data-producing
    # run: its help goes to STDERR so STDOUT stays a pure OSCAL channel (#70), and it still
    # exits 0 -- running the tool with nothing to do shows what it can do, it is not an error.
    if not argv:
        parser.print_help(sys.stderr)
        return _EXIT_OK
    args = parser.parse_args(argv)
    if args.model is None:
        parser.print_help(sys.stderr)
        return _EXIT_OK
    if getattr(args, "verb", None) is None:
        model_parsers[args.model].print_help(sys.stderr)
        return _EXIT_OK
    configure_logging(verbosity=args.verbose, json_logs=args.json_logs, quiet=args.quiet)
    log = get_logger("mint_oscal.cli")

    # The input path is `report` for generate, `document` for validate; use whichever exists so
    # the error handlers work for both verbs (a hardcoded `args.report` would AttributeError in
    # the handler on the validate path and leak a traceback).
    src = getattr(args, "report", None) or getattr(args, "document", "-")
    try:
        return _validate(args, log) if args.verb == "validate" else _run(args, log)
    except (FileNotFoundError, OSError) as exc:
        log.error("input_error", report=src, error=str(exc))
        return _EXIT_INPUT
    except json.JSONDecodeError as exc:
        log.error("invalid_json", report=src, error=str(exc))
        return _EXIT_INPUT
    except UnicodeDecodeError as exc:
        # A non-UTF-8 (binary) input is bad *input*, not a mint fault: map the decode failure to
        # malformed_input (exit 2), not the top-level internal_error (exit 70) it would otherwise
        # reach as a non-JSONDecodeError ValueError (#121).
        log.error("invalid_encoding", report=src, error=str(exc))
        return _EXIT_INPUT
    except NotImplementedError as exc:
        log.error(
            "not_implemented", model=args.model, fmt=getattr(args, "fmt", None), error=str(exc)
        )
        return _EXIT_NOT_IMPLEMENTED
    except Exception as exc:  # noqa: BLE001 -- top-level internal-error boundary
        # Any unexpected fault is mint's own bug, not the user's input: report it honestly as an
        # internal error with a distinct exit code (70, EX_SOFTWARE), never a leaked traceback,
        # and never mislabeled as malformed input (#70).
        log.error("internal_error", error=str(exc), error_type=type(exc).__name__)
        return _EXIT_INTERNAL


if __name__ == "__main__":
    raise SystemExit(main())
