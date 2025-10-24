Accessing Solutions
===================

Learn how to access variable values and solution metadata from optimization solutions.

Solution Object
---------------

The :class:`~lumix.solution.solution.LXSolution` class provides a comprehensive container for
optimization results, including variable values, metadata, and optional sensitivity information.

Basic Structure
~~~~~~~~~~~~~~~

.. code-block:: python

   @dataclass
   class LXSolution:
       objective_value: float
       status: str
       solve_time: float
       variables: Dict[str, Union[float, Dict[Any, float]]]
       mapped: Dict[str, Dict[Any, float]]
       shadow_prices: Dict[str, float] = field(default_factory=dict)
       reduced_costs: Dict[str, float] = field(default_factory=dict)
       gap: Optional[float] = None
       iterations: Optional[int] = None
       nodes: Optional[int] = None

Accessing Variable Values
--------------------------

By Variable Name
~~~~~~~~~~~~~~~~

Access values using the variable name (string):

.. code-block:: python

   # Scalar variable
   budget_used = solution.variables["budget"]
   print(f"Budget used: ${budget_used:.2f}")

   # Indexed variable (dict of values)
   production_values = solution.variables["production"]
   # {0: 10.0, 1: 20.0, 2: 15.0}

**When to use**: Quick access when you know the variable name.

By LXVariable Object
~~~~~~~~~~~~~~~~~~~~

Type-safe access using the variable definition:

.. code-block:: python

   production = LXVariable[Product, float]("production")
   # ... model building ...

   solution = optimizer.solve(model)

   # Type-safe access
   value = solution.get_variable(production)

**When to use**: Preferred for type safety and IDE autocomplete.

Working with Different Variable Types
--------------------------------------

Scalar Variables
~~~~~~~~~~~~~~~~

Variables with a single value:

.. code-block:: python

   # Define scalar variable
   total_cost = LXVariable[None, float]("total_cost").continuous()

   # Access value
   cost = solution.get_variable(total_cost)
   print(f"Total cost: ${cost:.2f}")

Single-Indexed Variables
~~~~~~~~~~~~~~~~~~~~~~~~~

Variables indexed by one dimension:

.. code-block:: python

   from dataclasses import dataclass

   @dataclass
   class Product:
       id: str
       name: str

   # Define indexed variable
   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

   # Access all values (solver indices)
   prod_values = solution.get_variable(production)
   # Result: {0: 10.0, 1: 20.0, 2: 15.0}

   # Access mapped values (original keys)
   mapped_values = solution.get_mapped(production)
   # Result: {"product_A": 10.0, "product_B": 20.0, "product_C": 15.0}

   # Iterate over mapped values
   for product_id, quantity in mapped_values.items():
       print(f"Product {product_id}: {quantity} units")

Multi-Indexed Variables
~~~~~~~~~~~~~~~~~~~~~~~~

Variables indexed by multiple dimensions:

.. code-block:: python

   from typing import Tuple

   @dataclass
   class Driver:
       id: int
       name: str

   @dataclass
   class Date:
       date: str

   # Define multi-indexed variable
   assignment = (
       LXVariable[Tuple[Driver, Date], int]("assignment")
       .binary()
       .indexed_by_product(
           LXIndexDimension(Driver, lambda d: d.id).from_data(drivers),
           LXIndexDimension(Date, lambda dt: dt.date).from_data(dates),
       )
   )

   # Access values
   assignments = solution.get_mapped(assignment)
   # Result: {(1, "2024-01-01"): 1, (1, "2024-01-02"): 0, ...}

   # Process multi-indexed results
   for (driver_id, date_str), value in assignments.items():
       if value > 0.5:  # For binary variables
           print(f"Driver {driver_id} assigned on {date_str}")

Mapped vs Direct Access
-----------------------

Understanding the Difference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

LumiX provides two ways to access variable values:

1. **Direct access** (``solution.variables``): Uses solver's internal indices
2. **Mapped access** (``solution.mapped``): Uses your data's original keys

