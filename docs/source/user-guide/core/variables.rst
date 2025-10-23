Variables Guide
===============

Variables represent the decisions to be made in your optimization model.

Variable Families
-----------------

**Key Concept**: In LumiX, an :class:`~lumix.core.variables.LXVariable` is not a single variable,
but a **family** that expands to multiple solver variables based on your data.

.. code-block:: python

   # This ONE LXVariable object represents MANY solver variables
   production = LXVariable[Product, float]("production").from_data(products)

   # Automatically expands to:
   #   production[product1], production[product2], production[product3], ...

Variable Types
--------------

Continuous Variables
~~~~~~~~~~~~~~~~~~~~

Real-valued variables for quantities that can take any value:

.. code-block:: python

   production = (
       LXVariable[Product, float]("production")
       .continuous()  # Default type
       .bounds(lower=0, upper=1000)
       .from_data(products)
   )

**Use for**: Production quantities, percentages, weights, allocations

Integer Variables
~~~~~~~~~~~~~~~~~

Whole number variables:

.. code-block:: python

   num_trucks = (
       LXVariable[Route, int]("trucks")
       .integer()
       .bounds(lower=0, upper=10)
       .from_data(routes)
   )

**Use for**: Counts, discrete quantities, number of items

Binary Variables
~~~~~~~~~~~~~~~~

Yes/no decision variables (0 or 1):

.. code-block:: python

   is_open = (
       LXVariable[Facility, int]("is_open")
       .binary()  # Automatically sets bounds to [0, 1]
       .from_data(facilities)
   )

**Use for**: Selection, activation, yes/no decisions

Indexing
--------

Single-Model Indexing
~~~~~~~~~~~~~~~~~~~~~

Index variables by a single data model:

.. code-block:: python

   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .indexed_by(lambda p: p.id)  # Index function
       .from_data(products)  # Data source
   )

**Index Options:**

- Simple: `.indexed_by(lambda p: p.id)`
- Tuple: `.indexed_by(lambda p: (p.category, p.id))`
- String: `.indexed_by(lambda p: f"{p.factory}_{p.id}")`

Multi-Model Indexing
~~~~~~~~~~~~~~~~~~~~

Index by multiple models using Cartesian product:

.. code-block:: python

   from lumix import LXIndexDimension, LXCartesianProduct

   assignment = (
       LXVariable[tuple[Driver, Date, Shift], int]("assignment")
       .binary()
       .indexed_by_product(
           LXIndexDimension(Driver, lambda d: d.id).from_data(drivers),
           LXIndexDimension(Date, lambda dt: dt.id).from_data(dates),
           LXIndexDimension(Shift, lambda s: s.id).from_data(shifts),
       )
   )

This creates variables for **every combination** of driver, date, and shift.

Filtering
---------

Filter which instances to include:

Single-Model Filter
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .where(lambda p: p.is_active and p.stock > 0)
       .from_data(products)
   )

Multi-Model Filter
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   assignment = (
       LXVariable[tuple[Driver, Date], int]("assignment")
       .binary()
       .indexed_by_product(
           LXIndexDimension(Driver, lambda d: d.id)
               .where(lambda d: d.is_qualified)  # Per-dimension filter
               .from_data(drivers),
           LXIndexDimension(Date, lambda dt: dt.id)
               .from_data(dates),
       )
       .where_multi(lambda driver, date:  # Cross-dimension filter
           date not in driver.days_off
       )
   )

Data Sources
------------

Direct Data
~~~~~~~~~~~

Provide data directly:

.. code-block:: python

   products = [Product(id="A", cost=10), Product(id="B", cost=20)]

   production = (
       LXVariable[Product, float]("production")
       .from_data(products)
   )

ORM Integration
~~~~~~~~~~~~~~~

Query from database:

.. code-block:: python

   from sqlalchemy.orm import Session

   production = (
       LXVariable[Product, float]("production")
       .from_model(Product, session=db_session)
   )

Cartesian Product
~~~~~~~~~~~~~~~~~

For multi-dimensional variables:

.. code-block:: python

   from lumix import LXCartesianProduct

   assignment = (
       LXVariable[tuple[Driver, Date], int]("assignment")
       .from_data(LXCartesianProduct(drivers, dates))
   )

Cost Coefficients
-----------------

Define objective coefficients:

Single-Model
~~~~~~~~~~~~

.. code-block:: python

   production = (
       LXVariable[Product, float]("production")
       .cost(lambda p: p.unit_profit)  # Coefficient from data
       .from_data(products)
   )

   # Use in objective
   model.maximize(
       LXLinearExpression().add_term(production, lambda p: p.profit)
   )

Multi-Model
~~~~~~~~~~~

.. code-block:: python

   shipment = (
       LXVariable[tuple[Origin, Destination], float]("shipment")
       .cost_multi(lambda o, d: calculate_shipping_cost(o, d))
       .indexed_by_product(...)
   )

Bounds
------

Set variable bounds:

Simple Bounds
~~~~~~~~~~~~~

.. code-block:: python

   production = (
       LXVariable[Product, float]("production")
       .bounds(lower=0, upper=1000)
       .from_data(products)
   )

Data-Driven Bounds
~~~~~~~~~~~~~~~~~~

Bounds can vary per instance:

.. code-block:: python

   # Use where clause for conditional bounds
   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .bounds(lower=0)
       .from_data(products)
   )

   # Add constraints for upper bounds from data
   model.add_constraint(
       LXConstraint[Product]("max_production")
       .expression(LXLinearExpression().add_term(production, 1.0))
       .le()
       .rhs(lambda p: p.max_capacity)
       .from_data(products)
   )

Best Practices
--------------

1. **Use Type Annotations**

   .. code-block:: python

      # Good: Type-safe
      production = LXVariable[Product, float]("production")

      # Bad: No type safety
      production = LXVariable("production")

2. **Name Variables Clearly**

   .. code-block:: python

      # Good: Descriptive
      daily_production = LXVariable[Product, float]("daily_production")

      # Bad: Cryptic
      x = LXVariable[Product, float]("x")

3. **Use Fluent API**

   .. code-block:: python

      # Good: Readable chain
      production = (
           LXVariable[Product, float]("production")
           .continuous()
           .bounds(lower=0)
           .from_data(products)
       )

4. **Filter Early**

   .. code-block:: python

      # Good: Filter at variable level
      production = (
          LXVariable[Product, float]("production")
          .where(lambda p: p.is_active)
          .from_data(products)
      )

      # Less efficient: Filter in constraints
      # Creates unnecessary variables

Common Patterns
---------------

Production Planning
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .bounds(lower=0)
       .cost(lambda p: -p.unit_cost)  # Negative for minimization
       .from_data(products)
   )

Facility Location
~~~~~~~~~~~~~~~~~

.. code-block:: python

   is_open = (
       LXVariable[Facility, int]("is_open")
       .binary()
       .cost(lambda f: f.fixed_cost)
       .from_data(facilities)
   )

Assignment
~~~~~~~~~~

.. code-block:: python

   assign = (
       LXVariable[tuple[Worker, Task], int]("assign")
       .binary()
       .indexed_by_product(
           LXIndexDimension(Worker, lambda w: w.id).from_data(workers),
           LXIndexDimension(Task, lambda t: t.id).from_data(tasks),
       )
       .where_multi(lambda w, t: t.skill_level <= w.skill_level)
   )

Next Steps
----------

- :doc:`constraints` - Learn about constraint families
- :doc:`expressions` - Build mathematical expressions
- :doc:`models` - Tie everything together
- :doc:`/api/core/index` - Full API reference
