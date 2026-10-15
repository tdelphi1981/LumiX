"""Linearization of nonlinear terms (spec W4).

Terms are expanded per instance by the canonical builder (the same items that
``LXModel.to_canonical()`` reports) and each item is replaced by an auxiliary
variable with linear constraints. The user's model is not changed; every call of
:meth:`LXLinearizer.linearize_model` starts afresh."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..core.canonical import LXCanonicalBuilder, LXCanonicalNonlinear
from ..core.constraints import LXConstraint
from ..core.enums import LXConstraintSense, LXObjectiveSense
from ..core.expressions import LXLinearExpression, LXNonLinearExpression, LXQuadraticExpression
from ..core.model import LXModel
from ..nonlinear.terms import LXIndicatorTerm
from ..solvers.capabilities import LXSolverCapability
from .config import LXLinearizerConfig
from .refs import LXAuxFactory, LXVarRef
from .techniques.absminmax import absolute, minmax
from .techniques.bilinear import product
from .techniques.piecewise import piecewise

_TAG = {"abs": "abs", "min": "min", "max": "max", "product": "prod", "piecewise": "pwl"}


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

    def _constraint(self, builder: LXCanonicalBuilder, constraint: LXConstraint) -> LXConstraint:
        return constraint      # nonlinear terms in constraints: B7 (W4 Görev 6)

    def _indicators(self, builder: LXCanonicalBuilder, expr: LXNonLinearExpression) -> None:
        for term in expr.nonlinear_terms:
            if isinstance(term, LXIndicatorTerm):
                self._indicator(builder, term)

    def _indicator(self, builder: LXCanonicalBuilder, term: LXIndicatorTerm) -> None:
        """
        Linearize indicator constraint: if b == condition then (expr sense rhs)

        Uses Big-M method to convert conditional constraint to linear form:
        - If condition=True and sense='<=':  expr - rhs <= M*(1-b)
        - If condition=True and sense='>=':  rhs - expr <= M*(1-b)
        - If condition=False and sense='<=': expr - rhs <= M*b
        - If condition=False and sense='>=': rhs - expr <= M*b
        - For '==': use both <= and >= constraints

        Args:
            term: Indicator term with binary variable, condition, expression, sense, and RHS

        Example:
            If is_open == 1 then flow >= 10:
            - Linearizes to: 10 - flow <= M*(1 - is_open)
            - When is_open=1: 10 - flow <= 0 → flow >= 10 (enforced)
            - When is_open=0: 10 - flow <= M (relaxed)
        """
        self._counts["indicator"] += 1
        binary_var = term.binary_var
        condition = term.condition
        expr = term.linear_expr
        sense = term.sense
        rhs = term.rhs
        M = self.config.big_m_value

        # Create constraint name
        constraint_prefix = (
            f"indicator_{binary_var.name}_{int(condition)}_{sense.replace('=', 'eq')}"
        )

        if sense == "<=":
            # expr <= rhs when condition matches
            # Linearize: expr - rhs <= M * (1-b) if condition=True
            #            expr - rhs <= M * b     if condition=False
            if condition:
                # expr <= rhs + M*(1-b)
                # Rewrite as: expr - M*b <= rhs - M
                indicator_expr = expr.copy()
                indicator_expr = indicator_expr.add_term(binary_var, -M)

                self._aux.constraints.append(
                    LXConstraint(f"{constraint_prefix}_le")
                    .expression(indicator_expr)
                    .le()
                    .rhs(rhs - M)
                )
            else:
                # expr <= rhs + M*b
                # Rewrite as: expr - M*b <= rhs
                indicator_expr = expr.copy()
                indicator_expr = indicator_expr.add_term(binary_var, -M)

                self._aux.constraints.append(
                    LXConstraint(f"{constraint_prefix}_le")
                    .expression(indicator_expr)
                    .le()
                    .rhs(rhs)
                )

        elif sense == ">=":
            # expr >= rhs when condition matches
            # Linearize: rhs - expr <= M * (1-b) if condition=True
            #            rhs - expr <= M * b     if condition=False
            if condition:
                # expr >= rhs - M*(1-b)
                # Rewrite as: rhs - expr <= M*(1-b)
                # Rewrite as: -expr + M*b <= M - rhs
                indicator_expr = LXLinearExpression()
                # Negate all terms in expr
                for var, coeff in expr.terms.items():
                    indicator_expr = indicator_expr.add_term(var, -coeff)
                indicator_expr = indicator_expr.add_term(binary_var, M)

                self._aux.constraints.append(
                    LXConstraint(f"{constraint_prefix}_ge")
                    .expression(indicator_expr)
                    .le()
                    .rhs(M - rhs)
                )
            else:
                # expr >= rhs - M*b
                # Rewrite as: rhs - expr <= M*b
                # Rewrite as: -expr - M*b <= -rhs
                indicator_expr = LXLinearExpression()
                # Negate all terms in expr
                for var, coeff in expr.terms.items():
                    indicator_expr = indicator_expr.add_term(var, -coeff)
                indicator_expr = indicator_expr.add_term(binary_var, -M)

                self._aux.constraints.append(
                    LXConstraint(f"{constraint_prefix}_ge")
                    .expression(indicator_expr)
                    .le()
                    .rhs(-rhs)
                )

        elif sense == "==":
            # expr == rhs when condition matches
            # Need both <= and >= constraints
            # Create two indicator terms and recursively linearize
            le_term = LXIndicatorTerm(
                binary_var=binary_var,
                condition=condition,
                linear_expr=expr,
                sense="<=",
                rhs=rhs,
            )
            ge_term = LXIndicatorTerm(
                binary_var=binary_var,
                condition=condition,
                linear_expr=expr,
                sense=">=",
                rhs=rhs,
            )

            self._indicator(builder, le_term)
            self._indicator(builder, ge_term)

    def _linearize_items(self, items: List[LXCanonicalNonlinear], sign: float
                         ) -> List[Tuple[LXCanonicalNonlinear, LXVarRef]]:
        """One output variable per item. ``sign``: +1 where the value is pushed down
        (minimized objective, ``<=`` row), -1 where it is pushed up, 0 in equalities."""
        tags: Dict[int, str] = {}
        out = []
        for item in items:
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
