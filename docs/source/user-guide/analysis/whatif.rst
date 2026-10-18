What-If Analysis
================

What-if analysis enables interactive exploration of parameter changes with immediate feedback
on how they affect the optimal solution, perfect for answering stakeholder questions on-the-fly.

Overview
--------

What-if analysis answers questions like:

- What if we increase capacity by 100 units?
- How would reducing the budget by 20% affect profit?
- Which parameter changes would have the biggest impact?
- Where are the bottlenecks in our system?

The :class:`~lumix.analysis.whatif.LXWhatIfAnalyzer` provides:

- Quick exploration of single parameter changes
- Automatic impact calculation (delta objective)
- Bottleneck identification
- Interactive decision support

Key Concepts
------------

What-If Changes
~~~~~~~~~~~~~~~

A **what-if change** represents a hypothetical modification to explore:

**Change Types:**

- **Constraint RHS**: Increase, decrease, or set constraint bounds
- **Variable Bounds**: Modify variable lower/upper limits
- **Objective Coefficients**: Change profit/cost coefficients (future)

**Properties:**

- Original value (before change)
- New value (after change)
- Delta (amount of change)

For a constraint whose right-hand side is a per-row function, there is no single value,
so ``original_value``, ``new_value`` and ``delta`` are ``None``.

What-If Results
~~~~~~~~~~~~~~~

The :class:`~lumix.analysis.whatif.LXWhatIfResult` contains:

- **Original objective**: Baseline objective value
- **New objective**: Objective after the change
- **Delta objective**: Change in objective (new - original)
- **Delta percentage**: Percentage change
- **Solutions**: Both original and new solutions

.. versionchanged:: 0.3.0
   When the baseline or the changed model has no solution (infeasible, unbounded),
   ``delta_objective`` and ``delta_percentage`` are ``nan`` and ``sensitivity_range``
   reports ``nan`` for that point; an infeasible run used to count as a change to an
   objective of 0. Check ``result.new_solution.is_feasible()`` first.

.. versionchanged:: 0.3.2
   ``delta_percentage`` is ``(new - baseline) / |baseline| * 100``: positive when the
   objective rises, whatever the baseline's sign, and ``nan`` for a zero baseline
   (it was 0.0). Scenario reports and charts use the same definition.

Bottlenecks
~~~~~~~~~~~

**Bottlenecks** are binding constraints that, when relaxed, would significantly improve
the objective value. What-if analysis can automatically identify them.

**Characteristics:**

- Binding (slack = 0)
- High shadow price
- Relaxing them improves the objective
- Worth investigating for improvement opportunities

Basic Usage
-----------

Creating an Analyzer
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.analysis import LXWhatIfAnalyzer

   # Create analyzer
   analyzer = LXWhatIfAnalyzer(
       model=model,
       optimizer=optimizer
   )

   # Get baseline solution (cached)
   baseline = analyzer.get_baseline_solution()
   print(f"Baseline objective: ${baseline.objective_value:,.2f}")

Increasing Constraint RHS
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # What if we increase capacity by 100?
   result = analyzer.increase_constraint_rhs("capacity", by=100)

   print(f"Original objective: ${result.original_objective:,.2f}")
   print(f"New objective:      ${result.new_objective:,.2f}")
   print(f"Impact:             ${result.delta_objective:,.2f}")
   print(f"Percentage change:  {result.delta_percentage:.1f}%")

Decreasing Constraint RHS
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # What if we reduce budget by 20%?
   result = analyzer.decrease_constraint_rhs("budget", by_percent=0.20)

   print(f"Reducing budget by 20% would decrease profit by ${-result.delta_objective:,.2f}")

Setting Constraint RHS
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # What if we set capacity to exactly 1500?
   result = analyzer.increase_constraint_rhs("capacity", to=1500)

   print(f"Setting capacity to 1500 would change objective by {result.delta_percentage:.1f}%")

Relaxing Constraints
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Relax constraint by 10%
   result = analyzer.relax_constraint("min_production", by_percent=0.10)

   print(f"Relaxing minimum production by 10%:")
   print(f"  Impact: ${result.delta_objective:,.2f}")

``relax_constraint`` raises the right-hand side of a ``<=`` row and lowers that of
a ``>=`` row; ``tighten_constraint`` does the opposite. On an equality, relaxing
raises the right-hand side and tightening lowers it.

