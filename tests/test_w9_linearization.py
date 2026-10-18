"""W9a/W9b (0.3.2): linearization inputs and keys."""
import math

import pytest

from lumix import (LXLinearExpression, LXModel, LXOptimizer, LXQuadraticExpression,
                   LXVariable)
from lumix.linearization import LXLinearizerConfig
from lumix.linearization.functions import LXNonLinearFunctions
from lumix.linearization.techniques.piecewise import LXPiecewiseLinearizer, piecewise_points


@pytest.mark.parametrize("n", [0, -1])
def test_w9_num_segments_below_one_raises(n):
    with pytest.raises(ValueError, match="num_segments must be an integer >= 1"):
        piecewise_points(math.exp, 0.0, 10.0, LXLinearizerConfig(), name="x",
                         num_segments=n, adaptive=False)


def test_w9_config_rejects_zero_segments():
    with pytest.raises(ValueError, match="pwl_num_segments must be an integer >= 1"):
        LXLinearizerConfig(pwl_num_segments=0)


def test_w9_nonfinite_piecewise_value_raises():
    with pytest.raises(ValueError, match="is not finite"):
        piecewise_points(lambda t: math.inf if t > 5 else t, 0.0, 10.0,
                         LXLinearizerConfig(), name="x", num_segments=4, adaptive=False)


def _var(lo, hi):
    return LXVariable[None, float]("x").continuous().bounds(lo, hi)


@pytest.mark.parametrize("fn, lo, hi", [
    (LXNonLinearFunctions.log, 0.0, 10.0),
    (LXNonLinearFunctions.sqrt, -1.0, 4.0),
    (LXNonLinearFunctions.tan, 0.0, 2.0),          # crosses pi/2
])
def test_w9_function_outside_its_domain_raises(fn, lo, hi):
    lin = LXPiecewiseLinearizer(LXLinearizerConfig())
    with pytest.raises(ValueError):
        fn(_var(lo, hi), lin)


def test_w9_log_on_positive_domain_has_no_sentinel():
    lin = LXPiecewiseLinearizer(LXLinearizerConfig())
    out = LXNonLinearFunctions.log(_var(0.5, 10.0), lin)
    assert out.lower_bound > -1e9


def test_w9_functions_follow_the_config_segments():
    cfg = LXLinearizerConfig(pwl_num_segments=3, adaptive_breakpoints=False)
    lin = LXPiecewiseLinearizer(cfg)
    LXNonLinearFunctions.exp(_var(0.0, 1.0), lin)
    # The SOS2 weights are one auxiliary variable per breakpoint, named ..._lam<i>.
    lambdas = [v for v in lin.auxiliary_vars if "_lam" in v.name]
    assert len(lambdas) == 4


def test_w9_indicator_term_with_bad_sense_raises_value_error():
    from lumix.nonlinear.terms import LXIndicatorTerm
    b = LXVariable[None, int]("b").binary()
    with pytest.raises(ValueError, match="sense must be"):
        LXIndicatorTerm(b, True, LXLinearExpression(), "<", 3.0)


def test_w9_linearized_quadratic_aux_is_keyed_by_index_keys():
    a = LXVariable[str, float]("a").continuous().bounds(0, 1) \
        .indexed_by(lambda k: k).from_data(["p", "q"])
    m = LXModel("m").add_variable(a)
    q = LXQuadraticExpression().add_quadratic(a, a, -1.0)
    q.linear_terms.add_term(a, 1.0)
    m.maximize(q)
    s = LXOptimizer().use_solver("ortools").enable_linearization().solve(m)
    aux = {k: v for name, vals in s.variables.items() if name.startswith("aux_prod")
           for k, v in vals.items()}
    assert aux and all(set(k) <= {"p", "q"} for k in aux)
