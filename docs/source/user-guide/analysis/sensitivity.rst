Sensitivity Analysis
====================

Sensitivity analysis helps you understand how changes in model parameters affect the optimal solution
using shadow prices, reduced costs, and binding constraint analysis.

Overview
--------

Sensitivity analysis answers questions like:

- How much would increasing capacity improve profit?
- Which constraints are limiting performance?
- What's the opportunity cost of a decision?
- How sensitive is the solution to parameter changes?

The :class:`~lumix.analysis.sensitivity.LXSensitivityAnalyzer` provides these insights **without re-solving**
the model by analyzing dual values from the original solution.

Key Concepts
------------

Shadow Prices (Dual Values)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The **shadow price** of a constraint represents the marginal value of relaxing that constraint by one unit.

.. math::

   \text{Shadow Price} = \frac{\partial \text{Objective}}{\partial \text{RHS}}

**Interpretation:**

- Positive shadow price: Relaxing the constraint would improve the objective
- Zero shadow price: The constraint is not binding (has slack)
- Magnitude: How much each unit of relaxation is worth

**Example:**

If a capacity constraint has a shadow price of $50:

- Increasing capacity by 1 unit would improve profit by approximately $50
- This constraint is **binding** (limiting performance)
- This is a potential **bottleneck**

Reduced Costs
~~~~~~~~~~~~~

The **reduced cost** of a variable represents the opportunity cost of forcing that variable to be non-zero
(if currently zero) or to increase its value (if already positive).

**Interpretation:**

- Positive reduced cost (minimization): How much the objective would increase per unit
- Negative reduced cost (maximization): How much profit you'd sacrifice per unit
- Zero reduced cost: Variable is in the optimal basis

Binding Constraints
~~~~~~~~~~~~~~~~~~~

A constraint is **binding** if it's satisfied as an equality at the optimal solution (slack = 0).

**Characteristics:**

- Shadow price ≠ 0
- Relaxing it would improve the objective
- Potential bottleneck
- Worth investigating for improvement

Basic Usage
-----------

Creating an Analyzer
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.analysis import LXSensitivityAnalyzer

   # After solving your model
   solution = optimizer.solve(model)

   # Create analyzer
   analyzer = LXSensitivityAnalyzer(model, solution)

Analyzing Constraints
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Analyze a specific constraint
   capacity_sens = analyzer.analyze_constraint("capacity")

   print(f"Shadow Price: ${capacity_sens.shadow_price:.2f}")
   print(f"Slack: {capacity_sens.slack:.2f}")
   print(f"Binding: {capacity_sens.is_binding}")

   # If solver provides range analysis
   if capacity_sens.allowable_increase:
       print(f"Valid up to +{capacity_sens.allowable_increase:.2f}")

Analyzing Variables
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Analyze a specific variable
   production_sens = analyzer.analyze_variable("production")

   print(f"Value: {production_sens.value:.2f}")
   print(f"Reduced Cost: ${production_sens.reduced_cost:.2f}")
   print(f"At Bound: {production_sens.is_at_bound}")

Generating Reports
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Generate comprehensive report
   report = analyzer.generate_report()
   print(report)

   # Example output:
   # Sensitivity Analysis Report
   # ============================
   #
   # Binding Constraints:
   #   capacity: shadow price = $50.00, slack = 0.00
   #   budget: shadow price = $12.50, slack = 0.00
   #
   # Non-binding Constraints:
   #   min_production: slack = 25.00
   #
   # Variables with Reduced Costs:
   #   product_a: value = 100.0, reduced_cost = $0.00
   #   product_b: value = 0.0, reduced_cost = $-5.00

Identifying Bottlenecks
-----------------------

Finding All Bottlenecks
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get all binding constraints
   bottlenecks = analyzer.identify_bottlenecks()

   for constraint_name in bottlenecks:
       sens = analyzer.analyze_constraint(constraint_name)
       print(f"{constraint_name}:")
       print(f"  Shadow Price: ${sens.shadow_price:.2f}")
       print(f"  Relaxing by 1 unit would improve objective by ${sens.shadow_price:.2f}")