``by_percent`` moves the right-hand side by a share of its absolute value:
``increase_constraint_rhs(..., by_percent=p)`` gives ``rhs + p * |rhs|``, and
relaxing a ``>=`` row with right-hand side ``-10`` by 20 % gives ``-12``.

.. versionchanged:: 0.3.0
   ``by_percent`` uses ``|rhs|``, so a negative right-hand side moves in the
   requested direction, and ``tighten_constraint`` on an equality lowers the
   right-hand side (it raised it, like ``relax_constraint``).

Per-Row Right-Hand Sides
~~~~~~~~~~~~~~~~~~~~~~~~

.. versionchanged:: 0.3.0
   ``increase_constraint_rhs``, ``decrease_constraint_rhs``, ``relax_constraint`` and
   ``tighten_constraint`` work on constraints whose right-hand side is a function.

For an indexed constraint family defined with ``.rhs(lambda row: ...)``, every row
changes:

.. code-block:: python

   # capacity[m] <= m.hours for every machine m
   analyzer.increase_constraint_rhs("capacity", by=10)          # m.hours + 10
   analyzer.increase_constraint_rhs("capacity", by_percent=0.2) # m.hours * 1.2
   analyzer.relax_constraint("capacity", by=5)                  # m.hours + 5 (<= rows)
   analyzer.increase_constraint_rhs("capacity", to=40)          # 40 for every row

   change = analyzer.increase_constraint_rhs("capacity", by=10).changes_applied[0]
   print(change.original_value, change.new_value, change.delta)  # None None None

Building Models with a Factory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. versionadded:: 0.3.0

By default the analyzer copies ``model`` for every what-if run (see
`Model Copying and ORM Data`_). Instead you can pass a function that builds the model:

.. code-block:: python

   analyzer = LXWhatIfAnalyzer(optimizer=optimizer, model_factory=build_model)
   result = analyzer.relax_constraint("capacity", by=100)

- The factory is called once for the baseline model (``analyzer.model``) and once per
  what-if run; nothing is copied.
- It must return a **new** model on every call; returning one it already returned
  raises ``ValueError``.
- Pass exactly one of ``model`` and ``model_factory`` (``ValueError`` otherwise); a
  missing ``optimizer`` raises ``TypeError``.
- A model built for a what-if run is freed once the run is over (the analyzer keeps
  only the baseline model).

See `ORM Data with a Fresh Session`_ for the typical use.

Recording Results
~~~~~~~~~~~~~~~~~

.. versionadded:: 0.3.0

With ``result_store=`` every solve is written to the database: the baseline when it is
computed, then each what-if run. The run is named after the what-if description
(for example ``"Relax capacity RHS by 100"``) and its modifications are the applied
changes.

.. code-block:: python

   from lumix import LXResultStore

   store = LXResultStore(session, analysis="capacity-what-if")
   analyzer = LXWhatIfAnalyzer(model, optimizer, result_store=store)

See :doc:`result-store`.

Finding Bottlenecks
-------------------

Automatic Bottleneck Detection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Find top 5 bottlenecks
   bottlenecks = analyzer.find_bottlenecks(test_amount=1.0, top_n=5)

   print("Top 5 Bottlenecks:")
   print("-" * 60)
   for name, improvement_per_unit in bottlenecks:
       print(f"{name:30s}: ${improvement_per_unit:>10.2f}/unit")

   # Example output:
   # Top 5 Bottlenecks:
   # ------------------------------------------------------------
   # warehouse_capacity              :     $50.00/unit
   # labor_hours                     :     $35.00/unit
   # truck_capacity                  :     $25.00/unit
   # material_budget                 :     $12.50/unit
   # min_quality_standard            :      $8.00/unit

``find_bottlenecks`` relaxes every constraint of the model by ``test_amount`` (one
re-solve per constraint) and returns ``(constraint_name, improvement_per_unit)`` pairs,
best first:

- The improvement is **positive when relaxing the constraint makes the objective
  better** in the objective's own direction: larger for maximization, smaller for
  minimization. For a cost-minimization model, ``("labor_hours", 35.0)`` means one more
  unit of labor saves 35.
