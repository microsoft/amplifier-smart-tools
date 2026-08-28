#!/usr/bin/env python3
"""DEFECT: the deterministic verb hangs even with stdin closed.

Violates: no-hang-stdin-closed (and, because the hang is on the deterministic
smoke path, deterministic-capability-runs times out too).
--help and bad invocations return promptly, but 'stats' enters an interactive
wait loop that ignores EOF, so a non-interactive caller with stdin closed hangs
forever. The kit's bounded timeout is what catches it.
"""

from __future__ import annotations

import argparse
import json
import sys
import time


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
    # THE DEFECT: waits for interactive input that will never come, ignoring the
    # closed-stdin EOF. A well-behaved tool would read args, not block here.
    sys.stdin.readline()  # returns "" immediately on closed stdin ...
    while True:  # ... and then we hang anyway, ignoring EOF.
        time.sleep(1)


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
