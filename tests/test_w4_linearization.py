"""W4 linearization regressions (catalog A14-A20, B7-B9) and the W3 carry-over."""
import itertools
import math
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from solver_matrix import AVAILABLE, solve_with  # noqa: E402
from test_canonical import fam  # noqa: E402

from lumix import (LXConstraint, LXLinearExpression, LXLinearizer, LXModel,
                   LXNonLinearExpression, LXOptimizer, LXQuadraticExpression, LXVariable)
from lumix.linearization import LXLinearizerConfig
from lumix.linearization.techniques.piecewise import LXPiecewiseLinearizer, adaptive_breakpoints
from lumix.solvers import ORTOOLS_CAPABILITIES


def lin(*pairs, const=0.0):
    e = LXLinearExpression()
    for v, c in pairs:
        e.add_term(v, c)
    return e.add_constant(const) if const else e


def cons(name, expr, sense, rhs):
    c = LXConstraint(name).expression(expr)
    return {"<=": c.le, ">=": c.ge, "==": c.eq}[sense]().rhs(rhs)


def model(vars_, constraints, sense, objective):
    m = LXModel("m")
    for v in vars_:
        m.add_variable(v)
    for c in constraints:
        m.add_constraint(c)
    return m.maximize(objective) if sense == "max" else m.minimize(objective)


def solve_lin(m, solver="ortools", config=None):
    lm = LXLinearizer(m, ORTOOLS_CAPABILITIES, config).linearize_model()
    return lm, solve_with(solver, lm)


def aux_count(lm, fragment):
    return sum(fragment in v.family for v in lm.to_canonical().variables)


# --- Görev 1: piecewise points, config, power (B8, B9, A20) --------------------------
@pytest.mark.parametrize("n", [1, 2, 4, 10, 20])
def test_b8_adaptive_breakpoints_have_num_segments(n):
    bp = adaptive_breakpoints(math.exp, 0.0, 3.0, n)
    assert len(bp) == n + 1 and bp[0] == 0.0 and bp[-1] == 3.0
    assert all(b > a for a, b in zip(bp, bp[1:]))


def test_b8_adaptive_breakpoints_are_deterministic_and_follow_curvature():
    runs = {tuple(adaptive_breakpoints(math.exp, 0.0, 3.0, 6)) for _ in range(5)}
    assert len(runs) == 1
    bp = next(iter(runs))
    widths = [b - a for a, b in zip(bp, bp[1:])]
    assert widths[-1] < widths[0]          # exp bends more on the right


def test_b8_linear_function_gets_uniform_breakpoints():
    assert adaptive_breakpoints(lambda t: 2 * t, 0.0, 3.0, 3) == pytest.approx([0, 1, 2, 3])


@pytest.mark.parametrize("method", ["sos2", "incremental", "logarithmic"])
@pytest.mark.parametrize("n", [1, 2])
def test_b8_few_adaptive_segments_solve(method, n):
    x = fam("x", ["k"], lower=0, upper=4)
    m = model([x], [cons("c", lin((x, 1)), "==", 4)], "min",
              LXNonLinearExpression().add_piecewise(x, lambda t: t * t, num_segments=n,
                                                    method=method))
    _, s = solve_lin(m)
    assert s.status == "optimal" and s.objective_value == pytest.approx(16)


def test_b9_config_applies_when_the_term_leaves_settings_open():
    x = fam("x", ["k"], lower=0, upper=4)
    m = model([x], [], "min", LXNonLinearExpression().add_piecewise(x, lambda t: t * t))
    cfg = LXLinearizerConfig(pwl_num_segments=4, pwl_method="incremental",
                             adaptive_breakpoints=False)
    lm = LXLinearizer(m, ORTOOLS_CAPABILITIES, cfg).linearize_model()
    assert aux_count(lm, "seg") == 4


