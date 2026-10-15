"""W6 LXResultStore: scenario and what-if results written to SQLAlchemy tables."""
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

sa = pytest.importorskip("sqlalchemy")
from sqlalchemy.orm import Session  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from test_w6_analysis import PlainP, capacity_model, mincost_model, opt  # noqa: E402

from lumix import (LXResultStore, LXScenario, LXScenarioAnalyzer,  # noqa: E402
                   LXStoredRun, LXWhatIfAnalyzer)


@pytest.fixture(autouse=True)
def _quiet():
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


@pytest.fixture
def engine():
    eng = sa.create_engine("sqlite://")
    LXResultStore.create_tables(eng)
    return eng


def scenarios(store):
    ps = [PlainP("a", 4, 3), PlainP("b", 6, 5)]
    an = LXScenarioAnalyzer(capacity_model(ps, lambda p: p.profit), opt(), result_store=store)
    an.add_scenario(LXScenario("double_cap").modify_constraint_rhs("cap", multiply=2.0))
    an.add_scenario(LXScenario("starve").modify_constraint_rhs("total", set_value=-1))
    an.run_all_scenarios()
    return an


def test_w6_store_records_every_scenario(engine):
    with Session(engine) as s:
        scenarios(LXResultStore(s, analysis="plan-a"))
    with Session(engine) as s:                     # committed: visible to a new session
        store = LXResultStore(s)
        runs = store.runs(analysis="plan-a")
        assert [r.scenario for r in runs] == ["baseline", "double_cap", "starve"]
        assert all(isinstance(r, LXStoredRun) for r in runs)
        base, dbl, starve = runs
        assert base.objective == pytest.approx(36.0) and base.status == "optimal"
        assert dbl.objective == pytest.approx(40.0)
        assert dbl.modifications == [{"target_type": "constraint", "target_name": "cap",
                                      "modification_type": "rhs_multiply", "value": 2.0}]
        assert starve.status == "infeasible" and starve.objective is None
        assert store.values(base.id) == {"q": pytest.approx({"a": 2.0, "b": 6.0})}
        assert store.values(base.id, kind="shadow_price") == {}


def test_w6_store_sensitivity_rows(engine):
    with Session(engine) as s:
        store = LXResultStore(s, include_sensitivity=True)
        ps = [PlainP("a", 4, 3), PlainP("b", 6, 5)]
        opt_s = opt().enable_sensitivity()
        an = LXScenarioAnalyzer(capacity_model(ps, lambda p: p.profit), opt_s,
                                result_store=store)
        an.run_all_scenarios()
        run = store.runs()[0]
        prices = store.values(run.id, kind="shadow_price")
        assert set(prices) == {"cap", "total"}
        assert prices["cap"] == pytest.approx({"a": 0.0, "b": 2.0})
        assert prices["total"] == pytest.approx(3.0)
        assert set(store.values(run.id, kind="reduced_cost")["q"]) == {"a", "b"}


def test_w6_store_whatif_runs(engine):
    with Session(engine) as s:
        store = LXResultStore(s, analysis="w")
        wa = LXWhatIfAnalyzer(mincost_model(), opt(), result_store=store)
        wa.relax_constraint("need_x", by=1)
        wa.modify_variable_bound("y", upper=10)
        runs = store.runs(analysis="w")
        assert [r.scenario for r in runs] == [
            "baseline", "Relax need_x RHS by -1", "Modify y bounds (upper bound: None → 10)"]
        assert runs[1].objective == pytest.approx(45.0)
        assert runs[1].modifications[0]["target_name"] == "need_x"
        assert runs[2].modifications == [{"change_type": "variable_bound",
                                          "target_name": "y", "bound": "upper",
                                          "original_value": None, "new_value": 10}]


@dataclass(frozen=True)
class K:
    id: int


def test_w6_store_key_encoding(engine):
    from lumix.solution.solution import LXSolution

    sol = LXSolution(objective_value=1.0, status="optimal", solve_time=0.0,
                     variables={"x": 2.5, "z": {("a", 1): 1.0, K(3): 4.0, None: 7.0}})
    with Session(engine) as s:
        store = LXResultStore(s)
        rid = store.record("manual", sol)
        assert store.values(rid) == {"x": 2.5,
                                     "z": {("a", 1): 1.0, "K(id=3)": 4.0, None: 7.0}}


def test_w6_store_commit_false_leaves_transaction_open(engine):
    with Session(engine) as s:
        store = LXResultStore(s, commit=False)
        store.record("x", mincost_model_solution())
        assert len(store.runs()) == 1               # flushed, visible in this session
        s.rollback()
        assert store.runs() == []


def mincost_model_solution():
    return opt().solve(mincost_model())


def test_w6_store_without_sqlalchemy_message(monkeypatch):
    import lumix.analysis.store as store_mod

    def boom():
        raise ImportError("LXResultStore needs SQLAlchemy: pip install 'lumix-opt[orm]'")

    monkeypatch.setattr(store_mod, "_tables", boom)
    with pytest.raises(ImportError, match="lumix-opt\\[orm\\]"):
        LXResultStore(object())
