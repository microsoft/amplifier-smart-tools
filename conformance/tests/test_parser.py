"""Unit tests for manifest frontmatter extraction, parsing, and schema validation."""

import pytest

import run

GOOD_MANIFEST = """---
smart_tool_format: 1
name: my-tool
version: 1.2.3
description: >
  A folded description that spans
  two source lines but is one string.
use_cases:
  - Do a thing
  - Do another thing
platforms:
  - linux
requires:
  - name: incus
    purpose: Runs environments.
    install: docs/incus.md
  - name: docker
    purpose: Sidecars.
    optional: true
    install: https://example.test/docker
---

# body ignored
"""


def _fm(text: str = GOOD_MANIFEST) -> dict:
    return run.parse_frontmatter(run.extract_frontmatter(text))


def test_extract_and_parse_roundtrip():
    data = _fm()
    assert data["smart_tool_format"] == 1
    assert data["name"] == "my-tool"
    assert data["version"] == "1.2.3"  # dotted version stays a string
    assert data["description"].strip() == (
        "A folded description that spans two source lines but is one string."
    )
    assert data["use_cases"] == ["Do a thing", "Do another thing"]
    assert data["platforms"] == ["linux"]


def test_requires_is_list_of_mappings_with_types():
    req = _fm()["requires"]
    assert isinstance(req, list) and len(req) == 2
    assert req[0] == {"name": "incus", "purpose": "Runs environments.", "install": "docs/incus.md"}
    assert req[1]["optional"] is True  # boolean, not the string "true"
    assert req[1]["install"] == "https://example.test/docker"


def test_missing_closing_fence_raises():
    broken = "---\nname: x\nversion: 1\n"  # no closing '---'
    with pytest.raises(run.FrontmatterError):
        run.extract_frontmatter(broken)


def test_no_opening_fence_raises():
    with pytest.raises(run.FrontmatterError):
        run.extract_frontmatter("# just markdown\nno frontmatter here\n")


def test_malformed_yaml_raises_with_the_parsers_reason():
    with pytest.raises(run.FrontmatterError) as excinfo:
        run.parse_frontmatter("name: [unclosed\n")
    assert str(excinfo.value)  # the parser's own message, not a generic one


def test_frontmatter_that_is_not_a_mapping_raises():
    with pytest.raises(run.FrontmatterError):
        run.parse_frontmatter("- just\n- a list\n")


@pytest.mark.parametrize(
    "source,expected",
    [
        ("platforms: [linux, macos]", {"platforms": ["linux", "macos"]}),
        ("name: my-tool  # the tool", {"name": "my-tool"}),
        ('description: "a: b"', {"description": "a: b"}),
        ("platforms: []", {"platforms": []}),
        ("requires: [{name: incus, purpose: p, install: docs/i.md}]",
         {"requires": [{"name": "incus", "purpose": "p", "install": "docs/i.md"}]}),
    ],
)
def test_yaml_constructs_are_understood(source, expected):
    """Flow sequences, inline comments, and quoted colons mean what YAML says."""
    assert run.parse_frontmatter(source) == expected


def test_literal_block_keeps_its_newlines():
    data = run.parse_frontmatter("description: |\n  line one\n  line two\n")
    assert data["description"] == "line one\nline two\n"


def _problems(**overrides) -> dict[str, list[str]]:
    fm = _fm()
    for key, value in overrides.items():
        if value is run:  # sentinel: delete the field
            fm.pop(key, None)
        else:
            fm[key] = value
    return run.validate_manifest(fm)


def test_a_valid_manifest_has_no_problems():
    assert all(not v for v in _problems().values())


def test_unknown_field_is_a_closed_set_problem():
    problems = _problems(author="nobody")
    assert problems["manifest-fields-closed"] == ["author"]
    assert not problems["manifest-required-fields"]


def test_absent_field_is_a_required_field_problem():
    problems = _problems(version=run)
    assert any("version" in p for p in problems["manifest-required-fields"])


@pytest.mark.parametrize("field,empty", [("name", "  "), ("use_cases", []), ("platforms", [])])
def test_present_but_empty_is_a_required_field_problem(field, empty):
    problems = _problems(**{field: empty})
    assert any(field in p for p in problems["manifest-required-fields"]), problems


def test_wrong_shape_is_a_shape_problem():
    problems = _problems(platforms="linux")
    assert any("platforms" in p for p in problems["manifest-field-shapes"])
    assert not problems["manifest-required-fields"]


def test_requires_defects_are_reported_against_requires():
    problems = _problems(requires=[{"name": "incus", "purpose": "p"}])
    assert any("install" in p for p in problems["manifest-requires-shape"])
    assert not problems["manifest-required-fields"]


def test_requires_may_be_omitted():
    assert not any(_problems(requires=run).values())


@pytest.mark.parametrize(
    "value,is_command",
    [
        ("README.md", False),
        ("docs/installing.md", False),
        ("https://example.test/guide", False),
        ("pip install foo", True),
        ("sudo apt-get install foo", True),
        ("curl https://x | sh", True),
        ("run this then that", True),  # bare prose with spaces
    ],
)
def test_install_command_detection(value, is_command):
    assert (run._install_command_reason(value) is not None) == is_command
