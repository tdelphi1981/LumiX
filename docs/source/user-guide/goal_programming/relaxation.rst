Constraint Relaxation
=====================

Understand how LumiX transforms hard constraints into soft constraints with deviation variables.

Overview
--------

**Constraint relaxation** is the process of converting a hard constraint (must be satisfied)
into a soft constraint (can be violated with a penalty). This is the foundation of goal
programming.

The relaxation creates:

- **Equality constraint** with deviation variables
- **Positive deviation variable** (over-achievement)
- **Negative deviation variable** (under-achievement)
- **Goal instances** that serve as the data source for deviations

Relaxation Mathematics
----------------------

Basic Transformation
~~~~~~~~~~~~~~~~~~~~

A hard constraint is transformed by adding deviation variables:

.. code-block:: text

   Hard Constraint:  expr ≤ rhs

   Relaxed Form:     expr + neg_dev - pos_dev = rhs
                     neg_dev ≥ 0
                     pos_dev ≥ 0

**Interpretation**:

- If ``expr < rhs``: ``neg_dev > 0``, ``pos_dev = 0`` (under-achievement)
- If ``expr > rhs``: ``neg_dev = 0``, ``pos_dev > 0`` (over-achievement)
- If ``expr = rhs``: ``neg_dev = 0``, ``pos_dev = 0`` (goal achieved)

Constraint Types
~~~~~~~~~~~~~~~~

Different constraint senses require different deviation penalties:

**Less-Than-or-Equal (LE: ≤)**:

.. code-block:: text

   Original:  expr ≤ rhs
   Relaxed:   expr + neg_dev - pos_dev = rhs
   Minimize:  pos_dev  (over-achievement is undesired)

   Example: overtime ≤ 40 hours
   - Want to stay under 40 hours
   - Exceeding 40 (pos_dev > 0) is penalized

**Greater-Than-or-Equal (GE: ≥)**:

.. code-block:: text

   Original:  expr ≥ rhs
   Relaxed:   expr + neg_dev - pos_dev = rhs
   Minimize:  neg_dev  (under-achievement is undesired)

   Example: production ≥ 1000 units
   - Want at least 1000 units
   - Producing less (neg_dev > 0) is penalized

**Equality (EQ: =)**:

.. code-block:: text

   Original:  expr = rhs
   Relaxed:   expr + neg_dev - pos_dev = rhs
   Minimize:  pos_dev + neg_dev  (any deviation is undesired)

   Example: budget = 50000
   - Want exactly 50000
   - Both over and under are penalized

Automatic Relaxation
--------------------

Using .as_goal()
~~~~~~~~~~~~~~~~

LumiX automatically relaxes constraints when you use ``.as_goal()``:

.. code-block:: python

   from lumix import LXConstraint
   from lumix.core.expressions import LXLinearExpression

   # Define a hard constraint
   demand_constraint = (
       LXConstraint[Product]("demand")
       .expression(production_expr)
       .ge()
       .rhs(lambda p: p.demand_target)
       .from_data(products)
   )

   # Mark as goal - automatic relaxation happens!
   demand_goal = (
       LXConstraint[Product]("demand")
       .expression(production_expr)
       .ge()
       .rhs(lambda p: p.demand_target)
       .as_goal(priority=1, weight=1.0)  # This triggers relaxation
       .from_data(products)
   )

   # Behind the scenes, LumiX:
   # 1. Creates pos_dev and neg_dev variables
   # 2. Converts to equality: production + neg_dev - pos_dev = demand_target
   # 3. Adds neg_dev to objective (since GE constraint)

What Happens Internally
~~~~~~~~~~~~~~~~~~~~~~~~

.. mermaid::

   graph LR
       A[Original Constraint] -->|as_goal| B[LXGoalMetadata]
       B --> C[relax_constraint]
       C --> D[Create Goal Instances]
       C --> E[Create Deviation Variables]
       C --> F[Build Equality Constraint]
       D --> E
       E --> F
       F --> G[RelaxedConstraint]

       style A fill:#e1f5ff
       style B fill:#fff4e1
       style C fill:#ffe1e1
       style D fill:#e1ffe1
       style E fill:#f0e1ff
       style F fill:#e8f4f8
       style G fill:#ffe8e8

Manual Relaxation
-----------------

Direct API Usage
~~~~~~~~~~~~~~~~

You can manually relax constraints using the relaxation API:

