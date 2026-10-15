Configuration
=============

Detailed guide for configuring the linearization engine.

Overview
--------

The :class:`~lumix.linearization.config.LXLinearizerConfig` class sets the constants
and defaults the linearization techniques use: the Big-M bound for unbounded
variables, the piecewise-linear settings, and the size limit of exact integer
products.

.. versionchanged:: 0.3.0
   The configuration is applied: ``LXLinearizer(model, capability, config)`` and
   ``LXOptimizer().enable_linearization(...)`` pass it to every technique. Before
   0.3.0 the piecewise settings were overridden by the terms' own defaults. Six
   fields that no technique reads are deprecated (see `Deprecated Fields`_).

Basic Configuration
-------------------

Creating a Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.linearization import LXLinearizerConfig

   # Default configuration
   config = LXLinearizerConfig()

   # Custom configuration
   config = LXLinearizerConfig(
       big_m_value=1e5,
       pwl_num_segments=30,
       adaptive_breakpoints=True
   )

The same settings can be given to the optimizer:

.. code-block:: python

   optimizer = LXOptimizer().use_solver("glpk").enable_linearization(
       big_m=1e5,                  # big_m_value
       pwl_segments=30,            # pwl_num_segments
       pwl_method="sos2",          # pwl_method
       adaptive_breakpoints=True,  # adaptive_breakpoints
       binary_expansion_bits=12,   # other fields by name
   )

Configuration Parameters
------------------------

Big-M Settings
~~~~~~~~~~~~~~

.. py:attribute:: big_m_value
   :type: float
   :value: 1e6

   Bound used where a variable or expression has no finite bound:

   - the product of a binary and an unbounded variable (see :doc:`bilinear`);
   - an indicator whose expression is unbounded (see
     :doc:`/user-guide/nonlinear/indicator`).

   Both cases issue a ``UserWarning``. Everywhere else the constants are computed
   from the variable bounds, so finite bounds make ``big_m_value`` unnecessary.
   Absolute values, min and max never use it: their exact form requires finite
   bounds (see :doc:`engine`).

   **Critical Setting:** Setting M too small cuts off solutions in which the
   unbounded variable exceeds it. Setting M too large can cause numerical issues
   and slow solving.

   **Example:**

   .. code-block:: python

      # Unbounded variables that never exceed 1000 in absolute value
      config = LXLinearizerConfig(big_m_value=1e3)

Piecewise-Linear Settings
~~~~~~~~~~~~~~~~~~~~~~~~~~

These three settings apply to every piecewise-linear term that leaves the
corresponding argument as ``None`` (the default of ``add_piecewise``,
``LXPiecewiseLinearTerm`` and ``approximate_function``); a value given on the term
wins. See :doc:`piecewise`.

