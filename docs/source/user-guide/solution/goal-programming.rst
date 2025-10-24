Goal Programming Solutions
===========================

Learn how to work with goal programming solutions and analyze goal deviations.

Overview
--------

Goal programming extends traditional optimization by allowing you to define multiple
objectives as **goals** with target values. Instead of strict constraints, goals can
be violated with penalties.

The :class:`~lumix.solution.solution.LXSolution` class provides methods to:

- Access deviation values (positive and negative)
- Check if goals are satisfied
- Calculate total deviations
- Analyze goal achievement

Goal Programming Concepts
--------------------------

What Are Goals?
~~~~~~~~~~~~~~~

A **goal** is a soft constraint that you'd like to achieve but can deviate from:

.. code-block:: text

   # Traditional hard constraint
   production >= demand  # Must be satisfied

   # Goal constraint
   production ≈ demand_target  # Try to achieve, but can deviate
   # Creates two deviation variables:
   #   - positive deviation (over-achievement)
   #   - negative deviation (under-achievement)

Deviation Variables
~~~~~~~~~~~~~~~~~~~

Each goal creates two deviation variables:

- **Positive deviation** (``pos``): Amount by which goal is exceeded
- **Negative deviation** (neg``): Amount by which goal is under-achieved

.. code-block:: python

   # Example: demand_target = 1000
   # If production = 1100:
   #   pos = 100 (over-production)
   #   neg = 0 (no under-production)

   # If production = 900:
   #   pos = 0 (no over-production)
   #   neg = 100 (under-production)

Accessing Goal Deviations
--------------------------

Get Deviations
~~~~~~~~~~~~~~

.. code-block:: python

   # Get deviations for a goal
   deviations = solution.get_goal_deviations("production_target")

   if deviations:
       pos_dev = deviations["pos"]  # Over-achievement
       neg_dev = deviations["neg"]  # Under-achievement

       print(f"Positive deviation: {pos_dev}")
       print(f"Negative deviation: {neg_dev}")
   else:
       print("Goal 'production_target' not found")

Return Value
~~~~~~~~~~~~

The ``get_goal_deviations()`` method returns a dictionary:

.. code-block:: python

   {
       "pos": Union[float, Dict[Any, float]],
       "neg": Union[float, Dict[Any, float]]
   }

For **scalar goals**:

.. code-block:: python

   deviations = solution.get_goal_deviations("total_cost_target")
   # {'pos': 0.0, 'neg': 150.5}

For **indexed goals**:

.. code-block:: python

   deviations = solution.get_goal_deviations("demand_target")
   # {
   #     'pos': {'product_A': 10.0, 'product_B': 0.0},
   #     'neg': {'product_A': 0.0, 'product_B': 5.0}
   # }

Checking Goal Satisfaction
---------------------------

is_goal_satisfied()
~~~~~~~~~~~~~~~~~~~

Check if a goal is achieved within tolerance:

.. code-block:: python

   # Check with default tolerance (1e-6)
   if solution.is_goal_satisfied("production_target"):
       print("Production target achieved!")

   # Check with custom tolerance
   if solution.is_goal_satisfied("quality_target", tolerance=0.01):
       print("Quality target achieved (within 1% tolerance)")

Return Values
~~~~~~~~~~~~~

- ``True``: Goal is satisfied (both deviations within tolerance)
- ``False``: Goal is not satisfied
- ``None``: Goal not found in solution

.. code-block:: python

   satisfied = solution.is_goal_satisfied("demand_target")

   if satisfied is True:
       print("Goal achieved")
   elif satisfied is False:
       print("Goal not achieved")
   else:
       print("Goal not found in solution")

Total Deviation
~~~~~~~~~~~~~~~

Get the sum of absolute deviations:

.. code-block:: python

   total_dev = solution.get_total_deviation("production_target")

   if total_dev is not None:
       print(f"Total deviation: {total_dev:.2f}")
   else:
       print("Goal not found")

**Calculation**:

