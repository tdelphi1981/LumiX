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
           +analyze_constraint(row_name)
           +analyze_variable(instance_name)
           +analyze_constraint_family(name)
           +analyze_variable_family(name)
           +identify_bottlenecks()
           +generate_report()
       }

       class LXScenarioAnalyzer {
           +base_model: LXModel
           +optimizer: LXOptimizer
           +scenarios: Dict
           +results: Dict
           +result_store: LXResultStore
           +add_scenario(scenario)
           +run_all_scenarios()
           +compare_scenarios()
           +get_best_scenario(maximize)
           -_apply_scenario()
           -_clone_model()
       }

       class LXWhatIfAnalyzer {
           +model: LXModel
           +optimizer: LXOptimizer
           -_baseline_solution: LXSolution
           +result_store: LXResultStore
           +increase_constraint_rhs()
           +decrease_constraint_rhs()
           +find_bottlenecks()
           -_new_model()
       }

       class ModelSource {
           +base: LXModel
           +new() LXModel
       }

       class LXResultStore {
           +record(scenario, solution, model, modifications)
           +runs(analysis)
           +values(run_id, kind)
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
       LXScenarioAnalyzer --> ModelSource
       LXWhatIfAnalyzer --> ModelSource
       LXScenarioAnalyzer --> LXResultStore
       LXWhatIfAnalyzer --> LXResultStore

Module Structure
----------------

File Organization
~~~~~~~~~~~~~~~~~

.. code-block:: text

   lumix/analysis/
   ├── __init__.py          # Public API exports
   ├── scenario.py          # Scenario analysis implementation
   ├── sensitivity.py       # Sensitivity analysis implementation
   ├── whatif.py            # What-if analysis implementation
   ├── store.py             # LXResultStore / LXStoredRun (0.3.0)
   ├── _store_tables.py     # SQLAlchemy tables, imported lazily by store.py
   ├── _factory.py          # ModelSource: copy of a base model or model_factory()
   └── _rhs.py              # set_rhs / shift_rhs, shared by scenario and what-if

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

   def _constraint_rows(constraint) -> List[Tuple[Any, str]]:
       """(index key, row name) per row; the names solvers key duals by."""
       if constraint.index_func is None:
           return [(None, constraint.name)]
       return [(key, f"{constraint.name}[{key}]")
               for key in (constraint.index_func(i) for i in constraint.get_instances())]

   class LXSensitivityAnalyzer(Generic[TModel]):
       def __init__(self, model: LXModel[TModel], solution: LXSolution[TModel]):
           self.model = model
           self.solution = solution

       def analyze_constraint(self, constraint_name: str) -> LXConstraintSensitivity:
           """One row: a scalar constraint or "family[key]"."""
           family = self.model.get_constraint(constraint_name)
           if family is not None and family.index_func is not None:
               raise ValueError("... use analyze_constraint_family(...)")

           shadow_price = self.solution.get_shadow_price(constraint_name)
           is_binding = shadow_price is not None and abs(shadow_price) > 1e-6
           return LXConstraintSensitivity(
               name=constraint_name, shadow_price=shadow_price,
               is_binding=is_binding, is_active=is_binding)

       def analyze_constraint_family(self, constraint_name: str):
           """Every row, keyed by index key ({None: ...} for a scalar)."""
           family = self.model.get_constraint(constraint_name)
           return {key: self.analyze_constraint(row)
                   for key, row in _constraint_rows(family)}

.. versionchanged:: 0.3.0
   Sensitivity works per constraint row and per variable instance. Solvers key duals and
   reduced costs by row / instance name (``"capacity[3]"``, ``"production[widget]"``),
   and the analyzer now uses the same names. ``analyze_constraint`` /
   ``analyze_variable`` reject an indexed family name with ``ValueError``; the
   ``*_family`` methods return a dictionary keyed by index key.

**Data Flow:**

.. mermaid::

   sequenceDiagram
       participant User
       participant Analyzer
       participant Solution

       User->>Analyzer: analyze_constraint("capacity[3]")
       Analyzer->>Solution: get_shadow_price("capacity[3]")
       Solution-->>Analyzer: shadow_price = 50.0
       Analyzer-->>User: LXConstraintSensitivity(shadow_price=50, is_binding=True)

**Performance:**

- **Time complexity**: O(1) per constraint (dictionary lookup)
- **Space complexity**: O(1) (no additional storage)
- **Bottleneck identification**: O(N) where N = number of constraints

2. Scenario Analyzer
~~~~~~~~~~~~~~~~~~~~

**Purpose**: Systematic comparison of multiple parameter configurations.

**Key Design:**

- **Model source**: A copy of the base model per run, or a fresh ``model_factory()``
  build (see `Model Sources`_)
- **Modification pipeline**: Apply changes to that model; unknown target or
  modification types raise ``ValueError``
- **Batch solving**: Run all scenarios sequentially
- **Result caching**: Store solutions for comparison

**Implementation:**

.. code-block:: python

   class LXScenarioAnalyzer(Generic[TModel]):
       def __init__(self, base_model=None, optimizer=None, include_baseline=True,
                    *, model_factory=None, result_store=None):
           self._source = ModelSource(base_model, model_factory, optimizer,
                                      "LXScenarioAnalyzer")
           self.base_model = self._source.base
           self.optimizer = optimizer
           self.result_store = result_store
           self.scenarios: Dict[str, LXScenario[TModel]] = {}
           self.results: Dict[str, LXSolution[TModel]] = {}

       def run_scenario(self, scenario_name: str) -> LXSolution[TModel]:
           """Run single scenario."""
           scenario = self.scenarios[scenario_name]

           # 1. New model (copy or factory) with modifications applied
           modified_model = self._apply_scenario(scenario)

           # 2. Solve and cache
           solution = self.optimizer.solve(modified_model)
           self.results[scenario_name] = solution

           # 3. Record (no-op without a result store)
           self._record(scenario_name, solution, modified_model, scenario.modifications)
           return solution

       def _clone_model(self, model: LXModel[TModel]) -> LXModel[TModel]:
           """Independent model for one run (argument kept for subclasses)."""
           return self._source.new()

       def _apply_scenario(self, scenario: LXScenario[TModel]) -> LXModel[TModel]:
           """Apply modifications to a new model."""
           modified_model = self._clone_model(self.base_model)
           for mod in scenario.modifications:
               if mod.target_type == "constraint":
                   self._apply_constraint_modification(modified_model, mod)
               elif mod.target_type == "variable":
                   self._apply_variable_modification(modified_model, mod)
               else:
                   raise ValueError(f"unsupported target type '{mod.target_type}'")
           return modified_model

Constraint modifications go through the shared helpers in ``_rhs.py``:

.. code-block:: python

   def shift_rhs(constraint, *, add=0.0, multiply=1.0):
       """rhs := rhs * multiply + add, for a scalar RHS or row by row."""
       if constraint.rhs_value is not None:          # scalar wins, as when solving
           constraint.rhs_value = constraint.rhs_value * multiply + add
       elif constraint.rhs_func is not None:         # per-row RHS: wrap the function
           inner = constraint.rhs_func
           constraint.rhs_func = lambda row: inner(row) * multiply + add
       else:
           raise ValueError(...)

``set_rhs`` replaces the right-hand side (a number becomes the RHS of every row).
Because ``shift_rhs`` wraps the current function, several modifications of the same
constraint compose in order.

.. versionchanged:: 0.3.0
   ``rhs_add``/``rhs_multiply`` used to ignore per-row right-hand sides, and unknown
   modification or target types used to be skipped silently.

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
- **Space complexity**: O(S × M) where M = model structure size; data instances are
  shared between copies, not duplicated
- **Optimization**: Could use copy-on-write for large models

**Design Trade-offs:**

- **Pro**: Simple, safe (no side effects on original model)
- **Con**: Memory grows with the number of scenarios
- **Alternative**: Modification history and rollback (more complex)

``get_best_scenario(maximize=None)`` considers only feasible results (``None`` if there
are none) and, by default, follows the base model's objective sense.

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
       def __init__(self, model=None, optimizer=None, baseline_solution=None,
                    *, model_factory=None, result_store=None):
           self._source = ModelSource(model, model_factory, optimizer, "LXWhatIfAnalyzer")
           self.model = self._source.base
           self.optimizer = optimizer
           self.result_store = result_store
           self._baseline_solution: Optional[LXSolution[TModel]] = baseline_solution

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

           # New model (copy or factory build) and modify
           modified_model = self._new_model()
           constraint = modified_model.get_constraint(constraint_name)
           original_rhs = constraint.rhs_value   # None for a per-row RHS
           shift_rhs(constraint, add=by)         # scalar or row by row

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

``find_bottlenecks(test_amount, top_n)`` calls ``relax_constraint`` for every constraint
family and scores ``sign * delta_objective / test_amount``, with ``sign = -1`` for
minimization, so a positive score always means "relaxing helps". Unbounded relaxations
score ``inf``; other non-feasible relaxations are skipped with a ``UserWarning``; an
infeasible baseline raises ``ValueError``.

.. versionchanged:: 0.3.0
   Scores follow the objective sense (minimization used to rank backwards).

**Performance:**

- **First call**: 2 solves (baseline + modified)
- **Subsequent calls**: 1 solve each (cached baseline)
- **Memory**: 1 cached solution + 1 modified model
- **Optimization**: Could use warm starts if solver supports

Model Sources
-------------

.. versionadded:: 0.3.0

Both re-solving analyzers obtain their models from a small internal ``ModelSource``
(``lumix/analysis/_factory.py``):

.. code-block:: python

   class ModelSource:
       def __init__(self, model, factory, optimizer, owner):
           if optimizer is None:
               raise TypeError(f"{owner} needs an optimizer")
           if (model is None) == (factory is None):
               raise ValueError(f"{owner} needs exactly one of a model or model_factory")
           self._factory = factory
           self.base = model if model is not None else factory()

       def new(self):
           if self._factory is None:
               return deepcopy(self.base)
           model = self._factory()       # must be a model it has not returned before
           ...
           return model

- **Copy**: ``deepcopy`` copies the model structure (families, constraints,
  expressions, data lists) and shares every data instance and every callable with the
  base model. ORM-backed families are materialized once at copy time; nothing is
  detached. This keeps identity-based closures (``p is a``, ``weights[p]``) correct in
  copies. See :doc:`/user-guide/utils/model-copying`.
- **Factory**: called for the base model and once per run. The source keeps every model
  it returned (so ``id()`` comparisons stay valid) and raises ``ValueError`` if the
  factory returns a model a second time.

Result Store
------------

.. versionadded:: 0.3.0

Each analyzer calls ``self._record(name, solution, model, modifications)`` after every
solve; it is a no-op unless ``result_store`` was given. ``LXResultStore`` (``store.py``)
writes one ``lumix_runs`` row and its ``lumix_run_values`` rows per call. SQLAlchemy is
imported lazily from ``_store_tables.py``, so ``import lumix`` works without it. The
value rows reuse the sensitivity analyzer's row and instance enumeration, so stored keys
match ``LXSolution.variables``. See :doc:`/user-guide/analysis/result-store`.

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
           base_model: Optional[LXModel[TModel]] = None,
           optimizer: Optional[LXOptimizer[TModel]] = None,
           include_baseline: bool = True,
           *,
           model_factory: Optional[Callable[[], LXModel[TModel]]] = None,
           result_store: Optional[LXResultStore] = None,
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

           # Modify objective on a new model (copy or factory build)
           modified_model = self._new_model()
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

- ``analyze_constraint()``: O(1) after the row index is built (O(R) once, R = rows)
- ``analyze_variable()``: O(1) after the instance index is built
- ``identify_bottlenecks()``: O(R) where R = number of constraint rows
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

- Model copy: O(M) per scenario (structure only; data instances are shared)
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
