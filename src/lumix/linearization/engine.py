"""Linearization of nonlinear terms (spec W4).

Terms are expanded per instance by the canonical builder (the same items that
``LXModel.to_canonical()`` reports) and each item is replaced by an auxiliary
variable with linear constraints. The user's model is not changed; every call of
:meth:`LXLinearizer.linearize_model` starts afresh."""
from __future__ import annotations

import copy
import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from ..core.canonical import LXCanonicalBuilder, LXCanonicalNonlinear
from ..core.constraints import LXConstraint
from ..core.enums import LXConstraintSense, LXObjectiveSense, LXVarType
from ..core.expressions import LXLinearExpression, LXNonLinearExpression, LXQuadraticExpression
from ..core.model import LXModel
from ..nonlinear.terms import LXIndicatorTerm
from ..solvers.capabilities import LXSolverCapability
from ..utils._warn import warn_user
from .config import LXLinearizerConfig
from .refs import LXAuxFactory, LXVarRef, scaled_bounds
from .techniques.absminmax import absolute, minmax
from .techniques.bilinear import product
from .techniques.piecewise import piecewise

_TAG = {"abs": "abs", "min": "min", "max": "max", "product": "prod", "piecewise": "pwl"}


logger = logging.getLogger(__name__)

_MISSING = object()


def _term_variables(term: Any) -> List[Any]:
    if hasattr(term, "vars"):
        return list(term.vars)
    return [getattr(term, n) for n in ("var", "var1", "var2") if hasattr(term, n)]


class _InstanceKeys:
    """Index key of a constraint row when the row is an instance of a variable family."""

    def __init__(self, instances: List[Any], var: Any) -> None:
        self._var = var
        self._instances = instances
        try:
            self._table = {inst: var.index_key(inst) for inst in instances}
        except TypeError:                         # unhashable data instances
            self._table = None

    def key_of(self, row: Any) -> Any:
        if self._table is not None:
            try:
                return self._table.get(row, _MISSING)
            except TypeError:
                return _MISSING
        return self._var.index_key(row) if row in self._instances else _MISSING


