#!/usr/bin/env python3
"""samplegood: the conformance kit's known-good smart tool. Library first, thin argparse CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

NAME = "samplegood"
PROVIDER_ENV = "SAMPLE_PROVIDER_KEY"

# (name, kind, summary). Drives the skill's capability list, `-h`, and the subparsers.
CAPABILITIES = (
    ("stats", "deterministic", "Count characters, words, and lines in TEXT."),
    ("summarize", "model-backed", "Produce a short summary of TEXT."),
)
SKILL_RESOURCES = ("SMART_TOOL.md", "docs/using-samplegood.md")


def skill_directory() -> Path:
    """The installed package root, resolved at runtime."""
    return Path(__file__).resolve().parent


def manifest_body() -> str:
    """The Markdown below the manifest's frontmatter."""
    lines = (skill_directory() / "SMART_TOOL.md").read_text(encoding="utf-8").splitlines()
    fences = [i for i, line in enumerate(lines) if line.strip() == "---"]
    if len(fences) < 2:
        raise ValueError("SMART_TOOL.md has no closed YAML frontmatter fence")
    return "\n".join(lines[fences[1] + 1 :]).strip()


def skill_resources() -> list[str]:
    """The files the skill lists, as paths relative to the skill directory."""
    return list(SKILL_RESOURCES)


def skill() -> str:
    """The tool's skill: manifest body plus generated capability list, wrapped with the file locations."""
    try:
        body = manifest_body()
    except (OSError, ValueError) as exc:
        # An unreadable manifest is reported by the manifest rules; the rest of the skill still renders.
        body = f"(manifest unavailable: {exc})"
    lines = [
        f'<skill_content name="{NAME}">',
        f"Skill directory: {skill_directory()}",
        "Relative paths in this skill are relative to the skill directory.",
        "",
        f"# {NAME}",
        "",
        body,
        "",
        "## Capabilities",
        "",
    ]
    for name, kind, summary in CAPABILITIES:
        lines.append(f"- `{name}` [{kind}] -- {summary} Arguments, result, and exit codes: `{NAME} {name} --help`.")
    lines += ["", "<skill_resources>"]
    lines += [f"  <file>{path}</file>" for path in skill_resources()]
    lines += ["</skill_resources>", "</skill_content>"]
    return "\n".join(lines)


def short_help() -> str:
    """The terse summary for a person."""
    lines = [f"usage: {NAME} <capability> [options]", "", "capabilities:"]
    lines += [f"  {name:<9}  {f'[{kind}]':<15}  {summary}" for name, kind, summary in CAPABILITIES]
    lines += [
        "",
        "  -h                              this summary",
        "  --help                          this tool's skill, for an agent driving it",
        f"  {NAME} <capability> --help  one capability in full",
    ]
    return "\n".join(lines)


def _emit(document: dict) -> None:
    json.dump(document, sys.stdout, sort_keys=True)
    sys.stdout.write("\n")


def _emit_error(code: str, message: str, remedy: str, exit_code: int) -> int:
    _emit({"error": {"code": code, "message": message, "remedy": remedy}})
    return exit_code


def cmd_stats(args: argparse.Namespace) -> int:
    text = args.text or ""
    _emit({"result": {"chars": len(text), "words": len(text.split()), "lines": len(text.splitlines())}})
    return 0


def cmd_summarize(args: argparse.Namespace) -> int:
    if not os.environ.get(PROVIDER_ENV):
        return _emit_error(
            "no_provider",
            "The 'summarize' capability is model-backed and no model provider is configured.",
            f"Set {PROVIDER_ENV} to a valid provider credential.",
            3,
        )
    _emit({"result": {"summary": (args.text or "")[:40]}})
    return 0


class _PrintAndExit(argparse.Action):
    """Print the text a callable returns, then exit 0."""

    def __init__(self, option_strings, render, dest=argparse.SUPPRESS, default=argparse.SUPPRESS, help=None):
        super().__init__(option_strings=option_strings, dest=dest, default=default, nargs=0, help=help)
        self.render = render

    def __call__(self, parser, namespace, values, option_string=None):
        sys.stdout.write(self.render() + "\n")
        parser.exit(0)


class _EnvelopeParser(argparse.ArgumentParser):
    """Reports a bad invocation as a JSON envelope on stdout, exit 2."""

    def error(self, message: str):
        _emit_error("bad_invocation", message, f"Run '{NAME} -h' for the capabilities.", 2)
        raise SystemExit(2)


def build_parser() -> argparse.ArgumentParser:
    parser = _EnvelopeParser(prog=NAME, add_help=False)
    parser.add_argument("-h", action=_PrintAndExit, render=short_help, help="Terse summary.")
    parser.add_argument("--help", action=_PrintAndExit, render=skill, help="This tool's skill.")
    sub = parser.add_subparsers(dest="verb")

    stats = sub.add_parser(
        "stats",
        help=CAPABILITIES[0][2],
        description=(
            "[deterministic] Count characters, words, and lines in TEXT. Runs with no model provider. "
            'Returns {"result": {"chars": int, "words": int, "lines": int}}. Exit codes: 0 success, 2 bad invocation.'
        ),
    )
    stats.add_argument("--text", default=None, help="Text to measure.")
    stats.set_defaults(func=cmd_stats)

    summarize = sub.add_parser(
        "summarize",
        help=CAPABILITIES[1][2],
        description=(
            "[model-backed] Produce a short summary of TEXT. Consumes tokens and may differ between runs. "
            'Returns {"result": {"summary": str}}. Exit codes: 0 success, 2 bad invocation, '
            f"3 no provider configured (set {PROVIDER_ENV})."
        ),
    )
    summarize.add_argument("--text", default=None, help="Text to summarize.")
    summarize.set_defaults(func=cmd_summarize)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not getattr(args, "verb", None):
        return _emit_error("no_capability", "No capability was named.", f"Run '{NAME} -h' for the capabilities.", 2)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