.. code-block:: python

   from lumix.goal_programming import relax_constraint, LXGoalMetadata
   from lumix.core.enums import LXConstraintSense

   # Create goal metadata
   metadata = LXGoalMetadata(
       priority=1,
       weight=1.0,
       constraint_sense=LXConstraintSense.GE
   )

   # Define constraint (not a goal yet)
   demand_constraint = (
       LXConstraint[Product]("demand")
       .expression(production_expr)
       .ge()
       .rhs(lambda p: p.demand_target)
       .from_data(products)
   )

   # Manually relax
   relaxed = relax_constraint(demand_constraint, metadata)

   # Access components
   equality_constraint = relaxed.constraint
   pos_deviation_var = relaxed.pos_deviation
   neg_deviation_var = relaxed.neg_deviation
   goal_instances = relaxed.goal_instances
   metadata_ref = relaxed.goal_metadata

Batch Relaxation
~~~~~~~~~~~~~~~~

Relax multiple constraints at once:

.. code-block:: python

   from lumix.goal_programming import relax_constraints

   constraints = [demand_constraint, quality_constraint, cost_constraint]

   metadata_map = {
       "demand": LXGoalMetadata(priority=1, weight=1.0, constraint_sense=LXConstraintSense.GE),
       "quality": LXGoalMetadata(priority=2, weight=1.0, constraint_sense=LXConstraintSense.GE),
       "cost": LXGoalMetadata(priority=3, weight=0.5, constraint_sense=LXConstraintSense.LE),
   }

   relaxed_list = relax_constraints(constraints, metadata_map)

   for relaxed in relaxed_list:
       print(f"Relaxed: {relaxed.constraint.name}")
       print(f"  Positive deviation variable: {relaxed.pos_deviation.name}")
       print(f"  Negative deviation variable: {relaxed.neg_deviation.name}")
       print(f"  Goal instances: {len(relaxed.goal_instances)}")

Goal Instances
--------------

Semantic Indexing
~~~~~~~~~~~~~~~~~

Deviation variables are indexed by **Goal instances**, not by the original data.
This provides semantic meaning to deviations:

.. code-block:: python

   # Each product gets a Goal instance
   # Goal instance contains metadata about the goal

   for goal in relaxed.goal_instances:
       print(f"Goal ID: {goal.id}")
       print(f"  Constraint: {goal.constraint_name}")
       print(f"  Priority: {goal.priority}")
       print(f"  Weight: {goal.weight}")
       print(f"  Target Value: {goal.target_value}")
       print(f"  Instance ID: {goal.instance_id}")

**Example** for indexed constraint:

.. code-block:: python

   # Constraint: production[product] >= demand[product]
   # Creates goals:
   #   - Goal("demand_product_A", constraint_name="demand", instance_id="product_A", ...)
   #   - Goal("demand_product_B", constraint_name="demand", instance_id="product_B", ...)
   #
   # Deviation variables:
   #   - pos_dev[Goal("demand_product_A")]
   #   - pos_dev[Goal("demand_product_B")]
   #   - neg_dev[Goal("demand_product_A")]
   #   - neg_dev[Goal("demand_product_B")]

Business Value
~~~~~~~~~~~~~~

Goal instances make deviations meaningful:

.. code-block:: text

   Instead of:
       "neg_dev[0] = 10"  (What does this mean?)

   You get:
       "Route 5 needs 3 additional buses"
       "Product A has 20 units excess inventory"
       "Department B is 5 hours over overtime limit"

Practical Examples
------------------

Production Planning
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dataclasses import dataclass

   @dataclass
   class Product:
       id: str
       demand_target: float
       production_cost: float

   products = [
       Product("A", demand_target=100, production_cost=5),
       Product("B", demand_target=150, production_cost=6),
   ]

   # Define production variable
   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .bounds(lower=0)
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

   # Goal: Meet demand
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

   # When relaxed, creates:
   #   - Goal instances: [Goal("demand_A", ...), Goal("demand_B", ...)]
   #   - Variables: pos_dev[Goal], neg_dev[Goal] for each goal
   #   - Constraint: production[p] + neg_dev - pos_dev = p.demand_target

Resource Constraints with Goals
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   @dataclass
   class Resource:
       id: str
       capacity: float
       target_utilization: float  # e.g., 0.8 for 80%

   # Hard constraint: Cannot exceed capacity
   capacity_hard = (
       LXConstraint[Resource]("capacity")
       .expression(usage_expr)
       .le()
       .rhs(lambda r: r.capacity)
       .from_data(resources)
       # No .as_goal() - stays hard constraint
   )

   # Soft goal: Target utilization
   utilization_goal = (
       LXConstraint[Resource]("utilization")
       .expression(usage_expr)
       .eq()  # Want exact target
       .rhs(lambda r: r.capacity * r.target_utilization)
       .as_goal(priority=2, weight=1.0)
       .from_data(resources)
   )

   # Result:
   #   - Capacity is hard limit (never exceeded)
   #   - Utilization can deviate but is penalized

