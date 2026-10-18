"""W9c (0.3.2): docs outputs, example 04, release metadata."""
import subprocess
import sys
from pathlib import Path

import lumix

ROOT = Path(__file__).resolve().parents[1]


def test_w9_version_is_0_3_2():
    assert lumix.__version__ == "0.3.2"


def test_w9_changelog_has_a_0_3_2_section_with_behavior_changes():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    section = text.split("## [0.3.2]", 1)[1].split("\n## [", 1)[0]
    assert "### Fixed" in section and "### Behavior changes" in section


def test_w9_rational_doc_shows_the_real_outputs():
    text = (ROOT / "docs/source/user-guide/utils/rational-conversion.rst").read_text()
    assert "9563/3044" in text and "Fraction(355, 113)" not in text


def test_w9_quickstart_shows_the_optimal_plan():
    text = (ROOT / "docs/source/getting-started/quickstart.rst").read_text()
    assert "Produce 40.00 units of Product A" in text
    assert "Produce 20.00 units of Product B" in text


def test_w9_example_04_runs_on_ortools_and_exits_zero():
    out = subprocess.run([sys.executable, "examples/04_basic_lp/basic_lp.py"],
                         cwd=ROOT, capture_output=True, text=True, timeout=300,
                         env={"MPLBACKEND": "Agg", "LUMIX_NO_SHOW": "1",
                              **__import__("os").environ})
    assert out.returncode == 0, out.stdout + out.stderr
    assert "Total Cost" in out.stdout
