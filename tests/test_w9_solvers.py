"""W9a/W9b (0.3.2): CP-SAT and CPLEX adapters."""
import importlib.util

import pytest

from lumix import (LXConstraint, LXLinearExpression, LXModel, LXOptimizer,
                   LXQuadraticExpression, LXVariable)
from tests.solver_matrix import solve_with

HAS_CPLEX = importlib.util.find_spec("cplex") is not None


def _free_int_min():
    x = LXVariable[None, int]("x").integer()            # no bounds
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint("c").expression(
        LXLinearExpression().add_term(x, 1.0)).le().rhs(5))
    return m.minimize(LXLinearExpression().add_term(x, 1.0))


def test_w9_cpsat_unbounded_integer_model_is_unbounded():
    assert solve_with("cpsat", _free_int_min()).status == "unbounded"


def test_w9_cpsat_bounded_large_optimum_stays_optimal():
    # Review Focus 5: an optimum inside the open-bound box is not "unbounded".
    x = LXVariable[None, int]("x").integer()
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint("c").expression(
        LXLinearExpression().add_term(x, 1.0)).ge().rhs(-1_000_000))
    s = solve_with("cpsat", m.minimize(LXLinearExpression().add_term(x, 1.0)))
    assert s.status == "optimal" and s.objective_value == pytest.approx(-1e6)


def test_w9_cpsat_overflow_message_names_the_value():
    x = LXVariable[None, int]("x").integer().bounds(0, 10)
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint("cap").expression(
        LXLinearExpression().add_term(x, 1.0)).le().rhs(1e20))
    m.maximize(LXLinearExpression().add_term(x, 1.0))
    with pytest.raises(ValueError) as err:
        solve_with("cpsat", m)
    assert "common denominator" not in str(err.value)
    assert "64-bit" in str(err.value) and "'cap'" in str(err.value)


def test_w9_cpsat_scaling_factor_reaches_the_solver():
    x = LXVariable[None, float]("x").continuous().bounds(0, 1)
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint("c").expression(
        LXLinearExpression().add_term(x, 3.0)).eq().rhs(1))
    m.maximize(LXLinearExpression().add_term(x, 1.0))
    s = (LXOptimizer().use_solver("cpsat", scaling_factor=3)
         .enable_rational_conversion().solve(m))
    assert s.variables["x"] == pytest.approx(1 / 3)


def test_w9_cpsat_solve_docstring_states_the_real_default_gap():
    from lumix.solvers.cpsat_solver import LXCPSATSolver
    doc = LXCPSATSolver.solve.__doc__
    assert "None = 0.0001" not in doc and "relative 0" in doc


def _scip_unbounded_model():
    # W7 rescan lp-11: Gurobi/CPLEX/GLPK say unbounded; SCIP says optimal -1.97e19.
    v0 = LXVariable[None, int]("v0").integer()
    v1 = LXVariable[None, int]("v1").binary()
    v2 = LXVariable[None, int]("v2").integer()
    v3 = LXVariable[None, int]("v3").integer().bounds(-3, None)
    m = LXModel("m").add_variable(v0).add_variable(v1).add_variable(v2).add_variable(v3)
    E = LXLinearExpression
    for name, expr, sense, rhs in (
            ("c0", E().add_term(v0, 7).add_term(v1, 0.2).add_term(v2, 1.5).add_term(v3, 0.1), "le", 1),
            ("c1", E().add_term(v0, 0.2).add_term(v2, 0.5).add_term(v3, -2.5), "le", -6),
            ("c2", E().add_term(v1, 3).add_term(v2, 0.125), "ge", 10)):
        c = LXConstraint(name).expression(expr)
        m.add_constraint((c.le() if sense == "le" else c.ge()).rhs(rhs))
    return m.minimize(E().add_term(v0, -2.5).add_term(v1, 2).add_term(v2, 0.2).add_term(v3, -2.5))


def test_w9_scip_huge_optimum_is_unbounded():
    assert solve_with("ortools", _scip_unbounded_model()).status == "unbounded"


def test_w9_scip_large_but_sane_optimum_stays_optimal():
    x = LXVariable[None, int]("x").integer().bounds(-10**12, 10)
    m = LXModel("m").add_variable(x).minimize(LXLinearExpression().add_term(x, 1.0))
    s = solve_with("ortools", m)
    assert s.status == "optimal" and s.objective_value == pytest.approx(-1e12)


@pytest.mark.skipif(not HAS_CPLEX, reason="cplex not installed")
def test_w9_cplex_convex_qp_returns_duals():
    x = LXVariable[None, float]("x").continuous().bounds(0, 10)
    y = LXVariable[None, float]("y").continuous().bounds(0, 10)
    m = LXModel("m").add_variable(x).add_variable(y)
    m.add_constraint(LXConstraint("c").expression(
        LXLinearExpression().add_term(x, 1.0).add_term(y, 1.0)).le().rhs(3))
    q = LXQuadraticExpression().add_quadratic(x, x, 1.0).add_quadratic(y, y, 1.0)
    q.linear_terms.add_term(x, -4.0).add_term(y, -6.0)
    s = LXOptimizer().use_solver("cplex").enable_sensitivity().solve(m.minimize(q))
    assert s.is_optimal() and s.objective_value == pytest.approx(-11.0, abs=1e-6)
    assert s.get_shadow_price("c") == pytest.approx(-2.0, abs=1e-4)


@pytest.mark.skipif(not HAS_CPLEX, reason="cplex not installed")
def test_w9_cplex_nonconvex_qp_still_solves():
    x = LXVariable[None, float]("x").continuous().bounds(-1, 2)
    m = LXModel("m").add_variable(x)
    s = solve_with("cplex", m.minimize(LXQuadraticExpression().add_quadratic(x, x, -1.0)))
    assert s.is_optimal() and s.objective_value == pytest.approx(-4.0, abs=1e-6)