.. code-block:: python

   # For scalar goals
   total_deviation = abs(pos_dev) + abs(neg_dev)

   # For indexed goals
   total_deviation = sum(abs(v) for v in pos_dev.values()) + \\
                     sum(abs(v) for v in neg_dev.values())

Working with Goal Solutions
----------------------------

Analyzing Goal Achievement
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def analyze_goal_achievement(solution, goal_names):
       """Analyze which goals are achieved."""

       print("Goal Achievement Analysis")
       print(f"{'Goal':<30} {'Satisfied':<12} {'Total Deviation'}")
       print("-" * 70)

       satisfied_count = 0

       for goal_name in goal_names:
           satisfied = solution.is_goal_satisfied(goal_name)
           total_dev = solution.get_total_deviation(goal_name)

           if satisfied:
               satisfied_count += 1
               status = "✓ Yes"
           else:
               status = "✗ No"

           dev_str = f"{total_dev:.2f}" if total_dev else "N/A"
           print(f"{goal_name:<30} {status:<12} {dev_str}")

       print(f"\nGoals achieved: {satisfied_count}/{len(goal_names)}")

Prioritizing Unmet Goals
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def prioritize_unmet_goals(solution, goals):
       """Rank goals by deviation for follow-up action."""

       unmet_goals = []

       for goal_name in goals:
           if not solution.is_goal_satisfied(goal_name):
               total_dev = solution.get_total_deviation(goal_name)
               if total_dev:
                   unmet_goals.append((goal_name, total_dev))

       # Sort by deviation (largest first)
       unmet_goals.sort(key=lambda x: x[1], reverse=True)

       print("Unmet Goals (prioritized by deviation):")
       for goal_name, deviation in unmet_goals:
           print(f"  {goal_name}: {deviation:.2f}")

           # Show breakdown
           deviations = solution.get_goal_deviations(goal_name)
           if deviations:
               print(f"    Positive: {deviations['pos']}")
               print(f"    Negative: {deviations['neg']}")

Deviation Breakdown
~~~~~~~~~~~~~~~~~~~

For indexed goals, analyze deviations by index:

.. code-block:: python

   def analyze_indexed_goal(solution, goal_name):
       """Detailed analysis of indexed goal deviations."""

       deviations = solution.get_goal_deviations(goal_name)

       if not deviations:
           print(f"Goal '{goal_name}' not found")
           return

       pos_dev = deviations["pos"]
       neg_dev = deviations["neg"]

       # Check if indexed
       if isinstance(pos_dev, dict):
           print(f"Goal: {goal_name} (indexed)")
           print(f"\n{'Index':<20} {'Pos Deviation':<18} {'Neg Deviation':<18} {'Status'}")
           print("-" * 80)

           all_keys = set(pos_dev.keys()) | set(neg_dev.keys())

           for key in sorted(all_keys):
               pos = pos_dev.get(key, 0)
               neg = neg_dev.get(key, 0)

               if abs(pos) < 1e-6 and abs(neg) < 1e-6:
                   status = "Satisfied"
               elif pos > 1e-6:
                   status = f"Over by {pos:.2f}"
               else:
                   status = f"Under by {neg:.2f}"

               print(f"{str(key):<20} {pos:<18.2f} {neg:<18.2f} {status}")
       else:
           # Scalar goal
           print(f"Goal: {goal_name} (scalar)")
           print(f"Positive deviation: {pos_dev:.2f}")
           print(f"Negative deviation: {neg_dev:.2f}")

Solution Summary with Goals
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``summary()`` method includes goal information:

.. code-block:: python

   print(solution.summary())

Output::

   Status: optimal
   Objective: 12345.678900
   Solve time: 0.123s
   Non-zero variables: 42/100

   Goal Constraints: 5
   Goals Satisfied: 3/5

Example Workflows
-----------------

