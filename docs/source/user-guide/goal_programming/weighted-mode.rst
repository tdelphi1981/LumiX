Weighted Goal Programming
=========================

Learn how to use weighted goal programming to solve multi-objective problems with a single optimization run.

Overview
--------

**Weighted goal programming** combines all goals into a single objective function using
weighted sums of deviations. This approach:

- Solves the problem in **one optimization run**
- Uses **exponential weight scaling** to respect priority hierarchy
- Is **computationally efficient** (single solve)
- Provides a **Pareto-optimal** solution

When to Use
-----------

Weighted goal programming is ideal when:

- You want a single optimal solution
- You have clear priority hierarchy but can accept some flexibility
- Computational efficiency is important
- You're comfortable with weighted trade-offs within priority levels

**Not recommended when**:

- Priorities must be absolutely enforced (use :doc:`sequential-mode` instead)
- You need exact lexicographic optimization

How It Works
------------

Weight Scaling
~~~~~~~~~~~~~~

LumiX automatically scales weights exponentially based on priority:

.. code-block:: text

   Priority 1 → Weight = 10^6
   Priority 2 → Weight = 10^5
   Priority 3 → Weight = 10^4
   ...

This ensures higher priorities **effectively dominate** lower priorities in the objective.

**Mathematical formulation**:

.. math::

   \text{minimize} \sum_{p=1}^{P} 10^{(6-p)} \sum_{g \in G_p} w_g (d_g^+ + d_g^-)

Where:

- :math:`P` = number of priorities
- :math:`G_p` = set of goals at priority :math:`p`
- :math:`w_g` = weight for goal :math:`g`
- :math:`d_g^+, d_g^-` = positive/negative deviations

Objective Construction
~~~~~~~~~~~~~~~~~~~~~~

For each goal, the system:

1. Determines which deviation(s) to minimize based on constraint sense
2. Applies the goal's weight
3. Scales by priority level weight
4. Sums all weighted deviations into single objective

.. code-block:: text

   LE (≤): minimize positive deviation (over-achievement)
       overtime <= 40  →  minimize pos_dev

   GE (≥): minimize negative deviation (under-achievement)
       demand >= 1000  →  minimize neg_dev

   EQ (=): minimize both deviations
       budget == 50000  →  minimize (pos_dev + neg_dev)

Basic Usage
-----------

Single-Priority Goals
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXModel, LXVariable, LXConstraint, LXOptimizer
   from lumix.core.expressions import LXLinearExpression

   # Define variables
   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .bounds(lower=0)
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

   # Goal: Meet demand (all same priority)
   demand_goal = (
       LXConstraint[Product]("demand_goal")
       .expression(
           LXLinearExpression()
           .add_term(production, coeff=1.0)
       )
       .ge()
       .rhs(lambda p: p.demand_target)
       .as_goal(priority=1, weight=1.0)
       .from_data(products)
   )

   # Build and solve
   model = (
       LXModel("production")
       .add_variable(production)
       .add_constraint(demand_goal)
   )

   optimizer = LXOptimizer().use_solver("gurobi")
   solution = optimizer.solve(model)

   # Analyze results
   for product_id, qty in solution.get_mapped(production).items():
       print(f"Product {product_id}: {qty} units")

   # Check goal achievement
   if solution.is_goal_satisfied("demand_goal"):
       print("All demand targets met!")
   else:
       deviations = solution.get_goal_deviations("demand_goal")
       total_under = sum(deviations['neg'].values())
       print(f"Total under-production: {total_under:.2f}")

Multi-Priority Goals
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Priority 1: Meet demand (highest)
   demand_goal = (
       LXConstraint[Product]("demand")
       .expression(production_expr)
       .ge()
       .rhs(lambda p: p.demand)
       .as_goal(priority=1, weight=1.0)
       .from_data(products)
   )

   # Priority 2: Maintain quality
   quality_goal = (
       LXConstraint("quality")
       .expression(quality_expr)
       .ge()
       .rhs(0.95)
       .as_goal(priority=2, weight=1.0)
   )

   # Priority 3: Control overtime
   overtime_goal = (
       LXConstraint("overtime")
       .expression(hours_expr)
       .le()
       .rhs(40)
       .as_goal(priority=3, weight=0.5)  # Lower weight
   )

   model = (
       LXModel("multi_priority")
       .add_variable(production)
       .add_constraint(demand_goal)
       .add_constraint(quality_goal)
       .add_constraint(overtime_goal)
   )

   solution = optimizer.solve(model)

   # With exponential scaling:
   #   Priority 1: weight = 1.0 × 10^6 = 1,000,000
   #   Priority 2: weight = 1.0 × 10^5 =   100,000
   #   Priority 3: weight = 0.5 × 10^4 =     5,000
   # Priority 1 goals dominate the objective

