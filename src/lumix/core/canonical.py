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
from .expressions import (LXKeyFilter, LXLinearExpression, LXNonLinearExpression,
                          LXQuadraticExpression, LXRowKeyFilter, call_arity, call_with_row,
                          positional_count, term_parts)

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
    #: Position of the source term in its expression; the items of one term share it.
    term: int = 0
    #: Index key of the instance the item applies to (``None`` for single variables).
    key: Any = None


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
    #: ``{(i, j): c}`` with ``i <= j``: the objective term ``c * x_i * x_j``.
    objective_quadratic: Dict[Tuple[int, int], float] = field(default_factory=dict)
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

    def _key_positions(self, var: "LXVariable") -> Dict[Any, List[int]]:
        slot = id(var)
        positions = self._positions.get(slot)
        if positions is None:
            positions = {}
            for i, instance in enumerate(self.instances(var)):
                positions.setdefault(var.index_key(instance), []).append(i)
            self._positions[slot] = positions
        return positions

    def candidates(self, var: "LXVariable", where: Any, row: Any = None) -> Tuple[List[Any], Any]:
        """Instances a term has to examine, in instance order.

        ``row`` narrows a same-type constraint row to its own instance; the
        builder passes it only for single-argument terms (spec §3 rule 3) and
        for an LXRowKeyFilter, which keeps only the instance keyed by the row.
        For an LXKeyFilter only the keyed instances are returned, with a filter
        that accepts everything."""
        instances = self.instances(var)
        if isinstance(where, LXRowKeyFilter):
            if row is None:
                return instances, where
            return ([instances[i] for i in self._key_positions(var).get(where.row_key(row), ())],
                    _accept_all)
        if row is not None and row in instances:
            return [row], where
        if not isinstance(where, LXKeyFilter):
            return instances, where
        positions = self._key_positions(var)
        hits = sorted(i for key in where.keys for i in positions.get(key, ()))
        return [instances[i] for i in hits], _accept_all


