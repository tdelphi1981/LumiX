Configuration
=============

Detailed guide for configuring the linearization engine.

Overview
--------

The :class:`~lumix.linearization.config.LXLinearizerConfig` class controls all aspects
of the linearization process, from method selection to accuracy requirements.

Basic Configuration
-------------------

Creating a Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.linearization import LXLinearizerConfig, LXLinearizationMethod

   # Default configuration
   config = LXLinearizerConfig()

   # Custom configuration
   config = LXLinearizerConfig(
       default_method=LXLinearizationMethod.MCCORMICK,
       big_m_value=1e5,
       pwl_num_segments=30,
       adaptive_breakpoints=True,
       verbose_logging=True
   )

Configuration Parameters
------------------------

General Settings
~~~~~~~~~~~~~~~~

.. py:attribute:: default_method
   :type: LXLinearizationMethod
   :value: LXLinearizationMethod.MCCORMICK

   Default linearization technique to use for bilinear products.

   **Available Methods:**

   - ``MCCORMICK``: McCormick envelopes (default, best for continuous variables)
   - ``BIG_M``: Big-M method (for binary × continuous)
   - ``BINARY_EXPANSION``: Binary expansion for integer products
   - ``SOS2``: Special Ordered Set type 2 for piecewise functions
   - ``LOGARITHMIC``: Logarithmic encoding for large integer products

   **Example:**

   .. code-block:: python

      # Use McCormick by default
      config = LXLinearizerConfig(
          default_method=LXLinearizationMethod.MCCORMICK
      )

.. py:attribute:: tolerance
   :type: float
   :value: 1e-6

   Numerical tolerance for comparisons and bound checking.

   **When Used:**

   - Checking if bounds are equal
   - Validating linearization accuracy
   - Comparing breakpoint values

   **Example:**

   .. code-block:: python

      config = LXLinearizerConfig(tolerance=1e-8)

.. py:attribute:: verbose_logging
   :type: bool
   :value: True

   Enable detailed linearization logging for debugging and analysis.

   **What Gets Logged:**

   - Detected nonlinear terms
   - Selected linearization techniques
   - Created auxiliary variables and constraints
   - Linearization statistics

   **Example:**

   .. code-block:: python

      # Enable verbose logging
      config = LXLinearizerConfig(verbose_logging=True)

Big-M Settings
~~~~~~~~~~~~~~

.. py:attribute:: big_m_value
   :type: float
   :value: 1e6

   Big-M constant for conditional constraints and Big-M linearization.

   **Critical Setting:** Setting M too small can lead to incorrect solutions.
   Setting M too large can cause numerical issues and slow solving.

   **Choosing M:**

   1. **Problem-Specific:** Use knowledge of variable bounds
   2. **Conservative:** Use 100× the maximum expected value
   3. **Validation:** Verify solutions don't hit M bounds

   **Example:**

   .. code-block:: python

      # For variables bounded in [0, 1000]
      config = LXLinearizerConfig(big_m_value=1e5)

      # For normalized variables in [0, 1]
      config = LXLinearizerConfig(big_m_value=100)

Piecewise-Linear Settings
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:attribute:: pwl_num_segments
   :type: int
   :value: 20

   Number of linear segments for piecewise-linear approximations.

   **Accuracy vs. Complexity:**

   - More segments → better accuracy
   - More segments → more variables and constraints
   - Typical range: 10-50 segments

   **Guidelines:**

   .. list-table::
      :header-rows: 1
      :widths: 30 20 50

      * - Function Type
        - Segments
        - Reason
      * - Smooth (sqrt, sin, cos)
        - 10-20
        - Uniform approximation sufficient
      * - Curved (exp, log, sigmoid)
        - 30-50
        - Sharp curvature needs more points
      * - Custom functions
        - 20-40
        - Depends on curvature

   **Example:**

   .. code-block:: python

      # High accuracy for exponential
      config = LXLinearizerConfig(pwl_num_segments=50)

