"""
Bilinear product linearization techniques.

Exact unless both factors are continuous:
1. Binary × Binary: AND logic (b * b = b)
2. Binary × bounded variable: four bound rows (z = y when b = 1, else 0)
3. Integer × (integer | continuous): binary expansion of the integer factor
4. Continuous × Continuous: McCormick envelopes, a relaxation (UserWarning,
   solution.relaxation)
"""

import math
import warnings
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
    """``z = x * y``: exact when a factor is binary or integer; McCormick envelopes
    (a relaxation, recorded in ``relaxation``) for two continuous variables."""
    binary = LXVarType.BINARY
    if x.var_type == binary and y.var_type == binary:
        return _and(aux, tag, key, x, y)
    if x.var_type == binary or y.var_type == binary:
        b, other = (x, y) if x.var_type == binary else (y, x)
        return _binary_times(aux, tag, key, b, other, config)
    integer = LXVarType.INTEGER
    ints = [r for r in (x, y) if r.var_type == integer]
    if ints:
        primary = min(ints, key=lambda r: (not r.bounded, r.upper - r.lower))
        other = y if primary is x else x
        return _expansion(aux, tag, key, primary, other, config)
    return _mccormick(aux, tag, key, x, y, relaxation)


def _same(x: LXVarRef, y: LXVarRef) -> bool:
    return x.var is y.var and x.key == y.key


def _and(aux, tag, key, x, y):
    if _same(x, y):
        return x                                   # b * b = b
    z = aux.var(tag, "z", key, "binary")
    aux.row(tag, "le_x", key, [(z, 1.0), (x, -1.0)], "<=", 0.0)
    aux.row(tag, "le_y", key, [(z, 1.0), (y, -1.0)], "<=", 0.0)
    aux.row(tag, "ge_sum", key, [(z, 1.0), (x, -1.0), (y, -1.0)], ">=", -1.0)
    return z


def _binary_times(aux, tag, key, b, y, config):
    """``z = b * y`` for ``y`` in [lo, hi]: z = y when b = 1, z = 0 when b = 0 (A14)."""
    lo, hi = y.lower, y.upper
    if not y.bounded:
        warnings.warn(
            f"'{y.label}' has no finite bounds; its product with binary '{b.label}' uses "
            f"big_m_value={config.big_m_value} (LXLinearizerConfig) as the bound",
            UserWarning, stacklevel=4)
        lo = lo if math.isfinite(lo) else -config.big_m_value
        hi = hi if math.isfinite(hi) else config.big_m_value
    z = aux.var(tag, "z", key, "continuous", min(lo, 0.0), max(hi, 0.0))
    aux.row(tag, "ub", key, [(z, 1.0), (b, -hi)], "<=", 0.0)                   # z <= hi b
    aux.row(tag, "lb", key, [(z, 1.0), (b, -lo)], ">=", 0.0)                   # z >= lo b
    aux.row(tag, "ub_y", key, [(z, 1.0), (y, -1.0), (b, -lo)], "<=", -lo)      # z <= y - lo (1 - b)
    aux.row(tag, "lb_y", key, [(z, 1.0), (y, -1.0), (b, -hi)], ">=", -hi)      # z >= y - hi (1 - b)
    return z


def _expansion(aux, tag, key, x, y, config):
    """``z = x * y`` for integer ``x`` in [L, U]: x = L + sum 2^k d_k, so
    z = L y + sum 2^k (d_k y), each d_k y exact by :func:`_binary_times`."""
    if not x.bounded:
        raise ValueError(
            f"The product {x.label} * {y.label} needs finite bounds on the integer variable "
            f"'{x.var.name}' (binary expansion)")
    low, span = int(x.lower), int(x.upper - x.lower)
    bits = span.bit_length()
    if bits > config.binary_expansion_bits:
        raise ValueError(
            f"{x.label} takes {span + 1} values; its binary expansion needs {bits} bits, more "
            f"than LXLinearizerConfig.binary_expansion_bits={config.binary_expansion_bits}. "
            "Raise it, or use 'gurobi' or 'cplex' for a quadratic objective")
    digits = [aux.var(tag, f"bit{k}", key, "binary") for k in range(bits)]
    aux.row(tag, "expand", key, [(x, 1.0)] + [(d, -float(2 ** k)) for k, d in enumerate(digits)],
            "==", float(low))
    corners = [a * b for a in (x.lower, x.upper) for b in (y.lower, y.upper)]
    finite = all(math.isfinite(c) for c in corners)
    z = aux.var(tag, "z", key, "continuous", min(corners) if finite else -math.inf,
                max(corners) if finite else math.inf)
    terms = [(z, 1.0), (y, -float(low))]
    for k, d in enumerate(digits):
        terms.append((_binary_times(aux, f"{tag}_bit{k}", key, d, y, config), -float(2 ** k)))
    aux.row(tag, "sum", key, terms, "==", 0.0)
    return z


def _mccormick(aux, tag, key, x, y, relaxation):
    if not (x.bounded and y.bounded):
        raise ValueError(
            f"McCormick envelopes require bounds on both variables. "
            f"Detected: {x.label} ∈ [{x.lower}, {x.upper}], {y.label} ∈ [{y.lower}, {y.upper}]. "
            "Please specify bounds using .bounds(lower=..., upper=...)")
    relaxation.append(f"{x.label} * {y.label}")
    warnings.warn(
        f"The product {x.label} * {y.label} of two continuous variables is linearized with "
        "McCormick envelopes, a relaxation: the reported optimum may not be attainable "
        "(solution.relaxation is True). Make a factor integer or binary, or use 'gurobi' or "
        "'cplex' for a quadratic objective", UserWarning, stacklevel=4)
    xl, xu, yl, yu = x.lower, x.upper, y.lower, y.upper
    corners = [xl * yl, xl * yu, xu * yl, xu * yu]
    z = aux.var(tag, "z", key, "continuous", min(corners), max(corners))
    aux.row(tag, "mc1", key, [(z, 1.0), (y, -xl), (x, -yl)], ">=", -xl * yl)
    aux.row(tag, "mc2", key, [(z, 1.0), (y, -xu), (x, -yu)], ">=", -xu * yu)
    aux.row(tag, "mc3", key, [(z, 1.0), (y, -xl), (x, -yu)], "<=", -xl * yu)
    aux.row(tag, "mc4", key, [(z, 1.0), (y, -xu), (x, -yl)], "<=", -xu * yl)
    return z



__all__ = ["LXBilinearLinearizer", "product"]
