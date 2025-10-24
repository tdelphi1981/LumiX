Sequential Goal Programming
===========================

Learn how to use sequential (lexicographic) goal programming for strict priority enforcement.

Overview
--------

**Sequential goal programming** (also called **lexicographic goal programming**) optimizes
goals one priority level at a time in strict order:

1. Optimize priority 1 goals, record optimal deviation values
2. Fix priority 1 deviations to optimal values
3. Optimize priority 2 goals (subject to fixed priority 1)
4. Repeat for all priorities

This guarantees that higher priority goals are **never compromised** for lower priorities.

When to Use
-----------

Sequential goal programming is ideal when:

- **Strict priority enforcement** is required (no trade-offs across priorities)
- Higher priority goals must be optimized first, no exceptions
- You need true lexicographic optimization
- You can afford multiple solve iterations

**Use weighted mode instead when**:

- Single solve is preferred (computational efficiency)
- Some flexibility across priorities is acceptable
- Priorities serve as general guidance rather than strict rules

How It Works
------------

Sequential Solving Process
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. mermaid::

   graph TD
       A[Priority 1 Goals] --> B[Solve P1]
       B --> C[Record P1 Optimal Deviations]
       C --> D[Fix P1 Deviations]
       D --> E[Priority 2 Goals]
       E --> F[Solve P2]
       F --> G[Record P2 Optimal Deviations]
       G --> H[Fix P2 Deviations]
       H --> I[Priority 3 Goals]
       I --> J[Solve P3]
       J --> K[Final Solution]

       style A fill:#e1f5ff
       style E fill:#fff4e1
       style I fill:#ffe1e1
       style K fill:#e1ffe1

**Key property**: Lower priorities **cannot degrade** higher priority solutions.

Mathematical Formulation
~~~~~~~~~~~~~~~~~~~~~~~~

For priorities P1, P2, P3, ...:

**Step 1**: Solve for P1

.. math::

   \min \sum_{g \in G_1} w_g d_g

   \text{subject to: model constraints}

**Step 2**: Fix P1 deviations, solve for P2

.. math::

   \min \sum_{g \in G_2} w_g d_g

   \text{subject to:}

   \quad \text{model constraints}

   \quad d_g^{P1} = d_g^{P1*} \quad \forall g \in G_1

**Step 3**: Fix P1 and P2, solve for P3, and so on.

Basic Usage
-----------

Setting Sequential Mode
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXModel, LXVariable, LXConstraint, LXOptimizer

   # Define variables and goals as usual
   production = LXVariable[Product, float]("production").from_data(products)

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

   # Build model
   model = (
       LXModel("production")
       .add_variable(production)
       .add_constraint(demand_goal)
       .add_constraint(quality_goal)
   )

   # Set sequential mode
   model.set_goal_mode("sequential")

   # Solve
   optimizer = LXOptimizer().use_solver("gurobi")
   solution = optimizer.solve(model)

   # The solver will:
   # 1. First optimize demand (priority 1)
   # 2. Then optimize quality without degrading demand (priority 2)

Using the Solver Directly
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.goal_programming import LXGoalProgrammingSolver

   # Set sequential mode
   model.set_goal_mode("sequential")

   # Get relaxed constraints (internal model state)
   relaxed_constraints = model._relaxed_constraints

   # Create sequential solver
   gp_solver = LXGoalProgrammingSolver(optimizer)

   # Solve sequentially
   solution = gp_solver.solve_sequential(
       model=model,
       relaxed_constraints=relaxed_constraints
   )

Practical Examples
------------------

