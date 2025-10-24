Solution Handling
=================

This guide covers how to work with optimization solutions in LumiX.

Introduction
------------

After solving an optimization model, LumiX provides a rich :class:`~lumix.solution.solution.LXSolution` object
that gives you access to:

- **Variable values**: Get values for decision variables
- **Mapped values**: Access values indexed by original data
- **Sensitivity data**: Shadow prices and reduced costs
- **Goal programming**: Deviation values and goal satisfaction
- **Solution metadata**: Status, objective value, solve time, and solver-specific information

Philosophy
----------

Type-Safe Solution Access
~~~~~~~~~~~~~~~~~~~~~~~~~~

LumiX maintains type safety when accessing solution values:

.. code-block:: python

   # Define variable with type annotations
   production = LXVariable[Product, float]("production")

   # Solution preserves types
   solution = optimizer.solve(model)
   value = solution.get_variable(production)  # Type: Union[float, Dict[Any, float]]

Data-Driven Mapping
~~~~~~~~~~~~~~~~~~~

Solutions are automatically mapped back to your data models:

.. code-block:: python

   # Access by variable name (solver indices)
   solution.variables["production"]  # {0: 10.0, 1: 20.0, ...}

   # Access by original keys (data indices)
   solution.mapped["production"]  # {"product_A": 10.0, "product_B": 20.0, ...}

Components
----------

The solution module consists of two main components:

.. mermaid::

   graph LR
       A[Solver] --> B[LXSolution]
       B --> C[Variable Values]
       B --> D[Sensitivity Data]
       B --> E[Goal Deviations]
       F[LXSolutionMapper] --> B
       G[Data Models] --> F

       style B fill:#e1f5ff
       style C fill:#fff4e1
       style D fill:#ffe1e1
       style E fill:#e1ffe1
       style F fill:#f0e1ff

1. **LXSolution** (:class:`~lumix.solution.solution.LXSolution`): Container for solution data and metadata
2. **LXSolutionMapper** (:class:`~lumix.solution.mapping.LXSolutionMapper`): Maps solution values to ORM models

Quick Example
-------------

Basic Solution Access
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXModel, LXVariable, LXOptimizer

   # Build and solve model
   model = LXModel("production")
   production = LXVariable[Product, float]("production").from_data(products)
   # ... add constraints and objective ...

   optimizer = LXOptimizer().use_solver("gurobi")
   solution = optimizer.solve(model)

   # Check solution status
   if solution.is_optimal():
       print(f"Optimal objective: {solution.objective_value:.2f}")
       print(f"Solve time: {solution.solve_time:.2f}s")

       # Access variable values
       for key, value in solution.get_mapped(production).items():
           print(f"Product {key}: {value} units")

Sensitivity Analysis
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get shadow price (dual value) for a constraint
   shadow_price = solution.get_shadow_price("capacity")
   print(f"Value of additional capacity: ${shadow_price:.2f}")

   # Get reduced cost for a variable
   reduced_cost = solution.get_reduced_cost("production[0]")
   print(f"Reduced cost: ${reduced_cost:.2f}")

Goal Programming
~~~~~~~~~~~~~~~~

.. code-block:: python

   # Check if goal is satisfied
   if solution.is_goal_satisfied("demand_target"):
       print("Demand goal achieved!")
   else:
       # Get deviations
       deviations = solution.get_goal_deviations("demand_target")
       print(f"Positive deviation: {deviations['pos']}")
       print(f"Negative deviation: {deviations['neg']}")

   # Get total deviation across all goals
   total_dev = solution.get_total_deviation("demand_target")
   print(f"Total deviation: {total_dev:.2f}")

Detailed Guides
---------------

.. toctree::
   :maxdepth: 2

   accessing-solutions
   sensitivity-analysis
   goal-programming
   mapping

Topics Covered
--------------

Accessing Solutions
~~~~~~~~~~~~~~~~~~~

