Objective Building
==================

Learn how goal programming objectives are constructed from relaxed constraints and deviation variables.

Overview
--------

Once constraints are relaxed and deviation variables are created, LumiX builds the objective
function by combining weighted deviations. The objective building module provides functions for:

- **Weighted objectives**: Single objective with exponentially scaled priorities
- **Sequential objectives**: Multiple objectives for lexicographic optimization
- **Combined objectives**: Mix traditional objectives with goal deviations
- **Custom objectives**: Extract priority 0 goals as custom terms

Objective Types
---------------

Weighted Objective
~~~~~~~~~~~~~~~~~~

Combines all goals into a single objective function:

.. math::

   \min \sum_{p=1}^{P} w_p \sum_{g \in G_p} w_g d_g

Where:

- :math:`w_p` = priority weight (e.g., :math:`10^{6-p}`)
- :math:`w_g` = goal weight
- :math:`d_g` = undesired deviation(s) for goal :math:`g`
- :math:`G_p` = set of goals at priority :math:`p`

.. code-block:: python

   from lumix.goal_programming import build_weighted_objective

   # Build weighted objective from relaxed constraints
   objective = build_weighted_objective(
       relaxed_constraints=relaxed_list,
       base=10.0,           # Base for exponential scaling
       exponent_offset=6    # Priority 1 → 10^6, Priority 2 → 10^5, etc.
   )

   # Use in model
   model.minimize(objective)

Sequential Objectives
~~~~~~~~~~~~~~~~~~~~~

Creates separate objectives for each priority level:

.. code-block:: python

   from lumix.goal_programming import build_sequential_objectives

   # Build list of (priority, objective) tuples
   sequential_objs = build_sequential_objectives(relaxed_list)

   # Returns:
   # [
   #     (1, objective_priority_1),
   #     (2, objective_priority_2),
   #     (3, objective_priority_3),
   # ]

   # Solve sequentially
   for priority, obj_expr in sequential_objs:
       model.minimize(obj_expr)
       solution = optimizer.solve(model)
       # Fix deviations at this priority before next iteration

Building Weighted Objectives
-----------------------------

Basic Usage
~~~~~~~~~~~

.. code-block:: python

   from lumix import LXModel, LXVariable, LXConstraint
   from lumix.core.expressions import LXLinearExpression
   from lumix.goal_programming import relax_constraint, LXGoalMetadata, build_weighted_objective
   from lumix.core.enums import LXConstraintSense

   # Define constraints
   demand_constraint = (
       LXConstraint[Product]("demand")
       .expression(production_expr)
       .ge()
       .rhs(lambda p: p.demand)
       .from_data(products)
   )

   quality_constraint = (
       LXConstraint("quality")
       .expression(quality_expr)
       .ge()
       .rhs(0.95)
   )

   # Create metadata
   demand_metadata = LXGoalMetadata(
       priority=1,
       weight=1.0,
       constraint_sense=LXConstraintSense.GE
   )

   quality_metadata = LXGoalMetadata(
       priority=2,
       weight=0.5,
       constraint_sense=LXConstraintSense.GE
   )

   # Relax constraints
   relaxed_demand = relax_constraint(demand_constraint, demand_metadata)
   relaxed_quality = relax_constraint(quality_constraint, quality_metadata)

   relaxed_list = [relaxed_demand, relaxed_quality]

   # Build weighted objective
   objective = build_weighted_objective(relaxed_list)

   # Resulting objective (conceptually):
   # minimize: 1,000,000 × 1.0 × sum(neg_dev[demand])
   #         +   100,000 × 0.5 × sum(neg_dev[quality])

Custom Weight Scaling
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Default: base=10, exponent_offset=6
   #   Priority 1: 10^6
   #   Priority 2: 10^5
   #   Priority 3: 10^4

   # Custom scaling for wider separation
   objective = build_weighted_objective(
       relaxed_list,
       base=100.0,          # Larger base
       exponent_offset=10   # Larger offset
   )

   # Results in:
   #   Priority 1: 100^10 = 10^20
   #   Priority 2: 100^9 = 10^18
   #   Priority 3: 100^8 = 10^16

Understanding Priority-to-Weight Conversion
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.goal_programming import priority_to_weight

   # Check weight for each priority
   for priority in [0, 1, 2, 3]:
       weight = priority_to_weight(priority)
       print(f"Priority {priority}: weight = {weight:,.0f}")

   # Output:
   #   Priority 0: weight = 1           (custom objectives)
   #   Priority 1: weight = 1,000,000
   #   Priority 2: weight = 100,000
   #   Priority 3: weight = 10,000

Building Sequential Objectives
-------------------------------

Basic Usage
~~~~~~~~~~~

