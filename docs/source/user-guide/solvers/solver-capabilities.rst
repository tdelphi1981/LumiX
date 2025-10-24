Solver Capabilities
===================

Understanding solver capabilities helps you choose the right solver and know when automatic linearization is needed.

Overview
--------

LumiX provides a **capability detection system** that describes what features each solver supports:

.. code-block:: python

   from lumix import GUROBI_CAPABILITIES, ORTOOLS_CAPABILITIES

   # Check what a solver supports
   print(GUROBI_CAPABILITIES.description())
   # Gurobi: Linear Programming, Mixed-Integer Programming,
   #         Quadratic Programming, Second-Order Cone Programming

   # Query specific features
   if ORTOOLS_CAPABILITIES.has_feature(LXSolverFeature.SOS2):
       print("OR-Tools supports SOS2 constraints")

Capability Classes
------------------

LXSolverCapability
~~~~~~~~~~~~~~~~~~

The main capability descriptor:

.. code-block:: python

   from lumix import LXSolverCapability, LXSolverFeature

   capability = LXSolverCapability(
       name="MySolver",
       features=LXSolverFeature.LINEAR | LXSolverFeature.INTEGER,
       max_variables=1_000_000,
       max_constraints=1_000_000,
       supports_warmstart=True,
       supports_parallel=True,
       supports_callbacks=False,
   )

**Attributes:**

- ``name``: Solver name
- ``features``: Bit flags of supported features
- ``max_variables``: Maximum number of variables
- ``max_constraints``: Maximum number of constraints
- ``supports_warmstart``: Can use previous solution as starting point
- ``supports_parallel``: Can use multiple threads
- ``supports_callbacks``: Supports lazy constraints/cuts

LXSolverFeature
~~~~~~~~~~~~~~~

Feature flags (can be combined):

.. code-block:: python

   from lumix import LXSolverFeature

   # Basic features
   LXSolverFeature.LINEAR           # Linear programming
   LXSolverFeature.INTEGER          # Integer variables
   LXSolverFeature.BINARY           # Binary variables
   LXSolverFeature.MIXED_INTEGER    # LP + INTEGER

   # Advanced features
   LXSolverFeature.QUADRATIC_CONVEX      # Convex QP
   LXSolverFeature.QUADRATIC_NONCONVEX   # Non-convex QP
   LXSolverFeature.SOCP                  # Second-order cone
   LXSolverFeature.SDP                   # Semidefinite programming

   # Special constraints
   LXSolverFeature.SOS1                  # Special Ordered Set 1
   LXSolverFeature.SOS2                  # Special Ordered Set 2
   LXSolverFeature.INDICATOR             # Indicator constraints
   LXSolverFeature.CARDINALITY           # Cardinality constraints

   # Nonlinear
   LXSolverFeature.PWL                   # Piecewise-linear
   LXSolverFeature.EXPONENTIAL_CONE      # Exponential cone
   LXSolverFeature.LOG                   # Logarithmic constraints

   # Advanced features
   LXSolverFeature.LAZY_CONSTRAINTS      # Lazy constraint callbacks
   LXSolverFeature.USER_CUTS             # User cut callbacks
   LXSolverFeature.HEURISTICS            # Custom heuristics
   LXSolverFeature.IIS                   # Irreducible Inconsistent Subsystem
   LXSolverFeature.CONFLICT_REFINEMENT   # Conflict refinement
   LXSolverFeature.SENSITIVITY_ANALYSIS  # Shadow prices, reduced costs

Pre-defined Capabilities
-------------------------

LumiX provides pre-configured capabilities for all supported solvers:

OR-Tools
~~~~~~~~

.. code-block:: python

   from lumix import ORTOOLS_CAPABILITIES

   print(ORTOOLS_CAPABILITIES.description())
   # OR-Tools: Linear Programming, Mixed-Integer Programming

**Features:**

.. code-block:: python

   ORTOOLS_CAPABILITIES = LXSolverCapability(
       name="OR-Tools",
       features=(
           LXSolverFeature.LINEAR
           | LXSolverFeature.INTEGER
           | LXSolverFeature.BINARY
           | LXSolverFeature.SOS1
           | LXSolverFeature.SOS2
           | LXSolverFeature.INDICATOR
       ),
       supports_warmstart=True,
       supports_parallel=True,
   )

**Supported:**

- ✓ Linear programming
- ✓ Integer/binary variables
- ✓ SOS1/SOS2 constraints
- ✓ Indicator constraints
- ✓ Parallel solving
- ✓ Warm start

**Not Supported:**

- ✗ Quadratic programming
- ✗ Second-order cone
- ✗ Piecewise-linear (native)
- ✗ Callbacks
- ✗ Sensitivity analysis

Gurobi
~~~~~~

.. code-block:: python

   from lumix import GUROBI_CAPABILITIES

   print(GUROBI_CAPABILITIES.description())
   # Gurobi: Linear Programming, Mixed-Integer Programming,
   #         Quadratic Programming, Second-Order Cone Programming