Learn how to:

- Access variable values by name or LXVariable object
- Work with scalar and indexed variables
- Handle multi-dimensional variables
- Extract solution metadata

See :doc:`accessing-solutions` for details.

Sensitivity Analysis
~~~~~~~~~~~~~~~~~~~~

Learn how to:

- Interpret shadow prices (dual values)
- Use reduced costs for sensitivity analysis
- Perform what-if analysis
- Understand solution stability

See :doc:`sensitivity-analysis` for details.

Goal Programming
~~~~~~~~~~~~~~~~

Learn how to:

- Access goal deviation values
- Check goal satisfaction
- Calculate total deviations
- Analyze multi-objective solutions

See :doc:`goal-programming` for details.

Solution Mapping
~~~~~~~~~~~~~~~~

Learn how to:

- Map solution values to ORM models
- Handle single-indexed variables
- Work with multi-indexed variables
- Process cartesian product results

See :doc:`mapping` for details.

Best Practices
--------------

1. **Always Check Status**

   .. code-block:: python

      if solution.is_optimal():
          # Process solution
          pass
      elif solution.is_feasible():
          # Sub-optimal but feasible
          pass
      else:
          # Infeasible or error
          print(f"Solution status: {solution.status}")

2. **Use Type-Safe Access**

   .. code-block:: python

      # Good: Type-safe with LXVariable object
      value = solution.get_variable(production)

      # Less ideal: String-based access
      value = solution.variables["production"]

3. **Leverage Mapped Values**

   .. code-block:: python

      # Good: Access by original data keys
      for product_id, qty in solution.get_mapped(production).items():
          product = products_by_id[product_id]
          print(f"{product.name}: {qty}")

      # Less convenient: Access by solver indices
      for idx, qty in solution.variables["production"].items():
          # Need to maintain index mapping yourself
          pass

4. **Handle Optional Values**

   .. code-block:: python

      # Sensitivity data may not be available for all solvers
      shadow_price = solution.get_shadow_price("capacity")
      if shadow_price is not None:
          print(f"Shadow price: {shadow_price}")
      else:
          print("Shadow prices not available from solver")

Common Patterns
---------------

Production Planning
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   solution = optimizer.solve(production_model)

   if solution.is_optimal():
       # Extract production quantities
       for product_id, qty in solution.get_mapped(production).items():
           if qty > 0.5:  # Filter near-zero values
               print(f"Produce {qty:.2f} units of product {product_id}")

       # Check resource utilization
       for resource_name in ["labor", "material", "capacity"]:
           shadow_price = solution.get_shadow_price(resource_name)
           if shadow_price and shadow_price > 0:
               print(f"Bottleneck: {resource_name} (value: ${shadow_price:.2f})")

Assignment Problems
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   solution = optimizer.solve(assignment_model)

   # Extract assignments (binary variables)
   assignments = solution.get_mapped(assign)
   for (worker_id, task_id), value in assignments.items():
       if value > 0.5:  # Binary variable check
           print(f"Assign worker {worker_id} to task {task_id}")

Multi-Objective Models
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   solution = optimizer.solve(goal_model)

   # Analyze goal achievement
   goals = ["profit_target", "quality_target", "service_target"]
   satisfied = sum(1 for g in goals if solution.is_goal_satisfied(g))

   print(f"Goals satisfied: {satisfied}/{len(goals)}")

   # Show deviations for unsatisfied goals
   for goal in goals:
       if not solution.is_goal_satisfied(goal):
           total_dev = solution.get_total_deviation(goal)
           print(f"{goal}: deviation = {total_dev:.2f}")

Next Steps
----------

- :doc:`accessing-solutions` - Learn to access solution values
- :doc:`sensitivity-analysis` - Perform sensitivity analysis
- :doc:`goal-programming` - Work with goal programming solutions
- :doc:`mapping` - Map solutions to data models
- :doc:`/api/solution/index` - Full API reference