Getting Most Sensitive Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get top N constraints by absolute shadow price
   top_constraints = analyzer.get_most_sensitive_constraints(top_n=5)

   print("Top 5 Most Sensitive Constraints:")
   for name, sensitivity in top_constraints:
       print(f"  {name}: ${sensitivity.shadow_price:.2f}/unit")

Getting Binding Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get all binding constraints with their shadow prices
   binding = analyzer.get_binding_constraints()

   for name, sensitivity in binding.items():
       if sensitivity.shadow_price > 0:  # For maximization
           print(f"{name} is a bottleneck worth ${sensitivity.shadow_price:.2f}/unit")

Practical Examples
------------------

Example 1: Production Planning
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dataclasses import dataclass
   from lumix import LXModel, LXVariable, LXConstraint, LXLinearExpression, LXOptimizer
   from lumix.analysis import LXSensitivityAnalyzer

   @dataclass
   class Product:
       id: str
       profit: float
       labor_hours: float
       material_cost: float

   # Create products
   products = [
       Product("A", 100, 2, 30),
       Product("B", 150, 3, 45),
       Product("C", 120, 2.5, 35),
   ]

   # Build model
   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .bounds(lower=0)
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

   model = (
       LXModel("production")
       .add_variable(production)
       .add_constraint(
           LXConstraint("labor")
           .expression(
               LXLinearExpression()
               .add_term(production, lambda p: p.labor_hours)
           )
           .le()
           .rhs(100)
       )
       .add_constraint(
           LXConstraint("material_budget")
           .expression(
               LXLinearExpression()
               .add_term(production, lambda p: p.material_cost)
           )
           .le()
           .rhs(1000)
       )
       .maximize(
           LXLinearExpression()
           .add_term(production, lambda p: p.profit)
       )
   )

   # Solve
   optimizer = LXOptimizer().use_solver("gurobi")
   solution = optimizer.solve(model)

   # Analyze sensitivity
   analyzer = LXSensitivityAnalyzer(model, solution)

   print(analyzer.generate_report())

   # Find bottlenecks
   bottlenecks = analyzer.identify_bottlenecks()
   print(f"\nBottlenecks: {bottlenecks}")

   # Should labor or material budget be increased?
   labor_sens = analyzer.analyze_constraint("labor")
   material_sens = analyzer.analyze_constraint("material_budget")

   print(f"\nLabor shadow price: ${labor_sens.shadow_price:.2f}/hour")
   print(f"Material shadow price: ${material_sens.shadow_price:.2f}/$")

   if labor_sens.shadow_price > material_sens.shadow_price:
       print("Priority: Increase labor capacity")
   else:
       print("Priority: Increase material budget")

Example 2: Resource Allocation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # After solving a resource allocation model...
   analyzer = LXSensitivityAnalyzer(model, solution)

   # Identify which resources are most valuable
   resource_constraints = [
       "warehouse_space",
       "truck_capacity",
       "driver_hours",
       "fuel_budget",
   ]

   print("Resource Value Analysis:")
   print("-" * 50)

   resource_values = []
   for constraint_name in resource_constraints:
       sens = analyzer.analyze_constraint(constraint_name)
       resource_values.append((constraint_name, sens.shadow_price))
       print(f"{constraint_name:20s}: ${sens.shadow_price:8.2f}/unit")

   # Sort by shadow price
   resource_values.sort(key=lambda x: x[1], reverse=True)

   print(f"\nMost valuable resource: {resource_values[0][0]}")
   print(f"Invest here for maximum ROI: ${resource_values[0][1]:.2f}/unit")

Example 3: Understanding Non-Binding Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Check which constraints have slack
   non_binding = analyzer.get_non_binding_constraints()

   print("Constraints with Slack (Not Limiting):")
   for name, sensitivity in non_binding.items():
       print(f"  {name}: slack = {sensitivity.slack:.2f}")
       print(f"    Could reduce RHS by {sensitivity.slack:.2f} without impact")

