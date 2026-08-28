"""Discrimination tests: the kit is green on sample-good and red-with-named-rule
on every sample-bad fixture."""

import json
import shutil
from pathlib import Path

import pytest

import run
from conftest import FIXTURES_DIR

# Short per-invocation timeout keeps the suite fast; the only fixture that spends
# the full budget is sample-bad-hang (its smoke path never returns).
TIMEOUT = 4.0

# Each sample-bad fixture embodies ONE defect whose PRIMARY rule is named here.
# Some runtime defects legitimately cascade (a tool that refuses to load also
# cannot run its deterministic verb); we assert the primary rule is *among* the
# failures, not that it is the only one.
EXPECTED_PRIMARY = {
    "sample-bad-descriptor-no-manifest": "descriptor-present",
    "sample-bad-manifest-missing": "manifest-present",
    "sample-bad-frontmatter-broken": "manifest-frontmatter-parses",
    "sample-bad-extra-field": "manifest-fields-closed",
    "sample-bad-missing-version": "manifest-required-fields",
    "sample-bad-name-uppercase": "manifest-name-format",
    "sample-bad-version-mismatch": "manifest-version-matches-package",
    "sample-bad-requires-install-command": "manifest-requires-shape",
    "sample-bad-double-manifest": "manifest-single-per-root",
    "sample-bad-refuses-without-provider": "loads-without-provider",
    "sample-bad-help-no-disclosure": "help-discloses-model-backed",
    "sample-bad-deterministic-refuses": "deterministic-capability-runs",
    "sample-bad-failure-traceback": "failure-names-remedy",
    "sample-bad-hang": "no-hang-stdin-closed",
}


def _evaluate(name: str) -> dict:
    return run.evaluate(FIXTURES_DIR / name, timeout=TIMEOUT)


def test_sample_good_is_green():
    result = _evaluate("sample-good")
    assert result["verdict"] == run.PASS
    assert result["counts"]["fail"] == 0
    # sample-good is a complete tool: nothing should even be skipped.
    assert result["counts"]["skip"] == 0, result["failed_rules"]


def test_manifest_is_found_inside_the_package():
    """The manifest sits where packaging carries it into the built artifact.

    For a src layout that is the module directory, not the directory holding the
    package definition. The descriptor names that path, so discovery works
    wherever an ecosystem's build requires the manifest to live.
    """
    result = _evaluate("sample-good")
    present = next(c for c in result["checks"] if c["id"] == "manifest-present")
    assert "src/samplegood/SMART_TOOL.md" in present["detail"]


def test_nested_distribution_does_not_count_against_its_parent():
    """A vendored tool's tree is bounded by its own descriptor.

    The fixtures directory holds many distributions, each with a manifest. A tool
    that vendors it must not thereby trip manifest-single-per-root.
    """
    result = run.evaluate(FIXTURES_DIR.parent, timeout=TIMEOUT)
    by_id = {c["id"]: c["status"] for c in result["checks"]}
    assert by_id["manifest-single-per-root"] != run.FAIL


@pytest.mark.parametrize("fixture,primary", sorted(EXPECTED_PRIMARY.items()))
def test_sample_bad_fails_with_named_rule(fixture, primary):
    result = _evaluate(fixture)
    assert result["verdict"] == run.FAIL, f"{fixture} unexpectedly passed"
    assert primary in result["failed_rules"], (
        f"{fixture}: expected rule {primary!r} to be named among failures, "
        f"got {result['failed_rules']}"
    )


def test_every_rule_has_a_negative_fixture():
    """The union of what the bad fixtures trip covers every rule the kit emits."""
    good = _evaluate("sample-good")
    all_rule_ids = {c["id"] for c in good["checks"]}
    covered = set(EXPECTED_PRIMARY.values())
    assert covered == all_rule_ids, (
        f"rules with no dedicated negative fixture: {sorted(all_rule_ids - covered)}"
    )