def test_b9_term_settings_win_over_config():
    x = fam("x", ["k"], lower=0, upper=4)
    m = model([x], [], "min", LXNonLinearExpression().add_piecewise(
        x, lambda t: t * t, num_segments=2, method="incremental", adaptive=False))
    cfg = LXLinearizerConfig(pwl_num_segments=8, pwl_method="sos2")
    lm = LXLinearizer(m, ORTOOLS_CAPABILITIES, cfg).linearize_model()
    assert aux_count(lm, "seg") == 2


@pytest.mark.parametrize("field,value", [("prefer_sos2", False), ("tolerance", 1e-3),
                                         ("auto_detect_bounds", False), ("verbose_logging", False),
                                         ("mccormick_tighten_bounds", False)])
def test_b9_unused_config_fields_warn(field, value):
    with pytest.warns(DeprecationWarning, match=field):
        LXLinearizerConfig(**{field: value})


def test_b9_used_config_fields_do_not_warn():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        LXLinearizerConfig(pwl_num_segments=5, big_m_value=1e4, binary_expansion_bits=12)


def _solve_function(build, lower, upper, sense):
    x = fam("x", ["k"], lower=lower, upper=upper)
    pl = LXPiecewiseLinearizer(LXLinearizerConfig())
    y = build(x, pl)
    m = LXModel("f").add_variable(x)
    for v in pl.auxiliary_vars:
        m.add_variable(v)
    for c in pl.auxiliary_constraints:
        m.add_constraint(c)
    return solve_with("ortools", m.maximize(lin((y, 1))) if sense == "max"
                      else m.minimize(lin((y, 1))))


def test_a20_power_of_negative_inputs():
    from lumix.linearization.functions import LXNonLinearFunctions as F
    assert _solve_function(lambda x, pl: F.power(x, 2, pl), -3, 1, "max").objective_value \
        == pytest.approx(9, abs=1e-6)
    assert _solve_function(lambda x, pl: F.power(x, 3, pl), -2, 1, "min").objective_value \
        == pytest.approx(-8, abs=1e-6)


def test_a20_fractional_power_of_negative_input_raises():
    from lumix.linearization.functions import LXNonLinearFunctions as F
    with pytest.raises(ValueError, match="not real"):
        _solve_function(lambda x, pl: F.power(x, 0.5, pl), -1, 4, "max")
# --- Görev 2: canonical nonlinear items (A16, spec §3.1 rule 2) ----------------------
def test_a16_canonical_items_are_per_instance():
    x = fam("x", ["p", "q"], lower=-10, upper=10)
    m = LXModel("m").add_variable(x).minimize(LXNonLinearExpression().add_abs(x, coeff=2.0))
    items = m.to_canonical().objective_nonlinear
    assert [(i.kind, i.variables, i.coeff, i.key) for i in items] == [
        ("abs", (0,), 2.0, "p"), ("abs", (1,), 2.0, "q")]


def test_a16_single_variable_is_broadcast_over_a_family():
    x = fam("x", ["p", "q"], lower=0, upper=5)
    s = fam("s", ["only"], lower=0, upper=5)
    m = LXModel("m").add_variables(x, s).maximize(LXNonLinearExpression().add_min(x, s))
    items = m.to_canonical().objective_nonlinear
    assert [(i.kind, i.variables, i.key, i.params["coefficients"]) for i in items] == [
        ("min", (0, 2), "p", (1.0, 1.0)), ("min", (1, 2), "q", (1.0, 1.0))]


def test_a16_families_with_different_keys_raise():
    x = fam("x", ["p", "q"], lower=0, upper=5)
    y = fam("y", ["p", "r"], lower=0, upper=5)
    m = LXModel("m").add_variables(x, y).maximize(LXNonLinearExpression().add_product(x, y))
    with pytest.raises(ValueError, match="different index keys"):
        m.to_canonical()


