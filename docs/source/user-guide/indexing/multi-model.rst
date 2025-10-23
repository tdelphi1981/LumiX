Multi-Model Indexing
====================

Multi-model indexing creates variables indexed by tuples of multiple data models using
cartesian products. This is LumiX's most powerful feature for complex scheduling, routing,
and allocation problems.

Concept
-------

A **multi-model indexed variable** represents a family of solver variables, one for each
valid combination of instances from multiple models:

.. code-block:: python

   from typing import Tuple

   duty = LXVariable[Tuple[Driver, Date], int]("duty").indexed_by_product(...)

   # Expands to:
   # duty[(driver1, date1)], duty[(driver1, date2)], ...
   # duty[(driver2, date1)], duty[(driver2, date2)], ...

Basic Usage
-----------

Two-Dimensional Indexing
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from typing import Tuple
   from lumix import LXVariable, LXIndexDimension

   @dataclass
   class Driver:
       id: str
       name: str
       daily_rate: float

   @dataclass
   class Date:
       date: datetime.date
       min_drivers: int

   # Define variable indexed by (Driver, Date)
   duty = (
       LXVariable[Tuple[Driver, Date], int]("duty")
       .binary()
       .indexed_by_product(
           LXIndexDimension(Driver, lambda d: d.id).from_data(drivers),
           LXIndexDimension(Date, lambda dt: dt.date).from_data(dates)
       )
       .cost_multi(lambda driver, date: driver.daily_rate)
   )

Three-Dimensional Indexing
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from typing import Tuple

   @dataclass
   class Shift:
       id: str
       start_time: str
       multiplier: float

   # Define variable indexed by (Driver, Date, Shift)
   schedule = (
       LXVariable[Tuple[Driver, Date, Shift], int]("schedule")
       .binary()
       .indexed_by_product(
           LXIndexDimension(Driver, lambda d: d.id).from_data(drivers),
           LXIndexDimension(Date, lambda dt: dt.date).from_data(dates),
           LXIndexDimension(Shift, lambda s: s.id).from_data(shifts)
       )
       .cost_multi(lambda driver, date, shift:
           driver.daily_rate * shift.multiplier
       )
   )

Cartesian Products
------------------

Creating Products
~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXCartesianProduct, LXIndexDimension

   # Method 1: Via variable definition
   duty = (
       LXVariable[Tuple[Driver, Date], int]("duty")
       .indexed_by_product(
           LXIndexDimension(Driver, lambda d: d.id).from_data(drivers),
           LXIndexDimension(Date, lambda dt: dt.date).from_data(dates)
       )
   )

   # Method 2: Explicit cartesian product
   product = LXCartesianProduct(
       LXIndexDimension(Driver, lambda d: d.id).from_data(drivers),
       LXIndexDimension(Date, lambda dt: dt.date).from_data(dates)
   )

   duty = (
       LXVariable[Tuple[Driver, Date], int]("duty")
       .binary()
       .from_data(product)
   )

Cross-Dimension Filtering
~~~~~~~~~~~~~~~~~~~~~~~~~~

Filter combinations based on relationships between models:

.. code-block:: python

   duty = (
       LXVariable[Tuple[Driver, Date], int]("duty")
       .binary()
       .indexed_by_product(
           LXIndexDimension(Driver, lambda d: d.id).from_data(drivers),
           LXIndexDimension(Date, lambda dt: dt.date).from_data(dates)
       )
       .where_multi(lambda driver, date:
           # Only create variables for valid combinations
           date.weekday() not in driver.days_off and
           driver.is_available_on(date)
       )
   )

Using Multi-Indexed Variables
------------------------------

In Objective Functions
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXLinearExpression

   # Cost function with both models
   cost_expr = (
       LXLinearExpression()
       .add_multi_term(
           duty,
           coeff=lambda driver, date: driver.daily_rate * date.overtime_mult
       )
   )

   model.minimize(cost_expr)

In Constraints
~~~~~~~~~~~~~~

**Summing Over One Dimension:**

.. code-block:: python

   # Each driver works at most 5 days
   for driver in drivers:
       model.add_constraint(
           LXConstraint(f"max_days_{driver.id}")
           .expression(
               LXLinearExpression()
               .add_multi_term(
                   duty,
                   coeff=lambda d, dt: 1.0,
                   where=lambda d, dt: d.id == driver.id  # Fix driver dimension
               )
           )
           .le()
           .rhs(5.0)
       )

   # Each date needs at least 3 drivers
   for date in dates:
       model.add_constraint(
           LXConstraint(f"coverage_{date.date}")
           .expression(
               LXLinearExpression()
               .add_multi_term(
                   duty,
                   coeff=lambda d, dt: 1.0,
                   where=lambda d, dt: dt.date == date.date  # Fix date dimension
               )
           )
           .ge()
           .rhs(float(date.min_drivers))
       )

Complete Example: Driver Scheduling
------------------------------------