Production Planning with Goals
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXModel, LXVariable, LXConstraint

   # Define variables
   production = LXVariable[Product, float]("production").from_data(products)

   # Define goals
   demand_goal = (
       LXConstraint[Product]("demand_goal")
       .expression(...)
       .eq()
       .rhs(lambda p: p.demand_target)
       .as_goal(priority=1)  # Higher priority
       .from_data(products)
   )

   quality_goal = (
       LXConstraint("quality_goal")
       .expression(...)
       .ge()
       .rhs(0.95)
       .as_goal(priority=2)  # Lower priority
   )

   # Build and solve
   model = LXModel("production_with_goals")
   model.add_variable(production)
   model.add_constraint(demand_goal)
   model.add_constraint(quality_goal)

   solution = optimizer.solve(model)

   # Analyze results
   if solution.is_optimal():
       print("=== Goal Achievement ===")

       # Check demand goals
       if solution.is_goal_satisfied("demand_goal"):
           print("✓ All demand targets met")
       else:
           print("✗ Some demand targets missed")
           analyze_indexed_goal(solution, "demand_goal")

       # Check quality goal
       if solution.is_goal_satisfied("quality_goal"):
           print("✓ Quality target met")
       else:
           deviations = solution.get_goal_deviations("quality_goal")
           if deviations["neg"] > 0:
               print(f"✗ Quality {deviations['neg']:.2%} below target")

Multi-Objective Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def solve_multi_objective(products, priorities):
       """Solve with multiple conflicting objectives."""

       # Goals with different priorities
       goals = {
           "maximize_profit": {
               "priority": 1,
               "weight": 1.0,
               "type": "maximize"
           },
           "minimize_waste": {
               "priority": 2,
               "weight": 0.5,
               "type": "minimize"
           },
           "meet_demand": {
               "priority": 1,
               "weight": 1.0,
               "type": "target"
           }
       }

       # Build model with goals...
       solution = optimizer.solve(model)

       # Analyze trade-offs
       print("=== Multi-Objective Results ===")
       print(f"Objective value: {solution.objective_value:.2f}")
       print()

       for goal_name, config in goals.items():
           satisfied = solution.is_goal_satisfied(goal_name)
           total_dev = solution.get_total_deviation(goal_name)

           status = "✓" if satisfied else "✗"
           print(f"{status} {goal_name} (priority {config['priority']})")

           if not satisfied and total_dev:
               print(f"   Deviation: {total_dev:.2f}")
               print(f"   Weight: {config['weight']}")
               print(f"   Weighted penalty: {total_dev * config['weight']:.2f}")

Sequential Goal Programming
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def sequential_goal_programming(products, goal_priorities):
       """Solve goals sequentially by priority."""

       # Priority levels (1 = highest)
       priorities = sorted(set(goal_priorities.values()))

       solutions_by_priority = {}

       for priority in priorities:
           print(f"\\n=== Solving Priority {priority} Goals ===")

           # Get goals at this priority
           current_goals = [
               name for name, p in goal_priorities.items()
               if p == priority
           ]

           # Build and solve model for this priority
           model = build_model_with_goals(current_goals)
           solution = optimizer.solve(model)

           solutions_by_priority[priority] = solution

           # Report results
           for goal_name in current_goals:
               satisfied = solution.is_goal_satisfied(goal_name)
               status = "✓" if satisfied else "✗"
               print(f"{status} {goal_name}")

               if not satisfied:
                   total_dev = solution.get_total_deviation(goal_name)
                   print(f"   Deviation: {total_dev:.2f}")

       return solutions_by_priority

Handling Deviation Types
-------------------------

Asymmetric Goals
~~~~~~~~~~~~~~~~

Sometimes you only care about one type of deviation:

.. code-block:: python

   def check_one_sided_goal(solution, goal_name, direction="under"):
       """Check goals where only one direction matters."""

       deviations = solution.get_goal_deviations(goal_name)

       if not deviations:
           return None

       if direction == "under":
           # Only care about under-achievement (negative deviation)
           total_under = deviations["neg"]
           if isinstance(total_under, dict):
               total_under = sum(total_under.values())

           if total_under < 1e-6:
               print(f"✓ {goal_name}: No under-achievement")
           else:
               print(f"✗ {goal_name}: Under by {total_under:.2f}")

       elif direction == "over":
           # Only care about over-achievement (positive deviation)
           total_over = deviations["pos"]
           if isinstance(total_over, dict):
               total_over = sum(total_over.values())

           if total_over < 1e-6:
               print(f"✓ {goal_name}: No over-achievement")
           else:
               print(f"✗ {goal_name}: Over by {total_over:.2f}")

