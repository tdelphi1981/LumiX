Analysis Architecture
=====================

Deep dive into the analysis module's architecture, design patterns, and implementation details.

Design Philosophy
-----------------

The analysis module implements three complementary approaches to post-optimization analysis:

1. **Sensitivity Analysis**: Leverages dual values from the solver (no re-solving)
2. **Scenario Analysis**: Systematic comparison through model cloning and modification
3. **What-If Analysis**: Interactive exploration with cached baseline

**Core Principles:**

- **Separation of Concerns**: Each analyzer handles one type of analysis
- **Solver Agnostic**: Works with any solver that provides solutions
- **Type Safety**: Generic types for data models
- **Performance**: Caching and lazy evaluation where possible

Architecture Overview
---------------------

.. mermaid::

   classDiagram
       class LXSensitivityAnalyzer {
           +model: LXModel
           +solution: LXSolution
           +analyze_constraint(name)
           +analyze_variable(name)
           +identify_bottlenecks()
           +generate_report()
       }

       class LXScenarioAnalyzer {
           +base_model: LXModel
           +optimizer: LXOptimizer
           +scenarios: Dict
           +results: Dict
           +add_scenario(scenario)
           +run_all_scenarios()
           +compare_scenarios()
           -_apply_scenario()
           -_clone_model()
       }

       class LXWhatIfAnalyzer {
           +model: LXModel
           +optimizer: LXOptimizer
           -_baseline_solution: LXSolution
           +increase_constraint_rhs()
           +decrease_constraint_rhs()
           +find_bottlenecks()
           -_solve_with_change()
       }

       class LXScenario {
           +name: str
           +modifications: List
           +description: str
           +modify_constraint_rhs()
           +modify_variable_bound()
       }

       class LXVariableSensitivity {
           +name: str
           +value: float
           +reduced_cost: float
           +allowable_increase: float
           +allowable_decrease: float
       }

       class LXConstraintSensitivity {
           +name: str
           +shadow_price: float
           +slack: float
           +allowable_increase: float
           +allowable_decrease: float
       }

       LXScenarioAnalyzer --> LXScenario
       LXScenarioAnalyzer --> LXModel
       LXSensitivityAnalyzer --> LXVariableSensitivity
       LXSensitivityAnalyzer --> LXConstraintSensitivity
       LXWhatIfAnalyzer --> LXModel

Module Structure
----------------

File Organization
~~~~~~~~~~~~~~~~~

.. code-block:: text

   lumix/analysis/
   ├── __init__.py          # Public API exports
   ├── scenario.py          # Scenario analysis implementation
   ├── sensitivity.py       # Sensitivity analysis implementation
   └── whatif.py            # What-if analysis implementation

**Design Rationale:**

- Each file contains one analyzer type and its related classes
- Clear separation makes code maintainable
- Easy to add new analysis types (e.g., ``robustness.py``)

Component Details
-----------------

1. Sensitivity Analyzer
~~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Analyze solution sensitivity without re-solving.

**Key Design:**

- Takes a **solved** ``LXSolution`` as input
- Extracts dual values (shadow prices, reduced costs)
- No model modification
- Zero solve time (instant analysis)

**Implementation:**

.. code-block:: python

   @dataclass
   class LXConstraintSensitivity:
       """Immutable result object."""
       name: str
       shadow_price: Optional[float] = None
       slack: Optional[float] = None
       is_binding: bool = False

   class LXSensitivityAnalyzer(Generic[TModel]):
       def __init__(self, model: LXModel[TModel], solution: LXSolution[TModel]):
           self.model = model
           self.solution = solution

       def analyze_constraint(self, name: str) -> LXConstraintSensitivity:
           """Extract sensitivity info from solution."""
           # Get shadow price from solution
           shadow_price = self.solution.get_dual_value(name)
           slack = self.solution.get_slack(name)

           return LXConstraintSensitivity(
               name=name,
               shadow_price=shadow_price,
               slack=slack,
               is_binding=(abs(slack) < 1e-6) if slack is not None else False
           )

**Data Flow:**

