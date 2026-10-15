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
