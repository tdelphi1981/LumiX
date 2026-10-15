"""
Bilinear product linearization techniques.

Implements three main methods:
1. Binary × Binary: AND logic
2. Binary × Continuous: Big-M method
3. Continuous × Continuous: McCormick envelopes
"""

import math
from typing import Any, List

from ...core.constraints import LXConstraint
from ...core.enums import LXVarType
from ...core.variables import LXVariable
from ...nonlinear.terms import LXBilinearTerm
from ..config import LXLinearizerConfig
from ..refs import LXAuxFactory, LXVarRef


class LXBilinearLinearizer:
    """Linearization of products of two single variables (public API; the
    linearization engine uses :func:`product` per instance)."""

    def __init__(self, config: LXLinearizerConfig):
        self.config = config
        self._aux = LXAuxFactory()
        self.auxiliary_vars: List[LXVariable] = self._aux.variables
        self.auxiliary_constraints: List[LXConstraint] = self._aux.constraints
        self.relaxation_terms: List[str] = []


    def linearize_bilinear(self, term: LXBilinearTerm) -> LXVariable:
        """
        Linearize the product of two single variables (scalars or families with one
        instance); terms in an LXNonLinearExpression apply to every instance.

        Args:
            term: Bilinear term to linearize

        Returns:
            Variable representing the product (the coefficient is not applied)
        """
        x = LXVarRef.single(term.var1, "linearize_bilinear")
        y = LXVarRef.single(term.var2, "linearize_bilinear")
        tag = self._aux.tag("prod", [term.var1.name, term.var2.name])
        return product(self._aux, tag, None, x, y, self.config, self.relaxation_terms).var


def product(aux: LXAuxFactory, tag: str, key: Any, x: LXVarRef, y: LXVarRef,
            config: LXLinearizerConfig, relaxation: List[str]) -> LXVarRef:
    """``z = x * y`` (0.2 formulas; Görev 5 replaces this body)."""
    binary = LXVarType.BINARY
    if x.var_type == binary and y.var_type == binary:
        z = aux.var(tag, "z", key, "binary")
        aux.row(tag, "le_x", key, [(z, 1.0), (x, -1.0)], "<=", 0.0)
        aux.row(tag, "le_y", key, [(z, 1.0), (y, -1.0)], "<=", 0.0)
        aux.row(tag, "ge_sum", key, [(z, 1.0), (x, -1.0), (y, -1.0)], ">=", -1.0)
        return z
    if x.var_type == binary or y.var_type == binary:
        b, c = (x, y) if x.var_type == binary else (y, x)
        hi = c.upper if math.isfinite(c.upper) else config.big_m_value
        lo = c.lower if math.isfinite(c.lower) else -config.big_m_value
        z = aux.var(tag, "z", key, "continuous", lo, hi)
        aux.row(tag, "ub", key, [(z, 1.0), (b, -hi)], "<=", 0.0)
        aux.row(tag, "lb", key, [(z, 1.0), (b, -lo)], ">=", 0.0)
        aux.row(tag, "ub_tight", key, [(z, 1.0), (c, -1.0), (b, lo)], "<=", lo)
        aux.row(tag, "lb_tight", key, [(z, 1.0), (c, -1.0), (b, hi)], ">=", hi)
        return z
    if not (x.bounded and y.bounded):
        raise ValueError(
            f"McCormick envelopes require bounds on both variables. "
            f"Detected: {x.label} ∈ [{x.lower}, {x.upper}], {y.label} ∈ [{y.lower}, {y.upper}]. "
            "Please specify bounds using .bounds(lower=..., upper=...)")
    xl, xu, yl, yu = x.lower, x.upper, y.lower, y.upper
    corners = [xl * yl, xl * yu, xu * yl, xu * yu]
    z = aux.var(tag, "z", key, "continuous", min(corners), max(corners))
    aux.row(tag, "mc1", key, [(z, 1.0), (y, -xl), (x, -yl)], ">=", -xl * yl)
    aux.row(tag, "mc2", key, [(z, 1.0), (y, -xu), (x, -yu)], ">=", -xu * yu)
    aux.row(tag, "mc3", key, [(z, 1.0), (y, -xl), (x, -yu)], "<=", -xl * yu)
    aux.row(tag, "mc4", key, [(z, 1.0), (y, -xu), (x, -yl)], "<=", -xu * yl)
    return z


__all__ = ["LXBilinearLinearizer", "product"]
