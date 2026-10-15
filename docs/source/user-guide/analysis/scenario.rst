Scenario Analysis
=================

Scenario analysis enables systematic comparison of multiple what-if scenarios to understand how
different business conditions or assumptions affect optimal decisions.

Overview
--------

Scenario analysis answers questions like:

- How do optimistic vs. pessimistic forecasts affect our plan?
- What if we have 20% more capacity?
- How would a budget cut impact operations?
- Which strategic option performs best?

The :class:`~lumix.analysis.scenario.LXScenarioAnalyzer` allows you to:

- Define multiple scenarios with different parameter combinations
- Run all scenarios in parallel
- Compare results side-by-side
- Identify the best scenario for your objectives

Key Concepts
------------

Scenarios
~~~~~~~~~

A **scenario** represents a set of modifications to your base model that reflect a particular
business condition or assumption.

**Components:**

- **Name**: Unique identifier for the scenario
- **Description**: Human-readable explanation
- **Modifications**: List of parameter changes to apply

**Example Scenarios:**

- "High Demand": 30% increase in demand constraints
- "Cost Reduction": 15% reduction in operating costs
- "Capacity Expansion": Additional warehouse space available
- "Supply Chain Disruption": Reduced supplier availability

Modifications
~~~~~~~~~~~~~

A **modification** specifies how to change a model parameter.

**Types:**

- **Constraint RHS**: Set, add, or multiply right-hand side values
- **Variable Bounds**: Modify lower or upper bounds
- **Objective Coefficients**: Not supported yet. A modification with any other target or
  modification type raises ``ValueError`` when the scenario is applied.

**Operations:**

- ``set_value``: Replace current value
- ``add``: Add to current value
- ``multiply``: Multiply current value by factor

``add`` and ``multiply`` work both on a scalar right-hand side (``.rhs(1000)``) and on a
per-row right-hand side (``.rhs(lambda row: row.capacity)``), where they apply to every row.
See `Per-Row Right-Hand Sides`_.

Scenario Comparison
~~~~~~~~~~~~~~~~~~~

After running scenarios, you can:

- Compare objective values across scenarios
- Calculate percentage differences from baseline
- Identify best and worst cases
- Generate comparison reports

Basic Usage
-----------

Creating Scenarios
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.analysis import LXScenario

   # Define a scenario
   high_capacity = (
       LXScenario("high_capacity")
       .modify_constraint_rhs("capacity", multiply=1.5)
       .describe("50% capacity increase")
   )

   # Multiple modifications
   optimistic = (
       LXScenario("optimistic")
       .modify_constraint_rhs("capacity", multiply=1.3)
       .modify_constraint_rhs("budget", add=50000)
       .modify_variable_bound("production", lower=100)
       .describe("Optimistic market conditions")
   )

Creating the Analyzer
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.analysis import LXScenarioAnalyzer

   # Create analyzer with baseline
   analyzer = LXScenarioAnalyzer(
       base_model=model,
       optimizer=optimizer,
       include_baseline=True  # Include unmodified model as "baseline"
   )

The analyzer never changes ``model``. Each scenario runs on a copy made with
``copy.deepcopy``: the copy has its own families and constraints, but shares every data
instance and every lambda with ``model`` (see :doc:`/user-guide/utils/model-copying`).
Instead of a model you can pass a ``model_factory``; see `Building Models with a Factory`_.

Adding Scenarios
~~~~~~~~~~~~~~~~

.. code-block:: python

   # Add single scenario
   analyzer.add_scenario(high_capacity)

   # Add multiple scenarios
   analyzer.add_scenarios(optimistic, pessimistic, conservative)

   # Or use fluent API
   analyzer = (
       LXScenarioAnalyzer(model, optimizer)
       .add_scenario(high_capacity)
       .add_scenario(low_capacity)
       .add_scenario(normal_capacity)
   )

Running Scenarios
~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Run all scenarios
   results = analyzer.run_all_scenarios()

   # Access individual results
   high_cap_solution = results["high_capacity"]
   print(f"High capacity objective: ${high_cap_solution.objective_value:,.2f}")

   # Run single scenario
   solution = analyzer.run_scenario("optimistic")

