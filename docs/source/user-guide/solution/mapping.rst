Solution Mapping
================

Learn how to map solution values back to your data models and ORM instances.

Overview
--------

The :class:`~lumix.solution.mapping.LXSolutionMapper` class provides utilities to map
solution values from solver indices back to your original data model instances.

**Why Mapping Matters**:

- Solver uses internal indices (0, 1, 2, ...)
- Your data has meaningful keys (product IDs, dates, etc.)
- ORM instances need to be correlated with solution values
- Business logic requires working with actual model objects

The Mapping Problem
-------------------

Understanding the Gap
~~~~~~~~~~~~~~~~~~~~~

When you define a variable family:

.. code-block:: python

   @dataclass
   class Product:
       id: str
       name: str
       cost: float

   products = [
       Product(id="A", name="Widget", cost=10.0),
       Product(id="B", name="Gadget", cost=15.0),
   ]

   production = (
       LXVariable[Product, float]("production")
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

The solver creates internal variables, but you need to map results back:

.. code-block:: text

   # Solver stores by keys
   solution.mapped["production"] = {"A": 10.0, "B": 20.0}

   # But you need Product instances
   for product in products:
       quantity = ???  # How to get the value for this product?

Automatic Mapping in LXSolution
--------------------------------

Built-in Mapped Access
~~~~~~~~~~~~~~~~~~~~~~

:class:`~lumix.solution.solution.LXSolution` provides automatic mapping via the
``mapped`` attribute and ``get_mapped()`` method:

.. code-block:: python

   # Automatic mapping by LumiX
   for product_id, quantity in solution.get_mapped(production).items():
       print(f"Product {product_id}: {quantity} units")

This works because:

1. Variable definition includes ``indexed_by(lambda p: p.id)``
2. LumiX stores the mapping from keys to values
3. ``get_mapped()`` returns values indexed by those keys

Using LXSolutionMapper
----------------------

For Advanced Mapping
~~~~~~~~~~~~~~~~~~~~

The :class:`~lumix.solution.mapping.LXSolutionMapper` class provides lower-level
mapping utilities for advanced scenarios:

.. code-block:: python

   from lumix.solution import LXSolutionMapper

   mapper = LXSolutionMapper[Product]()

   # Map solution values to model instances
   instance_values = mapper.map_variable_to_models(
       var=production,
       solution_values=solution.mapped["production"],
       model_instances=products
   )

   # Result: {Product(id="A"): 10.0, Product(id="B"): 20.0}
   for product, quantity in instance_values.items():
       print(f"{product.name}: {quantity} units")

Single-Indexed Variables
-------------------------

Mapping by ID
~~~~~~~~~~~~~

.. code-block:: python

   @dataclass
   class Product:
       id: str
       name: str

   products = [
       Product(id="A", name="Widget"),
       Product(id="B", name="Gadget"),
   ]

   production = (
       LXVariable[Product, float]("production")
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

   solution = optimizer.solve(model)

   # Method 1: Use get_mapped() (recommended)
   for product_id, qty in solution.get_mapped(production).items():
       # Look up product by ID
       product = next(p for p in products if p.id == product_id)
       print(f"{product.name}: {qty}")

   # Method 2: Use LXSolutionMapper
   mapper = LXSolutionMapper[Product]()
   instance_map = mapper.map_variable_to_models(
       var=production,
       solution_values=solution.mapped["production"],
       model_instances=products
   )

   for product, qty in instance_map.items():
       print(f"{product.name}: {qty}")

Mapping with Filtering
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Create lookup dictionary for efficient access
   products_by_id = {p.id: p for p in products}

   # Map and process
   for product_id, quantity in solution.get_mapped(production).items():
       product = products_by_id[product_id]

       if quantity > 0.01:  # Filter near-zero
           print(f"Produce {quantity:.2f} units of {product.name}")

Multi-Indexed Variables
------------------------

Mapping Cartesian Products
~~~~~~~~~~~~~~~~~~~~~~~~~~~

For variables indexed by multiple dimensions:

.. code-block:: python

   @dataclass
   class Driver:
       id: int
       name: str

   @dataclass
   class Date:
       date: str

   drivers = [Driver(id=1, name="Alice"), Driver(id=2, name="Bob")]
   dates = [Date(date="2024-01-01"), Date(date="2024-01-02")]

   assignment = (
       LXVariable[Tuple[Driver, Date], int]("assignment")
       .binary()
       .indexed_by_product(
           LXIndexDimension(Driver, lambda d: d.id).from_data(drivers),
           LXIndexDimension(Date, lambda dt: dt.date).from_data(dates),
       )
   )

   solution = optimizer.solve(model)

   # Method 1: Use get_mapped() for key tuples
   for (driver_id, date_str), assigned in solution.get_mapped(assignment).items():
       if assigned > 0.5:
           print(f"Driver {driver_id} assigned on {date_str}")

   # Method 2: Use LXSolutionMapper for instance tuples
   mapper = LXSolutionMapper()
   instance_map = mapper.map_multi_indexed_variable(
       var=assignment,
       solution_values=solution.mapped["assignment"]
   )

   # Result: {(Driver(id=1), Date(date="2024-01-01")): 1, ...}
   for (driver, date), assigned in instance_map.items():
       if assigned > 0.5:
           print(f"{driver.name} assigned on {date.date}")

Processing Multi-Indexed Results
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def process_assignment_solution(solution, assignment_var, drivers, dates):
       """Process multi-indexed assignment solution."""

       # Create lookup dictionaries
       drivers_by_id = {d.id: d for d in drivers}
       dates_by_str = {dt.date: dt for dt in dates}

       # Get mapped values (key tuples)
       assignments = solution.get_mapped(assignment_var)

       # Process assignments
       schedule = {}  # driver.name -> [dates]

       for (driver_id, date_str), assigned in assignments.items():
           if assigned > 0.5:  # Binary variable threshold
               driver = drivers_by_id[driver_id]
               date = dates_by_str[date_str]

               if driver.name not in schedule:
                   schedule[driver.name] = []
               schedule[driver.name].append(date.date)

       # Print schedule
       for driver_name, assigned_dates in schedule.items():
           print(f"{driver_name}: {', '.join(sorted(assigned_dates))}")

       return schedule

ORM Integration
---------------

Mapping to Database Records
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When using ORM models:

.. code-block:: python

   from sqlalchemy.orm import Session
   from lumix.utils import LXORMContext

   # Define ORM model
   class Product(Base):
       __tablename__ = "products"
       id = Column(String, primary_key=True)
       name = Column(String)
       cost = Column(Float)

   # Create variable from ORM
   production = (
       LXVariable[Product, float]("production")
       .indexed_by(lambda p: p.id)
       .from_model(Product, session=session)
   )

   solution = optimizer.solve(model)

   # Map back to ORM instances
   products = session.query(Product).all()
   products_by_id = {p.id: p for p in products}

   for product_id, quantity in solution.get_mapped(production).items():
       product = products_by_id[product_id]
       print(f"{product.name}: {quantity}")

       # Update database
       product.planned_production = quantity

   session.commit()

Bulk Updates
~~~~~~~~~~~~

.. code-block:: python

   def update_production_plan(session, solution, production_var):
       """Update production plan in database."""

       from sqlalchemy import update

       # Get all planned quantities
       planned = solution.get_mapped(production_var)

       # Bulk update
       for product_id, quantity in planned.items():
           stmt = (
               update(Product)
               .where(Product.id == product_id)
               .values(planned_production=quantity)
           )
           session.execute(stmt)

       session.commit()
       print(f"Updated {len(planned)} product production plans")

Custom Mapping Logic
--------------------

Complex Key Functions
~~~~~~~~~~~~~~~~~~~~~

For complex indexing:

.. code-block:: python

   @dataclass
   class Route:
       origin: str
       destination: str
       distance: float

   routes = [
       Route("NYC", "LA", 2800),
       Route("NYC", "CHI", 800),
   ]

   # Index by tuple
   shipment = (
       LXVariable[Route, float]("shipment")
       .indexed_by(lambda r: (r.origin, r.destination))
       .from_data(routes)
   )

   solution = optimizer.solve(model)

   # Create reverse lookup
   routes_by_key = {
       (r.origin, r.destination): r for r in routes
   }

   # Map solution to routes
   for (origin, dest), quantity in solution.get_mapped(shipment).items():
       route = routes_by_key[(origin, dest)]
       print(f"{route.origin} → {route.destination}: {quantity} units")

Hierarchical Mapping
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   @dataclass
   class Product:
       id: str
       category: str
       name: str

   def map_by_category(solution, production_var, products):
       """Group production by category."""

       from collections import defaultdict

       by_category = defaultdict(list)
       products_by_id = {p.id: p for p in products}

       for product_id, quantity in solution.get_mapped(production_var).items():
           product = products_by_id[product_id]
           by_category[product.category].append({
               'product': product,
               'quantity': quantity
           })

       # Report by category
       for category, items in by_category.items():
           total = sum(item['quantity'] for item in items)
           print(f"\\n{category} (Total: {total:.2f})")

           for item in sorted(items, key=lambda x: -x['quantity']):
               print(f"  {item['product'].name}: {item['quantity']:.2f}")

Handling Missing Mappings
--------------------------

Defensive Mapping
~~~~~~~~~~~~~~~~~

.. code-block:: python

   def safe_map_to_instances(solution_values, model_instances, key_func):
       """Safely map values to instances with error handling."""

       # Build reverse mapping
       instance_by_key = {key_func(inst): inst for inst in model_instances}

       mapped_values = {}
       missing_keys = []

       for key, value in solution_values.items():
           if key in instance_by_key:
               instance = instance_by_key[key]
               mapped_values[instance] = value
           else:
               missing_keys.append(key)

       if missing_keys:
           print(f"Warning: {len(missing_keys)} keys not found in model instances")
           print(f"Missing keys: {missing_keys[:5]}...")  # Show first 5

       return mapped_values

Handling Data Sync Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def sync_check(solution, production_var, current_products):
       """Check if solution data matches current data."""

       solution_keys = set(solution.get_mapped(production_var).keys())
       current_keys = {p.id for p in current_products}

       missing_in_solution = current_keys - solution_keys
       missing_in_current = solution_keys - current_keys

       if missing_in_solution:
           print(f"Warning: {len(missing_in_solution)} products not in solution")

       if missing_in_current:
           print(f"Warning: {len(missing_in_current)} solution keys not in current data")
           print("This may indicate data changed since model was built")

Best Practices
--------------

1. **Use get_mapped() for Most Cases**

   .. code-block:: python

      # Recommended: Use built-in mapping
      for key, value in solution.get_mapped(production).items():
          # Work with keys directly
          pass

      # Advanced: Only use LXSolutionMapper for special cases
      mapper = LXSolutionMapper()
      # ... custom mapping logic

2. **Create Lookup Dictionaries**

   .. code-block:: python

      # Good: Efficient lookup
      products_by_id = {p.id: p for p in products}

      for product_id, qty in solution.get_mapped(production).items():
          product = products_by_id[product_id]  # O(1) lookup

      # Bad: Linear search
      for product_id, qty in solution.get_mapped(production).items():
          product = next(p for p in products if p.id == product_id)  # O(n) lookup

3. **Handle Missing Mappings Gracefully**

   .. code-block:: python

      products_by_id = {p.id: p for p in products}

      for product_id, qty in solution.get_mapped(production).items():
          product = products_by_id.get(product_id)

          if product:
              print(f"{product.name}: {qty}")
          else:
              print(f"Warning: Product {product_id} not found")

4. **Validate Key Consistency**

   .. code-block:: python

      # Ensure keys match between model building and solution processing
      original_keys = {production.index_func(p) for p in products}
      solution_keys = set(solution.get_mapped(production).keys())

      assert original_keys == solution_keys, "Key mismatch!"

Common Patterns
---------------

Report Generation
~~~~~~~~~~~~~~~~~

.. code-block:: python

   def generate_production_report(solution, production_var, products):
       """Generate detailed production report."""

       products_by_id = {p.id: p for p in products}
       production_values = solution.get_mapped(production_var)

       # Calculate totals
       total_quantity = sum(production_values.values())
       total_cost = sum(
           qty * products_by_id[pid].cost
           for pid, qty in production_values.items()
       )

       # Generate report
       print("PRODUCTION REPORT")
       print("=" * 80)
       print(f"Total Quantity: {total_quantity:,.2f}")
       print(f"Total Cost: ${total_cost:,.2f}")
       print()

       print(f"{'Product':<30} {'Quantity':<15} {'Unit Cost':<12} {'Total Cost'}")
       print("-" * 80)

       for product_id, quantity in sorted(production_values.items()):
           product = products_by_id[product_id]
           total = quantity * product.cost

           print(f"{product.name:<30} {quantity:<15,.2f} ${product.cost:<11.2f} ${total:,.2f}")

Database Synchronization
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def sync_solution_to_database(session, solution, production_var):
       """Synchronize solution values to database."""

       # Get solution values
       planned_production = solution.get_mapped(production_var)

       # Query current products
       products = session.query(Product).all()
       products_by_id = {p.id: p for p in products}

       # Update with solution values
       updated_count = 0

       for product_id, quantity in planned_production.items():
           product = products_by_id.get(product_id)

           if product:
               product.planned_quantity = quantity
               updated_count += 1
           else:
               print(f"Warning: Product {product_id} not found in database")

       session.commit()
       print(f"Updated {updated_count} product records")

Next Steps
----------

- :doc:`accessing-solutions` - Learn about accessing solution values
- :doc:`sensitivity-analysis` - Perform sensitivity analysis
- :doc:`goal-programming` - Work with goal programming solutions
- :doc:`/api/solution/index` - Full API reference