Using Weights
-------------

Within Same Priority
~~~~~~~~~~~~~~~~~~~~

Weights control relative importance **within the same priority level**:

.. code-block:: python

   # Both priority 1, but different weights
   critical_product = (
       LXConstraint("product_a_demand")
       .expression(production_a_expr)
       .ge()
       .rhs(100)
       .as_goal(priority=1, weight=3.0)  # 3× more important
   )

   normal_product = (
       LXConstraint("product_b_demand")
       .expression(production_b_expr)
       .ge()
       .rhs(100)
       .as_goal(priority=1, weight=1.0)
   )

   # Effective weights:
   #   Product A: 3.0 × 10^6 = 3,000,000
   #   Product B: 1.0 × 10^6 = 1,000,000
   # System will favor meeting Product A's goal

Asymmetric Deviation Costs
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Inventory goal where under-stock is worse than over-stock
   inventory_goal = (
       LXConstraint[Product]("inventory")
       .expression(inventory_expr)
       .eq()  # Target exact amount
       .rhs(lambda p: p.target_inventory)
       .as_goal(priority=1, weight=1.0)
       .from_data(products)
   )

   # Note: EQ goals minimize BOTH pos and neg deviations equally
   # For asymmetric costs, use two separate constraints:

   # Penalize under-stock more
   min_inventory = (
       LXConstraint[Product]("min_inventory")
       .expression(inventory_expr)
       .ge()
       .rhs(lambda p: p.target_inventory)
       .as_goal(priority=1, weight=3.0)  # Higher penalty
       .from_data(products)
   )

   # Penalize over-stock less
   max_inventory = (
       LXConstraint[Product]("max_inventory")
       .expression(inventory_expr)
       .le()
       .rhs(lambda p: p.target_inventory)
       .as_goal(priority=1, weight=1.0)  # Lower penalty
       .from_data(products)
   )

Combining with Custom Objectives
---------------------------------

Priority 0 for Custom Objectives
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use **priority 0** to include a traditional objective alongside goals:

.. code-block:: python

   # Custom objective: Maximize profit (priority 0)
   profit_objective = (
       LXConstraint("profit")
       .expression(
           LXLinearExpression()
           .add_term(production, lambda p: p.profit_margin)
       )
       .ge()
       .rhs(0)
       .as_goal(priority=0, weight=1.0)  # Priority 0!
       .from_data(products)
   )

   # Regular goals (priority 1+)
   demand_goal = (
       LXConstraint[Product]("demand")
       .expression(production_expr)
       .ge()
       .rhs(lambda p: p.demand)
       .as_goal(priority=1, weight=1.0)
       .from_data(products)
   )

   quality_goal = (
       LXConstraint("quality")
       .expression(quality_expr)
       .ge()
       .rhs(0.95)
       .as_goal(priority=2, weight=1.0)
   )

   # Result:
   #   Priority 1 (demand) will be optimized first
   #   Then priority 2 (quality)
   #   Finally, profit will be maximized without hurting higher priorities

Practical Example
-----------------

