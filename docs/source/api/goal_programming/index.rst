Goal Programming Module API
============================

The goal programming module provides automatic LP-to-Goal Programming conversion with
constraint relaxation, deviation variables, and multiple solving modes.

Overview
--------

The goal programming module implements a complete goal programming framework that transforms
traditional optimization models into multi-objective goal programming models:

.. mermaid::

   graph TD
       A[Hard Constraints] --> B[Goal Constraints]
       B --> C[Constraint Relaxation]
       C --> D[Deviation Variables]
       D --> E[Objective Building]
       E --> F[Weighted/Sequential Solving]
       G[LXGoalMetadata] --> C
       H[LXGoalMode] --> F
       I[RelaxedConstraint] --> E

       style A fill:#e1f5ff
       style B fill:#fff4e1
       style C fill:#ffe1e1
       style D fill:#e1ffe1
       style E fill:#f0e1ff
       style F fill:#e8f4f8

Key Features
~~~~~~~~~~~~

- **Automatic Relaxation**: Convert hard constraints to soft constraints with deviation variables
- **Multiple Modes**: Weighted (single solve) and Sequential (lexicographic) goal programming
- **Priority-Based**: Support for multiple priority levels with automatic weight scaling
- **Custom Objectives**: Integrate traditional objectives with goal constraints
- **Type-Safe**: Full type safety with generic data models
- **Data-Driven**: Deviation variables indexed by Goal instances for semantic meaning

Components
----------

Goal Metadata and Data Structures
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.goal_programming.goal.LXGoal
   lumix.goal_programming.goal.LXGoalMetadata
   lumix.goal_programming.goal.LXGoalMode
   lumix.goal_programming.goal.get_deviation_var_name
   lumix.goal_programming.goal.priority_to_weight

The :class:`~lumix.goal_programming.goal.LXGoal` class represents individual goal instances
that serve as the data source for deviation variables. This provides semantic meaning to
deviations (e.g., "Route 5 needs 3 additional buses").

The :class:`~lumix.goal_programming.goal.LXGoalMetadata` class stores goal configuration
including priority, weight, and which deviations are undesired.

The :class:`~lumix.goal_programming.goal.LXGoalMode` enum defines solving modes: WEIGHTED
or SEQUENTIAL (lexicographic).

Constraint Relaxation
~~~~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.goal_programming.relaxation.RelaxedConstraint
   lumix.goal_programming.relaxation.relax_constraint
   lumix.goal_programming.relaxation.relax_constraints

The relaxation module transforms hard constraints into equality constraints with deviation
variables:

- **LE (≤)**: expr + neg_dev - pos_dev = rhs (minimize pos_dev)
- **GE (≥)**: expr + neg_dev - pos_dev = rhs (minimize neg_dev)
- **EQ (=)**: expr + neg_dev - pos_dev = rhs (minimize both)

Objective Building
~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.goal_programming.objective_builder.build_weighted_objective
   lumix.goal_programming.objective_builder.build_sequential_objectives
   lumix.goal_programming.objective_builder.combine_objectives
   lumix.goal_programming.objective_builder.extract_custom_objectives

The objective building module constructs goal programming objectives:

- **Weighted**: Single objective with exponentially scaled priorities
- **Sequential**: Multiple objectives solved lexicographically
- **Combined**: Mix traditional objectives with goal deviations
- **Custom**: Extract priority 0 goals as custom objective terms

Solver Orchestration
~~~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.goal_programming.solver.LXGoalProgrammingSolver
   lumix.goal_programming.solver.solve_goal_programming

The :class:`~lumix.goal_programming.solver.LXGoalProgrammingSolver` class orchestrates
sequential (lexicographic) goal programming with multiple solve iterations.

For weighted mode, transformation is handled directly in :class:`~lumix.core.model.LXModel`.

Detailed API Reference
----------------------

Goal Metadata
~~~~~~~~~~~~~

.. automodule:: lumix.goal_programming.goal
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

**Key Classes:**

- :class:`LXGoal`: Represents a single goal instance with metadata
- :class:`LXGoalMetadata`: Configuration for goal constraints (priority, weight, sense)
- :class:`LXGoalMode`: Enum for solving modes (WEIGHTED, SEQUENTIAL)

**Utility Functions:**

- :func:`get_deviation_var_name`: Generate standard deviation variable names
- :func:`priority_to_weight`: Convert priority levels to exponential weights

Constraint Relaxation
~~~~~~~~~~~~~~~~~~~~~

.. automodule:: lumix.goal_programming.relaxation
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

**Key Classes:**

- :class:`RelaxedConstraint`: Container for relaxed constraint with deviation variables

**Key Functions:**

- :func:`relax_constraint`: Relax a single constraint
- :func:`relax_constraints`: Batch relaxation of multiple constraints

Objective Building
~~~~~~~~~~~~~~~~~~

.. automodule:: lumix.goal_programming.objective_builder
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

**Key Functions:**

- :func:`build_weighted_objective`: Build single weighted objective
- :func:`build_sequential_objectives`: Build objectives for sequential solving
- :func:`combine_objectives`: Combine traditional and goal objectives
- :func:`extract_custom_objectives`: Extract priority 0 custom objectives

Solver
~~~~~~

.. automodule:: lumix.goal_programming.solver
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

**Key Classes:**

- :class:`LXGoalProgrammingSolver`: Orchestrates sequential goal programming

**Key Functions:**

- :func:`solve_goal_programming`: High-level convenience function

Usage Examples
--------------

