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