Production Planning with Multiple Goals
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dataclasses import dataclass
   from typing import List

   @dataclass
   class Product:
       id: str
       demand_target: float
       profit_margin: float
       production_cost: float

   @dataclass
   class Resource:
       id: str
       capacity: float
       cost_per_unit: float

   # Data
   products = [
       Product("A", demand_target=100, profit_margin=10, production_cost=5),
       Product("B", demand_target=150, profit_margin=12, production_cost=6),
       Product("C", demand_target=200, profit_margin=8, production_cost=4),
   ]

   resources = [
       Resource("labor", capacity=500, cost_per_unit=20),
       Resource("material", capacity=1000, cost_per_unit=5),
   ]

   # Variables
   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .bounds(lower=0)
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

   resource_usage = (
       LXVariable[Resource, float]("resource_usage")
       .continuous()
       .bounds(lower=0)
       .indexed_by(lambda r: r.id)
       .from_data(resources)
   )

   # Hard constraint: Resource capacity
   capacity_constraint = (
       LXConstraint[Resource]("capacity")
       .expression(
           LXLinearExpression()
           .add_term(resource_usage, coeff=1.0)
       )
       .le()
       .rhs(lambda r: r.capacity)
       .from_data(resources)
   )

   # Priority 0: Maximize profit (custom objective)
   profit_goal = (
       LXConstraint("profit")
       .expression(
           LXLinearExpression()
           .add_term(production, lambda p: p.profit_margin)
       )
       .ge()
       .rhs(0)
       .as_goal(priority=0, weight=1.0)
   )

   # Priority 1: Meet demand (highest priority goal)
   demand_goal = (
       LXConstraint[Product]("demand")
       .expression(
           LXLinearExpression()
           .add_term(production, coeff=1.0)
       )
       .ge()
       .rhs(lambda p: p.demand_target)
       .as_goal(priority=1, weight=1.0)
       .from_data(products)
   )

   # Priority 2: Efficient resource utilization (lower priority)
   # Want to use exactly 80% of capacity
   utilization_goal = (
       LXConstraint[Resource]("utilization")
       .expression(
           LXLinearExpression()
           .add_term(resource_usage, coeff=1.0)
       )
       .eq()  # Exact target
       .rhs(lambda r: r.capacity * 0.8)
       .as_goal(priority=2, weight=1.0)
       .from_data(resources)
   )

   # Build model
   model = (
       LXModel("production_planning")
       .add_variable(production)
       .add_variable(resource_usage)
       .add_constraint(capacity_constraint)  # Hard constraint
       .add_constraint(profit_goal)
       .add_constraint(demand_goal)
       .add_constraint(utilization_goal)
   )

   # Solve
   optimizer = LXOptimizer().use_solver("gurobi")
   solution = optimizer.solve(model)

   # Analyze results
   print("=" * 80)
   print("PRODUCTION PLANNING RESULTS")
   print("=" * 80)

   if solution.is_optimal():
       print(f"\nObjective Value: {solution.objective_value:.2f}")
       print(f"Solve Time: {solution.solve_time:.3f}s")

       # Production quantities
       print("\nProduction Plan:")
       print("-" * 80)
       for product_id, qty in solution.get_mapped(production).items():
           product = next(p for p in products if p.id == product_id)
           status = "✓" if qty >= product.demand_target else "✗"
           print(f"{status} Product {product_id}: {qty:6.2f} units (target: {product.demand_target})")

       # Resource usage
       print("\nResource Utilization:")
       print("-" * 80)
       for resource_id, usage in solution.get_mapped(resource_usage).items():
           resource = next(r for r in resources if r.id == resource_id)
           pct = (usage / resource.capacity) * 100
           print(f"{resource_id}: {usage:6.2f} / {resource.capacity} ({pct:.1f}%)")

       # Goal achievement
       print("\nGoal Achievement:")
       print("-" * 80)

       goals = [
           ("profit", "Maximize Profit", 0),
           ("demand", "Meet Demand", 1),
           ("utilization", "Target Utilization", 2),
       ]

       for goal_name, description, priority in goals:
           satisfied = solution.is_goal_satisfied(goal_name)
           status = "✓ Achieved" if satisfied else "✗ Not Achieved"

           print(f"\nPriority {priority}: {description}")
           print(f"  Status: {status}")

           if not satisfied:
               total_dev = solution.get_total_deviation(goal_name)
               print(f"  Total Deviation: {total_dev:.2f}")

               deviations = solution.get_goal_deviations(goal_name)
               if isinstance(deviations['pos'], dict):
                   total_pos = sum(deviations['pos'].values())
                   total_neg = sum(deviations['neg'].values())
               else:
                   total_pos = deviations['pos']
                   total_neg = deviations['neg']

               if total_pos > 1e-6:
                   print(f"  Over-achievement: {total_pos:.2f}")
               if total_neg > 1e-6:
                   print(f"  Under-achievement: {total_neg:.2f}")

Advanced Techniques
-------------------

Dynamic Weight Calculation
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Calculate weights based on goal importance
   def calculate_goal_weight(product: Product) -> float:
       """Weight based on profit margin and criticality."""
       base_weight = 1.0
       profit_factor = product.profit_margin / 10.0  # Normalize
       criticality = 2.0 if product.is_critical else 1.0
       return base_weight * profit_factor * criticality

   demand_goal = (
       LXConstraint[Product]("demand")
       .expression(production_expr)
       .ge()
       .rhs(lambda p: p.demand_target)
       .as_goal(
           priority=1,
           weight=1.0  # Could use lambda here if API supported it
       )
       .from_data(products)
   )

Conditional Goals
~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Only create goals for active products
   active_products = [p for p in products if p.is_active]

   demand_goal = (
       LXConstraint[Product]("demand")
       .expression(production_expr)
       .ge()
       .rhs(lambda p: p.demand_target)
       .where(lambda p: p.is_active)  # Filter
       .as_goal(priority=1, weight=1.0)
       .from_data(active_products)
   )

