"""Constraint relaxation for goal programming."""

from typing import Any, Callable, Dict, Generic, List, Tuple, TypeVar

from lumix.core.constraints import LXConstraint
from lumix.core.enums import LXConstraintSense
from lumix.core.expressions import LXLinearExpression, LXNonLinearExpression, LXRowKeyFilter
from lumix.core.variables import LXVariable

from .goal import LXGoal, LXGoalMetadata, get_deviation_var_name

TModel = TypeVar("TModel")


class RelaxedConstraint(Generic[TModel]):
    """
    Result of relaxing a constraint for goal programming.

    Contains the relaxed constraint (now an equality with deviation variables),
    the deviation variables themselves, and the goal instances that serve as
    the data source for deviation variables. In an indexed goal every row has
    its own pair of deviations (``<name>_<key>``).
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

    def __deepcopy__(self, memo):
        """Custom deepcopy that handles constraint and deviation variables.

        Args:
            memo: Dictionary for tracking circular references during deepcopy

        Returns:
            Deep copy of this relaxed constraint
        """
        from copy import deepcopy

        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result

        # Deep copy all components
        result.constraint = deepcopy(self.constraint, memo)
        result.pos_deviation = deepcopy(self.pos_deviation, memo)
        result.neg_deviation = deepcopy(self.neg_deviation, memo)
        result.goal_metadata = deepcopy(self.goal_metadata, memo)
        result.goal_instances = deepcopy(self.goal_instances, memo)

        return result

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

    # The sense may have been set after as_goal() (``.as_goal(1).ge()``): use the
    # constraint's sense as it is now.
    goal_metadata.update_sense(constraint.sense)

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
                constraint_sense=constraint.sense,
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
            constraint_sense=constraint.sense,
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

    # Relaxed expression: original_expr + neg_dev - pos_dev
    lhs = constraint.lhs
    if isinstance(lhs, LXNonLinearExpression):
        relaxed_expr = LXNonLinearExpression(lhs.linear_terms.copy(), list(lhs.nonlinear_terms),
                                             lhs.constant)
        linear = relaxed_expr.linear_terms
    elif isinstance(lhs, LXLinearExpression):
        relaxed_expr = linear = lhs.copy()
    else:
        raise ValueError(
            f"Goal '{constraint.name}' has a {type(lhs).__name__} expression; goals take "
            "LXLinearExpression or LXNonLinearExpression")
    if is_indexed:
        _add_own_deviations(linear, constraint.name, constraint.index_func,
                            neg_deviation, pos_deviation)
    else:
        linear.add_term(neg_deviation, coeff=1.0)    # + neg_dev
        linear.add_term(pos_deviation, coeff=-1.0)   # - pos_dev

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


def _add_own_deviations(expr: LXLinearExpression, name: str, index_func: Callable[[Any], Any],
                        neg: LXVariable, pos: LXVariable) -> None:
    """Row ``r`` of an indexed goal gets only the deviations of its own goal ``name_<key>``
    (A22). The filter lets the canonical builder look that goal up by key; the
    two-argument coefficient gives the same rows to readers that call the filter
    with the instance only."""
    def row_key(row: Any) -> str:
        return f"{name}_{index_func(row)}"

    for var, sign in ((neg, 1.0), (pos, -1.0)):
        def coeff(g: LXGoal, row: Any, sign: float = sign) -> float:
            return sign if g.id == row_key(row) else 0.0
        expr.add_term(var, coeff=coeff, where=LXRowKeyFilter(var, row_key))


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
