Indexing Guide
==============

Overview
--------

The indexing module is one of LumiX's most powerful features, enabling you to create variables
and constraints indexed by one or more data models. This allows you to build optimization models
that naturally reflect the structure of your data.

**Key Concept**: Instead of manually creating variables in loops with numeric indices, LumiX
automatically expands variable and constraint families based on your data models with full
type safety.

.. code-block:: python

   # Traditional approach - error-prone and verbose
   x = {}
   for i in range(len(products)):
       x[i] = model.addVar(name=f"x_{i}")

   # LumiX approach - data-driven and type-safe
   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

Core Concepts
-------------

.. toctree::
   :maxdepth: 1

   single-model
   multi-model
   dimensions
   filtering

Single-Model Indexing
~~~~~~~~~~~~~~~~~~~~~

Variables and constraints indexed by a single data model.

**Use cases:**

- Production planning (indexed by Product)
- Facility location (indexed by Facility)
- Resource allocation (indexed by Resource)

:doc:`single-model` - Learn about single-model indexing

Multi-Model Indexing
~~~~~~~~~~~~~~~~~~~~

Variables indexed by tuples of multiple data models using cartesian products.

**Use cases:**

- Driver scheduling (indexed by Driver × Date)
- Transportation planning (indexed by Origin × Destination)
- Shift assignment (indexed by Worker × Date × Shift)

:doc:`multi-model` - Learn about multi-model indexing

Index Dimensions
~~~~~~~~~~~~~~~~

Building blocks for multi-dimensional indexing with filtering and data sources.

**Key features:**

- Per-dimension filtering
- Multiple data sources (direct data, ORM queries)
- Type-safe key extraction
- Lazy evaluation

:doc:`dimensions` - Learn about index dimensions

Filtering Strategies
~~~~~~~~~~~~~~~~~~~~

Control which instances and combinations are included in your model.

**Filtering types:**

- Per-dimension filters (reduce data before expansion)
- Cross-dimension filters (filter combinations)
- Performance optimization techniques

:doc:`filtering` - Learn about filtering strategies

Why Indexing Matters
--------------------

Type Safety
~~~~~~~~~~~

LumiX preserves type information throughout your model:

.. code-block:: python

   production = LXVariable[Product, float]("production").from_data(products)

   # IDE knows 'p' is a Product - full autocomplete
   expr = LXLinearExpression().add_term(production, lambda p: p.profit)

Data-Driven Modeling
~~~~~~~~~~~~~~~~~~~~

Models automatically adapt to your data:

.. code-block:: python

   # Add more products? No code changes needed!
   products = load_products()  # Could be 10 or 10,000 products

   production = LXVariable[Product, float]("production").from_data(products)
   # Automatically creates the right number of variables

No Manual Loops
~~~~~~~~~~~~~~~

LumiX handles variable expansion internally:

.. code-block:: python

   # No loops needed - automatic expansion
   production = LXVariable[Product, float]("production").from_data(products)

   # Automatic expansion in expressions
   total_profit = LXLinearExpression().add_term(production, lambda p: p.profit)

   # Automatic expansion in constraints
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

Multi-Dimensional Support
~~~~~~~~~~~~~~~~~~~~~~~~~

Natural handling of multi-dimensional problems:

.. code-block:: python

   from typing import Tuple

   # Two-dimensional variable
   assignment = (
       LXVariable[Tuple[Driver, Date], int]("assignment")
       .binary()
       .indexed_by_product(
           LXIndexDimension(Driver, lambda d: d.id).from_data(drivers),
           LXIndexDimension(Date, lambda dt: dt.date).from_data(dates)
       )
   )

   # Access solution with type-safe indices
   for driver in drivers:
       for date in dates:
           value = solution.variables["assignment"][(driver.id, date.date)]
           if value > 0.5:
               print(f"{driver.name} works on {date.date}")

Quick Start Examples
--------------------

Production Planning (Single-Model)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dataclasses import dataclass
   from lumix import LXVariable, LXModel, LXLinearExpression, LXConstraint

   @dataclass
   class Product:
       id: str
       name: str
       profit: float
       resource_usage: float

   products = [
       Product("A", "Product A", profit=30, resource_usage=2),
       Product("B", "Product B", profit=40, resource_usage=3),
   ]

   # Define variable indexed by Product
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

   # Add resource constraint
   model.add_constraint(
       LXConstraint("resource_limit")
       .expression(
           LXLinearExpression()
           .add_term(production, lambda p: p.resource_usage)
       )
       .le()
       .rhs(100)
   )