Comparing Results
~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Generate comparison report
   report = analyzer.compare_scenarios()
   print(report)

   # Example output:
   # Scenario Comparison
   # ================================================================================
   # Baseline Objective: 125,000.00
   #
   # Scenario                       Objective          Status    vs Baseline
   # --------------------------------------------------------------------------------
   # high_capacity                 156,250.00         OPTIMAL        +25.00%
   # optimistic                    145,000.00         OPTIMAL        +16.00%
   # baseline                      125,000.00         OPTIMAL             -
   # conservative                  110,000.00         OPTIMAL        -12.00%
   # pessimistic                    95,000.00         OPTIMAL        -24.00%

Finding Best Scenario
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Follows the base model's objective sense (largest objective when it
   # maximizes, smallest when it minimizes)
   best = analyzer.get_best_scenario()
   print(f"Best scenario: {best}")

   # Force a direction: largest / smallest objective
   largest = analyzer.get_best_scenario(maximize=True)
   smallest = analyzer.get_best_scenario(maximize=False)

Only feasible results are considered; if no result is feasible,
``get_best_scenario`` returns ``None``.

.. versionchanged:: 0.3.0
   ``maximize`` defaults to ``None`` and follows the base model's objective sense
   (it used to always maximize), and infeasible results are skipped.

Modification Types
------------------

Constraint RHS Modifications
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   scenario = LXScenario("capacity_changes")

   # Set to specific value
   scenario.modify_constraint_rhs("max_capacity", set_value=1500.0)

   # Add to current value
   scenario.modify_constraint_rhs("max_capacity", add=200.0)

   # Multiply by factor
   scenario.modify_constraint_rhs("max_capacity", multiply=1.25)

Several modifications of the same constraint are applied in the order they were added.
``multiply=m`` followed by ``add=a`` turns a right-hand side ``b`` into ``b * m + a``.

Per-Row Right-Hand Sides
~~~~~~~~~~~~~~~~~~~~~~~~

.. versionchanged:: 0.3.0
   ``add`` and ``multiply`` apply row by row to constraints whose right-hand side is a
   function; they used to be silently ignored.

For an indexed constraint family whose right-hand side comes from the data, the
modifications act on every row:

.. code-block:: python

   # One row per machine: production on m <= m.hours
   model.add_constraint(
       LXConstraint[Machine]("capacity")
       .expression(hours_used)
       .le()
       .rhs(lambda m: m.hours)
       .from_data(machines)
       .indexed_by(lambda m: m.id)
   )

   # Every row: m.hours * 1.2
   LXScenario("overtime").modify_constraint_rhs("capacity", multiply=1.2)

   # Every row: m.hours - 8
   LXScenario("maintenance").modify_constraint_rhs("capacity", add=-8)

   # Every row: 40 (the same value for all rows)
   LXScenario("flat").modify_constraint_rhs("capacity", set_value=40)

   # Composed in order: m.hours * 0.5 - 1
   (LXScenario("half_minus_one")
    .modify_constraint_rhs("capacity", multiply=0.5)
    .modify_constraint_rhs("capacity", add=-1))

If a constraint has both a scalar right-hand side and a right-hand-side function, the
scalar wins, as it does when the model is solved.
Variable Bound Modifications
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   scenario = LXScenario("bound_changes")

   # Set lower bound
   scenario.modify_variable_bound("production", lower=100.0)

   # Set upper bound
   scenario.modify_variable_bound("production", upper=500.0)

   # Set both
   scenario.modify_variable_bound("inventory", lower=50.0, upper=200.0)

Custom Modifications
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.analysis import LXScenarioModification

   # Create custom modification
   mod = LXScenarioModification(
       target_type="constraint",
       target_name="demand",
       modification_type="rhs_multiply",
       value=1.2,
       description="20% demand increase"
   )

   scenario = LXScenario("custom").add_custom_modification(mod)

Supported combinations:

.. list-table::
   :header-rows: 1
   :widths: 25 40

   * - ``target_type``
     - ``modification_type``
   * - ``"constraint"``
     - ``"rhs_set"``, ``"rhs_add"``, ``"rhs_multiply"``
   * - ``"variable"``
     - ``"bound_lower"``, ``"bound_upper"``

.. versionchanged:: 0.3.0
   Any other target type (for example ``"objective"``) or modification type (for
   example ``"coeff_multiply"``) raises ``ValueError`` when the scenario runs; such
   modifications used to be ignored without notice.