class LXLinearizer:
    """
    Automatic linearization engine.

    Transforms nonlinear expressions into linear equivalents by:
    - Detecting nonlinear terms in model
    - Checking solver capabilities
    - Applying appropriate linearization techniques
    - Adding auxiliary variables and constraints

    Nonlinear terms on variable families
    apply to every instance (``|x|`` is ``sum(|x[i]|)``). Uses where the plain
    epigraph form is exact (a minimized ``|x|`` or ``max``, a maximized ``min``,
    and the same in ``<=`` / ``>=`` constraints) stay cheap; other uses get
    binaries and are exact.

    Example:
        linearizer = LXLinearizer(model, solver_capability, config)

        if linearizer.needs_linearization():
            linearized_model = linearizer.linearize_model()
    """

    def __init__(self, model: LXModel, solver_capability: LXSolverCapability,
                 config: Optional[LXLinearizerConfig] = None):
        self.model = model
        self.capability = solver_capability
        self.config = config or LXLinearizerConfig()
        self.auxiliary_vars: List[Any] = []
        self.auxiliary_constraints: List[LXConstraint] = []
        self.relaxation_terms: List[str] = []
        self._reset()

    def _reset(self) -> None:
        self._aux = LXAuxFactory()
        self.relaxation_terms = []
        self._counts = {k: 0 for k in ("bilinear", "piecewise", "absolute", "minmax", "indicator")}

    def needs_linearization(self) -> bool:
        objective = self.model.objective_expr
        if isinstance(objective, LXNonLinearExpression) and objective.nonlinear_terms:
            return True
        if (isinstance(objective, LXQuadraticExpression) and objective.quadratic_terms
                and not self.capability.can_solve_quadratic()):
            return True
        return any(isinstance(c.lhs, LXNonLinearExpression) and c.lhs.nonlinear_terms
                   for c in self.model.constraints)

    def linearize_model(self) -> LXModel:
        self._reset()
        builder = LXCanonicalBuilder(self.model, config=self.config)
        by_name = {v.name: v for v in self.model.variables}
        self._refs = [LXVarRef(by_name[cv.family], cv.key, cv.lower, cv.upper, cv.var_type)
                      for cv in builder.prepare()]
        linearized = LXModel(f"{self.model.name}_linearized")
        for var in self.model.variables:
            linearized.add_variable(var)
        self._objective(builder, linearized)
        for constraint in self.model.constraints:
            linearized.add_constraint(self._constraint(builder, constraint))
        for var in self._aux.variables:
            linearized.add_variable(var)
        for constraint in self._aux.constraints:
            linearized.add_constraint(constraint)
        linearized.relaxation_terms = list(self.relaxation_terms)
        # goal programming settings and the state of prepare_goal_programming()
        linearized.goal_mode = self.model.goal_mode
        if self.model._goal_programming_prepared:
            linearized._goal_programming_prepared = True
            linearized._relaxed_constraints = list(self.model._relaxed_constraints)
            linearized._goal_prepared_mode = getattr(self.model, "_goal_prepared_mode", None)
            linearized.objective_sense = self.model.objective_sense
        self.auxiliary_vars = list(self._aux.variables)
        self.auxiliary_constraints = list(self._aux.constraints)
        return linearized

    def _objective(self, builder: LXCanonicalBuilder, linearized: LXModel) -> None:
        model = self.model
        maximize = model.objective_sense == LXObjectiveSense.MAXIMIZE
        if getattr(model, "_objective_from_costs", False):
            linearized.maximize() if maximize else linearized.minimize()
            return
        expr = model.objective_expr
        if expr is None:
            return
        if isinstance(expr, LXNonLinearExpression):
            sign = -1.0 if maximize else 1.0
            out = expr.linear_terms.copy() + expr.constant
            self._indicators(builder, expr)
            for item, z in self._linearize_items(builder.nonlinear(expr, "the objective"), sign):
                z.add_to(out, item.coeff)
            expr = out
        elif (isinstance(expr, LXQuadraticExpression) and expr.quadratic_terms
              and not self.capability.can_solve_quadratic()):
            out = expr.linear_terms.copy() + expr.constant
            for item, z in self._linearize_items(builder.quadratic_items(expr), 0.0):
                z.add_to(out, item.coeff)
            expr = out
        linearized.maximize(expr) if maximize else linearized.minimize(expr)

    _SIGN = {LXConstraintSense.LE: 1.0, LXConstraintSense.GE: -1.0, LXConstraintSense.EQ: 0.0}

    def _constraint(self, builder: LXCanonicalBuilder, constraint: LXConstraint) -> LXConstraint:
        lhs = constraint.lhs
        if not (isinstance(lhs, LXNonLinearExpression) and lhs.nonlinear_terms):
            return constraint
        where = f"constraint '{constraint.name}'"
        self._indicators(builder, lhs)
        outputs = self._linearize_items(builder.nonlinear(lhs, where),
                                        self._SIGN[constraint.sense])
        new_lhs = lhs.linear_terms.copy() + lhs.constant
        if constraint.index_func is None:
            for item, z in outputs:
                z.add_to(new_lhs, item.coeff)
        else:
            self._row_terms(builder, new_lhs, lhs, outputs, where)
        result = copy.copy(constraint)
        result.lhs = new_lhs
        return result

    def _row_terms(self, builder, new_lhs, lhs, outputs, where) -> None:
        """Per-row contributions in an indexed constraint: a row that is an instance
        of one of the term's variable families takes that instance's item only, and a
        row of a family's own data type that is not one of its instances takes nothing
        (spec §3 rule 3, as for one-argument linear terms). Every multi-instance family
        of the term is checked, so the result does not depend on argument order."""
        lookups: Dict[int, List[Tuple[Any, _InstanceKeys]]] = {}
        for index, term in enumerate(lhs.nonlinear_terms):
            owners = [v for v in _term_variables(term)
                      if len(builder.families.get(v.name, {})) > 1]
            lookups[index] = [(v, _InstanceKeys(builder.cache.instances(v), v)) for v in owners]

        warned: set = set()

        def selected(term_index, item_key, row):
            outside = None
            for owner, keys in lookups[term_index]:
                row_key = keys.key_of(row)
                if row_key is not _MISSING:
                    return row_key == item_key
                if outside is None and builder._row_outside_family(owner, row):
                    outside = owner
            if outside is not None:
                if outside.name not in warned:
                    warned.add(outside.name)
                    logger.warning(
                        "Rows of %s are of the same type as variable '%s' but not among the "
                        "instances of '%s'; its nonlinear terms contribute nothing there",
                        where, outside.name, outside.name)
                return False
            return True

        groups: Dict[int, Tuple[Any, Dict[Any, List[Tuple[Any, float, int]]]]] = {}
        for item, z in outputs:
            by_key = groups.setdefault(id(z.var), (z.var, {}))[1]
            by_key.setdefault(z.key, []).append((item.key, item.coeff, item.term))
        for var, by_key in groups.values():
            def coeff(inst, row, var=var, by_key=by_key):
                return sum(c for k, c, t in by_key.get(var.index_key(inst), ())
                           if selected(t, k, row))

            def keep(inst, row, var=var, by_key=by_key):
                return any(selected(t, k, row) for k, _, t in by_key.get(var.index_key(inst), ()))
            new_lhs.add_term(var, coeff, where=keep)

    def _indicators(self, builder: LXCanonicalBuilder, expr: LXNonLinearExpression) -> None:
        for term in expr.nonlinear_terms:
            if isinstance(term, LXIndicatorTerm):
                self._indicator(builder, term)

    def _indicator(self, builder: LXCanonicalBuilder, term: LXIndicatorTerm) -> None:
        """``b == condition`` ⇒ ``expr sense rhs`` (A19). With ``a = 1 - b`` (condition
        True) or ``a = b`` (False): ``expr <= rhs + M a`` / ``expr >= rhs - M a``,
        M from the bounds of ``expr``."""
        self._counts["indicator"] += 1
        b = LXVarRef.single(term.binary_var, "An indicator's binary_var")
        if b.var_type != LXVarType.BINARY:
            raise ValueError(f"An indicator needs a binary variable; '{b.var.name}' is "
                             f"{b.var_type.value}")
        coeffs, constant = builder.linear_row(term.linear_expr, None, where="an indicator")
        spans = [scaled_bounds(c, self._refs[p]) for p, c in coeffs.items()]
        low = constant + sum(s[0] for s in spans)
        high = constant + sum(s[1] for s in spans)
        tag = self._aux.tag("ind", [b.var.name])
        terms = [(self._refs[p], c) for p, c in coeffs.items()]
        rhs = float(term.rhs) - constant
        for sense in {"<=": ("<=",), ">=": (">=",), "==": ("<=", ">=")}[term.sense]:
            m = (high if sense == "<=" else -low) - (term.rhs if sense == "<=" else -term.rhs)
            if not math.isfinite(m):
                warn_user(
                    f"The indicator on '{b.label}' has an unbounded expression; it uses "
                    f"big_m_value={self.config.big_m_value} (LXLinearizerConfig)",
                    UserWarning)
                m = self.config.big_m_value
            if m <= 0:
                continue                         # holds whatever b is
            if sense == "<=":                    # expr - rhs <= M a
                coef, bound = (m, rhs + m) if term.condition else (-m, rhs)
            else:                                # rhs - expr <= M a
                coef, bound = (-m, rhs - m) if term.condition else (m, rhs)
            self._aux.row(tag, "le" if sense == "<=" else "ge", None,
                          terms + [(b, coef)], sense, bound)

    def _linearize_items(self, items: List[LXCanonicalNonlinear], sign: float
                         ) -> List[Tuple[LXCanonicalNonlinear, LXVarRef]]:
        """One output variable per item. ``sign``: +1 where the value is pushed down
        (minimized objective, ``<=`` row), -1 where it is pushed up, 0 in equalities."""
        tags: Dict[int, str] = {}
        out = []
        for item in items:
            if item.coeff == 0 and item.kind in ("abs", "product"):
                continue  # zero weight: contributes nothing and needs no bounds
            refs = [self._refs[p] for p in item.variables]
            tag = tags.get(item.term)
            if tag is None:
                names = list(dict.fromkeys(r.var.name for r in refs))
                tag = tags[item.term] = self._aux.tag(_TAG[item.kind], names)
            out.append((item, self._technique(item, refs, tag, sign)))
        return out

    def _technique(self, item: LXCanonicalNonlinear, refs: List[LXVarRef], tag: str,
                   sign: float) -> LXVarRef:
        key = item.key
        if item.kind == "abs":
            self._counts["absolute"] += 1
            return absolute(self._aux, tag, key, refs[0], convex=sign * item.coeff > 0)
        if item.kind in ("min", "max"):
            self._counts["minmax"] += 1
            convex = sign < 0 if item.kind == "min" else sign > 0
            return minmax(self._aux, tag, key, item.kind, refs, item.params["coefficients"],
                          convex)
        if item.kind == "product":
            self._counts["bilinear"] += 1
            return product(self._aux, tag, key, refs[0], refs[1], self.config,
                           self.relaxation_terms)
        if item.kind == "piecewise":
            self._counts["piecewise"] += 1
            return piecewise(self._aux, tag, key, refs[0], item.params["breakpoints"],
                             item.params["values"], item.params["method"])
        raise ValueError(f"Unsupported nonlinear item: {item.kind}")

    def get_statistics(self) -> dict:
        return {
            "bilinear_terms": self._counts["bilinear"],
            "piecewise_terms": self._counts["piecewise"],
            "absolute_terms": self._counts["absolute"],
            "minmax_terms": self._counts["minmax"],
            "indicator_terms": self._counts["indicator"],
            "auxiliary_variables": len(self.auxiliary_vars),
            "auxiliary_constraints": len(self.auxiliary_constraints),
        }

__all__ = ["LXLinearizer"]
