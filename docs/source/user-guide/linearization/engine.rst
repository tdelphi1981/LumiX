Linearization Engine
====================

Guide for using the main linearization engine to automatically convert nonlinear models.

Overview
--------

The :class:`~lumix.linearization.engine.LXLinearizer` class orchestrates the entire
linearization process:

1. **Scan** model for nonlinear terms
2. **Check** solver capabilities
3. **Select** appropriate linearization techniques
4. **Apply** linearization transformations
5. **Build** linearized model with auxiliary variables and constraints

Basic Usage
-----------

Simple Linearization Workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXModel
   from lumix.linearization import LXLinearizer, LXLinearizerConfig
   from lumix.solvers import LXOptimizer

   # Build model with nonlinear terms (naturally!)
   model = build_your_model()  # May contain bilinear, abs, etc.

   # Configure linearization
   config = LXLinearizerConfig(
       default_method=LXLinearizationMethod.MCCORMICK,
       pwl_num_segments=30,
       adaptive_breakpoints=True
   )

   # Get solver capability
   optimizer = LXOptimizer().use_solver("glpk")
   solver_capability = optimizer.get_capability()

   # Create linearizer
   linearizer = LXLinearizer(model, solver_capability, config)

   # Check if linearization is needed
   if linearizer.needs_linearization():
       # Linearize the model
       linearized_model = linearizer.linearize_model()

       # Solve linearized model
       solution = optimizer.solve(linearized_model)
   else:
       # Model is already linear
       solution = optimizer.solve(model)

Key Methods
-----------

Constructor
~~~~~~~~~~~

.. py:method:: __init__(model, solver_capability, config=None)

   Initialize the linearization engine.

   **Parameters:**

   - ``model`` (LXModel): Model to linearize
   - ``solver_capability`` (LXSolverCapability): Solver capability information
   - ``config`` (LXLinearizerConfig, optional): Configuration (default: LXLinearizerConfig())

   **Example:**

   .. code-block:: python

      from lumix.linearization import LXLinearizer, LXLinearizerConfig

      linearizer = LXLinearizer(
          model=my_model,
          solver_capability=solver_cap,
          config=LXLinearizerConfig()
      )

Checking for Nonlinearity
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:method:: needs_linearization()

   Check if model contains nonlinear terms requiring linearization.

   **Returns:**

   - ``bool``: True if linearization is needed

   **Example:**

   .. code-block:: python

      if linearizer.needs_linearization():
          print("Model contains nonlinear terms")
          linearized = linearizer.linearize_model()
      else:
          print("Model is already linear")

Linearizing the Model
~~~~~~~~~~~~~~~~~~~~~

.. py:method:: linearize_model()

   Linearize the entire model.

   **Returns:**

   - ``LXModel``: New linearized model with auxiliary variables and constraints

   **What Happens:**

   1. Scans objective function for nonlinear terms
   2. Scans all constraints for nonlinear terms
   3. For each nonlinear term:
      - Determines variable types
      - Selects appropriate technique
      - Creates auxiliary variables
      - Creates auxiliary constraints
   4. Builds new model with all elements

   **Example:**

   .. code-block:: python

      linearized_model = linearizer.linearize_model()

      # Original model remains unchanged
      assert model.name == "original"

      # Linearized model has suffix
      assert linearized_model.name == "original_linearized"

Getting Statistics
~~~~~~~~~~~~~~~~~~

.. py:method:: get_statistics()

   Get linearization statistics.

   **Returns:**

   - ``dict``: Dictionary with linearization statistics

   **Statistics Included:**

   - ``bilinear_terms``: Number of bilinear products linearized
   - ``piecewise_terms``: Number of piecewise-linear approximations
   - ``absolute_terms``: Number of absolute value terms
   - ``minmax_terms``: Number of min/max terms
   - ``indicator_terms``: Number of indicator constraints
   - ``auxiliary_variables``: Total auxiliary variables created
   - ``auxiliary_constraints``: Total auxiliary constraints created

   **Example:**

   .. code-block:: python

      stats = linearizer.get_statistics()

      print(f"Linearization Statistics:")
      print(f"  Bilinear terms: {stats['bilinear_terms']}")
      print(f"  PWL approximations: {stats['piecewise_terms']}")
      print(f"  Auxiliary variables: {stats['auxiliary_variables']}")
      print(f"  Auxiliary constraints: {stats['auxiliary_constraints']}")