.. code-block:: python

   # Direct access - solver indices
   solution.variables["production"]
   # {0: 10.0, 1: 20.0, 2: 15.0}

   # Mapped access - original keys
   solution.mapped["production"]
   # {"product_A": 10.0, "product_B": 20.0, "product_C": 15.0}

When to Use Each
~~~~~~~~~~~~~~~~

**Use mapped access** (``get_mapped()``) when:

- Working with your original data models
- Need to correlate solutions with business objects
- Building reports or outputs
- Integrating with databases/ORMs

**Use direct access** (``variables``) when:

- Debugging solver behavior
- Validating solution structure
- Working with solver-specific tools

Example Comparison
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Mapped access (preferred for most use cases)
   for product_id, qty in solution.get_mapped(production).items():
       product = products_by_id[product_id]
       print(f"{product.name}: {qty} units @ ${product.price}")

   # Direct access (requires manual index mapping)
   for idx, qty in solution.variables["production"].items():
       product = products[idx]  # Assumes index order is preserved
       print(f"{product.name}: {qty}")

Solution Metadata
-----------------

Status Checking
~~~~~~~~~~~~~~~

Check the optimization status:

.. code-block:: python

   # Check if optimal
   if solution.is_optimal():
       print("Found optimal solution")

   # Check if feasible (optimal or sub-optimal)
   if solution.is_feasible():
       print("Found feasible solution")

   # Raw status string
   print(f"Status: {solution.status}")
   # Common values: "optimal", "feasible", "infeasible", "unbounded"

Objective Value
~~~~~~~~~~~~~~~

.. code-block:: python

   print(f"Objective value: {solution.objective_value:.6f}")

   # For minimization
   print(f"Minimum cost: ${solution.objective_value:,.2f}")

   # For maximization
   print(f"Maximum profit: ${solution.objective_value:,.2f}")

Solve Time
~~~~~~~~~~

.. code-block:: python

   print(f"Solved in {solution.solve_time:.3f} seconds")

   # For performance tracking
   if solution.solve_time > 60:
       print(f"Warning: Long solve time ({solution.solve_time:.1f}s)")

Solver-Specific Information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Some solvers provide additional information:

.. code-block:: python

   # MIP gap (for integer programs)
   if solution.gap is not None:
       print(f"Optimality gap: {solution.gap * 100:.2f}%")

   # Iteration count
   if solution.iterations is not None:
       print(f"Iterations: {solution.iterations}")

   # Node count (for branch-and-bound)
   if solution.nodes is not None:
       print(f"Nodes explored: {solution.nodes}")

Solution Summary
~~~~~~~~~~~~~~~~

Get a formatted summary:

.. code-block:: python

   print(solution.summary())

Output::

   Status: optimal
   Objective: 12345.678900
   Solve time: 0.123s
   Non-zero variables: 42/100
   Gap: 0.00%
   Iterations: 125
   Nodes: 0

Filtering and Processing Results
---------------------------------

Filter Near-Zero Values
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Filter out numerical noise
   epsilon = 1e-6

   for key, value in solution.get_mapped(production).items():
       if abs(value) > epsilon:
           print(f"{key}: {value}")

Filter Binary Variables
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # For binary/integer variables
   for (worker_id, task_id), assigned in solution.get_mapped(assignment).items():
       if assigned > 0.5:  # Threshold for binary variables
           print(f"Worker {worker_id} assigned to task {task_id}")

Sort Results
~~~~~~~~~~~~

.. code-block:: python

   # Sort by value (descending)
   production_values = solution.get_mapped(production)
   sorted_products = sorted(
       production_values.items(),
       key=lambda x: x[1],
       reverse=True
   )

   print("Top 5 products by production:")
   for product_id, quantity in sorted_products[:5]:
       print(f"  {product_id}: {quantity}")

Aggregate Results
~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Total production
   total = sum(solution.get_mapped(production).values())
   print(f"Total production: {total}")

   # Production by category
   from collections import defaultdict
   by_category = defaultdict(float)

   for product_id, quantity in solution.get_mapped(production).items():
       category = products_by_id[product_id].category
       by_category[category] += quantity

   for category, total in by_category.items():
       print(f"{category}: {total}")

