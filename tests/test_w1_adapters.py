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
    assert s.objective_value >= 0 and len(s.variables["x"]) == 30


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


def test_a8_cplex_status_mapping():
    pytest.importorskip("cplex")
    x = fam("x", ["k"], "integer", 0, 3)
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint("c").expression(LXLinearExpression().add_term(x, 1.0)).ge().rhs(5))
    m.minimize(LXLinearExpression().add_term(x, 1.0))
    assert solve_with("cplex", m).status == "infeasible"
    s = solve_with("cplex", knapsack(), solution_limit=1)
    # the first incumbent may be the all-zero packing; what matters is that it is returned
    assert s.status in ("feasible", "optimal") and s.objective_value >= 0 and len(s.variables["x"]) == 30
    y = fam("y", ["k"], "integer", 0, None)
    u = LXModel("u").add_variable(y)
    u.maximize(LXLinearExpression().add_term(y, 1.0))
    assert solve_with("cplex", u).status in ("unbounded", "inf_or_unbounded")


def test_cplex_maps_named_status_constants():
    cplex = pytest.importorskip("cplex")
    from lumix.solvers.cplex_solver import LXCPLEXSolver
    st = cplex.Cplex().solution.status
    m = LXCPLEXSolver._status_name
    assert m(st, st.optimal_tolerance, True) == "optimal"
    assert m(st, st.MIP_infeasible, False) == "infeasible"
    assert m(st, st.MIP_unbounded, False) == "unbounded"
    assert m(st, st.MIP_infeasible_or_unbounded, False) == "inf_or_unbounded"
    assert m(st, st.MIP_time_limit_feasible, True) == "feasible"
    assert m(st, st.MIP_time_limit_infeasible, False) == "time_limit"


def test_b10_glpk_infeasible_and_unbounded_lp():
    pytest.importorskip("swiglpk")
    x = fam("x", ["k"], lower=0, upper=None)
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint("c").expression(LXLinearExpression().add_term(x, 1.0)).le().rhs(-1))
    m.minimize(LXLinearExpression().add_term(x, 1.0))
    assert solve_with("glpk", m).status == "infeasible"
    u = LXModel("u").add_variable(fam("x", ["k"], lower=0))
    u.maximize(LXLinearExpression().add_term(u.variables[0], 1.0))
    assert solve_with("glpk", u).status == "unbounded"


def test_glpk_mip_respects_message_level(capfd):
    pytest.importorskip("swiglpk")
    solve_with("glpk", knapsack())
    assert "GLPK Simplex Optimizer" not in capfd.readouterr().out


def int_var(name, keys, lower=0, upper=10):
    return fam(name, keys, "integer", lower, upper)


def test_a6_cpsat_scales_rhs_with_coefficients():
    x = int_var("x", ["k"])
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint("c").expression(LXLinearExpression().add_term(x, 0.5)).le().rhs(2.25))
    m.maximize(LXLinearExpression().add_term(x, 1.0))
    assert solve_with("cpsat", m).objective_value == pytest.approx(4)


def test_a6_cpsat_keeps_fractional_objective_constant():
    x = int_var("x", ["k"], upper=4)
    m = LXModel("m").add_variable(x)
    m.maximize(LXLinearExpression().add_term(x, 1.0).add_constant(0.5))
    s = solve_with("cpsat", m)
    assert s.objective_value == pytest.approx(4.5) and s.gap in (None, pytest.approx(0))


def mixed_model():
    x = int_var("x", ["k"])
    y = fam("y", ["k"], lower=0, upper=10)
    m = LXModel("mixed").add_variables(x, y)
    m.add_constraint(LXConstraint("c").expression(
        LXLinearExpression().add_term(x, 1.0).add_term(y, 1.0)).le().rhs(7.5))
    m.maximize(LXLinearExpression().add_term(x, 2.0).add_term(y, 1.0))
    return m


def test_a6_cpsat_mixed_integer_and_scaled_continuous():
    s = solve_with("cpsat", mixed_model(), rational=True)
    assert s.status == "optimal" and s.objective_value == pytest.approx(14.5)
    assert s.variables["y"]["k"] == pytest.approx(0.5)


def test_a6_cpsat_scaling_state_does_not_leak_between_solves():
    from lumix import LXOptimizer
    opt = LXOptimizer().use_solver("cpsat").enable_rational_conversion()
    assert opt.solve(mixed_model()).objective_value == pytest.approx(14.5)
    x = int_var("x", ["k"])
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint("c").expression(LXLinearExpression().add_term(x, 1.0)).le().rhs(3))
    m.maximize(LXLinearExpression().add_term(x, 1.0))
    assert opt.solve(m).objective_value == pytest.approx(3)


