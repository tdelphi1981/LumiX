Goal Programming
================

This guide covers LumiX's goal programming capabilities for multi-objective optimization.

Introduction
------------

**Goal programming** extends traditional optimization by allowing you to define multiple
objectives as **goals** with target values. Instead of requiring strict constraint
satisfaction, goal programming allows constraints to be violated with controlled penalties.

This is ideal when you have conflicting objectives or when hard constraints would make
the problem infeasible. Goal programming finds the "best compromise" solution.

Philosophy
----------

Traditional vs. Goal Programming
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Traditional Optimization**:

.. code-block:: text

   Minimize cost
   Subject to:
       production >= demand  (MUST be satisfied)
       quality >= 0.95       (MUST be satisfied)
       overtime <= 40        (MUST be satisfied)

   Problem: May be infeasible if constraints conflict!

**Goal Programming**:

.. code-block:: text

   Minimize: deviations from goals
   Goals:
       production ≈ demand_target    (try to achieve, with priority 1)
       quality ≈ 0.95                (try to achieve, with priority 2)
       overtime ≈ 40                 (try to achieve, with priority 3)

   Result: Always feasible, finds best compromise!

Key Concepts
~~~~~~~~~~~~

1. **Soft Constraints (Goals)**: Can be violated with a penalty
2. **Deviation Variables**: Measure how much a goal is over/under achieved
3. **Priorities**: Order goals by importance (1 = highest)
4. **Weights**: Relative importance within same priority level
5. **Solving Modes**: Weighted (single solve) or Sequential (lexicographic)

When to Use Goal Programming
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Goal programming is ideal for:

- **Conflicting objectives**: Multiple objectives that cannot all be optimized simultaneously
- **Target-based planning**: When you have specific target values to achieve
- **Feasibility preservation**: When hard constraints might make the problem infeasible
- **Hierarchical objectives**: When objectives have different priority levels
- **What-if analysis**: Exploring trade-offs between different goals

Quick Example
-------------

Basic Goal Programming
~~~~~~~~~~~~~~~~~~~~~~~

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

   # Define a GOAL constraint (soft constraint)
   demand_goal = (
       LXConstraint[Product]("demand_goal")
       .expression(
           LXLinearExpression()
           .add_term(production, coeff=1.0)
       )
       .ge()  # Target: production >= demand
       .rhs(lambda p: p.demand_target)
       .as_goal(priority=1, weight=1.0)  # Mark as goal!
       .from_data(products)
   )

   # Build model
   model = (
       LXModel("production_planning")
       .add_variable(production)
       .add_constraint(demand_goal)
       # Can add more goals and hard constraints
   )

   # Solve
   optimizer = LXOptimizer().use_solver("gurobi")
   solution = optimizer.solve(model)

   # Check goal achievement
   if solution.is_goal_satisfied("demand_goal"):
       print("Demand goal achieved!")
   else:
       deviations = solution.get_goal_deviations("demand_goal")
       print(f"Under-achieved by: {deviations['neg']}")
       print(f"Over-achieved by: {deviations['pos']}")

How It Works
------------

Automatic Transformation
~~~~~~~~~~~~~~~~~~~~~~~~~

When you mark a constraint as a goal with ``.as_goal()``, LumiX automatically:

1. **Creates deviation variables**: Positive and negative deviations for each goal instance
2. **Relaxes the constraint**: Converts it to an equality with deviations
3. **Builds the objective**: Minimizes undesired deviations based on constraint type
4. **Applies priorities**: Uses exponential weights for priority levels

.. mermaid::

   graph LR
       A[Hard Constraint] -->|.as_goal| B[Goal Constraint]
       B --> C[Constraint Relaxation]
       C --> D[Deviation Variables]
       D --> E[Objective Function]
       E --> F[Solve]
       F --> G[Solution + Deviations]

       style A fill:#e1f5ff
       style B fill:#fff4e1
       style C fill:#ffe1e1
       style D fill:#e1ffe1
       style E fill:#f0e1ff
       style F fill:#e8f4f8
       style G fill:#ffe8e8