.. py:attribute:: pwl_method
   :type: Literal["sos2", "incremental", "logarithmic"]
   :value: "sos2"

   Method for piecewise-linear formulation.

   **Methods:**

   1. **SOS2** (Special Ordered Set type 2):
      - Best when solver supports SOS2
      - Fewest variables (n+1 continuous)
      - Recommended for Gurobi, CPLEX

   2. **Incremental**:
      - Uses binary selection variables
      - More variables but standard MILP
      - Recommended for solvers without SOS2

   3. **Logarithmic** (Gray code):
      - Uses log₂(n) binary variables
      - Best for many segments (>100)
      - Not yet implemented in LumiX

   **Example:**

   .. code-block:: python

      # Use SOS2 if solver supports it
      config = LXLinearizerConfig(
          pwl_method="sos2",
          prefer_sos2=True
      )

      # Use incremental for GLPK
      config = LXLinearizerConfig(pwl_method="incremental")

.. py:attribute:: prefer_sos2
   :type: bool
   :value: True

   Use SOS2 formulation when solver supports it, regardless of ``pwl_method``.

   **Auto-Detection:**

   The linearizer checks solver capabilities and automatically uses SOS2 if:
   - ``prefer_sos2=True``
   - Solver supports SOS2 (Gurobi, CPLEX, some OR-Tools modes)

   **Example:**

   .. code-block:: python

      config = LXLinearizerConfig(
          prefer_sos2=True  # Use SOS2 if available
      )

.. py:attribute:: adaptive_breakpoints
   :type: bool
   :value: True

   Use adaptive breakpoint generation based on function curvature.

   **How It Works:**

   - Samples function at many points
   - Computes second derivative (curvature measure)
   - Concentrates breakpoints where curvature is high

   **Benefits:**

   - Better accuracy with same number of segments
   - Automatically adapts to function shape
   - Especially useful for functions with varying curvature

   **When to Use:**

   - Curved functions (exp, log, sigmoid): ``adaptive=True``
   - Smooth functions (sqrt, linear pieces): ``adaptive=False`` (uniform is fine)

   **Example:**

   .. code-block:: python

      # Adaptive for exponential function
      config = LXLinearizerConfig(
          pwl_num_segments=30,
          adaptive_breakpoints=True
      )

McCormick Envelope Settings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:attribute:: auto_detect_bounds
   :type: bool
   :value: True

   Automatically detect variable bounds for McCormick envelopes.

   **How It Works:**

   - Checks variable lower_bound and upper_bound attributes
   - Falls back to default bounds if not specified
   - Raises error if bounds cannot be determined

   **Example:**

   .. code-block:: python

      config = LXLinearizerConfig(auto_detect_bounds=True)

      # Variables must have bounds
      x = LXVariable[Product, float]("x").bounds(lower=0, upper=100)
      y = LXVariable[Product, float]("y").bounds(lower=-50, upper=50)

.. py:attribute:: mccormick_tighten_bounds
   :type: bool
   :value: True

   Apply bound tightening preprocessing for McCormick envelopes.

   **What It Does:**

   - Tightens bounds using constraint propagation
   - Results in stronger linear relaxation
   - Improves solver performance

   **Trade-off:**

   - Small preprocessing overhead
   - Significant solving time improvement

   **Example:**

   .. code-block:: python

      # Enable bound tightening (recommended)
      config = LXLinearizerConfig(
          mccormick_tighten_bounds=True
      )

Binary Expansion Settings
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:attribute:: binary_expansion_bits
   :type: int
   :value: 10

   Number of bits for binary expansion method.

   **Purpose:**

   Linearize integer × integer products by representing integers in binary.

   **Capacity:**

   - ``bits=10`` → integers up to 2¹⁰ = 1024
   - ``bits=15`` → integers up to 2¹⁵ = 32,768
   - ``bits=20`` → integers up to 2²⁰ = 1,048,576

   **Variables Created:**

   - For product of two integers: ``2 × bits`` binary variables

   **Example:**

   .. code-block:: python

      # For integers up to 1000
      config = LXLinearizerConfig(binary_expansion_bits=10)

      # For larger integers up to 100,000
      config = LXLinearizerConfig(binary_expansion_bits=17)

Configuration Examples
----------------------