def test_a6_cpsat_open_bound_beyond_int32():
    x = int_var("x", ["k"], lower=0, upper=None)
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint("c").expression(LXLinearExpression().add_term(x, 1.0)).ge().rhs(3_000_000_000))
    m.minimize(LXLinearExpression().add_term(x, 1.0))
    assert solve_with("cpsat", m).objective_value == pytest.approx(3_000_000_000)


def test_a6_cpsat_unrepresentable_coefficient_raises():
    x = int_var("x", ["k"])
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint("c").expression(LXLinearExpression().add_term(x, 1e-7)).le().rhs(1))
    m.maximize(LXLinearExpression().add_term(x, 1.0))
    with pytest.raises(ValueError, match="cannot represent"):
        solve_with("cpsat", m)


@pytest.mark.parametrize("build", ["lhs_constant_model", "inventory_model", "mixed_model"])
def test_cpsat_matches_ortools_on_canonical_rows(build):
    """A1 and A5 through CP-SAT (continuous variables via rational conversion)."""
    model_fn = globals()[build]
    expected = solve_with("ortools", model_fn())
    s = solve_with("cpsat", model_fn(), rational=True)
    assert s.status == "optimal"
    assert s.objective_value == pytest.approx(expected.objective_value, abs=1e-6)


def test_a2_a3_a4_cpsat_integer_models():
    x = int_var("x", ["k"], upper=100)
    m = LXModel("m").add_variable(x)
    row = LXLinearExpression().add_term(x, 4.0) + LXLinearExpression().add_multi_term(x, coeff=lambda k: 1.0)
    m.add_constraint(LXConstraint("c").expression(row).le().rhs(10))
    m.maximize(LXLinearExpression().add_term(x, 3.0) + LXLinearExpression().add_multi_term(x, coeff=lambda k: -1.0))
    assert solve_with("cpsat", m).objective_value == pytest.approx(4.0)
    b = fam("b", ["k"], "binary", 0, 0)
    n = fam("n", ["k"], "integer", 0.5, 3.7)
    e = int_var("e", [])
    m2 = LXModel("m2").add_variables(b, n, e)
    m2.minimize(LXLinearExpression().add_term(b, -1.0).add_term(n, 1.0).add_term(e, 1.0))
    s = solve_with("cpsat", m2)
    assert s.variables["b"]["k"] == 0 and s.variables["n"]["k"] == 1 and s.variables["e"] == {}


def test_b3_cpsat_no_sensitivity_warning(caplog):
    import logging
    from lumix import LXOptimizer
    x = int_var("x", ["k"])
    m = LXModel("m").add_variable(x)
    m.maximize(LXLinearExpression().add_term(x, 1.0))
    with caplog.at_level(logging.WARNING):
        LXOptimizer().use_solver("cpsat").solve(m)
    assert "enable_sensitivity" not in caplog.text


def many_digit_model():
    x = int_var("x", ["k"])
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint("c").expression(LXLinearExpression().add_term(x, 0.12345)).le().rhs(1))
    m.maximize(LXLinearExpression().add_term(x, 1.0))
    return m


def test_cpsat_many_digit_coefficient_names_the_flag():
    with pytest.raises(ValueError, match="approximate_coefficients=True"):
        solve_with("cpsat", many_digit_model())


def test_cpsat_approximate_coefficients_flag(caplog):
    import logging
    from lumix import LXOptimizer
    with caplog.at_level(logging.WARNING):
        s = LXOptimizer().use_solver("cpsat").solve(many_digit_model(), approximate_coefficients=True)
    assert s.status == "optimal" and s.objective_value == pytest.approx(8)
    assert "approximated" in caplog.text


def test_b2_use_solver_after_solve_switches_adapter():
    pytest.importorskip("gurobipy")
    from lumix import LXOptimizer
    opt = LXOptimizer().use_solver("ortools")
    opt.solve(lhs_constant_model())
    opt.use_solver("gurobi")
    opt.solve(lhs_constant_model())
    assert type(opt._solver).__name__ == "LXGurobiSolver"


def test_b2_use_solver_kwargs_reach_the_solver():
    pytest.importorskip("gurobipy")
    from lumix import LXOptimizer
    s = LXOptimizer().use_solver("gurobi", SolutionLimit=1).solve(knapsack())
    assert s.status == "feasible"
