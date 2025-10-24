Indexing Module API
===================

The indexing module provides powerful multi-dimensional indexing capabilities for creating
variables and constraints indexed by one or more data models with type safety and filtering support.

Overview
--------

The indexing module enables data-driven modeling through two key components that work together
to create flexible, type-safe multi-dimensional index spaces:

.. mermaid::

   graph LR
       A[Data Models] --> B[LXIndexDimension]
       B --> C[LXCartesianProduct]
       C --> D[Multi-Model Variables]
       C --> E[Multi-Model Constraints]
       F[Filters] --> B
       G[Cross-Filters] --> C

       style A fill:#e1f5ff
       style B fill:#fff4e1
       style C fill:#ffe1e1
       style D fill:#e1ffe1
       style E fill:#f0e1ff

**Key Features:**

- **Type-Safe**: Full generic type support with IDE autocomplete
- **Data-Driven**: Automatic expansion based on data instances
- **Filtering**: Both per-dimension and cross-dimension filtering
- **Sparse Indexing**: Only create variables/constraints for valid combinations
- **ORM Integration**: Works with direct data or ORM queries

Components
----------

Index Dimension
~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.indexing.dimensions.LXIndexDimension

The :class:`~lumix.indexing.dimensions.LXIndexDimension` class represents a single dimension
in multi-dimensional indexing with:

- Model type specification
- Index key extraction
- Per-dimension filtering
- Data source configuration (direct data or ORM)

Cartesian Product
~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.indexing.cartesian.LXCartesianProduct

The :class:`~lumix.indexing.cartesian.LXCartesianProduct` class combines multiple dimensions
to create multi-dimensional index spaces with:

- Combination of 2+ dimensions
- Cross-dimension filtering
- Tuple-based indexing
- Sparse index generation

Detailed API Reference
----------------------

LXIndexDimension
~~~~~~~~~~~~~~~~

.. automodule:: lumix.indexing.dimensions
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

**Key Attributes:**

- ``model_type``: The Python class representing the data model
- ``key_func``: Function to extract index keys from instances
- ``filter_func``: Optional predicate to filter instances
- ``label``: Optional human-readable label

**Key Methods:**

- ``from_data(data)``: Provide data instances directly
- ``from_model(session)``: Query data from ORM session
- ``where(predicate)``: Apply per-dimension filtering
- ``get_instances()``: Retrieve filtered instances

LXCartesianProduct
~~~~~~~~~~~~~~~~~~

.. automodule:: lumix.indexing.cartesian
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

**Key Attributes:**

- ``dimensions``: List of index dimensions
- ``_cross_filter``: Optional cross-dimension filter predicate

**Key Methods:**

- ``add_dimension(dim)``: Add another dimension (for 3D+)
- ``where(predicate)``: Apply cross-dimension filtering

Usage Examples
--------------

Single-Dimension Indexing
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXVariable, LXIndexDimension

   # Create dimension for products
   product_dim = (
       LXIndexDimension(Product, lambda p: p.sku)
       .from_data(products)
       .where(lambda p: p.in_stock)
   )

   # Create variable indexed by products
   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .indexed_by(lambda p: p.sku)
       .from_data(products)
       .where(lambda p: p.in_stock)
   )

Two-Dimensional Indexing
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXVariable, LXIndexDimension
   from typing import Tuple

   # Create dimensions
   driver_dim = LXIndexDimension(Driver, lambda d: d.id).from_data(drivers)
   date_dim = LXIndexDimension(Date, lambda dt: dt.date).from_data(dates)

   # Create multi-indexed variable with cross-dimension filter
   assignment = (
       LXVariable[Tuple[Driver, Date], int]("assignment")
       .binary()
       .indexed_by_product(driver_dim, date_dim)
       .where_multi(lambda driver, date: driver.is_available(date))
   )

   # Access variable values
   for driver in drivers:
       for date in dates:
           if driver.is_available(date):
               print(f"assignment[{driver}, {date}] = {assignment[driver, date]}")

