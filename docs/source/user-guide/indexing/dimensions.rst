Index Dimensions
================

Index dimensions are the building blocks of multi-model indexing in LumiX. Each dimension
represents one axis of a multi-dimensional index space.

Overview
--------

An :class:`~lumix.indexing.dimensions.LXIndexDimension` encapsulates:

- The data model type (e.g., Driver, Product, Date)
- The indexing function (how to extract keys)
- Optional filters (which instances to include)
- Data source (direct data or ORM query)

Creating Dimensions
-------------------

Basic Dimension
~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXIndexDimension

   driver_dim = LXIndexDimension(Driver, lambda d: d.id).from_data(drivers)

With Filtering
~~~~~~~~~~~~~~

.. code-block:: python

   active_driver_dim = (
       LXIndexDimension(Driver, lambda d: d.id)
       .from_data(drivers)
       .where(lambda d: d.is_active and d.years_experience >= 2)
   )

With ORM
~~~~~~~~

.. code-block:: python

   product_dim = (
       LXIndexDimension(Product, lambda p: p.sku)
       .from_model(db_session)
       .where(lambda p: p.in_stock)
   )

Key Functions
-------------

The key function extracts a unique identifier from each model instance:

Simple Keys
~~~~~~~~~~~

.. code-block:: python

   # String ID
   LXIndexDimension(Driver, lambda d: d.id)

   # Integer ID
   LXIndexDimension(Product, lambda p: p.product_num)

   # Date
   LXIndexDimension(Date, lambda dt: dt.date)

Compound Keys
~~~~~~~~~~~~~

.. code-block:: python

   # Tuple of attributes
   LXIndexDimension(Route, lambda r: (r.origin, r.destination))

   # String concatenation
   LXIndexDimension(Location, lambda loc: f"{loc.city}_{loc.warehouse_id}")

Filtering
---------

Per-Dimension Filters
~~~~~~~~~~~~~~~~~~~~~

Applied before cartesian products:

.. code-block:: python

   # Single condition
   dim = (
       LXIndexDimension(Driver, lambda d: d.id)
       .where(lambda d: d.is_active)
       .from_data(drivers)
   )

   # Multiple conditions
   dim = (
       LXIndexDimension(Product, lambda p: p.sku)
       .where(lambda p: p.in_stock and p.price > 0 and not p.discontinued)
       .from_data(products)
   )

Filter Behavior
~~~~~~~~~~~~~~~

.. code-block:: python

   # Multiple where() calls override (don't combine)
   dim = (
       LXIndexDimension(Driver, lambda d: d.id)
       .where(lambda d: d.is_active)  # This filter is lost
       .where(lambda d: d.years_experience >= 5)  # Only this applies
   )

   # Combine conditions in one where()
   dim = (
       LXIndexDimension(Driver, lambda d: d.id)
       .where(lambda d: d.is_active and d.years_experience >= 5)
   )

Data Sources
------------

Direct Data
~~~~~~~~~~~

Use when data is already in memory:

.. code-block:: python

   products = load_products()  # List[Product]

   dim = LXIndexDimension(Product, lambda p: p.id).from_data(products)

ORM Queries
~~~~~~~~~~~

Use for database-backed models:

.. code-block:: python

   # SQLAlchemy
   dim = (
       LXIndexDimension(Product, lambda p: p.id)
       .from_model(db_session)
       .where(lambda p: p.category == "electronics")
   )

   # Django ORM
   dim = (
       LXIndexDimension(Customer, lambda c: c.id)
       .from_model(Customer.objects)
   )

Combining Dimensions
--------------------

Cartesian Products
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXCartesianProduct

   # Two dimensions
   product = LXCartesianProduct(
       LXIndexDimension(Driver, lambda d: d.id).from_data(drivers),
       LXIndexDimension(Date, lambda dt: dt.date).from_data(dates)
   )

   # Three dimensions
   product = (
       LXCartesianProduct(
           LXIndexDimension(Warehouse, lambda w: w.id).from_data(warehouses),
           LXIndexDimension(Product, lambda p: p.sku).from_data(products)
       )
       .add_dimension(LXIndexDimension(Month, lambda m: m.id).from_data(months))
   )

In Variables
~~~~~~~~~~~~

.. code-block:: python

   from typing import Tuple

   assignment = (
       LXVariable[Tuple[Driver, Date], int]("assignment")
       .binary()
       .indexed_by_product(
           LXIndexDimension(Driver, lambda d: d.id).from_data(drivers),
           LXIndexDimension(Date, lambda dt: dt.date).from_data(dates)
       )
   )

Best Practices
--------------

1. **Filter Early**

   Apply filters at the dimension level to reduce cartesian product size:

   .. code-block:: python

      # Good: Filter before product
      dim = (
          LXIndexDimension(Driver, lambda d: d.id)
          .where(lambda d: d.is_active)
          .from_data(drivers)
      )

      # Less efficient: Filter after product
      product.where(lambda d, dt: d.is_active and ...)

2. **Use Meaningful Keys**

   .. code-block:: python

      # Good: Business identifier
      LXIndexDimension(Product, lambda p: p.sku)

      # Avoid: Auto-increment if unstable
      LXIndexDimension(Product, lambda p: p.auto_id)

3. **Consistent Key Types**

   Ensure key types are hashable and consistent:

   .. code-block:: python

      # Good: Consistent types
      LXIndexDimension(Date, lambda dt: dt.date)  # Returns date object

      # Problematic: Inconsistent types
      LXIndexDimension(Date, lambda dt: str(dt.date) if dt.special else dt.date)

Advanced Patterns
-----------------

Conditional Dimensions
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Different filters based on scenario
   if scenario == "peak_season":
       driver_dim = (
           LXIndexDimension(Driver, lambda d: d.id)
           .where(lambda d: d.is_active and d.can_work_overtime)
       )
   else:
       driver_dim = (
           LXIndexDimension(Driver, lambda d: d.id)
           .where(lambda d: d.is_active)
       )

Dynamic Data Sources
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Choose data source at runtime
   if use_database:
       dim = LXIndexDimension(Product, lambda p: p.id).from_model(session)
   else:
       dim = LXIndexDimension(Product, lambda p: p.id).from_data(cached_products)

Dimension Reuse
~~~~~~~~~~~~~~~

.. code-block:: python

   # Define once, use in multiple variables
   driver_dim = (
       LXIndexDimension(Driver, lambda d: d.id)
       .where(lambda d: d.is_active)
       .from_data(drivers)
   )

   date_dim = LXIndexDimension(Date, lambda dt: dt.date).from_data(dates)

   # Use in multiple variables
   assignment = (
       LXVariable[Tuple[Driver, Date], int]("assignment")
       .indexed_by_product(driver_dim, date_dim)
   )

   backup = (
       LXVariable[Tuple[Driver, Date], int]("backup")
       .indexed_by_product(driver_dim, date_dim)
   )

Next Steps
----------

- :doc:`filtering` - Advanced filtering strategies
- :doc:`multi-model` - Using dimensions in multi-model indexing
- :mod:`lumix.indexing.dimensions` - API reference