- For an indexed constraint family, every row is relaxed by ``test_amount`` and the
  family is ranked as a whole.
- A relaxation that makes the model unbounded ranks as ``float("inf")``. Relaxations
  with any other non-feasible status are left out with a ``UserWarning``.
- A feasible baseline is required; otherwise ``ValueError`` is raised.

.. versionchanged:: 0.3.0
   Improvements follow the objective's sense; for minimization they used to come out
   negative and were ranked backwards. Constraints with a per-row right-hand side are
   supported. Equality rows are tried in both directions (raised and lowered) and the
   better one is reported; they used to be raised only.

Comparing Bottleneck Relaxation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Compare impact of relaxing each bottleneck
   bottlenecks = analyzer.find_bottlenecks(top_n=3)

   print("Bottleneck Comparison:")
   for name, _ in bottlenecks:
       # Try relaxing by 100 units (increases <= and decreases >= right-hand sides)
       result = analyzer.relax_constraint(name, by=100)
       print(f"{name:30s}: ${result.delta_objective:>10,.2f}")

Identifying Binding Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXSensitivityAnalyzer

   # Binding constraints come from the sensitivity analyzer
   baseline = analyzer.get_baseline_solution()
   binding = LXSensitivityAnalyzer(model, baseline).get_binding_constraints()

   print("Binding Constraints (Bottleneck Candidates):")
   for constraint_name in binding:
       print(f"  - {constraint_name}")

   # Or rank constraints by the improvement one more unit of right-hand side gives
   for name, improvement in analyzer.find_bottlenecks(top_n=5):
       print(f"  {name}: {improvement:+.2f} per unit")

Practical Examples
------------------

Example 1: Quick Decision Support
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.analysis import LXWhatIfAnalyzer

   # Stakeholder question: "Should we expand capacity?"
   analyzer = LXWhatIfAnalyzer(model, optimizer)

   # Try different capacity levels
   increases = [50, 100, 150, 200, 250]

   print("Capacity Expansion Analysis:")
   print("-" * 60)
   print(f"{'Increase':>10s} {'New Objective':>15s} {'Improvement':>15s}")
   print("-" * 60)

   for increase in increases:
       result = analyzer.increase_constraint_rhs("capacity", by=increase)
       print(f"{increase:>10d} ${result.new_objective:>14,.2f} ${result.delta_objective:>14,.2f}")

   # Recommendation
   print("\nRecommendation: Each unit of capacity adds approximately $X to profit")

Example 2: Budget Sensitivity
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Question: "What if we have to cut the budget?"
   budget_cuts = [0.05, 0.10, 0.15, 0.20, 0.25]  # 5% to 25%

   print("Budget Cut Impact Analysis:")
   print("-" * 60)
   print(f"{'Cut %':>8s} {'New Objective':>15s} {'Loss':>15s}")
   print("-" * 60)

   for cut in budget_cuts:
       result = analyzer.decrease_constraint_rhs("budget", by_percent=cut)
       loss = result.original_objective - result.new_objective
       print(f"{cut*100:>7.0f}% ${result.new_objective:>14,.2f} ${loss:>14,.2f}")

   # Risk assessment
   result_10pct = analyzer.decrease_constraint_rhs("budget", by_percent=0.10)
   result_20pct = analyzer.decrease_constraint_rhs("budget", by_percent=0.20)

   print("\nRisk Assessment:")
   print(f"  10% cut would reduce profit by {abs(result_10pct.delta_percentage):.1f}%")
   print(f"  20% cut would reduce profit by {abs(result_20pct.delta_percentage):.1f}%")

Example 3: Resource Allocation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Question: "Where should we invest to improve profit?"
   resources = {
       "warehouse_space": 100,    # $100k to add 100 units
       "truck_fleet": 75,         # $75k to add 5 trucks
       "labor_hours": 50,         # $50k for 100 hours
   }

   print("Investment ROI Analysis:")
   print("-" * 60)
   print(f"{'Resource':30s} {'Cost':>10s} {'Benefit':>15s} {'ROI':>10s}")
   print("-" * 60)

   best_roi = None
   best_resource = None

   for resource, cost in resources.items():
       # Determine appropriate increase
       if resource == "warehouse_space":
           result = analyzer.increase_constraint_rhs(resource, by=100)
       elif resource == "truck_fleet":
           result = analyzer.increase_constraint_rhs(resource, by=5)
       else:  # labor_hours
           result = analyzer.increase_constraint_rhs(resource, by=100)

       benefit = result.delta_objective
       roi = (benefit / cost * 1000) * 100 if cost > 0 else 0  # cost in $k

       print(f"{resource:30s} ${cost:>9,d}k ${benefit:>14,.2f} {roi:>9.1f}%")

       if best_roi is None or roi > best_roi:
           best_roi = roi
           best_resource = resource

   print(f"\nBest investment: {best_resource} (ROI: {best_roi:.1f}%)")

