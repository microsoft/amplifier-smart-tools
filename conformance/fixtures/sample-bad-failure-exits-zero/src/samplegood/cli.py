#!/usr/bin/env python3
"""DEFECT: a bad invocation reports an error but exits 0.

Violates: failure-exits-non-zero.
The tool loads fine, answers both -h and --help, discloses its model-backed
capability, and runs its deterministic verb -- but an unrecognised verb prints
an error and returns 0. The error is hidden from every script, pipeline, and
agent harness, all of which check the exit code and see success.
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
    handler = _DISPATCH.get(args.verb)
    if handler is None:
        # THE DEFECT: the error is described in the output but the process exits 0.
        _emit(
            {
                "error": {
                    "code": "unknown_capability",
                    "message": f"no such capability: {args.verb}",
                    "remedy": "Run 'samplegood --help' to see the available capabilities.",
                }
            }
        )
        return 0
    return handler(args.text)


if __name__ == "__main__":
    raise SystemExit(main())
