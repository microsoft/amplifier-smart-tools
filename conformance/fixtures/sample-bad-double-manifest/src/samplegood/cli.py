#!/usr/bin/env python3
"""samplegood -- a minimal reference smart tool.

This is a deliberately tiny, brand-neutral smart tool used by the conformance
kit as its known-good fixture. It exists to be *passed* by every rule:

  * It is a library-first tool with a thin CLI wrapper.
  * Its deterministic verb (``stats``) runs with no model provider configured.
  * Its model-backed verb (``summarize``) fails loudly with a named remedy when
    no provider is configured -- it never silently degrades.
  * ``--help`` discloses which capabilities are model-backed.
  * A bad invocation emits a structured JSON error envelope on stdout and exits
    non-zero -- never a bare stack trace.
  * Nothing here reads stdin, so a run with stdin closed never hangs.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# The single model-backed capability. A caller is told this via ``--help`` so it
# can make cost / determinism decisions before invoking.
MODEL_BACKED_VERBS = ("summarize",)

# Env var that would carry a provider credential. Deliberately generic so the
# fixture carries no consumer-brand token.
PROVIDER_ENV = "SAMPLE_PROVIDER_KEY"


def _emit(document: dict) -> None:
    """Write exactly one JSON document to stdout, newline-terminated."""
    json.dump(document, sys.stdout, sort_keys=True)
    sys.stdout.write("\n")


def _emit_error(code: str, message: str, remedy: str, exit_code: int) -> int:
    _emit({"error": {"code": code, "message": message, "remedy": remedy}})
    return exit_code


class _EnvelopeParser(argparse.ArgumentParser):
    """argparse parser that reports bad invocations as JSON envelopes on stdout.

    The spec requires failures to be structured and to name a remedy, never a
    bare usage dump on stderr or a stack trace. So we intercept argparse's
    error path and emit the same ``{"error": {...}}`` envelope every other
    failure uses.
    """

    def error(self, message: str):  # noqa: D401 - argparse contract
        _emit_error(
            "bad_invocation",
            message,
            "Run 'samplegood --help' for the full list of capabilities and their arguments.",
            2,
        )
        raise SystemExit(2)


def cmd_stats(args: argparse.Namespace) -> int:
    """[deterministic] Count characters, words, and lines in TEXT."""
    text = args.text if args.text is not None else ""
    _emit(
        {
            "result": {
                "chars": len(text),
                "words": len(text.split()),
                "lines": len(text.splitlines()) if text else 0,
            }
        }
    )
    return 0


def cmd_summarize(args: argparse.Namespace) -> int:
    """[model-backed] Produce a short summary of TEXT.

    Model-backed: fails loudly with a remedy when no provider is configured.
    """
    if not os.environ.get(PROVIDER_ENV):
        return _emit_error(
            "no_provider",
            "The 'summarize' capability is model-backed and no model provider is configured.",
            f"Set {PROVIDER_ENV} to a valid provider credential. See README.md.",
            3,
        )
    # A real tool would consult a model here. The fixture returns a stub result.
    text = args.text if args.text is not None else ""
    _emit({"result": {"summary": text[:40]}})
    return 0


_EPILOG = (
    "Capabilities:\n"
    "  stats      [deterministic]  Count characters, words, and lines in TEXT.\n"
    "  summarize  [model-backed]   Produce a short summary of TEXT.\n"
    "\n"
    "Model-backed capabilities: summarize. These consume tokens and may return a\n"
    "different answer on a second run. The deterministic capabilities run with no\n"
    "model provider configured.\n"
)


def build_parser() -> argparse.ArgumentParser:
    parser = _EnvelopeParser(
        prog="samplegood",
        description="A minimal reference smart tool for conformance testing.",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="verb")

    p_stats = sub.add_parser(
        "stats", help="[deterministic] Count characters, words, and lines in TEXT."
    )
    p_stats.add_argument("--text", default=None, help="Text to measure.")
    p_stats.set_defaults(func=cmd_stats)

    p_sum = sub.add_parser(
        "summarize", help="[model-backed] Produce a short summary of TEXT."
    )
    p_sum.add_argument("--text", default=None, help="Text to summarize.")
    p_sum.set_defaults(func=cmd_summarize)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "verb", None):
        return _emit_error(
            "no_capability",
            "No capability was named.",
            "Run 'samplegood --help' to see the available capabilities.",
            2,
        )
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
