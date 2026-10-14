"""
Tests for LXLinearizer on nonlinear objectives.

Each case has a known optimum; minimization and maximization are both covered
because the linearized model must keep the original objective sense.
"""

import pytest

pytest.importorskip("ortools")

from lumix import (
    LXConstraint,
    LXLinearExpression,
    LXLinearizer,
    LXModel,
    LXNonLinearExpression,
    LXOptimizer,
    LXVariable,
)
from lumix.core.enums import LXObjectiveSense
from lumix.solvers import ORTOOLS_CAPABILITIES


def scalar(name, lower, upper):
    return (
        LXVariable[str, float](name)
        .continuous()
        .bounds(lower=lower, upper=upper)
        .indexed_by(lambda k: k)
        .from_data([name])
    )


def solve_linearized(sense, objective, x=(2, 10), y=(2, 10), sum_at_least=None):
    X, Y = scalar("x", *x), scalar("y", *y)
    model = LXModel("nl")
    model.add_variable(X)
    model.add_variable(Y)
    if sum_at_least is not None:
        model.add_constraint(
            LXConstraint("sum")
            .expression(LXLinearExpression().add_term(X, 1).add_term(Y, 1))
            .ge()
            .rhs(sum_at_least)
        )
    expr = objective(X, Y)
    if sense == "max":
        model.maximize(expr)
    else:
        model.minimize(expr)
    linearized = LXLinearizer(model, ORTOOLS_CAPABILITIES).linearize_model()
    return linearized, LXOptimizer().use_solver("ortools").solve(linearized)


def parabola_down(t):
    return 9 - (t - 3) ** 2


def parabola_up(t):
    return (t - 3) ** 2


CASES = [
    ("max product", "max", 100, dict(sum_at_least=10),
     lambda X, Y: LXNonLinearExpression().add_product(X, Y)),
    ("min product", "min", 16, dict(sum_at_least=10),
     lambda X, Y: LXNonLinearExpression().add_product(X, Y)),
    ("max min", "max", 4, dict(x=(0, 4), y=(0, 6)),
     lambda X, Y: LXNonLinearExpression().add_min(X, Y)),
    ("min max", "min", 5, dict(x=(3, 9), y=(5, 9)),
     lambda X, Y: LXNonLinearExpression().add_max(X, Y)),
    ("min abs", "min", 2, dict(x=(2, 5)),
     lambda X, Y: LXNonLinearExpression().add_abs(X)),
    ("min piecewise", "min", 0, dict(x=(0, 6)),
     lambda X, Y: LXNonLinearExpression().add_piecewise(
         X, parabola_up, num_segments=6, adaptive=False)),
    ("max piecewise", "max", 9, dict(x=(0, 6)),
     lambda X, Y: LXNonLinearExpression().add_piecewise(
         X, parabola_down, num_segments=6, adaptive=False)),
    ("max piecewise plus linear", "max", 19, dict(x=(0, 6)),
     lambda X, Y: LXNonLinearExpression()
     .add_linear(LXLinearExpression().add_term(Y, 1))
     .add_piecewise(X, parabola_down, num_segments=6, adaptive=False)),
]


@pytest.mark.parametrize("label,sense,expected,bounds,objective", CASES,
                         ids=[c[0] for c in CASES])
def test_linearized_objective_reaches_known_optimum(label, sense, expected, bounds, objective):
    _, solution = solve_linearized(sense, objective, **bounds)
    assert solution.status == "optimal"
    assert solution.objective_value == pytest.approx(expected, abs=1e-6)


@pytest.mark.parametrize("sense", ["min", "max"])
def test_linearized_model_keeps_objective_sense(sense):
    linearized, _ = solve_linearized(
        sense, lambda X, Y: LXNonLinearExpression().add_product(X, Y), sum_at_least=10)
    expected = LXObjectiveSense.MAXIMIZE if sense == "max" else LXObjectiveSense.MINIMIZE
    assert linearized.objective_sense == expected


def test_enable_linearization_linearizes_during_solve():
    X, Y = scalar("x", 2, 10), scalar("y", 2, 10)
    model = LXModel("auto")
    model.add_variable(X)
    model.add_variable(Y)
    model.maximize(LXNonLinearExpression().add_product(X, Y))
    solution = LXOptimizer().use_solver("ortools").enable_linearization().solve(model)
    assert solution.status == "optimal"
    assert solution.objective_value == pytest.approx(100, abs=1e-6)