**Features:**

.. code-block:: python

   GUROBI_CAPABILITIES = LXSolverCapability(
       name="Gurobi",
       features=(
           LXSolverFeature.LINEAR
           | LXSolverFeature.INTEGER
           | LXSolverFeature.BINARY
           | LXSolverFeature.QUADRATIC_CONVEX
           | LXSolverFeature.QUADRATIC_NONCONVEX
           | LXSolverFeature.SOCP
           | LXSolverFeature.SOS1
           | LXSolverFeature.SOS2
           | LXSolverFeature.INDICATOR
           | LXSolverFeature.PWL
           | LXSolverFeature.LAZY_CONSTRAINTS
           | LXSolverFeature.USER_CUTS
           | LXSolverFeature.IIS
           | LXSolverFeature.CONFLICT_REFINEMENT
           | LXSolverFeature.SENSITIVITY_ANALYSIS
       ),
       supports_warmstart=True,
       supports_parallel=True,
       supports_callbacks=True,
   )

**Supported:**

- ✓ All linear features
- ✓ Quadratic (convex and non-convex)
- ✓ Second-order cone programming
- ✓ Piecewise-linear functions
- ✓ All special constraints
- ✓ Callbacks (lazy constraints, cuts)
- ✓ IIS and conflict refinement
- ✓ Sensitivity analysis

CPLEX
~~~~~

.. code-block:: python

   from lumix import CPLEX_CAPABILITIES

   # Similar to Gurobi
   print(CPLEX_CAPABILITIES.description())

**Features:** Same as Gurobi (see above)

GLPK
~~~~

.. code-block:: python

   from lumix import GLPK_CAPABILITIES

   print(GLPK_CAPABILITIES.description())
   # GLPK: Linear Programming, Mixed-Integer Programming

**Features:**

.. code-block:: python

   GLPK_CAPABILITIES = LXSolverCapability(
       name="GLPK",
       features=(
           LXSolverFeature.LINEAR
           | LXSolverFeature.INTEGER
           | LXSolverFeature.BINARY
           | LXSolverFeature.SENSITIVITY_ANALYSIS
       ),
       supports_warmstart=False,
       supports_parallel=False,
       supports_callbacks=False,
   )

**Supported:**

- ✓ Linear programming
- ✓ Integer/binary variables
- ✓ Sensitivity analysis

**Not Supported:**

- ✗ Quadratic programming
- ✗ Special constraints (SOS, indicator)
- ✗ Parallel solving
- ✗ Callbacks
- ✗ Warm start

CP-SAT
~~~~~~

.. code-block:: python

   from lumix import CPSAT_CAPABILITIES

   print(CPSAT_CAPABILITIES.description())
   # OR-Tools CP-SAT: Mixed-Integer Programming

**Features:**

.. code-block:: python

   CPSAT_CAPABILITIES = LXSolverCapability(
       name="OR-Tools CP-SAT",
       features=(
           LXSolverFeature.INTEGER
           | LXSolverFeature.BINARY
       ),
       supports_warmstart=True,
       supports_parallel=True,
       supports_callbacks=False,
   )

**Supported:**

- ✓ Integer/binary variables (only)
- ✓ Parallel solving
- ✓ Warm start (solution hints)

**Not Supported:**

- ✗ Continuous variables (CP-SAT is integer-only)
- ✗ Quadratic programming
- ✗ Callbacks

Querying Capabilities
---------------------

Check Specific Features
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import ORTOOLS_CAPABILITIES, LXSolverFeature

   # Check individual features
   if ORTOOLS_CAPABILITIES.has_feature(LXSolverFeature.LINEAR):
       print("Supports linear programming")

   if ORTOOLS_CAPABILITIES.has_feature(LXSolverFeature.QUADRATIC_CONVEX):
       print("Supports quadratic programming")
   else:
       print("Does not support quadratic - need linearization")

Convenience Methods
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import GUROBI_CAPABILITIES, ORTOOLS_CAPABILITIES

   # High-level checks
   if GUROBI_CAPABILITIES.can_solve_quadratic():
       print("Can solve quadratic problems")

   if ORTOOLS_CAPABILITIES.can_solve_integer():
       print("Can solve integer problems")

   if GUROBI_CAPABILITIES.can_use_sos2():
       print("Has native SOS2 support")

   if GUROBI_CAPABILITIES.can_use_indicator():
       print("Has native indicator constraint support")

Check Linearization Needs
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import ORTOOLS_CAPABILITIES

   # Check if linearization is needed
   if ORTOOLS_CAPABILITIES.needs_linearization_for_bilinear():
       print("Need to linearize x*y products for OR-Tools")

   if ORTOOLS_CAPABILITIES.needs_linearization_for_abs():
       print("Need to linearize |x| for OR-Tools")

   if ORTOOLS_CAPABILITIES.needs_linearization_for_minmax():
       print("Need to linearize min/max for OR-Tools")

