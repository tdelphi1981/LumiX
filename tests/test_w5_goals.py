"""W5 goal programming regressions (catalog A21, A22, A25, A26) and the W3/W4 carry-over."""
import copy
import itertools
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from solver_matrix import AVAILABLE, solve_with  # noqa: E402
from test_canonical import fam  # noqa: E402

from lumix import (LXConstraint, LXLinearExpression, LXModel, LXNonLinearExpression,
                   LXOptimizer, LXVariable)
from lumix.core.enums import LXConstraintSense, LXObjectiveSense


def lin(*pairs, const=0.0):
    e = LXLinearExpression()
    for v, c in pairs:
        e.add_term(v, c)
    return e.add_constant(const) if const else e


def hard(name, expr, sense, rhs):
    c = LXConstraint(name).expression(expr)
    return {"<=": c.le, ">=": c.ge, "==": c.eq}[sense]().rhs(rhs)


def goal(name, expr, sense, rhs, priority, weight=1.0):
    return hard(name, expr, sense, rhs).as_goal(priority=priority, weight=weight)


def positions(canon):
    return {(v.family, v.key): i for i, v in enumerate(canon.variables)}


# --- Görev 1: indexed goals get their own deviations (A22) -------------------------
@dataclass(frozen=True)
class Prod:
    id: str
    target: float


PRODS = [Prod("A", 10.0), Prod("B", 20.0)]


def _demand_model(products=PRODS):
    x = (LXVariable[Prod, float]("x").continuous().bounds(lower=0, upper=100)
         .indexed_by(lambda p: p.id).from_data(products))
    m = LXModel("idx").add_variable(x)
    m.add_constraint(hard("capA", LXLinearExpression().add_term(x, 1.0, keys=["A"]), "<=", 5))
    m.add_constraint(hard("total", lin((x, 1.0)), "<=", 25))
    m.add_constraint(LXConstraint[Prod]("demand").expression(lin((x, 1.0))).ge()
                     .rhs(lambda p: p.target).indexed_by(lambda p: p.id).from_data(products)
                     .as_goal(priority=1))
    return m


@pytest.mark.parametrize("solver", AVAILABLE)
def test_a22_indexed_goal_rows_have_their_own_deviations(solver):
    m = _demand_model()
    m.prepare_goal_programming()
    s = solve_with(solver, m)
    assert s.variables["x"] == pytest.approx({"A": 5.0, "B": 20.0})
    assert s.get_goal_deviations("demand")["neg"] == pytest.approx({"demand_A": 5.0, "demand_B": 0.0})


def test_a22_relaxed_rows_reference_only_their_own_deviation():
    m = _demand_model()
    m.prepare_goal_programming()
    c = m.to_canonical()
    pos = positions(c)
    rows = {r.name: r.coeffs for r in c.rows}
    assert rows["demand[A]"] == {pos[("x", "A")]: 1.0, pos[("demand_neg_dev", "demand_A")]: 1.0,
                                 pos[("demand_pos_dev", "demand_A")]: -1.0}


def test_a22_indexed_goal_build_is_linear_in_rows():
    items = [Prod(str(i), 1.0) for i in range(2000)]
    m = _demand_model(items)
    m.prepare_goal_programming()
    start = time.perf_counter()
    c = m.to_canonical()
    elapsed = time.perf_counter() - start
    goal_rows = [r for r in c.rows if r.family == "demand"]
    assert sum(len(r.coeffs) for r in goal_rows) == 3 * 2000
    assert elapsed < 2.0


def test_a22_row_filter_called_without_a_row_keeps_every_instance():
    # lumix-sezgi calls where(instance) with the instance only and lets the
    # two-argument coefficient select the row's own deviation.
    m = _demand_model()
    m.prepare_goal_programming()
    row = next(c for c in m.constraints if c.name == "demand")
    var, coeff, where = next(t for t in row.lhs.terms.values() if t[0].name == "demand_neg_dev")
    goals = var.get_instances()
    assert all(where(g) for g in goals)
    assert [coeff(g, PRODS[1]) for g in goals] == [0.0, 1.0]


