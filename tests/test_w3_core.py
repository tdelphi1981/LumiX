"""W3 core API regressions (catalog A9-A13, B5, B6, C)."""
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from solver_matrix import AVAILABLE, solve_with  # noqa: E402
from test_canonical import fam, row_map  # noqa: E402

from lumix import LXConstraint, LXLinearExpression, LXModel, LXOptimizer, LXVariable


@dataclass(frozen=True)
class R:
    id: str
    cap: float


def test_a9_last_rhs_call_wins():
    c = LXConstraint("c").rhs(5).rhs(lambda r: r.cap)
    assert c.rhs_value is None and c.rhs_func is not None
    c.rhs(7)
    assert c.rhs_value == 7 and c.rhs_func is None


def test_a10_goal_sense_is_read_at_solve_time():
    x = fam("x", ["k"], lower=0, upper=10)
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint("g").expression(LXLinearExpression().add_term(x, 1.0))
                     .as_goal(priority=1).ge().rhs(8))
    m.set_goal_mode("weighted")
    m.prepare_goal_programming()
    s = solve_with("ortools", m)
    assert s.variables["x"]["k"] >= 8 - 1e-6


def test_a11_constraint_data_without_index_raises():
    x = fam("x", ["k"], upper=5)
    c = LXConstraint[R]("cap").expression(LXLinearExpression().add_term(x, 1.0)).le().rhs(3).from_data([R("a", 1)])
    with pytest.raises(ValueError, match="indexed_by"):
        LXModel("m").add_variable(x).add_constraint(c).to_canonical()


from lumix import LXIndexDimension


@dataclass(frozen=True)
class A:
    id: int


@dataclass(frozen=True)
class B:
    id: int


AS, BS = [A(1), A(2)], [B(1), B(2)]


def product(name="v"):
    return LXVariable(name).binary().indexed_by_product(
        LXIndexDimension(A, lambda a: a.id).from_data(AS),
        LXIndexDimension(B, lambda b: b.id).from_data(BS))


def test_a13_where_multi_before_product_applies():
    v = LXVariable("v").binary().where_multi(lambda a, b: a.id == b.id).indexed_by_product(
        LXIndexDimension(A, lambda a: a.id).from_data(AS),
        LXIndexDimension(B, lambda b: b.id).from_data(BS))
    assert len(v.get_instances()) == 2


def test_a13_where_on_product_applies():
    assert len(product().where(lambda ab: ab[0].id == 1).get_instances()) == 2


@dataclass
class Driver:
    id: int
    routes: list
    active: bool = True


@dataclass(frozen=True)
class Route:
    id: int
    cost: float


R1, R2, R3 = Route(1, 4.0), Route(2, 1.0), Route(3, 2.0)


def join_var(drivers):
    return (LXVariable("assign").binary()
            .indexed_by_join(Driver, Route, join_func=lambda d: d.routes,
                             key_func=lambda d, r: (d.id, r.id))
            .from_data(drivers))


def test_b5_join_instances_and_keys():
    v = join_var([Driver(1, [R1, R2]), Driver(2, [R3])])
    assert [v.index_key(i) for i in v.get_instances()] == [(1, 1), (1, 2), (2, 3)]
    assert v.is_multi_indexed and not v.is_scalar


def test_b5_join_solves_with_two_argument_coefficients():
    drivers = [Driver(1, [R1, R2]), Driver(2, [R1, R3])]
    v = join_var(drivers)
    m = LXModel("m").add_variable(v)
    for d in drivers:
        m.add_constraint(LXConstraint(f"one_{d.id}").expression(
            LXLinearExpression().add_multi_term(v, where=lambda dd, r, d=d: dd.id == d.id)).eq().rhs(1))
    m.minimize(LXLinearExpression().add_multi_term(v, coeff=lambda d, r: r.cost))
    for solver in AVAILABLE:
        assert solve_with(solver, m).objective_value == pytest.approx(3.0)   # 1.0 + 2.0


