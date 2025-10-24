Solution Module API
===================

The solution module provides classes for working with optimization solutions, including
variable value access, sensitivity analysis, and solution mapping.

Overview
--------

The solution module implements type-safe solution handling with automatic mapping from
solver indices to user data:

.. mermaid::

   graph LR
       A[Solver] --> B[LXSolution]
       B --> C[Variable Values]
       B --> D[Mapped Values]
       B --> E[Sensitivity Data]
       B --> F[Goal Deviations]
       G[LXSolutionMapper] --> D
       H[Data Models] --> G

       style B fill:#e1f5ff
       style C fill:#fff4e1
       style D fill:#ffe1e1
       style E fill:#e1ffe1
       style F fill:#f0e1ff

Components
----------

Solution Container
~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.solution.solution.LXSolution

The :class:`~lumix.solution.solution.LXSolution` class provides comprehensive access to:

- Variable values (direct and mapped)
- Solution metadata (status, objective, solve time)
- Sensitivity analysis data (shadow prices, reduced costs)
- Goal programming information (deviations, satisfaction)

Solution Mapper
~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.solution.mapping.LXSolutionMapper

The :class:`~lumix.solution.mapping.LXSolutionMapper` class provides utilities for:

- Mapping solution values to model instances
- Handling single-indexed variables
- Processing multi-indexed variables
- Working with cartesian product results

Detailed API Reference
----------------------

LXSolution
~~~~~~~~~~

.. automodule:: lumix.solution.solution
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

**Key Attributes:**

- ``objective_value``: Final objective function value
- ``status``: Solution status string (optimal, feasible, infeasible, etc.)
- ``solve_time``: Time taken to solve in seconds
- ``variables``: Dictionary mapping variable names to values (solver indices)
- ``mapped``: Dictionary mapping variable names to values (data keys)
- ``shadow_prices``: Shadow prices (dual values) for constraints
- ``reduced_costs``: Reduced costs for variables
- ``gap``: Optimality gap (for MIP)
- ``iterations``: Number of solver iterations
- ``nodes``: Number of branch-and-bound nodes
- ``goal_deviations``: Deviation values for goal programming

**Key Methods:**

- ``get_variable(var)``: Get variable value with type inference
- ``get_mapped(var)``: Get values mapped by index keys
- ``get_shadow_price(constraint_name)``: Get shadow price for constraint
- ``get_reduced_cost(var_name)``: Get reduced cost for variable
- ``get_goal_deviations(goal_name)``: Get goal deviation values
- ``is_goal_satisfied(goal_name, tolerance)``: Check if goal is achieved
- ``get_total_deviation(goal_name)``: Get total absolute deviation
- ``is_optimal()``: Check if solution is optimal
- ``is_feasible()``: Check if solution is feasible
- ``summary()``: Get formatted solution summary

LXSolutionMapper
~~~~~~~~~~~~~~~~

.. automodule:: lumix.solution.mapping
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

**Key Methods:**

- ``map_variable_to_models(var, solution_values, model_instances)``: Map solution values to model instances for single-indexed variables
- ``map_multi_indexed_variable(var, solution_values)``: Map solution values to model instance tuples for multi-indexed variables

Usage Examples
--------------

Basic Solution Access
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXOptimizer, LXModel, LXVariable

   # Solve model
   optimizer = LXOptimizer().use_solver("gurobi")
   solution = optimizer.solve(model)

   # Check status
   if solution.is_optimal():
       print(f"Optimal objective: {solution.objective_value:.2f}")

   # Access variable values
   for key, value in solution.get_mapped(production).items():
       print(f"Product {key}: {value} units")

Sensitivity Analysis
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get shadow price
   shadow_price = solution.get_shadow_price("capacity_constraint")
   if shadow_price:
       print(f"Value of additional capacity: ${shadow_price:.2f}")

   # Get reduced cost
   reduced_cost = solution.get_reduced_cost("production[product_A]")
   if reduced_cost:
       print(f"Cost reduction needed: ${reduced_cost:.2f}")

Goal Programming
~~~~~~~~~~~~~~~~

.. code-block:: python

   # Check goal satisfaction
   if solution.is_goal_satisfied("demand_target"):
       print("Demand goal achieved!")
   else:
       deviations = solution.get_goal_deviations("demand_target")
       print(f"Positive deviation: {deviations['pos']}")
       print(f"Negative deviation: {deviations['neg']}")

   # Get total deviation
   total_dev = solution.get_total_deviation("demand_target")
   print(f"Total deviation: {total_dev:.2f}")

Solution Mapping
~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.solution import LXSolutionMapper

   # Create mapper
   mapper = LXSolutionMapper[Product]()

   # Map to model instances
   instance_values = mapper.map_variable_to_models(
       var=production,
       solution_values=solution.mapped["production"],
       model_instances=products
   )

   # Process by instance
   for product, quantity in instance_values.items():
       print(f"{product.name}: {quantity} units")

Multi-Indexed Variables
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Map multi-indexed solution
   instance_map = mapper.map_multi_indexed_variable(
       var=assignment,
       solution_values=solution.mapped["assignment"]
   )

   # Result: {(Driver(id=1), Date(date="2024-01-01")): 1, ...}
   for (driver, date), assigned in instance_map.items():
       if assigned > 0.5:
           print(f"{driver.name} assigned on {date.date}")

Solution Summary
~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get formatted summary
   print(solution.summary())

Output::

   Status: optimal
   Objective: 12345.678900
   Solve time: 0.123s
   Non-zero variables: 42/100
   Gap: 0.00%
   Iterations: 125

   Goal Constraints: 3
   Goals Satisfied: 2/3

Type Hints
----------

The solution module is fully type-annotated:

.. code-block:: python

   from typing import Dict, Any, Union, Optional, Tuple
   from lumix.solution import LXSolution, LXSolutionMapper
   from lumix.core import LXVariable

   # Type-safe solution access
   solution: LXSolution[Product]
   value: Union[float, Dict[Any, float]] = solution.get_variable(production)

   # Type-safe mapping
   mapper: LXSolutionMapper[Product]
   instance_map: Dict[Product, float] = mapper.map_variable_to_models(...)

Related Documentation
---------------------

User Guide
~~~~~~~~~~

- :doc:`/user-guide/solution/index` - Solution handling overview
- :doc:`/user-guide/solution/accessing-solutions` - Accessing variable values
- :doc:`/user-guide/solution/sensitivity-analysis` - Shadow prices and reduced costs
- :doc:`/user-guide/solution/goal-programming` - Goal programming solutions
- :doc:`/user-guide/solution/mapping` - Solution mapping to data models

Development Guide
~~~~~~~~~~~~~~~~~

- :doc:`/development/solution-architecture` - Solution module architecture
- :doc:`/development/extending-solution` - Extending solution functionality

See Also
--------

- :doc:`/api/core/index` - Core module (variables, constraints, models)
- :doc:`/api/nonlinear/index` - Nonlinear terms
- :doc:`/api/linearization/index` - Automatic linearization
- :doc:`/api/utils/index` - Utility components
