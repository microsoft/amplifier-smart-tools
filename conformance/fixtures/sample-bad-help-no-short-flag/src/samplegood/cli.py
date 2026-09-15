#!/usr/bin/env python3
"""DEFECT: `--help` works but `-h` is not recognised.

Violates: help-flags-supported. Everything else holds: the tool loads without a
provider, prints its skill on --help, answers `stats --help`, runs its
deterministic verb, exits non-zero on a bad invocation, and never hangs.
"""

from __future__ import annotations

import argparse
import json
import sys

SKILL = """<skill_content name="samplegood">
Skill directory: /dev/null
Relative paths in this skill are relative to the skill directory.

# samplegood

## Capabilities

- `stats` [deterministic] -- Count characters, words, and lines in TEXT. Arguments, result, and exit codes: `samplegood stats --help`.
</skill_content>"""


def _emit(document: dict) -> None:
    json.dump(document, sys.stdout, sort_keys=True)
    sys.stdout.write("\n")


def _emit_error(code: str, message: str, remedy: str, exit_code: int) -> int:
    _emit({"error": {"code": code, "message": message, "remedy": remedy}})
    return exit_code


class _SkillAction(argparse.Action):
    def __init__(self, option_strings, dest=argparse.SUPPRESS, default=argparse.SUPPRESS, help=None):
        super().__init__(option_strings=option_strings, dest=dest, default=default, nargs=0, help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        sys.stdout.write(SKILL + "\n")
        parser.exit(0)


class _EnvelopeParser(argparse.ArgumentParser):
    def error(self, message: str):
        _emit_error("bad_invocation", message, "Run 'samplegood --help'.", 2)
        raise SystemExit(2)


def cmd_stats(args: argparse.Namespace) -> int:
    text = args.text or ""
    _emit({"result": {"chars": len(text), "words": len(text.split()), "lines": len(text.splitlines())}})
    return 0


def build_parser() -> argparse.ArgumentParser:
    # THE DEFECT: only the long flag is registered, so `-h` is an unknown argument.
    parser = _EnvelopeParser(prog="samplegood", add_help=False)
    parser.add_argument("--help", action=_SkillAction)
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
