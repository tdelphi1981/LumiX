"""Goal programming metadata and data structures."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Set

from lumix.core.enums import LXConstraintSense


class LXGoalMode(Enum):
    """Goal programming solving modes."""

    WEIGHTED = "weighted"  # Single solve with weighted objectives
    SEQUENTIAL = "sequential"  # Lexicographic/preemptive (multiple solves)


@dataclass
class LXGoalMetadata:
    """
    Metadata for a goal constraint in goal programming.

    A goal constraint is a soft constraint that can be violated with a penalty.
    The goal is transformed by adding deviation variables:
        - For LE: expr + neg_dev - pos_dev == rhs (minimize pos_dev)
        - For GE: expr + neg_dev - pos_dev == rhs (minimize neg_dev)
        - For EQ: expr + neg_dev - pos_dev == rhs (minimize both)

    Attributes:
        priority: Priority level (1=highest, 2=second highest, etc.)
                  Priority 0 is reserved for custom objective terms
        weight: Relative weight within the same priority level
        constraint_sense: Original constraint type (LE, GE, EQ)
        undesired_deviations: Set of deviation types to minimize ('pos', 'neg', or both)
    """

    priority: int
    weight: float
    constraint_sense: LXConstraintSense
    undesired_deviations: Set[str] = field(default_factory=set)

    def __post_init__(self):
        """Determine undesired deviations based on constraint sense."""
        if not self.undesired_deviations:
            if self.constraint_sense == LXConstraintSense.LE:
                # expr <= rhs: positive deviation is undesired (over target)
                self.undesired_deviations = {"pos"}
            elif self.constraint_sense == LXConstraintSense.GE:
                # expr >= rhs: negative deviation is undesired (under target)
                self.undesired_deviations = {"neg"}
            elif self.constraint_sense == LXConstraintSense.EQ:
                # expr == rhs: both deviations are undesired
                self.undesired_deviations = {"pos", "neg"}

    def is_custom_objective(self) -> bool:
        """Check if this is a custom objective term (priority 0)."""
        return self.priority == 0

    def is_pos_undesired(self) -> bool:
        """Check if positive deviation should be minimized."""
        return "pos" in self.undesired_deviations

    def is_neg_undesired(self) -> bool:
        """Check if negative deviation should be minimized."""
        return "neg" in self.undesired_deviations


@dataclass
class LXGoal:
    """
    Represents a single goal instance in goal programming.

    Deviation variables are indexed by Goal instances, making deviations
    semantically meaningful: they measure achievement of specific goals
    rather than just constraint satisfaction.

    This provides practical business value:
    - Bus assignment: "Route 5 needs 3 additional buses" (neg_dev)
    - Production: "Product A has 20 units excess inventory" (pos_dev)
    - Scheduling: "Department B is 5 hours over overtime limit" (pos_dev)

    Attributes:
        id: Unique identifier for this goal instance
        constraint_name: Name of the original constraint
        priority: Goal priority level (1=highest, 0=custom objective)
        weight: Weight within the same priority level
        constraint_sense: Type of constraint (LE, GE, EQ)
        target_value: Target RHS value if constant
        instance_id: ID of the original constraint instance (if indexed)

    Examples:
        Single goal (non-indexed constraint):
            >>> goal = LXGoal(
            ...     id="total_demand",
            ...     constraint_name="demand_goal",
            ...     priority=1,
            ...     weight=1.0,
            ...     constraint_sense=LXConstraintSense.GE,
            ...     target_value=1000.0
            ... )

        Per-product goals (indexed constraint):
            >>> goals = [
            ...     LXGoal(
            ...         id="demand_product_1",
            ...         constraint_name="production_goal",
            ...         priority=1,
            ...         weight=1.0,
            ...         constraint_sense=LXConstraintSense.GE,
            ...         target_value=100.0,
            ...         instance_id=1
            ...     ),
            ...     LXGoal(
            ...         id="demand_product_2",
            ...         constraint_name="production_goal",
            ...         priority=1,
            ...         weight=1.0,
            ...         constraint_sense=LXConstraintSense.GE,
            ...         target_value=150.0,
            ...         instance_id=2
            ...     ),
            ... ]
    """

    id: str
    constraint_name: str
    priority: int
    weight: float
    constraint_sense: LXConstraintSense
    target_value: Optional[float] = None
    instance_id: Optional[Any] = None


def get_deviation_var_name(constraint_name: str, deviation_type: str) -> str:
    """
    Generate standard name for deviation variable.

    Args:
        constraint_name: Name of the goal constraint
        deviation_type: Either 'pos' or 'neg'

    Returns:
        Standard deviation variable name
    """
    return f"{constraint_name}_{deviation_type}_dev"


def priority_to_weight(priority: int, base: float = 10.0, exponent_offset: int = 6) -> float:
    """
    Convert priority level to weight for weighted goal programming.

    Higher priorities get exponentially larger weights to ensure
    they dominate lower priorities in the objective function.

    Args:
        priority: Priority level (1=highest, 2=second, etc.)
        base: Base for exponential scaling (default: 10)
        exponent_offset: Offset for exponent calculation (default: 6)
                        Priority 1 → 10^6, Priority 2 → 10^5, etc.

    Returns:
        Weight value for the priority level

    Examples:
        >>> priority_to_weight(1)
        1000000.0
        >>> priority_to_weight(2)
        100000.0
        >>> priority_to_weight(0)  # Custom objectives
        1.0
    """
    if priority == 0:
        # Custom objectives use weight 1.0 by default
        return 1.0
    return base ** (exponent_offset - priority)


__all__ = [
    "LXGoalMode",
    "LXGoalMetadata",
    "LXGoal",
    "get_deviation_var_name",
    "priority_to_weight",
]
