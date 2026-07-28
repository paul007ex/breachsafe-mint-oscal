# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: Apache-2.0
"""CLI: turn a security-tool report into an OSCAL document.

NIST ``oscal-cli``-aligned shape -- the OSCAL model is the first token, the verb
second::

    mint-oscal poam generate --from qureddy scan.json

Source is selected explicitly (``--from``); adapters (prowler, ocsf, ...) register
through the ``mint_oscal.adapters`` entry-point group without touching the CLI.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mint_oscal import convert
from mint_oscal.adapters import available_adapters, get_adapter
from mint_oscal.emitters import available_models
from mint_oscal.ir import IR
from mint_oscal.render import render
from mint_oscal.validate import structural_errors


def _build_parser() -> argparse.ArgumentParser:
    """Build the ``mint-oscal <model> generate ...`` argument parser."""
    parser = argparse.ArgumentParser(prog="mint-oscal")
    models = parser.add_subparsers(dest="model", required=True)
    sources = sorted(available_adapters())
    for model in available_models():
        model_parser = models.add_parser(model, help=f"OSCAL {model}")
        verbs = model_parser.add_subparsers(dest="verb", required=True)
        generate = verbs.add_parser("generate", help=f"generate an OSCAL {model}")
        generate.add_argument("--from", dest="source", choices=sources, required=True)
        generate.add_argument("report", help="path to the source report JSON")
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
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point: read a source report, emit an OSCAL document to stdout."""
    args = _build_parser().parse_args(argv)

    document = json.loads(Path(args.report).read_text(encoding="utf-8"))
    findings, subject = get_adapter(args.source)(document)
    ir = IR(findings=tuple(findings), subject=subject, source=args.source)
    oscal = convert(ir, shape=args.model, source=args.source.capitalize())

    if args.validate:
        problems = structural_errors(oscal)
        if problems:
            for problem in problems:
                print(f"structural error: {problem}", file=sys.stderr)  # noqa: T201
            return 1
        print("structural validation: OK", file=sys.stderr)  # noqa: T201

    sys.stdout.write(render(oscal, fmt=args.fmt))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
