"""Constraint relaxation for goal programming."""

from typing import Dict, Generic, List, Tuple, TypeVar

from lumix.core.constraints import LXConstraint
from lumix.core.enums import LXConstraintSense
from lumix.core.expressions import LXLinearExpression
from lumix.core.variables import LXVariable

from .goal import LXGoal, LXGoalMetadata, get_deviation_var_name

TModel = TypeVar("TModel")


class RelaxedConstraint(Generic[TModel]):
    """
    Result of relaxing a constraint for goal programming.

    Contains the relaxed constraint (now an equality with deviation variables),
    the deviation variables themselves, and the goal instances that serve as
    the data source for deviation variables.
    """

    def __init__(
        self,
        constraint: LXConstraint[TModel],
        pos_deviation: LXVariable[LXGoal, float],
        neg_deviation: LXVariable[LXGoal, float],
        goal_metadata: LXGoalMetadata,
        goal_instances: List[LXGoal],
    ):
        """
        Initialize relaxed constraint.

        Args:
            constraint: The relaxed constraint (LHS + neg_dev - pos_dev == RHS)
            pos_deviation: Positive deviation variable family (indexed by Goals)
            neg_deviation: Negative deviation variable family (indexed by Goals)
            goal_metadata: Goal metadata (priority, weight, undesired deviations)
            goal_instances: Goal instances serving as data source for deviations
        """
        self.constraint = constraint
        self.pos_deviation = pos_deviation
        self.neg_deviation = neg_deviation
        self.goal_metadata = goal_metadata
        self.goal_instances = goal_instances

    def get_undesired_variables(self) -> List[LXVariable[LXGoal, float]]:
        """
        Get list of undesired deviation variables to minimize.

        Returns:
            List of deviation variables to include in objective
        """
        undesired = []
        if self.goal_metadata.is_pos_undesired():
            undesired.append(self.pos_deviation)
        if self.goal_metadata.is_neg_undesired():
            undesired.append(self.neg_deviation)
        return undesired


