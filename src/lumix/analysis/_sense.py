"""The objective sense a solve actually optimizes (goal models included)."""
from __future__ import annotations

from typing import Any

from ..core.enums import LXObjectiveSense


def solved_sense(model: Any) -> LXObjectiveSense:
    """Sense of the objective whose value a solve of ``model`` reports.

    A model with goals is solved in its goal form: weighted mode minimizes the deviations,
    sequential mode ends with the final stage (minimized deviations when there is no
    model objective).
    """
    from ..goal_programming.view import goal_form

    form = goal_form(model)
    if form is not model and form.objective_expr is None:
        return LXObjectiveSense.MINIMIZE
    return form.objective_sense