Advanced Features
-----------------

Sensitivity Ranges
~~~~~~~~~~~~~~~~~~

Some solvers (Gurobi, CPLEX) provide sensitivity ranges:

.. code-block:: python

   sens = analyzer.analyze_constraint("capacity")

   if sens.allowable_increase and sens.allowable_decrease:
       print(f"Current RHS: 1000")
       print(f"Valid range for shadow price:")
       print(f"  Lower: {1000 - sens.allowable_decrease:.2f}")
       print(f"  Upper: {1000 + sens.allowable_increase:.2f}")
       print(f"Shadow price is valid within this range")

Comparing Multiple Solutions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Solve with different parameters
   solution1 = optimizer.solve(model)
   analyzer1 = LXSensitivityAnalyzer(model, solution1)

   # Modify and resolve
   model.get_constraint("capacity").rhs_value = 1200
   solution2 = optimizer.solve(model)
   analyzer2 = LXSensitivityAnalyzer(model, solution2)

   # Compare shadow prices
   print("Shadow Price Comparison:")
   for name in ["capacity", "budget"]:
       sp1 = analyzer1.analyze_constraint(name).shadow_price
       sp2 = analyzer2.analyze_constraint(name).shadow_price
       print(f"{name}: ${sp1:.2f} -> ${sp2:.2f}")

Solver Support
--------------

Sensitivity analysis requires dual values from the solver:

.. list-table::
   :header-rows: 1
   :widths: 25 25 25 25

   * - Solver
     - Shadow Prices
     - Reduced Costs
     - Sensitivity Ranges
   * - **Gurobi**
     - ✓
     - ✓
     - ✓
   * - **CPLEX**
     - ✓
     - ✓
     - ✓
   * - **OR-Tools**
     - ✓ (LP only)
     - ✓ (LP only)
     - ✗
   * - **GLPK**
     - ✓ (LP only)
     - ✓ (LP only)
     - ✗
   * - **CP-SAT**
     - ✗
     - ✗
     - ✗

Best Practices
--------------

1. **Solve to Optimality First**

   Sensitivity analysis is only meaningful for optimal solutions.

   .. code-block:: python

      solution = optimizer.solve(model)
      if not solution.is_optimal():
          print("Warning: Solution is not optimal, sensitivity may not be meaningful")

2. **Focus on Binding Constraints**

   Non-binding constraints have zero shadow price (by definition).

   .. code-block:: python

      # Only analyze binding constraints
      for name in analyzer.identify_bottlenecks():
          # These are the constraints worth investigating
          analyze_improvement_options(name)

3. **Validate Ranges**

   Shadow prices are only valid within their allowable ranges.

   .. code-block:: python

      sens = analyzer.analyze_constraint("capacity")
      change = 500  # Proposed increase

      if sens.allowable_increase and change > sens.allowable_increase:
          print(f"Warning: Change exceeds valid range")
          print(f"Shadow price may not apply for changes > {sens.allowable_increase}")

4. **Combine with What-If Analysis**

   Use sensitivity analysis to identify opportunities, what-if analysis to quantify them.

   .. code-block:: python

      from lumix.analysis import LXWhatIfAnalyzer

      # Sensitivity identifies bottleneck
      bottlenecks = analyzer.identify_bottlenecks()

      # What-if quantifies the impact
      whatif = LXWhatIfAnalyzer(model, optimizer)
      for constraint in bottlenecks[:3]:  # Top 3
           result = whatif.increase_constraint_rhs(constraint, by=100)
           print(f"{constraint}: ${result.delta_objective:,.2f}")

Next Steps
----------

- :doc:`scenario` - Compare multiple scenarios systematically
- :doc:`whatif` - Interactively explore parameter changes
- :doc:`/api/analysis/index` - Complete API reference
- :doc:`/development/analysis-architecture` - Architecture details