Basic Weighted Goal Programming
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXModel, LXVariable, LXConstraint, LXOptimizer
   from lumix.core.expressions import LXLinearExpression

   # Define variables
   production = LXVariable[Product, float]("production").from_data(products)

   # Define goal constraint
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

   # Build model (goal mode is set by as_goal())
   model = LXModel("production")
   model.add_variable(production)
   model.add_constraint(demand_goal)

   # Solve
   optimizer = LXOptimizer().use_solver("gurobi")
   solution = optimizer.solve(model)

   # Access goal deviations
   deviations = solution.get_goal_deviations("demand_goal")
   print(f"Positive deviation: {deviations['pos']}")
   print(f"Negative deviation: {deviations['neg']}")

Multi-Priority Goals
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Priority 1: Maximize profit (custom objective)
   profit_goal = (
       LXConstraint("profit")
       .expression(profit_expr)
       .ge()
       .rhs(0)
       .as_goal(priority=0, weight=1.0)  # Priority 0 = custom objective
   )

   # Priority 2: Meet demand (higher priority)
   demand_goal = (
       LXConstraint[Product]("demand")
       .expression(production_expr)
       .ge()
       .rhs(lambda p: p.demand)
       .as_goal(priority=1, weight=1.0)
       .from_data(products)
   )

   # Priority 3: Minimize overtime (lower priority)
   overtime_goal = (
       LXConstraint("overtime")
       .expression(overtime_expr)
       .le()
       .rhs(40)
       .as_goal(priority=2, weight=0.5)
   )

   model = (
       LXModel("multi_priority")
       .add_variable(production)
       .add_constraint(profit_goal)
       .add_constraint(demand_goal)
       .add_constraint(overtime_goal)
   )

   solution = optimizer.solve(model)

Direct Relaxation API
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.goal_programming import relax_constraint, LXGoalMetadata
   from lumix.core.enums import LXConstraintSense

   # Create goal metadata
   metadata = LXGoalMetadata(
       priority=1,
       weight=1.0,
       constraint_sense=LXConstraintSense.GE
   )

   # Relax constraint
   relaxed = relax_constraint(demand_constraint, metadata)

   # Access components
   equality_constraint = relaxed.constraint  # Now EQ with deviations
   pos_deviation = relaxed.pos_deviation     # LXVariable[LXGoal, float]
   neg_deviation = relaxed.neg_deviation     # LXVariable[LXGoal, float]
   goals = relaxed.goal_instances            # List[LXGoal]

Sequential Goal Programming
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.goal_programming import LXGoalProgrammingSolver

   # Set sequential mode
   model.set_goal_mode("sequential")

   # Create solver
   gp_solver = LXGoalProgrammingSolver(optimizer)

   # Get relaxed constraints from model
   relaxed_constraints = model._relaxed_constraints

   # Solve sequentially by priority
   solution = gp_solver.solve_sequential(model, relaxed_constraints)

Building Custom Objectives
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.goal_programming import (
       build_weighted_objective,
       build_sequential_objectives,
       combine_objectives
   )

   # Build weighted objective from relaxed constraints
   goal_objective = build_weighted_objective(relaxed_constraints)

   # Combine with traditional objective
   combined = combine_objectives(
       base_objective=profit_expr,
       goal_objective=goal_objective,
       goal_weight=0.1
   )

   # Or build sequential objectives
   sequential_objs = build_sequential_objectives(relaxed_constraints)
   # Returns: [(priority_1, expr_1), (priority_2, expr_2), ...]

Type Hints
----------

The goal programming module is fully type-annotated:

.. code-block:: python

   from typing import List, Dict, Tuple, Optional
   from lumix.goal_programming import (
       LXGoal,
       LXGoalMetadata,
       LXGoalMode,
       RelaxedConstraint,
       LXGoalProgrammingSolver
   )
   from lumix.core import LXConstraint, LXVariable
   from lumix.core.expressions import LXLinearExpression

   # Type-safe goal creation
   goal: LXGoal = LXGoal(
       id="demand_product_1",
       constraint_name="demand",
       priority=1,
       weight=1.0,
       constraint_sense=LXConstraintSense.GE,
       target_value=100.0,
       instance_id=1
   )

   # Type-safe relaxation
   relaxed: RelaxedConstraint[Product] = relax_constraint(
       constraint=demand_constraint,
       goal_metadata=metadata
   )

   # Type-safe solver
   solver: LXGoalProgrammingSolver = LXGoalProgrammingSolver(optimizer)
   solution: LXSolution[Product] = solver.solve_weighted(model)

Related Documentation
---------------------

User Guide
~~~~~~~~~~

- :doc:`/user-guide/goal_programming/index` - Goal programming overview
- :doc:`/user-guide/goal_programming/weighted-mode` - Weighted goal programming
- :doc:`/user-guide/goal_programming/sequential-mode` - Sequential goal programming
- :doc:`/user-guide/goal_programming/relaxation` - Constraint relaxation concepts
- :doc:`/user-guide/goal_programming/objective-building` - Building goal objectives

Development Guide
~~~~~~~~~~~~~~~~~

- :doc:`/development/goal-programming-architecture` - Architecture and design
- :doc:`/development/extending-goal-programming` - Extending goal programming

See Also
--------

- :doc:`/api/core/index` - Core module (constraints, variables, models)
- :doc:`/api/solution/index` - Solution module (accessing goal deviations)
- :doc:`/user-guide/solution/goal-programming` - Working with goal programming solutions
