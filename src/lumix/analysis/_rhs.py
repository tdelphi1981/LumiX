"""Right-hand-side edits shared by scenario and what-if analysis.

A constraint's RHS is either a scalar (``rhs_value``) or a per-row function
(``rhs_func``); ``rhs_value`` wins when both are set, as in canonicalization.
"""
from __future__ import annotations

from typing import Any, Callable, Union


def set_rhs(constraint: Any, value: Union[float, Callable[[Any], float]]) -> None:
    """Replace the RHS: a number becomes the RHS of every row, a callable a new rhs_func."""
    if callable(value):
        constraint.rhs_value = None
        constraint.rhs_func = value
    else:
        constraint.rhs_value = float(value)


def shift_rhs(constraint: Any, *, add: float = 0.0, multiply: float = 1.0,
              percent: float = 0.0) -> None:
    """``rhs := rhs * multiply + add + percent * |rhs|`` for a scalar RHS, or row by row
    for an rhs_func. ``percent`` moves the RHS up by a share of its size, also when the
    RHS is negative."""
    if constraint.rhs_value is not None:
        r = constraint.rhs_value
        constraint.rhs_value = r * multiply + add + percent * abs(r)
    elif constraint.rhs_func is not None:
        inner = constraint.rhs_func
        constraint.rhs_func = lambda instance: (
            inner(instance) * multiply + add + percent * abs(inner(instance)))
    else:
        raise ValueError(f"Constraint '{constraint.name}' has no RHS value")