Deviation Variables
~~~~~~~~~~~~~~~~~~~

Each goal creates two deviation variables per instance:

- **Positive deviation (pos)**: Amount by which the goal is over-achieved
- **Negative deviation (neg)**: Amount by which the goal is under-achieved

The relationship is: ``expr + neg_dev - pos_dev = rhs``

**For different constraint types**:

.. code-block:: text

   LE (expr <= rhs):  Minimize pos_dev (over-achievement bad)
   GE (expr >= rhs):  Minimize neg_dev (under-achievement bad)
   EQ (expr == rhs):  Minimize both (any deviation bad)

**Example**:

.. code-block:: python

   # Goal: production >= 100 units
   # If actual production = 110:
   #   pos_dev = 10 (over-production)
   #   neg_dev = 0  (no under-production)

   # If actual production = 90:
   #   pos_dev = 0   (no over-production)
   #   neg_dev = 10  (under-production)

Components Overview
-------------------

The goal programming module consists of four main components:

.. mermaid::

   graph TD
       A[LXConstraint.as_goal] --> B[LXGoalMetadata]
       B --> C[Constraint Relaxation]
       C --> D[RelaxedConstraint]
       D --> E[Deviation Variables]
       D --> F[Goal Instances]
       E --> G[Objective Builder]
       F --> G
       G --> H[LXGoalProgrammingSolver]
       H --> I[Solution with Deviations]

       style A fill:#e1f5ff
       style B fill:#fff4e1
       style C fill:#ffe1e1
       style D fill:#e1ffe1
       style E fill:#f0e1ff
       style F fill:#e8f4f8
       style G fill:#ffe8e8
       style H fill:#e8ffe8
       style I fill:#f0e8ff

1. **Goal Metadata** (:class:`~lumix.goal_programming.goal.LXGoalMetadata`): Stores priority, weight, and constraint sense
2. **Relaxation** (:class:`~lumix.goal_programming.relaxation.RelaxedConstraint`): Transforms hard constraints to soft constraints with deviations
3. **Objective Building** (:mod:`lumix.goal_programming.objective_builder`): Constructs weighted or sequential objectives
4. **Solver** (:class:`~lumix.goal_programming.solver.LXGoalProgrammingSolver`): Orchestrates weighted or sequential solving

Detailed Guides
---------------

.. toctree::
   :maxdepth: 2

   weighted-mode
   sequential-mode
   relaxation
   objective-building

Topics Covered
--------------

Weighted Goal Programming
~~~~~~~~~~~~~~~~~~~~~~~~~~

Single-solve approach where all goals are combined into one objective function with
exponentially scaled priorities. See :doc:`weighted-mode` for details.

**Use when**: Goals have clear priority hierarchy and you want a single optimal solution.

Sequential Goal Programming
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Multi-solve approach where goals are optimized one priority level at a time. Higher
priority goals are optimized first, then their optimal values are fixed while optimizing
lower priorities. See :doc:`sequential-mode` for details.

**Use when**: Priorities must be strictly enforced (lexicographic optimization).

Constraint Relaxation
~~~~~~~~~~~~~~~~~~~~~

Understanding how hard constraints are transformed into soft constraints with deviation
variables. See :doc:`relaxation` for details.

**Covers**: Deviation variable creation, goal instances, relaxation mathematics.

Objective Building
~~~~~~~~~~~~~~~~~~

How goal programming objectives are constructed from relaxed constraints. See
:doc:`objective-building` for details.

**Covers**: Weighted objectives, sequential objectives, combining with custom objectives.

Best Practices
--------------

1. **Choose Appropriate Priorities**

   .. code-block:: python

      # Good: Clear hierarchy
      demand_goal.as_goal(priority=1, weight=1.0)    # Must meet demand
      quality_goal.as_goal(priority=2, weight=1.0)   # Then maximize quality
      cost_goal.as_goal(priority=3, weight=1.0)      # Then minimize cost

      # Bad: Everything same priority defeats the purpose
      goal1.as_goal(priority=1, weight=1.0)
      goal2.as_goal(priority=1, weight=1.0)  # All priority 1 = single objective

