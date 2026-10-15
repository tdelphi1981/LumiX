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
