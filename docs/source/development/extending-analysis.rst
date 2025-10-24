Extending Analysis
==================

Guide for adding custom analysis types, extending existing analyzers, and creating specialized analysis tools.

Overview
--------

The analysis module is designed for extensibility. You can:

1. **Extend Existing Analyzers**: Add new methods to existing analysis classes
2. **Create New Analyzers**: Implement entirely new analysis types
3. **Custom Result Objects**: Define specialized result data structures
4. **Analysis Pipelines**: Combine multiple analyzers for complex workflows

Extension Patterns
------------------

1. Extending Sensitivity Analyzer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add custom metrics and analysis methods.

**Example: Relative Importance Analysis**

.. code-block:: python

   from lumix.analysis import LXSensitivityAnalyzer
   from typing import Dict

   class LXExtendedSensitivityAnalyzer(LXSensitivityAnalyzer[TModel]):
       """Enhanced sensitivity analysis with custom metrics."""

       def analyze_relative_importance(self) -> Dict[str, float]:
           """
           Calculate relative importance of each constraint.

           Returns:
               Dictionary mapping constraint names to importance scores (0-1)
           """
           bottlenecks = self.identify_bottlenecks()

           # Get shadow prices
           shadow_prices = {}
           for name in bottlenecks:
               sens = self.analyze_constraint(name)
               if sens.shadow_price:
                   shadow_prices[name] = abs(sens.shadow_price)

           # Normalize to relative importance
           total = sum(shadow_prices.values())
           if total == 0:
               return {}

           return {
               name: price / total
               for name, price in shadow_prices.items()
           }

       def generate_pareto_chart_data(self) -> List[Tuple[str, float, float]]:
           """
           Generate data for Pareto chart of constraint importance.

           Returns:
               List of (name, importance, cumulative_importance) tuples
           """
           importance = self.analyze_relative_importance()

           # Sort by importance
           sorted_items = sorted(
               importance.items(),
               key=lambda x: x[1],
               reverse=True
           )

           # Calculate cumulative
           cumulative = 0.0
           result = []
           for name, value in sorted_items:
               cumulative += value
               result.append((name, value, cumulative))

           return result

**Usage:**

.. code-block:: python

   analyzer = LXExtendedSensitivityAnalyzer(model, solution)

   # Use custom methods
   importance = analyzer.analyze_relative_importance()
   print("Constraint Importance:")
   for name, score in importance.items():
       print(f"  {name}: {score:.1%}")

   # Generate Pareto data
   pareto_data = analyzer.generate_pareto_chart_data()
   # Plot with matplotlib, etc.

2. Extending Scenario Analyzer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add scenario generation and comparison features.

**Example: Automated Scenario Generation**

.. code-block:: python

   from lumix.analysis import LXScenario, LXScenarioAnalyzer
   from typing import List

   class LXAutomatedScenarioAnalyzer(LXScenarioAnalyzer[TModel]):
       """Scenario analyzer with automatic scenario generation."""

       def generate_parameter_sweep(
           self,
           constraint_name: str,
           multipliers: List[float],
           prefix: str = "sweep"
       ) -> None:
           """
           Generate scenarios sweeping a parameter across multiple values.

           Args:
               constraint_name: Constraint to vary
               multipliers: List of multipliers to apply
               prefix: Prefix for scenario names
           """
           for mult in multipliers:
               scenario = (
                   LXScenario(f"{prefix}_{mult:.2f}")
                   .modify_constraint_rhs(constraint_name, multiply=mult)
                   .describe(f"{constraint_name} × {mult:.2f}")
               )
               self.add_scenario(scenario)

       def generate_stress_test_scenarios(self) -> None:
           """Generate worst/best case scenarios automatically."""
           # Worst case: reduce all capacity constraints by 30%
           worst = LXScenario("worst_case").describe("All constraints -30%")
           for constraint in self.base_model.constraints:
               if "capacity" in constraint.name.lower():
                   worst.modify_constraint_rhs(constraint.name, multiply=0.7)

           # Best case: increase all capacity constraints by 30%
           best = LXScenario("best_case").describe("All constraints +30%")
           for constraint in self.base_model.constraints:
               if "capacity" in constraint.name.lower():
                   best.modify_constraint_rhs(constraint.name, multiply=1.3)

           self.add_scenarios(worst, best)

       def generate_sensitivity_report_with_ranking(self) -> str:
           """Generate enhanced comparison report with rankings."""
           results = self.run_all_scenarios()

           # Rank scenarios
           ranked = sorted(
               results.items(),
               key=lambda x: x[1].objective_value,
               reverse=True  # Assume maximization
           )

           # Build report
           lines = ["Scenario Ranking Report", "=" * 80]

           for rank, (name, solution) in enumerate(ranked, 1):
               scenario_desc = self.scenarios.get(name, None)
               desc = scenario_desc.description if scenario_desc else "Baseline"

               lines.append(f"\n{rank}. {name}")
               lines.append(f"   Objective: ${solution.objective_value:,.2f}")
               lines.append(f"   Description: {desc}")

           return "\n".join(lines)

