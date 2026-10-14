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
