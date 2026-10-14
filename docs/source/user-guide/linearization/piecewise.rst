Piecewise-Linear Approximation
===============================

Guide for approximating nonlinear functions using piecewise-linear segments.

Overview
--------

Many optimization problems involve nonlinear functions that can be approximated
using piecewise-linear (PWL) segments:

- **Exponential growth**: e^x
- **Logarithmic utility**: log(x)
- **Power functions**: x^n
- **Trigonometric**: sin(x), cos(x)
- **Custom curves**: Any arbitrary function

The :class:`~lumix.linearization.techniques.piecewise.LXPiecewiseLinearizer` class
provides multiple formulation methods for PWL approximation.

Basic Concept
-------------

Approximating f(x) with Linear Segments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   f(x)
    |     *
    |    * *
    |   *   *        Original function: f(x) = x²
    |  *     *
    | *       *      Approximation: piecewise-linear
    |*_________*___
    0   x₁  x₂  x₃   Breakpoints

**Key Idea:**

1. Choose breakpoints: x₀, x₁, x₂, ..., xₙ
2. Evaluate function: f(x₀), f(x₁), ..., f(xₙ)
3. Create linear segments connecting the points
4. Model ensures x falls on one of the segments

Formulation Methods
-------------------

LumiX supports three PWL formulation methods. All three are exact for the
piecewise-linear function through the breakpoints, also when it is nonconvex
(n = number of segments):

