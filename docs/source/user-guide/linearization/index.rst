Linearization Concepts
======================

This guide covers automatic linearization of nonlinear optimization terms in LumiX.

Introduction
------------

The linearization module transforms nonlinear expressions into linear or mixed-integer
linear equivalents, enabling you to:

- **Solve nonlinear models** with linear programming (LP) or mixed-integer programming (MIP) solvers
- **Handle solver limitations** by converting unsupported nonlinear terms
- **Improve solve times** by using specialized linear formulations
- **Maintain model accuracy** through configurable approximation methods

Philosophy
----------

Traditional Approach (Manual Linearization)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Manual linearization is error-prone and requires deep mathematical knowledge:

.. code-block:: python

   # Manual McCormick envelope for x * y
   # Requires: x ∈ [xL, xU], y ∈ [yL, yU]

   z = model.addVar(name="z")  # Auxiliary variable for x * y

   # Four McCormick constraints
   model.addConstr(z >= xL*y + yL*x - xL*yL)
   model.addConstr(z >= xU*y + yU*x - xU*yU)
   model.addConstr(z <= xL*y + yU*x - xL*yU)
   model.addConstr(z <= xU*y + yL*x - xU*yL)

   # Use z in objective instead of x * y
   model.setObjective(profit * z, GRB.MAXIMIZE)

**Problems:**

- ✗ Manual constraint creation
- ✗ Easy to make mistakes in formulation
- ✗ Hard to maintain and modify
- ✗ Different formulations for different variable types

LumiX Approach (Automatic)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

LumiX handles linearization automatically:

.. code-block:: python

   from lumix import LXModel, LXNonLinearExpression
   from lumix.linearization import LXLinearizer, LXLinearizerConfig
   from lumix.solvers import GLPK_CAPABILITIES, LXOptimizer

   # Build model with nonlinear terms (naturally)
   model = LXModel("production")
   profit_expr = LXNonLinearExpression().add_product(production, price)  # Bilinear term

   model.maximize(profit_expr)

   # Configure linearization
   config = LXLinearizerConfig(adaptive_breakpoints=True)

   # Automatic linearization
   linearizer = LXLinearizer(model, GLPK_CAPABILITIES, config)
   if linearizer.needs_linearization():
       linearized_model = linearizer.linearize_model()

   # Or let the optimizer do it while solving
   solution = LXOptimizer().use_solver("glpk").enable_linearization().solve(model)

**Benefits:**

- ✓ Automatic detection of nonlinear terms
- ✓ Optimal technique selection based on variable types
- ✓ No manual constraint creation
- ✓ Configurable accuracy vs. complexity trade-offs
- ✓ Same linear model on every solver

Supported Nonlinear Terms
--------------------------

Terms on a variable family apply to every instance and are summed:
``add_abs(x)`` is :math:`\sum_i |x_i|` (see :doc:`engine`).

Bilinear Products (x × y)
~~~~~~~~~~~~~~~~~~~~~~~~~~

Linearization depends on variable types:

.. list-table::
   :header-rows: 1
   :widths: 30 40 30

   * - Variable Types
     - Technique
     - Result
   * - Binary × Binary
     - AND logic
     - Exact
   * - Binary × bounded variable
     - Four bound constraints
     - Exact
   * - Integer × integer or continuous
     - Binary expansion of the integer factor
     - Exact
   * - Continuous × Continuous
     - McCormick envelopes
     - Relaxation (``UserWarning``, ``solution.relaxation``)

See :doc:`bilinear` for details.

Absolute Values (|x|)
~~~~~~~~~~~~~~~~~~~~~

Linearized using two constraints:

- z ≥ x
- z ≥ -x

This is exact where z is pushed down (minimized with a positive weight, or in a
``<=`` constraint). Other uses (maximized, negative weight, ``>=`` or ``==``
constraints) add a binary per instance and need finite bounds; see
:doc:`engine`.

Piecewise-Linear Functions
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Arbitrary nonlinear functions approximated using:

- **SOS2 formulation**: Most efficient when solver supports SOS2
- **Incremental formulation**: Binary selection variables
- **Logarithmic formulation**: Gray code encoding for many segments

See :doc:`piecewise` and :doc:`nonlinear-functions` for details.

Min/Max Functions
~~~~~~~~~~~~~~~~~

Linearized using auxiliary variables and constraints:

- min(x₁, x₂, ..., xₙ): z ≤ xᵢ for all i (exact when z is maximized)
- max(x₁, x₂, ..., xₙ): z ≥ xᵢ for all i (exact when z is minimized)

Other uses add one selection binary per argument and need finite bounds; see
:doc:`engine`.

Indicator Constraints
~~~~~~~~~~~~~~~~~~~~~

Conditional constraints linearized using Big-M method:

- if b = 1 then expr ≤ rhs → expr ≤ rhs + M(1-b)
- if b = 0 then expr ≤ rhs → expr ≤ rhs + M·b
- ``>=`` and ``==`` work the same way; M comes from the bounds of expr

See :doc:`/user-guide/nonlinear/indicator` for details.

How Linearization Works
------------------------

.. mermaid::

   sequenceDiagram
       participant User
       participant Linearizer
       participant Scanner
       participant Techniques
       participant Model

       User->>Linearizer: linearize_model()
       Linearizer->>Scanner: Scan for nonlinear terms
       Scanner-->>Linearizer: [bilinear, abs, pwl, ...]
       loop For each term
           Linearizer->>Techniques: Apply appropriate technique
           Techniques-->>Linearizer: Auxiliary vars & constraints
       end
       Linearizer->>Model: Build linearized model
       Model-->>User: Linearized model ready to solve