Resource Allocation with Strict Priorities
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dataclasses import dataclass
   from typing import List

   @dataclass
   class Department:
       id: str
       critical: bool
       min_budget: float
       target_budget: float

   @dataclass
   class Project:
       id: str
       department_id: str
       value: float

   departments = [
       Department("safety", critical=True, min_budget=100, target_budget=150),
       Department("research", critical=False, min_budget=50, target_budget=100),
       Department("marketing", critical=False, min_budget=30, target_budget=80),
   ]

   # Variables
   budget_allocation = (
       LXVariable[Department, float]("budget")
       .continuous()
       .bounds(lower=0)
       .indexed_by(lambda d: d.id)
       .from_data(departments)
   )

   # Priority 1: Critical departments get at least minimum budget
   critical_min = (
       LXConstraint[Department]("critical_minimum")
       .expression(
           LXLinearExpression()
           .add_term(budget_allocation, coeff=1.0)
       )
       .ge()
       .rhs(lambda d: d.min_budget)
       .where(lambda d: d.critical)  # Only critical departments
       .as_goal(priority=1, weight=10.0)  # High weight
       .from_data(departments)
   )

   # Priority 2: All departments meet minimum
   all_minimum = (
       LXConstraint[Department]("all_minimum")
       .expression(
           LXLinearExpression()
           .add_term(budget_allocation, coeff=1.0)
       )
       .ge()
       .rhs(lambda d: d.min_budget)
       .as_goal(priority=2, weight=5.0)
       .from_data(departments)
   )

   # Priority 3: Approach target budgets
   target_goals = (
       LXConstraint[Department]("targets")
       .expression(
           LXLinearExpression()
           .add_term(budget_allocation, coeff=1.0)
       )
       .ge()
       .rhs(lambda d: d.target_budget)
       .as_goal(priority=3, weight=1.0)
       .from_data(departments)
   )

   # Hard constraint: Total budget limit
   total_budget = (
       LXConstraint("total")
       .expression(
           LXLinearExpression()
           .add_term(budget_allocation, coeff=1.0)
       )
       .le()
       .rhs(300)  # Total available budget
   )

   # Build model with sequential mode
   model = (
       LXModel("budget_allocation")
       .add_variable(budget_allocation)
       .add_constraint(critical_min)
       .add_constraint(all_minimum)
       .add_constraint(target_goals)
       .add_constraint(total_budget)
   )

   model.set_goal_mode("sequential")

   # Solve
   solution = optimizer.solve(model)

   # Analyze results by priority
   print("=" * 80)
   print("BUDGET ALLOCATION RESULTS (Sequential)")
   print("=" * 80)

   print("\nAllocations:")
   for dept_id, amount in solution.get_mapped(budget_allocation).items():
       dept = next(d for d in departments if d.id == dept_id)
       status = "CRITICAL" if dept.critical else "Regular"
       print(f"{dept_id} ({status}): ${amount:.2f} / ${dept.target_budget:.2f}")

   print("\n" + "=" * 80)
   print("Goal Achievement by Priority")
   print("=" * 80)

   goals = [
       ("critical_minimum", "Priority 1: Critical Dept Minimums", 1),
       ("all_minimum", "Priority 2: All Dept Minimums", 2),
       ("targets", "Priority 3: Target Budgets", 3),
   ]

   for goal_name, description, priority in goals:
       satisfied = solution.is_goal_satisfied(goal_name)
       print(f"\n{description}")
       print(f"Status: {'✓ ACHIEVED' if satisfied else '✗ Not Fully Achieved'}")

       if not satisfied:
           total_dev = solution.get_total_deviation(goal_name)
           print(f"Total Deviation: ${total_dev:.2f}")

