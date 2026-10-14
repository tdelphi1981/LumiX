"""Solver-independent canonical form of an LXModel (spec §3, §3.1).

Every solver adapter builds its native model from this form, and engines
outside LumiX (for example lumix-sezgi) can read it through
:meth:`LXModel.to_canonical` instead of re-implementing expression semantics.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

from .enums import LXConstraintSense, LXObjectiveSense, LXVarType
from .expressions import (LXKeyFilter, LXLinearExpression, LXNonLinearExpression, call_arity,
                          call_with_row, term_parts)

if TYPE_CHECKING:
    from .model import LXModel
    from .variables import LXVariable

SCHEMA_VERSION = 1
#: A sum smaller than NOISE times the magnitude of its summands is floating-point
#: cancellation (0.1 + 0.2 - 0.3) and becomes 0.
NOISE = 1e-12

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LXCanonicalVariable:
    family: str
    key: Any
    name: str
    var_type: LXVarType
    lower: float
    upper: float


@dataclass(frozen=True)
class LXCanonicalRow:
    name: str
    coeffs: Dict[int, float]
    sense: LXConstraintSense
    rhs: float
    family: str
    key: Any
    indexed: bool


@dataclass(frozen=True)
class LXCanonicalNonlinear:
    kind: str
    variables: Tuple[int, ...]
    coeff: float
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LXCanonicalModel:
    name: str
    variables: Tuple[LXCanonicalVariable, ...]
    families: Dict[str, Dict[Any, int]]
    rows: Tuple[LXCanonicalRow, ...]
    objective: Dict[int, float]
    objective_constant: float
    objective_nonlinear: Tuple[LXCanonicalNonlinear, ...]
    sense: Optional[LXObjectiveSense]
    scalar_families: Tuple[str, ...] = ()
    goal_stages: Tuple[Dict[int, float], ...] = ()
    schema_version: int = SCHEMA_VERSION


def canonical_bounds(var: "LXVariable") -> Tuple[float, float]:
    """Bounds of one variable family as floats (±inf when open). Binary bounds
    are intersected with [0, 1]; integer bounds are rounded inward."""
    lower = -math.inf if var.lower_bound is None else float(var.lower_bound)
    upper = math.inf if var.upper_bound is None else float(var.upper_bound)
    if var.var_type == LXVarType.BINARY:
        lower, upper = max(lower, 0.0), min(upper, 1.0)
    if var.var_type in (LXVarType.INTEGER, LXVarType.BINARY):
        if math.isfinite(lower):
            lower = float(math.ceil(lower - 1e-9))
        if math.isfinite(upper):
            upper = float(math.floor(upper + 1e-9))
        if lower > upper:
            raise ValueError(
                f"Variable '{var.name}' has no integer value within its bounds "
                f"[{var.lower_bound}, {var.upper_bound}]"
            )
    elif lower > upper:
        raise ValueError(
            f"Variable '{var.name}' has lower bound {lower} above upper bound {upper}"
        )
    return lower, upper


_BUILTIN_ROWS = (tuple, list, dict, set, frozenset, str, bytes, int, float, bool, complex)


def _difference(a: float, b: float) -> float:
    """``a - b`` with cancellation noise (0.3 - (0.1 + 0.2)) snapped to 0."""
    d = a - b
    return 0.0 if abs(d) <= NOISE * max(abs(a), abs(b)) else d


def _accept_all(*instance: Any) -> bool:
    """Filter used for terms whose instances were already selected by key."""
    return True


class LXInstanceCache:
    """Instances of each variable family, fetched once per build (0.2.0
    behavior, moved here from LXSolverInterface)."""

    def __init__(self) -> None:
        # Keyed by id(): two distinct LXVariable objects may share a name.
        self._instances: Dict[int, List[Any]] = {}
        self._positions: Dict[int, Dict[Any, List[int]]] = {}

    def instances(self, var: "LXVariable") -> List[Any]:
        slot = id(var)
        found = self._instances.get(slot)
        if found is None:
            found = [None] if var.is_scalar else list(var.get_instances())
            self._instances[slot] = found
        return found

    def candidates(self, var: "LXVariable", where: Any, row: Any = None) -> Tuple[List[Any], Any]:
        """Instances a term has to examine, in instance order.

        ``row`` narrows a same-type constraint row to its own instance; the
        builder passes it only for single-argument terms (spec §3 rule 3).
        For an LXKeyFilter only the keyed instances are returned, with a filter
        that accepts everything."""
        instances = self.instances(var)
        if row is not None and row in instances:
            return [row], where
        if not isinstance(where, LXKeyFilter):
            return instances, where
        slot = id(var)
        positions = self._positions.get(slot)
        if positions is None:
            positions = {}
            for i, instance in enumerate(instances):
                positions.setdefault(var.index_key(instance), []).append(i)
            self._positions[slot] = positions
        hits = sorted(i for key in where.keys for i in positions.get(key, ()))
        return [instances[i] for i in hits], _accept_all


class LXCanonicalBuilder:
    """Build the canonical form of one model."""

    def __init__(self, model: "LXModel", cache: Optional[LXInstanceCache] = None) -> None:
        self.model = model
        self.cache = cache or LXInstanceCache()
        self.families: Dict[str, Dict[Any, int]] = {}
        self.scalars: List[str] = []
        self._missing_rows: Dict[Tuple[str, str], None] = {}

    def build(self) -> LXCanonicalModel:
        variables = self._variables()
        rows: List[LXCanonicalRow] = []
        for constraint in self.model.constraints:
            rows.extend(self._rows(constraint))
        objective, constant, sense = self._objective()
        for where, family in self._missing_rows:
            logger.warning(
                "Rows of %s are of the same type as variable '%s' but not among the instances "
                "of '%s'; its one-argument terms contribute nothing there", where, family, family)
        return LXCanonicalModel(
            name=self.model.name,
            variables=tuple(variables),
            families=self.families,
            rows=tuple(rows),
            objective=objective,
            objective_constant=constant,
            objective_nonlinear=(),
            sense=sense,
            scalar_families=tuple(self.scalars),
        )

    # ---- variables -------------------------------------------------------
    def _variables(self) -> List[LXCanonicalVariable]:
        out: List[LXCanonicalVariable] = []
        for var in self.model.variables:
            if var.name in self.families:
                raise ValueError(f"Two variable families are named '{var.name}'")
            lower, upper = canonical_bounds(var)
            positions: Dict[Any, int] = {}
            if var.is_scalar:
                self.scalars.append(var.name)
                self.families[var.name] = {None: len(out)}
                out.append(LXCanonicalVariable(var.name, None, var.name, var.var_type, lower, upper))
                continue
            instances = self.cache.instances(var)
            if not instances:
                logger.warning(
                    "Variable '%s' has no instances (its data is empty); it adds no "
                    "variables and its terms contribute nothing", var.name)
            for instance in instances:
                key = var.index_key(instance)
                if key in positions:
                    raise ValueError(
                        f"Variable '{var.name}' has a duplicate index key {key!r}; "
                        "index keys must be unique within a family"
                    )
                positions[key] = len(out)
                out.append(LXCanonicalVariable(var.name, key, f"{var.name}[{key}]",
                                               var.var_type, lower, upper))
            self.families[var.name] = positions
        return out

    # ---- rows and objective ---------------------------------------------
    def _rows(self, constraint: Any) -> List[LXCanonicalRow]:
        if constraint.index_func is None and (constraint._data is not None
                                              or getattr(constraint, "_session", None) is not None):
            raise ValueError(
                f"Constraint '{constraint.name}' has data (from_data/from_model) but no "
                "indexed_by(...); add indexed_by to build one row per instance, or remove "
                "the data for a single constraint")
        if constraint.lhs is None:
            raise ValueError(f"Constraint '{constraint.name}' has no LHS expression")
        indexed = constraint.index_func is not None
        instances = constraint.get_instances() if indexed else [None]
        rows: List[LXCanonicalRow] = []
        seen: set = set()
        for instance in instances:
            key = constraint.index_func(instance) if indexed else None
            if indexed:
                if key in seen:
                    raise ValueError(
                        f"Constraint '{constraint.name}' has a duplicate index key {key!r}; "
                        "index keys must be unique within a family")
                seen.add(key)
            coeffs, constant = self.linear_row(constraint.lhs, instance,
                                               where=f"constraint '{constraint.name}'")
            if constraint.rhs_value is not None:
                rhs = constraint.rhs_value
            elif constraint.rhs_func is not None:
                rhs = constraint.rhs_func(instance)
            else:
                raise ValueError(f"Constraint '{constraint.name}' has no RHS value")
            rows.append(LXCanonicalRow(
                name=f"{constraint.name}[{key}]" if indexed else constraint.name,
                coeffs=coeffs, sense=constraint.sense, rhs=_difference(float(rhs), constant),
                family=constraint.name, key=key, indexed=indexed))
        return rows

    def _objective(self) -> Tuple[Dict[int, float], float, Optional[LXObjectiveSense]]:
        if getattr(self.model, "_objective_from_costs", False):
            # minimize()/maximize() without an expression: the variables' costs, taken
            # now so that families added after the call are included.
            expr = self.model.cost_objective()
            if expr is None:
                raise ValueError(
                    "minimize()/maximize() was called without an objective, but no "
                    "variable defines a cost (.cost() or .cost_multi())")
            self.model.objective_expr = expr
        expr = self.model.objective_expr
        if expr is None:
            return {}, 0.0, None
        coeffs, constant = self.linear_row(expr, None, where="the objective")
        return coeffs, constant, self.model.objective_sense

    def linear_row(self, expr: Any, row: Any = None,
                   where: str = "an expression") -> Tuple[Dict[int, float], float]:
        """Coefficients per canonical variable position (summed) and the constant."""
        expr = self._linear_part(expr, where)
        acc: Dict[int, float] = {}
        size: Dict[int, float] = {}   # sum of |value| per slot, to recognise cancellation noise
        for _, (var, merged_coeff, merged_keep) in expr.terms.items():
            positions = self._positions(var, where)
            # Narrowing is decided per added term, not per merged term (spec §3 rule 3).
            for coeff, keep in term_parts(merged_coeff, merged_keep):
                row_aware = row is not None and (call_arity(coeff) > 1 or call_arity(keep) > 1)
                if not row_aware and self._row_outside_family(var, row):
                    self._missing_rows.setdefault((where, var.name), None)
                    continue
                instances, keep = self.cache.candidates(var, keep, None if row_aware else row)
                for instance in instances:
                    if not call_with_row(keep, instance, row):
                        continue
                    value = float(call_with_row(coeff, instance, row))
                    if value:
                        slot = positions[var.index_key(instance)]
                        acc[slot] = acc.get(slot, 0.0) + value
                        size[slot] = size.get(slot, 0.0) + abs(value)
        for var, coeff, keep in expr._multi_terms:
            positions = self._positions(var, where)
            instances, keep = self.cache.candidates(var, keep)
            spread = var.is_multi_indexed
            for instance in instances:
                args = instance if spread else (instance,)
                if keep is not None and not keep(*args):
                    continue
                value = float(coeff(*args))
                if value:
                    slot = positions[var.index_key(instance)]
                    acc[slot] = acc.get(slot, 0.0) + value
                    size[slot] = size.get(slot, 0.0) + abs(value)
        return ({k: v for k, v in acc.items() if abs(v) > NOISE * size[k]},
                float(expr.constant))

    def _row_outside_family(self, var: "LXVariable", row: Any) -> bool:
        """A row of the variable's own (user-defined) data type that is not one of its
        instances, e.g. an inactive product filtered out of the variable's data. A
        one-argument term narrows such a row to nothing (spec §3 rule 3). Built-in
        types (tuples, strings, numbers) are not taken as "the same data"."""
        if row is None or type(row) in _BUILTIN_ROWS:
            return False
        instances = self.cache.instances(var)
        return bool(instances) and type(row) is type(instances[0]) and row not in instances

    def _positions(self, var: "LXVariable", where: str) -> Dict[Any, int]:
        positions = self.families.get(var.name)
        if positions is None:
            raise ValueError(
                f"Variable '{var.name}' is used in {where} but is not part of the model; "
                "add it with model.add_variable()"
            )
        return positions

    @staticmethod
    def _linear_part(expr: Any, where: str) -> LXLinearExpression:
        if isinstance(expr, LXLinearExpression):
            return expr
        if isinstance(expr, LXNonLinearExpression):
            if expr.nonlinear_terms:
                raise ValueError(
                    f"{where.capitalize()} has nonlinear terms; call "
                    "LXOptimizer().enable_linearization() or LXLinearizer(...).linearize_model() "
                    "before solving"
                )
            return expr.linear_terms
        raise ValueError(f"{where.capitalize()} has unsupported type {type(expr).__name__}")
