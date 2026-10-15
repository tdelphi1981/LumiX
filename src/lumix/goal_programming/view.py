"""Goal programming applied to a copy of a model (spec W5): solving or reading the
canonical form of a model with goals does not change the model."""
from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..core.model import LXModel


def goal_mode_value(mode: Any) -> str:
    """``"weighted"`` or ``"sequential"`` for a mode given as a string or LXGoalMode."""
    value = getattr(mode, "value", mode)
    return "weighted" if value is None else str(value)


def goal_form(model: "LXModel") -> "LXModel":
    """The model with its goals relaxed. ``model`` itself when it has no goals or
    was prepared with ``prepare_goal_programming()``; otherwise a prepared shallow
    copy that shares the variables, constraints and data of ``model``.

    Raises:
        ValueError: If ``model`` was prepared for the other goal mode."""
    if model._goal_programming_prepared:
        prepared = getattr(model, "_goal_prepared_mode", None)
        if prepared is not None and prepared != goal_mode_value(model.goal_mode):
            raise ValueError(
                f"The model was prepared for {prepared} goal programming and its goal mode "
                f"is now {goal_mode_value(model.goal_mode)}; build the model again (or solve "
                "it without calling prepare_goal_programming()) to change the mode")
        return model
    if not model.has_goals():
        return model
    view = copy.copy(model)
    view.variables = list(model.variables)
    view.constraints = list(model.constraints)
    view._relaxed_constraints = []
    return view.prepare_goal_programming()
