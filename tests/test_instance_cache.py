"""Per-build instance cache and the keyed fast path in solver adapters."""

from dataclasses import dataclass

import pytest

pytest.importorskip("ortools")

from lumix import (
    LXConstraint,
    LXIndexDimension,
    LXLinearExpression,
    LXModel,
    LXOptimizer,
    LXVariable,
)
from lumix.solvers.ortools_solver import LXORToolsSolver


@dataclass(frozen=True)
class Plant:
    id: int
    cap: float


@dataclass(frozen=True)
class Customer:
    id: int
    dem: float


def transport(n: int, keyed: bool, integer: bool = False):
    plants = [Plant(i, 3.0 * n) for i in range(n)]
    customers = [Customer(j, 1.0 + j % 3) for j in range(n)]
    x = LXVariable[tuple, float]("x").bounds(lower=0)
    x = (x.integer() if integer else x.continuous()).indexed_by_product(
        LXIndexDimension(Plant, lambda p: p.id).from_data(plants),
        LXIndexDimension(Customer, lambda c: c.id).from_data(customers),
    )
    model = LXModel("transport")
    model.add_variable(x)
    for p in plants:
        expr = LXLinearExpression()
        if keyed:
            expr.add_multi_term(x, keys=[(p.id, c.id) for c in customers])
        else:
            expr.add_multi_term(x, where=lambda a, b, pid=p.id: a.id == pid)
        model.add_constraint(LXConstraint(f"sup_{p.id}").expression(expr).le().rhs(p.cap))
    for c in customers:
        expr = LXLinearExpression()
        if keyed:
            expr.add_multi_term(x, keys=[(p.id, c.id) for p in plants])
        else:
            expr.add_multi_term(x, where=lambda a, b, cid=c.id: b.id == cid)
        model.add_constraint(LXConstraint(f"dem_{c.id}").expression(expr).ge().rhs(c.dem))
    model.minimize(LXLinearExpression().add_multi_term(
        x, coeff=lambda a, b: 1 + (a.id * 7 + b.id) % 5))
    return model, x


def lp_text(model) -> str:
    return LXORToolsSolver().build_model(model).ExportModelAsLpFormat(False)


def test_keys_and_where_build_identical_lp():
    assert lp_text(transport(6, keyed=True)[0]) == lp_text(transport(6, keyed=False)[0])


@pytest.mark.parametrize("solver", ["ortools", "cpsat", "gurobi"])
def test_keys_and_where_give_the_same_solution(solver):
    if solver == "gurobi":
        pytest.importorskip("gurobipy")
    integer = solver == "cpsat"
    a = LXOptimizer().use_solver(solver).solve(transport(5, keyed=True, integer=integer)[0])
    b = LXOptimizer().use_solver(solver).solve(transport(5, keyed=False, integer=integer)[0])
    assert a.status == b.status == "optimal"
    assert a.objective_value == pytest.approx(b.objective_value)


def test_get_instances_is_called_once_per_build_not_per_row(monkeypatch):
    counts = {}
    for n in (4, 16):
        model, x = transport(n, keyed=False)
        real = x.get_instances
        calls = []

        def counting():
            calls.append(1)
            return real()

        monkeypatch.setattr(x, "get_instances", counting)
        LXORToolsSolver().build_model(model)
        counts[n] = len(calls)
    assert counts[4] == counts[16]


def test_cache_is_reset_between_builds():
    model, x = transport(3, keyed=False)
    optimizer = LXOptimizer().use_solver("ortools")
    first = optimizer.solve(model)
    x._cartesian.dimensions[1].from_data([Customer(j, 5.0) for j in range(3)])
    model.constraints = [c for c in model.constraints if not c.name.startswith("dem_")]
    for j in range(3):
        model.add_constraint(
            LXConstraint(f"dem_{j}")
            .expression(LXLinearExpression().add_multi_term(
                x, where=lambda a, b, cid=j: b.id == cid))
            .ge().rhs(5.0))
    second = optimizer.solve(model)
    assert second.objective_value > first.objective_value
