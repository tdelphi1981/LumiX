"""Building blocks of the linearization techniques: references to single solver
variables, and a factory for auxiliary variables and constraints."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from ..core.canonical import canonical_bounds
from ..core.constraints import LXConstraint
from ..core.enums import LXVarType
from ..core.expressions import LXLinearExpression
from ..core.variables import LXVariable


@dataclass(frozen=True)
class LXVarRef:
    """One solver variable: the instance with index key ``key`` of family ``var``
    (a scalar variable has key ``None``), with its bounds (±inf when open)."""

    var: LXVariable
    key: Any
    lower: float
    upper: float
    var_type: LXVarType

    @classmethod
    def single(cls, var: LXVariable, what: str) -> "LXVarRef":
        """Reference to a variable that has exactly one instance."""
        lower, upper = canonical_bounds(var)
        if var.is_scalar:
            return cls(var, None, lower, upper, var.var_type)
        instances = var.get_instances()
        if len(instances) != 1:
            raise ValueError(
                f"{what} takes a single variable; '{var.name}' has {len(instances)} "
                "instances. LXNonLinearExpression terms apply to every instance of a family")
        return cls(var, var.index_key(instances[0]), lower, upper, var.var_type)

    def add_to(self, expr: LXLinearExpression, coeff: float) -> LXLinearExpression:
        if self.var.is_scalar:
            return expr.add_term(self.var, coeff)
        return expr.add_term(self.var, coeff, keys=[self.key])

    @property
    def bounded(self) -> bool:
        return math.isfinite(self.lower) and math.isfinite(self.upper)

    @property
    def integral(self) -> bool:
        """True for integer and binary variables."""
        return self.var_type in (LXVarType.INTEGER, LXVarType.BINARY)

    @property
    def label(self) -> str:
        return self.var.name if self.key is None else f"{self.var.name}[{self.key}]"


def value_kind(refs: Sequence[LXVarRef], coefficients: Sequence[float] = ()) -> str:
    """Kind of an auxiliary that holds an integer combination of ``refs``: integer when
    every variable is integral and every coefficient a whole number (so that solvers
    without continuous variables, such as CP-SAT, accept it), else continuous."""
    whole = all(float(c).is_integer() for c in coefficients)
    return "integer" if whole and all(r.integral for r in refs) else "continuous"


def scaled_bounds(c: float, ref: LXVarRef) -> Tuple[float, float]:
    """Bounds of ``c * ref``."""
    if c == 0:
        return 0.0, 0.0
    a, b = c * ref.lower, c * ref.upper
    return (a, b) if c > 0 else (b, a)


@dataclass(frozen=True)
class _AuxKey:
    """Instance of an auxiliary family. A type of its own, so constraint rows of
    user data are never taken as instances of an auxiliary family."""
    key: Any


class LXAuxFactory:
    """Auxiliary variables and constraints of one linearization run. The variables
    of one term and role form one family, indexed by the instance keys of the term
    (``aux_abs_x_1_z[p]``); every term gets its own number, so two terms on the same
    variables never share a name."""

    def __init__(self) -> None:
        self.variables: List[LXVariable] = []
        self.constraints: List[LXConstraint] = []
        self._families: Dict[str, Tuple[LXVariable, list, List[float], str]] = {}
        self._terms = 0

    def tag(self, kind: str, names: Sequence[str]) -> str:
        self._terms += 1
        return f"aux_{kind}_{'_'.join(names)}_{self._terms}"

    def var(self, tag: str, role: str, key: Any, kind: str = "continuous",
            lower: float = -math.inf, upper: float = math.inf) -> LXVarRef:
        name = f"{tag}_{role}"
        found = self._families.get(name)
        if found is None:
            data: list = []
            v = LXVariable[_AuxKey, float](name)
            v = {"continuous": v.continuous, "integer": v.integer, "binary": v.binary}[kind]()
            v = v.indexed_by(lambda a: a.key).from_data(data)
            self.variables.append(v)
            found = self._families[name] = (v, data, [lower, upper], kind)
        v, data, bounds, family_kind = found
        if family_kind != kind:
            raise RuntimeError(f"Auxiliary family '{name}' is {family_kind}, not {kind}")
        data.append(_AuxKey(key))
        if kind == "binary":
            return LXVarRef(v, key, 0.0, 1.0, v.var_type)
        bounds[0], bounds[1] = min(bounds[0], lower), max(bounds[1], upper)
        v.bounds(lower=None if math.isinf(bounds[0]) else bounds[0],
                 upper=None if math.isinf(bounds[1]) else bounds[1])
        return LXVarRef(v, key, lower, upper, v.var_type)

    def row(self, tag: str, role: str, key: Any, terms: Sequence[Tuple[LXVarRef, float]],
            sense: str, rhs: float) -> None:
        expr = LXLinearExpression()
        for ref, coeff in terms:
            if coeff:
                ref.add_to(expr, float(coeff))
        name = f"{tag}_{role}" if key is None else f"{tag}_{role}[{key}]"
        c = LXConstraint(name).expression(expr)
        self.constraints.append({"<=": c.le, ">=": c.ge, "==": c.eq}[sense]().rhs(float(rhs)))
