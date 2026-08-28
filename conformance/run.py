#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""smart-tools conformance kit -- run.py

The first machine-checkable conformance kit for the amplifier-smart-tools-spec
(https://github.com/microsoft/amplifier-smart-tools). It is generic
over ANY smart tool: point it at a distribution root and it derives a verdict
from the spec's must / must-not prose.

  usage:  python3 run.py <tool-dir> [--timeout SECONDS] [--json-only]
          uv run conformance/run.py <tool-dir>

Design commitments (mirroring proven conformance kits):
  * stdlib only -- no third-party dependency, no network access;
  * a JSON verdict on stdout, a human summary on stderr, exit 0 (pass) / 1 (fail);
  * honest SKIP -- a rule that cannot be evaluated is reported SKIP with a
    reason, never a fabricated PASS. The verdict is FAIL iff any rule FAILs.

Each check carries the spec sentence it operationalizes (see UPSTREAM-OFFER.md
for the full rule -> spec-sentence mapping).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"

MANIFEST_NAME = "SMART_TOOL.md"
HINT_NAME = "smart-tool-conformance.json"

# The manifest frontmatter is a closed set. "Fields not listed here are not part
# of the manifest." (manifest.md)
ALLOWED_FIELDS = (
    "smart_tool_format",
    "name",
    "version",
    "description",
    "use_cases",
    "platforms",
    "requires",
)
# `requires` is allowed to be absent for a tool with no prerequisites; every
# other field is described as part of the frontmatter and is required.
REQUIRED_FIELDS = (
    "smart_tool_format",
    "name",
    "version",
    "description",
    "use_cases",
    "platforms",
)
REQUIRES_ENTRY_KEYS = ("name", "purpose", "install", "optional")
REQUIRES_ENTRY_REQUIRED = ("name", "purpose", "install")

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Directories a distribution-root walk should never descend into.
WALK_SKIP = {".git", ".venv", "venv", "node_modules", "__pycache__", ".mypy_cache", ".tox", "dist", "build"}

# Env var names scrubbed before running the target tool, to prove the tool loads
# and runs its deterministic paths with no model provider configured.
PROVIDER_ENV_RE = re.compile(
    r"(API_KEY|ACCESS_KEY|SECRET|_TOKEN$|^ANTHROPIC|^OPENAI|^AZURE_OPENAI|^GOOGLE_API"
    r"|^GEMINI|^MISTRAL|^COHERE|^GROQ|^TOGETHER|^PERPLEXITY|^AMPLIFIER|^LLM|_LLM$"
    r"|^MODEL|_MODEL$|PROVIDER)",
    re.IGNORECASE,
)

# Tokens that mark an `install:` value as a command rather than a doc reference.
INSTALL_COMMAND_RE = re.compile(
    r"^(sudo|apt|apt-get|pip|pip3|pipx|npm|npx|yarn|pnpm|brew|curl|wget|dnf|yum"
    r"|pacman|apk|choco|winget|scoop|docker|uv|cargo|go|gem|make)\b",
    re.IGNORECASE,
)
SHELL_META = ("&&", "||", "|", ";", "$(", "`", ">", "<")

# --help disclosure tokens (case-insensitive) that satisfy "which capabilities
# are model-backed".
DISCLOSURE_TOKENS = ("model-backed", "model backed", "modelbacked")


# --------------------------------------------------------------------------- #
# Result plumbing
# --------------------------------------------------------------------------- #
@dataclass
class Check:
    id: str
    status: str
    spec: str
    detail: str = ""


@dataclass
class Recipe:
    argv: list[str] | None = None
    smoke: list[str] | None = None
    bad: list[str] = field(default_factory=lambda: ["__conformance_no_such_verb__"])
    reason: str = ""  # why argv is None, if it is


# --------------------------------------------------------------------------- #
# Minimal YAML-frontmatter parser (manifest subset, stdlib only)
# --------------------------------------------------------------------------- #
class FrontmatterError(ValueError):
    pass


def extract_frontmatter(text: str) -> str:
    """Return the YAML frontmatter block, or raise FrontmatterError."""
    # Tolerate a leading BOM / blank lines before the opening fence.
    lines = text.split("\n")
    i = 0
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    if i >= len(lines) or lines[i].strip().lstrip("\ufeff") != "---":
        raise FrontmatterError("file does not begin with a '---' YAML frontmatter fence")
    body: list[str] = []
    i += 1
    while i < len(lines):
        if lines[i].strip() == "---":
            return "\n".join(body)
        body.append(lines[i])
        i += 1
    raise FrontmatterError("frontmatter fence is not closed with a second '---'")


def _scalar(raw: str):
    s = raw.strip()
    if s == "":
        return ""
    if (s[0] == s[-1]) and s[0] in ("'", '"') and len(s) >= 2:
        return s[1:-1]
    low = s.lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "~"):
        return None
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    return s


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def parse_frontmatter(text: str) -> dict:
    """Parse the manifest frontmatter subset into a dict.

    Supports top-level scalars, folded block scalars (`key: >`), block sequences
    of scalars, and block sequences of mappings (used by `requires`). This is
    not a general YAML engine; malformed input raises FrontmatterError, which
    the kit reports as a manifest-parse failure.
    """
    raw_lines = [ln for ln in text.split("\n")]
    # Retain structure but drop blank and full-line comment lines.
    lines = [ln for ln in raw_lines if ln.strip() != "" and not ln.lstrip().startswith("#")]
    pos = 0

    def parse_map(base_indent: int):
        nonlocal pos
        result: dict = {}
        while pos < len(lines):
            line = lines[pos]
            ind = _indent(line)
            if ind < base_indent:
                break
            if ind > base_indent:
                raise FrontmatterError(f"unexpected indentation: {line!r}")
            content = line.strip()
            if content.startswith("- "):
                # A sequence at map level is not valid here.
                raise FrontmatterError(f"unexpected sequence item at mapping level: {line!r}")
            if ":" not in content:
                raise FrontmatterError(f"expected 'key: value', got {line!r}")
            key, _, rest = content.partition(":")
            key = key.strip()
            rest = rest.strip()
            pos += 1
            if rest in (">", "|", ">-", "|-"):
                result[key] = parse_folded(base_indent)
            elif rest == "":
                # Nested block: sequence or mapping (or empty).
                if pos < len(lines) and _indent(lines[pos]) > base_indent:
                    nxt = lines[pos].strip()
                    if nxt.startswith("- "):
                        result[key] = parse_seq(_indent(lines[pos]))
                    else:
                        result[key] = parse_map(_indent(lines[pos]))
                else:
                    result[key] = None
            else:
                result[key] = _scalar(rest)
        return result

    def parse_folded(key_indent: int) -> str:
        nonlocal pos
        parts: list[str] = []
        while pos < len(lines) and _indent(lines[pos]) > key_indent:
            parts.append(lines[pos].strip())
            pos += 1
        return " ".join(parts)

    def parse_seq(seq_indent: int):
        nonlocal pos
        items: list = []
        while pos < len(lines):
            line = lines[pos]
            ind = _indent(line)
            if ind != seq_indent or not line.strip().startswith("- "):
                break
            item_body = line.strip()[2:]
            if ":" in item_body and not (item_body[0] in ("'", '"')):
                # Sequence of mappings. First key is inline after "- ".
                entry: dict = {}
                key, _, rest = item_body.partition(":")
                entry[key.strip()] = _scalar(rest.strip()) if rest.strip() else None
                # The mapping's key column is where item_body begins.
                map_indent = seq_indent + 2
                pos += 1
                while pos < len(lines) and _indent(lines[pos]) >= map_indent and not lines[pos].strip().startswith("- "):
                    key_indent = _indent(lines[pos])
                    sub = lines[pos].strip()
                    if ":" not in sub:
                        raise FrontmatterError(f"expected 'key: value' in sequence mapping, got {lines[pos]!r}")
                    k, _, v = sub.partition(":")
                    v = v.strip()
                    pos += 1
                    if v in (">", "|", ">-", "|-"):
                        # A folded/literal block scalar INSIDE a sequence mapping
                        # (e.g. `requires: - name: .. / purpose: > / install: ..`).
                        # Consume the deeper-indented continuation lines as the
                        # value, mirroring the top-level `parse_folded`. Without
                        # this the parser wrongly reported a perfectly valid
                        # manifest (any `requires` entry whose `purpose:` is a
                        # folded scalar) as unparseable -- a false negative that
                        # condemned a correct tool.
                        entry[k.strip()] = parse_folded(key_indent)
                    else:
                        entry[k.strip()] = _scalar(v) if v else None
                items.append(entry)
            else:
                items.append(_scalar(item_body))
                pos += 1
        return items

    if not lines:
        return {}
    data = parse_map(_indent(lines[0]))
    return data