**Steps:**

1. **Detection**: Scan objective and constraints for nonlinear terms
2. **Expansion**: Expand each term into one item per variable instance
3. **Selection**: Choose a technique from the variable types and from how the
   item is used (minimized, maximized, in a ``<=``, ``>=`` or ``==`` row)
4. **Application**: Create auxiliary variables and constraints
5. **Assembly**: Build a new linearized model; the original model is not changed

Configuration
-------------

Fine-tune linearization behavior:

.. code-block:: python

   config = LXLinearizerConfig(
       # Big-M settings (only for unbounded variables and expressions)
       big_m_value=1e5,  # Adjust based on problem scale

       # Piecewise-linear settings
       pwl_num_segments=30,  # More segments = better accuracy
       pwl_method="sos2",  # or "incremental", "logarithmic"
       adaptive_breakpoints=True,  # Concentrate points where function curves

       # Binary expansion settings
       binary_expansion_bits=10  # Integer factors with up to 2^10 = 1024 values
   )

See :doc:`config` for all options.

Quick Examples
--------------

Basic Usage
~~~~~~~~~~~

.. code-block:: python

   from lumix import LXModel, LXNonLinearExpression, LXVariable
   from lumix.linearization import LXLinearizer, LXLinearizerConfig
   from lumix.solvers import GLPK_CAPABILITIES, LXOptimizer

   # Build model with nonlinear terms
   model = LXModel("portfolio")

   # Bilinear term: return * allocation
   profit = LXNonLinearExpression().add_product(return_var, allocation_var)

   model.maximize(profit)

   # Linearize
   config = LXLinearizerConfig()
   optimizer = LXOptimizer().use_solver("glpk")

   linearizer = LXLinearizer(model, GLPK_CAPABILITIES, config)
   linearized_model = linearizer.linearize_model()

   # Solve
   solution = optimizer.solve(linearized_model)

Using Pre-built Functions
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.linearization import LXNonLinearFunctions
   from lumix.linearization.techniques import LXPiecewiseLinearizer

   config = LXLinearizerConfig(pwl_num_segments=40)
   linearizer = LXPiecewiseLinearizer(config)

   # Exponential growth: e^(growth_rate * time)
   growth_output = LXNonLinearFunctions.exp(
       growth_rate_var,
       linearizer,
       segments=50
   )

   # Logarithmic utility: log(consumption)
   utility = LXNonLinearFunctions.log(
       consumption_var,
       linearizer,
       base=math.e
   )

   # Sigmoid probability: 1 / (1 + e^(-score))
   probability = LXNonLinearFunctions.sigmoid(
       score_var,
       linearizer,
       segments=40
   )

See :doc:`nonlinear-functions` for all available functions.

Performance Considerations
--------------------------

Accuracy vs. Complexity Trade-offs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Piecewise-Linear Approximation:**

- More segments → better accuracy but more variables/constraints
- Adaptive breakpoints → better accuracy with same number of segments
- Recommended: 20-50 segments for most functions

**Big-M Method:**

- Smaller M → tighter relaxation → faster solving
- M too small → incorrect solutions
- Recommended: Use tight bounds when possible

**McCormick Envelopes:**

- A relaxation: the optimum is a bound (``solution.relaxation`` is ``True``)
- Tighter bounds → better relaxation → faster solving
- Make a factor integer or binary for an exact product

Memory and Variables
~~~~~~~~~~~~~~~~~~~~~

Each linearized term adds auxiliary variables and constraints:

.. list-table::
   :header-rows: 1
   :widths: 30 25 25 20

   * - Term Type
     - Aux. Variables
     - Aux. Constraints
     - Complexity
   * - Bilinear (Binary × Binary)
     - 1
     - 3
     - O(1)
   * - Bilinear (Binary × Cont.)
     - 1
     - 4
     - O(1)
   * - Bilinear (Integer, K bits)
     - K binary + K + 1
     - 4K + 2
     - O(K)
   * - Bilinear (Cont. × Cont.)
     - 1
     - 4
     - O(1)
   * - Absolute value (plain / exact)
     - 1 / 2
     - 2 / 4
     - O(1)
   * - Min/Max, n terms (plain / exact)
     - 1 / 1 + n binary
     - n / 2n + 1
     - O(n)
   * - PWL (SOS2, k segments)
     - k+1 λ + 1 output + k binary
     - k + 5
     - O(k)
   * - PWL (Incremental, k seg.)
     - k binary + k delta + 1 out
     - k + 3
     - O(k)

The counts are per instance: a term on a family with n instances adds them n times.

**Optimization Tips:**

- Use filters to reduce variable expansion before linearization
- Choose appropriate pwl_num_segments based on required accuracy
- Prefer SOS2 formulation when solver supports it
- Use adaptive breakpoints to reduce segments needed

Component Details
-----------------

Dive deeper into each component:

.. toctree::
   :maxdepth: 2

   config
   engine
   bilinear
   piecewise
   nonlinear-functions

Next Steps
----------

Continue to:

- :doc:`config` - Configuration options
- :doc:`engine` - Using the linearization engine
- :doc:`bilinear` - Bilinear product linearization
- :doc:`piecewise` - Piecewise-linear approximation
- :doc:`nonlinear-functions` - Pre-built function approximations
- :doc:`/api/linearization/index` - Complete API reference
- :doc:`/development/linearization-architecture` - Architecture details