Driver Scheduling (Multi-Model)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from typing import Tuple
   from lumix import LXVariable, LXIndexDimension

   @dataclass
   class Driver:
       id: str
       name: str
       daily_rate: float
       is_active: bool

   @dataclass
   class Date:
       date: datetime.date
       min_drivers_required: int

   drivers = [...]
   dates = [...]

   # Define variable indexed by (Driver, Date)
   duty = (
       LXVariable[Tuple[Driver, Date], int]("duty")
       .binary()
       .indexed_by_product(
           LXIndexDimension(Driver, lambda d: d.id)
               .where(lambda d: d.is_active)
               .from_data(drivers),
           LXIndexDimension(Date, lambda dt: dt.date)
               .from_data(dates)
       )
       .cost_multi(lambda driver, date: driver.daily_rate)
       .where_multi(lambda driver, date: is_available(driver, date))
   )

Common Patterns
---------------

Filtering During Definition
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Apply filters early to reduce model size:

.. code-block:: python

   # Filter at variable level
   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .where(lambda p: p.is_active and p.stock > 0)
       .from_data(products)
   )

   # Filter dimensions
   driver_dim = (
       LXIndexDimension(Driver, lambda d: d.id)
       .where(lambda d: d.is_active and d.years_experience >= 2)
       .from_data(drivers)
   )

Sparse Indexing
~~~~~~~~~~~~~~~

Create variables only for valid combinations:

.. code-block:: python

   # Only create variables where driver can work on date
   duty = (
       LXVariable[Tuple[Driver, Date], int]("duty")
       .binary()
       .indexed_by_product(
           LXIndexDimension(Driver, lambda d: d.id).from_data(drivers),
           LXIndexDimension(Date, lambda dt: dt.date).from_data(dates)
       )
       .where_multi(lambda driver, date:
           date.weekday() not in driver.days_off and
           driver.can_work_date(date)
       )
   )

Compound Keys
~~~~~~~~~~~~~

Use tuples for complex indices:

.. code-block:: python

   # Route indexed by (origin, destination)
   route_dim = LXIndexDimension(
       Route,
       lambda r: (r.origin, r.destination)
   ).from_data(routes)

Best Practices
--------------

1. **Use Type Annotations**

   .. code-block:: python

      # Good: Full type information
      production = LXVariable[Product, float]("production")

      # Bad: No type information
      production = LXVariable("production")

2. **Filter Early**

   .. code-block:: python

      # Good: Filter at dimension level
      dim = (
          LXIndexDimension(Driver, lambda d: d.id)
          .where(lambda d: d.is_active)
          .from_data(drivers)
      )

      # Less efficient: Filter after cartesian product
      product.where(lambda d, dt: d.is_active and ...)

3. **Choose Descriptive Index Functions**

   .. code-block:: python

      # Good: Clear what the index represents
      .indexed_by(lambda product: product.sku)

      # Less clear: Generic
      .indexed_by(lambda p: p.id)

4. **Use Sparse Indexing for Large Models**

   .. code-block:: python

      # Create variables only where needed
      assignment = (
          LXVariable[Tuple[Worker, Task], int]("assignment")
          .binary()
          .indexed_by_product(...)
          .where_multi(lambda w, t: w.can_do_task(t))
      )

Performance Considerations
--------------------------

Cartesian Product Size
~~~~~~~~~~~~~~~~~~~~~~

Be aware of combinatorial explosion:

.. code-block:: python

   # 100 drivers × 7 dates = 700 variables (manageable)
   # 100 drivers × 30 dates × 3 shifts = 9,000 variables (still fine)
   # 1000 drivers × 365 dates × 10 shifts = 3.65M variables (problematic)

Use filtering to reduce size:

.. code-block:: python

   duty = (
       LXVariable[Tuple[Driver, Date, Shift], int]("duty")
       .indexed_by_product(...)
       .where_multi(lambda d, dt, s:
           # Only create variables for valid combinations
           d.can_work_shift(s) and
           dt.weekday() not in d.days_off
       )
   )

Lazy Evaluation
~~~~~~~~~~~~~~~

Data is retrieved only when needed:

.. code-block:: python

   # This doesn't query the database yet
   product_dim = LXIndexDimension(Product, lambda p: p.id).from_model(session)

   # Database query happens here during model solving
   optimizer.solve(model)

Next Steps
----------

- :doc:`single-model` - Master single-model indexing
- :doc:`multi-model` - Learn multi-dimensional indexing
- :doc:`dimensions` - Understand index dimensions
- :doc:`filtering` - Optimize with filtering strategies
- :doc:`/examples/index` - See complete working examples

See Also
--------

- :doc:`/user-guide/core/variables` - Variables that use indexing
- :doc:`/user-guide/core/constraints` - Constraints with indexing
- Driver Scheduling Example (examples/02_driver_scheduling) - Complete multi-model example
- Production Planning Example (examples/01_production_planning) - Single-model example
