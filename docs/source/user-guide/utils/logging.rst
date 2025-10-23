Model Logging Guide
===================

This guide covers the LXModelLogger class for tracking optimization model building,
solving progress, and solution analysis.

Overview
--------

The LXModelLogger provides domain-specific logging tailored for optimization models.
Unlike generic Python logging, it includes specialized methods for common optimization
events like model creation, variable/constraint addition, solving, and solution analysis.

**Key Benefits:**

- Automatic solve time tracking
- Consistent, formatted output for optimization events
- Configurable logging levels
- Built on Python's standard logging module

Basic Usage
-----------

Creating a Logger
~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.utils import LXModelLogger
   import logging

   # Create logger with default settings
   logger = LXModelLogger()

   # Create with custom name and level
   logger = LXModelLogger(
       name="production_model",
       level=logging.INFO  # or DEBUG, WARNING, ERROR
   )

Logging Model Construction
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXModel, LXVariable
   from lumix.utils import LXModelLogger

   logger = LXModelLogger(name="build", level=logging.DEBUG)

   # Log model creation
   model = LXModel("production_plan")
   logger.log_model_creation("production_plan", num_vars=100, num_constraints=50)

   # Log variable creation (DEBUG level)
   logger.log_variable_creation("production", "continuous", count=50)

   # Log constraint creation (DEBUG level)
   logger.log_constraint_creation("capacity", "<=", count=10)

Logging Solve Process
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXOptimizer

   logger = LXModelLogger(name="solve")

   # Start timing
   logger.log_solve_start("Gurobi")

   # Solve model
   optimizer = LXOptimizer().use_solver("gurobi")
   solution = optimizer.solve(model)

   # Log results (time automatically calculated)
   logger.log_solve_end(
       status=solution.status,
       objective_value=solution.objective_value
   )

Advanced Features
-----------------

Logging Linearization
~~~~~~~~~~~~~~~~~~~~~

When using automatic linearization, track the transformations:

.. code-block:: python

   logger = LXModelLogger(name="linearize", level=logging.DEBUG)

   # Log when linearization is applied
   logger.log_linearization(
       term_type="bilinear",
       method="McCormick",
       aux_vars=4
   )

   # Output: Linearized bilinear using McCormick (added 4 auxiliary variables)

Logging Scenario Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~

Track scenario analysis runs:

.. code-block:: python

   logger = LXModelLogger(name="scenarios")

   scenarios = [
       ("base_case", 0),
       ("high_demand", 5),
       ("low_cost", 3)
   ]

   for name, modifications in scenarios:
       logger.log_scenario(name, modifications)
       # ... run scenario ...

   # Output:
   # Running scenario 'base_case' with 0 modifications
   # Running scenario 'high_demand' with 5 modifications
   # Running scenario 'low_cost' with 3 modifications

Logging Sensitivity Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Track sensitivity analysis results:

.. code-block:: python

   logger = LXModelLogger(name="sensitivity", level=logging.DEBUG)

   for var_name, reduced_cost in sensitivity_results.items():
       logger.log_sensitivity(var_name, reduced_cost)

   # Output: Sensitivity: production[Widget_A] reduced cost = -2.500000

Generic Logging Methods
~~~~~~~~~~~~~~~~~~~~~~~

Use standard logging methods for custom messages:

.. code-block:: python

   logger = LXModelLogger(name="custom")

   # Info level
   logger.info("Starting preprocessing phase")

   # Debug level
   logger.debug(f"Constraint matrix sparsity: {sparsity:.2%}")

   # Warning level
   logger.warning("Model contains unbounded variables")

   # Error level
   logger.error("Failed to retrieve dual values")

Logging Levels
--------------

Choose the appropriate level based on your needs:

DEBUG Level
~~~~~~~~~~~

Most verbose - logs everything including variable/constraint creation:

.. code-block:: python

   logger = LXModelLogger(level=logging.DEBUG)

**Use When:**

- Development and debugging
- Detailed model analysis
- Troubleshooting model building issues

**Output Example:**

.. code-block:: text

   2025-10-22 14:30:01 - production - DEBUG - Created 50 continuous variable(s): production
   2025-10-22 14:30:01 - production - DEBUG - Created 10 constraint(s): capacity (<=)
   2025-10-22 14:30:01 - production - INFO - Created model 'ProductionPlan' with 50 variables and 10 constraints

INFO Level (Default)
~~~~~~~~~~~~~~~~~~~~

Standard level - logs major events:

.. code-block:: python

   logger = LXModelLogger(level=logging.INFO)  # or omit, it's default

**Use When:**

- Production environments
- Normal operations
- Tracking solve progress

**Output Example:**

.. code-block:: text

   2025-10-22 14:30:01 - production - INFO - Created model 'ProductionPlan' with 50 variables and 10 constraints
   2025-10-22 14:30:02 - production - INFO - Starting solve with Gurobi...
   2025-10-22 14:30:05 - production - INFO - Solve completed: Optimal | Objective: 42500.7500 | Time: 2.85s

WARNING Level
~~~~~~~~~~~~~

Only warnings and errors:

.. code-block:: python

   logger = LXModelLogger(level=logging.WARNING)

