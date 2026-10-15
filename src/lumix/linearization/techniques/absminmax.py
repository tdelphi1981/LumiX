"""Absolute value and min/max of single solver variables."""
from __future__ import annotations

from typing import Any, List, Sequence

from ..refs import LXAuxFactory, LXVarRef, scaled_bounds, value_kind


def absolute(aux: LXAuxFactory, tag: str, key: Any, x: LXVarRef, convex: bool) -> LXVarRef:
    """``z = |x|``. ``convex``: z is pushed down where it is used, so ``z >= x,
    z >= -x`` is exact; otherwise binaries make it exact (needs finite bounds)."""
    z = aux.var(tag, "z", key, value_kind([x]), 0.0, max(abs(x.lower), abs(x.upper)))
    aux.row(tag, "ge_pos", key, [(z, 1.0), (x, -1.0)], ">=", 0.0)
    aux.row(tag, "ge_neg", key, [(z, 1.0), (x, 1.0)], ">=", 0.0)
    if convex:
        return z
    if not x.bounded:
        raise ValueError(
            f"|{x.label}| is used where it must be exact (maximized, with a negative "
            f"weight, or in an equality); that needs finite bounds on '{x.var.name}'")
    m_neg, m_pos = 2 * max(0.0, -x.lower), 2 * max(0.0, x.upper)
    pos = aux.var(tag, "pos", key, "binary")                     # 1 when x >= 0
    aux.row(tag, "le_pos", key, [(z, 1.0), (x, -1.0), (pos, m_neg)], "<=", m_neg)
    aux.row(tag, "le_neg", key, [(z, 1.0), (x, 1.0), (pos, -m_pos)], "<=", 0.0)
    return z


def minmax(aux: LXAuxFactory, tag: str, key: Any, op: str, refs: Sequence[LXVarRef],
           coefficients: Sequence[float], convex: bool) -> LXVarRef:
    """``z = min(c_i x_i)`` or ``max(c_i x_i)``. ``convex``: a min pushed up or a max
    pushed down, where ``z <= c_i x_i`` (min) / ``z >= c_i x_i`` (max) is exact;
    otherwise one selection binary per argument makes ``z`` equal to the chosen one
    (needs finite bounds on every argument)."""
    spans = [scaled_bounds(c, r) for r, c in zip(refs, coefficients)]
    pick = min if op == "min" else max
    z = aux.var(tag, "z", key, value_kind(refs, coefficients), pick(s[0] for s in spans),
                pick(s[1] for s in spans))
    sense = "<=" if op == "min" else ">="
    for i, (r, c) in enumerate(zip(refs, coefficients)):
        aux.row(tag, f"bound{i}", key, [(z, 1.0), (r, -c)], sense, 0.0)
    if convex:
        return z
    unbounded = [r.label for r, c in zip(refs, coefficients) if c and not r.bounded]
    if unbounded:
        raise ValueError(
            f"{op}() is used where it must be exact; that needs finite bounds on "
            f"{', '.join(unbounded)}")
    picks = [aux.var(tag, f"pick{i}", key, "binary") for i in range(len(refs))]
    aux.row(tag, "pick_one", key, [(p, 1.0) for p in picks], "==", 1.0)
    floor, ceiling = min(s[0] for s in spans), max(s[1] for s in spans)
    for i, ((r, c), (lo_i, hi_i)) in enumerate(zip(zip(refs, coefficients), spans)):
        if op == "min":       # z >= c_i x_i - M (1 - pick_i)
            m = hi_i - floor
            aux.row(tag, f"tight{i}", key, [(z, 1.0), (r, -c), (picks[i], -m)], ">=", -m)
        else:                 # z <= c_i x_i + M (1 - pick_i)
            m = ceiling - lo_i
            aux.row(tag, f"tight{i}", key, [(z, 1.0), (r, -c), (picks[i], m)], "<=", m)
    return z