2. **Use Weights Within Priority Levels**

   .. code-block:: python

      # Within same priority, use weights for relative importance
      product_a_goal.as_goal(priority=1, weight=2.0)  # Twice as important
      product_b_goal.as_goal(priority=1, weight=1.0)

3. **Mix Hard and Soft Constraints**

   .. code-block:: python

      # Hard constraint (must be satisfied)
      capacity = (
          LXConstraint("capacity")
          .expression(production_expr)
          .le()
          .rhs(max_capacity)
          # No .as_goal() - stays hard constraint
      )

      # Soft constraint (can be violated with penalty)
      demand = (
          LXConstraint[Product]("demand")
          .expression(production_expr)
          .ge()
          .rhs(lambda p: p.demand)
          .as_goal(priority=1, weight=1.0)  # Can deviate
          .from_data(products)
      )

4. **Check Goal Satisfaction in Solutions**

   .. code-block:: python

      solution = optimizer.solve(model)

      # Check which goals were achieved
      for goal_name in ["demand", "quality", "overtime"]:
          if solution.is_goal_satisfied(goal_name):
              print(f"✓ {goal_name} achieved")
          else:
              total_dev = solution.get_total_deviation(goal_name)
              print(f"✗ {goal_name} deviated by {total_dev:.2f}")

Common Patterns
---------------

Production Planning
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Priority 1: Meet customer demand
   demand_goal = (
       LXConstraint[Product]("demand")
       .expression(production_expr)
       .ge()
       .rhs(lambda p: p.demand)
       .as_goal(priority=1, weight=1.0)
       .from_data(products)
   )

   # Priority 2: Maintain quality standards
   quality_goal = (
       LXConstraint("quality")
       .expression(quality_expr)
       .ge()
       .rhs(0.95)
       .as_goal(priority=2, weight=1.0)
   )

   # Priority 3: Minimize overtime
   overtime_goal = (
       LXConstraint("overtime")
       .expression(hours_expr)
       .le()
       .rhs(40)
       .as_goal(priority=3, weight=1.0)
   )

Resource Allocation
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Custom objective: Maximize profit
   profit_objective = (
       LXConstraint("profit")
       .expression(profit_expr)
       .ge()
       .rhs(0)
       .as_goal(priority=0, weight=1.0)  # Priority 0 = custom objective
   )

   # Goal: Distribute resources fairly
   fairness_goal = (
       LXConstraint[Department]("fairness")
       .expression(allocation_expr)
       .eq()  # Want exact target
       .rhs(lambda d: d.target_allocation)
       .as_goal(priority=1, weight=1.0)
       .from_data(departments)
   )

Multi-Objective Portfolio
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Conflicting objectives with different priorities
   return_goal = (
       LXConstraint("return")
       .expression(return_expr)
       .ge()
       .rhs(target_return)
       .as_goal(priority=1, weight=1.0)
   )

   risk_goal = (
       LXConstraint("risk")
       .expression(risk_expr)
       .le()
       .rhs(max_risk)
       .as_goal(priority=1, weight=0.8)  # Slightly less important
   )

   diversity_goal = (
       LXConstraint("diversity")
       .expression(diversity_expr)
       .ge()
       .rhs(min_diversity)
       .as_goal(priority=2, weight=1.0)
   )

Next Steps
----------

- :doc:`weighted-mode` - Learn weighted goal programming (recommended start)
- :doc:`sequential-mode` - Learn sequential goal programming
- :doc:`relaxation` - Understand constraint relaxation mechanics
- :doc:`objective-building` - Learn to build custom goal objectives
- :doc:`/api/goal_programming/index` - Full API reference
- :doc:`/user-guide/solution/goal-programming` - Working with goal programming solutions
