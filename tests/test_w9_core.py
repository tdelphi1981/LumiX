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
