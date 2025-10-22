"""Objective function construction for goal programming."""

from collections import defaultdict
from typing import Dict, List, Tuple, TypeVar

from lumix.core.expressions import LXLinearExpression
from lumix.core.variables import LXVariable

from .goal import LXGoalMode, priority_to_weight
from .relaxation import RelaxedConstraint

TModel = TypeVar("TModel")


def build_weighted_objective(
    relaxed_constraints: List[RelaxedConstraint],
    base: float = 10.0,
    exponent_offset: int = 6,
) -> LXLinearExpression:
    """
    Build single weighted objective for goal programming.

    Combines all priorities into one objective using exponentially decreasing
    weights to ensure higher priorities dominate lower priorities.

    Objective: minimize sum(priority_weight[p] * goal_weight[g] * deviation[g])

    Args:
        relaxed_constraints: List of relaxed constraints with deviation variables
        base: Base for exponential priority-to-weight conversion (default: 10)
        exponent_offset: Offset for exponent (default: 6, so P1=10^6, P2=10^5)

    Returns:
        Linear expression for weighted goal programming objective

    Example:
        Priority 1 goals get weight 10^6, priority 2 get 10^5, etc.
        This ensures P1 goals are effectively optimized first, then P2, etc.
    """
    objective = LXLinearExpression()

    for relaxed in relaxed_constraints:
        metadata = relaxed.goal_metadata

        # Get priority weight (exponential scaling)
        prio_weight = priority_to_weight(
            metadata.priority,
            base=base,
            exponent_offset=exponent_offset
        )

        # Combined weight = priority_weight * goal_weight
        combined_weight = prio_weight * metadata.weight

        # Add undesired deviation variables to objective
        for deviation_var in relaxed.get_undesired_variables():
            # Check if variable is indexed or single
            if deviation_var.index_func is not None:
                # Indexed variable - sum over all instances
                objective.add_term(deviation_var, coeff=combined_weight)
            else:
                # Single variable
                objective.add_term(deviation_var, coeff=combined_weight)

    return objective


def build_sequential_objectives(
    relaxed_constraints: List[RelaxedConstraint],
) -> List[Tuple[int, LXLinearExpression]]:
    """
    Build sequential objectives for lexicographic goal programming.

    Creates one objective per priority level. These are solved sequentially:
    1. Solve priority 1, record optimal deviation values
    2. Fix priority 1 deviations, solve priority 2
    3. Continue for all priorities

    Args:
        relaxed_constraints: List of relaxed constraints with deviation variables

    Returns:
        List of (priority, objective_expression) tuples, sorted by priority

    Example:
        >>> objectives = build_sequential_objectives(relaxed)
        >>> # [(1, expr_p1), (2, expr_p2), (3, expr_p3)]
        >>> # Solve P1 first, then P2, then P3
    """
    # Group constraints by priority
    priority_groups: Dict[int, List[RelaxedConstraint]] = defaultdict(list)

    for relaxed in relaxed_constraints:
        priority = relaxed.goal_metadata.priority
        priority_groups[priority].append(relaxed)

    # Build objective for each priority level
    objectives = []

    for priority in sorted(priority_groups.keys()):
        if priority == 0:
            # Skip priority 0 (custom objectives) in sequential mode
            # They should be handled separately or combined with P1
            continue

        priority_expr = LXLinearExpression()

        for relaxed in priority_groups[priority]:
            metadata = relaxed.goal_metadata
            goal_weight = metadata.weight

            # Add undesired deviations with goal weight
            for deviation_var in relaxed.get_undesired_variables():
                if deviation_var.index_func is not None:
                    # Indexed variable
                    priority_expr.add_term(deviation_var, coeff=goal_weight)
                else:
                    # Single variable
                    priority_expr.add_term(deviation_var, coeff=goal_weight)

        objectives.append((priority, priority_expr))

    return objectives


def combine_objectives(
    base_objective: LXLinearExpression,
    goal_objective: LXLinearExpression,
    goal_weight: float = 1.0,
) -> LXLinearExpression:
    """
    Combine a base objective with goal programming objective.

    This is useful when you have a primary objective function (e.g., maximize profit)
    and also want to incorporate goal constraints.

    Args:
        base_objective: Primary objective expression
        goal_objective: Goal programming objective (sum of weighted deviations)
        goal_weight: Relative weight for goal objective (default: 1.0)

    Returns:
        Combined objective expression

    Example:
        >>> profit_expr = LXLinearExpression().add_term(profit, 1.0)
        >>> goal_expr = build_weighted_objective(relaxed_constraints)
        >>> # Combine: maximize profit - goal_deviations
        >>> combined = combine_objectives(profit_expr, goal_expr, goal_weight=0.1)
    """
    combined = LXLinearExpression()

    # Add base objective terms
    combined.terms = base_objective.terms.copy()
    combined._multi_terms = base_objective._multi_terms.copy()
    combined.constant = base_objective.constant

    # Add goal objective terms with weight
    for var_name, (var, coeff_func, where_func) in goal_objective.terms.items():
        if var_name in combined.terms:
            # Variable already exists - combine coefficients
            existing_var, existing_coeff, existing_where = combined.terms[var_name]

            # Create combined coefficient function
            def combined_coeff(model, ec=existing_coeff, gc=coeff_func, gw=goal_weight):
                return ec(model) + gw * gc(model)

            combined.terms[var_name] = (var, combined_coeff, where_func)
        else:
            # New variable - add with goal weight
            def weighted_coeff(model, gc=coeff_func, gw=goal_weight):
                return gw * gc(model)

            combined.terms[var_name] = (var, weighted_coeff, where_func)

    # Add multi-terms
    for var, coeff_func, where_func in goal_objective._multi_terms:
        def weighted_multi_coeff(*args, cf=coeff_func, gw=goal_weight):
            return gw * cf(*args)

        combined._multi_terms.append((var, weighted_multi_coeff, where_func))

    combined.constant += goal_weight * goal_objective.constant

    return combined


def extract_custom_objectives(
    relaxed_constraints: List[RelaxedConstraint],
) -> List[RelaxedConstraint]:
    """
    Extract constraints marked as custom objectives (priority 0).

    These represent user-defined objective terms that should be incorporated
    into the optimization alongside goal deviations.

    Args:
        relaxed_constraints: List of all relaxed constraints

    Returns:
        List of relaxed constraints with priority 0
    """
    return [
        relaxed
        for relaxed in relaxed_constraints
        if relaxed.goal_metadata.is_custom_objective()
    ]


__all__ = [
    "build_weighted_objective",
    "build_sequential_objectives",
    "combine_objectives",
    "extract_custom_objectives",
]
