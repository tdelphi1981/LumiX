"""W3 core API regressions (catalog A9-A13, B5, B6, C)."""
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from solver_matrix import AVAILABLE, solve_with  # noqa: E402
from test_canonical import fam, row_map  # noqa: E402

from lumix import LXConstraint, LXLinearExpression, LXModel, LXOptimizer, LXVariable


@dataclass(frozen=True)
class R:
    id: str
    cap: float


def test_a9_last_rhs_call_wins():
    c = LXConstraint("c").rhs(5).rhs(lambda r: r.cap)
    assert c.rhs_value is None and c.rhs_func is not None
    c.rhs(7)
    assert c.rhs_value == 7 and c.rhs_func is None


def test_a10_goal_sense_is_read_at_solve_time():
    x = fam("x", ["k"], lower=0, upper=10)
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint("g").expression(LXLinearExpression().add_term(x, 1.0))
                     .as_goal(priority=1).ge().rhs(8))
    m.set_goal_mode("weighted")
    m.prepare_goal_programming()
    s = solve_with("ortools", m)
    assert s.variables["x"]["k"] >= 8 - 1e-6


def test_a11_constraint_data_without_index_raises():
    x = fam("x", ["k"], upper=5)
    c = LXConstraint[R]("cap").expression(LXLinearExpression().add_term(x, 1.0)).le().rhs(3).from_data([R("a", 1)])
    with pytest.raises(ValueError, match="indexed_by"):
        LXModel("m").add_variable(x).add_constraint(c).to_canonical()


from lumix import LXIndexDimension


@dataclass(frozen=True)
class A:
    id: int


@dataclass(frozen=True)
class B:
    id: int


AS, BS = [A(1), A(2)], [B(1), B(2)]


def product(name="v"):
    return LXVariable(name).binary().indexed_by_product(
        LXIndexDimension(A, lambda a: a.id).from_data(AS),
        LXIndexDimension(B, lambda b: b.id).from_data(BS))


def test_a13_where_multi_before_product_applies():
    v = LXVariable("v").binary().where_multi(lambda a, b: a.id == b.id).indexed_by_product(
        LXIndexDimension(A, lambda a: a.id).from_data(AS),
        LXIndexDimension(B, lambda b: b.id).from_data(BS))
    assert len(v.get_instances()) == 2


def test_a13_where_on_product_applies():
    assert len(product().where(lambda ab: ab[0].id == 1).get_instances()) == 2


@dataclass
class Driver:
    id: int
    routes: list
    active: bool = True


@dataclass(frozen=True)
class Route:
    id: int
    cost: float


R1, R2, R3 = Route(1, 4.0), Route(2, 1.0), Route(3, 2.0)


def join_var(drivers):
    return (LXVariable("assign").binary()
            .indexed_by_join(Driver, Route, join_func=lambda d: d.routes,
                             key_func=lambda d, r: (d.id, r.id))
            .from_data(drivers))


def test_b5_join_instances_and_keys():
    v = join_var([Driver(1, [R1, R2]), Driver(2, [R3])])
    assert [v.index_key(i) for i in v.get_instances()] == [(1, 1), (1, 2), (2, 3)]
    assert v.is_multi_indexed and not v.is_scalar


def test_b5_join_solves_with_two_argument_coefficients():
    drivers = [Driver(1, [R1, R2]), Driver(2, [R1, R3])]
    v = join_var(drivers)
    m = LXModel("m").add_variable(v)
    for d in drivers:
        m.add_constraint(LXConstraint(f"one_{d.id}").expression(
            LXLinearExpression().add_multi_term(v, where=lambda dd, r, d=d: dd.id == d.id)).eq().rhs(1))
    m.minimize(LXLinearExpression().add_multi_term(v, coeff=lambda d, r: r.cost))
    for solver in AVAILABLE:
        assert solve_with(solver, m).objective_value == pytest.approx(3.0)   # 1.0 + 2.0


def test_b5_join_where_multi_and_where():
    v = join_var([Driver(1, [R1, R2]), Driver(2, [R3], active=False)])
    v.where(lambda d: d.active).where_multi(lambda d, r: r.cost > 1)
    assert [v.index_key(i) for i in v.get_instances()] == [(1, 1)]


def test_b5_join_with_empty_relations(caplog):
    v = join_var([Driver(1, []), Driver(2, [])])
    with caplog.at_level(logging.WARNING):
        canon = LXModel("m").add_variable(v).to_canonical()
    assert canon.variables == () and "has no instances" in caplog.text