Error Handling
--------------

Handle Missing Values
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Check if variable exists
   if "production" in solution.variables:
       values = solution.variables["production"]
   else:
       print("Variable 'production' not found in solution")

   # Use get() with default
   budget = solution.variables.get("budget", 0.0)

Handle Infeasible Solutions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   solution = optimizer.solve(model)

   if not solution.is_feasible():
       print(f"Model is infeasible: {solution.status}")
       print("Possible issues:")
       print("  - Conflicting constraints")
       print("  - Over-constrained model")
       print("  - Incorrect bounds")
       return None

   # Continue with feasible solution
   return solution.get_mapped(production)

Handle Unbounded Solutions
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   if solution.status.lower() == "unbounded":
       print("Model is unbounded")
       print("Possible issues:")
       print("  - Missing constraints")
       print("  - Incorrect objective direction")
       print("  - Missing variable bounds")

Best Practices
--------------

1. **Always Check Status First**

   .. code-block:: python

      solution = optimizer.solve(model)

      if not solution.is_optimal():
          print(f"Warning: Solution status is {solution.status}")
          if not solution.is_feasible():
              return None  # Don't process infeasible solutions

2. **Use Mapped Access for Business Logic**

   .. code-block:: python

      # Good: Works with your data model
      for product_id, qty in solution.get_mapped(production).items():
          product = get_product(product_id)
          save_production_plan(product, qty)

      # Less ideal: Requires index management
      for idx, qty in solution.variables["production"].items():
          product = products[idx]  # Fragile

3. **Handle Optional Metadata Gracefully**

   .. code-block:: python

      # Solver may not provide all metadata
      if solution.gap is not None:
          print(f"Gap: {solution.gap * 100:.2f}%")
      else:
          print("Gap information not available")

4. **Filter Numerical Noise**

   .. code-block:: python

      epsilon = 1e-6
      significant_values = {
          k: v for k, v in solution.get_mapped(production).items()
          if abs(v) > epsilon
      }

Common Patterns
---------------

Production Planning
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def analyze_production_plan(solution, products):
       """Analyze and report production plan."""

       if not solution.is_optimal():
           print(f"Warning: Solution status is {solution.status}")

       production_values = solution.get_mapped(production)

       # Calculate metrics
       total_units = sum(production_values.values())
       total_value = sum(
           qty * products_by_id[pid].price
           for pid, qty in production_values.items()
       )

       # Generate report
       print(f"Total production: {total_units:,.0f} units")
       print(f"Total value: ${total_value:,.2f}")
       print(f"Profit: ${solution.objective_value:,.2f}")

       # List high-volume products
       high_volume = [
           (pid, qty) for pid, qty in production_values.items()
           if qty > 1000
       ]

       print(f"\nHigh-volume products ({len(high_volume)}):")
       for product_id, quantity in sorted(high_volume, key=lambda x: -x[1]):
           product = products_by_id[product_id]
           print(f"  {product.name}: {quantity:,.0f} units")

Resource Allocation
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def analyze_resource_allocation(solution, resources):
       """Analyze resource allocation and utilization."""

       allocation = solution.get_mapped(resource_allocation)

       # Calculate utilization by resource
       utilization = {}
       for (resource_id, task_id), amount in allocation.items():
           if resource_id not in utilization:
               utilization[resource_id] = 0
           utilization[resource_id] += amount

       # Report utilization
       for resource_id, used in utilization.items():
           resource = resources_by_id[resource_id]
           pct = (used / resource.capacity) * 100
           print(f"{resource.name}: {pct:.1f}% utilized ({used}/{resource.capacity})")

Next Steps
----------

- :doc:`sensitivity-analysis` - Analyze shadow prices and reduced costs
- :doc:`goal-programming` - Work with goal programming solutions
- :doc:`mapping` - Map solutions to ORM models
- :doc:`/api/solution/index` - Full API reference
