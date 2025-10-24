Using the Optimizer
===================

The :class:`~lumix.solvers.base.LXOptimizer` class is the main interface for solving optimization models in LumiX.

Overview
--------

The optimizer provides a **fluent API** for:

- Selecting solvers
- Configuring solver options
- Enabling advanced features
- Solving models
- Accessing solutions

Basic Usage
-----------

Simple Solve
~~~~~~~~~~~~

The simplest way to solve a model:

.. code-block:: python

   from lumix import LXOptimizer

   optimizer = LXOptimizer().use_solver("ortools")
   solution = optimizer.solve(model)

With Parameters
~~~~~~~~~~~~~~~

Pass solver-specific parameters:

.. code-block:: python

   solution = optimizer.solve(
       model,
       time_limit=300,       # 5 minutes maximum
       gap_tolerance=0.01,   # 1% MIP gap
   )

Fluent Configuration
~~~~~~~~~~~~~~~~~~~~

Chain methods for complex configuration:

.. code-block:: python

   optimizer = (
       LXOptimizer()
       .use_solver("gurobi")
       .enable_sensitivity()
       .enable_rational_conversion()
   )

   solution = optimizer.solve(model, time_limit=600)

Optimizer Methods
-----------------

use_solver()
~~~~~~~~~~~~

Select which solver to use:

.. code-block:: python

   # Available solvers
   optimizer = LXOptimizer().use_solver("ortools")   # Default, free
   optimizer = LXOptimizer().use_solver("gurobi")    # Commercial
   optimizer = LXOptimizer().use_solver("cplex")     # Commercial
   optimizer = LXOptimizer().use_solver("glpk")      # Free, basic
   optimizer = LXOptimizer().use_solver("cpsat")     # CP solver

**Signature:**

.. code-block:: python

   def use_solver(
       self,
       name: Literal["ortools", "gurobi", "cplex", "cpsat", "glpk"],
       **kwargs
   ) -> Self

**Parameters:**

- ``name``: Solver name (type-checked literal)
- ``**kwargs``: Solver-specific initialization parameters

enable_rational_conversion()
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Convert floating-point coefficients to rational numbers:

.. code-block:: python

   optimizer = (
       LXOptimizer()
       .use_solver("cpsat")  # CP-SAT requires integers
       .enable_rational_conversion(max_denom=10000)
   )

**Why?** Some solvers (like CP-SAT) only work with integer coefficients. This feature automatically converts floats like 0.333 to fractions like 1/3.

**Signature:**

.. code-block:: python

   def enable_rational_conversion(
       self,
       max_denom: int = 10000
   ) -> Self

**Parameters:**

- ``max_denom``: Maximum denominator for rational approximation (default: 10000)

**Example:**

.. code-block:: python

   # Model with float coefficients: 0.333 * x
   model = build_model_with_floats()

   # Automatically converts to: 333/1000 * x
   optimizer = LXOptimizer().enable_rational_conversion()
   solution = optimizer.solve(model)

enable_linearization()
~~~~~~~~~~~~~~~~~~~~~~

Automatically linearize nonlinear terms:

.. code-block:: python

   optimizer = (
       LXOptimizer()
       .use_solver("ortools")  # Doesn't support quadratic
       .enable_linearization(
           big_m=1e6,
           pwl_segments=20,
           pwl_method="sos2",
           adaptive_breakpoints=True
       )
   )

**Why?** Not all solvers support nonlinear terms (bilinear products, absolute values, min/max). This feature automatically linearizes them.

**Signature:**

.. code-block:: python

   def enable_linearization(
       self,
       big_m: float = 1e6,
       pwl_segments: int = 20,
       pwl_method: Literal["sos2", "incremental", "logarithmic"] = "sos2",
       prefer_sos2: bool = True,
       adaptive_breakpoints: bool = True,
       mccormick_tighten_bounds: bool = True,
       **kwargs
   ) -> Self

**Parameters:**

