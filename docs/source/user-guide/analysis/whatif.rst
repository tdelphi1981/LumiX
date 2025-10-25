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

What-If Results
~~~~~~~~~~~~~~~

The :class:`~lumix.analysis.whatif.LXWhatIfResult` contains:

- **Original objective**: Baseline objective value
- **New objective**: Objective after the change
- **Delta objective**: Change in objective (new - original)
- **Delta percentage**: Percentage change
- **Solutions**: Both original and new solutions

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
   result = analyzer.set_constraint_rhs("capacity", value=1500)

   print(f"Setting capacity to 1500 would change objective by {result.delta_percentage:.1f}%")

Relaxing Constraints
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Relax constraint by 10%
   result = analyzer.relax_constraint("min_production", by_percent=0.10)

   print(f"Relaxing minimum production by 10%:")
   print(f"  Impact: ${result.delta_objective:,.2f}")

Finding Bottlenecks
-------------------

Automatic Bottleneck Detection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Find top 5 bottlenecks
   bottlenecks = analyzer.find_bottlenecks(top_n=5)

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

Comparing Bottleneck Relaxation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Compare impact of relaxing each bottleneck
   bottlenecks = analyzer.find_bottlenecks(top_n=3)

   print("Bottleneck Comparison:")
   for name, _ in bottlenecks:
       # Try increasing by 100 units
       result = analyzer.increase_constraint_rhs(name, by=100)
       print(f"{name:30s}: ${result.delta_objective:>10,.2f}")

Identifying Binding Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get all binding constraints
   binding = analyzer.identify_binding_constraints()

   print("Binding Constraints (Bottleneck Candidates):")
   for constraint_name in binding:
       print(f"  - {constraint_name}")

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

   # Increase upper bound
   result = analyzer.increase_variable_upper_bound("production", by=50)
   print(f"Allowing 50 more units of production: ${result.delta_objective:,.2f}")

   # Decrease lower bound (relax minimum)
   result = analyzer.decrease_variable_lower_bound("production", by=20)
   print(f"Reducing minimum production by 20: ${result.delta_objective:,.2f}")

   # Set specific bound
   result = analyzer.set_variable_bound("production", upper=500)
   print(f"Setting max production to 500: ${result.delta_objective:,.2f}")

Example 5: Multi-Parameter What-If
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Question: "What's the combined effect of multiple changes?"

   # Use compare_changes for multiple what-ifs
   changes = [
       ("capacity", "increase", 100),
       ("capacity", "increase", 200),
       ("budget", "decrease_pct", 0.10),
       ("labor", "increase_pct", 0.20),
   ]

   results = analyzer.compare_changes(changes)

   print("Multi-Parameter What-If Analysis:")
   print("-" * 70)
   for description, result in results:
       print(f"{description:50s}: ${result.delta_objective:>10,.2f}")

Advanced Features
-----------------

Custom Change Types
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.analysis import LXWhatIfChange

   # Create custom change
   change = LXWhatIfChange(
       change_type="constraint_rhs",
       target_name="capacity",
       description="Capacity increase to 1500",
       original_value=1000,
       new_value=1500,
       delta=500
   )

   # Apply custom change
   result = analyzer.apply_change(change)

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

   # Sensitivity analysis (no re-solve)
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
          result = analyzer.increase_constraint_rhs(name, by=100)
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

      # 1. Sensitivity analysis identifies opportunities
      sens = LXSensitivityAnalyzer(model, solution)
      bottlenecks = sens.identify_bottlenecks()

      # 2. What-if analysis quantifies them exactly
      whatif = LXWhatIfAnalyzer(model, optimizer)
      for constraint in bottlenecks:
          result = whatif.increase_constraint_rhs(constraint, by=100)
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

Model Copying with ORM Integration
-----------------------------------

Under the Hood
~~~~~~~~~~~~~~

What-if analysis requires creating modified copies of your model without affecting the original. The ``LXWhatIfAnalyzer`` uses Python's ``deepcopy`` internally:

.. code-block:: python

   from copy import deepcopy

   # What-if analyzer does this internally
   modified_model = deepcopy(original_model)
   modified_model.constraints[0].rhs_value = new_value
   modified_solution = optimizer.solve(modified_model)

ORM Challenges
~~~~~~~~~~~~~~

