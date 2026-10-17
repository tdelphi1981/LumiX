"""Rows with an infinite or NaN right-hand side (0.3.1).

A row that bounds nothing (``<= +inf``, ``>= -inf``) is dropped from the canonical
model, so no solver ever receives an infinite RHS. A row no point can satisfy
(``>= +inf``, ``<= -inf``, ``== +-inf``) and a NaN RHS raise a ValueError that names
the row. In 0.3.0 the noise snap turned every infinite RHS into 0.
"""
import math

import pytest

from lumix import LXConstraint, LXLinearExpression, LXModel, LXVariable
from tests.solver_matrix import INTEGER_SOLVERS, solve_with


def _model(sense, rhs, maximize=True, integer=False, constant=0.0):
    if integer:
        x = LXVariable[None, int]("x").integer().bounds(0, 10)
    else:
        x = LXVariable[None, float]("x").continuous().bounds(0.0, 10.0)
    lhs = LXLinearExpression().add_term(x, 1.0)
    if constant:
        lhs = lhs.add_constant(constant)
    c = LXConstraint("cap").expression(lhs)
    c = {"le": c.le, "ge": c.ge, "eq": c.eq}[sense]()
    m = LXModel("m").add_variable(x).add_constraint(c.rhs(rhs))
    objective = LXLinearExpression().add_term(x, 1.0)
    return m.maximize(objective) if maximize else m.minimize(objective)


@pytest.mark.parametrize("sense, rhs", [("le", math.inf), ("ge", -math.inf)])
def test_vacuous_row_is_dropped(sense, rhs):
    assert _model(sense, rhs).to_canonical().rows == ()


def test_vacuous_row_is_dropped_from_an_indexed_family():
    x = LXVariable[str, float]("x").continuous().bounds(0.0, 10.0) \
        .indexed_by(lambda k: k).from_data(["a", "b"])
    caps = {"a": 4.0, "b": math.inf}
    c = (LXConstraint[str]("cap").expression(LXLinearExpression().add_term(x, 1.0))
         .le().rhs(lambda k: caps[k]).from_data(["a", "b"]).indexed_by(lambda k: k))
    canon = LXModel("m").add_variable(x).add_constraint(c).to_canonical()
    assert [r.name for r in canon.rows] == ["cap[a]"]


@pytest.mark.parametrize("sense, rhs", [("ge", math.inf), ("le", -math.inf),
                                        ("eq", math.inf), ("eq", -math.inf)])
def test_impossible_row_raises_naming_the_row(sense, rhs):
    with pytest.raises(ValueError, match=r"Constraint 'cap'.*infinite"):
        _model(sense, rhs).to_canonical()


@pytest.mark.parametrize("sense", ["le", "ge", "eq"])
def test_nan_rhs_raises_naming_the_row(sense):
    with pytest.raises(ValueError, match=r"Constraint 'cap'.*NaN"):
        _model(sense, math.nan).to_canonical()


def test_infinite_lhs_constant_counts_like_an_infinite_rhs():
    # x + inf <= 5 is x <= -inf: impossible.
    with pytest.raises(ValueError, match=r"Constraint 'cap'.*infinite"):
        _model("le", 5.0, constant=math.inf).to_canonical()


def test_finite_rhs_still_snaps_noise():
    row = _model("le", 0.3, constant=0.1 + 0.2).to_canonical().rows[0]
    assert row.rhs == 0.0


@pytest.mark.parametrize("solver", INTEGER_SOLVERS)
@pytest.mark.parametrize("sense, rhs, maximize, want",
                         [("le", math.inf, True, 10.0), ("ge", -math.inf, False, 0.0)])
def test_every_solver_ignores_a_vacuous_row(solver, sense, rhs, maximize, want):
    model = _model(sense, rhs, maximize=maximize, integer=solver == "cpsat")
    solution = solve_with(solver, model)
    assert solution.is_optimal()
    assert solution.objective_value == pytest.approx(want)
