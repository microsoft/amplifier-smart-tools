# Smart-tools conformance kit

The first machine-checkable conformance kit for the
[amplifier-smart-tools](https://github.com/microsoft/amplifier-smart-tools).
It is **generic over any smart tool**: point it at a distribution root and it
derives a PASS / FAIL verdict from the spec's must / must-not prose. It knows
nothing about this repository's tmux tool -- it validates against its own
fixtures under `fixtures/`.

## Quick start

```bash
# stdlib only -- no dependencies, no network
python3 conformance/run.py <path-to-a-smart-tool>

# or, uv-runnable:
uv run conformance/run.py <path-to-a-smart-tool>
```

`<path-to-a-smart-tool>` is a **distribution root**: the directory that holds the
package definition (`pyproject.toml` / `package.json`). The kit searches it for
the one `SMART_TOOL.md` the tool ships.

## Output contract

- **stdout** -- one JSON verdict document (`schema: smart-tools-conformance/v1`)
  with per-rule `status`, the spec sentence each rule operationalizes, and a
  `failed_rules` list.
- **stderr** -- a human-readable summary table.
- **exit code** -- `0` if no rule FAILed, `1` otherwise.
- **honest SKIP** -- a rule that cannot be evaluated (no manifest, no CLI recipe,
  a dynamic package version, ...) is reported `SKIP` with a reason. The kit never
  fabricates a PASS. The verdict is FAIL **iff** any rule is FAIL; SKIPs never
  fail a tool but are always surfaced.

```
--json-only    suppress the stderr summary
--timeout N    per-invocation timeout in seconds (default 20)
```

## What it checks

Fourteen rules, each carrying the spec sentence it operationalizes (full mapping
in [`UPSTREAM-OFFER.md`](UPSTREAM-OFFER.md)).

| Rule id | Enforces |
|---|---|
| `descriptor-present` | `smart-tool.json` at the distribution root names the manifest and how to launch the CLI. |
| `manifest-present` | The manifest exists at the path the descriptor names, inside the distribution. |
| `manifest-frontmatter-parses` | It opens with a closed YAML frontmatter fence that parses. |
| `manifest-fields-closed` | No field outside the closed set `smart_tool_format, name, version, description, use_cases, platforms, requires`. |
| `manifest-required-fields` | The required fields are present. |
| `manifest-name-format` | `name` is lowercase alphanumeric and hyphens. |
| `manifest-version-matches-package` | Manifest `version` equals the package-definition version. |
| `manifest-requires-shape` | Each `requires` entry is `{name, purpose, install[, optional]}`; `install` is a doc reference, never a command. |
| `manifest-single-per-root` | Exactly one `SMART_TOOL.md` under the root, not counting nested distributions. |
| `loads-without-provider` | With provider env scrubbed, the tool loads (`--help` exits 0) -- it does not refuse to load. |
| `help-discloses-model-backed` | `--help` discloses which capabilities are model-backed. |
| `deterministic-capability-runs` | A declared deterministic capability runs with provider env scrubbed. |
| `failure-names-remedy` | A bad invocation yields a structured JSON error + non-zero exit, not a bare stack trace. |
| `no-hang-stdin-closed` | A run with stdin closed completes within the bounded timeout. |

The descriptor rule and the eight `manifest-*` rules are pure file inspection and
run against any tool in any language. The five runtime rules need to *invoke* the
tool (see below); when no invocation is possible they SKIP honestly.

## The descriptor

Everything the kit needs to locate and start a tool comes from `smart-tool.json`
at the distribution root (see `spec/packaging.md`):

```json
{
  "manifest": "src/mytool/SMART_TOOL.md",
  "cli_argv": ["python3", "src/mytool/cli.py"],
  "deterministic_smoke": ["stats", "--text", "hello world"]
}
```

- `manifest` -- where `SMART_TOOL.md` lives, relative to the descriptor.
- `cli_argv` -- how to launch the CLI (run with the tool dir as cwd; a leading
  `python`/`python3` is resolved to the running interpreter).
- `deterministic_smoke` -- a side-effect-free deterministic invocation.

To exercise `failure-names-remedy` the kit appends a verb no tool defines,
`__conformance_no_such_verb__`, and inspects how the rejection is shaped.

This is the kit's only source. It never installs the tool under test: present it
with one that already runs, from source or installed onto the path. Without a
descriptor, `descriptor-present` FAILs and the five runtime rules SKIP rather
than passing or failing.

A subdirectory with its own descriptor is a nested distribution, and its manifest
is not counted against the parent.

### Provider scrubbing

Before the `loads-without-provider` and `deterministic-capability-runs` probes,
the kit removes provider/model environment variables (anything matching
`*_API_KEY`, `ANTHROPIC*`, `OPENAI*`, `*_MODEL`, `*PROVIDER*`, ...) so it observes
the tool as a caller with **no** model credentials would.

## Fixtures (proof of discrimination)

- `fixtures/sample-good/` -- a minimal, brand-neutral reference smart tool that
  passes every rule. It is laid out the way a real smart tool is: a `src/`
  package holding the library, the CLI, and the one manifest both of them read.
- `fixtures/sample-bad-*/` -- one defect each; the kit must fail each fixture with
  the corresponding rule named. Every rule the kit emits has a dedicated negative
  fixture (`tests/test_conformance.py::test_every_rule_has_a_negative_fixture`).

A tool that refuses to load also cannot run its deterministic verb, so a few
runtime defects legitimately cascade across more than one rule; the tests assert
the primary rule is *among* the failures.

## Running the kit's own tests

```bash
uv run --with pytest pytest -q conformance/
```

The tests cover the frontmatter parser and helpers directly, and run the kit
end-to-end against every fixture.