Building Models with a Factory
------------------------------

.. versionadded:: 0.3.0

Instead of a base model you can give the analyzer a function that builds the model:

.. code-block:: python

   def build_model():
       products = load_products()
       return build_production_model(products)   # a new LXModel on every call

   analyzer = LXScenarioAnalyzer(optimizer=optimizer, model_factory=build_model)
   analyzer.add_scenario(LXScenario("high_capacity").modify_constraint_rhs("capacity", multiply=1.5))
   results = analyzer.run_all_scenarios()

How it works:

- The factory is called once for the base model (``analyzer.base_model``) and once for
  every scenario (and every ``sensitivity_to_parameter`` value). Nothing is copied.
- It must return a **new** model on every call. Returning a model it already returned
  raises ``ValueError``.
- Pass exactly one of ``base_model`` and ``model_factory`` (``ValueError`` otherwise);
  a missing ``optimizer`` raises ``TypeError``.
- A model built for a scenario is freed once its run is over (the analyzer keeps only
  the base model).

A factory is the recommended way to analyze an ORM-backed model whose session may be
closed before the analysis runs: open a fresh session inside the factory.

.. code-block:: python

   from sqlalchemy.orm import Session, selectinload

   def build_model():
       with Session(engine) as session:     # fresh session, closed after loading
           products = (session.query(Product)
                       .options(selectinload(Product.category))   # what lambdas read
                       .all())
       production = (
           LXVariable[Product, float]("production")
           .continuous().bounds(lower=0)
           .indexed_by(lambda p: p.id)
           .from_data(products)
       )
       model = LXModel("plan").add_variable(production)
       # ... constraints and objective; lambdas may read p.category.factor,
       # which was loaded before the session closed
       return model

   analyzer = LXScenarioAnalyzer(optimizer=optimizer, model_factory=build_model)
   analyzer.add_scenario(LXScenario("half").modify_constraint_rhs("capacity", set_value=500))
   results = analyzer.run_all_scenarios()

.. important::

   Close the session inside the factory, after eager-loading every relationship your
   lambdas read (``selectinload`` / ``joinedload``). Loaded attributes stay readable on
   the instances after the session closes, and the connection goes back to the pool.
   A session left open per model holds one pooled connection each, so with SQLAlchemy's
   default pool (5 + 10 overflow) the 16th run would wait for a connection and fail.

Recording Results
-----------------

.. versionadded:: 0.3.0

Pass ``result_store=`` to write every solve (the baseline, each scenario and every
``sensitivity_to_parameter`` run) to the database:

.. code-block:: python

   from lumix import LXResultStore

   store = LXResultStore(session, analysis="q3-capacity")
   analyzer = LXScenarioAnalyzer(model, optimizer, result_store=store)

See :doc:`result-store`.

Practical Examples
------------------

Example 1: Demand Scenarios
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.analysis import LXScenario, LXScenarioAnalyzer

   # Create demand scenarios
   high_demand = (
       LXScenario("high_demand")
       .modify_constraint_rhs("demand", multiply=1.3)
       .describe("30% increase in demand")
   )

   normal_demand = (
       LXScenario("normal_demand")
       .modify_constraint_rhs("demand", multiply=1.0)
       .describe("Expected demand")
   )

   low_demand = (
       LXScenario("low_demand")
       .modify_constraint_rhs("demand", multiply=0.7)
       .describe("30% decrease in demand")
   )

   # Run analysis
   analyzer = (
       LXScenarioAnalyzer(model, optimizer)
       .add_scenarios(high_demand, normal_demand, low_demand)
   )

   results = analyzer.run_all_scenarios()

   # Compare
   print(analyzer.compare_scenarios())

   # Decision making (profit model: maximization)
   best = analyzer.get_best_scenario()                # follows the model's sense
   worst = analyzer.get_best_scenario(maximize=False)  # smallest feasible profit

   print(f"\nBest case ({best}):")
   print(f"  Objective: ${results[best].objective_value:,.2f}")

   print(f"\nWorst case ({worst}):")
   print(f"  Objective: ${results[worst].objective_value:,.2f}")

   # Range analysis
   obj_range = (
       results[best].objective_value - results[worst].objective_value
   )
   print(f"\nObjective range: ${obj_range:,.2f}")