**Usage:**

.. code-block:: python

   analyzer = LXAutomatedScenarioAnalyzer(model, optimizer)

   # Automatically generate scenarios
   analyzer.generate_parameter_sweep(
       "capacity",
       multipliers=[0.5, 0.75, 1.0, 1.25, 1.5]
   )

   analyzer.generate_stress_test_scenarios()

   # Run and report
   results = analyzer.run_all_scenarios()
   print(analyzer.generate_sensitivity_report_with_ranking())

3. Extending What-If Analyzer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add new what-if operations.

**Example: Multi-Parameter What-If**

.. code-block:: python

   from lumix.analysis import LXWhatIfAnalyzer, LXWhatIfResult
   from typing import Dict
   from copy import deepcopy

   class LXMultiParameterWhatIfAnalyzer(LXWhatIfAnalyzer[TModel]):
       """What-if analyzer supporting multi-parameter changes."""

       def explore_combined_changes(
           self,
           changes: Dict[str, float]
       ) -> LXWhatIfResult[TModel]:
           """
           Explore impact of changing multiple parameters simultaneously.

           Args:
               changes: Dict mapping constraint names to delta values

           Returns:
               What-if result for combined changes

           Example:
               >>> changes = {
               ...     "capacity": 100,      # Increase by 100
               ...     "budget": -50000,     # Decrease by 50k
               ... }
               >>> result = analyzer.explore_combined_changes(changes)
           """
           baseline = self.get_baseline_solution()

           # Clone and apply all changes
           modified_model = deepcopy(self.model)
           for constraint_name, delta in changes.items():
               constraint = modified_model.get_constraint(constraint_name)
               if constraint:
                   constraint.rhs_value += delta

           # Solve
           new_solution = self.optimizer.solve(modified_model)

           # Build description
           desc_parts = [
               f"{name}: {delta:+.2f}"
               for name, delta in changes.items()
           ]
           description = "Combined changes: " + ", ".join(desc_parts)

           return LXWhatIfResult(
               description=description,
               original_objective=baseline.objective_value,
               new_objective=new_solution.objective_value,
               delta_objective=new_solution.objective_value - baseline.objective_value,
               delta_percentage=(
                   (new_solution.objective_value - baseline.objective_value)
                   / baseline.objective_value * 100
               ),
               original_solution=baseline,
               new_solution=new_solution
           )

       def find_optimal_relaxation(
           self,
           constraint_names: List[str],
           total_budget: float,
           cost_per_unit: Dict[str, float]
       ) -> Dict[str, float]:
           """
           Find optimal allocation of relaxation budget across constraints.

           Args:
               constraint_names: Constraints to consider
               total_budget: Total budget for relaxation
               cost_per_unit: Cost to relax each constraint by 1 unit

           Returns:
               Dict mapping constraint names to recommended relaxation amounts
           """
           # Get marginal value of each constraint
           marginal_values = {}
           for name in constraint_names:
               result = self.increase_constraint_rhs(name, by=1)
               marginal_values[name] = result.delta_objective

           # Calculate ROI for each constraint
           roi = {
               name: marginal_values[name] / cost_per_unit[name]
               for name in constraint_names
               if name in cost_per_unit
           }

           # Greedy allocation (simplified - could use optimization here!)
           allocation = {name: 0.0 for name in constraint_names}
           remaining_budget = total_budget

           while remaining_budget > 0:
               # Find best ROI
               best_name = max(roi.items(), key=lambda x: x[1])[0]
               best_cost = cost_per_unit[best_name]

               if best_cost > remaining_budget:
                   break

               allocation[best_name] += 1
               remaining_budget -= best_cost

           return allocation

**Usage:**

.. code-block:: python

   analyzer = LXMultiParameterWhatIfAnalyzer(model, optimizer)

   # Multi-parameter what-if
   result = analyzer.explore_combined_changes({
       "capacity": 100,
       "budget": -50000,
       "labor": 50
   })
   print(f"Combined impact: ${result.delta_objective:,.2f}")

   # Optimal relaxation allocation
   allocation = analyzer.find_optimal_relaxation(
       constraint_names=["capacity", "labor", "budget"],
       total_budget=100000,
       cost_per_unit={"capacity": 500, "labor": 1000, "budget": 1}
   )

   print("Optimal allocation:")
   for name, units in allocation.items():
       print(f"  {name}: {units:.0f} units")