Production Scheduling with Hierarchical Goals
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Priority 1: Safety constraints (must be met)
   safety_goal = (
       LXConstraint[Machine]("safety")
       .expression(safety_expr)
       .le()
       .rhs(lambda m: m.max_safe_hours)
       .as_goal(priority=1, weight=100.0)
       .from_data(machines)
   )

   # Priority 2: Customer commitments (high importance)
   commitment_goal = (
       LXConstraint[Order]("commitments")
       .expression(production_expr)
       .ge()
       .rhs(lambda o: o.committed_quantity)
       .where(lambda o: o.is_committed)
       .as_goal(priority=2, weight=10.0)
       .from_data(orders)
   )

   # Priority 3: Additional demand (nice to have)
   additional_demand = (
       LXConstraint[Order]("additional")
       .expression(production_expr)
       .ge()
       .rhs(lambda o: o.requested_quantity)
       .where(lambda o: not o.is_committed)
       .as_goal(priority=3, weight=1.0)
       .from_data(orders)
   )

   model = (
       LXModel("hierarchical_production")
       .add_variable(production)
       .add_constraint(safety_goal)
       .add_constraint(commitment_goal)
       .add_constraint(additional_demand)
   )

   model.set_goal_mode("sequential")
   solution = optimizer.solve(model)

   # With sequential mode:
   # - Safety is optimized first (may result in zero deviations)
   # - Then commitments are optimized without degrading safety
   # - Finally additional demand is satisfied if possible

Weighted vs. Sequential Comparison
-----------------------------------

Same Problem, Different Modes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Define model with multi-priority goals
   model = LXModel("comparison")
   # ... add variables and goals with priorities 1, 2, 3 ...

   # Weighted mode (default)
   solution_weighted = optimizer.solve(model)

   # Sequential mode
   model.set_goal_mode("sequential")
   solution_sequential = optimizer.solve(model)

   # Compare results
   print("Weighted Mode:")
   for goal in ["p1_goal", "p2_goal", "p3_goal"]:
       dev = solution_weighted.get_total_deviation(goal)
       print(f"  {goal}: {dev:.2f}")

   print("\nSequential Mode:")
   for goal in ["p1_goal", "p2_goal", "p3_goal"]:
       dev = solution_sequential.get_total_deviation(goal)
       print(f"  {goal}: {dev:.2f}")

   # Sequential mode guarantees:
   # - P1 goal has best possible deviations
   # - P2 goal is optimized without degrading P1
   # - P3 goal is optimized without degrading P1 or P2

Expected Differences
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - Aspect
     - Weighted Mode
     - Sequential Mode
   * - Number of solves
     - 1
     - N (number of priorities)
   * - Priority enforcement
     - Approximate (via weights)
     - Strict (lexicographic)
   * - Computational cost
     - Lower
     - Higher
   * - Solution guarantee
     - Single Pareto-optimal
     - Lexicographically optimal
   * - Trade-offs
     - Across priorities possible
     - Only within same priority

Advanced Techniques
-------------------

Custom Priority Ordering
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Sometimes you want to solve priorities in custom order
   from lumix.goal_programming import build_sequential_objectives

   # Build objectives manually
   sequential_objs = build_sequential_objectives(relaxed_constraints)

   # sequential_objs is [(priority, expression), ...]
   # Solve in custom order if needed
   for priority, obj_expr in sorted(sequential_objs, key=lambda x: x[0]):
       print(f"Solving priority {priority}")
       # Custom solving logic here

Monitoring Progress
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Track how each priority level performs
   gp_solver = LXGoalProgrammingSolver(optimizer)

   # Wrap solve method to monitor
   original_solve = gp_solver.optimizer.solve

   def monitored_solve(model):
       print(f"Solving: {model.name}")
       result = original_solve(model)
       print(f"  Objective: {result.objective_value:.2f}")
       print(f"  Status: {result.status}")
       return result

   gp_solver.optimizer.solve = monitored_solve

   solution = gp_solver.solve_sequential(model, relaxed_constraints)

Partial Sequential
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Group some priorities together, separate others
   # Example: P1 strict, P2+P3 weighted

   # P1 goals
   critical_goals = [g for g in goals if g.priority == 1]

   # P2+P3 goals (will be solved together with weights)
   lower_goals = [g for g in goals if g.priority >= 2]

   # Solve P1 first
   model_p1 = build_model_with_goals(critical_goals)
   solution_p1 = optimizer.solve(model_p1)

   # Fix P1 deviations, solve P2+P3 with weights
   # (implementation would require manual deviation fixing)