def relax_constraint(
    constraint: LXConstraint[TModel],
    goal_metadata: LXGoalMetadata,
) -> RelaxedConstraint[TModel]:
    """
    Relax a constraint by adding deviation variables.

    Transforms the constraint based on its type:
    - LE (expr <= rhs): expr + neg_dev - pos_dev == rhs (minimize pos_dev)
    - GE (expr >= rhs): expr + neg_dev - pos_dev == rhs (minimize neg_dev)
    - EQ (expr == rhs): expr + neg_dev - pos_dev == rhs (minimize both)

    Args:
        constraint: Original goal constraint to relax
        goal_metadata: Goal metadata with priority and weight info

    Returns:
        RelaxedConstraint containing the equality constraint with deviations
        and the deviation variable families

    Raises:
        ValueError: If constraint has no LHS expression

    Example:
        >>> goal = LXConstraint[Product]("production_goal")
        ...     .expression(production_expr)
        ...     .ge()
        ...     .rhs(lambda p: p.target)
        >>> relaxed = relax_constraint(goal, goal_metadata)
        >>> # Now: production_expr + neg_dev - pos_dev == target
        >>> # Objective: minimize neg_dev (under-production is bad for GE)
    """
    if constraint.lhs is None:
        raise ValueError(
            f"Cannot relax constraint '{constraint.name}' - no LHS expression defined"
        )

    # Create deviation variables indexed by Goal instances
    pos_dev_name = get_deviation_var_name(constraint.name, "pos")
    neg_dev_name = get_deviation_var_name(constraint.name, "neg")

    # Check if constraint is indexed (has data instances)
    is_indexed = constraint.index_func is not None

    # Create Goal instances as the data source for deviation variables
    goal_instances: List[LXGoal] = []

    if is_indexed:
        # Create one Goal instance per constraint instance
        constraint_instances = constraint.get_instances()

        for instance in constraint_instances:
            # Get instance ID using the constraint's index function
            instance_id = constraint.index_func(instance)

            # Get target value (use function if available, otherwise constant)
            target_val = (
                constraint.rhs_func(instance)
                if constraint.rhs_func
                else constraint.rhs_value
            )

            # Create Goal instance for this constraint instance
            goal_instance = LXGoal(
                id=f"{constraint.name}_{instance_id}",
                constraint_name=constraint.name,
                priority=goal_metadata.priority,
                weight=goal_metadata.weight,
                constraint_sense=goal_metadata.constraint_sense,
                target_value=target_val,
                instance_id=instance_id,
            )
            goal_instances.append(goal_instance)

        # Create deviation variables indexed by Goal instances
        pos_deviation = (
            LXVariable[LXGoal, float](pos_dev_name)
            .continuous()
            .bounds(lower=0.0)
            .indexed_by(lambda g: g.id)
            .from_data(goal_instances)
        )
        neg_deviation = (
            LXVariable[LXGoal, float](neg_dev_name)
            .continuous()
            .bounds(lower=0.0)
            .indexed_by(lambda g: g.id)
            .from_data(goal_instances)
        )
    else:
        # Create single Goal instance for non-indexed constraint
        goal_instance = LXGoal(
            id=constraint.name,
            constraint_name=constraint.name,
            priority=goal_metadata.priority,
            weight=goal_metadata.weight,
            constraint_sense=goal_metadata.constraint_sense,
            target_value=constraint.rhs_value,
            instance_id=None,  # No instance for non-indexed constraints
        )
        goal_instances = [goal_instance]

        # Create deviation variables indexed by this single Goal
        pos_deviation = (
            LXVariable[LXGoal, float](pos_dev_name)
            .continuous()
            .bounds(lower=0.0)
            .indexed_by(lambda g: g.id)
            .from_data(goal_instances)
        )
        neg_deviation = (
            LXVariable[LXGoal, float](neg_dev_name)
            .continuous()
            .bounds(lower=0.0)
            .indexed_by(lambda g: g.id)
            .from_data(goal_instances)
        )

    # Create new expression: original_expr + neg_dev - pos_dev
    # Start with a copy of the original expression's terms
    relaxed_expr = LXLinearExpression[TModel]()
    relaxed_expr.terms = constraint.lhs.terms.copy()
    relaxed_expr._multi_terms = constraint.lhs._multi_terms.copy()
    relaxed_expr.constant = constraint.lhs.constant

    # Add deviation terms
    if is_indexed:
        # For indexed constraints, add terms with coefficient 1.0 for each instance
        relaxed_expr.add_term(neg_deviation, coeff=1.0)  # + neg_dev
        relaxed_expr.add_term(pos_deviation, coeff=-1.0)  # - pos_dev
    else:
        # For non-indexed constraints, same approach
        relaxed_expr.add_term(neg_deviation, coeff=1.0)
        relaxed_expr.add_term(pos_deviation, coeff=-1.0)

    # Create relaxed constraint (always equality)
    relaxed_constraint = LXConstraint[TModel](constraint.name)
    relaxed_constraint.lhs = relaxed_expr
    relaxed_constraint.sense = LXConstraintSense.EQ
    relaxed_constraint.rhs_value = constraint.rhs_value
    relaxed_constraint.rhs_func = constraint.rhs_func
    relaxed_constraint.model_type = constraint.model_type
    relaxed_constraint.index_func = constraint.index_func
    relaxed_constraint._data = constraint._data
    relaxed_constraint._session = constraint._session

    return RelaxedConstraint(
        constraint=relaxed_constraint,
        pos_deviation=pos_deviation,
        neg_deviation=neg_deviation,
        goal_metadata=goal_metadata,
        goal_instances=goal_instances,
    )


def relax_constraints(
    constraints: List[LXConstraint[TModel]],
    goal_metadata_map: Dict[str, LXGoalMetadata],
) -> List[RelaxedConstraint[TModel]]:
    """
    Relax multiple constraints for goal programming.

    Args:
        constraints: List of constraints to relax
        goal_metadata_map: Mapping from constraint name to goal metadata

    Returns:
        List of relaxed constraints with their deviation variables

    Example:
        >>> constraints = [goal1, goal2, goal3]
        >>> metadata = {
        ...     "goal1": LXGoalMetadata(priority=1, weight=1.0, ...),
        ...     "goal2": LXGoalMetadata(priority=2, weight=0.5, ...),
        ... }
        >>> relaxed = relax_constraints(constraints, metadata)
    """
    relaxed_list = []
    for constraint in constraints:
        if constraint.name in goal_metadata_map:
            goal_metadata = goal_metadata_map[constraint.name]
            relaxed = relax_constraint(constraint, goal_metadata)
            relaxed_list.append(relaxed)
    return relaxed_list


__all__ = ["RelaxedConstraint", "relax_constraint", "relax_constraints"]
