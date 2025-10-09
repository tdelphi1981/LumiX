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
    - Mapped values (variables mapped to model instances)
    - Shadow prices (dual values for constraints)
    - Reduced costs (for sensitivity analysis)

    Examples:
        solution = optimizer.solve(model)

        # Access by variable name
        prod_value = solution.variables["production"]

        # Access by LXVariable object
        prod_value = solution.get_variable(production)

        # Access multi-indexed variables
        duty_value = solution.variables["duty"][(driver_id, date)]

        # Access mapped to models
        for (driver, date), value in solution.get_mapped(duty).items():
            if value > 0.5:
                print(f"{driver.name} works on {date}")
    """

    objective_value: float
    status: str
    solve_time: float

    # Type-safe variable values
    variables: Dict[str, Union[float, Dict[Any, float]]] = field(default_factory=dict)

    # Mapped to original models
    mapped: Dict[str, Dict[TModel, float]] = field(default_factory=dict)

    # Sensitivity data
    shadow_prices: Dict[str, float] = field(default_factory=dict)
    reduced_costs: Dict[str, float] = field(default_factory=dict)

    # Solver-specific information
    gap: Optional[float] = None
    iterations: Optional[int] = None
    nodes: Optional[int] = None

    def get_variable(self, var: LXVariable[TModel, TValue]) -> Union[TValue, Dict[Any, TValue]]:
        """
        Get variable value with full type inference.

        Args:
            var: LXVariable to get value for

        Returns:
            Variable value (scalar or dict for indexed variables)
        """
        return self.variables.get(var.name, 0)  # type: ignore

    def get_mapped(self, var: LXVariable[TModel, TValue]) -> Dict[TModel, TValue]:
        """
        Get values mapped to model instances.

        Args:
            var: LXVariable to get mapped values for

        Returns:
            Dictionary mapping model instances to values
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

        return "\n".join(summary_lines)


__all__ = ["LXSolution"]
