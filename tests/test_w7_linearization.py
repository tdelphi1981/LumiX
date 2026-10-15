"""W7: linearization carry-overs from the W4 final review."""
import sys
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from solver_matrix import AVAILABLE  # noqa: E402
from test_canonical import fam  # noqa: E402
from test_w4_linearization import cons, lin, model  # noqa: E402

from lumix import (LXConstraint, LXLinearExpression, LXLinearizer, LXModel,
                   LXNonLinearExpression, LXOptimizer, LXVariable)
from lumix.solvers import ORTOOLS_CAPABILITIES


def _caught(action):
    with warnings.catch_warnings(record=True) as got:
        warnings.simplefilter("always")
        action()
    return got


def _assert_points_here(got, category, match):
    hits = [w for w in got if issubclass(w.category, category) and match in str(w.message)]
    assert hits, [str(w.message) for w in got]
    assert all(w.filename == __file__ for w in hits), [(w.filename, w.lineno) for w in hits]


def test_w4_mccormick_warning_points_at_the_caller():
    x, y = fam("x", ["k"], lower=0, upper=4), fam("y", ["k"], lower=0, upper=4)
    m = model([x, y], [cons("c", lin((x, 1), (y, 1)), "<=", 4)], "max",
              LXNonLinearExpression().add_product(x, y))
    got = _caught(lambda: LXOptimizer().use_solver("ortools").enable_linearization().solve(m))
    _assert_points_here(got, UserWarning, "McCormick")


def test_w4_big_m_warning_points_at_the_caller():
    b, y = fam("b", ["k"], "binary"), fam("y", ["k"], lower=0)
    m = model([b, y], [cons("c", lin((y, 1)), "<=", 5)], "max",
              LXNonLinearExpression().add_product(b, y))
    got = _caught(lambda: LXLinearizer(m, ORTOOLS_CAPABILITIES).linearize_model())
    _assert_points_here(got, UserWarning, "big_m_value")


def test_w4_indicator_warning_points_at_the_caller():
    b, z = fam("b", ["k"], "binary"), fam("z", ["k"])
    obj = LXNonLinearExpression().add_indicator(b, True, lin((z, 1))).add_linear(lin((b, 1)))
    m = model([b, z], [cons("zc", lin((z, 1)), "<=", 4)], "max", obj)
    got = _caught(lambda: LXLinearizer(m, ORTOOLS_CAPABILITIES).linearize_model())
    _assert_points_here(got, UserWarning, "unbounded expression")


def test_w4_piecewise_warning_points_at_the_caller():
    x = fam("x", ["k"], lower=0, upper=10)
    m = model([x], [], "min", LXNonLinearExpression().add_piecewise(
        x, lambda t: t * t, x_min=0, x_max=5, num_segments=4))
    got = _caught(lambda: LXLinearizer(m, ORTOOLS_CAPABILITIES).linearize_model())
    _assert_points_here(got, UserWarning, "restricts")


def test_w4_deprecated_config_warning_points_at_the_caller():
    got = _caught(lambda: LXOptimizer().enable_linearization(prefer_sos2=False))
    _assert_points_here(got, DeprecationWarning, "prefer_sos2")


def test_w4_mccormick_warning_suggests_add_quadratic():
    x, y = fam("x", ["k"], lower=0, upper=4), fam("y", ["k"], lower=0, upper=4)
    m = model([x, y], [], "max", LXNonLinearExpression().add_product(x, y))
    got = _caught(lambda: LXLinearizer(m, ORTOOLS_CAPABILITIES).linearize_model())
    text = " ".join(str(w.message) for w in got)
    assert "add_quadratic" in text and "use 'gurobi'" not in text


def test_w4_zero_weight_terms_need_no_bounds():
    x, y = fam("x", ["k"]), fam("y", ["k"])
    for sense in ("min", "max"):
        obj = LXNonLinearExpression().add_linear(lin((x, 1))).add_abs(x, 0.0).add_product(x, y, 0.0)
        m = model([x, y], [cons("c", lin((x, 1)), "<=", 3), cons("d", lin((x, 1)), ">=", -3)],
                  sense, obj)
        s = LXOptimizer().use_solver("ortools").enable_linearization().solve(m)
        assert s.objective_value == pytest.approx(3 if sense == "max" else -3)


def test_w4_single_variable_aux_values_are_numbers():
    x = LXVariable[str, float]("x").continuous().bounds(lower=-5, upper=5)
    m = LXModel("m").add_variable(x).minimize(LXNonLinearExpression().add_abs(x))
    m.add_constraint(LXConstraint("c").expression(LXLinearExpression().add_term(x)).le().rhs(-2))
    s = LXOptimizer().use_solver("ortools").enable_linearization().solve(m)
    aux = {k: v for k, v in s.variables.items() if k.startswith("aux_abs")}
    assert aux and all(isinstance(v, float) for v in aux.values()), aux
    assert list(aux.values())[0] == pytest.approx(2.0)


def _product_rows(swap):
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class Pp:
        id: str

    @dataclass(frozen=True)
    class Ww:
        id: str
        cap: float

    ps, ws = [Pp("a"), Pp("b")], [Ww("a", 1.0), Ww("b", 1.0)]
    x = LXVariable[Pp, int]("x").binary().indexed_by(lambda p: p.id).from_data(ps)
    y = (LXVariable[Ww, float]("y").continuous().bounds(lower=0, upper=1)
         .indexed_by(lambda w: w.id).from_data(ws))
    term = LXNonLinearExpression().add_product(*((y, x) if swap else (x, y)))
    m = LXModel("m").add_variables(x, y).maximize(lin((y, 1)))
    m.add_constraint(LXConstraint[Ww]("cap").expression(term).le().rhs(lambda w: w.cap)
                     .indexed_by(lambda w: w.id).from_data(ws))
    lm = LXLinearizer(m, ORTOOLS_CAPABILITIES).linearize_model()
    c = lm.to_canonical()
    names = {i: f"{v.family}[{v.key}]" for i, v in enumerate(c.variables)}
    return {r.name: sorted(names[i] for i in r.coeffs) for r in c.rows if r.name.startswith("cap")}


def test_w4_row_narrowing_does_not_depend_on_argument_order():
    for swap in (False, True):
        rows = _product_rows(swap)
        assert all(len(v) == 1 for v in rows.values()), rows
        assert rows["cap[a]"][0].endswith("[a]") and rows["cap[b]"][0].endswith("[b]")


@pytest.mark.parametrize("solver", AVAILABLE)
@pytest.mark.parametrize("sense, rhs, expected", [("<=", 3, 3.0), (">=", 3, 10.0), ("==", 3, 3.0)])
def test_w4_add_indicator_sense_and_rhs(solver, sense, rhs, expected):
    b, z = fam("b", ["k"], "binary"), fam("z", ["k"], lower=0, upper=10)
    obj = (LXNonLinearExpression().add_indicator(b, True, lin((z, 1)), sense=sense, rhs=rhs)
           .add_linear(lin((z, 1))))
    m = model([b, z], [cons("on", lin((b, 1)), ">=", 1)], "max", obj)
    s = LXOptimizer().use_solver(solver).enable_linearization().solve(m)
    assert s.variables["z"]["k"] == pytest.approx(expected)


def test_w4_add_indicator_rejects_an_unknown_sense():
    b, z = fam("b", ["k"], "binary"), fam("z", ["k"], lower=0, upper=10)
    with pytest.raises(ValueError, match="sense"):
        LXNonLinearExpression().add_indicator(b, True, lin((z, 1)), sense="<")