Using Capabilities in Code
---------------------------

Automatic Feature Detection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXOptimizer

   def solve_with_best_available(model):
       """Solve using best available solver for the model."""
       # Try Gurobi first (if available)
       try:
           optimizer = LXOptimizer().use_solver("gurobi")
           if model.has_quadratic_terms():
               # Gurobi supports quadratic natively
               return optimizer.solve(model)
       except ImportError:
           pass

       # Fall back to OR-Tools with linearization
       optimizer = (
           LXOptimizer()
           .use_solver("ortools")
           .enable_linearization()  # Auto-linearize if needed
       )
       return optimizer.solve(model)

Capability-Aware Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXOptimizer, ORTOOLS_CAPABILITIES

   optimizer = LXOptimizer().use_solver("ortools")

   # Enable linearization if solver needs it
   if ORTOOLS_CAPABILITIES.needs_linearization_for_bilinear():
       optimizer.enable_linearization(
           big_m=1e6,
           pwl_segments=20
       )

   solution = optimizer.solve(model)

Feature-Based Solver Selection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import (
       GUROBI_CAPABILITIES,
       CPLEX_CAPABILITIES,
       ORTOOLS_CAPABILITIES,
       LXSolverFeature
   )

   def select_solver_for_features(required_features):
       """Select best solver that supports all required features."""
       solvers = [
           ("gurobi", GUROBI_CAPABILITIES),
           ("cplex", CPLEX_CAPABILITIES),
           ("ortools", ORTOOLS_CAPABILITIES),
       ]

       for solver_name, capability in solvers:
           if all(capability.has_feature(f) for f in required_features):
               return solver_name

       raise ValueError("No solver supports all required features")

   # Example: Need quadratic and SOS2
   required = [LXSolverFeature.QUADRATIC_CONVEX, LXSolverFeature.SOS2]
   solver = select_solver_for_features(required)
   print(f"Use {solver}")  # "gurobi" or "cplex"

Capability Matrix
-----------------

Complete Feature Support Matrix:

.. list-table::
   :header-rows: 1
   :widths: 30 14 14 14 14 14

   * - Feature
     - OR-Tools
     - Gurobi
     - CPLEX
     - GLPK
     - CP-SAT
   * - **Problem Types**
     -
     -
     -
     -
     -
   * - Linear (LP)
     - ✓
     - ✓
     - ✓
     - ✓
     - ✗
   * - Integer (MIP)
     - ✓
     - ✓
     - ✓
     - ✓
     - ✓
   * - Quadratic (QP)
     - ✗
     - ✓
     - ✓
     - ✗
     - ✗
   * - SOCP
     - ✗
     - ✓
     - ✓
     - ✗
     - ✗
   * - **Special Constraints**
     -
     -
     -
     -
     -
   * - SOS1
     - ✓
     - ✓
     - ✓
     - ✗
     - ✗
   * - SOS2
     - ✓
     - ✓
     - ✓
     - ✗
     - ✗
   * - Indicator
     - ✓
     - ✓
     - ✓
     - ✗
     - ✗
   * - PWL Functions
     - ✗
     - ✓
     - ✓
     - ✗
     - ✗
   * - **Advanced Features**
     -
     -
     -
     -
     -
   * - Warm Start
     - ✓
     - ✓
     - ✓
     - ✗
     - ✓
   * - Parallel
     - ✓
     - ✓
     - ✓
     - ✗
     - ✓
   * - Callbacks
     - ✗
     - ✓
     - ✓
     - ✗
     - ✗
   * - Sensitivity
     - ✗
     - ✓
     - ✓
     - ✓
     - ✗
   * - IIS/Conflict
     - ✗
     - ✓
     - ✓
     - ✗
     - ✗

Custom Capabilities
-------------------

If you implement a custom solver, define its capabilities:

.. code-block:: python

   from lumix import LXSolverCapability, LXSolverFeature

   MY_SOLVER_CAPABILITIES = LXSolverCapability(
       name="MySolver",
       features=(
           LXSolverFeature.LINEAR
           | LXSolverFeature.INTEGER
           | LXSolverFeature.QUADRATIC_CONVEX
       ),
       max_variables=10_000_000,
       max_constraints=10_000_000,
       supports_warmstart=True,
       supports_parallel=True,
       supports_callbacks=False,
   )

   # Use in custom solver implementation
   class MyCustomSolver(LXSolverInterface):
       def __init__(self):
           super().__init__(MY_SOLVER_CAPABILITIES)

Next Steps
----------

- :doc:`choosing-solver` - How to choose based on capabilities
- :doc:`using-optimizer` - Using the optimizer with capability awareness
- :doc:`advanced-features` - Advanced solver features
- :doc:`/development/extending-solvers` - Implementing custom solvers
- :doc:`/api/solvers/index` - API reference