Example 2: Investment Options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Compare different investment strategies
   warehouse_expansion = (
       LXScenario("warehouse_expansion")
       .modify_constraint_rhs("storage_capacity", multiply=2.0)
       .modify_constraint_rhs("budget", add=-100000)  # Cost
       .describe("Double warehouse capacity ($100k)")
   )

   fleet_expansion = (
       LXScenario("fleet_expansion")
       .modify_constraint_rhs("truck_capacity", multiply=1.5)
       .modify_constraint_rhs("budget", add=-75000)  # Cost
       .describe("50% more trucks ($75k)")
   )

   automation = (
       LXScenario("automation")
       .modify_constraint_rhs("labor_hours", multiply=0.6)  # 40% reduction
       .modify_constraint_rhs("budget", add=-150000)  # Cost
       .describe("Automation investment ($150k)")
   )

   # Run and compare
   analyzer = LXScenarioAnalyzer(model, optimizer)
   analyzer.add_scenarios(
       warehouse_expansion,
       fleet_expansion,
       automation
   )

   results = analyzer.run_all_scenarios(include_baseline=True)

   # Calculate ROI for each option
   baseline_obj = results["baseline"].objective_value

   print("Investment ROI Analysis:")
   print("-" * 60)

   investments = [
       ("warehouse_expansion", 100000),
       ("fleet_expansion", 75000),
       ("automation", 150000),
   ]

   for name, cost in investments:
       improvement = results[name].objective_value - baseline_obj
       roi = (improvement / cost) * 100 if cost > 0 else 0
       print(f"{name:25s}: ${improvement:10,.2f} ({roi:5.1f}% ROI)")

Example 3: Sensitivity to Multiple Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Test sensitivity to capacity at different levels
   capacity_multipliers = [0.5, 0.7, 0.9, 1.0, 1.1, 1.3, 1.5, 2.0]

   results = analyzer.sensitivity_to_parameter(
       parameter_name="capacity",
       values=capacity_multipliers,
       modification_type="rhs_multiply",
       target_type="constraint"
   )

   # Plot results
   print("Capacity Sensitivity:")
   print("-" * 60)
   print(f"{'Multiplier':<12} {'Objective':>15} {'Change':>15}")
   print("-" * 60)

   baseline = results[1.0].objective_value
   for multiplier in sorted(results.keys()):
       obj = results[multiplier].objective_value
       change = obj - baseline
       print(f"{multiplier:<12.1f} ${obj:>14,.2f} ${change:>14,.2f}")

Example 4: Stress Testing
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Create worst-case scenario
   worst_case = (
       LXScenario("worst_case")
       .modify_constraint_rhs("capacity", multiply=0.7)  # 30% reduction
       .modify_constraint_rhs("budget", multiply=0.8)     # 20% cut
       .modify_constraint_rhs("demand", multiply=1.3)     # 30% increase
       .describe("Worst case: reduced capacity, tight budget, high demand")
   )

   # Create best-case scenario
   best_case = (
       LXScenario("best_case")
       .modify_constraint_rhs("capacity", multiply=1.3)  # 30% increase
       .modify_constraint_rhs("budget", multiply=1.2)     # 20% more
       .modify_constraint_rhs("demand", multiply=0.9)     # 10% decrease
       .describe("Best case: excess capacity, flexible budget, low demand")
   )

   # Run stress test
   analyzer = (
       LXScenarioAnalyzer(model, optimizer)
       .add_scenarios(worst_case, best_case)
   )

   results = analyzer.run_all_scenarios(include_baseline=True)

   # Analyze robustness
   baseline_obj = results["baseline"].objective_value
   worst_obj = results["worst_case"].objective_value
   best_obj = results["best_case"].objective_value

   downside_risk = (baseline_obj - worst_obj) / baseline_obj * 100
   upside_potential = (best_obj - baseline_obj) / baseline_obj * 100

   print("Stress Test Results:")
   print(f"  Baseline:           ${baseline_obj:,.2f}")
   print(f"  Worst Case:         ${worst_obj:,.2f} ({-downside_risk:.1f}%)")
   print(f"  Best Case:          ${best_obj:,.2f} (+{upside_potential:.1f}%)")
   print(f"  Downside Risk:      {downside_risk:.1f}%")
   print(f"  Upside Potential:   {upside_potential:.1f}%")

