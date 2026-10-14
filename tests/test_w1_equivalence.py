"""Independent verification of W1 (spec §6): every installed solver agrees with
brute-force enumeration and with a hand-built pywraplp reference on random models."""
import sys
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

sys.path.insert(0, str(Path(__file__).parent))
from solver_matrix import AVAILABLE, INTEGER_SOLVERS, brute_force, solve_with  # noqa: E402

from lumix import LXConstraint, LXLinearExpression, LXModel, LXVariable

KEYS = ["a", "b", "c"]
coef = st.integers(-4, 4)


@st.composite
def small_mips(draw):
    """Integer models exercising A1-A5: LHS constants, repeated terms (add_term +
    add_multi_term on one family), fractional integer bounds, binaries with
    tightened bounds, an empty family, both senses."""
    lo = draw(st.sampled_from([-2, -1.5, 0, 0.5]))
    up = lo + draw(st.sampled_from([1, 2, 2.7, 3]))
    x = (LXVariable[str, float]("x").integer().bounds(lower=lo, upper=up)
         .indexed_by(lambda k: k).from_data(KEYS))
    b = (LXVariable[str, float]("b").binary().bounds(lower=0, upper=draw(st.sampled_from([0, 1])))
         .indexed_by(lambda k: k).from_data(KEYS[:2]))
    empty = LXVariable[str, float]("e").integer().bounds(0, 5).indexed_by(lambda k: k).from_data([])
    m = LXModel("rand").add_variables(x, b, empty)
    for r in range(draw(st.integers(1, 3))):
        cx = {k: draw(coef) for k in KEYS}
        dup = {k: draw(coef) for k in KEYS}
        expr = (LXLinearExpression().add_term(x, lambda k, c=cx: c[k])
                .add_term(b, draw(coef)).add_term(empty, 1.0)
                .add_constant(draw(st.integers(-3, 3))))
        expr = expr + LXLinearExpression().add_multi_term(x, coeff=lambda k, c=dup: c[k])
        rhs = draw(st.integers(-6, 6))
        sense = draw(st.sampled_from(["le", "ge", "eq"]))
        m.add_constraint(getattr(LXConstraint(f"r{r}").expression(expr), sense)().rhs(rhs))
    obj = {k: draw(coef) for k in KEYS}
    expr = (LXLinearExpression().add_term(x, lambda k, c=obj: c[k]).add_term(b, draw(coef))
            .add_constant(draw(st.integers(-5, 5))))
    m.maximize(expr) if draw(st.booleans()) else m.minimize(expr)
    return m


@pytest.mark.parametrize("solver", INTEGER_SOLVERS)
@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow],
          derandomize=True)
@given(model=small_mips())
def test_solvers_match_brute_force(solver, model):
    expected_status, expected = brute_force(model)
    s = solve_with(solver, model)
    if expected_status == "infeasible":
        assert s.status in ("infeasible", "inf_or_unbounded")
    else:
        assert s.status == "optimal", (solver, s.status)
        assert s.objective_value == pytest.approx(expected, abs=1e-6)


def pywraplp_reference(model):
    """Hand-built OR-Tools model from LumiX *objects*, not from the canonical
    form: guards against a shared mistake in to_canonical()."""
    from ortools.linear_solver import pywraplp
    solver = pywraplp.Solver.CreateSolver("SCIP")
    import math
    inf = solver.infinity()
    handles = {}
    for var in model.variables:
        lo = -inf if var.lower_bound is None else var.lower_bound
        hi = inf if var.upper_bound is None else var.upper_bound
        if var.var_type.value != "continuous":
            lo = lo if lo == -inf else math.ceil(lo - 1e-9)
            hi = hi if hi == inf else math.floor(hi + 1e-9)
        if var.var_type.value == "binary":
            lo, hi = max(lo, 0), min(hi, 1)
        for inst in var.get_instances():
            key = var.index_key(inst)
            handles[(var.name, key)] = solver.IntVar(lo, hi, f"{var.name}[{key}]")

    def linear(expr):
        acc, const = {}, expr.constant
        for _, (var, c, w) in expr.terms.items():
            for inst in var.get_instances():
                if w(inst):
                    acc[(var.name, var.index_key(inst))] = acc.get((var.name, var.index_key(inst)), 0) + c(inst)
        for var, c, w in expr._multi_terms:
            for inst in var.get_instances():
                if w is None or w(inst):
                    acc[(var.name, var.index_key(inst))] = acc.get((var.name, var.index_key(inst)), 0) + c(inst)
        return acc, const

    for con in model.constraints:
        acc, const = linear(con.lhs)
        rhs = con.rhs_value - const
        lo, hi = {"<=": (-inf, rhs), ">=": (rhs, inf), "==": (rhs, rhs)}[con.sense.value]
        ct = solver.Constraint(lo, hi)
        for k, c in acc.items():
            ct.SetCoefficient(handles[k], c)
    acc, const = linear(model.objective_expr)
    obj = solver.Objective()
    for k, c in acc.items():
        obj.SetCoefficient(handles[k], c)
    obj.SetOffset(const)
    obj.SetMaximization() if model.objective_sense.value == "max" else obj.SetMinimization()
    status = solver.Solve()
    return status, (obj.Value() if status == pywraplp.Solver.OPTIMAL else None)


@settings(max_examples=60, deadline=None, derandomize=True)
@given(model=small_mips())
def test_canonical_matches_hand_built_reference(model):
    from ortools.linear_solver import pywraplp
    status, value = pywraplp_reference(model)
    expected_status, expected = brute_force(model)
    if status == pywraplp.Solver.OPTIMAL:
        assert expected_status == "optimal" and value == pytest.approx(expected, abs=1e-6)
    else:
        assert expected_status == "infeasible"
