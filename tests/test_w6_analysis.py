"""W6 analysis regressions (catalog A23, A24, B11, B12, B15, C get_best_scenario) and
the W6 additions (model_factory, LXResultStore lives in test_w6_store.py)."""
import copy
import logging
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from solver_matrix import AVAILABLE  # noqa: E402

from lumix import (LXConstraint, LXLinearExpression, LXModel, LXOptimizer,
                   LXScenario, LXScenarioAnalyzer, LXSensitivityAnalyzer,
                   LXVariable, LXWhatIfAnalyzer)
from lumix.indexing import LXIndexDimension


@pytest.fixture(autouse=True)
def _quiet():
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


def opt():
    return LXOptimizer().use_solver("ortools")


class PlainP:  # identity equality and identity hash
    def __init__(self, id, cap, profit):
        self.id, self.cap, self.profit = id, cap, profit


def capacity_model(ps, profit):
    """max sum profit(p) q[p]  s.t. q[p] <= p.cap (row per p), sum q <= 8."""
    q = LXVariable[PlainP, float]("q").continuous().bounds(lower=0) \
        .indexed_by(lambda p: p.id).from_data(ps)
    m = LXModel("m").add_variable(q)
    m.add_constraint(LXConstraint[PlainP]("cap").expression(LXLinearExpression().add_term(q))
                     .le().rhs(lambda p: p.cap).from_data(ps).indexed_by(lambda p: p.id))
    m.add_constraint(LXConstraint("total").expression(LXLinearExpression().add_term(q))
                     .le().rhs(8))
    m.maximize(LXLinearExpression().add_term(q, profit))
    return m


# ---- Task 1: A23 / B15 -------------------------------------------------------

def test_a23_noop_whatif_keeps_closure_identity():
    ps = [PlainP("a", 4, 3), PlainP("b", 6, 5)]
    a = ps[0]
    q = LXVariable[PlainP, float]("q").continuous().bounds(lower=0) \
        .indexed_by(lambda p: p.id).from_data(ps)
    m = LXModel("plain").add_variable(q)
    m.add_constraint(LXConstraint[PlainP]("cap").expression(LXLinearExpression().add_term(q))
                     .le().rhs(lambda p: p.cap).from_data(ps).indexed_by(lambda p: p.id))
    m.add_constraint(LXConstraint("only_a").expression(
        LXLinearExpression().add_term(q, coeff=lambda p: 1.0 if p is a else 0.0)).le().rhs(1))
    m.add_constraint(LXConstraint("total").expression(LXLinearExpression().add_term(q))
                     .le().rhs(100))
    m.maximize(LXLinearExpression().add_term(q, lambda p: p.profit))
    r = LXWhatIfAnalyzer(m, opt()).increase_constraint_rhs("total", by=0)
    assert r.original_objective == pytest.approx(33.0)
    assert r.new_objective == pytest.approx(33.0)
    assert m.get_constraint("total").rhs_value == 100      # original untouched


def test_a23_scenario_with_instance_keyed_dict():
    ps = [PlainP("a", 4, 0), PlainP("b", 6, 0)]
    w = {ps[0]: 3.0, ps[1]: 5.0}
    sa = LXScenarioAnalyzer(capacity_model(ps, lambda p: w[p]), opt())
    sa.add_scenario(LXScenario("total_10").modify_constraint_rhs("total", set_value=10))
    res = sa.run_all_scenarios()
    assert res["baseline"].objective_value == pytest.approx(36.0)
    assert res["total_10"].objective_value == pytest.approx(42.0)


def test_a23_product_dimension_identity_survives_copy():
    @dataclass(frozen=True)
    class P:
        id: str

    @dataclass(frozen=True)
    class W:
        id: int

    ps, ws = [P("a"), P("b")], [W(1), W(2)]
    z = LXVariable[tuple, float]("z").continuous().bounds(lower=0, upper=3).indexed_by_product(
        LXIndexDimension(P, lambda p: p.id).from_data(ps),
        LXIndexDimension(W, lambda w: w.id).from_data(ws))
    m = LXModel("m").add_variable(z)
    m.add_constraint(LXConstraint("tot").expression(
        LXLinearExpression().add_multi_term(z, coeff=lambda p, w: 1.0)).le().rhs(7))
    m.maximize(LXLinearExpression().add_multi_term(
        z, coeff=lambda p, w: 1.0 if p is ps[0] else 2.0))
    m2 = copy.deepcopy(m)
    assert opt().solve(m2).objective_value == pytest.approx(opt().solve(m).objective_value)


def test_a23_copy_shares_instances_but_not_structure():
    ps = [PlainP("a", 4, 3), PlainP("b", 6, 5)]
    m = capacity_model(ps, lambda p: p.profit)
    m2 = copy.deepcopy(m)
    v, v2 = m.get_variable("q"), m2.get_variable("q")
    assert v2 is not v and v2._data is not v._data
    assert all(x is y for x, y in zip(v._data, v2._data))
    c, c2 = m.get_constraint("cap"), m2.get_constraint("cap")
    assert c2 is not c and c2.rhs_func is c.rhs_func
    m2.get_constraint("total").rhs_value = 1
    assert m.get_constraint("total").rhs_value == 8


def _lazy_orm_model():
    sa = pytest.importorskip("sqlalchemy")
    from sqlalchemy.orm import Session, declarative_base, relationship
    Base = declarative_base()

    class Category(Base):
        __tablename__ = "cat"
        id = sa.Column(sa.Integer, primary_key=True)
        factor = sa.Column(sa.Float)

    class Product(Base):
        __tablename__ = "products"
        id = sa.Column(sa.Integer, primary_key=True)
        profit = sa.Column(sa.Float)
        cat_id = sa.Column(sa.ForeignKey("cat.id"))
        category = relationship("Category")

    eng = sa.create_engine("sqlite://")
    Base.metadata.create_all(eng)
    with Session(eng) as s:
        c = Category(id=1, factor=2.0)
        s.add_all([c, Product(id=1, profit=3.0, category=c)])
        s.commit()
    s = Session(eng)
    prods = s.query(Product).all()                      # category NOT loaded
    y = LXVariable[Product, float]("y").continuous().bounds(lower=0, upper=10) \
        .indexed_by(lambda p: p.id).from_data(prods)
    m = LXModel("mm").add_variable(y).maximize(
        LXLinearExpression().add_term(y, lambda p: p.profit * p.category.factor))
    m.add_constraint(LXConstraint("cap").expression(LXLinearExpression().add_term(y))
                     .le().rhs(10))
    return m, s, Product


def test_b15_copy_of_lazy_relationship_model_solves():
    m, s, _ = _lazy_orm_model()
    assert opt().solve(copy.deepcopy(m)).objective_value == pytest.approx(60.0)
    sa = LXScenarioAnalyzer(m, opt(), include_baseline=False)
    sa.add_scenario(LXScenario("half").modify_constraint_rhs("cap", set_value=5))
    assert sa.run_all_scenarios()["half"].objective_value == pytest.approx(30.0)
    s.close()


def test_b15_detach_loads_unloaded_relationship():
    from lumix.utils.copy_utils import detach_orm_object
    m, s, Product = _lazy_orm_model()
    p = s.query(Product).first()
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        d = detach_orm_object(p)
    assert d.category.factor == 2.0
    s.close()
