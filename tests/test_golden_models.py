"""
Golden-model tests: the OR-Tools model built for examples 01-05 must not change.

The LP text of each example model was recorded before the 0.2.0 build changes
(instance cache, keyed terms). Regenerate only for an intended change:
``LUMIX_REGEN_GOLDEN=1 pytest tests/test_golden_models.py``.
"""

import importlib.util
import os
import sys
from pathlib import Path

import pytest

pytest.importorskip("ortools")

from lumix.solvers.ortools_solver import LXORToolsSolver

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = Path(__file__).parent / "golden"
EXAMPLES = {
    "01_production_planning": ("production_planning.py", "build_production_model"),
    "02_driver_scheduling": ("driver_scheduling.py", "build_scheduling_model"),
    "03_facility_location": ("facility_location.py", "build_facility_location_model"),
    "04_basic_lp": ("basic_lp.py", "build_diet_model"),
    "05_cpsat_assignment": ("cpsat_assignment.py", "build_assignment_model"),
}


def _build(example: str):
    folder = ROOT / "examples" / example
    script, builder = EXAMPLES[example]
    sys.modules.pop("sample_data", None)  # every example ships its own sample_data
    sys.path.insert(0, str(folder))
    try:
        spec = importlib.util.spec_from_file_location(f"golden_{example}", folder / script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        built = getattr(module, builder)()
    finally:
        sys.path.remove(str(folder))
        sys.modules.pop("sample_data", None)
    return built[0] if isinstance(built, tuple) else built


@pytest.mark.parametrize("example", sorted(EXAMPLES))
def test_example_model_is_unchanged(example):
    lp = LXORToolsSolver().build_model(_build(example)).ExportModelAsLpFormat(False)
    path = GOLDEN / f"{example}.lp"
    if os.environ.get("LUMIX_REGEN_GOLDEN"):
        GOLDEN.mkdir(exist_ok=True)
        path.write_text(lp, encoding="utf-8")
    assert path.exists(), f"missing golden file {path.name}; run with LUMIX_REGEN_GOLDEN=1"
    assert lp == path.read_text(encoding="utf-8")