.. list-table::
   :header-rows: 1
   :widths: 20 25 25 30

   * - Method
     - Variables
     - Constraints
     - Best For
   * - SOS2
     - n+1 continuous + n binary
     - n+5
     - Default; general use
   * - Incremental
     - n binary + n continuous
     - 3n+1
     - Standard MILP solvers
   * - Logarithmic
     - n'+1 continuous + log₂(n') binary (n' = n rounded up to a power of two)
     - 2·log₂(n')+3
     - Many segments

.. versionchanged:: 0.2.1
   SOS2 enforces adjacency with segment binaries and is exact. Earlier versions
   added no SOS2 condition at all, so the model was only the convex hull of the
   function: maximizing a convex function could return a value above it. The
   logarithmic method is implemented (it raised ``NotImplementedError``).

SOS2 Formulation
----------------

Special Ordered Set Type 2 Formulation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Variables:**

- λ₀, λ₁, ..., λₙ: Convex combination weights
- y: Output variable

**Constraints:**

.. math::

   \sum_{i=0}^{n} \lambda_i = 1 \\
   x = \sum_{i=0}^{n} \lambda_i \cdot x_i \\
   y = \sum_{i=0}^{n} \lambda_i \cdot f(x_i) \\
   \text{SOS2}(\lambda_0, \lambda_1, ..., \lambda_n)

**SOS2 Property:**

At most 2 adjacent λ variables can be non-zero.

**Example:**

.. code-block:: python

   from lumix.linearization.techniques import LXPiecewiseLinearizer
   from lumix.linearization.config import LXLinearizerConfig
   import math

   # Configure for SOS2
   config = LXLinearizerConfig(
       pwl_method="sos2",
       pwl_num_segments=30,
       prefer_sos2=True
   )

   linearizer = LXPiecewiseLinearizer(config)

   # Approximate exp(x) for x ∈ [0, 5]
   exp_output = linearizer.approximate_function(
       func=lambda x: math.exp(x),
       var=input_var,
       num_segments=30,
       x_min=0,
       x_max=5,
       method="sos2"
   )

**Adjacency:**

No solver adapter passes SOS2 sets to the solver yet, so LumiX enforces the SOS2
property with one binary z per segment: Σz = 1, λ₀ ≤ z₀, λᵢ ≤ zᵢ₋₁ + zᵢ,
λₙ ≤ zₙ₋₁. The formulation works on every MILP solver.

Incremental Formulation
-----------------------

Binary Selection Variable Formulation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Variables:**

- s₀, s₁, ..., sₙ₋₁: Binary segment selection variables
- δ₀, δ₁, ..., δₙ₋₁: Continuous delta variables (how far into segment)
- y: Output variable

**Constraints:**

.. math::

   \sum_{i=0}^{n-1} s_i = 1 \quad \text{(exactly one segment active)} \\
   \delta_i \leq s_i \quad \text{(delta only if segment active)} \\
   x = \sum_{i=0}^{n-1} (x_i \cdot s_i + \delta_i \cdot (x_{i+1} - x_i)) \\
   y = \sum_{i=0}^{n-1} (f(x_i) \cdot s_i + \delta_i \cdot (f(x_{i+1}) - f(x_i)))

**Example:**

.. code-block:: python

   config = LXLinearizerConfig(
       pwl_method="incremental",
       pwl_num_segments=20  # Fewer segments (more variables)
   )

   linearizer = LXPiecewiseLinearizer(config)

   # Approximate sqrt(x) for x ∈ [0, 100]
   sqrt_output = linearizer.approximate_function(
       func=lambda x: math.sqrt(x) if x >= 0 else 0,
       var=input_var,
       num_segments=20,
       x_min=0,
       x_max=100,
       method="incremental"
   )

**Advantages:**

- Works with any MILP solver
- No special solver features required
- Explicit segment selection (interpretable)

**Disadvantages:**

- Many variables (2n binary/continuous + 1 output)
- Many constraints (3n+1)
- Slower than SOS2 when available

Logarithmic Formulation
-----------------------

Gray Code Encoding Formulation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Idea:**

Use log₂(n) binary variables to encode which segment is active.

**Variables:**

- λ₀, ..., λₙ': Convex-combination weights (as in SOS2)
- y₀, ..., y_{log₂(n')-1}: Binary Gray-code variables
- Output variable

Segment s gets the Gray code g(s) = s XOR (s >> 1). For every bit l, the λ of
breakpoints whose adjacent segments all have bit l set sum to at most yₗ, and those
whose adjacent segments all have it clear sum to at most 1 − yₗ (Vielma and
Nemhauser, 2011). The segment count is padded to a power of two with zero-width
segments at the last breakpoint.

**When to Use:**

- Many segments (the binary count grows with log₂ of the segment count)

Breakpoint Generation
---------------------

Explicit Breakpoints
~~~~~~~~~~~~~~~~~~~~

.. versionadded:: 0.2.1

Pass ``breakpoints`` to use your own x-coordinates instead of generated ones. For a
function defined by data points this makes the term exact:

.. code-block:: python

   points = [(0, 10), (5, 2), (20, 30)]
   f = lambda x: np.interp(x, [p[0] for p in points], [p[1] for p in points])
   expr.add_piecewise(x, f, breakpoints=[0, 5, 20])

``breakpoints`` must contain at least two strictly increasing values and replaces
``num_segments``, ``adaptive``, ``x_min`` and ``x_max`` (combining it with
``x_min``/``x_max`` raises ``ValueError``).

The Domain Constrains the Variable
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The input variable is written as a combination of the breakpoints, so it cannot
leave ``[x_min, x_max]`` (or ``[breakpoints[0], breakpoints[-1]]``). When that range
is narrower than the variable's bounds, LumiX issues a ``UserWarning``. Cover the
variable's whole range unless you mean to restrict it.


Uniform Breakpoints
~~~~~~~~~~~~~~~~~~~

Evenly spaced breakpoints across domain:

.. code-block:: python

   config = LXLinearizerConfig(
       pwl_num_segments=20,
       adaptive_breakpoints=False  # Uniform spacing
   )

   linearizer = LXPiecewiseLinearizer(config)

   # x ∈ [0, 10] with 20 segments
   # Breakpoints: 0, 0.5, 1.0, 1.5, ..., 10.0

**Best For:**

- Smooth functions (sqrt, linear pieces)
- Functions with constant curvature
- Quick approximations

Adaptive Breakpoints
~~~~~~~~~~~~~~~~~~~~

Breakpoints concentrated where function curves sharply:

.. code-block:: python

   config = LXLinearizerConfig(
       pwl_num_segments=30,
       adaptive_breakpoints=True  # Curvature-based spacing
   )

   linearizer = LXPiecewiseLinearizer(config)

**How It Works:**

1. Sample function at many points (10× num_segments)
2. Compute second derivative (curvature measure)
3. Place more breakpoints where curvature is high

**Example:**

.. code-block:: python

   # Exponential: e^x curves sharply for large x
   # Adaptive places more points at high x

   exp_output = linearizer.approximate_function(
       func=lambda x: math.exp(x),
       var=x,
       num_segments=30,
       x_min=0,
       x_max=5,
       adaptive=True  # More points where curvature is high
   )

**Best For:**

- Curved functions (exp, log, sigmoid)
- Functions with varying curvature
- High-accuracy requirements

Accuracy Considerations
-----------------------

Choosing Number of Segments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Trade-off:**

- More segments → better accuracy
- More segments → more variables and constraints

**Guidelines:**

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Function Type
     - Segments
     - Reason
   * - Smooth (sqrt)
     - 10-20
     - Low curvature, uniform is fine
   * - Curved (exp, log)
     - 30-50
     - High curvature, need more points
   * - Very curved (sigmoid)
     - 40-60
     - Sharp transition, many points needed
   * - Trigonometric (sin, cos)
     - 30-50
     - Periodic, cover full cycle
   * - Custom functions
     - 20-40
     - Depends on curvature

**Validation:**

.. code-block:: python

   import numpy as np

   # Test approximation accuracy
   x_test = np.linspace(0, 10, 100)
   errors = []

   for x_val in x_test:
       true_value = math.exp(x_val)
       approx_value = evaluate_pwl(x_val)  # From linearized model
       error = abs(true_value - approx_value) / true_value
       errors.append(error)

   max_error = max(errors)
   print(f"Maximum relative error: {max_error:.2%}")

Domain Selection
~~~~~~~~~~~~~~~~

**Choose appropriate [x_min, x_max]:**

.. code-block:: python

   # Option 1: Use variable bounds
   x = LXVariable[Model, float]("x").bounds(lower=0, upper=100)
   output = linearizer.approximate_function(
       func=lambda x: x**2,
       var=x,
       # x_min, x_max auto-detected from variable bounds
   )

   # Option 2: Specify domain explicitly
   output = linearizer.approximate_function(
       func=lambda x: math.log(x),
       var=x,
       x_min=1,  # log(x) undefined for x ≤ 0
       x_max=1000
   )

Complete Examples
-----------------

Example 1: Exponential Growth Model
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXModel, LXVariable
   from lumix.linearization.techniques import LXPiecewiseLinearizer
   from lumix.linearization.config import LXLinearizerConfig
   import math

   # Time variable
   time = (
       LXVariable[Period, float]("time")
       .continuous()
       .bounds(lower=0, upper=10)
       .indexed_by(lambda p: p.id)
       .from_data(periods)
   )

   # Configure linearizer
   config = LXLinearizerConfig(
       pwl_method="sos2",
       pwl_num_segments=40,  # Exponential needs more segments
       adaptive_breakpoints=True  # Concentrate at high curvature
   )

   linearizer = LXPiecewiseLinearizer(config)

   # Approximate e^(0.5*t)
   growth_output = linearizer.approximate_function(
       func=lambda t: math.exp(0.5 * t),
       var=time,
       num_segments=40,
       x_min=0,
       x_max=10,
       method="sos2",
       adaptive=True
   )

   # Add to model
   model = LXModel("growth")
   for var in linearizer.auxiliary_vars:
       model.add_variable(var)
   for constraint in linearizer.auxiliary_constraints:
       model.add_constraint(constraint)

   # Use growth_output in objective or constraints
   model.maximize(growth_output)

Example 2: Logarithmic Utility
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Consumption variable
   consumption = (
       LXVariable[Agent, float]("consumption")
       .continuous()
       .bounds(lower=1, upper=1000)  # log undefined at 0
       .indexed_by(lambda a: a.id)
       .from_data(agents)
   )

   # Logarithmic utility function
   config = LXLinearizerConfig(
       pwl_method="sos2",
       pwl_num_segments=35,
       adaptive_breakpoints=True  # log curves near 0
   )

   linearizer = LXPiecewiseLinearizer(config)

   utility_output = linearizer.approximate_function(
       func=lambda c: math.log(c) if c > 0 else -1e10,
       var=consumption,
       num_segments=35,
       x_min=1,  # Avoid log(0)
       x_max=1000,
       method="sos2",
       adaptive=True
   )

   # Maximize total utility
   model.maximize(utility_output)

Example 3: Custom Piecewise Cost Function
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Custom cost function with quantity discounts
   def cost_function(quantity):
       if quantity < 100:
           return 10 * quantity  # $10 per unit
       elif quantity < 500:
           return 900 + 8 * (quantity - 100)  # $8 per unit
       else:
           return 4100 + 5 * (quantity - 500)  # $5 per unit

   # Production quantity
   quantity = (
       LXVariable[Product, float]("quantity")
       .continuous()
       .bounds(lower=0, upper=1000)
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

   config = LXLinearizerConfig(
       pwl_method="incremental",  # Good for piecewise functions
       pwl_num_segments=50,
       adaptive_breakpoints=False  # Uniform for piecewise
   )

   linearizer = LXPiecewiseLinearizer(config)

   cost_output = linearizer.approximate_function(
       func=cost_function,
       var=quantity,
       num_segments=50,
       x_min=0,
       x_max=1000,
       method="incremental"
   )

   # Minimize total cost
   model.minimize(cost_output)

Performance Tips
----------------

1. **Choose Method Based on Solver**

   .. code-block:: python

      # For Gurobi/CPLEX
      config = LXLinearizerConfig(pwl_method="sos2", prefer_sos2=True)

      # For GLPK
      config = LXLinearizerConfig(pwl_method="incremental")

2. **Use Adaptive for Curved Functions**

   .. code-block:: python

      # Exponential, logarithmic, sigmoid: adaptive=True
      config = LXLinearizerConfig(adaptive_breakpoints=True)

      # Smooth functions: adaptive=False
      config = LXLinearizerConfig(adaptive_breakpoints=False)

3. **Balance Segments and Accuracy**

   .. code-block:: python

      # Start with fewer segments
      config = LXLinearizerConfig(pwl_num_segments=20)

      # Test accuracy, increase if needed
      config = LXLinearizerConfig(pwl_num_segments=40)

4. **Use Tight Domain Bounds**

   .. code-block:: python

      # Good: Tight domain
      output = linearizer.approximate_function(
          func=lambda x: math.exp(x),
          var=x,
          x_min=0,
          x_max=5  # Only where needed
      )

      # Bad: Wide unnecessary domain
      output = linearizer.approximate_function(
          func=lambda x: math.exp(x),
          var=x,
          x_min=0,
          x_max=100  # Way too wide!
      )

See Also
--------

- :doc:`nonlinear-functions` - Pre-built function approximations
- :doc:`config` - Configuration options
- :doc:`/api/linearization/index` - API reference
