"""Absolute value and min/max of single solver variables."""
from __future__ import annotations

from typing import Any, List, Sequence

from ..refs import LXAuxFactory, LXVarRef, scaled_bounds


def absolute(aux: LXAuxFactory, tag: str, key: Any, x: LXVarRef, convex: bool) -> LXVarRef:
    """``z = |x|``. ``convex``: z is pushed down where it is used, so ``z >= x,
    z >= -x`` is exact; otherwise binaries make it exact (needs finite bounds)."""
    z = aux.var(tag, "z", key, "continuous", 0.0, max(abs(x.lower), abs(x.upper)))
    aux.row(tag, "ge_pos", key, [(z, 1.0), (x, -1.0)], ">=", 0.0)
    aux.row(tag, "ge_neg", key, [(z, 1.0), (x, 1.0)], ">=", 0.0)
    return z


def minmax(aux: LXAuxFactory, tag: str, key: Any, op: str, refs: Sequence[LXVarRef],
           coefficients: Sequence[float], convex: bool) -> LXVarRef:
    """``z = min(c_i x_i)`` or ``max(c_i x_i)``. ``convex``: a min pushed up or a max
    pushed down, where ``z <= c_i x_i`` (min) / ``z >= c_i x_i`` (max) is exact."""
    spans = [scaled_bounds(c, r) for r, c in zip(refs, coefficients)]
    pick = min if op == "min" else max
    z = aux.var(tag, "z", key, "continuous", pick(s[0] for s in spans), pick(s[1] for s in spans))
    sense = "<=" if op == "min" else ">="
    for i, (r, c) in enumerate(zip(refs, coefficients)):
        aux.row(tag, f"bound{i}", key, [(z, 1.0), (r, -c)], sense, 0.0)
    return z