def test_b5_join_where_multi_and_where():
    v = join_var([Driver(1, [R1, R2]), Driver(2, [R3], active=False)])
    v.where(lambda d: d.active).where_multi(lambda d, r: r.cost > 1)
    assert [v.index_key(i) for i in v.get_instances()] == [(1, 1)]


def test_b5_join_with_empty_relations(caplog):
    v = join_var([Driver(1, []), Driver(2, [])])
    with caplog.at_level(logging.WARNING):
        canon = LXModel("m").add_variable(v).to_canonical()
    assert canon.variables == () and "has no instances" in caplog.text


@dataclass(frozen=True)
class P:
    id: int
    unit_cost: float


PS = [P(1, 3.0), P(2, 5.0)]


def costed():
    return (LXVariable[P, float]("x").continuous().bounds(lower=1, upper=10)
            .indexed_by(lambda p: p.id).cost(lambda p: p.unit_cost).from_data(PS))


@pytest.mark.parametrize("solver", AVAILABLE)
def test_a12_minimize_without_argument_uses_costs(solver):
    m = LXModel("m").add_variable(costed())
    m.minimize()
    assert solve_with(solver, m).objective_value == pytest.approx(8.0)


def test_a12_cost_multi_and_late_variables():
    v = product("v").cost_multi(lambda a, b: a.id * 10 + b.id)
    m = LXModel("m").maximize()
    m.add_variable(v)
    assert solve_with("ortools", m).objective_value == pytest.approx(11 + 12 + 21 + 22)


def test_a12_explicit_objective_ignores_costs():
    x = costed()
    m = LXModel("m").add_variable(x)
    m.minimize(LXLinearExpression().add_term(x, 1.0))
    assert solve_with("ortools", m).objective_value == pytest.approx(2.0)


def test_a12_no_costs_raises():
    m = LXModel("m").add_variable(fam("x", ["k"], upper=1))
    m.minimize()
    with pytest.raises(ValueError, match="cost"):
        m.to_canonical()


def test_a12_cost_expression():
    e = costed().cost_expression()
    assert isinstance(e, LXLinearExpression) and fam("y", ["k"]).cost_expression() is None


def test_add_does_not_mutate_operands():
    x = fam("x", ["a"], upper=5)
    y = fam("y", ["a"], upper=5)
    base = LXLinearExpression().add_term(x, 1.0).add_constant(1)
    a = base + LXLinearExpression().add_term(y, 2.0)
    b = base * 3
    assert set(base.terms) == {"x"} and base.constant == 1
    assert set(a.terms) == {"x", "y"} and b.constant == 3
    base += LXLinearExpression().add_term(y, 1.0)
    assert set(base.terms) == {"x", "y"}


def test_sum_and_numpy_scalars():
    np = pytest.importorskip("numpy")
    x = fam("x", ["a"], upper=5)
    e = sum([LXLinearExpression().add_term(x, 1.0), LXLinearExpression().add_term(x, 2.0)])
    e = e * np.float64(2) + np.int64(1)
    e = 2 * e - LXLinearExpression().add_term(x, 1.0)
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint("c").expression(e).le().rhs(100))
    coeffs, row = row_map(m.to_canonical(), "c")
    assert coeffs == {"x[a]": 11.0} and row.rhs == 98.0
    assert (-e).constant == -2


def test_duplicate_family_name_raises():
    m = LXModel("m").add_variable(fam("x", ["a"]))
    with pytest.raises(ValueError, match="already has a variable family named 'x'"):
        m.add_variable(fam("x", ["b"]))
    with pytest.raises(ValueError, match="already has a variable family named 'y'"):
        LXModel("m2").add_variables(fam("y", ["a"]), fam("y", ["b"]))


from lumix import LXQuadraticExpression, LXQuadraticTerm


def test_b6_quadratic_add_keeps_both():
    x = fam("x", ["a"], upper=10)
    q1 = LXQuadraticExpression().add_squared(x, 1.0)
    q2 = LXQuadraticExpression().add_squared(x, 2.0)
    q2.constant = 5
    r = q1 + q2
    assert len(r.quadratic_terms) == 2 and r.constant == 5 and len(q1.quadratic_terms) == 1