def test_canonical_piecewise_item_has_numeric_points():
    x = fam("x", ["k"], lower=0, upper=4)
    m = LXModel("m").add_variable(x).minimize(LXNonLinearExpression().add_piecewise(
        x, lambda t: t * t, breakpoints=[0, 2, 4], method="incremental"))
    (item,) = m.to_canonical().objective_nonlinear
    assert item.kind == "piecewise" and item.params == {
        "breakpoints": (0.0, 2.0, 4.0), "values": (0.0, 4.0, 16.0), "method": "incremental"}


def test_nonlinear_expression_constant_is_kept():
    x = fam("x", ["k"], lower=1, upper=4)
    e = LXNonLinearExpression().add_linear(lin((x, 1.0)))
    e.constant = 5.0
    m = LXModel("m").add_variable(x).minimize(e)
    assert m.to_canonical().objective_constant == 5.0
    assert solve_with("ortools", m).objective_value == pytest.approx(6.0)


def test_indicator_in_objective_needs_linearization_for_canonical():
    from lumix.nonlinear.terms import LXIndicatorTerm
    x, b = fam("x", ["k"], lower=0, upper=4), fam("b", ["k"], "binary")
    e = LXNonLinearExpression().add_nonlinear_term(LXIndicatorTerm(b, True, lin((x, 1)), "<=", 2))
    m = LXModel("m").add_variables(x, b).maximize(e)
    with pytest.raises(ValueError, match="indicator"):
        m.to_canonical()


@pytest.mark.parametrize("solver", AVAILABLE)
def test_solvers_still_require_linearization(solver):
    x = fam("x", ["k"], lower=-3, upper=5)
    m = LXModel("m").add_variable(x).minimize(LXNonLinearExpression().add_abs(x))
    with pytest.raises(ValueError, match="enable_linearization"):
        solve_with(solver, m)


# --- Görev 3: item-based linearizer (A15, A16, A17 name collisions) ----------------
def test_a15_repeated_solves_do_not_drift_or_change_the_model():
    a, b = fam("a", ["k"], lower=0, upper=10), fam("b", ["k"], lower=0, upper=10)
    e = LXNonLinearExpression().add_min(a, b).add_linear(lin((a, 1.0)))
    e.constant = 5.0
    m = model([a, b], [cons("cap", lin((a, 1), (b, 1)), "<=", 8)], "max", e)
    snapshot = (dict(e.linear_terms.terms), e.linear_terms.constant, e.constant,
                list(e.nonlinear_terms))
    opt = LXOptimizer().use_solver("ortools").enable_linearization()
    assert [opt.solve(m).objective_value for _ in range(3)] == pytest.approx([13, 13, 13])
    assert (dict(e.linear_terms.terms), e.linear_terms.constant, e.constant,
            list(e.nonlinear_terms)) == snapshot


def test_a15_linearize_model_twice_gives_the_same_model():
    x = fam("x", ["p", "q"], lower=-4, upper=4)
    m = model([x], [], "min", LXNonLinearExpression().add_abs(x))
    lz = LXLinearizer(m, ORTOOLS_CAPABILITIES)
    first, second = lz.linearize_model(), lz.linearize_model()
    assert [v.name for v in first.variables] == [v.name for v in second.variables]
    assert [c.name for c in first.constraints] == [c.name for c in second.constraints]
    assert len(lz.auxiliary_vars) == len(first.variables) - 1


def test_a16_abs_on_a_family_is_a_sum_over_instances():
    x = fam("x", ["p", "q"], lower=-10, upper=10)
    cs = [cons("xp", LXLinearExpression().add_term(x, 1.0, keys=["p"]), ">=", 3),
          cons("xq", LXLinearExpression().add_term(x, 1.0, keys=["q"]), "<=", -3)]
    _, s = solve_lin(model([x], cs, "min", LXNonLinearExpression().add_abs(x)))
    assert s.objective_value == pytest.approx(6)


def test_a16_piecewise_on_a_family():
    x = fam("x", ["p", "q"], lower=0, upper=6)
    cs = [cons("xp", LXLinearExpression().add_term(x, 1.0, keys=["p"]), "==", 1),
          cons("xq", LXLinearExpression().add_term(x, 1.0, keys=["q"]), "==", 5)]
    e = LXNonLinearExpression().add_piecewise(x, lambda t: (t - 3) ** 2, num_segments=6,
                                              adaptive=False)
    _, s = solve_lin(model([x], cs, "min", e))
    assert s.status == "optimal" and s.objective_value == pytest.approx(8)


