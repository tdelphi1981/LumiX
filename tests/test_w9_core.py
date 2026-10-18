"""W9a (0.3.2): non-finite values in the canonical model, narrowing by type,
binary() bounds."""
import math
from typing import NamedTuple

import pytest

from lumix import (LXConstraint, LXLinearExpression, LXModel, LXNonLinearExpression,
                   LXQuadraticExpression, LXVariable)
from tests.solver_matrix import AVAILABLE, solve_with


def _x(lo=0.0, hi=10.0):
    return LXVariable[None, float]("x").continuous().bounds(lo, hi)


def _y():
    return LXVariable[None, float]("y").continuous().bounds(0.0, 10.0)


@pytest.mark.parametrize("bad", [math.inf, -math.inf, math.nan])
def test_w9_nonfinite_row_coefficient_raises(bad):
    x, y = _x(), _y()
    m = LXModel("m").add_variable(x).add_variable(y)
    m.add_constraint(LXConstraint("cap").expression(
        LXLinearExpression().add_term(x, bad).add_term(y, 1.0)).le().rhs(5))
    m.maximize(LXLinearExpression().add_term(y, 1.0))
    with pytest.raises(ValueError, match=r"Constraint 'cap': coefficient of 'x' is"):
        m.to_canonical()


@pytest.mark.parametrize("bad", [math.inf, math.nan])
def test_w9_nonfinite_objective_coefficient_raises(bad):
    x = _x()
    m = LXModel("m").add_variable(x).maximize(LXLinearExpression().add_term(x, bad))
    with pytest.raises(ValueError, match=r"The objective: coefficient of 'x' is"):
        m.to_canonical()


def test_w9_nonfinite_callable_coefficient_names_the_instance():
    x = LXVariable[str, float]("x").continuous().bounds(0, 1) \
        .indexed_by(lambda k: k).from_data(["a", "b"])
    m = LXModel("m").add_variable(x)
    m.maximize(LXLinearExpression().add_term(x, lambda k: math.nan if k == "b" else 1.0))
    with pytest.raises(ValueError, match=r"coefficient of 'x\[b\]' is nan"):
        m.to_canonical()


def test_w9_nonfinite_objective_constant_raises():
    x = _x()
    m = LXModel("m").add_variable(x).maximize(
        LXLinearExpression().add_term(x, 1.0).add_constant(math.inf))
    with pytest.raises(ValueError, match=r"The objective: its constant is inf"):
        m.to_canonical()


def test_w9_nonfinite_quadratic_coefficient_raises():
    x = _x()
    q = LXQuadraticExpression().add_quadratic(x, x, math.inf)
    m = LXModel("m").add_variable(x).minimize(q)
    with pytest.raises(ValueError, match=r"The objective: quadratic coefficient .* is inf"):
        m.to_canonical()


def test_w9_nonfinite_nonlinear_coefficient_raises():
    x = _x(-5.0, 5.0)
    m = LXModel("m").add_variable(x).minimize(LXNonLinearExpression().add_abs(x, math.nan))
    with pytest.raises(ValueError, match=r"The objective: abs\(\) coefficient is nan"):
        m.to_canonical()


@pytest.mark.parametrize("lo, hi", [(math.inf, math.inf), (-math.inf, -math.inf),
                                    (math.nan, 1.0)])
def test_w9_impossible_variable_bounds_raise(lo, hi):
    x = LXVariable[None, float]("x").continuous().bounds(lo, hi)
    m = LXModel("m").add_variable(x).maximize(LXLinearExpression().add_term(x, 1.0))
    with pytest.raises(ValueError, match=r"Variable 'x' has bounds"):
        m.to_canonical()


@pytest.mark.parametrize("solver", AVAILABLE)
def test_w9_infinite_bounds_still_solve(solver):
    # Review Focus 1: open bounds behind a finite row are fine.
    x = LXVariable[None, float]("x").continuous().bounds(None, math.inf)
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint("cap").expression(
        LXLinearExpression().add_term(x, 1.0)).le().rhs(7))
    m.add_constraint(LXConstraint("low").expression(
        LXLinearExpression().add_term(x, 1.0)).ge().rhs(-3))
    m.maximize(LXLinearExpression().add_term(x, 1.0))
    s = solve_with(solver, m)
    assert s.is_optimal() and s.objective_value == pytest.approx(7.0)


class _A(NamedTuple):
    id: int


class _B(NamedTuple):
    id: int


def test_w9_rows_of_another_namedtuple_type_are_not_narrowed():
    x = (LXVariable[_A, float]("x").continuous().bounds(0, 1)
         .indexed_by(lambda a: a.id).from_data([_A(1), _A(2)]))
    c = (LXConstraint[_B]("c").expression(LXLinearExpression().add_term(x, 1.0))
         .le().rhs(1).from_data([_B(1), _B(2)]).indexed_by(lambda b: b.id))
    canon = LXModel("m").add_variable(x).add_constraint(c).to_canonical()
    assert [r.coeffs for r in canon.rows] == [{0: 1.0, 1: 1.0}, {0: 1.0, 1: 1.0}]


def test_w9_builtin_rows_still_narrow_by_value():
    # I7 (test_w1_review.py::test_i7) keeps value narrowing for built-in rows.
    x = LXVariable[int, float]("x").continuous().bounds(0, 1) \
        .indexed_by(lambda k: k).from_data([1, 2, 3])
    c = (LXConstraint[int]("c").expression(LXLinearExpression().add_term(x, 1.0))
         .le().rhs(1).from_data([2, 3]).indexed_by(lambda k: k))
    canon = LXModel("m").add_variable(x).add_constraint(c).to_canonical()
    assert [r.coeffs for r in canon.rows] == [{1: 1.0}, {2: 1.0}]


def test_w9_binary_keeps_bounds_set_before_it():
    b = LXVariable[None, int]("b").bounds(0, 0).binary()
    assert (b.lower_bound, b.upper_bound) == (0, 0)
    m = LXModel("m").add_variable(b).maximize(LXLinearExpression().add_term(b, 1.0))
    assert solve_with("ortools", m).objective_value == pytest.approx(0.0)


def test_w9_binary_without_bounds_is_zero_one():
    b = LXVariable[None, int]("b").binary()
    m = LXModel("m").add_variable(b)
    v = m.to_canonical().variables[0]
    assert (v.lower, v.upper) == (0.0, 1.0)


def test_w9_solver_base_has_no_stale_candidates_helper():
    from lumix.solvers.base import LXSolverInterface
    assert not hasattr(LXSolverInterface, "_candidates")
