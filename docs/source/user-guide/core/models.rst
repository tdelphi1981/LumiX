Models Guide
============

The model ties together variables, constraints, and objectives.

Model Building
--------------

:class:`~lumix.core.model.LXModel` is the central component that contains your optimization problem.

Basic Structure
~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXModel

   model = (
       LXModel("model_name")
       .add_variable(production)
       .add_variable(inventory)
       .add_constraint(capacity)
       .add_constraint(demand)
       .maximize(profit_expr)
   )

Building Step-by-Step
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Create model
   model = LXModel("production_plan")

   # Add variables
   model.add_variable(production)
   model.add_variable(inventory)

   # Add constraints
   model.add_constraint(capacity_constraint)
   model.add_constraint(demand_constraint)

   # Set objective
   model.maximize(profit_expression)

Adding Components
-----------------

Variables
~~~~~~~~~

.. code-block:: python

   # Single variable
   model.add_variable(production)

   # Multiple variables
   model.add_variables(production, inventory, shipment)

Constraints
~~~~~~~~~~~

.. code-block:: python

   # Single constraint
   model.add_constraint(capacity)

   # Multiple constraints
   model.add_constraints(capacity, demand, balance)

Objectives
~~~~~~~~~~

.. code-block:: python

   # Maximize
   model.maximize(profit_expr)

   # Minimize
   model.minimize(cost_expr)

**Note**: Every model must have exactly one objective.

Type Safety
-----------

Use generic type parameter for type checking:

.. code-block:: python

   from dataclasses import dataclass

   @dataclass
   class Product:
       id: str
       profit: float

   # Type-safe model
   model = LXModel[Product]("production")

   # IDE knows product variables are Product type
   production = LXVariable[Product, float]("production").from_data(products)
   model.add_variable(production)

Model Summary
-------------

Get a quick overview:

.. code-block:: python

   print(model.summary())

Output::

   LXModel: production_plan
     Variable Families: 2
     Constraint Families: 3
     Objective: maximize

Querying Components
-------------------

Get Variables
~~~~~~~~~~~~~

.. code-block:: python

   production_var = model.get_variable("production")

Get Constraints
~~~~~~~~~~~~~~~

.. code-block:: python

   capacity_const = model.get_constraint("capacity")

Goal Programming
----------------

For multi-objective optimization:

.. code-block:: python

   model = LXModel("multi_objective").set_goal_mode("weighted")

   # Add goal constraints
   model.add_constraint(
       profit_constraint.as_goal(priority=1, weight=1.0)
   )
   model.add_constraint(
       quality_constraint.as_goal(priority=2, weight=0.8)
   )

**Modes**:

- ``weighted``: Solve once with weighted sum
- ``sequential``: Solve lexicographically (multiple solves)

Solving
-------

Pass model to optimizer:

.. code-block:: python

   from lumix import LXOptimizer

   optimizer = LXOptimizer().use_solver("gurobi")
   solution = optimizer.solve(model)

   if solution.is_optimal():
       print(f"Objective: {solution.objective_value}")

Best Practices
--------------

1. **Use Descriptive Names**

   .. code-block:: python

      # Good
      model = LXModel("production_planning")

      # Bad
      model = LXModel("m1")

2. **Fluent API for Readability**

   .. code-block:: python

      model = (
          LXModel("plan")
          .add_variable(production)
          .add_constraint(capacity)
          .maximize(profit)
      )

3. **Validate Before Solving**

   .. code-block:: python

      print(model.summary())  # Check component counts

4. **Organize by Concern**

   .. code-block:: python

      # Variables
      production = ...
      inventory = ...

      # Constraints
      capacity = ...
      demand = ...

      # Model
      model = (
          LXModel("plan")
          .add_variables(production, inventory)
          .add_constraints(capacity, demand)
          .maximize(profit)
      )

Complete Example
----------------

.. code-block:: python

   from lumix import (
       LXModel,
       LXVariable,
       LXConstraint,
       LXLinearExpression,
       LXOptimizer,
   )

   # Define variables
   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .bounds(lower=0)
       .from_data(products)
   )

   # Define constraints
   capacity = (
       LXConstraint("capacity")
       .expression(
           LXLinearExpression().add_term(production, lambda p: p.usage)
       )
       .le()
       .rhs(max_capacity)
   )

   # Build model
   model = (
       LXModel("production_plan")
       .add_variable(production)
       .add_constraint(capacity)
       .maximize(
           LXLinearExpression().add_term(production, lambda p: p.profit)
       )
   )

   # Solve
   optimizer = LXOptimizer().use_solver("gurobi")
   solution = optimizer.solve(model)

Next Steps
----------

- :doc:`/getting-started/solvers` - Choose a solver
- :doc:`/examples/index` - Working examples
- :doc:`/api/core/index` - Full API reference