Example 4: Exploring Variable Bounds
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Question: "What if we change production limits?"

   # modify_variable_bound takes absolute values (there is no ``by=`` form)
   result = analyzer.modify_variable_bound("production", upper=550)
   print(f"Raising the production limit to 550: ${result.delta_objective:,.2f}")

   # Relax the minimum
   result = analyzer.modify_variable_bound("production", lower=0)
   print(f"Removing the minimum production: ${result.delta_objective:,.2f}")

   # Both bounds at once
   result = analyzer.modify_variable_bound("production", lower=10, upper=500)
   print(f"Production between 10 and 500: ${result.delta_objective:,.2f}")

Example 5: Multi-Parameter What-If
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Question: "What's the combined effect of multiple changes?"

   # compare_changes runs one what-if per (name, change_type, amount) tuple;
   # change types: "increase", "decrease", "relax", "tighten"
   changes = [
       ("capacity", "increase", 100),
       ("capacity", "increase", 200),
       ("budget", "decrease", 1000),
   ]

   results = analyzer.compare_changes(changes)   # List[LXWhatIfResult]

   print("Multi-Parameter What-If Analysis:")
   print("-" * 70)
   for result in results:
       print(f"{result.description:50s}: ${result.delta_objective:>10,.2f}")

   # Percent changes use the single-change methods
   result = analyzer.increase_constraint_rhs("labor", by_percent=0.20)

Each call changes one parameter of a fresh copy of the model; the effects of
separate calls are not combined. For combined changes use a
:class:`~lumix.analysis.scenario.LXScenario` with several modifications.

Advanced Features
-----------------

Exact Values and Change Records
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Set a right-hand side to an exact value
   result = analyzer.increase_constraint_rhs("capacity", to=1500)

   # Every result lists what was changed as LXWhatIfChange records
   for change in result.changes_applied:
       print(change.change_type, change.target_name, change.original_value,
             change.new_value)

Interactive Exploration
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Interactive CLI for stakeholders
   while True:
       constraint = input("Which constraint to modify? (or 'quit'): ")
       if constraint == 'quit':
           break

       amount = float(input(f"Increase {constraint} by how much?: "))

       result = analyzer.increase_constraint_rhs(constraint, by=amount)

       print(f"\nImpact: ${result.delta_objective:,.2f}")
       print(f"New objective: ${result.new_objective:,.2f}\n")

Comparing with Sensitivity Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.analysis import LXSensitivityAnalyzer, LXWhatIfAnalyzer

   # Get baseline solution
   solution = optimizer.solve(model)

   # Sensitivity analysis (no re-solve); "capacity" is a scalar constraint here.
   # For a row of an indexed family use its row name, e.g. "capacity[3]".
   sens = LXSensitivityAnalyzer(model, solution)
   shadow_price = sens.analyze_constraint("capacity").shadow_price

   print(f"Shadow price (sensitivity): ${shadow_price:.2f}/unit")

   # What-if analysis (re-solve)
   whatif = LXWhatIfAnalyzer(model, optimizer)
   result = whatif.increase_constraint_rhs("capacity", by=1)

   print(f"Actual impact (what-if):    ${result.delta_objective:.2f}/unit")

   # They should be similar (if within valid range)
   if abs(shadow_price - result.delta_objective) < 0.01:
       print("Shadow price accurately predicts impact!")

Caching and Performance
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Baseline is automatically cached
   analyzer = LXWhatIfAnalyzer(model, optimizer)

   # First call solves baseline
   result1 = analyzer.increase_constraint_rhs("capacity", by=100)  # Solves 2x

   # Subsequent calls reuse cached baseline
   result2 = analyzer.increase_constraint_rhs("capacity", by=200)  # Solves 1x
   result3 = analyzer.decrease_constraint_rhs("budget", by=100)    # Solves 1x

   # Clear cache if model changes
   analyzer._baseline_solution = None