Production Environment
~~~~~~~~~~~~~~~~~~~~~~

Optimized for solve time and numerical stability:

.. code-block:: python

   production_config = LXLinearizerConfig(
       # Use proven methods
       default_method=LXLinearizationMethod.MCCORMICK,
       pwl_method="sos2",

       # Tight M values (problem-specific)
       big_m_value=1e4,  # Based on domain knowledge

       # Balanced accuracy
       pwl_num_segments=25,
       adaptive_breakpoints=True,

       # Enable optimizations
       mccormick_tighten_bounds=True,
       prefer_sos2=True,

       # Moderate logging
       verbose_logging=False,

       # Standard tolerance
       tolerance=1e-6
   )

Research / Prototyping
~~~~~~~~~~~~~~~~~~~~~~

High accuracy for validation and experimentation:

.. code-block:: python

   research_config = LXLinearizerConfig(
       # High accuracy
       pwl_num_segments=50,
       adaptive_breakpoints=True,

       # Conservative Big-M
       big_m_value=1e6,

       # Detailed logging
       verbose_logging=True,

       # Tight tolerance
       tolerance=1e-8,

       # Best formulations
       prefer_sos2=True,
       mccormick_tighten_bounds=True
   )

Memory-Constrained
~~~~~~~~~~~~~~~~~~

Minimize auxiliary variables and constraints:

.. code-block:: python

   memory_config = LXLinearizerConfig(
       # Fewer segments
       pwl_num_segments=10,
       adaptive_breakpoints=True,  # Get more from fewer segments

       # Prefer techniques with fewer variables
       pwl_method="sos2",  # Fewer vars than incremental
       prefer_sos2=True,

       # Minimal logging
       verbose_logging=False
   )

Solver-Specific Configurations
-------------------------------

Gurobi / CPLEX
~~~~~~~~~~~~~~

Leverage advanced solver features:

.. code-block:: python

   advanced_solver_config = LXLinearizerConfig(
       # Use SOS2 (natively supported)
       pwl_method="sos2",
       prefer_sos2=True,

       # Can use smaller Big-M (better presolve)
       big_m_value=1e4,

       # Enable all optimizations
       mccormick_tighten_bounds=True,
       auto_detect_bounds=True
   )

GLPK / Basic Solvers
~~~~~~~~~~~~~~~~~~~~

No SOS2 support, use standard MILP:

.. code-block:: python

   basic_solver_config = LXLinearizerConfig(
       # Use incremental (no SOS2 in GLPK)
       pwl_method="incremental",
       prefer_sos2=False,

       # Fewer segments (slower with incremental)
       pwl_num_segments=15,

       # Standard settings
       big_m_value=1e5,
       adaptive_breakpoints=True
   )

Validation and Debugging
-------------------------

Checking Configuration
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   config = LXLinearizerConfig(
       pwl_num_segments=30,
       verbose_logging=True
   )

   # Validate settings
   assert config.pwl_num_segments > 0, "Need at least one segment"
   assert config.tolerance > 0, "Tolerance must be positive"
   assert config.big_m_value > 0, "Big-M must be positive"

Logging Output
~~~~~~~~~~~~~~

With ``verbose_logging=True``, you'll see:

.. code-block:: text

   [Linearization] Scanning model for nonlinear terms...
   [Linearization] Found 3 bilinear terms
   [Linearization] Found 2 piecewise-linear terms
   [Linearization] Linearizing bilinear term: price[p1] * quantity[p1]
   [Linearization] Using McCormick envelopes (continuous × continuous)
   [Linearization] Created auxiliary variable: aux_mccormick_price_quantity_1
   [Linearization] Created 4 McCormick constraints
   [Linearization] Summary:
   [Linearization]   - Bilinear terms: 3
   [Linearization]   - Piecewise terms: 2
   [Linearization]   - Auxiliary variables: 8
   [Linearization]   - Auxiliary constraints: 17

See Also
--------

- :doc:`engine` - Using the linearization engine
- :doc:`bilinear` - Bilinear linearization techniques
- :doc:`piecewise` - Piecewise-linear approximation
- :doc:`/api/linearization/index` - API reference
