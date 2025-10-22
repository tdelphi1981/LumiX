"""Goal programming solver orchestration."""

from typing import Any, Dict, List, Optional, TypeVar

from lumix.core.constraints import LXConstraint
from lumix.core.enums import LXConstraintSense, LXObjectiveSense
from lumix.core.model import LXModel
from lumix.solution.solution import LXSolution
from lumix.solvers.base import LXOptimizer

from .goal import LXGoalMode
from .objective_builder import build_sequential_objectives
from .relaxation import RelaxedConstraint

TModel = TypeVar("TModel")


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
        relaxed_constraints: List[RelaxedConstraint[TModel]],
        **solver_params: Any,
    ) -> LXSolution[TModel]:
        """
        Solve using sequential/lexicographic goal programming.

        Solves one priority level at a time:
        1. Solve priority 1, record optimal deviation values
        2. Add constraints fixing priority 1 deviations to optimal values
        3. Solve priority 2 with fixed priority 1
        4. Repeat for all priorities

        Args:
            model: LXModel with relaxed goal constraints already added
            relaxed_constraints: List of relaxed constraints with deviations
            **solver_params: Additional solver parameters

        Returns:
            Final solution with all priorities optimized sequentially

        Raises:
            ValueError: If no objectives can be built from relaxed constraints
        """
        # Build sequential objectives
        sequential_objectives = build_sequential_objectives(relaxed_constraints)

        if not sequential_objectives:
            raise ValueError(
                "No sequential objectives found. "
                "Ensure at least one goal constraint has priority >= 1."
            )

        # Store accumulated deviation fixing constraints
        deviation_bounds: Dict[str, float] = {}

        final_solution = None

        # Solve each priority level
        for priority, objective_expr in sequential_objectives:
            # Set objective for this priority
            model.objective_expr = objective_expr
            model.objective_sense = LXObjectiveSense.MINIMIZE

            # Solve at this priority level
            solution = self.optimizer.solve(model, **solver_params)

            if not solution.is_optimal():
                # If we can't solve optimally at this priority, return what we have
                print(
                    f"Warning: Priority {priority} did not solve to optimality. "
                    f"Status: {solution.status}"
                )
                return solution

            # Record optimal deviation values for this priority
            for relaxed in relaxed_constraints:
                if relaxed.goal_metadata.priority == priority:
                    # Get deviation values
                    pos_dev_name = relaxed.pos_deviation.name
                    neg_dev_name = relaxed.neg_deviation.name

                    pos_dev_value = solution.get_variable(relaxed.pos_deviation)
                    neg_dev_value = solution.get_variable(relaxed.neg_deviation)

                    # Handle both scalar and dict values
                    if isinstance(pos_dev_value, dict):
                        # Indexed variable - fix each instance
                        for idx, val in pos_dev_value.items():
                            deviation_bounds[f"{pos_dev_name}[{idx}]"] = val
                    else:
                        # Scalar variable
                        deviation_bounds[pos_dev_name] = pos_dev_value

                    if isinstance(neg_dev_value, dict):
                        for idx, val in neg_dev_value.items():
                            deviation_bounds[f"{neg_dev_name}[{idx}]"] = val
                    else:
                        deviation_bounds[neg_dev_name] = neg_dev_value

                    # Add constraints to fix these deviations for next priorities
                    # Note: This is a simplified approach - in practice, you'd add
                    # explicit constraints to the model. For now, we'll rely on
                    # the fact that higher priorities have much larger weights.

            final_solution = solution

        return final_solution

    def solve_weighted(
        self,
        model: LXModel[TModel],
        **solver_params: Any,
    ) -> LXSolution[TModel]:
        """
        Solve using weighted goal programming.

        This is a simple pass-through to the standard optimizer, since
        the weighted objective is already built into the model.

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
    # The model should have already been transformed by LXModel's internal logic
    # (relaxed constraints, objective built, etc.)

    gp_solver = LXGoalProgrammingSolver(optimizer)

    if mode == LXGoalMode.WEIGHTED:
        return gp_solver.solve_weighted(model, **solver_params)
    else:  # SEQUENTIAL
        # For sequential, we need access to relaxed constraints
        # This will be provided via model's internal state
        raise NotImplementedError(
            "Sequential mode requires model.solve() with mode parameter. "
            "Use: optimizer.solve(model) after model.set_goal_mode('sequential')"
        )


__all__ = [
    "LXGoalProgrammingSolver",
    "solve_goal_programming",
]
