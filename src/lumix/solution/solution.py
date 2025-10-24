"""Solution classes for LumiX."""

from dataclasses import dataclass, field
from typing import Any, Dict, Generic, Optional, TypeVar, Union

from ..core.variables import LXVariable

TModel = TypeVar("TModel")
TValue = TypeVar("TValue", int, float)
TIndex = TypeVar("TIndex")


@dataclass
class LXSolution(Generic[TModel]):
    """
    Type-safe solution with automatic mapping.

    Provides access to:

    - Variable values (by name or LXVariable object)
    - Mapped values (variables mapped by index keys)
    - Shadow prices (dual values for constraints)
    - Reduced costs (for sensitivity analysis)

    Examples:
        Basic usage::

            solution = optimizer.solve(model)

            # Access by variable name
            prod_value = solution.variables["production"]

            # Access by LXVariable object
            prod_value = solution.get_variable(production)

            # Access multi-indexed variables
            duty_value = solution.variables["duty"][(driver_id, date)]

            # Access mapped values (indexed by keys)
            for key, value in solution.get_mapped(duty).items():
                if value > 0.5:
                    print(f"Variable {key} = {value}")
    """

    objective_value: float
    status: str
    solve_time: float

    # Type-safe variable values
    variables: Dict[str, Union[float, Dict[Any, float]]] = field(default_factory=dict)

    # Mapped values by index keys (same structure as variables)
    # Note: Uses index keys (e.g., product.id) not model instances
    # to avoid hashability issues with non-frozen dataclasses
    mapped: Dict[str, Dict[Any, float]] = field(default_factory=dict)

    # Sensitivity data
    shadow_prices: Dict[str, float] = field(default_factory=dict)
    reduced_costs: Dict[str, float] = field(default_factory=dict)

    # Solver-specific information
    gap: Optional[float] = None
    iterations: Optional[int] = None
    nodes: Optional[int] = None

    # Goal programming information
    goal_deviations: Dict[str, Dict[str, Union[float, Dict[Any, float]]]] = field(
        default_factory=dict
    )

    def get_variable(self, var: LXVariable[TModel, TValue]) -> Union[TValue, Dict[Any, TValue]]:
        """
        Get variable value with full type inference.

        Args:
            var: LXVariable to get value for

        Returns:
            Variable value (scalar or dict for indexed variables)
        """
        return self.variables.get(var.name, 0)  # type: ignore

    def get_mapped(self, var: LXVariable[TModel, TValue]) -> Dict[Any, TValue]:
        """
        Get values mapped by index keys.

        Returns the same structure as variables, indexed by the keys
        extracted via the variable's index_func (e.g., product.id).

        Note:
            This returns index keys, not model instances, to avoid
            hashability issues with non-frozen dataclasses.

        Args:
            var: LXVariable to get mapped values for

        Returns:
            Dictionary mapping index keys to values

        Examples:
            For production indexed by product.id::

                for product_id, qty in solution.get_mapped(production).items():
                    print(f"Product {product_id}: {qty} units")
        """
        return self.mapped.get(var.name, {})  # type: ignore

    def get_shadow_price(self, constraint_name: str) -> Optional[float]:
        """
        Get shadow price (dual value) for constraint.

        Args:
            constraint_name: Constraint name

        Returns:
            Shadow price if available
        """
        return self.shadow_prices.get(constraint_name)

    def get_reduced_cost(self, var_name: str) -> Optional[float]:
        """
        Get reduced cost for variable.

        Args:
            var_name: Variable name

        Returns:
            Reduced cost if available
        """
        return self.reduced_costs.get(var_name)

    def get_goal_deviations(
        self, goal_name: str
    ) -> Optional[Dict[str, Union[float, Dict[Any, float]]]]:
        """
        Get deviation values for a goal constraint.

        Returns both positive and negative deviations for the specified goal.

        Args:
            goal_name: Name of the goal constraint

        Returns:
            Dictionary with keys 'pos' and 'neg' containing deviation values,
            or None if goal not found

        Example:
            >>> deviations = solution.get_goal_deviations("production_target")
            >>> pos_dev = deviations["pos"]  # Over-production
            >>> neg_dev = deviations["neg"]  # Under-production
        """
        return self.goal_deviations.get(goal_name)

    def is_goal_satisfied(
        self, goal_name: str, tolerance: float = 1e-6
    ) -> Optional[bool]:
        """
        Check if a goal is satisfied within tolerance.

        A goal is satisfied if both positive and negative deviations are
        within the specified tolerance.

        Args:
            goal_name: Name of the goal constraint
            tolerance: Tolerance for deviation (default: 1e-6)

        Returns:
            True if goal is satisfied, False if not, None if goal not found

        Example:
            >>> if solution.is_goal_satisfied("demand_goal", tolerance=0.01):
            ...     print("Demand goal achieved!")
        """
        deviations = self.get_goal_deviations(goal_name)
        if deviations is None:
            return None

        pos_dev = deviations.get("pos", 0)
        neg_dev = deviations.get("neg", 0)

        # Handle both scalar and dict values
        if isinstance(pos_dev, dict):
            pos_satisfied = all(abs(v) <= tolerance for v in pos_dev.values())
        else:
            pos_satisfied = abs(pos_dev) <= tolerance

        if isinstance(neg_dev, dict):
            neg_satisfied = all(abs(v) <= tolerance for v in neg_dev.values())
        else:
            neg_satisfied = abs(neg_dev) <= tolerance

        return pos_satisfied and neg_satisfied

    def get_total_deviation(self, goal_name: str) -> Optional[float]:
        """
        Get total absolute deviation for a goal.

        Sum of absolute values of all positive and negative deviations.

        Args:
            goal_name: Name of the goal constraint

        Returns:
            Total deviation, or None if goal not found

        Example:
            >>> total_dev = solution.get_total_deviation("production_target")
            >>> print(f"Total deviation: {total_dev}")
        """
        deviations = self.get_goal_deviations(goal_name)
        if deviations is None:
            return None

        total = 0.0

        for dev_type in ["pos", "neg"]:
            dev = deviations.get(dev_type, 0)
            if isinstance(dev, dict):
                total += sum(abs(v) for v in dev.values())
            else:
                total += abs(dev)

        return total

    def is_optimal(self) -> bool:
        """Check if solution is optimal."""
        return self.status.lower() in ["optimal", "opt_optimal"]

    def is_feasible(self) -> bool:
        """Check if solution is feasible."""
        return self.status.lower() in ["optimal", "feasible", "opt_optimal"]

    def summary(self) -> str:
        """
        Get solution summary.

        Returns:
            String summary
        """
        nonzero = sum(
            1
            for v in self.variables.values()
            if (isinstance(v, dict) and any(abs(val) > 1e-6 for val in v.values()))
            or (isinstance(v, (int, float)) and abs(v) > 1e-6)
        )

        summary_lines = [
            f"Status: {self.status}",
            f"Objective: {self.objective_value:.6f}",
            f"Solve time: {self.solve_time:.3f}s",
            f"Non-zero variables: {nonzero}/{len(self.variables)}",
        ]

        if self.gap is not None:
            summary_lines.append(f"Gap: {self.gap * 100:.2f}%")
        if self.iterations is not None:
            summary_lines.append(f"Iterations: {self.iterations}")
        if self.nodes is not None:
            summary_lines.append(f"Nodes: {self.nodes}")

        # Add goal programming summary
        if self.goal_deviations:
            summary_lines.append(f"\nGoal Constraints: {len(self.goal_deviations)}")
            satisfied = sum(
                1
                for goal_name in self.goal_deviations.keys()
                if self.is_goal_satisfied(goal_name, tolerance=1e-6)
            )
            summary_lines.append(
                f"Goals Satisfied: {satisfied}/{len(self.goal_deviations)}"
            )

        return "\n".join(summary_lines)


__all__ = ["LXSolution"]
