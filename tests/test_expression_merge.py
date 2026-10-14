"""Adding expressions or terms that share a variable must keep every term."""

import pytest

pytest.importorskip("ortools")

from lumix import LXConstraint, LXLinearExpression, LXModel, LXVariable
from lumix.solvers.ortools_solver import LXORToolsSolver

ITEMS = ["a", "b", "c"]


def var():
    return (
        LXVariable[str, float]("x").continuous().bounds(lower=0)
        .indexed_by(lambda k: k).from_data(ITEMS)
    )


def row_coefficients(x, expr) -> dict:
    model = LXModel("m")
    model.add_variable(x)
    model.add_constraint(LXConstraint("row").expression(expr).le().rhs(10))
    solver = LXORToolsSolver()
    solver.build_model(model)
    row = solver._constraint_map["row"]
    return {v.name(): row.GetCoefficient(v)
            for v in solver._solver.variables() if row.GetCoefficient(v)}


def test_adding_expressions_with_the_same_variable_keeps_all_terms():
    x = var()
    e1 = LXLinearExpression().add_term(x, 1.0, where=lambda k: k in ("a", "b"))
    e2 = LXLinearExpression().add_term(x, 2.0, where=lambda k: k in ("b", "c"))
    assert row_coefficients(x, e1 + e2) == {"x[a]": 1.0, "x[b]": 3.0, "x[c]": 2.0}


def test_add_term_twice_on_the_same_variable_keeps_both():
    x = var()
    expr = (LXLinearExpression()
            .add_term(x, 1.0, where=lambda k: k == "a")
            .add_term(x, 2.0, where=lambda k: k == "c"))
    assert row_coefficients(x, expr) == {"x[a]": 1.0, "x[c]": 2.0}


def test_merged_coefficients_keep_constraint_instance_argument():
    x = var()
    expr = (LXLinearExpression()
            .add_term(x, lambda k, row=None: 1.0)
            .add_term(x, 2.0, where=lambda k: k == "b"))
    assert row_coefficients(x, expr) == {"x[a]": 1.0, "x[b]": 3.0, "x[c]": 1.0}


def test_scaling_an_expression_scales_every_term_and_the_constant():
    x = var()
    expr = LXLinearExpression().add_term(x, 3.0, where=lambda k: k != "b").add_constant(1.0)
    scaled = expr * 2
    assert row_coefficients(x, scaled) == {"x[a]": 6.0, "x[c]": 6.0}
    assert scaled.constant == 2.0


def test_scaling_scales_multi_terms():
    x = var()
    expr = LXLinearExpression().add_multi_term(x, coeff=lambda k: 4.0) * 0.5
    assert row_coefficients(x, expr) == {"x[a]": 2.0, "x[b]": 2.0, "x[c]": 2.0}
