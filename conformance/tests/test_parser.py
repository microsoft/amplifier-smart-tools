"""Unit tests for the stdlib manifest frontmatter parser and helpers in run.py."""

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


def test_extract_and_parse_roundtrip():
    data = run.parse_frontmatter(run.extract_frontmatter(GOOD_MANIFEST))
    assert data["smart_tool_format"] == 1
    assert data["name"] == "my-tool"
    assert data["version"] == "1.2.3"  # dotted version stays a string
    assert data["description"] == (
        "A folded description that spans two source lines but is one string."
    )
    assert data["use_cases"] == ["Do a thing", "Do another thing"]
    assert data["platforms"] == ["linux"]


def test_requires_is_list_of_mappings_with_types():
    data = run.parse_frontmatter(run.extract_frontmatter(GOOD_MANIFEST))
    req = data["requires"]
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


def test_scalar_typing():
    assert run._scalar("1") == 1
    assert run._scalar("true") is True
    assert run._scalar("false") is False
    assert run._scalar("0.1.0") == "0.1.0"
    assert run._scalar('"quoted"') == "quoted"


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
