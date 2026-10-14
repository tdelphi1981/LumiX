"""Solver-independent canonical form of an LXModel (spec §3, §3.1).

Every solver adapter builds its native model from this form, and engines
outside LumiX (for example lumix-sezgi) can read it through
:meth:`LXModel.to_canonical` instead of re-implementing expression semantics.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

from .enums import LXConstraintSense, LXObjectiveSense, LXVarType
from .expressions import LXKeyFilter, LXLinearExpression, LXNonLinearExpression, call_arity, call_with_row

if TYPE_CHECKING:
    from .model import LXModel
    from .variables import LXVariable

SCHEMA_VERSION = 1


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
            found = list(var.get_instances())
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

    def build(self) -> LXCanonicalModel:
        variables = self._variables()
        rows: List[LXCanonicalRow] = []
        for constraint in self.model.constraints:
            rows.extend(self._rows(constraint))
        objective, constant, sense = self._objective()
        return LXCanonicalModel(
            name=self.model.name,
            variables=tuple(variables),
            families=self.families,
            rows=tuple(rows),
            objective=objective,
            objective_constant=constant,
            objective_nonlinear=(),
            sense=sense,
        )

    # ---- variables -------------------------------------------------------
    def _variables(self) -> List[LXCanonicalVariable]:
        out: List[LXCanonicalVariable] = []
        for var in self.model.variables:
            if var.name in self.families:
                raise ValueError(f"Two variable families are named '{var.name}'")
            lower, upper = canonical_bounds(var)
            positions: Dict[Any, int] = {}
            for instance in self.cache.instances(var):
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
        if constraint.lhs is None:
            raise ValueError(f"Constraint '{constraint.name}' has no LHS expression")
        indexed = constraint.index_func is not None
        instances = constraint.get_instances() if indexed else [None]
        rows: List[LXCanonicalRow] = []
        for instance in instances:
            key = constraint.index_func(instance) if indexed else None
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
                coeffs=coeffs, sense=constraint.sense, rhs=float(rhs) - constant,
                family=constraint.name, key=key, indexed=indexed))
        return rows

    def _objective(self) -> Tuple[Dict[int, float], float, Optional[LXObjectiveSense]]:
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
        for _, (var, coeff, keep) in expr.terms.items():
            positions = self._positions(var, where)
            row_aware = row is not None and (call_arity(coeff) > 1 or call_arity(keep) > 1)
            instances, keep = self.cache.candidates(var, keep, None if row_aware else row)
            for instance in instances:
                if not call_with_row(keep, instance, row):
                    continue
                value = float(call_with_row(coeff, instance, row))
                if value:
                    slot = positions[var.index_key(instance)]
                    acc[slot] = acc.get(slot, 0.0) + value
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
        return {k: v for k, v in acc.items() if v != 0.0}, float(expr.constant)

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