**Use When:**

- Production with minimal logging
- Only want to see problems
- Performance-critical applications

ERROR Level
~~~~~~~~~~~

Only errors:

.. code-block:: python

   logger = LXModelLogger(level=logging.ERROR)

**Use When:**

- Error tracking only
- Silent operation except for failures

Integration Examples
--------------------

Complete Model Workflow
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import logging
   from lumix import LXModel, LXVariable, LXConstraint, LXLinearExpression, LXOptimizer
   from lumix.utils import LXModelLogger

   # Create logger
   logger = LXModelLogger(name="production", level=logging.INFO)

   logger.info("=== Building Production Planning Model ===")

   # Build model
   model = LXModel("production_plan")

   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .bounds(lower=0)
       .from_data(products)
   )
   model.add_variable(production)
   logger.log_variable_creation("production", "continuous", count=len(products))

   capacity_constraint = (
       LXConstraint[Resource]("capacity")
       .expression(
           LXLinearExpression().add_term(production, lambda p, r: p.usage[r.id])
       )
       .le()
       .rhs(lambda r: r.capacity)
       .from_data(resources)
   )
   model.add_constraint(capacity_constraint)
   logger.log_constraint_creation("capacity", "<=", count=len(resources))

   model.maximize(
       LXLinearExpression().add_term(production, lambda p: p.profit)
   )

   logger.log_model_creation(
       "production_plan",
       num_vars=len(products),
       num_constraints=len(resources)
   )

   # Solve
   logger.log_solve_start("Gurobi")
   optimizer = LXOptimizer().use_solver("gurobi")
   solution = optimizer.solve(model)
   logger.log_solve_end(solution.status, solution.objective_value)

   # Solution summary
   nonzero_vars = sum(1 for v in solution.values.values() if abs(v) > 1e-6)
   logger.log_solution_summary(nonzero_vars, len(products))

   logger.info("=== Optimization Complete ===")

Multiple Models
~~~~~~~~~~~~~~~

Use different loggers for different models:

.. code-block:: python

   # Separate loggers
   logger_prod = LXModelLogger(name="production")
   logger_routing = LXModelLogger(name="routing")

   # Production model
   logger_prod.info("Building production model")
   # ... build and solve ...

   # Routing model
   logger_routing.info("Building routing model")
   # ... build and solve ...

Custom Formatting
~~~~~~~~~~~~~~~~~

Customize the log format by modifying the handler:

.. code-block:: python

   import logging

   logger = LXModelLogger(name="custom_format")

   # Get the underlying Python logger
   py_logger = logger.logger

   # Remove existing handlers
   py_logger.handlers.clear()

   # Add custom handler
   handler = logging.StreamHandler()
   handler.setFormatter(logging.Formatter(
       '[%(levelname)s] %(message)s'  # Simple format
   ))
   py_logger.addHandler(handler)

   logger.info("This uses custom format")

Best Practices
--------------

1. **Consistent Naming**

   Use descriptive, hierarchical names:

   .. code-block:: python

      # Good
      logger = LXModelLogger(name="supply_chain.production")
      logger = LXModelLogger(name="supply_chain.routing")

      # Avoid
      logger = LXModelLogger(name="logger1")

2. **Appropriate Levels**

   .. code-block:: python

      # Development: DEBUG
      logger = LXModelLogger(level=logging.DEBUG)

      # Production: INFO
      logger = LXModelLogger(level=logging.INFO)

      # Performance-critical: WARNING
      logger = LXModelLogger(level=logging.WARNING)

3. **Structured Logging**

   Log at key milestones, not in tight loops:

   .. code-block:: python

      # Good
      logger.log_variable_creation("production", "continuous", count=len(products))

      # Avoid
      for product in products:
          logger.log_variable_creation(f"x[{product.id}]", "continuous")

4. **Conditional Logging**

   For expensive log messages, use conditionals:

   .. code-block:: python

      if logger.logger.isEnabledFor(logging.DEBUG):
          expensive_message = compute_detailed_stats()
          logger.debug(expensive_message)

5. **Error Handling**

   Always log errors with context:

   .. code-block:: python

      try:
          solution = optimizer.solve(model)
      except Exception as e:
          logger.error(f"Solve failed: {e}")
          raise

Common Patterns
---------------

Progress Tracking
~~~~~~~~~~~~~~~~~

.. code-block:: python

   logger = LXModelLogger(name="progress")

   total = len(scenarios)
   for i, scenario in enumerate(scenarios, 1):
       logger.info(f"Processing scenario {i}/{total}: {scenario.name}")
       # ... process scenario ...

Performance Monitoring
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import time

   logger = LXModelLogger(name="performance")

   start = time.time()
   # ... build model ...
   build_time = time.time() - start

   logger.info(f"Model built in {build_time:.2f}s")

   logger.log_solve_start("Gurobi")
   # ... solve ...
   logger.log_solve_end(status, objective_value)

See Also
--------

- :class:`~lumix.utils.logger.LXModelLogger` - API reference
- :doc:`/api/utils/index` - Utils module API
- Python logging documentation: https://docs.python.org/3/library/logging.html
