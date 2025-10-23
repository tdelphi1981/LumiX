Filtering Strategies
====================

Filtering is essential for creating efficient optimization models. LumiX provides multiple
levels of filtering to control which variables and constraints are created.

Why Filter?
-----------

**Benefits:**

- Reduce model size (fewer variables/constraints)
- Improve solve time
- Create sparse models (only valid combinations)
- Express business rules naturally

**Without filtering:**

.. code-block:: python

   # Creates variables for ALL combinations, including invalid ones
   # 100 drivers × 365 days = 36,500 variables
   assignment = (
       LXVariable[Tuple[Driver, Date], int]("assignment")
       .indexed_by_product(
           LXIndexDimension(Driver, lambda d: d.id).from_data(drivers),
           LXIndexDimension(Date, lambda dt: dt.date).from_data(dates)
       )
   )

**With filtering:**

.. code-block:: python

   # Creates variables only for valid combinations
   # ~20,000 variables after filtering
   assignment = (
       LXVariable[Tuple[Driver, Date], int]("assignment")
       .indexed_by_product(
           LXIndexDimension(Driver, lambda d: d.id)
               .where(lambda d: d.is_active)  # Per-dimension filter
               .from_data(drivers),
           LXIndexDimension(Date, lambda dt: dt.date)
               .where(lambda dt: dt >= today)  # Per-dimension filter
               .from_data(dates)
       )
       .where_multi(lambda d, dt:  # Cross-dimension filter
           dt.weekday() not in d.days_off
       )
   )

Filtering Levels
----------------

Level 1: Data Filtering
~~~~~~~~~~~~~~~~~~~~~~~~

Filter data before creating dimensions:

.. code-block:: python

   # Filter in Python before LumiX
   active_drivers = [d for d in all_drivers if d.is_active]

   dim = LXIndexDimension(Driver, lambda d: d.id).from_data(active_drivers)

Level 2: Dimension Filtering
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Filter within dimension using ``.where()``:

.. code-block:: python

   dim = (
       LXIndexDimension(Driver, lambda d: d.id)
       .from_data(all_drivers)
       .where(lambda d: d.is_active and d.years_experience >= 2)
   )

**When to use:** Simple conditions on single dimension

Level 3: Cross-Dimension Filtering
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Filter combinations using ``.where_multi()``:

.. code-block:: python

   assignment = (
       LXVariable[Tuple[Driver, Date], int]("assignment")
       .indexed_by_product(driver_dim, date_dim)
       .where_multi(lambda driver, date:
           date.weekday() not in driver.days_off and
           driver.can_work_on(date)
       )
   )

**When to use:** Relationships between dimensions

Level 4: Variable Filtering
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Filter on single-dimension variables using ``.where()``:

.. code-block:: python

   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .where(lambda p: p.is_active and p.stock > 0)
       .from_data(products)
   )

**When to use:** Simple single-model filtering

Filtering Strategies
--------------------

Strategy 1: Filter Early
~~~~~~~~~~~~~~~~~~~~~~~~~

Apply most restrictive filters first:

.. code-block:: python

   # Good: Filter at dimension level (early)
   dim = (
       LXIndexDimension(Driver, lambda d: d.id)
       .where(lambda d: d.is_active)  # Reduces from 100 to 80 drivers
       .from_data(drivers)
   )

   # Then cross-dimension filter
   .where_multi(lambda d, dt: ...)  # Operates on 80 drivers, not 100

   # Bad: Only cross-dimension filter (late)
   .where_multi(lambda d, dt: d.is_active and ...)  # Checks all 100 drivers

Strategy 2: Separate Static vs Dynamic
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Static filters (data-based) at dimension level
   driver_dim = (
       LXIndexDimension(Driver, lambda d: d.id)
       .where(lambda d: d.is_active and d.certification_valid)
       .from_data(drivers)
   )

   # Dynamic filters (relationship-based) at cross-dimension level
   assignment = (
       LXVariable[Tuple[Driver, Date], int]("assignment")
       .indexed_by_product(driver_dim, date_dim)
       .where_multi(lambda d, dt: dt.weekday() not in d.days_off)
   )

Strategy 3: Combine Simple Conditions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Good: Single where() with combined conditions
   dim = (
       LXIndexDimension(Product, lambda p: p.sku)
       .where(lambda p:
           p.in_stock and
           p.price > 0 and
           not p.discontinued and
           p.category in ["A", "B", "C"]
       )
   )

   # Avoid: Multiple where() calls (last one wins)
   dim = (
       LXIndexDimension(Product, lambda p: p.sku)
       .where(lambda p: p.in_stock)  # This is lost
       .where(lambda p: p.price > 0)  # Only this applies
   )

Common Filtering Patterns
--------------------------

Time-Based Filtering
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from datetime import date, timedelta

   today = date.today()
   next_month = today + timedelta(days=30)

   date_dim = (
       LXIndexDimension(Date, lambda dt: dt.date)
       .where(lambda dt: today <= dt.date <= next_month)
       .from_data(all_dates)
   )

Availability Filtering
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   assignment = (
       LXVariable[Tuple[Worker, Task], int]("assignment")
       .indexed_by_product(worker_dim, task_dim)
       .where_multi(lambda w, t:
           # Worker has required skills
           all(skill in w.skills for skill in t.required_skills) and
           # Worker is available during task period
           w.available_from <= t.start_date <= w.available_until and
           # Worker not already assigned to conflicting task
           not w.has_conflict(t)
       )
   )