def test_a16_aux_values_are_reported_per_instance():
    x = fam("x", ["p", "q"], lower=-10, upper=10)
    cs = [cons("xp", LXLinearExpression().add_term(x, 1.0, keys=["p"]), "==", 3),
          cons("xq", LXLinearExpression().add_term(x, 1.0, keys=["q"]), "==", -4)]
    lm, s = solve_lin(model([x], cs, "min", LXNonLinearExpression().add_abs(x)))
    (z,) = [v.name for v in lm.variables if v.name.startswith("aux_abs_x_")]
    assert s.variables[z] == pytest.approx({"p": 3.0, "q": 4.0})


def test_a17_two_terms_on_the_same_variables_do_not_collide():
    a, b = fam("a", ["k"], lower=0, upper=10), fam("b", ["k"], lower=0, upper=10)
    e = LXNonLinearExpression().add_min(a, b).add_min(a, b, coefficients=[3.0, 1.0])
    lm, s = solve_lin(model([a, b], [cons("fa", lin((a, 1)), "==", 2),
                                     cons("fb", lin((b, 1)), "==", 6)], "max", e))
    assert s.objective_value == pytest.approx(8)
    names = [v.name for v in lm.variables]
    rows = [c.name for c in lm.constraints]
    assert len(set(names)) == len(names) and len(set(rows)) == len(rows)


# --- Görev 4: nonconvex abs/min/max are exact (A17) ---------------------------------
@pytest.mark.parametrize("sense,op,expected", [("max", "max", 8), ("min", "max", 0),
                                               ("max", "min", 4), ("min", "min", 0)])
def test_a17_min_max_in_both_directions(sense, op, expected):
    a, b = fam("a", ["k"], lower=0, upper=10), fam("b", ["k"], lower=0, upper=10)
    e = getattr(LXNonLinearExpression(), "add_" + op)(a, b)
    _, s = solve_lin(model([a, b], [cons("cap", lin((a, 1), (b, 1)), "<=", 8)], sense, e))
    assert s.status == "optimal" and s.objective_value == pytest.approx(expected)


@pytest.mark.parametrize("sense,coeff,lower_x,expected", [
    ("max", 1.0, None, 5), ("max", 1.0, 1, 2), ("min", -1.0, 1, -2)])
def test_a17_nonconvex_abs(sense, coeff, lower_x, expected):
    x = fam("x", ["k"], lower=-5, upper=2)
    cs = [] if lower_x is None else [cons("c", lin((x, 1)), ">=", lower_x)]
    _, s = solve_lin(model([x], cs, sense, LXNonLinearExpression().add_abs(x, coeff=coeff)))
    assert s.objective_value == pytest.approx(expected)


def test_a17_abs_twice_on_one_variable():
    x = fam("x", ["k"], lower=-5, upper=2)
    e = LXNonLinearExpression().add_abs(x).add_abs(x, coeff=2.0)
    _, s = solve_lin(model([x], [cons("c", lin((x, 1)), "<=", -1)], "min", e))
    assert s.objective_value == pytest.approx(3)


def test_a17_exact_form_needs_bounds():
    x = fam("x", ["k"])
    with pytest.raises(ValueError, match="finite bounds"):
        solve_lin(model([x], [], "max", LXNonLinearExpression().add_abs(x)))


def test_a17_convex_use_needs_no_bounds():
    x = fam("x", ["k"])
    _, s = solve_lin(model([x], [cons("c", lin((x, 1)), ">=", -3)], "min",
                           LXNonLinearExpression().add_abs(x)))
    assert s.objective_value == pytest.approx(0)