.. code-block:: python

   from lumix.goal_programming import build_sequential_objectives

   # Build sequential objectives
   sequential_objs = build_sequential_objectives(relaxed_list)

   # Solve each priority level
   for priority, objective_expr in sequential_objs:
       print(f"Optimizing priority {priority}")

       # Set objective
       model.objective_expr = objective_expr
       model.objective_sense = LXObjectiveSense.MINIMIZE

       # Solve
       solution = optimizer.solve(model)

       if not solution.is_optimal():
           print(f"Warning: Priority {priority} not optimal")
           break

       # Fix deviations for next iteration
       # (implementation details omitted)

What Gets Excluded
~~~~~~~~~~~~~~~~~~

Priority 0 goals (custom objectives) are excluded from sequential objectives:

.. code-block:: python

   # Priority 0 goals are NOT included in sequential objectives
   profit_goal = (
       LXConstraint("profit")
       .expression(profit_expr)
       .ge()
       .rhs(0)
       .as_goal(priority=0, weight=1.0)  # Priority 0
   )

   # build_sequential_objectives will skip this
   # These should be handled separately or combined with highest priority

Combining Objectives
--------------------

Traditional + Goal Objectives
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.goal_programming import combine_objectives

   # Traditional objective: Maximize profit
   profit_expr = (
       LXLinearExpression()
       .add_term(production, lambda p: p.profit_margin)
   )

   # Goal objective: Minimize deviations
   goal_expr = build_weighted_objective(relaxed_list)

   # Combine (for minimization problem)
   combined = combine_objectives(
       base_objective=profit_expr,
       goal_objective=goal_expr,
       goal_weight=0.01  # Relative weight for goals
   )

   # Result:
   #   minimize: profit_expr + 0.01 × goal_expr
   #   (Note: if profit should be maximized, negate it first)

Handling Maximization
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # For maximization objectives, negate before combining
   profit_expr_neg = (
       LXLinearExpression()
       .add_term(production, lambda p: -p.profit_margin)  # Negated
   )

   # Now combine with goals (all minimization)
   combined = combine_objectives(
       base_objective=profit_expr_neg,  # -profit (to minimize)
       goal_objective=goal_expr,         # deviations (to minimize)
       goal_weight=1.0
   )

Custom Objectives (Priority 0)
-------------------------------

Extracting Custom Objectives
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.goal_programming import extract_custom_objectives

   # Some goals have priority 0 (custom objectives)
   profit_goal = (
       LXConstraint("profit")
       .expression(profit_expr)
       .ge()
       .rhs(0)
       .as_goal(priority=0, weight=1.0)
   )

   # After relaxation
   relaxed_profit = relax_constraint(profit_goal, profit_metadata)

   all_relaxed = [relaxed_demand, relaxed_quality, relaxed_profit]

   # Extract priority 0 goals
   custom_objs = extract_custom_objectives(all_relaxed)

   # custom_objs contains only relaxed_profit
   for custom in custom_objs:
       print(f"Custom objective: {custom.constraint.name}")

Using Custom Objectives
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Priority 0 goals are treated as custom objective terms
   # They contribute to the objective with weight 1.0 (no priority scaling)

   # In weighted mode:
   #   Objective = custom_objectives + priority_1_goals + priority_2_goals + ...
   #
   # Where custom_objectives use weight 1.0,
   # and priority goals use exponential scaling

   # Example:
   #   minimize: 1.0 × neg_dev[profit]           (priority 0)
   #           + 1,000,000 × neg_dev[demand]     (priority 1)
   #           + 100,000 × neg_dev[quality]      (priority 2)

Practical Examples
------------------

Multi-Objective Production Planning
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dataclasses import dataclass
   from typing import List

   @dataclass
   class Product:
       id: str
       demand: float
       profit_margin: float

   products = [
       Product("A", demand=100, profit_margin=10),
       Product("B", demand=150, profit_margin=12),
   ]

   # Variables
   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .bounds(lower=0)
       .indexed_by(lambda p: p.id)
       .from_data(products)
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

   # Priority 1: Meet demand
   demand_goal = (
       LXConstraint[Product]("demand")
       .expression(
           LXLinearExpression()
           .add_term(production, coeff=1.0)
       )
       .ge()
       .rhs(lambda p: p.demand)
       .as_goal(priority=1, weight=1.0)
       .from_data(products)
   )

   # Build model (automatic objective building)
   model = (
       LXModel("multi_objective")
       .add_variable(production)
       .add_constraint(profit_goal)
       .add_constraint(demand_goal)
   )

   # Behind the scenes:
   #   1. Constraints are relaxed
   #   2. Weighted objective is built:
   #        minimize: 1.0 × neg_dev[profit]
   #                + 1,000,000 × neg_dev[demand]
   #   3. Demand is effectively prioritized over profit