class LXCanonicalBuilder:
    """Build the canonical form of one model."""

    def __init__(self, model: "LXModel", cache: Optional[LXInstanceCache] = None,
                 config: Any = None) -> None:
        self.model = model
        self._config = config
        self.variables: List[LXCanonicalVariable] = []
        self.nonlinear_items: List[LXCanonicalNonlinear] = []
        self.cache = cache or LXInstanceCache()
        self.families: Dict[str, Dict[Any, int]] = {}
        self.scalars: List[str] = []
        self.quadratic: Dict[Tuple[int, int], float] = {}
        self._missing_rows: Dict[Tuple[str, str], None] = {}

    @property
    def config(self) -> Any:
        if self._config is None:
            from ..linearization.config import LXLinearizerConfig
            self._config = LXLinearizerConfig()
        return self._config

    def prepare(self) -> List[LXCanonicalVariable]:
        """Number the variables (positions and ``families``); done once per build."""
        if not self.variables:
            self.variables = self._variables()
        return self.variables

    def build(self) -> LXCanonicalModel:
        variables = self.prepare()
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
            objective_nonlinear=tuple(self.nonlinear_items),
            sense=sense,
            scalar_families=tuple(self.scalars),
            objective_quadratic=self.quadratic,
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
        else:
            expr = self.model.objective_expr
        if expr is None:
            return {}, 0.0, None
        if isinstance(expr, LXNonLinearExpression):
            from ..nonlinear.terms import LXIndicatorTerm
            if any(isinstance(t, LXIndicatorTerm) for t in expr.nonlinear_terms):
                raise ValueError(
                    "The objective has indicator terms, which are constraints; call "
                    "LXOptimizer().enable_linearization() or LXLinearizer(...).linearize_model() "
                    "before solving")
            self.nonlinear_items = self.nonlinear(expr, "the objective")
            coeffs, constant = self.linear_row(expr.linear_terms, None, where="the objective")
            return coeffs, constant + float(expr.constant), self.model.objective_sense
        if isinstance(expr, LXQuadraticExpression):
            coeffs, constant = self.linear_row(expr.linear_terms, None, where="the objective")
            self.quadratic = self._quadratic(expr)
            return coeffs, constant + float(expr.constant), self.model.objective_sense
        coeffs, constant = self.linear_row(expr, None, where="the objective")
        return coeffs, constant, self.model.objective_sense

    def linear_row(self, expr: Any, row: Any = None,
                   where: str = "an expression") -> Tuple[Dict[int, float], float]:
        """Coefficients per canonical variable position (summed) and the constant."""
        extra = float(expr.constant) if isinstance(expr, LXNonLinearExpression) else 0.0
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
                instances, keep = self.cache.candidates(
                    var, keep, row if (not row_aware or isinstance(keep, LXRowKeyFilter)) else None)
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
                float(expr.constant) + extra)

    def nonlinear(self, expr: LXNonLinearExpression, where: str) -> List[LXCanonicalNonlinear]:
        """The nonlinear terms of ``expr`` as per-instance items (W4, spec §3.1 rule 2).
        A term on variable families applies to each instance and the results are
        summed; the families of one term must have the same index keys, and a single
        variable (a scalar or a one-instance family) is used for every instance.
        Indicator terms are constraints and are left to the linearizer."""
        from ..nonlinear.terms import (LXAbsoluteTerm, LXBilinearTerm, LXIndicatorTerm,
                                       LXMinMaxTerm, LXPiecewiseLinearTerm)
        items: List[LXCanonicalNonlinear] = []
        for index, term in enumerate(expr.nonlinear_terms):
            if isinstance(term, LXIndicatorTerm):
                continue
            if isinstance(term, LXAbsoluteTerm):
                for key, ps in self._aligned([term.var], where):
                    items.append(LXCanonicalNonlinear("abs", ps, float(term.coefficient), {},
                                                      index, key))
            elif isinstance(term, LXMinMaxTerm):
                coeffs = tuple(float(c) for c in (term.coefficients or [1.0] * len(term.vars)))
                if len(coeffs) != len(term.vars):
                    raise ValueError(f"{where.capitalize()}: {term.operation}() has "
                                     f"{len(term.vars)} variables but {len(coeffs)} coefficients")
                for key, ps in self._aligned(term.vars, where):
                    items.append(LXCanonicalNonlinear(term.operation, ps, 1.0,
                                                      {"coefficients": coeffs}, index, key))
            elif isinstance(term, LXBilinearTerm):
                for key, ps in self._aligned([term.var1, term.var2], where):
                    items.append(LXCanonicalNonlinear("product", ps, float(term.coefficient), {},
                                                      index, key))
            elif isinstance(term, LXPiecewiseLinearTerm):
                params = self._piecewise_params(term)
                for key, ps in self._aligned([term.var], where):
                    items.append(LXCanonicalNonlinear("piecewise", ps, 1.0, params, index, key))
            else:
                raise ValueError(f"Unsupported nonlinear term type: {type(term).__name__}")
        return items

    def _aligned(self, variables: List["LXVariable"], where: str) -> List[Tuple[Any, Tuple[int, ...]]]:
        """``(key, positions)`` per instance of the term's families (see :meth:`nonlinear`)."""
        maps = [self._positions(v, where) for v in variables]
        keys: Optional[List[Any]] = None
        for v, positions in zip(variables, maps):
            if len(positions) == 1:
                continue
            if keys is None:
                keys = list(positions)
            elif set(positions) != set(keys):
                names = ", ".join(sorted({u.name for u in variables}))
                raise ValueError(
                    f"{where.capitalize()}: a nonlinear term combines variable families with "
                    f"different index keys ({names}); use families over the same keys, or "
                    "single variables")
        if keys is None:
            return [(None, tuple(next(iter(m.values())) for m in maps))]
        return [(k, tuple(m[k] if len(m) != 1 else next(iter(m.values())) for m in maps))
                for k in keys]

    def _piecewise_params(self, term: Any) -> Dict[str, Any]:
        from ..linearization.techniques.piecewise import piecewise_points
        lower, upper = canonical_bounds(term.var)
        points, values = piecewise_points(
            term.func, None if math.isinf(lower) else lower, None if math.isinf(upper) else upper,
            self.config, name=term.var.name, num_segments=term.num_segments, x_min=term.x_min,
            x_max=term.x_max, adaptive=term.adaptive, breakpoints=term.breakpoints)
        return {"breakpoints": tuple(points), "values": tuple(values),
                "method": term.method or self.config.pwl_method}

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

    def _quadratic(self, expr: LXQuadraticExpression) -> Dict[Tuple[int, int], float]:
        """Objective products ``{(i, j): c}`` (i <= j, summed, zeros dropped)."""
        acc: Dict[Tuple[int, int], float] = {}
        for term in expr.quadratic_terms:
            p1 = self._positions(term.var1, "the objective")
            p2 = self._positions(term.var2, "the objective")
            first = self.cache.instances(term.var1)
            if term.diagonal:
                pairs = [(i, i, self._quad_coeff(term, i, None)) for i in first]
            else:
                second = self.cache.instances(term.var2)
                pairs = [(i, j, self._quad_coeff(term, i, j)) for i in first for j in second]
            for i, j, value in pairs:
                a = p1[term.var1.index_key(i)]
                b = p2[term.var2.index_key(j)]
                key = (min(a, b), max(a, b))
                acc[key] = acc.get(key, 0.0) + float(value)
        return {k: v for k, v in acc.items() if v}

    @staticmethod
    def _quad_coeff(term: Any, i: Any, j: Any) -> Any:
        """A callable coefficient gets the instances, or their parts on multi-index
        families when it takes one argument per part (like ``add_multi_term``)."""
        c = term.coefficient
        if not callable(c):
            return c
        sides = [(term.var1, i)] if term.diagonal else [(term.var1, i), (term.var2, j)]
        whole = [inst for _, inst in sides]
        parts = [p for var, inst in sides
                 for p in (inst if var.is_multi_indexed else (inst,))]
        if len(parts) != len(whole) and positional_count(c) == len(parts):
            return c(*parts)
        return c(*whole)

    def quadratic_items(self, expr: LXQuadraticExpression) -> List[LXCanonicalNonlinear]:
        """The objective products of ``expr`` as product items (one per pair of
        positions, coefficients summed, each its own term) for the linearizer."""
        # Every pair is a term of its own, so each gets its own auxiliary family.
        return [LXCanonicalNonlinear("product", (i, j), c, {}, n, (i, j))
                for n, ((i, j), c) in enumerate(self._quadratic(expr).items())]

    @staticmethod
    def _linear_part(expr: Any, where: str) -> LXLinearExpression:
        if isinstance(expr, LXQuadraticExpression):
            raise ValueError(f"{where.capitalize()} is quadratic; quadratic expressions are "
                             "supported only in the objective")
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
