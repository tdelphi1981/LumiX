Extending Indexing
==================

Guide for developers who want to extend or customize LumiX's indexing capabilities.

When to Extend
--------------

Consider extending the indexing module when you need:

- Specialized dimension types (e.g., time periods, geographic regions)
- Custom data sources (e.g., REST APIs, special databases)
- Advanced filtering logic (e.g., graph-based, optimization-based)
- Domain-specific index patterns (e.g., shift scheduling, network routing)

Custom Dimension Types
----------------------

Basic Custom Dimension
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.indexing import LXIndexDimension
   from datetime import datetime, timedelta
   from typing import List

   class LXTimeDimension(LXIndexDimension[datetime]):
       """Dimension for time periods with built-in filtering."""

       def __init__(self, start: datetime, end: datetime, interval: timedelta):
           """Create time dimension with automatic period generation.

           Args:
               start: Start datetime
               end: End datetime
               interval: Time interval between periods
           """
           # Generate periods
           periods = []
           current = start
           while current <= end:
               periods.append(current)
               current += interval

           # Initialize parent
           super().__init__(
               model_type=datetime,
               key_func=lambda dt: dt.isoformat()
           )
           self.from_data(periods)

       def business_hours_only(self):
           """Filter to business hours (9 AM - 5 PM)."""
           return self.where(lambda dt: 9 <= dt.hour < 17)

       def weekdays_only(self):
           """Filter to weekdays (Monday-Friday)."""
           return self.where(lambda dt: dt.weekday() < 5)

**Usage**:

.. code-block:: python

   from datetime import datetime, timedelta

   # Create time dimension for next week, hourly intervals
   time_dim = (
       LXTimeDimension(
           start=datetime.now(),
           end=datetime.now() + timedelta(days=7),
           interval=timedelta(hours=1)
       )
       .business_hours_only()
       .weekdays_only()
   )

Geographic Dimension
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dataclasses import dataclass
   from typing import Tuple

   @dataclass
   class Location:
       id: str
       name: str
       latitude: float
       longitude: float

   class LXGeographicDimension(LXIndexDimension[Location]):
       """Dimension for geographic locations with distance filtering."""

       def __init__(self, locations: List[Location]):
           super().__init__(
               model_type=Location,
               key_func=lambda loc: loc.id
           )
           self.from_data(locations)

       def within_radius(self, center: Location, max_distance_km: float):
           """Filter to locations within radius of center."""
           def distance_filter(loc: Location) -> bool:
               # Haversine distance calculation
               dist = self._calculate_distance(center, loc)
               return dist <= max_distance_km

           return self.where(distance_filter)

       def in_region(self, min_lat: float, max_lat: float,
                     min_lon: float, max_lon: float):
           """Filter to locations within bounding box."""
           return self.where(lambda loc:
               min_lat <= loc.latitude <= max_lat and
               min_lon <= loc.longitude <= max_lon
           )

       @staticmethod
       def _calculate_distance(loc1: Location, loc2: Location) -> float:
           # Haversine formula implementation
           pass

**Usage**:

.. code-block:: python

   warehouse_dim = (
       LXGeographicDimension(warehouses)
       .within_radius(center=distribution_center, max_distance_km=100)
   )

Custom Data Sources
-------------------

REST API Data Source
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import requests
   from typing import Type, TypeVar, List

   TModel = TypeVar("TModel")

   class LXAPIDimension(LXIndexDimension[TModel]):
       """Dimension that fetches data from REST API."""

       def __init__(self, model_type: Type[TModel], key_func, api_url: str):
           super().__init__(model_type, key_func)
           self.api_url = api_url

       def from_api(self, **query_params):
           """Fetch data from API."""
           response = requests.get(self.api_url, params=query_params)
           response.raise_for_status()
           data = [self.model_type(**item) for item in response.json()]
           self._data = data
           return self

**Usage**:

.. code-block:: python

   product_dim = (
       LXAPIDimension(Product, lambda p: p.id, "https://api.example.com/products")
       .from_api(category="electronics", in_stock=True)
       .where(lambda p: p.price > 0)
   )

Cached Data Source
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from functools import lru_cache
   from typing import Type, TypeVar, Callable, List

   class LXCachedDimension(LXIndexDimension[TModel]):
       """Dimension with cached data retrieval."""

       def __init__(self, model_type: Type[TModel], key_func,
                    data_loader: Callable[[], List[TModel]]):
           super().__init__(model_type, key_func)
           self._data_loader = data_loader

       @lru_cache(maxsize=1)
       def get_instances(self) -> List[TModel]:
           """Get instances with caching."""
           if self._data is None:
               self._data = self._data_loader()

           instances = self._data
           if self.filter_func:
               instances = [i for i in instances if self.filter_func(i)]

           return instances

