"""The version string must be the same everywhere it is published."""

import re
from pathlib import Path

import lumix

ROOT = Path(__file__).resolve().parents[1]


def _match(path: str, pattern: str) -> str:
    text = (ROOT / path).read_text(encoding="utf-8")
    found = re.search(pattern, text, re.MULTILINE)
    assert found, f"no version in {path}"
    return found.group(1)


def test_version_is_consistent():
    expected = _match("pyproject.toml", r'^version = "([^"]+)"')
    assert lumix.__version__ == expected
    assert _match("CITATION.cff", r"^version: (\S+)") == expected
    assert _match("docs/source/conf.py", r'^release = "([^"]+)"') == expected
    assert _match("docs/source/conf.py", r'^version = "([^"]+)"') == expected