.. code-block:: python

   from dataclasses import dataclass
   from datetime import date, timedelta
   from typing import Tuple
   from lumix import (
       LXModel,
       LXVariable,
       LXConstraint,
       LXLinearExpression,
       LXIndexDimension,
       LXOptimizer,
   )

   @dataclass
   class Driver:
       id: str
       name: str
       daily_rate: float
       max_days: int
       days_off: list[int]  # Weekdays (0=Monday)
       is_active: bool

   @dataclass
   class Date:
       date: date
       min_drivers: int
       overtime_multiplier: float

   # Sample data
   drivers = [
       Driver("D1", "Alice", 200, 5, [5, 6], True),
       Driver("D2", "Bob", 180, 6, [6], True),
       Driver("D3", "Carol", 220, 4, [0, 6], True),
   ]

   start_date = date(2024, 1, 1)
   dates = [
       Date(start_date + timedelta(days=i), 2, 1.5 if (start_date + timedelta(days=i)).weekday() >= 5 else 1.0)
       for i in range(7)
   ]

   # Helper function
   def is_available(driver: Driver, dt: Date) -> bool:
       return dt.date.weekday() not in driver.days_off

   # Define multi-indexed variable
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
       .cost_multi(lambda driver, date: driver.daily_rate * date.overtime_multiplier)
       .where_multi(lambda driver, date: is_available(driver, date))
   )

   # Build model
   model = (
       LXModel("driver_scheduling")
       .add_variable(duty)
       .minimize(
           LXLinearExpression()
           .add_multi_term(duty, lambda d, dt: d.daily_rate * dt.overtime_multiplier)
       )
   )

   # Constraint: Each driver works at most max_days
   for driver in drivers:
       if not driver.is_active:
           continue
       model.add_constraint(
           LXConstraint(f"max_days_{driver.id}")
           .expression(
               LXLinearExpression()
               .add_multi_term(
                   duty,
                   coeff=lambda d, dt: 1.0,
                   where=lambda d, dt: d.id == driver.id
               )
           )
           .le()
           .rhs(float(driver.max_days))
       )

   # Constraint: Each date needs minimum drivers
   for dt in dates:
       model.add_constraint(
           LXConstraint(f"coverage_{dt.date}")
           .expression(
               LXLinearExpression()
               .add_multi_term(
                   duty,
                   coeff=lambda d, date: 1.0,
                   where=lambda d, date: date.date == dt.date
               )
           )
           .ge()
           .rhs(float(dt.min_drivers))
       )

   # Solve
   optimizer = LXOptimizer().use_solver("ortools")
   solution = optimizer.solve(model)

   # Display results
   if solution.is_optimal():
       print(f"Optimal cost: ${solution.objective_value:,.2f}")
       for dt in dates:
           print(f"\n{dt.date.strftime('%A %Y-%m-%d')}:")
           for driver in drivers:
               if not driver.is_active or not is_available(driver, dt):
                   continue
               value = solution.variables["duty"].get((driver.id, dt.date), 0)
               if value > 0.5:
                   cost = driver.daily_rate * dt.overtime_multiplier
                   print(f"  {driver.name}: ${cost:.2f}")

Common Use Cases
----------------

Assignment Problems
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Worker × Task assignment
   assignment = (
       LXVariable[Tuple[Worker, Task], int]("assignment")
       .binary()
       .indexed_by_product(
           LXIndexDimension(Worker, lambda w: w.id).from_data(workers),
           LXIndexDimension(Task, lambda t: t.id).from_data(tasks)
       )
       .where_multi(lambda w, t: t.required_skill in w.skills)
   )

Transportation Problems
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Origin × Destination shipments
   shipment = (
       LXVariable[Tuple[Warehouse, Customer], float]("shipment")
       .continuous()
       .bounds(lower=0)
       .indexed_by_product(
           LXIndexDimension(Warehouse, lambda w: w.id).from_data(warehouses),
           LXIndexDimension(Customer, lambda c: c.id).from_data(customers)
       )
       .cost_multi(lambda w, c: calculate_shipping_cost(w, c))
       .where_multi(lambda w, c: w.can_serve_region(c.region))
   )

Resource Allocation
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Project × Resource × TimePeriod allocation
   allocation = (
       LXVariable[Tuple[Project, Resource, Period], float]("allocation")
       .continuous()
       .bounds(lower=0)
       .indexed_by_product(
           LXIndexDimension(Project, lambda p: p.id).from_data(projects),
           LXIndexDimension(Resource, lambda r: r.id).from_data(resources),
           LXIndexDimension(Period, lambda t: t.id).from_data(periods)
       )
       .where_multi(lambda p, r, t:
           p.start_period <= t.id <= p.end_period and
           r.type in p.required_resource_types
       )
   )

Best Practices
--------------

1. **Use type annotations for tuples:**

   .. code-block:: python

      # Good: Explicit tuple type
      duty = LXVariable[Tuple[Driver, Date], int]("duty")

      # Bad: No type information
      duty = LXVariable("duty")

2. **Filter at dimension level first:**

   .. code-block:: python

      # Good: Reduce data before cartesian product
      LXIndexDimension(Driver, lambda d: d.id).where(lambda d: d.is_active)

      # Then apply cross-dimension filters
      .where_multi(lambda d, dt: ...)

3. **Be mindful of combinatorial explosion:**

   .. code-block:: python

      # 10 × 10 = 100 variables (fine)
      # 100 × 100 = 10,000 variables (fine)
      # 1000 × 1000 = 1,000,000 variables (problematic without filtering)

4. **Use sparse indexing:**

   .. code-block:: python

      # Only create variables where needed
      .where_multi(lambda d, dt: valid_combination(d, dt))

Next Steps
----------

- :doc:`dimensions` - Deep dive into index dimensions
- :doc:`filtering` - Advanced filtering strategies
- :doc:`/examples/index` - See driver scheduling example
- :doc:`/user-guide/core/expressions` - Using multi-indexed variables in expressions