# --- Görev 5: products (A14, A18), quadratic objectives, relaxation flag -------------
@pytest.mark.parametrize("lo,hi,sense,coeff", [(0, 10, "max", 1.0), (0, 10, "min", 1.0),
                                               (2, 10, "max", 1.0), (2, 10, "min", -1.0),
                                               (-5, 10, "max", 1.0), (-5, 10, "min", 1.0)])
def test_a14_binary_times_continuous(lo, hi, sense, coeff):
    b, x = fam("b", ["k"], "binary"), fam("x", ["k"], lower=lo, upper=hi)
    e = LXNonLinearExpression().add_product(b, x, coeff=coeff).add_linear(lin((x, -0.1)))
    _, s = solve_lin(model([b, x], [], sense, e))
    cands = [coeff * bb * xx - 0.1 * xx for bb in (0, 1) for xx in (lo, hi)]
    assert s.objective_value == pytest.approx(max(cands) if sense == "max" else min(cands))


def test_a14_fixed_zero_binary_keeps_x_free():
    b, x = fam("b", ["k"], "binary"), fam("x", ["k"], lower=0, upper=10)
    e = LXNonLinearExpression().add_product(b, x, coeff=0.0).add_linear(lin((x, 1.0)))
    _, s = solve_lin(model([b, x], [cons("b0", lin((b, 1)), "==", 0)], "max", e))
    assert s.status == "optimal" and s.objective_value == pytest.approx(10)


@pytest.mark.parametrize("sense", ["max", "min"])
@pytest.mark.parametrize("c", [3.0, -3.0])
def test_a18_binary_times_binary(sense, c):
    a, b = fam("a", ["k"], "binary"), fam("b", ["k"], "binary")
    e = LXNonLinearExpression().add_product(a, b, coeff=c).add_linear(lin((a, -1), (b, -1)))
    _, s = solve_lin(model([a, b], [], sense, e))
    vals = [c * x * y - x - y for x, y in itertools.product((0, 1), (0, 1))]
    assert s.objective_value == pytest.approx(max(vals) if sense == "max" else min(vals))


def test_a18_integer_product_is_exact():
    x, y = fam("x", ["k"], "integer", 0, 3), fam("y", ["k"], "integer", 0, 3)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        _, s = solve_lin(model([x, y], [cons("c", lin((x, 1), (y, 1)), "<=", 3)], "max",
                               LXNonLinearExpression().add_product(x, y)))
    assert s.objective_value == pytest.approx(2) and not s.relaxation


def test_a18_integer_with_fractional_bounds():
    x, y = fam("x", ["k"], "integer", 0.5, 3.7), fam("y", ["k"], lower=-2, upper=1.5)
    _, s = solve_lin(model([x, y], [], "min", LXNonLinearExpression().add_product(x, y)))
    assert s.objective_value == pytest.approx(-6)          # x = 3, y = -2


def test_a18_continuous_product_is_a_flagged_relaxation():
    x, y = fam("x", ["k"], lower=0, upper=10), fam("y", ["k"], lower=0, upper=10)
    m = model([x, y], [cons("c", lin((x, 1), (y, 1)), "<=", 10)], "max",
              LXNonLinearExpression().add_product(x, y))
    with pytest.warns(UserWarning, match="McCormick"):
        s = LXOptimizer().use_solver("ortools").enable_linearization().solve(m)
    assert s.relaxation is True


def test_a18_expansion_bit_limit():
    x, y = fam("x", ["k"], "integer", 0, 5000), fam("y", ["k"], lower=0, upper=1)
    m = model([x, y], [], "max", LXNonLinearExpression().add_product(x, y))
    with pytest.raises(ValueError, match="binary_expansion_bits"):
        solve_lin(m, config=LXLinearizerConfig(binary_expansion_bits=10))


