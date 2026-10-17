"""W7: README and documentation snippets (B17), includes, imports."""
import ast
import contextlib
import importlib
import io
import logging
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "source"

README_PRELUDE = '''
from dataclasses import dataclass
from typing import Tuple
from lumix import *
# data the README fragments assume the reader has
@dataclass(frozen=True)
class Driver: id: int
@dataclass(frozen=True)
class Date: id: int
@dataclass(frozen=True)
class Shift: id: int
drivers, dates, shifts = [Driver(1)], [Date(1)], [Shift(1)]
capacity = 100
for p in products: p.usage = p.resource_usage
x = LXVariable("x").continuous().bounds(lower=-5, upper=10)
y = LXVariable("y").continuous().bounds(lower=0, upper=5)
model.add_variable(x).add_variable(y)
profit_expr = LXLinearExpression().add_term(production, lambda p: p.profit)
quality_expr = LXLinearExpression().add_term(production, 1.0)
sensitivity_analyzer = LXSensitivityAnalyzer(model, solution)
'''


def _readme_blocks():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    return re.findall(r"`{3}python\n(.*?)`{3}", text, re.S)


def _run_statements(src, ns):
    tree = ast.parse(src)
    for node in tree.body:
        exec(compile(ast.Module([node], []), "README.md", "exec"), ns)


def test_b17_readme_blocks_run(tmp_path, monkeypatch):
    logging.disable(logging.CRITICAL)
    monkeypatch.chdir(tmp_path)
    try:
        import plotly.basedatatypes as pbd
        monkeypatch.setattr(pbd.BaseFigure, "show", lambda self, *a, **k: None)
        has_plotly = True
    except ImportError:
        has_plotly = False
    blocks = _readme_blocks()
    first = blocks[0]                       # the "Simple Example": a complete program
    failures = []
    for i, block in enumerate(blocks[1:], start=1):
        if block.lstrip().startswith("# Manual indexing"):
            continue                        # the "without LumiX" comparison, not LumiX code
        if "lumix.visualization" in block and not has_plotly:
            continue
        ns = {}
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(first, "README.md", "exec"), ns)
            exec(README_PRELUDE, ns)
            try:
                _run_statements(block, ns)
            except Exception as e:  # noqa: BLE001 - report every failing block
                failures.append(f"block {i}: {type(e).__name__}: {e}")
    logging.disable(logging.NOTSET)
    assert failures == []


_IMPORT = re.compile(r"from\s+(lumix[\w\.]*)\s+import\s+(\([^)]*\)|[^\n]+)")


def test_b17_documented_imports_resolve():
    files = [ROOT / "README.md", *DOCS.rglob("*.rst"), *ROOT.glob("examples/**/README.md")]
    bad = set()
    for f in files:
        for m in _IMPORT.finditer(f.read_text(encoding="utf-8", errors="ignore")):
            mod, names = m.group(1), m.group(2)
            names = [n.strip().split(" as ")[0].strip()
                     for n in names.strip("()").replace("\n", ",").split(",")]
            try:
                module = importlib.import_module(mod)
            except ImportError as e:
                if "extra" in str(e):        # optional dependency not installed
                    continue
                bad.add(f"{f.relative_to(ROOT)}: module {mod}")
                continue
            for n in names:
                if not re.fullmatch(r"[A-Za-z_]\w*", n):
                    continue
                if not hasattr(module, n):
                    try:
                        importlib.import_module(f"{mod}.{n}")
                    except ImportError:
                        bad.add(f"{f.relative_to(ROOT)}: {mod}.{n}")
    assert sorted(bad) == []


def _includes():
    directive = re.compile(r"^\s*\.\.\s+literalinclude::\s*(\S+)")
    option = re.compile(r"^\s+:([a-z-]+):\s*(.*)$")
    for rst in DOCS.rglob("*.rst"):
        lines = rst.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            m = directive.match(line)
            if not m:
                continue
            opts = {}
            for follow in lines[i + 1:]:
                o = option.match(follow)
                if not o:
                    break
                opts[o.group(1)] = o.group(2).strip()
            yield rst, i + 1, (rst.parent / m.group(1)).resolve(), opts


def test_w7_includes_use_markers_not_line_numbers():
    with_lines = [f"{rst.relative_to(DOCS)}:{n}" for rst, n, _t, opts in _includes() if "lines" in opts]
    assert with_lines == []


def test_w7_include_markers_exist_and_select_code():
    problems = []
    for rst, n, target, opts in _includes():
        if not target.exists():
            problems.append(f"{rst.relative_to(DOCS)}:{n} missing {target.name}")
            continue
        text = target.read_text(encoding="utf-8")
        for key in ("start-after", "end-before"):
            if key in opts and opts[key] not in text:
                problems.append(f"{rst.relative_to(DOCS)}:{n} {key} {opts[key]!r} not in {target.name}")
        if "start-after" in opts and "end-before" in opts and opts["start-after"] in text:
            body = text.split(opts["start-after"], 1)[1].split(opts["end-before"], 1)[0]
            if not body.strip():
                problems.append(f"{rst.relative_to(DOCS)}:{n} selects nothing")
            elif '"""' in body and target.suffix == ".py" and body.count('"""') % 2:
                problems.append(f"{rst.relative_to(DOCS)}:{n} cuts a docstring")
    assert problems == []


def test_version_is_0_3_1():
    import lumix

    assert lumix.__version__ == "0.3.1"


def test_w7_changelog_has_a_0_3_0_section():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    section = text.split("## [0.3.0]", 1)[1].split("\n## [", 1)[0]
    for heading in ("### Added", "### Fixed", "### Behavior changes", "### Deprecated"):
        assert heading in section, heading
    assert "### Changed" not in section
    for catalog_id in ("A1:", "A26:", "B13:", "B14:", "B16:", "B17:"):
        assert catalog_id in section, catalog_id