Creating New Analyzers
-----------------------

Example: Robustness Analyzer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a completely new analyzer type.

.. code-block:: python

   from dataclasses import dataclass
   from typing import Generic, List, TypeVar
   from lumix.core import LXModel
   from lumix.solvers import LXOptimizer
   from lumix.solution import LXSolution

   TModel = TypeVar("TModel")

   @dataclass
   class LXRobustnessResult:
       """Results of robustness analysis."""
       objective_range: float
       worst_case_objective: float
       best_case_objective: float
       coefficient_of_variation: float
       is_robust: bool  # Based on threshold

   class LXRobustnessAnalyzer(Generic[TModel]):
       """
       Analyze solution robustness to parameter uncertainty.

       Tests how sensitive the solution is to variations in uncertain parameters.
       """

       def __init__(
           self,
           model: LXModel[TModel],
           optimizer: LXOptimizer[TModel],
           robustness_threshold: float = 0.1  # 10% variation is "robust"
       ):
           self.model = model
           self.optimizer = optimizer
           self.robustness_threshold = robustness_threshold

       def analyze_parameter_robustness(
           self,
           constraint_name: str,
           uncertainty_range: float = 0.2  # ±20%
       ) -> LXRobustnessResult:
           """
           Analyze robustness to uncertainty in a parameter.

           Args:
               constraint_name: Constraint to test
               uncertainty_range: Fraction of uncertainty (0.2 = ±20%)

           Returns:
               Robustness analysis results
           """
           from copy import deepcopy

           baseline_solution = self.optimizer.solve(self.model)
           baseline_obj = baseline_solution.objective_value

           # Test worst case (-uncertainty)
           worst_model = deepcopy(self.model)
           constraint = worst_model.get_constraint(constraint_name)
           constraint.rhs_value *= (1 - uncertainty_range)
           worst_solution = self.optimizer.solve(worst_model)

           # Test best case (+uncertainty)
           best_model = deepcopy(self.model)
           constraint = best_model.get_constraint(constraint_name)
           constraint.rhs_value *= (1 + uncertainty_range)
           best_solution = self.optimizer.solve(best_model)

           # Calculate metrics
           worst_obj = worst_solution.objective_value
           best_obj = best_solution.objective_value
           obj_range = best_obj - worst_obj
           mean_obj = (worst_obj + best_obj) / 2
           std_dev = obj_range / 4  # Approximate std dev
           cv = std_dev / mean_obj if mean_obj != 0 else float('inf')

           return LXRobustnessResult(
               objective_range=obj_range,
               worst_case_objective=worst_obj,
               best_case_objective=best_obj,
               coefficient_of_variation=cv,
               is_robust=(cv <= self.robustness_threshold)
           )

       def generate_robustness_report(
           self,
           constraint_names: List[str]
       ) -> str:
           """Generate comprehensive robustness report."""
           lines = ["Robustness Analysis Report", "=" * 80]

           for name in constraint_names:
               result = self.analyze_parameter_robustness(name)
               lines.append(f"\n{name}:")
               lines.append(f"  Objective Range: ${result.objective_range:,.2f}")
               lines.append(f"  Coefficient of Variation: {result.coefficient_of_variation:.2%}")
               lines.append(f"  Robust: {'Yes' if result.is_robust else 'No'}")

           return "\n".join(lines)

**Usage:**

.. code-block:: python

   # Create robustness analyzer
   analyzer = LXRobustnessAnalyzer(
       model=model,
       optimizer=optimizer,
       robustness_threshold=0.15  # 15% CV threshold
   )

   # Analyze single parameter
   result = analyzer.analyze_parameter_robustness("demand", uncertainty_range=0.25)

   if result.is_robust:
       print(f"Solution is robust to ±25% uncertainty in demand")
   else:
       print(f"Warning: High sensitivity (CV = {result.coefficient_of_variation:.1%})")

   # Full report
   print(analyzer.generate_robustness_report(["demand", "capacity", "cost"]))

Custom Result Objects
---------------------

Define specialized result structures for your analysis.

.. code-block:: python

   from dataclasses import dataclass, field
   from typing import Dict, List

   @dataclass
   class LXDecompositionResult:
       """Results of objective decomposition analysis."""
       total_objective: float
       component_contributions: Dict[str, float]
       component_percentages: Dict[str, float]
       top_contributors: List[Tuple[str, float]] = field(default_factory=list)

       def __post_init__(self):
           """Calculate derived fields."""
           # Sort contributors
           self.top_contributors = sorted(
               self.component_contributions.items(),
               key=lambda x: abs(x[1]),
               reverse=True
           )

   @dataclass
   class LXTradeOffResult:
       """Results of trade-off analysis between objectives."""
       objective1_name: str
       objective2_name: str
       pareto_frontier: List[Tuple[float, float]]
       knee_point: Tuple[float, float]  # Optimal balance point

