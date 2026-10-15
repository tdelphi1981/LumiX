"""Goal programming solver orchestration."""

import copy
import logging
from typing import Any, List, Optional, TypeVar

from lumix.core.constraints import LXConstraint
from lumix.core.enums import LXConstraintSense, LXObjectiveSense
from lumix.core.model import LXModel
from lumix.solution.solution import LXSolution
from lumix.solvers.base import LXOptimizer

from .goal import LXGoalMode, LXGoalStage
from .objective_builder import build_sequential_objectives
from .relaxation import RelaxedConstraint
from .view import goal_form, goal_mode_value

TModel = TypeVar("TModel")

logger = logging.getLogger(__name__)

#: Relative slack of a stage bound: later stages keep each earlier stage within
#: ``optimum + SEQUENTIAL_TOLERANCE * max(1, |optimum|)``.
SEQUENTIAL_TOLERANCE = 1e-6


def _stage_model(model: LXModel, bounds: List[LXConstraint], expr: Any,
                 sense: LXObjectiveSense) -> LXModel:
    """A shallow copy of ``model`` with the stage bounds added and the stage objective."""
    stage = copy.copy(model)
    stage.constraints = list(model.constraints) + bounds
    return stage.minimize(expr) if sense == LXObjectiveSense.MINIMIZE else stage.maximize(expr)


class LXGoalProgrammingSolver:
    """
    Orchestrates sequential (lexicographic) goal programming.

    For weighted mode, the model transformation is handled directly in LXModel.
    This solver is specifically for sequential mode, which requires multiple
    solve iterations.

    Example:
        >>> solver = LXGoalProgrammingSolver(optimizer)
        >>> solution = solver.solve_sequential(model, relaxed_constraints)
    """

    def __init__(self, optimizer: LXOptimizer):
        """
        Initialize goal programming solver.

        Args:
            optimizer: LXOptimizer instance configured with solver
        """
        self.optimizer = optimizer

    def solve_sequential(
        self,
        model: LXModel[TModel],
        relaxed_constraints: Optional[List[RelaxedConstraint[TModel]]] = None,
        **solver_params: Any,
    ) -> LXSolution[TModel]:
        """
        Solve goal programming lexicographically (A21): priority 1 first, then each
        lower priority with every earlier stage held at its optimum (within
        SEQUENTIAL_TOLERANCE), and finally the model's own objective and the
        priority-0 goals. ``solution.goal_stages`` reports each solve. A stage that
        does not solve to optimality ends the sequence; its solution is returned.

        ``model`` is not changed; one with unprepared goals is relaxed on a copy.

        Args:
            model: LXModel with goals (prepared or not)
            relaxed_constraints: Relaxed goals; default the model's own
            **solver_params: Additional solver parameters

        Returns:
            Solution of the last stage that was solved

        Raises:
            ValueError: If there is neither a goal with priority >= 1 nor a final objective

        .. versionchanged:: 0.3.0
           Earlier stages are kept at their optimum; the final objective is solved last.
        """
        model = goal_form(model)
        relaxed = model._relaxed_constraints if relaxed_constraints is None else relaxed_constraints
        stage_exprs = build_sequential_objectives(relaxed)
        final = None
        if model.objective_expr is not None or model._objective_from_costs:
            final = (model.cost_objective() if model._objective_from_costs else model.objective_expr,
                     model.objective_sense)
        if not stage_exprs and final is None:
            raise ValueError("No sequential objectives found. "
                             "Ensure at least one goal constraint has priority >= 1.")
        bounds: List[LXConstraint] = []
        stages: List[LXGoalStage] = []
        solution = None
        for priority, expr in stage_exprs:
            solution = self.optimizer._solve_once(
                _stage_model(model, bounds, expr, LXObjectiveSense.MINIMIZE), **solver_params)
            stages.append(LXGoalStage(priority, solution.objective_value, solution.status))
            if not solution.is_optimal():
                logger.warning("Goal priority %d did not solve to optimality (status %s); "
                               "lower priorities are not optimized", priority, solution.status)
                break
            value = float(solution.objective_value)
            bounds.append(LXConstraint(f"goal_priority_{priority}_bound").expression(expr).le()
                          .rhs(value + SEQUENTIAL_TOLERANCE * max(1.0, abs(value))))
        else:
            if final is not None:
                expr, sense = final
                solution = self.optimizer._solve_once(_stage_model(model, bounds, expr, sense),
                                                      **solver_params)
                stages.append(LXGoalStage(0, solution.objective_value, solution.status))
        solution.goal_stages = stages
        model.populate_goal_deviations(solution)
        return solution

    def solve_weighted(
        self,
        model: LXModel[TModel],
        **solver_params: Any,
    ) -> LXSolution[TModel]:
        """
        Solve using weighted goal programming.

        A pass-through to the optimizer: the model is relaxed on a copy when
        needed, and the weighted objective is built there.

        Args:
            model: LXModel with weighted goal objective already set
            **solver_params: Additional solver parameters

        Returns:
            Solution from single optimization
        """
        return self.optimizer.solve(model, **solver_params)


def solve_goal_programming(
    model: LXModel[TModel],
    optimizer: LXOptimizer,
    mode: LXGoalMode = LXGoalMode.WEIGHTED,
    **solver_params: Any,
) -> LXSolution[TModel]:
    """
    High-level convenience function for goal programming.

    Args:
        model: LXModel with goal constraints (marked with .as_goal())
        optimizer: Configured optimizer
        mode: Goal programming mode (WEIGHTED or SEQUENTIAL)
        **solver_params: Additional solver parameters

    Returns:
        Solution based on selected mode

    Example:
        >>> model = LXModel("production")
        >>> model.add_constraint(
        ...     LXConstraint("demand_goal")
        ...     .expression(production_expr)
        ...     .ge()
        ...     .rhs(1000)
        ...     .as_goal(priority=1, weight=1.0)
        ... )
        >>> optimizer = LXOptimizer().use_solver("gurobi")
        >>> solution = solve_goal_programming(model, optimizer, mode=LXGoalMode.WEIGHTED)
    """
    gp_solver = LXGoalProgrammingSolver(optimizer)
    if model._goal_programming_prepared and goal_mode_value(model.goal_mode) != mode.value:
        raise ValueError(f"The model was prepared for {model.goal_mode} goal programming; "
                         f"it cannot be solved in {mode.value} mode")
    view = copy.copy(model)
    view.goal_mode = mode.value
    if mode == LXGoalMode.WEIGHTED:
        return gp_solver.solve_weighted(view, **solver_params)
    return gp_solver.optimizer.solve(view, **solver_params)


__all__ = [
    "SEQUENTIAL_TOLERANCE",
    "LXGoalProgrammingSolver",
    "solve_goal_programming",
]