Deviation Variable Details
---------------------------

Naming Convention
~~~~~~~~~~~~~~~~~

Deviation variables follow a standard naming pattern:

.. code-block:: python

   from lumix.goal_programming import get_deviation_var_name

   # For a goal named "demand"
   pos_name = get_deviation_var_name("demand", "pos")  # "demand_pos_dev"
   neg_name = get_deviation_var_name("demand", "neg")  # "demand_neg_dev"

Variable Bounds
~~~~~~~~~~~~~~~

Deviation variables are always non-negative continuous variables:

.. code-block:: python

   # Automatically created as:
   pos_deviation = (
       LXVariable[LXGoal, float]("demand_pos_dev")
       .continuous()
       .bounds(lower=0.0)  # Non-negative
       .indexed_by(lambda g: g.id)
       .from_data(goal_instances)
   )

Accessing in Solution
~~~~~~~~~~~~~~~~~~~~~

Deviation values are available in the solution:

.. code-block:: python

   solution = optimizer.solve(model)

   # Via goal deviations
   deviations = solution.get_goal_deviations("demand")
   print(f"Positive deviations: {deviations['pos']}")
   print(f"Negative deviations: {deviations['neg']}")

   # Via variable access
   pos_dev_values = solution.get_variable(relaxed.pos_deviation)
   neg_dev_values = solution.get_variable(relaxed.neg_deviation)

Understanding Undesired Deviations
-----------------------------------

Deviation Selection
~~~~~~~~~~~~~~~~~~~

The relaxation automatically determines which deviations to minimize:

.. code-block:: python

   # For LE (≤)
   undesired = relaxed.goal_metadata.is_pos_undesired()  # True
   # Minimizes: pos_dev (over-achievement)

   # For GE (≥)
   undesired = relaxed.goal_metadata.is_neg_undesired()  # True
   # Minimizes: neg_dev (under-achievement)

   # For EQ (=)
   undesired_pos = relaxed.goal_metadata.is_pos_undesired()  # True
   undesired_neg = relaxed.goal_metadata.is_neg_undesired()  # True
   # Minimizes: both pos_dev and neg_dev

Getting Undesired Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get list of deviation variables to include in objective
   undesired_vars = relaxed.get_undesired_variables()

   # For GE constraint, returns: [neg_deviation]
   # For LE constraint, returns: [pos_deviation]
   # For EQ constraint, returns: [pos_deviation, neg_deviation]

Best Practices
--------------

1. **Mix Hard and Soft Constraints**

   .. code-block:: python

      # Hard constraints for physical limits
      capacity = (
          LXConstraint[Resource]("capacity")
          .expression(usage_expr)
          .le()
          .rhs(lambda r: r.max_capacity)
          # No .as_goal()
      )

      # Soft goals for targets
      target = (
          LXConstraint[Resource]("target")
          .expression(usage_expr)
          .eq()
          .rhs(lambda r: r.target_usage)
          .as_goal(priority=1, weight=1.0)
      )

2. **Choose Appropriate Constraint Sense**

   .. code-block:: python

      # Use GE for minimum requirements
      min_production.ge().rhs(min_qty).as_goal(priority=1, weight=1.0)

      # Use LE for maximum limits
      max_overtime.le().rhs(max_hours).as_goal(priority=2, weight=1.0)

      # Use EQ only when exact target is truly needed
      exact_budget.eq().rhs(budget).as_goal(priority=1, weight=1.0)

3. **Understand Goal Semantics**

   .. code-block:: python

      # Goal instances provide meaning
      for goal in relaxed.goal_instances:
          # Can identify specific instances that deviated
          if goal.instance_id == "product_A":
              print(f"Product A target: {goal.target_value}")

4. **Check Relaxation Results**

   .. code-block:: python

      # Verify relaxation created expected structure
      relaxed = relax_constraint(constraint, metadata)

      print(f"Original sense: {metadata.constraint_sense}")
      print(f"Relaxed to EQ: {relaxed.constraint.sense == LXConstraintSense.EQ}")
      print(f"Deviation variables: {relaxed.pos_deviation.name}, {relaxed.neg_deviation.name}")
      print(f"Goal instances: {len(relaxed.goal_instances)}")

Next Steps
----------

- :doc:`objective-building` - Learn how deviation variables are used in objectives
- :doc:`weighted-mode` - Apply relaxation in weighted goal programming
- :doc:`sequential-mode` - Apply relaxation in sequential goal programming
- :doc:`/api/goal_programming/index` - Full API reference
- :doc:`/user-guide/solution/goal-programming` - Accessing deviations in solutions
