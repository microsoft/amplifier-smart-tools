#!/usr/bin/env python3
"""DEFECT: a bad invocation crashes with a bare stack trace.

Violates: failure-names-remedy.
The tool loads fine, --help discloses model-backed capabilities, and the
deterministic verb runs -- but an unrecognised verb raises an uncaught
exception, handing the caller a Python traceback on stderr instead of a
structured error that names the remedy.
"""

from __future__ import annotations

import argparse
import json
import sys

MODEL_BACKED_VERBS = ("summarize",)


def _emit(document: dict) -> None:
    json.dump(document, sys.stdout, sort_keys=True)
    sys.stdout.write("\n")


def cmd_stats(text: str) -> int:
    _emit({"result": {"chars": len(text), "words": len(text.split()), "lines": len(text.splitlines())}})
    return 0


_DISPATCH = {"stats": cmd_stats}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="samplegood",
        epilog="Model-backed capabilities: summarize.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("verb", nargs="?", help="stats | summarize")
    parser.add_argument("--text", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.verb:
        _emit({"error": {"code": "no_capability", "message": "no verb", "remedy": "see --help"}})
        return 2
    # THE DEFECT: unknown verb -> KeyError, uncaught -> bare traceback + exit 1.
    handler = _DISPATCH[args.verb]
    return handler(args.text)


if __name__ == "__main__":
    raise SystemExit(main())
