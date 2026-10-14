"""Regressions from the W1 final review (C1, C2, I1-I6, M1-M5) and the deferred
status/logging items (unbounded LP on GLOP and CPLEX, Gurobi log output)."""
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from solver_matrix import AVAILABLE, solve_with  # noqa: E402
from test_canonical import fam, row_map  # noqa: E402

from lumix import LXConstraint, LXLinearExpression, LXModel, LXOptimizer, LXVariable
from lumix.core.expressions import call_arity


@dataclass(frozen=True)
class T:
    t: int
    demand: float


TS = [T(1, 5.0), T(2, 7.0), T(3, 4.0)]


def inventory_mixed_arity():
    """inv[t] - inv[t-1] - prod[t] == -demand[t] written with a one-argument and a
    two-argument term on the same variable (the form the 0.3.0 docs recommend)."""
    inv = LXVariable[T, float]("inv").integer().bounds(lower=0, upper=100).indexed_by(lambda p: p.t).from_data(TS)
    prod = LXVariable[T, float]("prod").integer().bounds(lower=0, upper=6).indexed_by(lambda p: p.t).from_data(TS)
    bal = (LXConstraint[T]("bal")
           .expression(LXLinearExpression()
                       .add_term(inv, 1.0)
                       .add_term(inv, -1.0, where=lambda s, row: s.t == row.t - 1)
                       .add_term(prod, -1.0))
           .eq().rhs(lambda row: -row.demand).indexed_by(lambda p: p.t).from_data(TS))
    return (LXModel("inv").add_variables(inv, prod).add_constraint(bal)
            .minimize(LXLinearExpression().add_term(prod, 1.0).add_term(inv, 1.0)))


def test_c1_merged_one_and_two_argument_terms_narrow_separately():
    canon = inventory_mixed_arity().to_canonical()
    assert row_map(canon, "bal[1]")[0] == {"inv[1]": 1.0, "prod[1]": -1.0}
    assert row_map(canon, "bal[2]")[0] == {"inv[1]": -1.0, "inv[2]": 1.0, "prod[2]": -1.0}


@pytest.mark.parametrize("solver", AVAILABLE + ["cpsat"])
def test_c1_inventory_mixed_arity_solves(solver):
    s = solve_with(solver, inventory_mixed_arity())
    assert s.status == "optimal" and s.objective_value == pytest.approx(17)


def test_c1_sum_of_expressions_narrows_each_part():
    x = (LXVariable[T, float]("x").continuous().bounds(lower=0)
         .indexed_by(lambda p: p.t).from_data(TS))
    e = (LXLinearExpression().add_term(x, 1.0)
         + LXLinearExpression().add_term(x, lambda s, row: 0.1 * s.t))
    cap = LXConstraint[T]("cap").expression(e * 2).le().rhs(10).indexed_by(lambda p: p.t).from_data(TS)
    canon = LXModel("m").add_variable(x).add_constraint(cap).to_canonical()
    assert row_map(canon, "cap[2]")[0] == pytest.approx({"x[1]": 0.2, "x[2]": 2.4, "x[3]": 0.6})


def test_c2_default_arguments_do_not_count_toward_arity():
    assert call_arity(lambda it, g="A": it) == 1
    assert call_arity(lambda s, t, k=1: s) == 2
    assert call_arity({}.get) == 1


def test_c2_loop_capture_filter_in_a_constraint_family():
    @dataclass(frozen=True)
    class Item:
        id: str
        group: str

    @dataclass(frozen=True)
    class Period:
        id: int
        cap: float

    items = [Item("i1", "A"), Item("i2", "A"), Item("i3", "B")]
    periods = [Period(1, 1.0), Period(2, 1.0)]
    x = LXVariable[Item, float]("x").continuous().bounds(lower=0, upper=10).indexed_by(lambda i: i.id).from_data(items)
    m = LXModel("m").add_variable(x)
    for g in ["A", "B"]:
        m.add_constraint(LXConstraint[Period](f"cap_{g}")
                         .expression(LXLinearExpression().add_term(x, 1.0, where=lambda it, g=g: it.group == g))
                         .le().rhs(lambda p: p.cap).indexed_by(lambda p: p.id).from_data(periods))
    m.maximize(LXLinearExpression().add_term(x, 1.0))
    assert row_map(m.to_canonical(), "cap_A[1]")[0] == {"x[i1]": 1.0, "x[i2]": 1.0}
    assert solve_with("ortools", m).objective_value == pytest.approx(2.0)


def test_i1_cpsat_unbounded_through_a_non_objective_variable():
    x = fam("x", ["k"], "integer", 0, None)
    y = fam("y", ["k"], "integer", 0, None)
    m = LXModel("m").add_variables(x, y)
    m.add_constraint(LXConstraint("c").expression(
        LXLinearExpression().add_term(x, 2.0).add_term(y, -1.0)).le().rhs(0))
    m.maximize(LXLinearExpression().add_term(x, 1.0))
    assert solve_with("cpsat", m).status != "optimal"