- ``big_m``: Big-M constant for conditional constraints (default: 1e6)
- ``pwl_segments``: Number of segments for piecewise-linear approximations (default: 20)
- ``pwl_method``: Method for PWL ("sos2", "incremental", "logarithmic")
- ``prefer_sos2``: Use SOS2 when solver supports it (default: True)
- ``adaptive_breakpoints``: Use adaptive breakpoint generation (default: True)
- ``mccormick_tighten_bounds``: Apply bound tightening for McCormick envelopes (default: True)

**Example:**

.. code-block:: python

   # Model with x * y bilinear products
   model = build_bilinear_model()

   optimizer = (
       LXOptimizer()
       .use_solver("ortools")
       .enable_linearization(big_m=1e5, pwl_segments=30)
   )

   # Automatically linearizes x*y using McCormick envelopes
   solution = optimizer.solve(model)

enable_sensitivity()
~~~~~~~~~~~~~~~~~~~~

Enable sensitivity analysis (shadow prices, reduced costs):

.. code-block:: python

   optimizer = LXOptimizer().enable_sensitivity()
   solution = optimizer.solve(model)

   # Access sensitivity information
   for constraint_name, shadow_price in solution.shadow_prices.items():
       print(f"{constraint_name}: {shadow_price}")

**Note:** Only supported by solvers with sensitivity analysis capability (Gurobi, CPLEX, GLPK).

solve()
~~~~~~~

Solve the optimization model:

.. code-block:: python

   solution = optimizer.solve(
       model,
       time_limit=600,
       gap_tolerance=0.01,
       **solver_params
   )

**Signature:**

.. code-block:: python

   def solve(
       self,
       model: LXModel,
       **solver_params: Any
   ) -> LXSolution

**Common Parameters:**

- ``time_limit``: Maximum solve time in seconds
- ``gap_tolerance``: MIP gap tolerance (for integer programs)

**Solver-Specific Parameters:**

**Gurobi:**

.. code-block:: python

   solution = optimizer.solve(
       model,
       Threads=4,              # Number of threads
       MIPFocus=1,             # 1=feasibility, 2=optimality, 3=bound
       Presolve=2,             # -1=auto, 0=off, 1=conservative, 2=aggressive
       Method=-1,              # -1=auto, 0=primal, 1=dual, 2=barrier
       LogToConsole=1,         # 0=off, 1=on
   )

**CPLEX:**

.. code-block:: python

   solution = optimizer.solve(
       model,
       threads=4,
       mip_emphasis=1,         # 0=balanced, 1=feasibility, 2=optimality, 3=bound, 4=hidden
       preprocessing_presolve=1,  # 0=off, 1=on
   )

**OR-Tools:**

.. code-block:: python

   solution = optimizer.solve(
       model,
       num_search_workers=4,   # Parallel workers
       log_search_progress=True,
   )

**Returns:**

:class:`~lumix.solution.solution.LXSolution` object containing:

- ``status``: Solution status ("optimal", "feasible", "infeasible", etc.)
- ``objective_value``: Optimal objective value
- ``variable_values``: Dictionary of variable values
- ``solve_time``: Time taken to solve
- ``shadow_prices``: Shadow prices (if sensitivity enabled)
- ``reduced_costs``: Reduced costs (if sensitivity enabled)

Complete Examples
-----------------

Example 1: Production Planning with Gurobi
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXModel, LXOptimizer

   # Build model
   model = build_production_model(products, resources)

   # Configure optimizer
   optimizer = (
       LXOptimizer()
       .use_solver("gurobi")
       .enable_sensitivity()
   )

   # Solve with parameters
   solution = optimizer.solve(
       model,
       time_limit=300,
       gap_tolerance=0.001,   # 0.1% gap
       Threads=8,
       MIPFocus=2,            # Focus on optimality
   )

   # Check results
   if solution.is_optimal():
       print(f"Maximum profit: ${solution.objective_value:,.2f}")

       # Show production quantities
       for product in products:
           value = solution.get_value(production, product)
           print(f"Produce {value:.0f} units of {product.name}")

       # Show shadow prices (resource values)
       for resource in resources:
           price = solution.get_shadow_price(capacity, resource)
           print(f"{resource.name} shadow price: ${price:.2f}")