**Usage**:

.. code-block:: python

   def load_drivers():
       # Expensive database query
       return session.query(Driver).all()

   driver_dim = LXCachedDimension(
       Driver,
       lambda d: d.id,
       data_loader=load_drivers
   ).where(lambda d: d.is_active)

Custom Cartesian Products
--------------------------

Sparse Cartesian Product
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from typing import Dict, Tuple, Set
   from lumix.indexing import LXCartesianProduct, LXIndexDimension

   class LXSparseCartesianProduct(LXCartesianProduct):
       """Cartesian product with pre-computed valid combinations."""

       def __init__(self, dim1: LXIndexDimension, dim2: LXIndexDimension,
                    valid_pairs: Set[Tuple]):
           """Initialize with valid pair set.

           Args:
               dim1: First dimension
               dim2: Second dimension
               valid_pairs: Set of (key1, key2) tuples that are valid
           """
           super().__init__(dim1, dim2)
           self.valid_pairs = valid_pairs

       def where(self, predicate):
           """Combine sparsity matrix with user predicate."""
           original_filter = self._cross_filter

           def combined_filter(m1, m2):
               # Check sparsity first (fast)
               key1 = self.dimensions[0].key_func(m1)
               key2 = self.dimensions[1].key_func(m2)
               if (key1, key2) not in self.valid_pairs:
                   return False

               # Then apply user predicate
               if original_filter and not original_filter(m1, m2):
                   return False

               return predicate(m1, m2) if predicate else True

           self._cross_filter = combined_filter
           return self

**Usage**:

.. code-block:: python

   # Pre-compute valid (driver, route) pairs
   valid_pairs = {
       (d.id, r.id)
       for d in drivers
       for r in routes
       if r.id in d.qualified_routes
   }

   # Use sparse product
   assignment = (
       LXVariable[Tuple[Driver, Route], int]("assignment")
       .binary()
       .indexed_by_product(
           LXSparseCartesianProduct(
               driver_dim,
               route_dim,
               valid_pairs=valid_pairs
           )
       )
   )

Graph-Based Product
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import networkx as nx

   class LXGraphCartesianProduct(LXCartesianProduct):
       """Cartesian product based on graph connectivity."""

       def __init__(self, dim1: LXIndexDimension, dim2: LXIndexDimension,
                    graph: nx.Graph):
           super().__init__(dim1, dim2)
           self.graph = graph

       def where_connected(self, max_distance: int = 1):
           """Filter to connected nodes within max_distance."""
           def connectivity_filter(m1, m2):
               key1 = self.dimensions[0].key_func(m1)
               key2 = self.dimensions[1].key_func(m2)

               # Check if nodes are connected
               if not self.graph.has_node(key1) or not self.graph.has_node(key2):
                   return False

               try:
                   distance = nx.shortest_path_length(self.graph, key1, key2)
                   return distance <= max_distance
               except nx.NetworkXNoPath:
                   return False

           return self.where(connectivity_filter)

**Usage**:

.. code-block:: python

   # Create network graph
   network = nx.Graph()
   for route in routes:
       network.add_edge(route.origin, route.destination)

   # Use graph-based product
   shipment = (
       LXVariable[Tuple[Origin, Destination], float]("shipment")
       .indexed_by_product(
           LXGraphCartesianProduct(origin_dim, dest_dim, network)
           .where_connected(max_distance=3)
       )
   )

Advanced Filtering
------------------

Constraint-Based Filtering
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from typing import Callable, Dict

   class LXConstraintBasedFilter:
       """Filter based on constraint satisfaction."""

       def __init__(self):
           self.constraints: List[Callable] = []

       def add_constraint(self, constraint: Callable) -> 'LXConstraintBasedFilter':
           """Add constraint predicate."""
           self.constraints.append(constraint)
           return self

       def check(self, *models) -> bool:
           """Check if all constraints are satisfied."""
           return all(constraint(*models) for constraint in self.constraints)

**Usage**:

.. code-block:: python

   filter_engine = (
       LXConstraintBasedFilter()
       .add_constraint(lambda d, dt: dt.weekday() not in d.days_off)
       .add_constraint(lambda d, dt: d.remaining_hours >= 8)
       .add_constraint(lambda d, dt: dt.required_certification in d.certifications)
   )

   duty = (
       LXVariable[Tuple[Driver, Date], int]("duty")
       .indexed_by_product(driver_dim, date_dim)
       .where_multi(filter_engine.check)
   )

