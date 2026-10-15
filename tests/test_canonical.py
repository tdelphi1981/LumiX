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


from lumix.core.enums import LXConstraintSense, LXObjectiveSense


def row_map(canon, name):
    row = next(r for r in canon.rows if r.name == name)
    return {canon.variables[i].name: c for i, c in row.coeffs.items()}, row


def test_a1_constraint_constant_moves_to_rhs():
    x = fam("x", ["k"], upper=100)
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint("c").expression(LXLinearExpression().add_term(x, 1.0).add_constant(5)).le().rhs(8))
    coeffs, row = row_map(m.to_canonical(), "c")
    assert coeffs == {"x[k]": 1.0} and row.rhs == 3.0


def test_a2_repeated_terms_are_summed():
    x = fam("x", ["k"], upper=100)
    e = LXLinearExpression().add_term(x, 4.0)
    e._multi_terms.append((x, lambda k: 1.0, None))       # add_term + sum_over on one family
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint("c").expression(e).le().rhs(10))
    m.maximize(LXLinearExpression().add_term(x, 3.0) + LXLinearExpression().add_multi_term(x, coeff=lambda k: -1.0))
    canon = m.to_canonical()
    assert row_map(canon, "c")[0] == {"x[k]": 5.0}
    assert canon.objective == {0: 2.0}


def test_a2_cancelling_terms_drop_out():
    x = fam("x", ["k"], upper=1)
    e = LXLinearExpression().add_term(x, 1.0) + LXLinearExpression().add_multi_term(x, coeff=lambda k: -1.0)
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint("c").expression(e).le().rhs(0))
    assert row_map(m.to_canonical(), "c")[0] == {}


@dataclass(frozen=True)
class Period:
    t: int
    demand: float


PERIODS = [Period(1, 0.0), Period(2, 4.0), Period(3, 4.0)]


def inventory_model():
    inv = (LXVariable[Period, float]("inv").continuous().bounds(lower=0, upper=100)
           .indexed_by(lambda p: p.t).from_data(PERIODS))
    prod = (LXVariable[Period, float]("prod").continuous().bounds(lower=0, upper=100)
            .indexed_by(lambda p: p.t).from_data(PERIODS))
    balance = (LXConstraint[Period]("balance")
               .expression(LXLinearExpression()
                           .add_term(inv, lambda s, t: 1.0 if s.t == t.t else (-1.0 if s.t == t.t - 1 else 0.0))
                           .add_term(prod, lambda s, t: -1.0 if s.t == t.t else 0.0))
               .eq().rhs(lambda t: -t.demand)
               .from_data(PERIODS[1:]).indexed_by(lambda t: t.t))
    start = (LXConstraint("start").expression(
        LXLinearExpression().add_term(inv, 1.0, where=lambda s: s.t == 1)
        .add_term(prod, -1.0, where=lambda s: s.t == 1)).eq().rhs(0))
    m = LXModel("inventory").add_variables(inv, prod).add_constraint(balance).add_constraint(start)
    m.minimize(LXLinearExpression().add_term(prod, lambda s: 0.0 if s.t == 1 else 10.0).add_term(inv, 1.0))
    return m


def test_a5_two_argument_coefficient_sees_whole_family():
    coeffs, row = row_map(inventory_model().to_canonical(), "balance[2]")
    assert coeffs == {"inv[1]": -1.0, "inv[2]": 1.0, "prod[2]": -1.0}
    assert row.rhs == -4.0 and row.family == "balance" and row.key == 2 and row.indexed


def test_a5_constant_coeff_still_narrows():
    caps = [Period(1, 3.0), Period(2, 5.0)]
    x = (LXVariable[Period, float]("x").continuous().bounds(lower=0)
         .indexed_by(lambda p: p.t).from_data(caps))
    cap = (LXConstraint[Period]("cap").expression(LXLinearExpression().add_term(x, 1.0))
           .le().rhs(lambda p: p.demand).from_data(caps).indexed_by(lambda p: p.t))
    canon = LXModel("m").add_variable(x).add_constraint(cap).to_canonical()
    assert row_map(canon, "cap[1]")[0] == {"x[1]": 1.0}
    assert row_map(canon, "cap[2]")[0] == {"x[2]": 1.0}