.. mermaid::

   sequenceDiagram
       participant User
       participant Analyzer
       participant Solution

       User->>Analyzer: analyze_constraint("capacity")
       Analyzer->>Solution: get_dual_value("capacity")
       Solution-->>Analyzer: shadow_price = 50.0
       Analyzer->>Solution: get_slack("capacity")
       Solution-->>Analyzer: slack = 0.0
       Analyzer-->>User: LXConstraintSensitivity(shadow_price=50, slack=0)

**Performance:**

- **Time complexity**: O(1) per constraint (dictionary lookup)
- **Space complexity**: O(1) (no additional storage)
- **Bottleneck identification**: O(N) where N = number of constraints

2. Scenario Analyzer
~~~~~~~~~~~~~~~~~~~~

**Purpose**: Systematic comparison of multiple parameter configurations.

**Key Design:**

- **Model cloning**: Deep copy to preserve original
- **Modification pipeline**: Apply changes to cloned model
- **Batch solving**: Run all scenarios sequentially
- **Result caching**: Store solutions for comparison

**Implementation:**

.. code-block:: python

   class LXScenarioAnalyzer(Generic[TModel]):
       def __init__(
           self,
           base_model: LXModel[TModel],
           optimizer: LXOptimizer[TModel],
           include_baseline: bool = True
       ):
           self.base_model = base_model
           self.optimizer = optimizer
           self.scenarios: Dict[str, LXScenario[TModel]] = {}
           self.results: Dict[str, LXSolution[TModel]] = {}

       def run_scenario(self, scenario_name: str) -> LXSolution[TModel]:
           """Run single scenario."""
           scenario = self.scenarios[scenario_name]

           # 1. Clone model (preserve original)
           modified_model = self._clone_model(self.base_model)

           # 2. Apply modifications
           modified_model = self._apply_scenario(scenario)

           # 3. Solve
           solution = self.optimizer.solve(modified_model)

           # 4. Cache result
           self.results[scenario_name] = solution

           return solution

       def _clone_model(self, model: LXModel[TModel]) -> LXModel[TModel]:
           """Deep copy model."""
           return deepcopy(model)

       def _apply_scenario(self, scenario: LXScenario[TModel]) -> LXModel[TModel]:
           """Apply modifications to model."""
           for mod in scenario.modifications:
               if mod.target_type == "constraint":
                   self._apply_constraint_modification(modified_model, mod)
               elif mod.target_type == "variable":
                   self._apply_variable_modification(modified_model, mod)

           return modified_model

**Data Flow:**

.. mermaid::

   sequenceDiagram
       participant User
       participant Analyzer
       participant Model
       participant Optimizer

       User->>Analyzer: add_scenario(high_capacity)
       User->>Analyzer: run_all_scenarios()

       loop For each scenario
           Analyzer->>Analyzer: _clone_model()
           Analyzer->>Analyzer: _apply_scenario()
           Analyzer->>Optimizer: solve(modified_model)
           Optimizer-->>Analyzer: solution
           Analyzer->>Analyzer: cache result
       end

       Analyzer-->>User: results dict

**Performance:**

- **Time complexity**: O(S × T) where S = scenarios, T = solve time
- **Space complexity**: O(S × M) where M = model size (due to cloning)
- **Optimization**: Could use copy-on-write for large models

**Design Trade-offs:**

- **Pro**: Simple, safe (no side effects on original model)
- **Con**: Memory-intensive for large models
- **Alternative**: Modification history and rollback (more complex)

3. What-If Analyzer
~~~~~~~~~~~~~~~~~~~

**Purpose**: Interactive single-parameter exploration.

**Key Design:**

- **Baseline caching**: Solve baseline once, reuse
- **Single modification**: One change at a time
- **Immediate results**: Fast turnaround for stakeholders
- **Automatic bottleneck finding**: Identify high-impact parameters

**Implementation:**