Portfolio Optimization
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Priority 0: Maximize return
   return_goal = (
       LXConstraint("return")
       .expression(return_expr)
       .ge()
       .rhs(0)
       .as_goal(priority=0, weight=1.0)
   )

   # Priority 1: Control risk
   risk_goal = (
       LXConstraint("risk")
       .expression(risk_expr)
       .le()
       .rhs(max_risk)
       .as_goal(priority=1, weight=1.0)
   )

   # Priority 2: Diversification
   diversity_goal = (
       LXConstraint("diversity")
       .expression(diversity_expr)
       .ge()
       .rhs(min_diversity)
       .as_goal(priority=2, weight=1.0)
   )

   model = (
       LXModel("portfolio")
       .add_variable(allocation)
       .add_constraint(return_goal)
       .add_constraint(risk_goal)
       .add_constraint(diversity_goal)
   )

   # Objective hierarchy:
   #   1. First meet risk constraints (priority 1)
   #   2. Then achieve diversification (priority 2)
   #   3. Finally maximize return (priority 0, lower weight)

Advanced Techniques
-------------------

Dynamic Objective Construction
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Build objective based on solution state
   def build_adaptive_objective(solution, relaxed_constraints):
       """Adjust weights based on previous solution."""

       # Calculate achieved deviations
       achieved_devs = {}
       for relaxed in relaxed_constraints:
           total_dev = solution.get_total_deviation(relaxed.constraint.name)
           achieved_devs[relaxed.constraint.name] = total_dev

       # Increase weight for goals that weren't achieved
       adjusted_relaxed = []
       for relaxed in relaxed_constraints:
           if achieved_devs[relaxed.constraint.name] > 1e-3:
               # Increase weight for unmet goals
               relaxed.goal_metadata.weight *= 2.0

           adjusted_relaxed.append(relaxed)

       # Build new objective
       return build_weighted_objective(adjusted_relaxed)

Conditional Objective Terms
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Include goals conditionally based on scenario
   def build_scenario_objective(scenario, all_relaxed):
       """Build objective for specific scenario."""

       if scenario == "cost_focused":
           # Filter to cost-related goals only
           relevant = [r for r in all_relaxed if "cost" in r.constraint.name]

       elif scenario == "quality_focused":
           # Filter to quality-related goals
           relevant = [r for r in all_relaxed if "quality" in r.constraint.name]

       else:  # balanced
           relevant = all_relaxed

       return build_weighted_objective(relevant)

Debugging Objectives
--------------------

Inspecting Objective Structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Build objective
   objective = build_weighted_objective(relaxed_list)

   # Inspect terms
   print(f"Objective has {len(objective.terms)} variable terms")
   print(f"Objective constant: {objective.constant}")

   for var_name, (var, coeff_func, where_func) in objective.terms.items():
       print(f"  Variable: {var_name}")
       print(f"    Coefficient function: {coeff_func}")

Validating Weights
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Verify priority weights
   for relaxed in relaxed_list:
       priority = relaxed.goal_metadata.priority
       weight = relaxed.goal_metadata.weight

       priority_weight = priority_to_weight(priority)
       combined_weight = priority_weight * weight

       print(f"Goal: {relaxed.constraint.name}")
       print(f"  Priority: {priority}")
       print(f"  Weight: {weight}")
       print(f"  Priority Weight: {priority_weight:,.0f}")
       print(f"  Combined: {combined_weight:,.0f}")

Best Practices
--------------

1. **Use Appropriate Priority Scaling**

   .. code-block:: python

      # Default scaling is usually sufficient
      objective = build_weighted_objective(relaxed_list)

      # Only adjust if priorities aren't being respected
      # (This is rare with default 10^6, 10^5, 10^4 scaling)

2. **Be Careful with Combined Objectives**

   .. code-block:: python

      # Ensure compatible scales
      # Goal deviations are often large numbers (e.g., 1000s)
      # Traditional objectives might be small (e.g., 0-1)

      # Use appropriate goal_weight to balance
      combined = combine_objectives(
          base_objective=small_scale_expr,
          goal_objective=large_scale_goal_expr,
          goal_weight=0.001  # Reduce goal influence
      )

3. **Monitor Objective Value**

   .. code-block:: python

      solution = optimizer.solve(model)

      print(f"Objective value: {solution.objective_value:.2f}")

      # For weighted mode, large objective values indicate many/large deviations
      # Break down by priority to understand contributions

4. **Validate Against Expected Behavior**

   .. code-block:: python

      # Test that higher priorities dominate
      # Create small test case with conflicting goals

      # Verify that priority 1 goal is achieved even if
      # it means sacrificing priority 2 goals

Next Steps
----------

- :doc:`weighted-mode` - Apply objective building in weighted mode
- :doc:`sequential-mode` - Use sequential objectives
- :doc:`relaxation` - Understand where deviation variables come from
- :doc:`/api/goal_programming/index` - Full API reference
- :doc:`/user-guide/solution/goal-programming` - Working with goal programming solutions