@pytest.mark.parametrize("solver", AVAILABLE)
def test_goal_with_a_nonlinear_expression(solver):
    x = fam("x", ["k"], lower=-5, upper=5)
    m = LXModel("m").add_variable(x)
    m.add_constraint(hard("lo", lin((x, 1.0)), "<=", 1))
    m.add_constraint(goal("absgoal", LXNonLinearExpression().add_abs(x), ">=", 4, priority=1))
    m.prepare_goal_programming()
    s = LXOptimizer().use_solver(solver).enable_linearization().solve(m)
    assert s.status == "optimal"
    assert s.get_goal_deviations("absgoal")["neg"] == pytest.approx({"absgoal": 0.0})
    assert s.variables["x"]["k"] <= -4 + 1e-6


@pytest.mark.parametrize("solver", AVAILABLE)
def test_a22_indexed_nonlinear_goal(solver):
    x = (LXVariable[Prod, float]("x").continuous().bounds(lower=-30, upper=30)
         .indexed_by(lambda p: p.id).from_data(PRODS))
    m = LXModel("m").add_variable(x)
    m.add_constraint(hard("capA", LXLinearExpression().add_term(x, 1.0, keys=["A"]), "<=", 2))
    m.add_constraint(hard("capA2", LXLinearExpression().add_term(x, 1.0, keys=["A"]), ">=", -3))
    m.add_constraint(LXConstraint[Prod]("far").expression(LXNonLinearExpression().add_abs(x))
                     .ge().rhs(lambda p: p.target).indexed_by(lambda p: p.id).from_data(PRODS)
                     .as_goal(priority=1))
    m.prepare_goal_programming()
    s = LXOptimizer().use_solver(solver).enable_linearization().solve(m)
    assert s.get_goal_deviations("far")["neg"] == pytest.approx({"far_A": 7.0, "far_B": 0.0})


# --- Görev 2: goals are prepared by solve and to_canonical (A26) -------------------
def _cap_goal():
    x = fam("x", ["k"], lower=0)
    m = LXModel("m").add_variable(x)
    m.add_constraint(hard("cap", lin((x, 1.0)), "<=", 5))
    m.add_constraint(goal("g", lin((x, 1.0)), ">=", 8, priority=1))
    return m


@pytest.mark.parametrize("solver", AVAILABLE)
def test_a26_goals_are_prepared_by_solve(solver):
    s = solve_with(solver, _cap_goal())
    assert s.status == "optimal" and s.variables["x"]["k"] == pytest.approx(5)
    assert s.get_goal_deviations("g")["neg"] == pytest.approx({"g": 3.0})


def test_a26_solve_and_to_canonical_leave_the_model_unchanged():
    m = _cap_goal()
    before = (list(m.variables), list(m.constraints), m.objective_expr, m.goal_mode)
    LXOptimizer().use_solver("ortools").solve(m)
    m.to_canonical()
    assert (list(m.variables), list(m.constraints), m.objective_expr, m.goal_mode) == before
    assert m.has_goals() and not m._goal_programming_prepared


def test_a26_to_canonical_relaxes_goals():
    c = _cap_goal().to_canonical()
    assert {v.family for v in c.variables} == {"x", "g_pos_dev", "g_neg_dev"}
    assert [r.name for r in c.rows] == ["cap", "g"]
    assert c.rows[1].sense == LXConstraintSense.EQ
    assert c.sense == LXObjectiveSense.MINIMIZE and len(c.objective) == 1


def test_a26_explicit_prepare_still_works():
    m = _cap_goal()
    m.prepare_goal_programming()
    opt = LXOptimizer().use_solver("ortools")
    values = [opt.solve(m).objective_value, opt.solve(m).objective_value,
              opt.solve(copy.deepcopy(m)).objective_value]
    assert values == pytest.approx([3e6, 3e6, 3e6])
    assert opt.solve(m).get_goal_deviations("g")["neg"] == pytest.approx({"g": 3.0})


# --- Görev 3: priority 0 goals and the user's objective (A25) ----------------------
@pytest.mark.parametrize("solver", AVAILABLE)
def test_a25_priority_zero_goal_is_optimized(solver):
    x = fam("x", ["k"], lower=0, upper=10)
    m = LXModel("m").add_variable(x)
    m.add_constraint(goal("profit", lin((x, 3.0)), ">=", 0, priority=0))
    m.add_constraint(goal("g", lin((x, 1.0)), "<=", 4, priority=1))
    s = solve_with(solver, m)
    assert s.variables["x"]["k"] == pytest.approx(4)
    assert s.get_goal_deviations("profit") is None


