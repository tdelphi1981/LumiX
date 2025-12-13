"""Scenario and What-If analysis for LumiX models."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Dict, Generic, List, Optional, TypeVar, Union

from typing_extensions import Self

from ..core.constraints import LXConstraint
from ..core.model import LXModel
from ..core.variables import LXVariable
from ..solution.solution import LXSolution
from ..solvers.base import LXOptimizer

if TYPE_CHECKING:
    from ..visualization.scenario import LXScenarioCompare

TModel = TypeVar("TModel")


@dataclass
class LXScenarioModification:
    """
    Represents a single modification to a model parameter.

    Examples:
        Increase capacity by 20%::

            LXScenarioModification(
                target_type="constraint",
                target_name="capacity",
                modification_type="rhs_multiply",
                value=1.2
            )

        Set minimum production to 100::

            LXScenarioModification(
                target_type="constraint",
                target_name="min_production",
                modification_type="rhs_set",
                value=100.0
            )
    """

    target_type: str  # "constraint", "variable", "objective"
    target_name: str  # Name of the constraint/variable
    modification_type: str  # "rhs_set", "rhs_add", "rhs_multiply", "bound_set", "coeff_multiply"
    value: Union[float, Callable[[Any], float]]
    description: str = ""


@dataclass
class LXScenario(Generic[TModel]):
    """
    Type-safe scenario definition for what-if analysis.

    A scenario represents a set of modifications to a base model that allow
    you to explore different business conditions or assumptions.

    Examples:
        Create a high-capacity scenario::

            high_capacity = (
                LXScenario[Product]("high_capacity")
                .modify_constraint_rhs("capacity", multiply=1.5)
                .describe("Increase capacity by 50%")
            )

        Create a low-cost scenario::

            low_cost = (
                LXScenario[Product]("low_cost")
                .modify_constraint_rhs("min_production", set_value=50.0)
                .modify_variable_bound("production", lower=10.0)
                .describe("Lower minimum production requirements")
            )

        Create a combined scenario::

            optimistic = (
                LXScenario[Product]("optimistic")
                .modify_constraint_rhs("capacity", multiply=1.3)
                .modify_constraint_rhs("budget", add=10000.0)
                .describe("Optimistic market conditions")
            )
    """

    name: str
    modifications: List[LXScenarioModification] = field(default_factory=list)
    description: str = ""

    def describe(self, description: str) -> Self:
        """
        Add description to scenario.

        Args:
            description: Human-readable description

        Returns:
            Self for chaining
        """
        self.description = description
        return self

    def modify_constraint_rhs(
        self,
        constraint_name: str,
        set_value: Optional[float] = None,
        add: Optional[float] = None,
        multiply: Optional[float] = None,
        description: str = "",
    ) -> Self:
        """
        Modify constraint right-hand side.

        Args:
            constraint_name: Name of constraint to modify
            set_value: Set RHS to this value
            add: Add this value to RHS
            multiply: Multiply RHS by this factor
            description: Description of modification

        Returns:
            Self for chaining

        Examples:
            # Set capacity to 1000
            scenario.modify_constraint_rhs("capacity", set_value=1000.0)

            # Increase capacity by 200
            scenario.modify_constraint_rhs("capacity", add=200.0)

            # Increase capacity by 50%
            scenario.modify_constraint_rhs("capacity", multiply=1.5)
        """
        if set_value is not None:
            mod = LXScenarioModification(
                target_type="constraint",
                target_name=constraint_name,
                modification_type="rhs_set",
                value=set_value,
                description=description or f"Set {constraint_name} RHS to {set_value}",
            )
        elif add is not None:
            mod = LXScenarioModification(
                target_type="constraint",
                target_name=constraint_name,
                modification_type="rhs_add",
                value=add,
                description=description or f"Add {add} to {constraint_name} RHS",
            )
        elif multiply is not None:
            mod = LXScenarioModification(
                target_type="constraint",
                target_name=constraint_name,
                modification_type="rhs_multiply",
                value=multiply,
                description=description or f"Multiply {constraint_name} RHS by {multiply}",
            )
        else:
            raise ValueError("Must specify one of: set_value, add, or multiply")

        self.modifications.append(mod)
        return self

    def modify_variable_bound(
        self,
        variable_name: str,
        lower: Optional[float] = None,
        upper: Optional[float] = None,
        description: str = "",
    ) -> Self:
        """
        Modify variable bounds.

        Args:
            variable_name: Name of variable to modify
            lower: New lower bound
            upper: New upper bound
            description: Description of modification

        Returns:
            Self for chaining

        Examples:
            # Set lower bound
            scenario.modify_variable_bound("production", lower=100.0)

            # Set both bounds
            scenario.modify_variable_bound("inventory", lower=50.0, upper=500.0)
        """
        if lower is not None:
            mod = LXScenarioModification(
                target_type="variable",
                target_name=variable_name,
                modification_type="bound_lower",
                value=lower,
                description=description or f"Set {variable_name} lower bound to {lower}",
            )
            self.modifications.append(mod)

        if upper is not None:
            mod = LXScenarioModification(
                target_type="variable",
                target_name=variable_name,
                modification_type="bound_upper",
                value=upper,
                description=description or f"Set {variable_name} upper bound to {upper}",
            )
            self.modifications.append(mod)

        return self

    def add_custom_modification(self, modification: LXScenarioModification) -> Self:
        """
        Add custom modification.

        Args:
            modification: Custom modification to add

        Returns:
            Self for chaining
        """
        self.modifications.append(modification)
        return self


class LXScenarioAnalyzer(Generic[TModel]):
    """
    Scenario analysis for optimization models.

    Allows running multiple what-if scenarios on a base model and comparing
    the results to understand how different assumptions affect outcomes.

    Examples:
        Create analyzer and add scenarios::

            analyzer = LXScenarioAnalyzer(base_model, optimizer)

            # Add scenarios
            analyzer.add_scenario(
                LXScenario[Product]("high_capacity")
                .modify_constraint_rhs("capacity", multiply=1.5)
            )

            analyzer.add_scenario(
                LXScenario[Product]("low_capacity")
                .modify_constraint_rhs("capacity", multiply=0.8)
            )

            # Run all scenarios
            results = analyzer.run_all_scenarios()

            # Compare results
            print(analyzer.compare_scenarios())

            # Get specific result
            high_cap_solution = analyzer.get_result("high_capacity")
    """

    def __init__(
        self,
        base_model: LXModel[TModel],
        optimizer: LXOptimizer[TModel],
        include_baseline: bool = True,
    ):
        """
        Initialize scenario analyzer.

        Args:
            base_model: Base optimization model
            optimizer: Optimizer to use for solving scenarios
            include_baseline: Whether to include baseline (unmodified) scenario
        """
        self.base_model = base_model
        self.optimizer = optimizer
        self.include_baseline = include_baseline
        self.scenarios: Dict[str, LXScenario[TModel]] = {}
        self.results: Dict[str, LXSolution[TModel]] = {}

    def add_scenario(self, scenario: LXScenario[TModel]) -> Self:
        """
        Add scenario to analyze.

        Args:
            scenario: Scenario to add

        Returns:
            Self for chaining
        """
        self.scenarios[scenario.name] = scenario
        return self

    def add_scenarios(self, *scenarios: LXScenario[TModel]) -> Self:
        """
        Add multiple scenarios.

        Args:
            *scenarios: Scenarios to add

        Returns:
            Self for chaining
        """
        for scenario in scenarios:
            self.scenarios[scenario.name] = scenario
        return self

    def run_scenario(self, scenario_name: str) -> LXSolution[TModel]:
        """
        Run single scenario.

        Args:
            scenario_name: Name of scenario to run

        Returns:
            Solution for the scenario

        Raises:
            KeyError: If scenario not found
        """
        if scenario_name not in self.scenarios:
            raise KeyError(f"Scenario '{scenario_name}' not found")

        scenario = self.scenarios[scenario_name]
        modified_model = self._apply_scenario(scenario)
        solution = self.optimizer.solve(modified_model)
        self.results[scenario_name] = solution

        return solution

    def run_all_scenarios(self, include_baseline: Optional[bool] = None) -> Dict[str, LXSolution[TModel]]:
        """
        Run all scenarios.

        Args:
            include_baseline: Override include_baseline setting

        Returns:
            Dictionary mapping scenario names to solutions
        """
        include_baseline = include_baseline if include_baseline is not None else self.include_baseline

        # Run baseline if requested
        if include_baseline:
            baseline_solution = self.optimizer.solve(self.base_model)
            self.results["baseline"] = baseline_solution

        # Run all scenarios
        for scenario_name in self.scenarios:
            self.run_scenario(scenario_name)

        return self.results

    def get_result(self, scenario_name: str) -> Optional[LXSolution[TModel]]:
        """
        Get result for specific scenario.

        Args:
            scenario_name: Name of scenario

        Returns:
            Solution if available, None otherwise
        """
        return self.results.get(scenario_name)

    def compare_scenarios(
        self,
        scenario_names: Optional[List[str]] = None,
        include_baseline: bool = True,
        sort_by_objective: bool = True,
    ) -> str:
        """
        Compare scenario results.

        Args:
            scenario_names: Scenarios to compare (None = all)
            include_baseline: Include baseline in comparison
            sort_by_objective: Sort results by objective value

        Returns:
            Formatted comparison report
        """
        if not self.results:
            return "No results available. Run scenarios first."

        # Determine which scenarios to include
        if scenario_names is None:
            compare_names = list(self.results.keys())
        else:
            compare_names = [name for name in scenario_names if name in self.results]

        if not include_baseline and "baseline" in compare_names:
            compare_names.remove("baseline")

        if not compare_names:
            return "No scenarios to compare."

        # Sort by objective if requested
        if sort_by_objective:
            compare_names.sort(key=lambda name: self.results[name].objective_value, reverse=True)

        # Build comparison report
        lines = ["Scenario Comparison", "=" * 80]

        # Add baseline reference if available
        if "baseline" in self.results:
            baseline_obj = self.results["baseline"].objective_value
            lines.append(f"Baseline Objective: {baseline_obj:,.2f}")
            lines.append("")

        # Add scenario results
        lines.append(f"{'Scenario':<30s} {'Objective':>15s} {'Status':>12s} {'vs Baseline':>15s}")
        lines.append("-" * 80)

        for name in compare_names:
            solution = self.results[name]
            obj_str = f"{solution.objective_value:,.2f}"
            status_str = solution.status

            # Calculate difference from baseline
            if "baseline" in self.results and name != "baseline":
                baseline_obj = self.results["baseline"].objective_value
                if baseline_obj != 0:
                    diff_pct = ((solution.objective_value - baseline_obj) / baseline_obj) * 100
                    diff_str = f"{diff_pct:+.2f}%"
                else:
                    diff_str = "N/A"
            else:
                diff_str = "-"

            lines.append(f"{name:<30s} {obj_str:>15s} {status_str:>12s} {diff_str:>15s}")

        # Add scenario descriptions
        lines.append("")
        lines.append("Scenario Descriptions:")
        lines.append("-" * 80)
        for name in compare_names:
            if name == "baseline":
                lines.append(f"  baseline: Original model without modifications")
            elif name in self.scenarios:
                scenario = self.scenarios[name]
                desc = scenario.description or "No description"
                lines.append(f"  {name}: {desc}")
                for mod in scenario.modifications:
                    if mod.description:
                        lines.append(f"    • {mod.description}")

        return "\n".join(lines)

    def get_best_scenario(self, maximize: bool = True) -> Optional[str]:
        """
        Get name of best scenario by objective value.

        Args:
            maximize: True if objective is maximization, False for minimization

        Returns:
            Name of best scenario, or None if no results
        """
        if not self.results:
            return None

        if maximize:
            return max(self.results.items(), key=lambda x: x[1].objective_value)[0]
        else:
            return min(self.results.items(), key=lambda x: x[1].objective_value)[0]

    def sensitivity_to_parameter(
        self,
        parameter_name: str,
        values: List[float],
        modification_type: str = "rhs_multiply",
        target_type: str = "constraint",
    ) -> Dict[float, LXSolution[TModel]]:
        """
        Analyze sensitivity to a single parameter across multiple values.

        Args:
            parameter_name: Name of parameter to vary
            values: List of values to test
            modification_type: Type of modification
            target_type: Type of target ("constraint" or "variable")

        Returns:
            Dictionary mapping parameter values to solutions

        Examples:
            Analyze sensitivity to capacity multiplier::

                results = analyzer.sensitivity_to_parameter(
                    "capacity",
                    values=[0.8, 0.9, 1.0, 1.1, 1.2, 1.3],
                    modification_type="rhs_multiply"
                )

                for multiplier, solution in results.items():
                    print(f"Capacity × {multiplier}: ${solution.objective_value:,.2f}")
        """
        sensitivity_results: Dict[float, LXSolution[TModel]] = {}

        for value in values:
            # Create temporary scenario
            scenario = LXScenario[TModel](f"{parameter_name}_{value}")
            mod = LXScenarioModification(
                target_type=target_type,
                target_name=parameter_name,
                modification_type=modification_type,
                value=value,
            )
            scenario.modifications.append(mod)

            # Apply and solve
            modified_model = self._apply_scenario(scenario)
            solution = self.optimizer.solve(modified_model)
            sensitivity_results[value] = solution

        return sensitivity_results

    def _apply_scenario(self, scenario: LXScenario[TModel]) -> LXModel[TModel]:
        """
        Apply scenario modifications to create modified model.

        Args:
            scenario: Scenario to apply

        Returns:
            Modified model
        """
        # Deep copy the model
        modified_model = self._clone_model(self.base_model)

        # Apply each modification
        for mod in scenario.modifications:
            if mod.target_type == "constraint":
                self._apply_constraint_modification(modified_model, mod)
            elif mod.target_type == "variable":
                self._apply_variable_modification(modified_model, mod)
            elif mod.target_type == "objective":
                # Future: objective modifications
                pass

        return modified_model

    def _clone_model(self, model: LXModel[TModel]) -> LXModel[TModel]:
        """
        Clone a model (deep copy).

        Args:
            model: Model to clone

        Returns:
            Cloned model
        """
        # Deep copy is safest approach
        return deepcopy(model)

    def _apply_constraint_modification(
        self,
        model: LXModel[TModel],
        mod: LXScenarioModification,
    ) -> None:
        """
        Apply constraint modification to model.

        Args:
            model: Model to modify
            mod: Modification to apply
        """
        constraint = model.get_constraint(mod.target_name)
        if constraint is None:
            raise ValueError(f"Constraint '{mod.target_name}' not found in model")

        if mod.modification_type == "rhs_set":
            constraint.rhs_value = float(mod.value)  # type: ignore
        elif mod.modification_type == "rhs_add":
            if constraint.rhs_value is not None:
                constraint.rhs_value += float(mod.value)  # type: ignore
        elif mod.modification_type == "rhs_multiply":
            if constraint.rhs_value is not None:
                constraint.rhs_value *= float(mod.value)  # type: ignore

    def _apply_variable_modification(
        self,
        model: LXModel[TModel],
        mod: LXScenarioModification,
    ) -> None:
        """
        Apply variable modification to model.

        Args:
            model: Model to modify
            mod: Modification to apply
        """
        variable = model.get_variable(mod.target_name)
        if variable is None:
            raise ValueError(f"Variable '{mod.target_name}' not found in model")

        if mod.modification_type == "bound_lower":
            variable.lower_bound = float(mod.value)  # type: ignore
        elif mod.modification_type == "bound_upper":
            variable.upper_bound = float(mod.value)  # type: ignore

    def visualize(self) -> "LXScenarioCompare[TModel]":
        """
        Create interactive visualization for scenario comparison.

        Requires the visualization extra: pip install lumix-opt[viz]

        Returns:
            LXScenarioCompare instance

        Examples:
            Basic usage::

                analyzer = LXScenarioAnalyzer(model, optimizer)
                analyzer.add_scenario(scenario1)
                analyzer.add_scenario(scenario2)
                analyzer.run_all_scenarios()
                analyzer.visualize().show()

            Comparison chart::

                analyzer.visualize().plot_comparison().show()

            Export to HTML::

                analyzer.visualize().to_html("scenarios.html")
        """
        from ..visualization import LXScenarioCompare

        return LXScenarioCompare(self)


__all__ = [
    "LXScenario",
    "LXScenarioModification",
    "LXScenarioAnalyzer",
]
