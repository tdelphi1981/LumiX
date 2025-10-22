"""
Goal Programming module for LumiX.

Provides automatic LP-to-Goal Programming conversion with:
- Constraint relaxation via deviation variables
- Weighted and sequential (lexicographic) solving modes
- Priority-based objective construction
- Support for custom objective terms

Examples:
    Basic goal programming:
        >>> model = LXModel("production")
        >>> model.add_constraint(
        ...     LXConstraint[Product]("production_target")
        ...     .expression(production_expr)
        ...     .ge()
        ...     .rhs(lambda p: p.target)
        ...     .as_goal(priority=1, weight=1.0)
        ... )
        >>> model.set_goal_mode("weighted")
        >>> solution = optimizer.solve(model)

    Multi-priority with custom objective:
        >>> # Custom objective (priority 0)
        >>> model.add_constraint(
        ...     LXConstraint("profit")
        ...     .expression(profit_expr)
        ...     .ge()
        ...     .rhs(0)
        ...     .as_goal(priority=0, weight=1.0)
        ... )
        >>> # High priority goal
        >>> model.add_constraint(
        ...     LXConstraint("demand")
        ...     .expression(demand_expr)
        ...     .ge()
        ...     .rhs(1000)
        ...     .as_goal(priority=1, weight=1.0)
        ... )
        >>> # Lower priority goal
        >>> model.add_constraint(
        ...     LXConstraint("overtime")
        ...     .expression(overtime_expr)
        ...     .le()
        ...     .rhs(40)
        ...     .as_goal(priority=2, weight=0.5)
        ... )
"""

from .goal import LXGoal, LXGoalMetadata, LXGoalMode, get_deviation_var_name, priority_to_weight
from .objective_builder import (
    build_sequential_objectives,
    build_weighted_objective,
    combine_objectives,
    extract_custom_objectives,
)
from .relaxation import RelaxedConstraint, relax_constraint, relax_constraints
from .solver import LXGoalProgrammingSolver, solve_goal_programming

__all__ = [
    # Core classes and types
    "LXGoal",
    "LXGoalMetadata",
    "LXGoalMode",
    "RelaxedConstraint",
    # Relaxation functions
    "relax_constraint",
    "relax_constraints",
    # Objective building
    "build_weighted_objective",
    "build_sequential_objectives",
    "combine_objectives",
    "extract_custom_objectives",
    # Solver
    "LXGoalProgrammingSolver",
    "solve_goal_programming",
    # Utilities
    "get_deviation_var_name",
    "priority_to_weight",
]