@pytest.mark.parametrize("sense,expected", [("max", 4.0), ("min", 2.0)])
def test_a25_user_objective_is_the_lowest_priority(sense, expected):
    x = fam("x", ["k"], lower=0, upper=10)
    m = LXModel("m").add_variable(x)
    m.add_constraint(goal("hi", lin((x, 1.0)), "<=", 4, priority=1))
    m.add_constraint(goal("lo", lin((x, 1.0)), ">=", 2, priority=1))
    m.maximize(lin((x, 1.0))) if sense == "max" else m.minimize(lin((x, 1.0)))
    s = solve_with("ortools", m)
    assert s.variables["x"]["k"] == pytest.approx(expected)


def test_a25_cost_objective_with_goals():
    g = fam("g", ["k"], "integer", 0, 10).cost(lambda k: -1.0)
    m = LXModel("m").add_variable(g).minimize()
    m.add_constraint(goal("cap", lin((g, 1.0)), "<=", 3, priority=1))
    s = solve_with("ortools", m)
    assert s.variables["g"]["k"] == pytest.approx(3)


def test_a25_user_objective_and_priority_zero_goal_combine():
    x, y = fam("x", ["k"], lower=0, upper=10), fam("y", ["k"], lower=0, upper=10)
    m = LXModel("m").add_variables(x, y).maximize(lin((x, 1.0)))
    m.add_constraint(hard("cap", lin((x, 1.0), (y, 1.0)), "<=", 10))
    m.add_constraint(goal("prefer_y", lin((y, 2.0)), ">=", 0, priority=0))
    s = solve_with("ortools", m)
    assert (s.variables["x"]["k"], s.variables["y"]["k"]) == pytest.approx((0, 10))


@pytest.mark.parametrize("build,match", [
    (lambda x: goal("p0", lin((x, 1.0)), "==", 3, priority=0), "Priority 0"),
    (lambda x: (LXConstraint[str]("p0").expression(lin((x, 1.0))).ge().rhs(0)
                .indexed_by(lambda k: k).from_data(["k"]).as_goal(priority=0)), "indexed"),
    (lambda x: goal("neg", lin((x, 1.0)), ">=", 3, priority=-1), "priority")])
def test_a25_invalid_custom_goals_raise(build, match):
    x = fam("x", ["k"], lower=0, upper=10)
    m = LXModel("m").add_variable(x)
    m.add_constraint(goal("g", lin((x, 1.0)), "<=", 4, priority=1))
    m.add_constraint(build(x))
    with pytest.raises(ValueError, match=match):
        solve_with("ortools", m)


def test_a25_nonlinear_objective_with_goals_raises():
    x = fam("x", ["k"], lower=-5, upper=5)
    m = LXModel("m").add_variable(x).minimize(LXNonLinearExpression().add_abs(x))
    m.add_constraint(goal("g", lin((x, 1.0)), ">=", 2, priority=1))
    with pytest.raises(ValueError, match="nonlinear objective"):
        m.to_canonical()


def test_a25_quadratic_objective_with_goals():
    from lumix import LXQuadraticExpression
    solvers = [s for s in ("gurobi", "cplex") if s in AVAILABLE]
    if not solvers:
        pytest.skip("needs gurobi or cplex")
    x = fam("x", ["k"], lower=0, upper=10)
    m = LXModel("m").add_variable(x).minimize(LXQuadraticExpression().add_squared(x, 1.0))
    m.add_constraint(goal("g", lin((x, 1.0)), ">=", 3, priority=1))
    for solver in solvers:
        assert solve_with(solver, m).variables["x"]["k"] == pytest.approx(3, abs=1e-5)


# --- Görev 4: sequential goal programming is lexicographic (A21) -------------------
def _lex_model(scale=1.0):
    x, y = fam("x", ["k"], lower=0), fam("y", ["k"], lower=0)
    m = LXModel("seq").add_variables(x, y)
    m.add_constraint(hard("cap", lin((x, 1.0), (y, 1.0)), "<=", 10))
    m.add_constraint(goal("gx", lin((x, 1.0)), ">=", 8, priority=1))
    m.add_constraint(goal("gy", lin((y, scale)), ">=", 8 * scale, priority=2))
    return m.set_goal_mode("sequential")


@pytest.mark.parametrize("solver", AVAILABLE)
def test_a21_sequential_is_lexicographic(solver):
    s = solve_with(solver, _lex_model())
    assert s.status == "optimal"
    assert (s.variables["x"]["k"], s.variables["y"]["k"]) == pytest.approx((8, 2))
    assert [(st.priority, st.status) for st in s.goal_stages] == [(1, "optimal"), (2, "optimal")]
    assert [st.objective_value for st in s.goal_stages] == pytest.approx([0, 6])
    assert s.get_goal_deviations("gy")["neg"] == pytest.approx({"gy": 6.0})


