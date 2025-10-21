"""Sensitivity analysis for LumiX optimization models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Generic, List, Optional, Tuple, TypeVar

from ..core.model import LXModel
from ..solution.solution import LXSolution

TModel = TypeVar("TModel")


@dataclass
class LXVariableSensitivity:
    """
    Sensitivity analysis results for a variable.

    Attributes:
        name: Variable name
        value: Current value in solution
        reduced_cost: Reduced cost (opportunity cost)
        allowable_increase: Maximum increase before basis change (if available)
        allowable_decrease: Maximum decrease before basis change (if available)
        is_basic: Whether variable is basic in optimal solution
        is_at_bound: Whether variable is at its bound
    """

    name: str
    value: float
    reduced_cost: Optional[float] = None
    allowable_increase: Optional[float] = None
    allowable_decrease: Optional[float] = None
    is_basic: bool = False
    is_at_bound: bool = False


@dataclass
class LXConstraintSensitivity:
    """
    Sensitivity analysis results for a constraint.

    Attributes:
        name: Constraint name
        shadow_price: Shadow price (marginal value of relaxation)
        slack: Slack or surplus value
        allowable_increase: Maximum RHS increase before basis change (if available)
        allowable_decrease: Maximum RHS decrease before basis change (if available)
        is_binding: Whether constraint is binding (tight)
        is_active: Whether constraint is active at optimum
    """

    name: str
    shadow_price: Optional[float] = None
    slack: Optional[float] = None
    allowable_increase: Optional[float] = None
    allowable_decrease: Optional[float] = None
    is_binding: bool = False
    is_active: bool = False


class LXSensitivityAnalyzer(Generic[TModel]):
    """
    Sensitivity analysis for optimization models.

    Analyzes how changes in parameters affect the optimal solution, including:
    - Shadow prices (dual values) for constraints
    - Reduced costs for variables
    - Binding constraints identification
    - Sensitivity ranges (when available from solver)

    Examples:
        # Create analyzer
        analyzer = LXSensitivityAnalyzer(model, solution)

        # Analyze variable sensitivity
        var_sensitivity = analyzer.analyze_variable("production")
        print(f"Reduced cost: {var_sensitivity.reduced_cost}")

        # Analyze constraint sensitivity
        const_sensitivity = analyzer.analyze_constraint("capacity")
        print(f"Shadow price: {const_sensitivity.shadow_price}")

        # Get binding constraints
        binding = analyzer.get_binding_constraints()
        for name, sensitivity in binding.items():
            print(f"{name}: shadow price = {sensitivity.shadow_price}")

        # Generate full report
        print(analyzer.generate_report())

        # Get most sensitive parameters
        sensitive_constraints = analyzer.get_most_sensitive_constraints(top_n=5)
    """

    def __init__(self, model: LXModel[TModel], solution: LXSolution[TModel]):
        """
        Initialize sensitivity analyzer.

        Args:
            model: Optimization model
            solution: Solution to analyze
        """
        self.model = model
        self.solution = solution
        self._variable_sensitivity_cache: Dict[str, LXVariableSensitivity] = {}
        self._constraint_sensitivity_cache: Dict[str, LXConstraintSensitivity] = {}

    def analyze_variable(self, var_name: str) -> LXVariableSensitivity:
        """
        Analyze sensitivity of a variable.

        Args:
            var_name: Variable name

        Returns:
            Variable sensitivity information

        Raises:
            ValueError: If variable not found in solution
        """
        # Check cache
        if var_name in self._variable_sensitivity_cache:
            return self._variable_sensitivity_cache[var_name]

        # Get variable value
        if var_name not in self.solution.variables:
            raise ValueError(f"Variable '{var_name}' not found in solution")

        var_value = self.solution.variables[var_name]

        # Handle indexed variables (get first value or 0)
        if isinstance(var_value, dict):
            value = next(iter(var_value.values())) if var_value else 0.0
        else:
            value = float(var_value)

        # Get reduced cost
        reduced_cost = self.solution.get_reduced_cost(var_name)

        # Get variable bounds
        variable = self.model.get_variable(var_name)
        lower_bound = variable.lower_bound if variable else None
        upper_bound = variable.upper_bound if variable else None

        # Determine if at bound
        is_at_bound = False
        if lower_bound is not None and abs(value - float(lower_bound)) < 1e-6:
            is_at_bound = True
        elif upper_bound is not None and abs(value - float(upper_bound)) < 1e-6:
            is_at_bound = True

        # Determine if basic (non-zero reduced cost means non-basic)
        is_basic = reduced_cost is None or abs(reduced_cost) < 1e-6

        sensitivity = LXVariableSensitivity(
            name=var_name,
            value=value,
            reduced_cost=reduced_cost,
            is_basic=is_basic,
            is_at_bound=is_at_bound,
            # Note: allowable_increase/decrease require solver support
            # These would be populated by solver-specific sensitivity analysis
        )

        # Cache result
        self._variable_sensitivity_cache[var_name] = sensitivity

        return sensitivity

    def analyze_constraint(self, constraint_name: str) -> LXConstraintSensitivity:
        """
        Analyze sensitivity of a constraint.

        Args:
            constraint_name: Constraint name

        Returns:
            Constraint sensitivity information
        """
        # Check cache
        if constraint_name in self._constraint_sensitivity_cache:
            return self._constraint_sensitivity_cache[constraint_name]

        # Get shadow price
        shadow_price = self.solution.get_shadow_price(constraint_name)

        # Determine if binding (non-zero shadow price indicates binding)
        is_binding = shadow_price is not None and abs(shadow_price) > 1e-6
        is_active = is_binding  # For linear programs, binding = active

        sensitivity = LXConstraintSensitivity(
            name=constraint_name,
            shadow_price=shadow_price,
            is_binding=is_binding,
            is_active=is_active,
            # Note: slack and allowable ranges require solver support
            # These would be populated by solver-specific sensitivity analysis
        )

        # Cache result
        self._constraint_sensitivity_cache[constraint_name] = sensitivity

        return sensitivity

    def analyze_all_variables(self) -> Dict[str, LXVariableSensitivity]:
        """
        Analyze all variables in solution.

        Returns:
            Dictionary mapping variable names to sensitivity information
        """
        results = {}
        for var_name in self.solution.variables:
            results[var_name] = self.analyze_variable(var_name)
        return results

    def analyze_all_constraints(self) -> Dict[str, LXConstraintSensitivity]:
        """
        Analyze all constraints in model.

        Returns:
            Dictionary mapping constraint names to sensitivity information
        """
        results = {}
        for constraint in self.model.constraints:
            results[constraint.name] = self.analyze_constraint(constraint.name)
        return results

    def get_binding_constraints(
        self,
        threshold: float = 1e-6,
    ) -> Dict[str, LXConstraintSensitivity]:
        """
        Get all binding (tight) constraints.

        A constraint is binding if its shadow price is non-zero.

        Args:
            threshold: Threshold for considering shadow price as non-zero

        Returns:
            Dictionary of binding constraints

        Examples:
            binding = analyzer.get_binding_constraints()
            for name, sens in binding.items():
                print(f"{name} is binding with shadow price {sens.shadow_price}")
        """
        all_constraints = self.analyze_all_constraints()
        return {
            name: sens
            for name, sens in all_constraints.items()
            if sens.shadow_price is not None and abs(sens.shadow_price) > threshold
        }

    def get_non_basic_variables(
        self,
        threshold: float = 1e-6,
    ) -> Dict[str, LXVariableSensitivity]:
        """
        Get all non-basic variables (with non-zero reduced costs).

        Args:
            threshold: Threshold for considering reduced cost as non-zero

        Returns:
            Dictionary of non-basic variables
        """
        all_variables = self.analyze_all_variables()
        return {
            name: sens
            for name, sens in all_variables.items()
            if sens.reduced_cost is not None and abs(sens.reduced_cost) > threshold
        }

    def get_most_sensitive_constraints(
        self,
        top_n: int = 10,
    ) -> List[Tuple[str, LXConstraintSensitivity]]:
        """
        Get constraints with highest shadow prices (most valuable to relax).

        Args:
            top_n: Number of constraints to return

        Returns:
            List of (name, sensitivity) tuples sorted by shadow price magnitude

        Examples:
            top_constraints = analyzer.get_most_sensitive_constraints(top_n=5)
            for name, sens in top_constraints:
                print(f"{name}: ${sens.shadow_price:.2f} per unit relaxation")
        """
        all_constraints = self.analyze_all_constraints()

        # Filter to those with shadow prices
        with_shadow_prices = [
            (name, sens)
            for name, sens in all_constraints.items()
            if sens.shadow_price is not None
        ]

        # Sort by absolute shadow price (magnitude)
        sorted_constraints = sorted(
            with_shadow_prices,
            key=lambda x: abs(x[1].shadow_price or 0),
            reverse=True,
        )

        return sorted_constraints[:top_n]

    def get_most_sensitive_variables(
        self,
        top_n: int = 10,
    ) -> List[Tuple[str, LXVariableSensitivity]]:
        """
        Get variables with highest reduced costs.

        Args:
            top_n: Number of variables to return

        Returns:
            List of (name, sensitivity) tuples sorted by reduced cost magnitude
        """
        all_variables = self.analyze_all_variables()

        # Filter to those with reduced costs
        with_reduced_costs = [
            (name, sens)
            for name, sens in all_variables.items()
            if sens.reduced_cost is not None
        ]

        # Sort by absolute reduced cost
        sorted_variables = sorted(
            with_reduced_costs,
            key=lambda x: abs(x[1].reduced_cost or 0),
            reverse=True,
        )

        return sorted_variables[:top_n]

    def identify_bottlenecks(
        self,
        shadow_price_threshold: float = 0.01,
    ) -> List[str]:
        """
        Identify bottleneck constraints (binding with high shadow prices).

        Args:
            shadow_price_threshold: Minimum shadow price to consider

        Returns:
            List of bottleneck constraint names

        Examples:
            bottlenecks = analyzer.identify_bottlenecks()
            print(f"Found {len(bottlenecks)} bottlenecks:")
            for name in bottlenecks:
                print(f"  - {name}")
        """
        binding = self.get_binding_constraints()
        bottlenecks = [
            name
            for name, sens in binding.items()
            if sens.shadow_price is not None
            and abs(sens.shadow_price) >= shadow_price_threshold
        ]
        return bottlenecks

    def generate_report(
        self,
        include_variables: bool = True,
        include_constraints: bool = True,
        include_binding_only: bool = False,
        top_n: Optional[int] = None,
    ) -> str:
        """
        Generate comprehensive sensitivity analysis report.

        Args:
            include_variables: Include variable sensitivity
            include_constraints: Include constraint sensitivity
            include_binding_only: Only show binding constraints
            top_n: Only show top N most sensitive items

        Returns:
            Formatted sensitivity report

        Examples:
            # Full report
            print(analyzer.generate_report())

            # Only binding constraints
            print(analyzer.generate_report(
                include_variables=False,
                include_binding_only=True
            ))

            # Top 10 most sensitive
            print(analyzer.generate_report(top_n=10))
        """
        lines = ["Sensitivity Analysis Report", "=" * 80]

        # Solution summary
        lines.append("")
        lines.append(f"Model: {self.model.name}")
        lines.append(f"Objective Value: {self.solution.objective_value:,.2f}")
        lines.append(f"Status: {self.solution.status}")
        lines.append(f"Solve Time: {self.solution.solve_time:.3f}s")

        # Constraint sensitivity
        if include_constraints:
            lines.append("")
            lines.append("Constraint Sensitivity (Shadow Prices)")
            lines.append("=" * 80)

            if include_binding_only:
                constraints = self.get_binding_constraints()
                lines.append(f"Showing {len(constraints)} binding constraints")
            else:
                constraints = self.analyze_all_constraints()

            if top_n is not None:
                # Get top N by shadow price magnitude
                sorted_items = sorted(
                    constraints.items(),
                    key=lambda x: abs(x[1].shadow_price or 0),
                    reverse=True,
                )
                constraints = dict(sorted_items[:top_n])
                lines.append(f"Showing top {top_n} by shadow price magnitude")

            lines.append("")
            lines.append(f"{'Constraint':<30s} {'Shadow Price':>15s} {'Status':>12s}")
            lines.append("-" * 80)

            for name, sens in sorted(
                constraints.items(),
                key=lambda x: abs(x[1].shadow_price or 0),
                reverse=True,
            ):
                shadow_str = f"{sens.shadow_price:.6f}" if sens.shadow_price else "0.000000"
                status = "Binding" if sens.is_binding else "Non-binding"
                lines.append(f"{name:<30s} {shadow_str:>15s} {status:>12s}")

            # Interpretation
            lines.append("")
            lines.append("Interpretation:")
            lines.append("  • Shadow price = marginal value of relaxing constraint by 1 unit")
            lines.append("  • Positive = relaxing increases objective (for maximization)")
            lines.append("  • Binding = constraint is tight at optimum")

        # Variable sensitivity
        if include_variables:
            lines.append("")
            lines.append("Variable Sensitivity (Reduced Costs)")
            lines.append("=" * 80)

            variables = self.analyze_all_variables()

            if top_n is not None:
                # Get top N by reduced cost magnitude
                sorted_items = sorted(
                    variables.items(),
                    key=lambda x: abs(x[1].reduced_cost or 0),
                    reverse=True,
                )
                variables = dict(sorted_items[:top_n])
                lines.append(f"Showing top {top_n} by reduced cost magnitude")

            lines.append("")
            lines.append(f"{'Variable':<30s} {'Value':>15s} {'Reduced Cost':>15s} {'Status':>12s}")
            lines.append("-" * 80)

            for name, sens in sorted(
                variables.items(),
                key=lambda x: abs(x[1].reduced_cost or 0),
                reverse=True,
            ):
                value_str = f"{sens.value:.6f}"
                rc_str = f"{sens.reduced_cost:.6f}" if sens.reduced_cost else "0.000000"
                status = "At bound" if sens.is_at_bound else "Interior"
                lines.append(f"{name:<30s} {value_str:>15s} {rc_str:>15s} {status:>12s}")

            # Interpretation
            lines.append("")
            lines.append("Interpretation:")
            lines.append("  • Reduced cost = opportunity cost of forcing variable to increase")
            lines.append("  • Zero reduced cost = variable in optimal basis")
            lines.append("  • Non-zero = variable at bound, not economical to change")

        # Bottleneck analysis
        bottlenecks = self.identify_bottlenecks()
        if bottlenecks:
            lines.append("")
            lines.append("Identified Bottlenecks")
            lines.append("=" * 80)
            lines.append(f"Found {len(bottlenecks)} bottleneck constraints:")
            for name in bottlenecks:
                sens = self.analyze_constraint(name)
                lines.append(f"  • {name}: shadow price = {sens.shadow_price:.6f}")

        return "\n".join(lines)

    def generate_summary(self) -> str:
        """
        Generate brief sensitivity summary.

        Returns:
            Brief summary of key sensitivity metrics
        """
        binding = self.get_binding_constraints()
        bottlenecks = self.identify_bottlenecks()
        non_basic = self.get_non_basic_variables()

        lines = ["Sensitivity Summary", "=" * 80]
        lines.append(f"Binding constraints: {len(binding)}")
        lines.append(f"Bottlenecks (high shadow price): {len(bottlenecks)}")
        lines.append(f"Non-basic variables: {len(non_basic)}")

        if bottlenecks:
            lines.append("")
            lines.append("Top bottlenecks to address:")
            top_bottlenecks = self.get_most_sensitive_constraints(top_n=3)
            for name, sens in top_bottlenecks:
                lines.append(f"  • {name}: shadow price = {sens.shadow_price:.4f}")

        return "\n".join(lines)


__all__ = [
    "LXSensitivityAnalyzer",
    "LXVariableSensitivity",
    "LXConstraintSensitivity",
]
