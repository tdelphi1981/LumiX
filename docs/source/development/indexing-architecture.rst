Indexing Architecture
=====================

Deep dive into the indexing module's architecture and design patterns.

Design Philosophy
-----------------

The indexing module follows these key principles:

1. **Late Binding**: Dimensions store metadata; expansion happens during solving
2. **Type Safety**: Full generic type support with ``Generic[TModel]``
3. **Composability**: Dimensions combine via cartesian products
4. **Lazy Evaluation**: Data retrieved only when needed

Architecture Overview
---------------------

.. mermaid::

   classDiagram
       class LXIndexDimension {
           +model_type: Type[TModel]
           +key_func: Callable
           +filter_func: Optional[Callable]
           +_data: Optional[List]
           +_session: Optional[Any]
           +from_data(data)
           +from_model(session)
           +get_instances()
           +where(predicate)
       }

       class LXCartesianProduct {
           +dimensions: List[LXIndexDimension]
           +_cross_filter: Optional[Callable]
           +add_dimension(dim)
           +where(predicate)
       }

       class LXVariable {
           +_cartesian: Optional[LXCartesianProduct]
           +indexed_by_product(dim1, dim2)
           +where_multi(predicate)
           +get_instances()
       }

       LXCartesianProduct --> LXIndexDimension
       LXVariable --> LXCartesianProduct

Component Details
-----------------

LXIndexDimension
~~~~~~~~~~~~~~~~

**Purpose**: Represents a single dimension in multi-dimensional indexing.

**Key Features**:

- Generic type parameter ``TModel``
- Flexible data sources (direct data or ORM)
- Per-dimension filtering
- Lazy data retrieval

**Implementation**:

.. code-block:: python

   @dataclass
   class LXIndexDimension(Generic[TModel]):
       model_type: Type[TModel]
       key_func: Callable[[TModel], Any]
       filter_func: Optional[Callable[[TModel], bool]] = None
       _data: Optional[List[TModel]] = None
       _session: Optional[Any] = None

       def get_instances(self) -> List[TModel]:
           # 1. Retrieve data (from _data or _session)
           # 2. Apply filter_func if present
           # 3. Return filtered instances

**Data Flow**:

1. User creates dimension with model type and key function
2. User provides data source (``.from_data()`` or ``.from_model()``)
3. Optionally adds filter (``.where()``)
4. During solving, ``get_instances()`` retrieves and filters data

LXCartesianProduct
~~~~~~~~~~~~~~~~~~

**Purpose**: Combines multiple dimensions into multi-dimensional index space.

**Key Features**:

- Stores list of dimensions
- Supports 2D, 3D, N-dimensional products
- Cross-dimension filtering
- Lazy combination generation

**Implementation**:

.. code-block:: python

   class LXCartesianProduct(Generic[TModel1, TModel2]):
       def __init__(self, dim1, dim2):
           self.dimensions = [dim1, dim2]
           self._cross_filter: Optional[Callable] = None

       def add_dimension(self, dim):
           self.dimensions.append(dim)
           return self

       def where(self, predicate):
           self._cross_filter = predicate
           return self

**Expansion Logic** (in ``LXVariable.get_instances()``):

.. code-block:: python

   # 1. Get instances from each dimension
   dimension_instances = [dim.get_instances() for dim in dimensions]

   # 2. Generate cartesian product
   combinations = itertools.product(*dimension_instances)

   # 3. Apply cross-filter if present
   if cross_filter:
       combinations = [c for c in combinations if cross_filter(*c)]

   return list(combinations)

Integration with Core
~~~~~~~~~~~~~~~~~~~~~

The indexing module integrates with the core module's ``LXVariable``:

.. code-block:: python

   class LXVariable:
       _cartesian: Optional[LXCartesianProduct] = None

       def indexed_by_product(self, dim1, dim2, *extra_dims):
           self._cartesian = LXCartesianProduct(dim1, dim2)
           for dim in extra_dims:
               self._cartesian.add_dimension(dim)
           return self

       def get_instances(self):
           if self._cartesian:
               # Multi-model indexing path
               dimension_instances = [
                   dim.get_instances() for dim in self._cartesian.dimensions
               ]
               combinations = itertools.product(*dimension_instances)
               if self._cartesian._cross_filter:
                   combinations = [
                       c for c in combinations
                       if self._cartesian._cross_filter(*c)
                   ]
               return list(combinations)
           elif self._data:
               # Single-model indexing path
               return self._data
           # ...

Type System
-----------

Generics for Type Safety
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   TModel = TypeVar("TModel")

   class LXIndexDimension(Generic[TModel]):
       model_type: Type[TModel]
       # ...

**Benefits**:

- IDE autocomplete in lambdas
- mypy type checking
- Self-documenting code

**Usage**:

.. code-block:: python

   # TModel = Driver
   dim = LXIndexDimension(Driver, lambda d: d.id)
   #                                     ^ IDE knows 'd' is Driver

   # TModel1 = Driver, TModel2 = Date
   product = LXCartesianProduct(driver_dim, date_dim)

Tuple Types for Multi-Indexing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from typing import Tuple

   # Variable knows it's indexed by (Driver, Date)
   duty = LXVariable[Tuple[Driver, Date], int]("duty")

   # Lambda receives both models with full type information
   .cost_multi(lambda driver, date: driver.daily_rate * date.multiplier)
   #                  ^^^^^^  ^^^^ IDE provides autocomplete

Data Flow
---------

Model Building Phase
~~~~~~~~~~~~~~~~~~~~