def test_a16_product_on_families_is_per_instance():
    K = ["p", "q"]
    y = fam("y", K, lower=0, upper=4)
    b = fam("b", K, "binary")
    cs = [cons("bp", LXLinearExpression().add_term(b, 1.0, keys=["p"]), "==", 1),
          cons("bq", LXLinearExpression().add_term(b, 1.0, keys=["q"]), "==", 0),
          cons("yq", LXLinearExpression().add_term(y, 1.0, keys=["q"]), "==", 4)]
    _, s = solve_lin(model([y, b], cs, "max", LXNonLinearExpression().add_product(b, y)))
    assert s.objective_value == pytest.approx(4)


def test_quadratic_family_squares_through_linearization():
    a = fam("a", ["k", "l"], "binary")
    m = LXModel("m").add_variable(a).maximize(LXQuadraticExpression().add_squared(a, 1.0))
    s = LXOptimizer().use_solver("ortools").enable_linearization().solve(m)
    assert s.objective_value == pytest.approx(2.0) and not s.relaxation


def test_quadratic_stays_native_on_qp_solvers():
    solvers = [s for s in ("gurobi", "cplex") if s in AVAILABLE]
    if not solvers:
        pytest.skip("needs gurobi or cplex")
    x = fam("x", ["k"], lower=0, upper=4)
    q = LXQuadraticExpression().add_squared(x, 1.0) + lin((x, -4.0), const=4.0)
    m = model([x], [], "min", q)
    for solver in solvers:
        with warnings.catch_warnings():
            warnings.simplefilter("error")         # no McCormick warning: stays native
            s = LXOptimizer().use_solver(solver).enable_linearization().solve(m)
        assert s.objective_value == pytest.approx(0, abs=1e-6) and not s.relaxation
        y = fam("y", ["k"], lower=-3, upper=2)
        e = LXNonLinearExpression().add_abs(y).add_linear(lin((y, 1.0)))
        s = LXOptimizer().use_solver(solver).enable_linearization().solve(model([y], [], "max", e))
        assert s.objective_value == pytest.approx(4)


# --- Görev 6: indicators (A19) and nonlinear terms in constraints (B7) -------------
def _indicator_brute(cond, sense, rhs, objsense, w, const):
    best = None
    for bv in (0, 1):
        for xv in [i / 2 for i in range(-20, 21)]:
            active = (bv == 1) == cond
            lhs = xv + const
            ok = (not active) or (lhs <= rhs + 1e-9 if sense == "<=" else
                                  lhs >= rhs - 1e-9 if sense == ">=" else abs(lhs - rhs) < 1e-9)
            if ok:
                o = xv + w * bv
                if best is None or (o > best if objsense == "max" else o < best):
                    best = o
    return best


@pytest.mark.parametrize("cond", [True, False])
@pytest.mark.parametrize("sense", ["<=", ">=", "=="])
@pytest.mark.parametrize("objsense,w", [("max", 1.0), ("min", -1.0)])
@pytest.mark.parametrize("const", [0.0, 3.0])
def test_a19_indicator_matches_brute_force(cond, sense, objsense, w, const):
    from lumix.nonlinear.terms import LXIndicatorTerm
    x, b = fam("x", ["k"], lower=-10, upper=10), fam("b", ["k"], "binary")
    e = LXNonLinearExpression().add_nonlinear_term(
        LXIndicatorTerm(b, cond, lin((x, 1), const=const), sense, 2.0))
    e.add_linear(lin((x, 1), (b, w)))
    _, s = solve_lin(model([x, b], [], objsense, e))
    assert s.objective_value == pytest.approx(_indicator_brute(cond, sense, 2.0, objsense, w, const))


def test_a19_two_indicators_on_one_binary():
    x, y, b = (fam("x", ["k"], lower=-10, upper=10), fam("y", ["k"], lower=-10, upper=10),
               fam("b", ["k"], "binary"))
    e = (LXNonLinearExpression().add_indicator(b, True, lin((x, 1)))
         .add_indicator(b, True, lin((y, 1))))
    e.add_linear(lin((x, 1), (y, 1), (b, 5)))
    _, s = solve_lin(model([x, y, b], [], "max", e))
    assert s.objective_value == pytest.approx(20)