Best Practices
--------------

1. **Use Clear Priority Hierarchy**

   .. code-block:: python

      # Good: Distinct priorities for different objectives
      safety_goal.as_goal(priority=1, weight=1.0)    # Safety first!
      quality_goal.as_goal(priority=2, weight=1.0)   # Then quality
      cost_goal.as_goal(priority=3, weight=1.0)      # Then cost

      # Avoid: Too many priority levels
      # More than 4-5 priorities usually indicates poor problem design

2. **Set Realistic Weights**

   .. code-block:: python

      # Good: Weights reflect relative importance within priority
      high_value_customer.as_goal(priority=1, weight=2.0)
      normal_customer.as_goal(priority=1, weight=1.0)

      # Avoid: Extreme weight differences within same priority
      # If weights differ by >1000×, consider separate priorities instead

3. **Monitor Goal Achievement**

   .. code-block:: python

      # Always check which goals were achieved
      goals_to_check = ["demand", "quality", "overtime"]

      achieved = sum(
          1 for g in goals_to_check
          if solution.is_goal_satisfied(g)
      )

      print(f"Goals achieved: {achieved}/{len(goals_to_check)}")

      # Analyze unmet goals
      for goal in goals_to_check:
          if not solution.is_goal_satisfied(goal):
              dev = solution.get_total_deviation(goal)
              print(f"⚠ {goal}: deviation = {dev:.2f}")

4. **Document Goal Rationale**

   .. code-block:: python

      # Good: Clear documentation of goal purpose and priorities
      demand_goal = (
          LXConstraint[Product]("demand")
          .expression(production_expr)
          .ge()
          .rhs(lambda p: p.demand_target)
          # Priority 1: Customer satisfaction is top priority
          # Weight 1.0: All customers equally important
          .as_goal(priority=1, weight=1.0)
          .from_data(products)
      )

Troubleshooting
---------------

Goals Not Respected
~~~~~~~~~~~~~~~~~~~

**Issue**: Lower priority goals seem to affect higher priority goals.

**Solution**: Check if priority weights are too close. The default exponential scaling
(10^6, 10^5, 10^4) should be sufficient, but you can verify:

.. code-block:: python

   from lumix.goal_programming import priority_to_weight

   # Check weight scaling
   for priority in [1, 2, 3]:
       weight = priority_to_weight(priority)
       print(f"Priority {priority}: {weight:.0f}")

   # If needed, use sequential mode for strict enforcement
   model.set_goal_mode("sequential")

Infeasible Solution
~~~~~~~~~~~~~~~~~~~

**Issue**: Model returns infeasible even with goal programming.

**Cause**: Hard constraints (non-goal constraints) are conflicting.

**Solution**: Convert more constraints to goals:

.. code-block:: python

   # Before: Hard constraint might cause infeasibility
   overtime_constraint = (
       LXConstraint("overtime")
       .expression(hours_expr)
       .le()
       .rhs(40)
       # No .as_goal() - hard constraint
   )

   # After: Soft constraint allows violation if needed
   overtime_goal = (
       LXConstraint("overtime")
       .expression(hours_expr)
       .le()
       .rhs(40)
       .as_goal(priority=2, weight=1.0)  # Now soft
   )

Unexpected Deviations
~~~~~~~~~~~~~~~~~~~~~

**Issue**: Goals have unexpected deviation values.

**Debugging**:

.. code-block:: python

   # Inspect all goal deviations
   for goal_name in ["demand", "quality", "overtime"]:
       deviations = solution.get_goal_deviations(goal_name)

       print(f"\n{goal_name}:")
       print(f"  Positive deviation: {deviations['pos']}")
       print(f"  Negative deviation: {deviations['neg']}")

       # For indexed goals, show breakdown
       if isinstance(deviations['pos'], dict):
           for key in deviations['pos'].keys():
               pos = deviations['pos'][key]
               neg = deviations['neg'][key]
               if pos > 1e-6 or neg > 1e-6:
                   print(f"    {key}: pos={pos:.2f}, neg={neg:.2f}")

Next Steps
----------

- :doc:`sequential-mode` - Learn about lexicographic goal programming
- :doc:`relaxation` - Understand constraint relaxation mechanics
- :doc:`objective-building` - Advanced objective construction
- :doc:`/api/goal_programming/index` - Full API reference
- :doc:`/user-guide/solution/goal-programming` - Accessing goal programming solutions