Advanced Features
-----------------

Conditional Modifications
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Use lambdas for dynamic modifications
   def get_seasonal_multiplier(season):
       return {"winter": 0.7, "spring": 1.0, "summer": 1.3, "fall": 0.9}[season]

   for season in ["winter", "spring", "summer", "fall"]:
       scenario = (
           LXScenario(f"{season}_demand")
           .modify_constraint_rhs(
               "demand",
               multiply=get_seasonal_multiplier(season)
           )
           .describe(f"{season.capitalize()} seasonal pattern")
       )
       analyzer.add_scenario(scenario)

Scenario Filtering
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Compare only specific scenarios
   report = analyzer.compare_scenarios(
       scenario_names=["high_capacity", "low_capacity"],
       include_baseline=True,
       sort_by_objective=True
   )

Programmatic Scenario Generation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Generate scenarios programmatically
   for pct in range(-30, 31, 10):  # -30% to +30% in 10% steps
       multiplier = 1.0 + (pct / 100.0)
       scenario = (
           LXScenario(f"capacity_{pct:+d}pct")
           .modify_constraint_rhs("capacity", multiply=multiplier)
           .describe(f"Capacity {pct:+d}%")
       )
       analyzer.add_scenario(scenario)

   # Run all programmatically generated scenarios
   results = analyzer.run_all_scenarios()

Best Practices
--------------

1. **Always Include Baseline**

   Compare scenarios against the unmodified model.

   .. code-block:: python

      analyzer = LXScenarioAnalyzer(model, optimizer, include_baseline=True)

2. **Use Descriptive Names and Descriptions**

   Make reports readable and understandable.

   .. code-block:: python

      scenario = (
          LXScenario("q4_holiday_surge")  # Clear name
          .modify_constraint_rhs("demand", multiply=1.5)
          .describe("Q4 holiday season: 50% demand increase")  # Explanation
      )

3. **Test Extreme Cases**

   Include both optimistic and pessimistic scenarios.

   .. code-block:: python

      # Not just likely scenarios
      scenarios = [
          create_scenario("best_case", 1.5),
          create_scenario("likely", 1.1),
          create_scenario("worst_case", 0.6),
       ]

4. **Validate Scenario Feasibility**

   Check that scenarios produce feasible solutions.

   .. code-block:: python

      results = analyzer.run_all_scenarios()

      for name, solution in results.items():
          if not solution.is_optimal():
              print(f"Warning: {name} is infeasible or non-optimal")

5. **Combine with Sensitivity Analysis**

   Use sensitivity to guide scenario design.

   .. code-block:: python

      from lumix.analysis import LXSensitivityAnalyzer

      # Identify sensitive parameters
      sens = LXSensitivityAnalyzer(model, baseline_solution)
      bottlenecks = sens.identify_bottlenecks()

      # Bottlenecks are constraint rows ("capacity[3]" for an indexed family);
      # scenarios modify whole constraint families, so map rows to families
      families = dict.fromkeys(name.split("[", 1)[0] for name in bottlenecks)

      # Create scenarios around bottlenecks
      for constraint in families:
          scenario = LXScenario(f"{constraint}_relaxed")
          scenario.modify_constraint_rhs(constraint, multiply=1.2)
          analyzer.add_scenario(scenario)

Performance Considerations
--------------------------

Scenario analysis solves the model multiple times, which can be time-consuming for large models.

**Optimization Tips:**

1. **Limit the number of scenarios** for large models
2. **Use warm starts** if your solver supports it
3. **Run scenarios in parallel** (future feature)
4. **Cache baseline solution** to avoid re-solving

.. code-block:: python

   # Efficient scenario analysis
   # 1. Solve baseline once
   baseline = optimizer.solve(model)

   # 2. Create analyzer with cached baseline
   analyzer = LXScenarioAnalyzer(model, optimizer, include_baseline=False)

   # 3. Use baseline for comparisons
   # (Store baseline separately)

Next Steps
----------

- :doc:`sensitivity` - Understand shadow prices and reduced costs
- :doc:`whatif` - Interactive exploration of changes
- :doc:`result-store` - Persist scenario results
- :doc:`/api/analysis/index` - Complete API reference
- :doc:`/development/analysis-architecture` - Architecture details
