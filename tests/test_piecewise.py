"""
Exactness of piecewise-linear terms.

Every formulation must reproduce the piecewise-linear function through its
breakpoints exactly, also when the function is nonconvex (a convex-combination
relaxation would not). Results are compared with brute force: the optimum of a
piecewise-linear function plus a linear term over an interval lies at a
breakpoint or at an end of the interval.
"""

import random

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
from lumix.solvers import ORTOOLS_CAPABILITIES

METHODS = ["sos2", "incremental", "logarithmic"]


def scalar(name, lower, upper):
    return (
        LXVariable[str, float](name)
        .continuous()
        .bounds(lower=lower, upper=upper)
        .indexed_by(lambda k: k)
        .from_data([name])
    )


def interpolate(points):
    def f(x):
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            if x <= x1:
                return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
        return points[-1][1]
    return f


def solve(sense, terms, X, at_most=None, linear=0.0, solver="ortools"):
    model = LXModel("pwl")
    model.add_variable(X)
    if at_most is not None:
        model.add_constraint(
            LXConstraint("cap").expression(LXLinearExpression().add_term(X, 1)).le().rhs(at_most))
    expr = LXNonLinearExpression()
    if linear:
        expr.add_linear(LXLinearExpression().add_term(X, linear))
    for kwargs in terms:
        expr.add_piecewise(X, **kwargs)
    model.maximize(expr) if sense == "max" else model.minimize(expr)
    linearized = LXLinearizer(model, ORTOOLS_CAPABILITIES).linearize_model()
    return LXOptimizer().use_solver(solver).solve(linearized)


def random_cases(count, seed):
    rng = random.Random(seed)
    for _ in range(count):
        k = rng.randint(2, 10)
        xs = sorted(x / 2 for x in rng.sample(range(41), k))
        points = [(x, rng.randint(-20, 20)) for x in xs]
        cap = rng.uniform(xs[0], xs[-1])
        yield points, cap, rng.choice([-1, 0, 0.5]), rng.choice(["min", "max"])


def brute_force(points, cap, linear, sense):
    f = interpolate(points)
    candidates = [x for x, _ in points if x <= cap] + [cap]
    values = [f(x) + linear * x for x in candidates]
    return max(values) if sense == "max" else min(values)


@pytest.mark.parametrize("method", METHODS)
def test_random_piecewise_functions_are_exact(method):
    for points, cap, linear, sense in random_cases(40, seed=7):
        X = scalar("x", points[0][0], points[-1][0])
        term = dict(func=interpolate(points), breakpoints=[x for x, _ in points], method=method)
        solution = solve(sense, [term], X, at_most=cap, linear=linear)
        assert solution.status == "optimal", (points, cap, linear, sense)
        assert solution.objective_value == pytest.approx(
            brute_force(points, cap, linear, sense), abs=1e-6), (points, cap, linear, sense)


@pytest.mark.parametrize("method", METHODS)
def test_nonconvex_maximum_is_not_relaxed(method):
    # A convex-combination relaxation mixes (0, 10) and (20, 30) and reaches 25 at x = 15.
    points = [(0, 10), (5, 2), (20, 30)]
    X = scalar("x", 0, 20)
    term = dict(func=interpolate(points), breakpoints=[0, 5, 20], method=method)
    solution = solve("max", [term], X, at_most=15)
    assert solution.objective_value == pytest.approx(2 + 28 * 10 / 15, abs=1e-6)


@pytest.mark.parametrize("segments", range(1, 10))
def test_logarithmic_handles_any_segment_count(segments):
    xs = list(range(segments + 1))
    points = [(x, (x % 2) * 10 - x) for x in xs]   # zig-zag: nonconvex
    X = scalar("x", 0, segments)
    term = dict(func=interpolate(points), breakpoints=xs, method="logarithmic")
    for cap in (0.5, segments - 0.5, segments):
        solution = solve("max", [term], X, at_most=cap)
        assert solution.objective_value == pytest.approx(
            brute_force(points, cap, 0.0, "max"), abs=1e-6), (segments, cap)


def test_breakpoints_are_used_as_given():
    points = [(0, 0), (0.25, 1), (1.5, 0), (2, 0)]
    X = scalar("x", 0, 2)
    term = dict(func=interpolate(points), breakpoints=[0, 0.25, 1.5, 2], method="incremental")
    solution = solve("max", [term], X)
    assert solution.objective_value == pytest.approx(1, abs=1e-6)
    assert solution.variables["x"]["x"] == pytest.approx(0.25, abs=1e-6)


@pytest.mark.parametrize("breakpoints", [[1], [0, 0, 1], [0, 2, 1]])
def test_breakpoints_must_increase(breakpoints):
    X = scalar("x", 0, 2)
    with pytest.raises(ValueError, match="breakpoints"):
        solve("max", [dict(func=lambda x: x, breakpoints=breakpoints)], X)


def test_breakpoints_and_domain_are_exclusive():
    X = scalar("x", 0, 2)
    with pytest.raises(ValueError, match="breakpoints"):
        solve("max", [dict(func=lambda x: x, breakpoints=[0, 2], x_min=0)], X)


def test_zero_lower_domain_bound_is_honoured():
    # x_min=0 used to be ignored (falsy) and replaced by the variable's bound -5.
    X = scalar("x", -5, 5)
    term = dict(func=lambda x: 0.0, x_min=0, x_max=5, num_segments=5, adaptive=False,
                method="incremental")
    with pytest.warns(UserWarning, match="restricts"):
        solution = solve("min", [term], X, linear=1.0)
    assert solution.objective_value == pytest.approx(0, abs=1e-6)


def test_domain_narrower_than_bounds_warns():
    X = scalar("x", 0, 20)
    with pytest.warns(UserWarning, match=r"restricts x to \[0(\.0)?, 5(\.0)?\]"):
        solve("max", [dict(func=lambda x: x, breakpoints=[0, 5])], X)


def test_two_piecewise_terms_on_one_variable():
    up = [(0, 0), (10, 10)]
    tent = [(0, 0), (4, 8), (10, 0)]
    X = scalar("x", 0, 10)
    terms = [dict(func=interpolate(up), breakpoints=[0, 10], method=m)
             for m in ("sos2",)] + [dict(func=interpolate(tent), breakpoints=[0, 4, 10],
                                         method="sos2")]
    solution = solve("max", terms, X)
    assert solution.objective_value == pytest.approx(12, abs=1e-6)


def test_random_piecewise_functions_on_gurobi():
    pytest.importorskip("gurobipy")
    for points, cap, linear, sense in random_cases(15, seed=11):
        for method in METHODS:
            X = scalar("x", points[0][0], points[-1][0])
            term = dict(func=interpolate(points), breakpoints=[x for x, _ in points],
                        method=method)
            solution = solve(sense, [term], X, at_most=cap, linear=linear, solver="gurobi")
            assert solution.objective_value == pytest.approx(
                brute_force(points, cap, linear, sense), abs=1e-5), (method, points, cap)
