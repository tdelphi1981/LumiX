"""Canonical model (spec §3, §3.1): arity rule, variables, rows, objective."""
import math
from dataclasses import dataclass
from typing import NamedTuple

import pytest

from lumix import LXConstraint, LXLinearExpression, LXModel, LXVariable
from lumix.core.expressions import LXKeyFilter, call_arity, call_with_row


def test_call_arity_rules():
    assert call_arity(lambda a: a) == 1
    assert call_arity(lambda a, b: a) == 2
    assert call_arity(lambda *args: 1) == 2
    assert call_arity(len) == 1                       # builtin, no signature issue
    x = LXVariable[str, float]("x").indexed_by(lambda k: k).from_data(["a"])
    assert call_arity(LXKeyFilter(x, ["a"])) == 1

    class Two:
        def __call__(self, a, b):
            return 0
    assert call_arity(Two()) == 2


def test_call_with_row_passes_row_only_to_two_argument_callables():
    assert call_with_row(lambda a: a, 1, 2) == 1
    assert call_with_row(lambda a, b: (a, b), 1, 2) == (1, 2)
    assert call_with_row(lambda a, b=0: (a, b), 1, None) == (1, 0)


def test_merged_and_scaled_terms_keep_component_arity():
    x = LXVariable[str, float]("x").indexed_by(lambda k: k).from_data(["a", "b"])
    one = LXLinearExpression().add_term(x, 1.0, where=lambda k: k == "a")
    other = LXLinearExpression().add_term(x, 2.0, where=lambda k: k == "b")
    merged = one + other
    _, coeff, where = merged.terms["x"]
    assert call_arity(coeff) == 1 and call_arity(where) == 1
    scaled = LXLinearExpression().add_term(x, 3.0) * 2
    assert call_arity(scaled.terms["x"][1]) == 1
    two = LXLinearExpression().add_term(x, lambda s, t: 1.0) + LXLinearExpression().add_term(x, 1.0)
    assert call_arity(two.terms["x"][1]) == 2


from lumix.core.canonical import LXCanonicalBuilder, canonical_bounds
from lumix.core.enums import LXVarType


def fam(name, keys, kind="continuous", lower=None, upper=None):
    v = LXVariable[str, float](name)
    v = {"continuous": v.continuous, "integer": v.integer, "binary": v.binary}[kind]()
    if lower is not None or upper is not None:
        v = v.bounds(lower=lower, upper=upper)
    return v.indexed_by(lambda k: k).from_data(list(keys))


def test_a3_binary_bounds_are_kept():
    assert canonical_bounds(fam("b", "a", "binary", 1, 1)) == (1.0, 1.0)
    assert canonical_bounds(fam("b", "a", "binary")) == (0.0, 1.0)
    assert canonical_bounds(fam("b", "a", "binary", 0, 0)) == (0.0, 0.0)


def test_a3_integer_bounds_round_inward():
    assert canonical_bounds(fam("n", "a", "integer", 0.5, 3.7)) == (1.0, 3.0)
    assert canonical_bounds(fam("n", "a", "integer", -2.5, -0.2)) == (-2.0, -1.0)


def test_b1_open_bounds_are_infinite():
    assert canonical_bounds(fam("n", "a", "integer", 0, None)) == (0.0, math.inf)
    assert canonical_bounds(fam("c", "a")) == (-math.inf, math.inf)


def test_a3_empty_integer_range_raises():
    with pytest.raises(ValueError, match="no integer value"):
        canonical_bounds(fam("n", "a", "integer", 0.2, 0.8))


def test_a4_empty_family_has_no_variables():
    m = LXModel("m").add_variable(fam("x", []))
    canon = LXCanonicalBuilder(m).build()
    assert canon.variables == () and canon.families == {"x": {}}


def test_variables_keep_model_and_instance_order_and_names():
    m = LXModel("m").add_variable(fam("x", ["b", "a"])).add_variable(fam("y", ["c"]))
    canon = LXCanonicalBuilder(m).build()
    assert [v.name for v in canon.variables] == ["x[b]", "x[a]", "y[c]"]
    assert canon.families == {"x": {"b": 0, "a": 1}, "y": {"c": 2}}


def test_duplicate_index_key_raises():
    m = LXModel("m").add_variable(fam("x", ["a", "a"]))
    with pytest.raises(ValueError, match="duplicate index key"):
        LXCanonicalBuilder(m).build()


def test_is_multi_indexed():
    from lumix import LXIndexDimension
    assert not fam("x", "a").is_multi_indexed
    prod = (LXVariable[tuple, float]("p").continuous().indexed_by_product(
        LXIndexDimension(str, lambda s: s).from_data(["a"]),
        LXIndexDimension(str, lambda s: s).from_data(["b"])))
    assert prod.is_multi_indexed
