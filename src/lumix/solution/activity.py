"""Left-hand-side activity of every constraint row in a solution."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Optional

from ..core.enums import LXConstraintSense

if TYPE_CHECKING:
    from ..core.model import LXModel
    from .solution import LXSolution


@dataclass(frozen=True)
class LXRowActivity:
    """One constraint row evaluated at a solution."""

    lhs: float
    rhs: float
    sense: LXConstraintSense
    slack: float     #: rhs - lhs for <=, lhs - rhs for >=, -|lhs - rhs| for ==
    binding: bool    #: |slack| within 1e-6 relative to the right-hand side


def row_activity(model: "LXModel", solution: "LXSolution") -> Dict[str, LXRowActivity]:
    """Activity of each row of ``model`` (by row name, ``name[key]`` for indexed rows).

    Rows on variables the solution does not report (for example auxiliaries of a
    linearized model) are left out; an infeasible solution gives an empty dict.
    """
    if not solution.variables:
        return {}
    from ..goal_programming.view import goal_form

    form = goal_form(model)
    # A goal row is reported as the goal itself: without its deviations, with its sense.
    goals = {r.constraint.name: r for r in getattr(form, "_relaxed_constraints", [])}
    deviations = {v.name for r in goals.values() for v in (r.pos_deviation, r.neg_deviation)}
    canonical = form.to_canonical()
    scalars = set(canonical.scalar_families)

    def value(index: int) -> Optional[float]:
        var = canonical.variables[index]
        got = solution.variables.get(var.family)
        if got is None:
            return None
        if var.family in scalars or not isinstance(got, dict):
            return float(got)
        v = got.get(var.key)
        return None if v is None else float(v)

    out: Dict[str, LXRowActivity] = {}
    for row in canonical.rows:
        coeffs, sense = row.coeffs, row.sense
        goal = goals.get(row.family)
        if goal is not None:
            coeffs = {i: c for i, c in coeffs.items()
                      if canonical.variables[i].family not in deviations}
            sense = goal.goal_metadata.constraint_sense
        values = [value(i) for i in coeffs]
        if any(v is None for v in values):
            continue
        lhs = sum(c * v for c, v in zip(coeffs.values(), values))
        if sense == LXConstraintSense.LE:
            slack = row.rhs - lhs
        elif sense == LXConstraintSense.GE:
            slack = lhs - row.rhs
        else:
            slack = -abs(lhs - row.rhs)
        binding = abs(slack) <= 1e-6 * max(1.0, abs(row.rhs))
        out[row.name] = LXRowActivity(lhs, row.rhs, sense, slack, binding)
    return out