.. py:attribute:: pwl_num_segments
   :type: int
   :value: 20

   Number of linear segments for piecewise-linear approximations (the term's
   ``num_segments``).

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

   Method for the piecewise-linear formulation (the term's ``method``). All three
   are exact for the piecewise-linear function through the breakpoints and work on
   every MILP solver; LumiX does not pass SOS2 sets to the solver.

   **Methods:**

   1. **SOS2**: convex-combination weights, adjacency enforced with one binary per
      segment
   2. **Incremental**: one binary and one fraction variable per segment
   3. **Logarithmic** (Gray code): ⌈log₂(n)⌉ binaries, the fewest for many segments

   **Example:**

   .. code-block:: python

      config = LXLinearizerConfig(pwl_method="sos2")
      config = LXLinearizerConfig(pwl_method="logarithmic")

.. py:attribute:: adaptive_breakpoints
   :type: bool
   :value: True

   Use adaptive breakpoint generation based on function curvature (the term's
   ``adaptive``).

   **How It Works:**

   - Samples the function at 10 × ``num_segments`` + 1 points
   - Mixes the curvature (absolute second differences) with a uniform density
   - Places the breakpoints at equally spaced quantiles of that density

   The breakpoints are deterministic, and there are exactly ``num_segments + 1`` of
   them.

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

Binary Expansion Settings
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:attribute:: binary_expansion_bits
   :type: int
   :value: 10

   Largest number of binary digits of the integer factor in an exact product
   (integer × integer or integer × continuous, see :doc:`bilinear`).

   An integer variable with bounds [L, U] needs ``(U - L).bit_length()`` digits.
   When that exceeds ``binary_expansion_bits`` the linearizer raises
   ``ValueError``; raise the setting, or use Gurobi or CPLEX for a quadratic
   objective.

   **Capacity:**

   - ``bits=10`` → up to 2¹⁰ = 1024 integer values
   - ``bits=15`` → up to 2¹⁵ = 32,768 integer values
   - ``bits=20`` → up to 2²⁰ = 1,048,576 integer values

   **Variables Created:**

   - For each product: one binary per digit of the expanded factor, plus one
     binary × variable product (one continuous variable, four constraints) per digit

   **Example:**

   .. code-block:: python

      # For integers in [0, 1000]
      config = LXLinearizerConfig(binary_expansion_bits=10)

      # For integers in [0, 100000]
      config = LXLinearizerConfig(binary_expansion_bits=17)

Deprecated Fields
~~~~~~~~~~~~~~~~~

.. deprecated:: 0.3.0
   The following fields have no effect. Setting one of them to a value other than
   its default issues a ``DeprecationWarning``. They will be removed in 0.4.0.

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - Field
     - Default
     - Note
   * - ``default_method``
     - ``LXLinearizationMethod.MCCORMICK``
     - The technique follows from the variable types (see :doc:`bilinear`).
   * - ``tolerance``
     - ``1e-6``
     - Not read by any technique.
   * - ``verbose_logging``
     - ``True``
     - Nothing is logged; approximations are reported as ``UserWarning``.
   * - ``prefer_sos2``
     - ``True``
     - Use ``pwl_method``.
   * - ``auto_detect_bounds``
     - ``True``
     - The variable bounds are always used.
   * - ``mccormick_tighten_bounds``
     - ``True``
     - Bounds are not tightened.

The ``prefer_sos2`` and ``mccormick_tighten_bounds`` arguments of
``LXOptimizer.enable_linearization()`` have no effect either.

Configuration Examples
----------------------

Production Environment
~~~~~~~~~~~~~~~~~~~~~~

Optimized for solve time and numerical stability:

.. code-block:: python

   production_config = LXLinearizerConfig(
       pwl_method="sos2",

       # Tight M values (problem-specific)
       big_m_value=1e4,  # Based on domain knowledge

       # Balanced accuracy
       pwl_num_segments=25,
       adaptive_breakpoints=True,
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

       # Larger exact integer products
       binary_expansion_bits=14,
   )

Memory-Constrained
~~~~~~~~~~~~~~~~~~

Minimize auxiliary variables and constraints:

.. code-block:: python

   memory_config = LXLinearizerConfig(
       # Fewer segments
       pwl_num_segments=10,
       adaptive_breakpoints=True,  # Get more from fewer segments

       # Fewest binaries per piecewise term
       pwl_method="logarithmic",
   )

Validation and Debugging
-------------------------

Checking Configuration
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   config = LXLinearizerConfig(pwl_num_segments=30)

   # Validate settings
   assert config.pwl_num_segments > 0, "Need at least one segment"
   assert config.big_m_value > 0, "Big-M must be positive"

Warnings
~~~~~~~~

The linearizer does not log. It issues a ``UserWarning`` when it

- uses McCormick envelopes (a relaxation) for a product of two continuous
  variables;
- uses ``big_m_value`` for an unbounded variable or expression;
- restricts a piecewise term's variable to a domain narrower than its bounds.

See :doc:`engine` for turning them into errors.

See Also
--------

- :doc:`engine` - Using the linearization engine
- :doc:`bilinear` - Bilinear linearization techniques
- :doc:`piecewise` - Piecewise-linear approximation
- :doc:`/api/linearization/index` - API reference