Best Practices
--------------

1. **Limit Number of Priorities**

   .. code-block:: python

      # Good: 2-4 priority levels
      safety.as_goal(priority=1, weight=1.0)
      quality.as_goal(priority=2, weight=1.0)
      cost.as_goal(priority=3, weight=1.0)

      # Avoid: Too many levels (computational cost)
      # More than 5 priorities often indicates overcomplication

2. **Use Sequential Only When Necessary**

   .. code-block:: python

      # Weighted mode is usually sufficient and much faster
      # Use sequential only when strict priority enforcement needed

      # Example: When higher priorities might not achieve zero deviation
      # and you want to ensure lower priorities don't interfere

3. **Monitor Solve Time**

   .. code-block:: python

      import time

      start = time.time()
      solution = optimizer.solve(model)
      end = time.time()

      print(f"Solve time: {end - start:.2f}s")

      # If sequential mode is too slow:
      # - Reduce number of priority levels
      # - Use weighted mode instead
      # - Simplify model

4. **Check Intermediate Solutions**

   .. code-block:: python

      # In sequential mode, check if higher priorities achieved zero deviation
      solution = optimizer.solve(model)

      # Priority 1 should ideally have zero (or very small) deviations
      p1_dev = solution.get_total_deviation("priority_1_goal")

      if p1_dev > 1e-3:
          print(f"Warning: Priority 1 has non-zero deviation: {p1_dev}")
          # This indicates P1 goals may be conflicting or infeasible

Troubleshooting
---------------

Slow Performance
~~~~~~~~~~~~~~~~

**Issue**: Sequential mode takes too long.

**Solutions**:

1. Reduce number of priorities
2. Use weighted mode instead
3. Combine some priority levels
4. Simplify model structure

.. code-block:: python

   # Before: 5 priorities (5 solves)
   goals = [
       (goal1, 1), (goal2, 2), (goal3, 3), (goal4, 4), (goal5, 5)
   ]

   # After: 3 priorities (3 solves)
   goals = [
       (goal1, 1),           # Critical
       (goal2, 2), (goal3, 2),  # Important (combined)
       (goal4, 3), (goal5, 3)   # Nice-to-have (combined)
   ]

Priority 1 Not Optimal
~~~~~~~~~~~~~~~~~~~~~~

**Issue**: Priority 1 goals have non-zero deviations.

**Cause**: Priority 1 goals are conflicting or constrained by hard constraints.

**Solution**: Check hard constraints and goal feasibility:

.. code-block:: python

   # Temporarily convert all hard constraints to goals to check feasibility
   # Then identify which hard constraints are causing issues

Unexpected Results
~~~~~~~~~~~~~~~~~~

**Issue**: Sequential mode gives unexpected results compared to weighted.

**Debugging**:

.. code-block:: python

   # Compare both modes
   model.set_goal_mode("weighted")
   sol_weighted = optimizer.solve(model)

   model.set_goal_mode("sequential")
   sol_sequential = optimizer.solve(model)

   # Analyze differences
   for goal in goal_names:
       dev_w = sol_weighted.get_total_deviation(goal)
       dev_s = sol_sequential.get_total_deviation(goal)

       print(f"{goal}:")
       print(f"  Weighted: {dev_w:.2f}")
       print(f"  Sequential: {dev_s:.2f}")
       print(f"  Difference: {abs(dev_w - dev_s):.2f}")

Next Steps
----------

- :doc:`weighted-mode` - Compare with weighted goal programming
- :doc:`relaxation` - Understand constraint relaxation mechanics
- :doc:`objective-building` - Learn objective construction details
- :doc:`/api/goal_programming/index` - Full API reference
- :doc:`/user-guide/solution/goal-programming` - Working with solutions