Best Practices
--------------

1. **Start with Bottleneck Analysis**

   Identify the most impactful parameters first.

   .. code-block:: python

      # Always start here
      bottlenecks = analyzer.find_bottlenecks(top_n=5)

      # Then explore the top bottlenecks
      for name, _ in bottlenecks[:3]:
          result = analyzer.relax_constraint(name, by=100)
          print(f"{name}: ${result.delta_objective:,.2f}")

2. **Test Realistic Ranges**

   Don't explore unrealistic parameter values.

   .. code-block:: python

      # Bad: Unrealistic 10x increase
      result = analyzer.increase_constraint_rhs("capacity", by=10000)

      # Good: Realistic 20% increase
      current_capacity = 1000
      result = analyzer.increase_constraint_rhs("capacity", by=current_capacity * 0.2)

3. **Combine with Sensitivity Analysis**

   Use sensitivity for quick estimates, what-if for validation.

   .. code-block:: python

      # 1. Sensitivity analysis identifies opportunities (constraint rows,
      #    e.g. "capacity[3]" for an indexed family)
      sens = LXSensitivityAnalyzer(model, solution)
      bottlenecks = sens.identify_bottlenecks()

      # 2. What-if analysis quantifies them exactly; it changes whole
      #    constraint families, so map rows to family names
      whatif = LXWhatIfAnalyzer(model, optimizer)
      for constraint in dict.fromkeys(b.split("[", 1)[0] for b in bottlenecks):
          result = whatif.relax_constraint(constraint, by=100)
          print(f"{constraint}: ${result.delta_objective:,.2f}")

4. **Document Assumptions**

   Make it clear what each what-if represents.

   .. code-block:: python

      result = analyzer.increase_constraint_rhs("capacity", by=200)
      result.changes_applied[0].description = (
          "Warehouse expansion project: +200 units capacity"
      )

5. **Validate Feasibility**

   Check that what-if scenarios produce feasible solutions.

   .. code-block:: python

      result = analyzer.decrease_constraint_rhs("budget", by=10000)

      if not result.new_solution.is_optimal():
          print("Warning: This change makes the model infeasible!")
          print("Recommendation: Less aggressive budget cut")

Performance Considerations
--------------------------

What-if analysis re-solves the model for each change, which can be slow for large models.

**Optimization Tips:**

1. **Use Sensitivity First**: For quick estimates, use shadow prices
2. **Batch Similar Changes**: Group related what-ifs together
3. **Cache Baseline**: The analyzer automatically caches the baseline solution
4. **Warm Starts**: Use solver warm start if available

.. code-block:: python

   # Efficient what-if workflow

   # 1. Solve once and cache
   analyzer = LXWhatIfAnalyzer(model, optimizer)
   baseline = analyzer.get_baseline_solution()  # Cached

   # 2. Multiple what-ifs reuse cached baseline
   results = []
   for increase in [50, 100, 150]:  # Each solves once
       result = analyzer.increase_constraint_rhs("capacity", by=increase)
       results.append(result)

When to Use What-If vs. Scenario Analysis
------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Aspect
     - What-If Analysis
     - Scenario Analysis
   * - **Number of Changes**
     - Single parameter
     - Multiple parameters
   * - **Use Case**
     - Quick exploration
     - Systematic comparison
   * - **Workflow**
     - Interactive
     - Batch processing
   * - **Best For**
     - Answering questions on-the-fly
     - Comparing predefined scenarios
   * - **Speed**
     - Fast (1 re-solve)
     - Moderate (N re-solves)

**Recommendation:**

- Use **what-if** for exploring individual parameters interactively
- Use **scenario** for comparing complete alternative futures systematically
- Use **both** together for comprehensive analysis

Model Copying and ORM Data
--------------------------

Under the Hood
~~~~~~~~~~~~~~

What-if analysis never changes the model you pass in. Unless you give a
``model_factory``, each what-if run works on a copy made with ``copy.deepcopy``:

.. code-block:: python

   from copy import deepcopy

   # What-if analyzer does this internally
   modified_model = deepcopy(original_model)
   modified_model.get_constraint("capacity").rhs_value = new_value
   modified_solution = optimizer.solve(modified_model)

.. versionchanged:: 0.3.0
   The copy shares data instances and callables with the original; nothing is
   deep-copied or detached any more.

The copy has its own variable and constraint families, expressions and data lists, so
changing a right-hand side or a bound in the copy leaves the original untouched. Every
**data instance** (plain objects and ORM objects alike) and every **callable** (the
lambdas you passed to ``.rhs()``, ``.add_term()``, ``.indexed_by()`` ...) is shared with
the original. As a result:

- Closures that test identity (``lambda p: 1.0 if p is flagship else 0.0``) or look up
  dictionaries keyed by instances (``lambda p: weights[p]``) behave in the copy exactly
  as in the original.
- An ORM-backed family (``from_model(Product, session=session)``) runs its query once,
  when the copy is made; the copy then holds that list of (shared) instances.
- ORM instances are not detached: a lambda that touches a lazy relationship
  (``p.category.factor``) loads it through the instance's own session, as it would in the
  original model.

ORM Data with a Fresh Session
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Because instances are shared, a copied ORM model needs the instances' session to be
usable whenever lambdas read attributes that are not loaded yet. If that session may be
closed before or during the analysis, build the model with a factory that opens a fresh
session:

.. code-block:: python

   from sqlalchemy.orm import Session, selectinload
   from lumix import LXLinearExpression, LXModel, LXVariable, LXWhatIfAnalyzer

   def build_model():
       with Session(engine) as session:     # closed after loading
           products = (session.query(Product)
                       .options(selectinload(Product.category))   # what lambdas read
                       .all())

       production = (
           LXVariable[Product, float]("production")
           .continuous()
           .bounds(lower=0)
           .indexed_by(lambda p: p.id)
           .from_data(products)
       )
       model = LXModel("production").add_variable(production)
       # ... add constraints ...
       model.maximize(
           LXLinearExpression().add_term(production, lambda p: p.profit * p.category.factor)
       )
       return model

   analyzer = LXWhatIfAnalyzer(optimizer=optimizer, model_factory=build_model)
   result = analyzer.increase_constraint_rhs("capacity", by=100)

.. important::

   Close the session inside the factory, after eager-loading every relationship your
   lambdas read (``selectinload`` / ``joinedload``). Loaded attributes stay readable on
   the instances after the session closes, and the connection goes back to the pool.
   A session left open per model holds one pooled connection each, so with SQLAlchemy's
   default pool (5 + 10 overflow) the 16th run would wait for a connection and fail.

Without a factory, keep the model's session open for the lifetime of the analyzer.

Pickling
~~~~~~~~

Detaching ORM objects from their session (``lumix.utils.copy_utils.detach_orm_object``)
is now used only when a model is **pickled**. When it detaches an instance that still has
a session, it loads unloaded relationships first; without a session it warns that those
relationships will not be available. See :doc:`/user-guide/utils/model-copying`.

Best Practices with ORM
~~~~~~~~~~~~~~~~~~~~~~~

1. **Prefer a model factory** when the session that loaded the data may be closed.

2. **Or keep the session open** while the analyzer is in use:

   .. code-block:: python

      with Session(engine) as session:
          model = build_model(session)
          analyzer = LXWhatIfAnalyzer(model, optimizer)
          result = analyzer.increase_constraint_rhs("capacity", by=100)

3. **Avoid Session Queries in Lambdas**

   Lambdas run for every row; read attributes of the instance instead of querying:

   .. code-block:: python

      # Bad: a query per coefficient
      bad_func = lambda p: session.query(Cost).filter_by(product_id=p.id).one().value  # ❌

      # Good: use loaded attributes
      good_func = lambda p: p.cost  # ✓

Next Steps
----------

- :doc:`sensitivity` - Understand shadow prices and reduced costs
- :doc:`scenario` - Compare multiple scenarios systematically
- :doc:`/user-guide/utils/model-copying` - How model copies share data
- :doc:`result-store` - Persist what-if results
- :doc:`/api/analysis/index` - Complete API reference
- :doc:`/tutorials/production_planning/step7_whatif` - Tutorial with what-if analysis
- :doc:`/development/analysis-architecture` - Architecture details
