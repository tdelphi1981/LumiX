"""W9 final review fixes (0.3.2)."""
import math

import numpy as np
import pytest

from lumix import LXConstraint, LXLinearExpression, LXModel, LXOptimizer, LXVariable
from tests.solver_matrix import solve_with


def _cpsat(m, **kw):
    return LXOptimizer().use_solver("cpsat", **kw).enable_rational_conversion().solve(m)


def test_w9_cpsat_continuous_optimum_past_the_cap_is_not_unbounded():
    x = LXVariable[None, float]("x").continuous().bounds(0, None)
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint("c").expression(
        LXLinearExpression().add_term(x, 1.0)).le().rhs(5e9))
    assert _cpsat(m.maximize(LXLinearExpression().add_term(x, 1.0))).status != "unbounded"


def test_w9_cpsat_finite_bound_past_the_cap_is_not_unbounded():
    x = LXVariable[None, int]("x").integer().bounds(0, 1e13)
    m = LXModel("m").add_variable(x).maximize(LXLinearExpression().add_term(x, 1.0))
    assert solve_with("cpsat", m).status != "unbounded"


def test_w9_cpsat_row_bound_past_the_cap_is_not_unbounded():
    x = LXVariable[None, int]("x").integer().bounds(0, None)
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint("c").expression(
        LXLinearExpression().add_term(x, 1.0)).le().rhs(1e13))
    assert solve_with("cpsat", m.maximize(LXLinearExpression().add_term(x, 1.0))).status \
        != "unbounded"


def test_w9_numpy_rows_still_narrow_by_value():
    x = LXVariable[int, float]("x").continuous().bounds(0, 1) \
        .indexed_by(lambda k: k).from_data([1, 2, 3])
    c = (LXConstraint[int]("cap").expression(LXLinearExpression().add_term(x, 1.0))
         .le().rhs(1).from_data(list(np.array([1, 2, 3]))).indexed_by(lambda r: int(r)))
    canon = LXModel("m").add_variable(x).add_constraint(c).to_canonical()
    assert [r.coeffs for r in canon.rows] == [{0: 1.0}, {1: 1.0}, {2: 1.0}]


def test_w9_binary_at_one_is_at_bound():
    from lumix.analysis.sensitivity import LXSensitivityAnalyzer
    b = LXVariable[None, int]("b").binary()
    m = LXModel("m").add_variable(b).maximize(LXLinearExpression().add_term(b, 1.0))
    s = LXOptimizer().use_solver("ortools").solve(m)
    assert LXSensitivityAnalyzer(m, s).analyze_variable("b").is_at_bound


def test_w9_pct_change_snaps_noise_so_no_minus_zero_is_printed():
    from lumix.analysis._change import pct_change
    assert f"{pct_change(100.0 - 1e-12, 100.0):+.1f}%" == "+0.0%"


@pytest.mark.parametrize("bad", [0, -5, 0.5])
def test_w9_cpsat_scaling_factor_below_one_raises(bad):
    x = LXVariable[None, float]("x").continuous().bounds(0, 1)
    m = LXModel("m").add_variable(x).maximize(LXLinearExpression().add_term(x, 1.0))
    with pytest.raises(ValueError, match="scaling_factor"):
        _cpsat(m, scaling_factor=bad)


def test_w9_changelog_lists_every_behavior_change():
    from pathlib import Path
    text = (Path(__file__).resolve().parents[1] / "CHANGELOG.md").read_text()
    section = text.split("## [0.3.2]", 1)[1].split("\n## [", 1)[0]
    behavior = section.split("### Behavior changes", 1)[1]
    for needle in ("SCIP", "template", "height", "N/A", "threshold=", "custom(",
                   "pwl_num_segments", "is_at_bound"):
        assert needle in behavior, needle