def test_b6_canonical_quadratic_semantics():
    w = fam("w", ["a", "b"], lower=0, upper=1)
    cov = {("a", "a"): 2.0, ("a", "b"): 0.5, ("b", "a"): 0.5, ("b", "b"): 1.0}
    q = LXQuadraticExpression().add_quadratic(w, w, coeff=lambda i, j: cov[(i, j)])
    q = q + LXLinearExpression().add_term(w, -1.0)
    canon = LXModel("m").add_variable(w).minimize(q).to_canonical()
    assert canon.objective_quadratic == {(0, 0): 2.0, (0, 1): 1.0, (1, 1): 1.0}
    assert canon.objective == {0: -1.0, 1: -1.0}


def test_b6_squared_is_diagonal_and_alias():
    x = fam("x", ["a", "b"], upper=3)
    q = LXQuadraticExpression().add_squared(x, 2.0).add_quadratic_term(x, x, coefficient=0.0)
    q = q.add_quadratic_term(LXQuadraticTerm(x, x, 0.0))
    canon = LXModel("m").add_variable(x).minimize(q).to_canonical()
    assert canon.objective_quadratic == {(0, 0): 2.0, (1, 1): 2.0}


def test_b6_quadratic_constraint_raises():
    x = fam("x", ["a"], upper=3)
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint("c").expression(LXQuadraticExpression().add_squared(x)).le().rhs(1))
    with pytest.raises(ValueError, match="quadratic"):
        m.to_canonical()


import itertools


def quad_model():
    """min (x - 2)^2 + (y - 1)^2 + x*y over integers 0..3 (convex)."""
    x = fam("x", ["k"], "integer", 0, 3)
    y = fam("y", ["k"], "integer", 0, 3)
    q = (LXQuadraticExpression().add_squared(x).add_squared(y).add_quadratic(x, y, 1.0)
         + LXLinearExpression().add_term(x, -4.0).add_term(y, -2.0).add_constant(5))
    return LXModel("q").add_variables(x, y).minimize(q)


def brute(model):
    canon = model.to_canonical()
    best = None
    for point in itertools.product(*(range(int(v.lower), int(v.upper) + 1) for v in canon.variables)):
        val = canon.objective_constant + sum(c * point[i] for i, c in canon.objective.items())
        val += sum(c * point[i] * point[j] for (i, j), c in canon.objective_quadratic.items())
        best = val if best is None else min(best, val)
    return best


@pytest.mark.parametrize("solver", [s for s in ("gurobi", "cplex") if s in AVAILABLE])
def test_b6_native_quadratic_objective(solver):
    s = solve_with(solver, quad_model())
    assert s.status == "optimal" and s.objective_value == pytest.approx(brute(quad_model()))


@pytest.mark.parametrize("solver", ["ortools", "glpk", "cpsat"])
def test_b6_quadratic_needs_linearization(solver):
    with pytest.raises(ValueError, match="enable_linearization"):
        solve_with(solver, quad_model())


def test_b6_binary_quadratic_through_linearization():
    a = fam("a", ["k"], "binary")
    b = fam("b", ["k"], "binary")
    q = LXQuadraticExpression().add_quadratic(a, b, 3.0) + LXLinearExpression().add_term(a, 1.0)
    m = LXModel("m").add_variables(a, b).maximize(q)
    s = LXOptimizer().use_solver("ortools").enable_linearization().solve(m)
    assert s.objective_value == pytest.approx(4.0)


def test_b6_family_quadratic_without_native_support_raises():
    a = fam("a", ["k", "l"], "binary")
    q = LXQuadraticExpression().add_squared(a, 1.0)
    m = LXModel("m").add_variables(a).maximize(q)
    with pytest.raises(ValueError, match="gurobi"):
        LXOptimizer().use_solver("ortools").enable_linearization().solve(m)


# --- Görev 7: independent checks (spec §6) ---------------------------------------
from hypothesis import HealthCheck, given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