Analysis Pipelines
------------------

Combine multiple analyzers for comprehensive analysis.

.. code-block:: python

   class LXComprehensiveAnalysisPipeline:
       """Pipeline combining multiple analysis types."""

       def __init__(self, model: LXModel, optimizer: LXOptimizer):
           self.model = model
           self.optimizer = optimizer

       def run_full_analysis(self) -> Dict[str, Any]:
           """Run complete analysis pipeline."""
           # 1. Solve model
           solution = self.optimizer.solve(self.model)

           # 2. Sensitivity analysis
           from lumix.analysis import LXSensitivityAnalyzer
           sens_analyzer = LXSensitivityAnalyzer(self.model, solution)
           bottlenecks = sens_analyzer.identify_bottlenecks()

           # 3. What-if analysis on bottlenecks
           from lumix.analysis import LXWhatIfAnalyzer
           whatif_analyzer = LXWhatIfAnalyzer(self.model, self.optimizer)
           whatif_results = {}
           for constraint in bottlenecks[:3]:  # Top 3
               result = whatif_analyzer.increase_constraint_rhs(constraint, by=100)
               whatif_results[constraint] = result

           # 4. Scenario analysis
           from lumix.analysis import LXScenario, LXScenarioAnalyzer
           scenario_analyzer = LXScenarioAnalyzer(self.model, self.optimizer)
           scenario_analyzer.add_scenario(
               LXScenario("optimistic")
               .modify_constraint_rhs(bottlenecks[0], multiply=1.5)
           )
           scenario_results = scenario_analyzer.run_all_scenarios()

           return {
               "solution": solution,
               "bottlenecks": bottlenecks,
               "sensitivity": sens_analyzer.generate_report(),
               "whatif": whatif_results,
               "scenarios": scenario_results
           }

**Usage:**

.. code-block:: python

   pipeline = LXComprehensiveAnalysisPipeline(model, optimizer)
   results = pipeline.run_full_analysis()

   print("=== Comprehensive Analysis ===\n")
   print("Bottlenecks:", results["bottlenecks"])
   print("\n", results["sensitivity"])

Best Practices
--------------

1. Follow Existing Patterns
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Maintain consistency with existing analyzers:

- Use dataclasses for result objects
- Support generic types with ``TypeVar``
- Return immutable results
- Use fluent API where appropriate

2. Document Thoroughly
~~~~~~~~~~~~~~~~~~~~~~

Provide comprehensive docstrings:

.. code-block:: python

   class LXCustomAnalyzer:
       """
       Short description.

       Longer explanation of what this analyzer does,
       when to use it, and how it works.

       Examples:
           Basic usage example::

               analyzer = LXCustomAnalyzer(model, optimizer)
               result = analyzer.analyze()
               print(result.summary())

       See Also:
           - :class:`LXSensitivityAnalyzer`: For sensitivity analysis
           - :class:`LXScenarioAnalyzer`: For scenario comparison
       """

3. Handle Edge Cases
~~~~~~~~~~~~~~~~~~~~

- Check for infeasible solutions
- Handle missing data gracefully
- Validate inputs

.. code-block:: python

   def analyze_constraint(self, name: str):
       constraint = self.model.get_constraint(name)
       if constraint is None:
           raise ValueError(f"Constraint '{name}' not found in model")

       if not self.solution.is_optimal():
           warnings.warn("Solution is not optimal, analysis may not be meaningful")

4. Add Tests
~~~~~~~~~~~~

Test your extensions:

.. code-block:: python

   def test_extended_sensitivity_analyzer():
       # Create test model
       model, solution = create_test_model()

       # Test extension
       analyzer = LXExtendedSensitivityAnalyzer(model, solution)
       importance = analyzer.analyze_relative_importance()

       # Verify
       assert sum(importance.values()) == pytest.approx(1.0)  # Normalized
       assert all(0 <= v <= 1 for v in importance.values())

Next Steps
----------

- :doc:`analysis-architecture` - Understand the architecture
- :doc:`design-decisions` - Learn design rationales
- :doc:`/api/analysis/index` - API reference
- :doc:`/user-guide/analysis/index` - User guide

Contributing
------------

If you've created a useful extension, consider contributing it back to LumiX:

1. Fork the repository
2. Add your extension to ``lumix/analysis/``
3. Write tests in ``tests/analysis/``
4. Update documentation
5. Submit a pull request

See the `Contributing Guide <https://github.com/lumix/lumix/blob/main/CONTRIBUTING.md>`_ for details.