Supported Nonlinear Terms
--------------------------

The engine automatically detects and linearizes:

Bilinear Products
~~~~~~~~~~~~~~~~~

**Term Type:** ``LXBilinearTerm``

**Example:**

.. code-block:: python

   # In model: revenue = price * quantity
   # Automatically detected and linearized

**Techniques:**

- Binary × Binary → AND logic
- Binary × Continuous → Big-M method
- Continuous × Continuous → McCormick envelopes

See :doc:`bilinear` for details.

Piecewise-Linear Functions
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Term Type:** ``LXPiecewiseLinearTerm``

**Example:**

.. code-block:: python

   # In model: cost = piecewise_function(quantity)
   # Automatically approximated

**Techniques:**

- SOS2 formulation (preferred)
- Incremental formulation
- Logarithmic formulation (future)

See :doc:`piecewise` for details.

Absolute Values
~~~~~~~~~~~~~~~

**Term Type:** ``LXAbsoluteTerm``

**Example:**

.. code-block:: python

   # In model: deviation = |actual - target|
   # Automatically linearized

**Technique:**

- Auxiliary variable with two constraints:
  - z ≥ x
  - z ≥ -x

Min/Max Functions
~~~~~~~~~~~~~~~~~

**Term Type:** ``LXMinMaxTerm``

**Example:**

.. code-block:: python

   # In model: bottleneck = max(process1_time, process2_time, process3_time)
   # Automatically linearized

**Technique:**

- min(x₁, ..., xₙ): z ≤ xᵢ for all i (z minimized)
- max(x₁, ..., xₙ): z ≥ xᵢ for all i (z maximized)

Indicator Constraints
~~~~~~~~~~~~~~~~~~~~~

**Term Type:** ``LXIndicatorTerm``

**Example:**

.. code-block:: python

   # In model: if is_open == 1 then flow >= min_flow
   # Automatically linearized using Big-M

**Technique:**

- Big-M method to convert conditional constraints

Solver Capability Awareness
----------------------------

The engine checks solver capabilities and adapts accordingly:

Native Quadratic Support
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # For Gurobi/CPLEX with quadratic support
   if not solver_capability.needs_linearization_for_bilinear():
       # Keep bilinear terms as-is (solver handles natively)
       pass
   else:
       # Linearize bilinear terms
       linearize_bilinear_term(term)

Native SOS2 Support
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # For solvers with SOS2 support
   if solver_capability.supports_sos2():
       # Use SOS2 formulation (most efficient)
       formulation = "sos2"
   else:
       # Fall back to incremental
       formulation = "incremental"

Complete Examples
-----------------

Example 1: Production Planning with Nonlinear Costs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXModel, LXVariable, LXConstraint
   from lumix.linearization import LXLinearizer, LXLinearizerConfig
   from lumix.solvers import LXOptimizer
   import math

   # Define variables
   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .bounds(lower=0, upper=1000)
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

   # Build model with nonlinear objective
   model = LXModel("production")

   # Nonlinear objective: minimize quadratic cost
   # cost = a * production² + b * production + c
   # (Simplified example - would use quadratic expression in practice)

   # Add constraints
   model.add_constraint(
       LXConstraint("capacity")
       .expression(production)
       .le()
       .rhs(5000)
   )

   # Configure linearization
   config = LXLinearizerConfig(
       default_method=LXLinearizationMethod.MCCORMICK,
       pwl_num_segments=25,
       verbose_logging=True
   )

   # Solve with linearization
   optimizer = LXOptimizer().use_solver("glpk")
   solver_cap = optimizer.get_capability()

   linearizer = LXLinearizer(model, solver_cap, config)

   if linearizer.needs_linearization():
       print("Linearizing model...")
       linearized = linearizer.linearize_model()

       # Print statistics
       stats = linearizer.get_statistics()
       print(f"Added {stats['auxiliary_variables']} auxiliary variables")
       print(f"Added {stats['auxiliary_constraints']} auxiliary constraints")

       # Solve
       solution = optimizer.solve(linearized)
   else:
       solution = optimizer.solve(model)

   print(f"Optimal cost: ${solution.objective_value:,.2f}")

