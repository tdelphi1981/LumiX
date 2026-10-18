"""W9a/W9b (0.3.2): goal programming."""
import pytest

from lumix import (LXConstraint, LXLinearExpression, LXModel, LXNonLinearExpression,
                   LXOptimizer, LXVariable, solve_goal_programming)
from lumix.core.enums import LXConstraintSense
from tests.solver_matrix import AVAILABLE, solve_with


def _two_goals():
    x = LXVariable[None, float]("x").continuous().bounds(0, 10)
    m = LXModel("m").add_variable(x)
    for name, sense, rhs, p in (("hi", "ge", 8, 1), ("lo", "le", 3, 2)):
        c = LXConstraint(name).expression(LXLinearExpression().add_term(x, 1.0))
        c = (c.ge() if sense == "ge" else c.le()).rhs(rhs).as_goal(priority=p)
        m.add_constraint(c)
    return m


def test_w9_mode_string_weighted_solves_weighted():
    s = solve_goal_programming(_two_goals(), LXOptimizer().use_solver("ortools"),
                               mode="weighted")
    assert not s.goal_stages          # weighted: one solve, no stages


def test_w9_mode_string_is_case_insensitive_and_checked():
    opt = LXOptimizer().use_solver("ortools")
    assert solve_goal_programming(_two_goals(), opt, mode="SEQUENTIAL").goal_stages
    with pytest.raises(ValueError, match="mode"):
        solve_goal_programming(_two_goals(), opt, mode="lexicographic")


def _abs_goal(sense):
    f = LXVariable[None, float]("f").continuous()          # free
    m = LXModel("m").add_variable(f).set_goal_mode("weighted")
    c = LXConstraint("g").expression(LXNonLinearExpression().add_abs(f))
    c = (c.le().rhs(3) if sense == "le" else c.ge().rhs(-1)).as_goal(priority=1)
    m.add_constraint(c)
    m.minimize(LXLinearExpression().add_term(f, -1.0))      # push f up against |f| <= 3
    return m


@pytest.mark.parametrize("solver", AVAILABLE)
def test_w9_le_goal_on_abs_of_a_free_variable_solves(solver):
    s = (LXOptimizer().use_solver(solver).enable_linearization()).solve(_abs_goal("le"))
    assert s.is_optimal()
    assert s.variables["f"] == pytest.approx(3.0, abs=1e-6)


def test_w9_one_sided_nonlinear_goal_row_and_fixed_deviation():
    # A row with |f| has no canonical form before linearization: inspect the relaxation.
    (rc,) = _abs_goal("le").prepare_goal_programming()._relaxed_constraints
    assert rc.constraint.sense == LXConstraintSense.LE
    assert (rc.neg_deviation.lower_bound, rc.neg_deviation.upper_bound) == (0.0, 0.0)
    assert (rc.pos_deviation.lower_bound, rc.pos_deviation.upper_bound) == (0.0, None)
    names = {var.name for var, _, _ in rc.constraint.lhs.linear_terms.terms.values()}
    assert names == {"g_pos_dev"}


def test_w9_linear_goals_keep_equality_rows():
    # Review Focus 2: linear goals are relaxed as before.
    canon = _two_goals().to_canonical()
    goal_rows = [r for r in canon.rows if r.family in ("hi", "lo")]
    assert [r.sense for r in goal_rows] == [LXConstraintSense.EQ] * 2
    for r in goal_rows:
        assert sorted(r.coeffs.values()) == [-1.0, 1.0, 1.0]


def test_w9_canonical_lists_goal_deviation_families():
    canon = _two_goals().to_canonical()
    assert canon.goal_deviations == (("hi", "hi_pos_dev", "hi_neg_dev"),
                                     ("lo", "lo_pos_dev", "lo_neg_dev"))
    assert canon.schema_version == 1


def test_w9_model_without_goals_has_no_goal_deviations():
    x = LXVariable[None, float]("x").continuous().bounds(0, 1)
    assert LXModel("m").add_variable(x).to_canonical().goal_deviations == ()


def test_w9_prepared_goal_model_lists_goal_deviations():
    m = _two_goals().prepare_goal_programming()
    assert len(m.to_canonical().goal_deviations) == 2