.. mermaid::

   sequenceDiagram
       participant User
       participant Dimension
       participant CartesianProduct
       participant Variable

       User->>Dimension: Create with model type & key func
       User->>Dimension: from_data(drivers)
       Note over Dimension: Stores data reference
       User->>Dimension: where(lambda d: d.is_active)
       Note over Dimension: Stores filter predicate

       User->>CartesianProduct: Create(driver_dim, date_dim)
       Note over CartesianProduct: Stores dimension list
       User->>CartesianProduct: where(lambda d, dt: ...)
       Note over CartesianProduct: Stores cross-filter

       User->>Variable: indexed_by_product(...)
       Note over Variable: Stores CartesianProduct reference

**Key Point**: No data expansion yet - only metadata stored.

Solving Phase
~~~~~~~~~~~~~

.. mermaid::

   sequenceDiagram
       participant Solver
       participant Variable
       participant CartesianProduct
       participant Dimension

       Solver->>Variable: get_instances()
       Variable->>CartesianProduct: Get dimensions
       loop For each dimension
           CartesianProduct->>Dimension: get_instances()
           Dimension->>Dimension: Retrieve data (_data or _session)
           Dimension->>Dimension: Apply filter_func
           Dimension-->>CartesianProduct: Filtered instances
       end
       CartesianProduct->>CartesianProduct: Generate cartesian product
       CartesianProduct->>CartesianProduct: Apply _cross_filter
       CartesianProduct-->>Variable: Filtered combinations
       Variable-->>Solver: Final instance list

**Key Point**: Expansion and filtering happen here, not during model building.

Performance Considerations
--------------------------

Late Binding Overhead
~~~~~~~~~~~~~~~~~~~~~

**Trade-off**: Late binding adds overhead but provides flexibility.

**Mitigation**:

- Data retrieved once per solve
- Filters applied efficiently (early exit on False)
- Cartesian product uses ``itertools.product`` (memory-efficient)

Memory Usage
~~~~~~~~~~~~

**Dimension Storage**:

- Dimensions store references, not copies
- Filter predicates are small (lambda closures)

**Cartesian Product**:

- Not materialized until needed
- Can be large: O(n1 × n2 × ... × nN)
- Filters reduce size before variable creation

**Optimization**:

.. code-block:: python

   # Bad: Stores all combinations
   all_combos = list(itertools.product(drivers, dates))  # Large list

   # Good: Filters while generating
   combos = [
       (d, dt) for d in drivers for dt in dates
       if cross_filter(d, dt)
   ]  # Smaller list

Filtering Performance
~~~~~~~~~~~~~~~~~~~~~

**Filter Order Matters**:

.. code-block:: python

   # Good: Dimension filters first (reduces product size)
   driver_dim = LXIndexDimension(...).where(lambda d: expensive_check(d))
   # Operates on 100 drivers

   # Then cartesian product
   # Operates on (filtered_drivers × dates)

   # Bad: Only cross-filter
   product.where(lambda d, dt: expensive_check(d) and ...)
   # Operates on (all_drivers × dates) - much larger

Extension Points
----------------

Custom Dimension Types
~~~~~~~~~~~~~~~~~~~~~~

Subclass for specialized dimensions:

.. code-block:: python

   class LXTimeDimension(LXIndexDimension[datetime]):
       """Dimension for time periods with automatic filtering."""

       def __init__(self, start: datetime, end: datetime, interval: timedelta):
           periods = generate_periods(start, end, interval)
           super().__init__(
               datetime,
               lambda dt: dt.isoformat(),
           )
           self.from_data(periods)

       def business_hours_only(self):
           return self.where(lambda dt: 9 <= dt.hour < 17)

Custom Cartesian Products
~~~~~~~~~~~~~~~~~~~~~~~~~~

Subclass for specialized products:

.. code-block:: python

   class LXSparseCartesianProduct(LXCartesianProduct):
       """Cartesian product with built-in sparsity checking."""

       def __init__(self, dim1, dim2, sparsity_matrix):
           super().__init__(dim1, dim2)
           self.sparsity = sparsity_matrix

       def where(self, predicate):
           # Combine sparsity matrix with user predicate
           def combined(m1, m2):
               return self.sparsity.get((m1.id, m2.id), False) and predicate(m1, m2)
           self._cross_filter = combined
           return self

Testing Strategy
----------------

Unit Tests
~~~~~~~~~~

Test individual components:

.. code-block:: python

   def test_dimension_filtering():
       dim = (
           LXIndexDimension(Driver, lambda d: d.id)
           .from_data([driver1, driver2, driver3])
           .where(lambda d: d.is_active)
       )
       instances = dim.get_instances()
       assert len(instances) == 2
       assert all(d.is_active for d in instances)

   def test_cartesian_product():
       product = LXCartesianProduct(driver_dim, date_dim)
       product.where(lambda d, dt: dt.weekday() not in d.days_off)
       # Test expansion logic

Integration Tests
~~~~~~~~~~~~~~~~~

Test with variables:

.. code-block:: python

   def test_multi_indexed_variable():
       duty = (
           LXVariable[Tuple[Driver, Date], int]("duty")
           .binary()
           .indexed_by_product(driver_dim, date_dim)
           .where_multi(lambda d, dt: is_valid(d, dt))
       )
       instances = duty.get_instances()
       # Verify correct expansion

Type Tests
~~~~~~~~~~

Use mypy for static type checking:

.. code-block:: bash

   mypy src/lumix/indexing

Next Steps
----------

- :doc:`extending-indexing` - How to extend indexing components
- :doc:`core-architecture` - Integration with core module
- :doc:`design-decisions` - Why things work this way
- :mod:`lumix.indexing` - API reference