Capacity Filtering
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   shipment = (
       LXVariable[Tuple[Warehouse, Customer], float]("shipment")
       .indexed_by_product(warehouse_dim, customer_dim)
       .where_multi(lambda w, c:
           # Warehouse has sufficient capacity
           w.remaining_capacity >= c.order_size and
           # Warehouse can serve customer region
           c.region in w.service_regions and
           # Distance is acceptable
           calculate_distance(w, c) <= MAX_DISTANCE
       )
   )

Business Rule Filtering
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   route = (
       LXVariable[Tuple[Origin, Destination], float]("route")
       .indexed_by_product(origin_dim, destination_dim)
       .where_multi(lambda o, d:
           # No self-loops
           o.id != d.id and
           # Route must be operational
           is_route_operational(o, d) and
           # Comply with regulations
           meets_regulations(o, d) and
           # Within service network
           are_connected(o, d)
       )
   )

Performance Optimization
------------------------

Measure Filter Impact
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Check how many variables are created
   print(f"Potential combinations: {len(drivers) * len(dates)}")

   # With dimension filters only
   filtered_drivers = sum(1 for d in drivers if dim_filter(d))
   filtered_dates = sum(1 for dt in dates if date_filter(dt))
   print(f"After dimension filters: {filtered_drivers * filtered_dates}")

   # After cross-dimension filters
   actual_count = sum(
       1 for d in filtered_drivers
       for dt in filtered_dates
       if cross_filter(d, dt)
   )
   print(f"After cross-dimension filters: {actual_count}")

Optimize Filter Order
~~~~~~~~~~~~~~~~~~~~~

Place most restrictive filters first:

.. code-block:: python

   # Good: Most restrictive first
   .where_multi(lambda d, dt:
       d.is_certified and  # Filters out 50% (check first)
       dt.is_weekday and  # Filters out 28% of remaining
       d.can_work_overtime  # Filters out 10% of remaining
   )

   # Less optimal: Least restrictive first
   .where_multi(lambda d, dt:
       d.can_work_overtime and  # Only filters 10%
       dt.is_weekday and  # Then filters 28%
       d.is_certified  # Then filters 50%
   )

Cache Complex Computations
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Bad: Expensive computation in filter
   .where_multi(lambda w, c:
       calculate_distance(w.location, c.location) <= MAX_DISTANCE
   )

   # Good: Pre-compute distances
   distances = {
       (w.id, c.id): calculate_distance(w.location, c.location)
       for w in warehouses
       for c in customers
   }

   .where_multi(lambda w, c:
       distances.get((w.id, c.id), float('inf')) <= MAX_DISTANCE
   )

Debugging Filters
-----------------

Count Filtered Items
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Before filtering
   print(f"Total drivers: {len(drivers)}")

   # Create dimension with filter
   dim = (
       LXIndexDimension(Driver, lambda d: d.id)
       .where(lambda d: d.is_active and d.certified)
       .from_data(drivers)
   )

   # Check filtered count
   filtered = dim.get_instances()
   print(f"Filtered drivers: {len(filtered)}")

   # Inspect filtered items
   print("Active certified drivers:")
   for driver in filtered:
       print(f"  - {driver.name}")

Test Filters Separately
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Test dimension filter
   dimension_filter = lambda d: d.is_active and d.years_experience >= 5
   passed_dim = [d for d in drivers if dimension_filter(d)]
   print(f"Passed dimension filter: {len(passed_dim)}")

   # Test cross-dimension filter
   cross_filter = lambda d, dt: dt.weekday() not in d.days_off
   passed_cross = [
       (d, dt) for d in passed_dim for dt in dates
       if cross_filter(d, dt)
   ]
   print(f"Passed cross filter: {len(passed_cross)}")

Best Practices
--------------

1. **Filter at the right level**

   .. code-block:: python

      # Data-based filters: Dimension level
      .where(lambda d: d.is_active)

      # Relationship-based filters: Cross-dimension level
      .where_multi(lambda d, dt: dt not in d.blackout_dates)

2. **Combine conditions efficiently**

   .. code-block:: python

      # Good: Short-circuit evaluation
      .where(lambda p: p.in_stock and p.price > 0 and expensive_check(p))

      # Bad: Always evaluates expensive_check
      .where(lambda p: expensive_check(p) and p.in_stock)

3. **Document complex filters**

   .. code-block:: python

      def is_valid_assignment(driver: Driver, date: Date) -> bool:
          """Check if driver can be assigned to date.

          Rules:
          - Driver must be active and certified
          - Date must not be in driver's blackout dates
          - Driver must not exceed monthly hours
          """
          return (
              driver.is_active and
              driver.is_certified and
              date not in driver.blackout_dates and
              driver.remaining_hours_this_month >= 8
          )

      assignment = (
          LXVariable[Tuple[Driver, Date], int]("assignment")
          .indexed_by_product(driver_dim, date_dim)
          .where_multi(is_valid_assignment)
      )

Next Steps
----------

- :doc:`dimensions` - Learn more about index dimensions
- :doc:`multi-model` - Apply filtering to multi-model problems
- :doc:`/user-guide/core/variables` - Variable filtering details
- :doc:`/examples/index` - See filtering in real examples