Three-Dimensional Indexing
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXCartesianProduct, LXIndexDimension

   # Create three dimensions
   warehouse_dim = LXIndexDimension(Warehouse, lambda w: w.id).from_data(warehouses)
   product_dim = LXIndexDimension(Product, lambda p: p.sku).from_data(products)
   month_dim = LXIndexDimension(Month, lambda m: m.id).from_data(months)

   # Create 3D cartesian product
   inventory = (
       LXVariable[Tuple[Warehouse, Product, Month], float]("inventory")
       .continuous()
       .indexed_by_product(warehouse_dim, product_dim, month_dim)
       .where_multi(lambda w, p, m: w.stocks_product(p) and m.is_active)
   )

Per-Dimension vs Cross-Dimension Filtering
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXIndexDimension

   # Per-dimension filter: applied within each dimension
   active_drivers = (
       LXIndexDimension(Driver, lambda d: d.id)
       .from_data(drivers)
       .where(lambda d: d.is_active and d.years_experience >= 2)
   )

   weekdays = (
       LXIndexDimension(Date, lambda dt: dt.date)
       .from_data(dates)
       .where(lambda dt: dt.is_weekday)
   )

   # Cross-dimension filter: applied to combinations
   assignment = (
       LXVariable[Tuple[Driver, Date], int]("assignment")
       .binary()
       .indexed_by_product(active_drivers, weekdays)
       .where_multi(lambda driver, date:
           date not in driver.days_off and
           driver.is_available(date)
       )
   )

ORM Integration
~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXIndexDimension
   from sqlalchemy.orm import Session

   # Use ORM session instead of direct data
   driver_dim = (
       LXIndexDimension(Driver, lambda d: d.id)
       .from_model(db_session)
       .where(lambda d: d.is_active)
   )

   # Data is queried lazily when needed
   active_drivers = driver_dim.get_instances()

Sparse Indexing
~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXVariable, LXIndexDimension
   from typing import Tuple

   # Create route network with only valid connections
   routes = (
       LXVariable[Tuple[City, City], float]("flow")
       .continuous()
       .indexed_by_product(
           LXIndexDimension(City, lambda c: c.id).from_data(cities),
           LXIndexDimension(City, lambda c: c.id).from_data(cities)
       )
       .where_multi(lambda origin, dest:
           origin != dest and  # No self-loops
           (origin, dest) in valid_routes  # Only valid connections
       )
   )

   # Only valid (origin, dest) pairs create variables
   print(f"Created {len(routes.variables)} route variables")

Type Hints
----------

The indexing module is fully type-annotated for IDE support:

.. code-block:: python

   from typing import Tuple, Callable, List
   from lumix.indexing import LXIndexDimension, LXCartesianProduct

   # Type-safe dimension creation
   driver_dim: LXIndexDimension[Driver] = (
       LXIndexDimension(Driver, lambda d: d.id)
       .from_data(drivers)
   )

   # Type-safe cartesian product
   product: LXCartesianProduct[Driver, Date] = LXCartesianProduct(
       LXIndexDimension(Driver, lambda d: d.id).from_data(drivers),
       LXIndexDimension(Date, lambda dt: dt.date).from_data(dates)
   )

   # Type-safe filter predicates
   driver_filter: Callable[[Driver], bool] = lambda d: d.is_active
   cross_filter: Callable[[Driver, Date], bool] = lambda d, dt: d.is_available(dt)

   # Type-safe instance retrieval
   instances: List[Driver] = driver_dim.get_instances()

Related Documentation
---------------------

User Guide
~~~~~~~~~~

- :doc:`/user-guide/indexing/index` - Indexing overview
- :doc:`/user-guide/indexing/single-model` - Single-model indexing patterns
- :doc:`/user-guide/indexing/multi-model` - Multi-model indexing patterns
- :doc:`/user-guide/indexing/dimensions` - Working with dimensions
- :doc:`/user-guide/indexing/filtering` - Filtering strategies

Development Guide
~~~~~~~~~~~~~~~~~

- :doc:`/development/indexing-architecture` - Indexing module architecture
- :doc:`/development/extending-indexing` - Extending indexing functionality

See Also
--------

- :doc:`/api/core/index` - Core module (uses indexing for variables/constraints)
- :doc:`/api/utils/index` - Utils module (ORM integration)
- :doc:`/api/solution/index` - Solution module (mapping indexed solutions)

Examples
--------

**Complete Examples:**

- Driver Scheduling (examples/02_driver_scheduling) - Comprehensive multi-dimensional example
- Production Planning (examples/01_production_planning) - Single-dimension example
- Network Flow - Multi-dimensional routing with sparse indexing