Example 2: Revenue Maximization with Price-Quantity Product
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dataclasses import dataclass

   @dataclass
   class Product:
       id: str
       min_price: float
       max_price: float
       min_quantity: float
       max_quantity: float

   products = [
       Product("A", 10, 100, 0, 1000),
       Product("B", 20, 150, 0, 500),
   ]

   # Variables
   price = (
       LXVariable[Product, float]("price")
       .continuous()
       .indexed_by(lambda p: p.id)
       .bounds_func(lambda p: (p.min_price, p.max_price))
       .from_data(products)
   )

   quantity = (
       LXVariable[Product, float]("quantity")
       .continuous()
       .indexed_by(lambda p: p.id)
       .bounds_func(lambda p: (p.min_quantity, p.max_quantity))
       .from_data(products)
   )

   # Model
   model = LXModel("revenue_maximization")

   # Bilinear objective: maximize revenue = sum(price * quantity)
   # This will be automatically linearized using McCormick envelopes

   # Configure
   config = LXLinearizerConfig(
       default_method=LXLinearizationMethod.MCCORMICK,
       mccormick_tighten_bounds=True,
       verbose_logging=True
   )

   # Linearize and solve
   optimizer = LXOptimizer().use_solver("glpk")
   linearizer = LXLinearizer(
       model,
       optimizer.get_capability(),
       config
   )

   linearized = linearizer.linearize_model()
   solution = optimizer.solve(linearized)

Debugging and Validation
-------------------------

Verbose Logging
~~~~~~~~~~~~~~~

Enable detailed logging to understand what's being linearized:

.. code-block:: python

   config = LXLinearizerConfig(verbose_logging=True)
   linearizer = LXLinearizer(model, solver_cap, config)

   # Will output:
   # [Linearization] Scanning model...
   # [Linearization] Found 3 bilinear terms
   # [Linearization] Linearizing: price * quantity
   # [Linearization] Using McCormick envelopes
   # [Linearization] Created aux_mccormick_price_quantity_1
   # ...

Inspecting Auxiliary Elements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   linearized = linearizer.linearize_model()

   # Inspect auxiliary variables
   for var in linearizer.auxiliary_vars:
       print(f"Auxiliary variable: {var.name}")
       print(f"  Type: {var.var_type}")
       print(f"  Bounds: [{var.lower_bound}, {var.upper_bound}]")

   # Inspect auxiliary constraints
   for constraint in linearizer.auxiliary_constraints:
       print(f"Auxiliary constraint: {constraint.name}")
       print(f"  Sense: {constraint.sense}")

Validating Results
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Solve both original and linearized models
   original_solution = optimizer.solve(model)  # May fail if nonlinear
   linearized_solution = optimizer.solve(linearized)

   # Compare objectives (should be close)
   obj_diff = abs(original_solution.objective_value -
                  linearized_solution.objective_value)

   print(f"Objective difference: {obj_diff}")
   assert obj_diff < 1e-3, "Linearization error too large!"

Performance Considerations
--------------------------

Model Size Growth
~~~~~~~~~~~~~~~~~

Linearization adds auxiliary variables and constraints:

.. code-block:: python

   print(f"Original model:")
   print(f"  Variables: {len(model.variables)}")
   print(f"  Constraints: {len(model.constraints)}")

   linearized = linearizer.linearize_model()

   print(f"Linearized model:")
   print(f"  Variables: {len(linearized.variables)}")
   print(f"  Constraints: {len(linearized.constraints)}")

   stats = linearizer.get_statistics()
   print(f"Added: {stats['auxiliary_variables']} vars, "
         f"{stats['auxiliary_constraints']} constraints")

Balancing Accuracy and Speed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # High accuracy (slower)
   high_accuracy_config = LXLinearizerConfig(
       pwl_num_segments=50,
       adaptive_breakpoints=True,
       mccormick_tighten_bounds=True
   )

   # Faster solving (lower accuracy)
   fast_config = LXLinearizerConfig(
       pwl_num_segments=15,
       adaptive_breakpoints=False,
       mccormick_tighten_bounds=False
   )

See Also
--------

- :doc:`config` - Configuration options
- :doc:`bilinear` - Bilinear linearization
- :doc:`piecewise` - Piecewise-linear approximation
- :doc:`nonlinear-functions` - Pre-built functions
- :doc:`/api/linearization/index` - API reference