Example 2: Scheduling with CP-SAT
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXModel, LXOptimizer

   # Build integer scheduling model
   model = build_scheduling_model(tasks, workers, days)

   # Use CP-SAT (requires integer coefficients)
   optimizer = (
       LXOptimizer()
       .use_solver("cpsat")
       .enable_rational_conversion()  # Convert floats to rationals
   )

   # Solve
   solution = optimizer.solve(model, time_limit=60)

   # Show assignments
   for task in tasks:
       for worker in workers:
           for day in days:
               if solution.get_value(assignment, (task, worker, day)) > 0.5:
                   print(f"{task.name} assigned to {worker.name} on {day}")

Example 3: Nonlinear Model with Linearization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXModel, LXOptimizer

   # Model with bilinear terms (price * quantity)
   model = build_pricing_model(products)

   # Use OR-Tools with automatic linearization
   optimizer = (
       LXOptimizer()
       .use_solver("ortools")
       .enable_linearization(
           big_m=1e6,
           pwl_segments=30,
           mccormick_tighten_bounds=True
       )
   )

   # Solve (automatically linearizes bilinear terms)
   solution = optimizer.solve(model)

   # Results
   for product in products:
       price = solution.get_value(price_var, product)
       quantity = solution.get_value(quantity_var, product)
       revenue = price * quantity
       print(f"{product.name}: price=${price:.2f}, qty={quantity:.0f}, revenue=${revenue:,.2f}")

Best Practices
--------------

1. **Solver Selection**

   - Start with OR-Tools (free, good for most problems)
   - Use Gurobi/CPLEX for large-scale or performance-critical problems
   - Use CP-SAT for pure integer/scheduling problems
   - Use GLPK only for very small problems or teaching

2. **Time Limits**

   - Always set a time limit for MIP problems (can run indefinitely)
   - Use ``gap_tolerance`` for MIP to stop when "good enough" solution found

3. **Linearization**

   - Enable only when needed (solver lacks native support)
   - Tune ``big_m`` based on your problem's value ranges
   - Increase ``pwl_segments`` for better nonlinear function approximations

4. **Sensitivity Analysis**

   - Enable only for LP problems or after MIP solve
   - Not all solvers support it (check capabilities)

5. **Reusing Optimizers**

   - Create optimizer once, solve multiple models
   - Configuration persists across solves

   .. code-block:: python

      optimizer = LXOptimizer().use_solver("gurobi").enable_sensitivity()

      solution1 = optimizer.solve(model1)
      solution2 = optimizer.solve(model2)  # Same configuration

Error Handling
--------------

Import Errors
~~~~~~~~~~~~~

.. code-block:: python

   try:
       optimizer = LXOptimizer().use_solver("gurobi")
       solution = optimizer.solve(model)
   except ImportError as e:
       print(f"Solver not available: {e}")
       # Fall back to OR-Tools
       optimizer = LXOptimizer().use_solver("ortools")
       solution = optimizer.solve(model)

Infeasible Models
~~~~~~~~~~~~~~~~~

.. code-block:: python

   solution = optimizer.solve(model)

   if solution.status == "infeasible":
       print("Model is infeasible!")
       # Debug: Check constraint conflicts
       # or relax some constraints

Time Limit Exceeded
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   solution = optimizer.solve(model, time_limit=60)

   if solution.status == "time_limit":
       print(f"Time limit reached. Best objective: {solution.objective_value}")
       # Use best solution found so far (if available)

Next Steps
----------

- :doc:`choosing-solver` - How to choose the right solver
- :doc:`solver-configuration` - Advanced solver configuration
- :doc:`solver-capabilities` - Understanding solver capabilities
- :doc:`advanced-features` - Callbacks, warm start, solution pools
- :doc:`/api/solvers/index` - Complete API reference
