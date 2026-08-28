#!/usr/bin/env python3
"""DEFECT: the deterministic verb demands a model provider.

Violates: deterministic-capability-runs.
The tool loads and --help works, but 'stats' -- which is pure counting and
should be deterministic -- refuses to run without a provider configured. A
caller that only wants the deterministic capability is wrongly forced to supply
model credentials.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

PROVIDER_ENV = "SAMPLE_PROVIDER_KEY"
MODEL_BACKED_VERBS = ("summarize",)


def _emit(document: dict) -> None:
    json.dump(document, sys.stdout, sort_keys=True)
    sys.stdout.write("\n")


def _emit_error(code: str, message: str, remedy: str, exit_code: int) -> int:
    _emit({"error": {"code": code, "message": message, "remedy": remedy}})
    return exit_code


class _EnvelopeParser(argparse.ArgumentParser):
    def error(self, message: str):
        _emit_error("bad_invocation", message, "Run 'samplegood --help'.", 2)
        raise SystemExit(2)


def cmd_stats(args: argparse.Namespace) -> int:
    # THE DEFECT: a deterministic verb demanding a provider.
    if not os.environ.get(PROVIDER_ENV):
        return _emit_error(
            "no_provider",
            "stats requires a model provider to be configured.",
            f"Set {PROVIDER_ENV}.",
            3,
        )
    text = args.text or ""
    _emit({"result": {"chars": len(text), "words": len(text.split()), "lines": len(text.splitlines())}})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = _EnvelopeParser(prog="samplegood", epilog="Model-backed capabilities: summarize.")
    sub = parser.add_subparsers(dest="verb")
    p = sub.add_parser("stats", help="[deterministic] count text")
    p.add_argument("--text", default=None)
    p.set_defaults(func=cmd_stats)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not getattr(args, "verb", None):
        return _emit_error("no_capability", "No capability named.", "Run 'samplegood --help'.", 2)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