def test_a19_indicator_needs_a_single_binary():
    from lumix.nonlinear.terms import LXIndicatorTerm
    x, b = fam("x", ["k"], lower=0, upper=4), fam("b", ["p", "q"], "binary")
    e = LXNonLinearExpression().add_nonlinear_term(LXIndicatorTerm(b, True, lin((x, 1)), "<=", 2))
    with pytest.raises(ValueError, match="single variable"):
        solve_lin(model([x, b], [], "max", e.add_linear(lin((x, 1)))))


@pytest.mark.parametrize("path", ["optimizer", "linearizer"])
def test_b7_abs_in_a_constraint(path):
    x = fam("x", ["k"], lower=-10, upper=10)
    m = model([x], [LXConstraint("absle").expression(LXNonLinearExpression().add_abs(x)).le()
                    .rhs(2)], "max", lin((x, 1)))
    assert LXLinearizer(m, ORTOOLS_CAPABILITIES).needs_linearization()
    s = (LXOptimizer().use_solver("ortools").enable_linearization().solve(m)
         if path == "optimizer" else solve_lin(m)[1])
    assert s.objective_value == pytest.approx(2)


@pytest.mark.parametrize("sense,rhs,expected", [(">=", 2, 2), ("==", 3, -3)])
def test_b7_nonconvex_constraint_uses_are_exact(sense, rhs, expected):
    x = fam("x", ["k"], lower=-1 if sense == ">=" else -5, upper=5)
    c = cons("absc", LXNonLinearExpression().add_abs(x), sense, rhs)
    _, s = solve_lin(model([x], [c], "min", lin((x, 1))))
    assert s.objective_value == pytest.approx(expected)


def test_b7_integer_square_in_a_constraint():
    x = fam("x", ["k"], "integer", 0, 10)
    c = cons("sq", LXNonLinearExpression().add_product(x, x), "<=", 4)
    _, s = solve_lin(model([x], [c], "max", lin((x, 1))))
    assert s.objective_value == pytest.approx(2)


@dataclass(frozen=True)
class P:
    id: str
    cap: float


def test_b7_indexed_constraint_narrows_with_broadcast():
    ps = [P("a", 3.0), P("b", 5.0)]
    x = LXVariable[P, float]("x").continuous().bounds(lower=0, upper=10).indexed_by(
        lambda p: p.id).from_data(ps)
    s_ = fam("s", ["only"], lower=0, upper=10)
    row = (LXConstraint[P]("cap").expression(LXNonLinearExpression().add_max(x, s_)).le()
           .rhs(lambda p: p.cap).indexed_by(lambda p: p.id).from_data(ps))
    m = model([x, s_], [row], "max", lin((x, 1), (s_, 1)))
    _, s = solve_lin(m)
    assert s.objective_value == pytest.approx(3 + 5 + 3)      # s <= min(cap) = 3


def test_b7_row_of_other_data_sees_every_instance():
    ps = [P("a", 0.0), P("b", 0.0)]
    x = LXVariable[P, float]("x").continuous().bounds(lower=-4, upper=4).indexed_by(
        lambda p: p.id).from_data(ps)
    budgets = [("r", 5.0)]
    row = (LXConstraint("budget").expression(LXNonLinearExpression().add_abs(x)).le()
           .rhs(lambda r: r[1]).indexed_by(lambda r: r[0]).from_data(budgets))
    _, s = solve_lin(model([x], [row], "max", lin((x, 1))))
    assert s.objective_value == pytest.approx(5)              # |x_a| + |x_b| <= 5


def test_b7_same_term_in_objective_and_constraint():
    x = fam("x", ["k"], lower=-5, upper=5)
    e = LXNonLinearExpression().add_abs(x)
    c = LXConstraint("c").expression(e).ge().rhs(2)
    lm, s = solve_lin(model([x], [c], "min", e))
    assert s.objective_value == pytest.approx(2)
    names = [v.name for v in lm.variables]
    assert len(set(names)) == len(names)