def test_skip_is_honest_never_a_fabricated_pass():
    """A rule that cannot be evaluated is SKIP, not PASS.

    sample-bad-missing-version has no manifest version, so the version-match
    rule has nothing to compare and must SKIP -- never silently PASS.
    """
    result = _evaluate("sample-bad-missing-version")
    by_id = {c["id"]: c["status"] for c in result["checks"]}
    assert by_id["manifest-version-matches-package"] == run.SKIP


def test_tool_runs_in_a_scratch_directory(tmp_path: Path):
    """A conformance run leaves nothing behind in the distribution it inspects.

    The tool is started from a scratch directory, so anything it writes relative
    to its working directory lands there rather than in its own tree.
    """
    tool = tmp_path / "tool"
    shutil.copytree(FIXTURES_DIR / "sample-good", tool)

    # A wrapper that litters its working directory, then defers to the real CLI.
    # Wrapping rather than editing cli.py keeps the tool itself valid, so a
    # crash cannot masquerade as "nothing was written".
    (tool / "litter_wrapper.py").write_text(
        "import runpy\n"
        "from pathlib import Path\n"
        "Path('LITTER.txt').write_text('written from the working directory')\n"
        "cli = Path(__file__).parent / 'src' / 'samplegood' / 'cli.py'\n"
        "runpy.run_path(str(cli), run_name='__main__')\n",
        encoding="utf-8",
    )
    descriptor = json.loads((tool / "smart-tool.json").read_text())
    descriptor["cli_argv"] = ["uv", "run", "--no-project", "litter_wrapper.py"]
    (tool / "smart-tool.json").write_text(json.dumps(descriptor, indent=2), encoding="utf-8")

    result = run.evaluate(tool, timeout=TIMEOUT)

    # The CLI really ran: --help succeeded through the wrapper.
    by_id = {c["id"]: c["status"] for c in result["checks"]}
    assert by_id["loads-without-provider"] == run.PASS, "the wrapper never reached the CLI"
    assert not list(tool.rglob("LITTER.txt")), "the tool wrote into the distribution"


def test_runtime_rules_skip_without_a_descriptor(tmp_path: Path):
    """A directory with a manifest but no descriptor is not a distribution.

    The runtime rules cannot be evaluated without one, so they SKIP honestly
    rather than being fabricated as PASS or condemned as FAIL. The missing
    descriptor itself is what fails.
    """
    (tmp_path / "SMART_TOOL.md").write_text(
        "---\n"
        "smart_tool_format: 1\n"
        "name: manifest-only\n"
        "version: 0.0.1\n"
        "description: >\n"
        "  A manifest with no runnable CLI.\n"
        "use_cases:\n"
        "  - Exercise the no-recipe path\n"
        "platforms:\n"
        "  - linux\n"
        "---\n\n# body\n",
        encoding="utf-8",
    )
    result = run.evaluate(tmp_path, timeout=TIMEOUT)
    by_id = {c["id"]: c["status"] for c in result["checks"]}
    for rule in (
        "loads-without-provider",
        "help-discloses-model-backed",
        "deterministic-capability-runs",
        "failure-names-remedy",
        "no-hang-stdin-closed",
    ):
        assert by_id[rule] == run.SKIP, f"{rule} should SKIP without a descriptor"
    assert by_id["descriptor-present"] == run.FAIL
    # Nothing beyond the missing descriptor and the manifest it would have named.
    assert set(result["failed_rules"]) == {"descriptor-present", "manifest-present"}


def test_verdict_json_shape():
    result = _evaluate("sample-good")
    assert set(result) >= {"schema", "target", "verdict", "counts", "failed_rules", "checks"}
    assert result["schema"] == "smart-tools-conformance/v1"
    for c in result["checks"]:
        assert set(c) == {"id", "status", "spec", "detail"}
        assert c["status"] in (run.PASS, run.FAIL, run.SKIP)