When using ORM frameworks (SQLAlchemy, Django), model copying faces challenges:

**Problem**: ORM objects are bound to database sessions and cannot be pickled/deep copied directly.

**Solution**: LumiX implements automatic **ORM detachment** in ``__deepcopy__`` methods.

How It Works
~~~~~~~~~~~~

1. **Detect ORM Objects**: Identify SQLAlchemy (``_sa_instance_state``) or Django (``_state``, ``_meta``) instances
2. **Materialize Data**: Force-load lazy relationships before copying
3. **Detach from Session**: Create plain Python objects with same attributes
4. **Handle Closures**: Inspect lambda closures for captured ORM objects and detach them
5. **Deep Copy**: Use standard ``deepcopy`` with detached objects

Example with SQLAlchemy
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from sqlalchemy.orm import Session
   from lumix import LXModel, LXVariable, LXWhatIfAnalyzer

   # Build model with ORM data (session-bound objects)
   session = Session(engine)
   products = session.query(Product).all()  # SQLAlchemy objects

   production = LXVariable[Product, float]("production")
       .continuous()
       .indexed_by(lambda p: p.id)
       .from_data(products)  # Uses ORM objects

   model = LXModel("production").add_variable(production)

   # What-if analyzer handles ORM detachment automatically
   analyzer = LXWhatIfAnalyzer(model, optimizer)

   # This works! Model is copied with ORM detachment
   result = analyzer.increase_constraint_rhs("capacity", by=100)

**Behind the scenes:**

1. ``LXWhatIfAnalyzer`` calls ``deepcopy(model)``
2. ``LXModel.__deepcopy__`` detaches all ORM objects
3. Modified model is independent of database session
4. Safe to solve and compare

The copy_utils Module
~~~~~~~~~~~~~~~~~~~~~~

LumiX provides utilities in ``lumix.utils.copy_utils`` for ORM-safe copying:

.. code-block:: python

   from lumix.utils.copy_utils import (
       detach_orm_object,
       materialize_and_detach_list,
       copy_function_detaching_closure
   )

   # Detach single ORM object
   product = session.query(Product).first()
   detached = detach_orm_object(product)
   # Now safe to pickle/deepcopy

   # Detach list of ORM objects
   products = session.query(Product).all()
   detached_list = materialize_and_detach_list(products, {})

   # Copy lambda with ORM object in closure
   profit_func = lambda p: product.profit * p.quantity
   safe_func = copy_function_detaching_closure(profit_func, {})

These utilities are automatically used by ``__deepcopy__`` methods in core classes.

Supported ORMs
~~~~~~~~~~~~~~

- **SQLAlchemy**: Full support with automatic session detachment
- **Django ORM**: Full support with field value copying
- **Plain Python**: No modification needed (pass-through)

For complete details, see :doc:`/user-guide/utils/model-copying`.

Best Practices with ORM
~~~~~~~~~~~~~~~~~~~~~~~~

1. **Use Eager Loading**

   Load all needed data before what-if analysis to avoid lazy-loading errors:

   .. code-block:: python

      from sqlalchemy.orm import joinedload

      products = session.query(Product).options(
          joinedload(Product.materials),
          joinedload(Product.machine_requirements)
      ).all()

2. **Close Session After Model Building**

   Once the model is built, the session is no longer needed:

   .. code-block:: python

      model = build_model(session)
      session.close()  # Safe to close

      # What-if analysis still works
      analyzer = LXWhatIfAnalyzer(model, optimizer)
      result = analyzer.increase_constraint_rhs("capacity", by=100)

3. **Avoid Complex Closures**

   Keep lambda functions simple to avoid pickling issues:

   .. code-block:: python

      # Bad: Complex closure with session
      bad_func = lambda p: session.query(...).first().cost  # ❌

      # Good: Simple value capture
      cost = product.cost
      good_func = lambda p: cost * p.quantity  # ✓

Next Steps
----------

- :doc:`sensitivity` - Understand shadow prices and reduced costs
- :doc:`scenario` - Compare multiple scenarios systematically
- :doc:`/user-guide/utils/model-copying` - Deep dive into ORM-safe copying
- :doc:`/api/analysis/index` - Complete API reference
- :doc:`/tutorials/production_planning/step7_whatif` - Tutorial with what-if analysis
- :doc:`/development/analysis-architecture` - Architecture details