Optimization-Based Filtering
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   class LXOptimizedFilter:
       """Filter that pre-computes optimal valid combinations."""

       def __init__(self, dim1: LXIndexDimension, dim2: LXIndexDimension):
           self.dim1 = dim1
           self.dim2 = dim2
           self._valid_cache: Dict[Tuple, bool] = {}

       def precompute_valid(self, checker: Callable) -> 'LXOptimizedFilter':
           """Pre-compute valid combinations."""
           instances1 = self.dim1.get_instances()
           instances2 = self.dim2.get_instances()

           for m1 in instances1:
               for m2 in instances2:
                   key = (self.dim1.key_func(m1), self.dim2.key_func(m2))
                   self._valid_cache[key] = checker(m1, m2)

           return self

       def is_valid(self, m1, m2) -> bool:
           """Check if combination is valid (uses cache)."""
           key = (self.dim1.key_func(m1), self.dim2.key_func(m2))
           return self._valid_cache.get(key, False)

**Usage**:

.. code-block:: python

   # Pre-compute valid assignments
   filter_engine = LXOptimizedFilter(driver_dim, task_dim).precompute_valid(
       lambda d, t: expensive_validation(d, t)
   )

   assignment = (
       LXVariable[Tuple[Driver, Task], int]("assignment")
       .indexed_by_product(driver_dim, task_dim)
       .where_multi(filter_engine.is_valid)
   )

Testing Custom Extensions
--------------------------

Unit Tests
~~~~~~~~~~

.. code-block:: python

   import pytest
   from datetime import datetime, timedelta

   def test_time_dimension_creation():
       """Test time dimension creates correct periods."""
       start = datetime(2024, 1, 1, 0, 0)
       end = datetime(2024, 1, 1, 23, 0)
       dim = LXTimeDimension(start, end, timedelta(hours=1))

       instances = dim.get_instances()
       assert len(instances) == 24
       assert instances[0] == start
       assert instances[-1] == end

   def test_time_dimension_business_hours():
       """Test business hours filtering."""
       start = datetime(2024, 1, 1, 0, 0)
       end = datetime(2024, 1, 1, 23, 0)
       dim = LXTimeDimension(start, end, timedelta(hours=1)).business_hours_only()

       instances = dim.get_instances()
       assert all(9 <= dt.hour < 17 for dt in instances)
       assert len(instances) == 8

Integration Tests
~~~~~~~~~~~~~~~~~

.. code-block:: python

   def test_custom_dimension_in_variable():
       """Test custom dimension works with variables."""
       time_dim = LXTimeDimension(
           start=datetime.now(),
           end=datetime.now() + timedelta(days=1),
           interval=timedelta(hours=1)
       ).business_hours_only()

       schedule = (
           LXVariable[Tuple[Worker, datetime], int]("schedule")
           .binary()
           .indexed_by_product(worker_dim, time_dim)
       )

       instances = schedule.get_instances()
       assert all(isinstance(t, tuple) for t in instances)
       assert all(9 <= t[1].hour < 17 for t in instances)

Best Practices
--------------

1. **Preserve Type Safety**

   .. code-block:: python

      # Good: Maintain generic type parameters
      class MyDimension(LXIndexDimension[TModel]):
          pass

      # Bad: Lose type information
      class MyDimension(LXIndexDimension):
          pass

2. **Document Behavior**

   .. code-block:: python

      class LXTimeDimension(LXIndexDimension[datetime]):
          """Time dimension with automatic period generation.

          This dimension generates time periods automatically based on start,
          end, and interval parameters. It provides built-in filters for
          common temporal patterns (business hours, weekdays, etc.).

          Examples:
              Create hourly periods for next week::

                  dim = LXTimeDimension(
                      start=datetime.now(),
                      end=datetime.now() + timedelta(weeks=1),
                      interval=timedelta(hours=1)
                  )
          """

3. **Test Thoroughly**

   - Test dimension creation
   - Test filtering behavior
   - Test integration with variables
   - Test edge cases (empty data, no matches, etc.)

4. **Consider Performance**

   - Cache expensive computations
   - Use lazy evaluation when possible
   - Profile with realistic data sizes

Next Steps
----------

- :doc:`indexing-architecture` - Understand underlying architecture
- :doc:`core-architecture` - Integration with core module
- :mod:`lumix.indexing` - API reference
- :doc:`/examples/index` - See real-world usage
