"""W7: analysis carry-overs from the W6 final review."""
import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from test_w6_analysis import PlainP, capacity_model, mincost_model, opt  # noqa: E402

from lumix import (LXConstraint, LXLinearExpression, LXModel, LXScenario, LXScenarioAnalyzer,
                   LXSensitivityAnalyzer, LXVariable, LXWhatIfAnalyzer)


@pytest.fixture(autouse=True)
def _quiet():
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


def _fixed_model():
    x = LXVariable[int, float]("x").continuous().bounds(lower=0).indexed_by(lambda k: k).from_data([1])
    m = LXModel("fixed").add_variable(x)
    m.add_constraint(LXConstraint("fix").expression(LXLinearExpression().add_term(x)).eq().rhs(5))
    return m.minimize(LXLinearExpression().add_term(x, 1.0))


def test_w6_find_bottlenecks_tries_equalities_both_ways():
    # x == 5, min x: lowering the right-hand side improves by 1 per unit
    assert LXWhatIfAnalyzer(_fixed_model(), opt()).find_bottlenecks() == [("fix", pytest.approx(1.0))]


def test_w6_find_bottlenecks_has_no_negative_zero():
    ps = [PlainP("a", 4, 3), PlainP("b", 6, 5)]
    m = capacity_model(ps, lambda p: p.profit)
    m.add_constraint(LXConstraint("loose").expression(
        LXLinearExpression().add_term(m.get_variable("q"))).le().rhs(1000))
    result = dict(LXWhatIfAnalyzer(m, opt()).find_bottlenecks())
    assert str(result["loose"]) == "0.0"


def test_w6_factory_must_not_share_constraints_with_the_base():
    shared = LXConstraint("need_x")
    base = mincost_model()

    def factory():
        m = mincost_model()
        m.constraints = [shared if c.name == "need_x" else c for c in m.constraints]
        return m

    shared.expression(LXLinearExpression().add_term(base.get_variable("x"))).ge().rhs(5)
    wa = LXWhatIfAnalyzer(model_factory=factory, optimizer=opt())
    with pytest.raises(ValueError, match="shares"):
        wa.relax_constraint("need_x", by=1)


def test_w6_store_uses_text_columns():
    sa = pytest.importorskip("sqlalchemy")
    from lumix import LXResultStore

    eng = sa.create_engine("sqlite://")
    LXResultStore.create_tables(eng)
    runs = {c["name"]: str(c["type"]) for c in sa.inspect(eng).get_columns("lumix_runs")}
    values = {c["name"]: str(c["type"]) for c in sa.inspect(eng).get_columns("lumix_run_values")}
    assert runs["scenario"] == "TEXT" and values["name"] == "TEXT"


def test_w6_given_baseline_is_recorded_once():
    sa = pytest.importorskip("sqlalchemy")
    from sqlalchemy.orm import Session

    from lumix import LXResultStore

    eng = sa.create_engine("sqlite://")
    LXResultStore.create_tables(eng)
    store = LXResultStore(Session(eng))
    m = mincost_model()
    wa = LXWhatIfAnalyzer(m, opt(), baseline_solution=opt().solve(m), result_store=store)
    wa.relax_constraint("need_x", by=1)
    wa.relax_constraint("need_y", by=1)
    names = [r.scenario for r in store.runs()]
    assert names.count("baseline") == 1 and names[0] == "baseline" and len(names) == 3


def test_w6_sensitivity_sees_rows_added_after_the_first_lookup():
    m = mincost_model()
    sol = opt().enable_sensitivity().solve(m)
    an = LXSensitivityAnalyzer(m, sol)
    an.analyze_constraint("need_x")
    m.add_constraint(LXConstraint("extra").expression(
        LXLinearExpression().add_term(m.get_variable("x"))).le().rhs(100))
    assert an.analyze_constraint("extra").shadow_price is None


def test_w6_scalar_lookup_does_not_build_the_row_index(monkeypatch):
    import lumix.analysis.sensitivity as sens

    ps = [PlainP("a", 4, 3), PlainP("b", 6, 5)]
    m = capacity_model(ps, lambda p: p.profit)
    an = LXSensitivityAnalyzer(m, opt().enable_sensitivity().solve(m))
    calls = []
    original = sens._constraint_rows
    monkeypatch.setattr(sens, "_constraint_rows", lambda c: calls.append(c.name) or original(c))
    an.analyze_constraint("total")
    assert calls == []


def test_w6_constraint_slack_is_filled():
    ps = [PlainP("a", 4, 3), PlainP("b", 6, 5)]
    m = capacity_model(ps, lambda p: p.profit)
    an = LXSensitivityAnalyzer(m, opt().enable_sensitivity().solve(m))
    # optimum q = (2, 6): total binding; cap[a] has slack 2, cap[b] binding
    assert an.analyze_constraint("total").slack == pytest.approx(0.0)
    assert an.analyze_constraint("cap[a]").slack == pytest.approx(2.0)
    assert not an.analyze_constraint("cap[a]").is_binding
    assert an.analyze_constraint("cap[b]").is_binding