from solver_matrix import INTEGER_SOLVERS  # noqa: E402

QP_SOLVERS = [s for s in ("gurobi", "cplex") if s in AVAILABLE]


@st.composite
def quadratic_cases(draw):
    n = draw(st.integers(2, 3))
    coef = st.integers(-3, 3)
    diag = [draw(coef) for _ in range(n)]
    cross = {(i, j): draw(coef) for i in range(n) for j in range(i + 1, n)}
    linear = [draw(coef) for _ in range(n)]
    rows = [([draw(coef) for _ in range(n)], draw(st.integers(-2, 6)))
            for _ in range(draw(st.integers(0, 2)))]
    return n, diag, cross, linear, rows, draw(st.sampled_from(["min", "max"]))


def quadratic_oracle(n, diag, cross, linear, rows, sense):
    """Optimum by enumeration, written from the raw coefficients (not the canonical model)."""
    best = None
    for x in itertools.product(range(4), repeat=n):
        if any(sum(a * v for a, v in zip(coeffs, x)) > rhs for coeffs, rhs in rows):
            continue
        value = (sum(d * v * v for d, v in zip(diag, x)) + sum(l * v for l, v in zip(linear, x))
                 + sum(c * x[i] * x[j] for (i, j), c in cross.items()))
        if best is None or (value > best if sense == "max" else value < best):
            best = value
    return best


@pytest.mark.skipif(not QP_SOLVERS, reason="needs gurobi or cplex")
@settings(max_examples=40, derandomize=True, deadline=None,
          suppress_health_check=[HealthCheck.too_slow])
@given(quadratic_cases())
def test_quadratic_objectives_match_brute_force(case):
    n, diag, cross, linear, rows, sense = case
    xs = [fam(f"x{i}", ["k"], "integer", 0, 3) for i in range(n)]
    q = LXQuadraticExpression()
    for x, d in zip(xs, diag):
        q.add_squared(x, float(d))
    for (i, j), c in cross.items():
        q.add_quadratic(xs[i], xs[j], float(c))
    lin = LXLinearExpression()
    for x, l in zip(xs, linear):
        lin.add_term(x, float(l))
    q = q + lin
    model = LXModel("qp").add_variables(*xs)
    for r, (coeffs, rhs) in enumerate(rows):
        e = LXLinearExpression()
        for x, a in zip(xs, coeffs):
            e.add_term(x, float(a))
        model.add_constraint(LXConstraint(f"r{r}").expression(e).le().rhs(rhs))
    model.maximize(q) if sense == "max" else model.minimize(q)
    expected = quadratic_oracle(*case)
    for solver in QP_SOLVERS:
        s = solve_with(solver, model)
        if expected is None:
            assert s.status == "infeasible", (solver, case)
        else:
            assert s.status == "optimal", (solver, case, s.status)
            assert s.objective_value == pytest.approx(expected, abs=1e-6), (solver, case)


@settings(max_examples=25, derandomize=True, deadline=None)
@given(st.lists(st.integers(-5, 5), min_size=2, max_size=4), st.integers(0, 6))
def test_cost_objective_equals_explicit_objective(costs, demand):
    keys = [f"k{i}" for i in range(len(costs))]
    price = dict(zip(keys, costs))

    def build(explicit):
        x = fam("x", keys, "integer", 0, 3)
        if not explicit:
            x = x.cost(lambda k: price[k])
        m = LXModel("m").add_variable(x)
        m.add_constraint(LXConstraint("d").expression(LXLinearExpression().add_term(x, 1.0))
                         .ge().rhs(demand))
        return m.minimize(LXLinearExpression().add_term(x, lambda k: price[k])) if explicit \
            else m.minimize()

    for solver in INTEGER_SOLVERS:
        a, b = solve_with(solver, build(False)), solve_with(solver, build(True))
        assert a.status == b.status, solver
        if a.status == "optimal":
            assert a.objective_value == pytest.approx(b.objective_value, abs=1e-6), solver