Weighted Deviations
~~~~~~~~~~~~~~~~~~~

Calculate weighted deviation for cost analysis:

.. code-block:: python

   def calculate_weighted_deviation(solution, goal_name, pos_weight, neg_weight):
       """Calculate deviation with asymmetric weights."""

       deviations = solution.get_goal_deviations(goal_name)

       if not deviations:
           return None

       pos_dev = deviations["pos"]
       neg_dev = deviations["neg"]

       # Handle scalar vs indexed
       if isinstance(pos_dev, dict):
           total_pos = sum(pos_dev.values())
           total_neg = sum(neg_dev.values())
       else:
           total_pos = pos_dev
           total_neg = neg_dev

       weighted_total = total_pos * pos_weight + total_neg * neg_weight

       print(f"{goal_name}:")
       print(f"  Positive deviation: {total_pos:.2f} × {pos_weight} = {total_pos * pos_weight:.2f}")
       print(f"  Negative deviation: {total_neg:.2f} × {neg_weight} = {total_neg * neg_weight:.2f}")
       print(f"  Total weighted deviation: {weighted_total:.2f}")

       return weighted_total

Best Practices
--------------

1. **Always Check Goal Existence**

   .. code-block:: python

      deviations = solution.get_goal_deviations("my_goal")
      if deviations is None:
          print("Goal not found")
          return

2. **Use Appropriate Tolerance**

   .. code-block:: python

      # For percentage goals
      satisfied = solution.is_goal_satisfied("quality", tolerance=0.01)  # 1%

      # For absolute goals
      satisfied = solution.is_goal_satisfied("demand", tolerance=1.0)  # 1 unit

3. **Handle Both Scalar and Indexed Goals**

   .. code-block:: python

      deviations = solution.get_goal_deviations("my_goal")
      pos_dev = deviations["pos"]

      # Check if indexed
      if isinstance(pos_dev, dict):
          total = sum(pos_dev.values())
      else:
          total = pos_dev

4. **Report Goal Achievement Clearly**

   .. code-block:: python

      def report_goals(solution, goal_names):
          achieved = sum(1 for g in goal_names if solution.is_goal_satisfied(g))
          total = len(goal_names)
          pct = (achieved / total) * 100

          print(f"Goals Achieved: {achieved}/{total} ({pct:.1f}%)")

Common Patterns
---------------

Dashboard Summary
~~~~~~~~~~~~~~~~~

.. code-block:: python

   def goal_programming_dashboard(solution, goals_config):
       """Create dashboard summary of goal achievement."""

       print("=" * 80)
       print("GOAL PROGRAMMING DASHBOARD".center(80))
       print("=" * 80)

       by_priority = {}
       for goal_name, config in goals_config.items():
           priority = config.get("priority", 1)
           if priority not in by_priority:
               by_priority[priority] = []
           by_priority[priority].append(goal_name)

       for priority in sorted(by_priority.keys()):
           print(f"\\nPriority {priority} Goals:")
           print("-" * 80)

           for goal_name in by_priority[priority]:
               satisfied = solution.is_goal_satisfied(goal_name)
               total_dev = solution.get_total_deviation(goal_name)

               status_icon = "✓" if satisfied else "✗"
               status_text = "Satisfied" if satisfied else f"Deviation: {total_dev:.2f}"

               print(f"{status_icon} {goal_name:<40} {status_text}")

       print("=" * 80)

Next Steps
----------

- :doc:`accessing-solutions` - Learn about accessing solution values
- :doc:`sensitivity-analysis` - Perform sensitivity analysis
- :doc:`mapping` - Map solutions to ORM models
- :doc:`/api/solution/index` - Full API reference