.. code-block:: python

   class LXWhatIfAnalyzer(Generic[TModel]):
       def __init__(
           self,
           model: LXModel[TModel],
           optimizer: LXOptimizer[TModel]
       ):
           self.model = model
           self.optimizer = optimizer
           self._baseline_solution: Optional[LXSolution[TModel]] = None

       def get_baseline_solution(self) -> LXSolution[TModel]:
           """Get or create cached baseline."""
           if self._baseline_solution is None:
               self._baseline_solution = self.optimizer.solve(self.model)
           return self._baseline_solution

       def increase_constraint_rhs(
           self,
           constraint_name: str,
           by: float
       ) -> LXWhatIfResult[TModel]:
           """Increase RHS and quantify impact."""
           # Get baseline
           baseline = self.get_baseline_solution()

           # Clone and modify
           modified_model = deepcopy(self.model)
           constraint = modified_model.get_constraint(constraint_name)
           original_rhs = constraint.rhs_value
           constraint.rhs_value += by

           # Solve
           new_solution = self.optimizer.solve(modified_model)

           # Calculate impact
           return LXWhatIfResult(
               description=f"Increase {constraint_name} RHS by {by}",
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

**Data Flow:**

.. mermaid::

   sequenceDiagram
       participant User
       participant Analyzer
       participant Model
       participant Optimizer

       User->>Analyzer: increase_constraint_rhs("capacity", 100)

       alt Baseline cached
           Analyzer->>Analyzer: Use cached baseline
       else No cache
           Analyzer->>Optimizer: solve(model)
           Optimizer-->>Analyzer: baseline_solution
           Analyzer->>Analyzer: Cache baseline
       end

       Analyzer->>Analyzer: Clone model
       Analyzer->>Analyzer: Modify constraint
       Analyzer->>Optimizer: solve(modified_model)
       Optimizer-->>Analyzer: new_solution

       Analyzer->>Analyzer: Calculate delta
       Analyzer-->>User: LXWhatIfResult

**Performance:**

- **First call**: 2 solves (baseline + modified)
- **Subsequent calls**: 1 solve each (cached baseline)
- **Memory**: 1 cached solution + 1 modified model
- **Optimization**: Could use warm starts if solver supports

Type System
-----------

Generic Type Parameters
~~~~~~~~~~~~~~~~~~~~~~~

All analyzers use generics for type safety:

.. code-block:: python

   TModel = TypeVar("TModel")  # User's data model type

   class LXSensitivityAnalyzer(Generic[TModel]):
       def __init__(
           self,
           model: LXModel[TModel],
           solution: LXSolution[TModel]
       ):
           ...

   class LXScenarioAnalyzer(Generic[TModel]):
       def __init__(
           self,
           base_model: LXModel[TModel],
           optimizer: LXOptimizer[TModel]
       ):
           ...

**Benefits:**

- IDE autocomplete knows the model type
- Type checkers catch mismatched types
- Self-documenting code

Result Objects
~~~~~~~~~~~~~~

Immutable dataclasses for results:

.. code-block:: python

   @dataclass
   class LXConstraintSensitivity:
       """Immutable sensitivity result."""
       name: str
       shadow_price: Optional[float] = None
       slack: Optional[float] = None
       is_binding: bool = False

   @dataclass
   class LXWhatIfResult(Generic[TModel]):
       """Immutable what-if result."""
       description: str
       original_objective: float
       new_objective: float
       delta_objective: float
       original_solution: LXSolution[TModel]
       new_solution: LXSolution[TModel]

**Design Rationale:**

- **Immutability**: Results don't change after creation
- **Dataclass**: Auto-generated ``__init__``, ``__repr__``
- **Type hints**: Full type safety

Extension Points
----------------

Custom Sensitivity Metrics
~~~~~~~~~~~~~~~~~~~~~~~~~~

Extend ``LXSensitivityAnalyzer`` for custom metrics:

.. code-block:: python

   class LXAdvancedSensitivityAnalyzer(LXSensitivityAnalyzer[TModel]):
       """Extended sensitivity with custom metrics."""

       def analyze_relative_importance(self) -> Dict[str, float]:
           """Calculate relative importance of constraints."""
           bottlenecks = self.identify_bottlenecks()
           shadow_prices = [
               self.analyze_constraint(name).shadow_price
               for name in bottlenecks
           ]

           total = sum(abs(sp) for sp in shadow_prices if sp)
           return {
               name: abs(sp) / total
               for name, sp in zip(bottlenecks, shadow_prices)
               if sp and total > 0
           }

Custom Scenario Types
~~~~~~~~~~~~~~~~~~~~~

Create specialized scenarios:

.. code-block:: python

   class LXSeasonalScenario(LXScenario[TModel]):
       """Scenario for seasonal variations."""

       def __init__(self, name: str, season: str):
           super().__init__(name)
           self.season = season
           self._apply_seasonal_patterns()

       def _apply_seasonal_patterns(self):
           """Apply season-specific modifications."""
           if self.season == "summer":
               self.modify_constraint_rhs("demand", multiply=1.3)
               self.modify_constraint_rhs("capacity", multiply=0.9)

Custom What-If Operations
~~~~~~~~~~~~~~~~~~~~~~~~~~

Add new what-if operations:

.. code-block:: python

   class LXExtendedWhatIfAnalyzer(LXWhatIfAnalyzer[TModel]):
       """Extended what-if with custom operations."""

       def explore_objective_coefficient(
           self,
           variable_name: str,
           coefficient: float
       ) -> LXWhatIfResult[TModel]:
           """What if we change an objective coefficient?"""
           baseline = self.get_baseline_solution()

           # Modify objective
           modified_model = deepcopy(self.model)
           # Implementation: modify objective expression
           # ...

           new_solution = self.optimizer.solve(modified_model)

           return LXWhatIfResult(...)

Testing Strategy
----------------

Unit Tests
~~~~~~~~~~

Test individual components:

.. code-block:: python

   def test_sensitivity_analyzer_identifies_bottlenecks():
       # Create test model and solution
       model, solution = create_test_model_and_solution()

       # Analyze
       analyzer = LXSensitivityAnalyzer(model, solution)
       bottlenecks = analyzer.identify_bottlenecks()

       # Verify
       assert "capacity" in bottlenecks
       assert "budget" in bottlenecks

Integration Tests
~~~~~~~~~~~~~~~~~

Test end-to-end workflows:

.. code-block:: python

   def test_scenario_analysis_workflow():
       # Build model
       model = create_production_model()

       # Create scenarios
       analyzer = LXScenarioAnalyzer(model, optimizer)
       analyzer.add_scenario(high_capacity_scenario)
       analyzer.add_scenario(low_capacity_scenario)

       # Run
       results = analyzer.run_all_scenarios()

       # Verify
       assert len(results) == 3  # 2 scenarios + baseline
       assert results["high_capacity"].objective_value > results["baseline"].objective_value

Performance Tests
~~~~~~~~~~~~~~~~~

Test caching and efficiency:

.. code-block:: python

   def test_whatif_analyzer_caches_baseline():
       analyzer = LXWhatIfAnalyzer(model, optimizer)

       # First call should solve baseline
       with timer() as t1:
           result1 = analyzer.increase_constraint_rhs("capacity", by=100)

       # Second call should reuse cached baseline
       with timer() as t2:
           result2 = analyzer.increase_constraint_rhs("capacity", by=200)

       # Second call should be faster
       assert t2.elapsed < t1.elapsed * 0.6  # At least 40% faster

Performance Considerations
--------------------------

Sensitivity Analysis
~~~~~~~~~~~~~~~~~~~~

**Time Complexity:**

- ``analyze_constraint()``: O(1)
- ``analyze_variable()``: O(1)
- ``identify_bottlenecks()``: O(N) where N = number of constraints
- ``generate_report()``: O(N + M) where M = number of variables

**Optimization:**

- All operations are lookups (no re-solving)
- Bottleneck analysis could be cached

Scenario Analysis
~~~~~~~~~~~~~~~~~

**Time Complexity:**

- ``add_scenario()``: O(1)
- ``run_scenario()``: O(T) where T = solve time
- ``run_all_scenarios()``: O(S × T) where S = number of scenarios

**Memory Complexity:**

- Model cloning: O(M) per scenario
- Solution storage: O(V) per scenario where V = number of variables

**Optimization:**

- **Parallel solving**: Run scenarios in parallel (future)
- **Incremental changes**: Avoid full model clone (complex)
- **Solution compression**: Store only variable values, not full solution

What-If Analysis
~~~~~~~~~~~~~~~~

**Time Complexity:**

- First call: O(2T) (baseline + modified)
- Subsequent calls: O(T) (cached baseline)

**Memory Complexity:**

- Cached baseline: O(V)
- Modified model: O(M)

**Optimization:**

- Warm starts if solver supports
- Partial model updates instead of full clone

Next Steps
----------

- :doc:`extending-analysis` - How to add custom analysis types
- :doc:`design-decisions` - Why things work this way
- :doc:`/api/analysis/index` - Full API reference
- :doc:`/user-guide/analysis/index` - User guide
