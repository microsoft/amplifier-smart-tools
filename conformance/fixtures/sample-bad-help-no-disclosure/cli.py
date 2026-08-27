#!/usr/bin/env python3
"""DEFECT: --help does not disclose which capabilities are model-backed.

Violates: help-discloses-model-backed.
Everything else is fine -- the tool loads without a provider, the deterministic
verb runs, a bad invocation is a structured error -- but --help never tells a
caller that 'summarize' is model-backed, so a caller cannot reason about cost or
determinism before invoking it.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

PROVIDER_ENV = "SAMPLE_PROVIDER_KEY"


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
    text = args.text or ""
    _emit({"result": {"chars": len(text), "words": len(text.split()), "lines": len(text.splitlines())}})
    return 0


def cmd_summarize(args: argparse.Namespace) -> int:
    if not os.environ.get(PROVIDER_ENV):
        return _emit_error("no_provider", "summarize needs a provider", f"Set {PROVIDER_ENV}.", 3)
    _emit({"result": {"summary": (args.text or "")[:40]}})
    return 0


def build_parser() -> argparse.ArgumentParser:
    # NOTE: no epilog, and no per-verb marking of which capability is model-backed.
    parser = _EnvelopeParser(prog="samplegood", description="A minimal reference smart tool.")
    sub = parser.add_subparsers(dest="verb")
    p_stats = sub.add_parser("stats", help="Count characters, words, and lines in TEXT.")
    p_stats.add_argument("--text", default=None)
    p_stats.set_defaults(func=cmd_stats)
    p_sum = sub.add_parser("summarize", help="Produce a short summary of TEXT.")
    p_sum.add_argument("--text", default=None)
    p_sum.set_defaults(func=cmd_summarize)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not getattr(args, "verb", None):
        return _emit_error("no_capability", "No capability named.", "Run 'samplegood --help'.", 2)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