def test_a21_sequential_differs_from_weighted_when_scales_differ():
    m = _lex_model(scale=20.0)
    seq = solve_with("ortools", m)
    weighted = solve_with("ortools", copy.copy(m).set_goal_mode("weighted"))
    assert seq.variables["x"]["k"] == pytest.approx(8)
    # Weighted: one unit of y removes 20 units of gy's deviation (2e6) against 1e6 for
    # a unit of x, so y takes its target 8 and x the rest: x = 2.
    assert weighted.variables["x"]["k"] == pytest.approx(2)


def test_a21_mode_can_change_between_solves():
    m = _lex_model(scale=20.0)
    assert solve_with("ortools", m).variables["x"]["k"] == pytest.approx(8)
    m.set_goal_mode("weighted")
    assert solve_with("ortools", m).variables["x"]["k"] == pytest.approx(2)
    m.set_goal_mode("sequential")
    assert solve_with("ortools", m).variables["x"]["k"] == pytest.approx(8)


def test_a21_weights_within_a_priority():
    x, y = fam("x", ["k"], lower=0), fam("y", ["k"], lower=0)
    m = LXModel("w").add_variables(x, y).set_goal_mode("sequential")
    m.add_constraint(hard("cap", lin((x, 1.0), (y, 1.0)), "<=", 10))
    m.add_constraint(goal("gx", lin((x, 1.0)), ">=", 8, priority=1, weight=1.0))
    m.add_constraint(goal("gy", lin((y, 1.0)), ">=", 8, priority=1, weight=3.0))
    s = solve_with("ortools", m)
    assert (s.variables["x"]["k"], s.variables["y"]["k"]) == pytest.approx((2, 8))


@pytest.mark.parametrize("sense,expected", [("max", 4.0), ("min", 2.0)])
def test_a21_user_objective_is_the_last_stage(sense, expected):
    x = fam("x", ["k"], lower=0, upper=10)
    m = LXModel("m").add_variable(x).set_goal_mode("sequential")
    m.add_constraint(goal("hi", lin((x, 1.0)), "<=", 4, priority=1))
    m.add_constraint(goal("lo", lin((x, 1.0)), ">=", 2, priority=2))
    m.maximize(lin((x, 1.0))) if sense == "max" else m.minimize(lin((x, 1.0)))
    s = solve_with("ortools", m)
    assert s.variables["x"]["k"] == pytest.approx(expected)
    assert [st.priority for st in s.goal_stages] == [1, 2, 0]
    assert s.objective_value == pytest.approx(expected)


def test_a21_infeasible_stage_stops():
    x = fam("x", ["k"], lower=0)
    m = LXModel("m").add_variable(x).set_goal_mode("sequential")
    m.add_constraint(hard("neg", lin((x, 1.0)), "<=", -1))
    m.add_constraint(goal("g", lin((x, 1.0)), ">=", 2, priority=1))
    m.add_constraint(goal("h", lin((x, 1.0)), "<=", 9, priority=2))
    s = solve_with("ortools", m)
    assert s.status == "infeasible"
    assert [(st.priority, st.status) for st in s.goal_stages] == [(1, "infeasible")]


def test_a21_sequential_leaves_the_model_unchanged():
    m = _lex_model()
    m.maximize(lin((m.variables[0], 1.0)))
    before = (m.objective_expr, m.objective_sense, list(m.constraints), list(m.variables))
    solve_with("ortools", m)
    assert (m.objective_expr, m.objective_sense, list(m.constraints), list(m.variables)) == before


def test_a21_solve_goal_programming_sequential():
    from lumix import LXGoalMode, solve_goal_programming
    m = _lex_model(scale=20.0).set_goal_mode("weighted")
    s = solve_goal_programming(m, LXOptimizer().use_solver("ortools"), mode=LXGoalMode.SEQUENTIAL)
    assert s.variables["x"]["k"] == pytest.approx(8)
    assert m.goal_mode == "weighted"


def test_canonical_goal_stages():
    c = _lex_model().to_canonical()
    pos = positions(c)
    assert c.goal_stages == ({pos[("gx_neg_dev", "gx")]: 1.0}, {pos[("gy_neg_dev", "gy")]: 1.0})
    assert c.objective == {}
    assert _lex_model().set_goal_mode("weighted").to_canonical().goal_stages == ()