def test_two_argument_where_receives_the_row():
    caps = [Period(1, 3.0), Period(2, 5.0)]
    x = (LXVariable[Period, float]("x").continuous().indexed_by(lambda p: p.t).from_data(caps))
    upto = (LXConstraint[Period]("upto")
            .expression(LXLinearExpression().add_term(x, 1.0, where=lambda s, t: s.t <= t.t))
            .le().rhs(10).from_data(caps).indexed_by(lambda p: p.t))
    canon = LXModel("m").add_variable(x).add_constraint(upto).to_canonical()
    assert row_map(canon, "upto[2]")[0] == {"x[1]": 1.0, "x[2]": 1.0}


class Item(NamedTuple):
    name: str
    active: bool


def test_b4_namedtuple_data_is_not_unpacked():
    items = [Item("a", True), Item("b", False)]
    x = LXVariable[Item, float]("x").continuous().indexed_by(lambda r: r.name).from_data(items)
    m = LXModel("m").add_variable(x)
    m.maximize(LXLinearExpression().sum_over(x, where=lambda r: r.active))
    assert m.to_canonical().objective == {0: 1.0}


def test_a4_empty_indexed_constraint_family_has_no_rows():
    x = fam("x", ["k"], upper=5)
    empty = (LXConstraint[str]("none").expression(LXLinearExpression().add_term(x, 1.0))
             .le().rhs(3).from_data([]).indexed_by(lambda s: s))
    canon = LXModel("m").add_variable(x).add_constraint(empty).to_canonical()
    assert canon.rows == ()


def test_objective_constant_and_sense():
    x = fam("x", ["k"], upper=5)
    m = LXModel("m").add_variable(x)
    m.maximize(LXLinearExpression().add_term(x, 2.0).add_constant(7))
    canon = m.to_canonical()
    assert canon.objective == {0: 2.0} and canon.objective_constant == 7.0
    assert canon.sense == LXObjectiveSense.MAXIMIZE and canon.schema_version == 1


def test_unknown_variable_in_expression_raises():
    x = fam("x", ["k"])
    y = fam("y", ["k"])
    m = LXModel("m").add_variable(x)
    m.minimize(LXLinearExpression().add_term(y, 1.0))
    with pytest.raises(ValueError, match="'y' is used in the objective but is not part of the model"):
        m.to_canonical()


def test_nonlinear_objective_requires_linearization():
    from lumix import LXNonLinearExpression, LXOptimizer
    x = fam("x", ["k"], lower=0, upper=5)
    m = LXModel("m").add_variable(x)
    m.minimize(LXNonLinearExpression().add_abs(x))
    assert [i.kind for i in m.to_canonical().objective_nonlinear] == ["abs"]
    with pytest.raises(ValueError, match="enable_linearization"):
        LXOptimizer().use_solver("ortools").solve(m)


def test_a4_scalar_variable_without_data_source():
    """Documented scalar form (user-guide/solution/accessing-solutions.rst)."""
    t = LXVariable[None, float]("total_cost").continuous().bounds(lower=0)
    assert t.is_scalar and not fam("x", ["k"]).is_scalar
    m = LXModel("m").add_variable(t)
    m.add_constraint(LXConstraint("c").expression(LXLinearExpression().add_term(t, 2.0)).ge().rhs(5))
    m.minimize(LXLinearExpression().add_term(t, 1.0))
    canon = m.to_canonical()
    assert [(v.name, v.key) for v in canon.variables] == [("total_cost", None)]
    assert canon.families == {"total_cost": {None: 0}} and canon.scalar_families == ("total_cost",)
    assert row_map(canon, "c")[0] == {"total_cost": 2.0}


def test_a4_empty_family_warns(caplog):
    import logging
    m = LXModel("m").add_variable(fam("x", []))
    with caplog.at_level(logging.WARNING):
        m.to_canonical()
    assert "'x' has no instances" in caplog.text
