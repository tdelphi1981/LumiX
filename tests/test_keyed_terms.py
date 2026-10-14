"""keys= on expression terms: validation and predicate semantics."""

import copy
from dataclasses import dataclass

import pytest

from lumix import LXIndexDimension, LXKeyFilter, LXLinearExpression, LXVariable


@dataclass(frozen=True)
class Plant:
    id: str


@dataclass(frozen=True)
class Customer:
    id: str


PLANTS = [Plant("a"), Plant("b"), Plant("c")]
CUSTOMERS = [Customer("r"), Customer("s")]


def plant_var():
    return LXVariable[Plant, float]("y").indexed_by(lambda p: p.id).from_data(PLANTS)


def flow_var():
    return LXVariable[tuple, float]("x").indexed_by_product(
        LXIndexDimension(Plant, lambda p: p.id).from_data(PLANTS),
        LXIndexDimension(Customer, lambda c: c.id).from_data(CUSTOMERS),
    )


def test_add_term_with_keys_stores_a_key_filter():
    y = plant_var()
    expr = LXLinearExpression().add_term(y, 2.0, keys=["a", "c", "a"])
    _, coeff, where = expr.terms["y"]
    assert isinstance(where, LXKeyFilter)
    assert where.keys == frozenset({"a", "c"})
    assert [p.id for p in PLANTS if where(p)] == ["a", "c"]
    assert coeff(PLANTS[0]) == 2.0


def test_key_filter_on_cartesian_family():
    x = flow_var()
    expr = LXLinearExpression().add_multi_term(x, keys=[("b", "s")])
    _, _, where = expr._multi_terms[0]
    assert where(Plant("b"), Customer("s"))
    assert not where(Plant("b"), Customer("r"))


def test_sum_over_passes_keys():
    x = flow_var()
    expr = LXLinearExpression().sum_over(x, keys=[("a", "r")])
    assert isinstance(expr._multi_terms[0][2], LXKeyFilter)


def test_unknown_keys_match_nothing():
    y = plant_var()
    where = LXLinearExpression().add_term(y, keys=["zzz"]).terms["y"][2]
    assert not any(where(p) for p in PLANTS)


def test_keys_and_where_together_are_rejected():
    with pytest.raises(ValueError, match="either"):
        LXLinearExpression().add_term(plant_var(), where=lambda p: True, keys=["a"])
    with pytest.raises(ValueError, match="either"):
        LXLinearExpression().add_multi_term(flow_var(), where=lambda p, c: True, keys=[])


def test_keys_rejects_string():
    with pytest.raises(TypeError, match="keys=\\[key\\]"):
        LXLinearExpression().add_term(plant_var(), keys="a")


def test_key_filter_survives_deepcopy():
    expr = LXLinearExpression().add_term(plant_var(), keys=["b"])
    copied = copy.deepcopy(expr)
    where = copied.terms["y"][2]
    assert isinstance(where, LXKeyFilter) and where(Plant("b")) and not where(Plant("a"))
