"""W1 adapter regressions (catalog A1-A5, A7, A8, B1, B2, B4, B10)."""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from solver_matrix import AVAILABLE, solve_with  # noqa: E402
from test_canonical import fam, inventory_model  # noqa: E402

from lumix import LXConstraint, LXLinearExpression, LXModel, LXVariable

SOLVERS = pytest.mark.parametrize("solver", AVAILABLE)


def lhs_constant_model():
    x = fam("x", ["k"], lower=0, upper=100)
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint("c").expression(LXLinearExpression().add_term(x, 1.0).add_constant(5)).le().rhs(8))
    m.maximize(LXLinearExpression().add_term(x, 1.0).add_constant(10))
    return m


@SOLVERS
def test_a1_constraint_lhs_constant(solver):
    s = solve_with(solver, lhs_constant_model())
    assert s.status == "optimal" and s.objective_value == pytest.approx(13)


@SOLVERS
def test_a2_repeated_terms_sum(solver):
    x = fam("x", ["k"], lower=0, upper=100)
    m = LXModel("m").add_variable(x)
    row = LXLinearExpression().add_term(x, 4.0) + LXLinearExpression().add_multi_term(x, coeff=lambda k: 1.0)
    m.add_constraint(LXConstraint("c").expression(row).le().rhs(10))
    m.maximize(LXLinearExpression().add_term(x, 3.0) + LXLinearExpression().add_multi_term(x, coeff=lambda k: -1.0))
    s = solve_with(solver, m)
    assert s.objective_value == pytest.approx(4.0) and s.variables["x"]["k"] == pytest.approx(2.0)


@SOLVERS
def test_a3_bounds_respected(solver):
    b = fam("b", ["k"], "binary", 0, 0)
    n = fam("n", ["k"], "integer", 0.5, 3.7)
    m = LXModel("m").add_variables(b, n)
    m.minimize(LXLinearExpression().add_term(b, -1.0).add_term(n, 1.0))
    s = solve_with(solver, m)
    assert s.variables["b"]["k"] == pytest.approx(0) and s.variables["n"]["k"] == pytest.approx(1)


@SOLVERS
def test_a4_empty_family_solves(solver):
    x = fam("x", [], lower=0, upper=10)
    y = fam("y", ["k"], lower=0, upper=5)
    m = LXModel("m").add_variables(x, y)
    m.maximize(LXLinearExpression().add_term(x, 1.0).add_term(y, 1.0))
    s = solve_with(solver, m)
    assert s.status == "optimal" and s.objective_value == pytest.approx(5)
    assert s.variables["x"] == {}


@SOLVERS
def test_a5_inventory_balance(solver):
    s = solve_with(solver, inventory_model())
    assert s.status == "optimal" and s.objective_value == pytest.approx(12)
    assert s.variables["inv"] == pytest.approx({1: 8.0, 2: 4.0, 3: 0.0})


@SOLVERS
def test_b1_integer_with_open_bound(solver):
    y = fam("y", ["k"], "integer", 0, None)
    m = LXModel("m").add_variable(y)
    m.add_constraint(LXConstraint("c").expression(LXLinearExpression().add_term(y, 1.0)).ge().rhs(3))
    m.minimize(LXLinearExpression().add_term(y, 1.0))
    s = solve_with(solver, m)
    assert s.status == "optimal" and s.objective_value == pytest.approx(3)


def test_b2_ortools_applies_gap_and_threads():
    from lumix.solvers.ortools_solver import LXORToolsSolver
    from ortools.linear_solver import pywraplp

    params = LXORToolsSolver._solver_parameters(0.25)
    assert params.GetDoubleParam(pywraplp.MPSolverParameters.RELATIVE_MIP_GAP) == pytest.approx(0.25)
    s = solve_with("ortools", lhs_constant_model(), threads=2)
    assert s.status == "optimal"


def test_b2_ortools_warns_on_unknown_parameter(caplog):
    import logging
    from lumix import LXOptimizer
    with caplog.at_level(logging.WARNING):
        LXOptimizer().use_solver("ortools").solve(lhs_constant_model(), no_such_param=1)
    assert "no_such_param" in caplog.text


def knapsack(n=30):
    import random
    rng = random.Random(3)
    items = [f"i{j}" for j in range(n)]
    w = {i: rng.randint(5, 40) for i in items}
    v = {i: rng.randint(5, 60) for i in items}
    x = fam("x", items, "binary")
    m = LXModel("knap").add_variable(x)
    m.add_constraint(LXConstraint("cap").expression(LXLinearExpression().add_term(x, lambda i: w[i])).le().rhs(200))
    m.maximize(LXLinearExpression().add_term(x, lambda i: v[i]))
    return m


def test_a7_gurobi_returns_incumbent_on_solution_limit():
    pytest.importorskip("gurobipy")
    s = solve_with("gurobi", knapsack(), SolutionLimit=1)
    assert s.status == "feasible"
    assert s.objective_value > 0 and len(s.variables["x"]) == 30


def test_gurobi_resolves_inf_or_unbounded():
    pytest.importorskip("gurobipy")
    # Gurobi's presolve answers INF_OR_UNBD (status 4) for this LP
    x = fam("x", ["k"], lower=0, upper=None)
    y = fam("y", ["k"], lower=0, upper=None)
    m = LXModel("m").add_variables(x, y)
    m.add_constraint(LXConstraint("c").expression(
        LXLinearExpression().add_term(x, 1.0).add_term(y, -1.0)).le().rhs(1))
    m.maximize(LXLinearExpression().add_term(x, 1.0).add_term(y, 1.0))
    assert solve_with("gurobi", m).status == "unbounded"
