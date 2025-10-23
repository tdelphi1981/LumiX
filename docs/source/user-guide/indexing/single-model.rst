Single-Model Indexing
=====================

Single-model indexing creates variables and constraints indexed by a single data model type.
This is the most common and straightforward use of LumiX's indexing capabilities.

Concept
-------

A **single-model indexed variable** represents a family of solver variables, one for each
instance of a data model:

.. code-block:: python

   production = LXVariable[Product, float]("production").from_data(products)

   # Expands to: production[product1], production[product2], ...

Basic Usage
-----------

Variable Definition
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dataclasses import dataclass
   from lumix import LXVariable

   @dataclass
   class Product:
       id: str
       name: str
       profit: float
       cost: float

   products = [
       Product("A", "Product A", profit=30, cost=10),
       Product("B", "Product B", profit=40, cost=15),
   ]

   # Define variable indexed by Product
   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .bounds(lower=0, upper=1000)
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

Index Functions
~~~~~~~~~~~~~~~

The index function extracts the unique key from each model instance:

**Simple ID:**

.. code-block:: python

   .indexed_by(lambda p: p.id)

**Compound Key (Tuple):**

.. code-block:: python

   .indexed_by(lambda r: (r.origin, r.destination))

**String Concatenation:**

.. code-block:: python

   .indexed_by(lambda p: f"{p.category}_{p.sku}")

Data Sources
------------

Direct Data
~~~~~~~~~~~

Provide data instances directly:

.. code-block:: python

   products = load_products()  # List[Product]

   production = (
       LXVariable[Product, float]("production")
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

ORM Integration
~~~~~~~~~~~~~~~

Query from database:

.. code-block:: python

   from sqlalchemy.orm import Session

   production = (
       LXVariable[Product, float]("production")
       .indexed_by(lambda p: p.id)
       .from_model(Product, session=db_session)
   )

Using in Expressions
--------------------

Objective Functions
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXLinearExpression

   # Maximize total profit
   profit_expr = (
       LXLinearExpression()
       .add_term(production, lambda p: p.profit)
   )

   model.maximize(profit_expr)

   # Minimize total cost
   cost_expr = (
       LXLinearExpression()
       .add_term(production, lambda p: p.cost)
   )

   model.minimize(cost_expr)

Constraints
~~~~~~~~~~~

.. code-block:: python

   from lumix import LXConstraint

   # Single global constraint
   total_production = LXConstraint("total_limit").expression(
       LXLinearExpression().add_term(production, 1.0)
   ).le().rhs(1000)

   model.add_constraint(total_production)

   # Constraint family - one per resource
   for resource in resources:
       model.add_constraint(
           LXConstraint[Product](f"resource_{resource.id}")
           .expression(
               LXLinearExpression()
               .add_term(production, lambda p: p.usage.get(resource.id, 0))
           )
           .le()
           .rhs(resource.capacity)
           .from_data(products)
       )

Complete Example
----------------

.. code-block:: python

   from dataclasses import dataclass
   from lumix import (
       LXModel,
       LXVariable,
       LXConstraint,
       LXLinearExpression,
       LXOptimizer,
   )

   @dataclass
   class Product:
       id: str
       name: str
       profit: float
       resource_usage: float
       max_production: float

   products = [
       Product("A", "Product A", profit=30, resource_usage=2, max_production=50),
       Product("B", "Product B", profit=40, resource_usage=3, max_production=40),
       Product("C", "Product C", profit=25, resource_usage=1.5, max_production=60),
   ]

   # Define variable
   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .bounds(lower=0)
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

   # Build model
   model = (
       LXModel("production_plan")
       .add_variable(production)
       .maximize(
           LXLinearExpression()
           .add_term(production, lambda p: p.profit)
       )
   )

   # Global resource constraint
   model.add_constraint(
       LXConstraint("resource_limit")
       .expression(
           LXLinearExpression()
           .add_term(production, lambda p: p.resource_usage)
       )
       .le()
       .rhs(200)  # Total resource capacity
   )

   # Per-product max production constraints
   model.add_constraint(
       LXConstraint[Product]("max_production")
       .expression(LXLinearExpression().add_term(production, 1.0))
       .le()
       .rhs(lambda p: p.max_production)
       .from_data(products)
   )

   # Solve
   optimizer = LXOptimizer().use_solver("ortools")
   solution = optimizer.solve(model)

   # Access results
   if solution.is_optimal():
       print(f"Optimal profit: ${solution.objective_value:,.2f}")
       for product in products:
           qty = solution.variables["production"][product.id]
           print(f"  {product.name}: {qty:.2f} units")

Filtering
---------

Apply filters to include only certain instances:

.. code-block:: python

   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .where(lambda p: p.is_active and p.stock_available)
       .from_data(products)
   )

Common Patterns
---------------

Binary Selection
~~~~~~~~~~~~~~~~

.. code-block:: python

   is_selected = (
       LXVariable[Facility, int]("is_selected")
       .binary()
       .indexed_by(lambda f: f.id)
       .from_data(facilities)
   )

Integer Counts
~~~~~~~~~~~~~~

.. code-block:: python

   num_trucks = (
       LXVariable[Route, int]("num_trucks")
       .integer()
       .bounds(lower=0, upper=10)
       .indexed_by(lambda r: (r.origin, r.destination))
       .from_data(routes)
   )

Continuous Quantities
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   flow = (
       LXVariable[Arc, float]("flow")
       .continuous()
       .bounds(lower=0)
       .indexed_by(lambda a: (a.from_node, a.to_node))
       .from_data(arcs)
   )

Best Practices
--------------

1. **Use meaningful index keys:**

   .. code-block:: python

      # Good: Business identifier
      .indexed_by(lambda p: p.sku)

      # Avoid: Auto-increment IDs if not stable
      .indexed_by(lambda p: p.db_id)

2. **Filter early:**

   .. code-block:: python

      # Good: Filter at variable level
      production = (
          LXVariable[Product, float]("production")
          .where(lambda p: p.is_active)
          .from_data(products)
      )

      # Less efficient: Filter in constraints
      # Creates unnecessary variables

3. **Use type annotations:**

   .. code-block:: python

      # Good: Full type information
      production = LXVariable[Product, float]("production")

      # Bad: No type information
      production = LXVariable("production")

Next Steps
----------

- :doc:`multi-model` - Learn multi-dimensional indexing
- :doc:`dimensions` - Understand index dimensions in depth
- :doc:`filtering` - Advanced filtering strategies
- :doc:`/user-guide/core/variables` - Variable families in detail