def test_i2_duplicate_constraint_key_raises():
    x = fam("x", ["k"], upper=5)
    cap = (LXConstraint[tuple]("cap").expression(LXLinearExpression().add_term(x, 1.0))
           .le().rhs(lambda p: p[1]).indexed_by(lambda p: p[0]).from_data([("a", 3), ("a", 1)]))
    with pytest.raises(ValueError, match="duplicate index key"):
        LXModel("m").add_variable(x).add_constraint(cap).to_canonical()


def test_i3_float_cancellation_noise_is_zero():
    x = fam("x", ["k"], "integer", 0, 10)
    y = fam("y", ["k"], "integer", 0, 10)
    m = LXModel("m").add_variables(x, y)
    m.add_constraint(LXConstraint("c").expression(
        LXLinearExpression().add_term(x, 0.1).add_term(x, 0.2).add_term(x, -0.3)
        .add_term(y, 1.0).add_constant(0.1).add_constant(0.2)).le().rhs(0.3))
    m.maximize(LXLinearExpression().add_term(x, 1.0).add_term(y, 1.0))
    coeffs, row = row_map(m.to_canonical(), "c")
    assert coeffs == {"y[k]": 1.0} and row.rhs == 0.0
    assert solve_with("cpsat", m).objective_value == pytest.approx(10)


def test_i4_cpsat_open_bound_with_large_coefficient():
    x = fam("x", ["k"], "integer", 0, None)
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint("c").expression(LXLinearExpression().add_term(x, 1e7)).le().rhs(5e8))
    m.maximize(LXLinearExpression().add_term(x, 1.0))
    s = solve_with("cpsat", m)
    assert s.status == "optimal" and s.objective_value == pytest.approx(50)


def test_i5_cpsat_off_grid_equality_warns(caplog):
    x = fam("x", ["k"], lower=0, upper=10)
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint("c").expression(LXLinearExpression().add_term(x, 3.0)).eq().rhs(1))
    m.minimize(LXLinearExpression().add_term(x, 1.0))
    with caplog.at_level(logging.WARNING):
        s = LXOptimizer().use_solver("cpsat").enable_rational_conversion().solve(m)
    assert s.status == "infeasible"
    assert "grid" in caplog.text


def test_i6_from_model_without_session_is_not_scalar():
    @dataclass
    class Product:
        id: int
    v = LXVariable[Product, float]("production").continuous().from_model(Product)
    assert not v.is_scalar
    with pytest.raises(ValueError, match="no data source"):
        LXModel("m").add_variable(v).to_canonical()


def test_m1_cpsat_tolerance_is_relative():
    x = fam("x", ["k"], "integer", 0, 10)
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint("c").expression(LXLinearExpression().add_term(x, 0.000100000049)).le().rhs(1))
    m.maximize(LXLinearExpression().add_term(x, 1.0))
    with pytest.raises(ValueError, match="cannot represent"):
        solve_with("cpsat", m)


def infeasible_mip_with_unbounded_relaxation():
    a = fam("a", ["k"], "integer", None, None)
    b = fam("b", ["k"], "integer", None, None)
    m = LXModel("m").add_variables(a, b)
    m.add_constraint(LXConstraint("c").expression(
        LXLinearExpression().add_term(a, 2.0).add_term(b, -2.0)).eq().rhs(1))
    m.maximize(LXLinearExpression().add_term(a, 1.0))
    return m


def test_m3_glpk_does_not_claim_unbounded_for_an_infeasible_mip():
    assert solve_with("glpk", infeasible_mip_with_unbounded_relaxation()).status in (
        "infeasible", "inf_or_unbounded")


def unbounded(kind="continuous"):
    x = fam("x", ["k"], kind, 0, None)
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint("c").expression(LXLinearExpression().add_term(x, 1.0)).ge().rhs(1))
    m.maximize(LXLinearExpression().add_term(x, 1.0))
    return m


@pytest.mark.parametrize("solver", AVAILABLE)
@pytest.mark.parametrize("kind", ["continuous", "integer"])
def test_unbounded_is_reported_unbounded_without_values(solver, kind):
    s = solve_with(solver, unbounded(kind))
    assert s.status == "unbounded"
    assert s.variables == {}


def test_m5_ortools_mip_has_no_sensitivity():
    s = LXOptimizer().use_solver("ortools").enable_sensitivity().solve(unbounded("integer"))
    m = LXModel("m").add_variable(fam("x", ["k"], "integer", 0, 3))
    m.maximize(LXLinearExpression().add_term(m.variables[0], 1.0))
    s = LXOptimizer().use_solver("ortools").enable_sensitivity().solve(m)
    assert s.shadow_prices == {} and s.reduced_costs == {}


def test_gurobi_is_quiet_by_default(capfd):
    pytest.importorskip("gurobipy")
    solve_with("gurobi", unbounded())
    out = capfd.readouterr().out
    assert "Gurobi Optimizer version" not in out and "Optimize a model" not in out
