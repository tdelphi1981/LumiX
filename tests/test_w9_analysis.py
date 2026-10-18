"""W9a/W9b (0.3.2): percentages, binding constraints, logging, warnings."""
import logging
import math
import subprocess
import sys

import pytest

import lumix
from lumix import (LXConstraint, LXLinearExpression, LXModel, LXOptimizer, LXVariable)
from lumix.analysis._change import pct_change


def test_w9_pct_change_uses_the_absolute_base():
    assert pct_change(-7.0, -5.0) == pytest.approx(-40.0)
    assert pct_change(12.0, 10.0) == pytest.approx(20.0)
    assert math.isnan(pct_change(3.0, 0.0))


def _neg_model(need=5.0):
    x = LXVariable[None, float]("x").continuous().bounds(0, 100)
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint("need").expression(
        LXLinearExpression().add_term(x, 1.0)).ge().rhs(need))
    return m.maximize(LXLinearExpression().add_term(x, -1.0))     # baseline -5


def test_w9_whatif_percentage_has_the_sign_of_the_change():
    from lumix.analysis.whatif import LXWhatIfAnalyzer
    a = LXWhatIfAnalyzer(_neg_model(), LXOptimizer().use_solver("ortools"))
    r = a.increase_constraint_rhs("need", to=7.0)
    assert r.delta_objective == pytest.approx(-2.0)
    assert r.delta_percentage == pytest.approx(-40.0)


def test_w9_binding_constraints_use_slack():
    x = LXVariable[None, float]("x").continuous().bounds(0, 10)
    m = LXModel("m").add_variable(x)
    for name in ("c1", "c2"):
        m.add_constraint(LXConstraint(name).expression(
            LXLinearExpression().add_term(x, 1.0)).le().rhs(4))
    m.maximize(LXLinearExpression().add_term(x, 1.0))
    s = LXOptimizer().use_solver("ortools").solve(m)      # no sensitivity: duals None
    from lumix.analysis.sensitivity import LXSensitivityAnalyzer
    assert set(LXSensitivityAnalyzer(m, s).get_binding_constraints()) == {"c1", "c2"}


def test_w9_enable_logging_rejects_a_bad_level_without_side_effects():
    root = logging.getLogger("lumix")
    before = list(root.handlers)
    with pytest.raises(ValueError):
        lumix.enable_logging("VERBOSE")
    assert root.handlers == before


def test_w9_enable_logging_does_not_print_twice_with_a_root_handler(capsys):
    root = logging.getLogger()
    rh = logging.StreamHandler(sys.stdout)
    root.addHandler(rh)
    try:
        lumix.enable_logging("INFO", stream=sys.stdout, fmt="L %(message)s")
        logging.getLogger("lumix.test").info("hello")
        assert capsys.readouterr().out.count("hello") == 1
    finally:
        lumix.disable_logging()
        root.removeHandler(rh)
    assert logging.getLogger("lumix").propagate is True


def test_w9_warning_from_python_c_points_at_user_code():
    code = ("import warnings; warnings.simplefilter('always')\n"
            "from lumix.linearization import LXLinearizerConfig\n"
            "LXLinearizerConfig(tolerance=1e-3)\n")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert "<string>:3" in out.stderr and "sys:1" not in out.stderr