# --------------------------------------------------------------------------- #
# Package metadata + CLI recipe discovery
# --------------------------------------------------------------------------- #
def package_version(target: Path):
    """Return (version, source) or (None, reason)."""
    py = target / "pyproject.toml"
    if py.is_file():
        try:
            data = tomllib.loads(py.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - report as skip reason
            return None, f"pyproject.toml unparseable: {exc}"
        project = data.get("project", {})
        if "version" in project:
            return str(project["version"]), "pyproject.toml [project].version"
        if "version" in project.get("dynamic", []):
            return None, "pyproject.toml declares a dynamic version (not statically resolvable)"
        return None, "pyproject.toml has no [project].version"
    pj = target / "package.json"
    if pj.is_file():
        try:
            data = json.loads(pj.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            return None, f"package.json unparseable: {exc}"
        if "version" in data:
            return str(data["version"]), "package.json version"
        return None, "package.json has no version field"
    return None, "no package definition (pyproject.toml / package.json) found"


def discover_recipe(target: Path) -> Recipe:
    """Determine how to invoke the tool's CLI, or explain why we cannot."""
    hint_path = target / HINT_NAME
    if hint_path.is_file():
        try:
            hint = json.loads(hint_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            return Recipe(reason=f"{HINT_NAME} unparseable: {exc}")
        argv = hint.get("cli_argv")
        if isinstance(argv, list) and argv:
            argv = list(argv)
            if argv[0] in ("python", "python3"):
                argv[0] = sys.executable
            rec = Recipe(argv=argv)
            if isinstance(hint.get("deterministic_smoke"), list):
                rec.smoke = list(hint["deterministic_smoke"])
            if isinstance(hint.get("bad_invocation"), list) and hint["bad_invocation"]:
                rec.bad = list(hint["bad_invocation"])
            return rec

    # Fall back to a Python [project.scripts] entry driven through `uv run`.
    py = target / "pyproject.toml"
    if py.is_file():
        try:
            data = tomllib.loads(py.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            data = {}
        scripts = data.get("project", {}).get("scripts", {})
        if scripts:
            import shutil

            if shutil.which("uv"):
                script = next(iter(scripts))
                return Recipe(argv=["uv", "run", "--project", str(target), script])
            return Recipe(reason="pyproject declares [project.scripts] but 'uv' is not on PATH to run it")
    return Recipe(reason=f"no CLI entry point discoverable (no {HINT_NAME}, no [project.scripts])")


def scrubbed_env() -> dict:
    env = {k: v for k, v in os.environ.items() if not PROVIDER_ENV_RE.search(k)}
    return env


@dataclass
class Run:
    rc: int
    out: str
    err: str
    timed_out: bool


def run_cli(argv: list[str], cwd: Path, timeout: float, scrub: bool = True) -> Run:
    env = scrubbed_env() if scrub else dict(os.environ)
    try:
        proc = subprocess.run(
            argv,
            cwd=str(cwd),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout,
        )
        return Run(proc.returncode, proc.stdout, proc.stderr, False)
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout or ""
        err = exc.stderr or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        if isinstance(err, bytes):
            err = err.decode("utf-8", "replace")
        return Run(-1, out, err, True)


# --------------------------------------------------------------------------- #
# Checks
# --------------------------------------------------------------------------- #
def evaluate(target: str | Path, timeout: float = 20.0) -> dict:
    target = Path(target).resolve()
    checks: list[Check] = []

    def add(id_, status, spec, detail=""):
        checks.append(Check(id_, status, spec, detail))

    # --- Manifest gathering ------------------------------------------------- #
    # The manifest sits beside the code that reads it, so it is found by searching
    # the distribution rather than by a fixed path. Exactly one is permitted; when
    # a tool ships several, M8 reports it and the first is parsed.
    found_manifests = sorted(_find_manifests(target))
    manifest_path = found_manifests[0] if found_manifests else target / MANIFEST_NAME
    fm: dict | None = None
    fm_error: str | None = None
    if manifest_path.is_file():
        try:
            fm = parse_frontmatter(extract_frontmatter(manifest_path.read_text(encoding="utf-8")))
            if not isinstance(fm, dict):
                fm, fm_error = None, "frontmatter is not a mapping"
        except FrontmatterError as exc:
            fm_error = str(exc)
        except Exception as exc:  # noqa: BLE001
            fm_error = f"unexpected parse error: {exc}"

    # M1 manifest-present
    manifest_spec = ("manifest.md: 'SMART_TOOL.md, in the tool's own source, beside the "
                     "code that reads it.'")
    if manifest_path.is_file():
        add("manifest-present", PASS, manifest_spec,
            f"{MANIFEST_NAME} found at {manifest_path.relative_to(target)}")
    else:
        add("manifest-present", FAIL, manifest_spec,
            f"no {MANIFEST_NAME} anywhere under {target}")

    # M2 manifest-frontmatter-parses
    if not manifest_path.is_file():
        add("manifest-frontmatter-parses", SKIP,
            "manifest.md: 'YAML frontmatter, then a Markdown body.'", "no manifest to parse")
    elif fm is not None:
        add("manifest-frontmatter-parses", PASS,
            "manifest.md: 'YAML frontmatter, then a Markdown body.'", "frontmatter parsed")
    else:
        add("manifest-frontmatter-parses", FAIL,
            "manifest.md: 'YAML frontmatter, then a Markdown body.'", fm_error or "parse failed")

    manifest_ok = fm is not None

    # M3 manifest-fields-closed
    if not manifest_ok:
        add("manifest-fields-closed", SKIP,
            "manifest.md: 'Fields not listed here are not part of the manifest.'",
            "manifest not available")
    else:
        extra = [k for k in fm if k not in ALLOWED_FIELDS]
        if extra:
            add("manifest-fields-closed", FAIL,
                "manifest.md: 'Fields not listed here are not part of the manifest.'",
                f"field(s) not in the closed set: {', '.join(sorted(extra))}")
        else:
            add("manifest-fields-closed", PASS,
                "manifest.md: 'Fields not listed here are not part of the manifest.'",
                "only recognised fields present")

    # M4 manifest-required-fields
    if not manifest_ok:
        add("manifest-required-fields", SKIP,
            "manifest.md: the frontmatter fields each described as part of the manifest",
            "manifest not available")
    else:
        missing = [k for k in REQUIRED_FIELDS if k not in fm]
        if missing:
            add("manifest-required-fields", FAIL,
                "manifest.md: the frontmatter fields each described as part of the manifest",
                f"missing required field(s): {', '.join(missing)}")
        else:
            add("manifest-required-fields", PASS,
                "manifest.md: the frontmatter fields each described as part of the manifest",
                "all required fields present")

    # M5 manifest-name-format
    if not manifest_ok or "name" not in fm:
        add("manifest-name-format", SKIP,
            "manifest.md: 'name is lowercase alphanumeric and hyphens.'",
            "no name field to validate")
    else:
        name = fm["name"]
        if isinstance(name, str) and NAME_RE.match(name):
            add("manifest-name-format", PASS,
                "manifest.md: 'name is lowercase alphanumeric and hyphens.'", f"name={name!r}")
        else:
            add("manifest-name-format", FAIL,
                "manifest.md: 'name is lowercase alphanumeric and hyphens.'",
                f"name {name!r} is not lowercase alphanumeric with hyphens")

    # M6 manifest-version-matches-package
    pkg_version, pkg_source = package_version(target)
    if not manifest_ok or "version" not in fm:
        add("manifest-version-matches-package", SKIP,
            "manifest.md: 'version ... matches the version in the package definition.'",
            "no manifest version to compare")
    elif pkg_version is None:
        add("manifest-version-matches-package", SKIP,
            "manifest.md: 'version ... matches the version in the package definition.'",
            pkg_source)
    else:
        mver = str(fm["version"]).strip()
        if mver == pkg_version.strip():
            add("manifest-version-matches-package", PASS,
                "manifest.md: 'version ... matches the version in the package definition.'",
                f"manifest {mver} == {pkg_source} {pkg_version}")
        else:
            add("manifest-version-matches-package", FAIL,
                "manifest.md: 'version ... matches the version in the package definition.'",
                f"manifest {mver} != {pkg_source} {pkg_version}")

    # M7 manifest-requires-shape
    if not manifest_ok:
        add("manifest-requires-shape", SKIP,
            "manifest.md: 'Each entry carries name, purpose, and install ... install is a "
            "reference to documentation ... never a command.'", "manifest not available")
    elif "requires" not in fm or fm["requires"] in (None, []):
        add("manifest-requires-shape", SKIP,
            "manifest.md: 'Each entry carries name, purpose, and install ... install is a "
            "reference to documentation ... never a command.'", "no 'requires' entries to validate")
    else:
        req = fm["requires"]
        problems: list[str] = []
        if not isinstance(req, list):
            problems.append("'requires' is not a list")
        else:
            for idx, entry in enumerate(req):
                if not isinstance(entry, dict):
                    problems.append(f"entry #{idx} is not a mapping")
                    continue
                for k in REQUIRES_ENTRY_REQUIRED:
                    if k not in entry:
                        problems.append(f"entry #{idx} ({entry.get('name', '?')}) missing '{k}'")
                extra_keys = [k for k in entry if k not in REQUIRES_ENTRY_KEYS]
                if extra_keys:
                    problems.append(f"entry #{idx} has unknown key(s): {', '.join(extra_keys)}")
                if "optional" in entry and not isinstance(entry["optional"], bool):
                    problems.append(f"entry #{idx} 'optional' must be a boolean")
                install = entry.get("install")
                if isinstance(install, str):
                    reason = _install_command_reason(install)
                    if reason:
                        problems.append(f"entry #{idx} ({entry.get('name', '?')}) install {reason}")
        if problems:
            add("manifest-requires-shape", FAIL,
                "manifest.md: 'Each entry carries name, purpose, and install ... install is a "
                "reference to documentation ... never a command.'", "; ".join(problems))
        else:
            add("manifest-requires-shape", PASS,
                "manifest.md: 'Each entry carries name, purpose, and install ... install is a "
                "reference to documentation ... never a command.'",
                f"{len(req)} requires entry(ies) well-formed")

    # M8 manifest-single-per-root
    found = found_manifests
    if len(found) > 1:
        rels = ", ".join(sorted(str(p.relative_to(target)) for p in found))
        add("manifest-single-per-root", FAIL,
            "manifest.md: 'Exactly one manifest per distribution. A second SMART_TOOL.md "
            "beneath a distribution root is incorrect.'",
            f"{len(found)} manifests under root: {rels}")
    elif len(found) == 1:
        add("manifest-single-per-root", PASS,
            "manifest.md: 'Exactly one manifest per distribution. A second SMART_TOOL.md "
            "beneath a distribution root is incorrect.'", "exactly one manifest under root")
    else:
        add("manifest-single-per-root", SKIP,
            "manifest.md: 'Exactly one manifest per distribution. A second SMART_TOOL.md "
            "beneath a distribution root is incorrect.'", "no manifest found under root")

    # --- Runtime gathering -------------------------------------------------- #
    recipe = discover_recipe(target)
    help_run = smoke_run = bad_run = None
    if recipe.argv is not None:
        help_run = run_cli(recipe.argv + ["--help"], target, timeout, scrub=True)
        if recipe.smoke:
            smoke_run = run_cli(recipe.argv + recipe.smoke, target, timeout, scrub=True)
        bad_run = run_cli(recipe.argv + recipe.bad, target, timeout, scrub=True)

    # R1 loads-without-provider
    spec_r1 = ("structure.md: 'the straight code paths run with no model provider configured "
               "... the tool must not refuse to load without them.'")
    if recipe.argv is None:
        add("loads-without-provider", SKIP, spec_r1, recipe.reason)
    elif help_run.timed_out:
        add("loads-without-provider", SKIP, spec_r1,
            "startup did not complete within timeout (inconclusive; see no-hang)")
    elif help_run.rc == 0:
        add("loads-without-provider", PASS, spec_r1,
            "'--help' exits 0 with provider env scrubbed")
    else:
        add("loads-without-provider", FAIL, spec_r1,
            f"'--help' exits {help_run.rc} with provider env scrubbed (tool refuses to load): "
            f"{_first_line(help_run.err or help_run.out)}")

    # R2 help-discloses-model-backed
    spec_r2 = "invocation.md: '--help ... which capabilities are model-backed.'"
    if recipe.argv is None:
        add("help-discloses-model-backed", SKIP, spec_r2, recipe.reason)
    elif help_run.timed_out or help_run.rc != 0:
        add("help-discloses-model-backed", SKIP, spec_r2,
            "could not obtain a successful '--help' (see loads-without-provider / no-hang)")
    else:
        blob = (help_run.out + "\n" + help_run.err).lower()
        if any(tok in blob for tok in DISCLOSURE_TOKENS):
            add("help-discloses-model-backed", PASS, spec_r2,
                "'--help' discloses which capabilities are model-backed")
        else:
            add("help-discloses-model-backed", FAIL, spec_r2,
                "'--help' does not disclose which capabilities are model-backed "
                "(expected a 'model-backed' marker)")

    # R3 deterministic-capability-runs
    spec_r3 = ("structure.md: 'A caller that only wants the deterministic capabilities never has "
               "to supply model credentials.'")
    if recipe.argv is None:
        add("deterministic-capability-runs", SKIP, spec_r3, recipe.reason)
    elif not recipe.smoke:
        add("deterministic-capability-runs", SKIP, spec_r3,
            "no deterministic smoke invocation declared (smart-tool-conformance.json)")
    elif smoke_run.timed_out:
        add("deterministic-capability-runs", FAIL, spec_r3,
            f"deterministic '{' '.join(recipe.smoke)}' did not complete within {timeout:g}s "
            "with provider env scrubbed")
    elif smoke_run.rc == 0:
        add("deterministic-capability-runs", PASS, spec_r3,
            f"deterministic '{' '.join(recipe.smoke)}' runs (exit 0) with provider env scrubbed")
    else:
        add("deterministic-capability-runs", FAIL, spec_r3,
            f"deterministic '{' '.join(recipe.smoke)}' exits {smoke_run.rc} with provider env "
            f"scrubbed: {_first_line(smoke_run.err or smoke_run.out)}")

    # R4 failure-names-remedy (failure shape)
    spec_r4 = ("invocation.md/README.md: 'A failure names what went wrong and how to correct it "
               "... not ... a bare stack trace' -- structured error, non-zero exit.")
    if recipe.argv is None:
        add("failure-names-remedy", SKIP, spec_r4, recipe.reason)
    elif bad_run.timed_out:
        add("failure-names-remedy", SKIP, spec_r4, "bad invocation did not complete (see no-hang)")
    else:
        combined = bad_run.out + "\n" + bad_run.err
        has_traceback = "Traceback (most recent call last)" in combined
        structured = _looks_structured(bad_run.out)
        if bad_run.rc == 0:
            add("failure-names-remedy", FAIL, spec_r4,
                f"bad invocation '{' '.join(recipe.bad)}' exited 0 (a bad invocation must fail)")
        elif has_traceback:
            add("failure-names-remedy", FAIL, spec_r4,
                "bad invocation produced a bare stack trace instead of a structured error")
        elif not structured:
            add("failure-names-remedy", FAIL, spec_r4,
                "bad invocation exited non-zero but emitted no structured (JSON) error on stdout")
        else:
            add("failure-names-remedy", PASS, spec_r4,
                f"bad invocation exits {bad_run.rc} with a structured JSON error on stdout")

    # R5 no-hang (stdin closed, bounded)
    spec_r5 = "contracts/README: 'a run with stdin closed never hangs' (non-interactive caller)."
    hang_probe = smoke_run if (recipe.smoke and smoke_run is not None) else help_run
    probe_desc = " ".join(recipe.smoke) if (recipe.smoke and smoke_run is not None) else "--help"
    if recipe.argv is None:
        add("no-hang-stdin-closed", SKIP, spec_r5, recipe.reason)
    elif hang_probe is None:
        add("no-hang-stdin-closed", SKIP, spec_r5, "no probe invocation available")
    elif hang_probe.timed_out:
        add("no-hang-stdin-closed", FAIL, spec_r5,
            f"'{probe_desc}' with stdin closed exceeded {timeout:g}s (possible hang)")
    else:
        add("no-hang-stdin-closed", PASS, spec_r5,
            f"'{probe_desc}' completes with stdin closed")

    # --- Verdict ------------------------------------------------------------ #
    counts = {
        "pass": sum(c.status == PASS for c in checks),
        "fail": sum(c.status == FAIL for c in checks),
        "skip": sum(c.status == SKIP for c in checks),
    }
    verdict = FAIL if counts["fail"] else PASS
    return {
        "schema": "smart-tools-conformance/v1",
        "target": str(target),
        "verdict": verdict,
        "counts": counts,
        "failed_rules": [c.id for c in checks if c.status == FAIL],
        "checks": [vars(c) for c in checks],
    }


def _install_command_reason(install: str) -> str | None:
    s = install.strip()
    if not s:
        return "is empty"
    if any(meta in s for meta in SHELL_META):
        return "contains shell metacharacters (looks like a command, not a doc reference)"
    if INSTALL_COMMAND_RE.match(s):
        return "starts with an installer command verb (must be a doc path or URL, not a command)"
    if re.search(r"\s", s):
        return "contains whitespace (a doc reference is a bare relative path or URL)"
    return None


def _find_manifests(root: Path) -> list[Path]:
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in WALK_SKIP]
        if MANIFEST_NAME in filenames:
            out.append(Path(dirpath) / MANIFEST_NAME)
    return out


def _looks_structured(stdout: str) -> bool:
    s = stdout.strip()
    if not s:
        return False
    try:
        obj = json.loads(s)
    except Exception:  # noqa: BLE001
        # Accept a JSON object on the first non-empty line (tools may print more after).
        first = s.split("\n", 1)[0].strip()
        try:
            obj = json.loads(first)
        except Exception:  # noqa: BLE001
            return False
    return isinstance(obj, (dict, list))


def _first_line(text: str) -> str:
    text = (text or "").strip()
    return text.split("\n", 1)[0][:200] if text else "(no output)"


# --------------------------------------------------------------------------- #
# Human summary + CLI
# --------------------------------------------------------------------------- #
def render_summary(result: dict) -> str:
    lines = [f"smart-tools conformance :: {result['target']}"]
    for c in result["checks"]:
        lines.append(f"  {c['status']:<4} {c['id']:<30} {c['detail']}")
    counts = result["counts"]
    lines.append(
        f"VERDICT: {result['verdict']} "
        f"({counts['pass']} pass, {counts['fail']} fail, {counts['skip']} skip)"
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="conformance/run.py",
        description="Machine-checkable conformance kit for the amplifier-smart-tools-spec.",
    )
    parser.add_argument("target", help="Path to a smart tool's distribution root.")
    parser.add_argument("--timeout", type=float, default=20.0,
                        help="Per-invocation timeout in seconds (default: 20).")
    parser.add_argument("--json-only", action="store_true",
                        help="Suppress the human summary on stderr.")
    args = parser.parse_args(argv)

    target = Path(args.target)
    if not target.is_dir():
        err = {"schema": "smart-tools-conformance/v1", "target": str(target),
               "verdict": FAIL, "error": f"not a directory: {target}"}
        print(json.dumps(err, indent=2))
        print(f"error: not a directory: {target}", file=sys.stderr)
        return 1

    result = evaluate(target, timeout=args.timeout)
    print(json.dumps(result, indent=2))
    if not args.json_only:
        print(render_summary(result), file=sys.stderr)
    return 0 if result["verdict"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
