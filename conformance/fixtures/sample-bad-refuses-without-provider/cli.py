#!/usr/bin/env python3
"""DEFECT: refuses to load without a model provider.

Violates: loads-without-provider.
structure.md requires the straight code paths to run with no provider
configured; this tool demands one at import time, so it will not even load to
print --help. (A load refusal cascades: the deterministic and failure-shape
checks cannot pass either, because nothing can run.)
"""

from __future__ import annotations

import argparse
import json
import os
import sys

PROVIDER_ENV = "SAMPLE_PROVIDER_KEY"

# THE DEFECT: mandatory provider at load time.
if not os.environ.get(PROVIDER_ENV):
    sys.stderr.write(
        f"fatal: {PROVIDER_ENV} is not set; this tool refuses to load without a provider\n"
    )
    raise SystemExit(1)

MODEL_BACKED_VERBS = ("summarize",)


def _emit(document: dict) -> None:
    json.dump(document, sys.stdout, sort_keys=True)
    sys.stdout.write("\n")


def cmd_stats(args: argparse.Namespace) -> int:
    text = args.text or ""
    _emit({"result": {"chars": len(text), "words": len(text.split()), "lines": len(text.splitlines())}})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="samplegood", epilog="Model-backed capabilities: summarize.")
    sub = parser.add_subparsers(dest="verb")
    p = sub.add_parser("stats", help="[deterministic] count text")
    p.add_argument("--text", default=None)
    p.set_defaults(func=cmd_stats)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not getattr(args, "verb", None):
        _emit({"error": {"code": "no_capability", "message": "no verb", "remedy": "see --help"}})
        return 2
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
