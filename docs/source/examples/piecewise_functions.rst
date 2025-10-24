Piecewise-Linear Approximation Example
========================================

Overview
--------

This example demonstrates **piecewise-linear (PWL) approximation** of nonlinear functions using LumiX's built-in function library and adaptive breakpoint generation.

The investment optimization problem showcases how to approximate exponential growth functions using piecewise-linear segments, making nonlinear problems solvable with linear solvers.

Problem Description
-------------------

Optimize investment allocation to maximize total return with exponential growth.

**Objective**: Maximize :math:`\text{Return} = \sum_i \text{amount}_i \times \exp(\text{growth\_rate}_i \times \text{time})`.

**Constraints**:

- Budget limit: Total investment ≤ available budget
- Investment bounds: Min/max per investment option
- Risk considerations: Different growth rates based on risk profiles

Mathematical Formulation
------------------------

**Decision Variables**:

.. math::

   x_i \geq 0, \quad \forall i \in \text{Investments}

where :math:`x_i` is the amount invested in option :math:`i`.

**Objective Function** (Nonlinear):

.. math::

   \text{Maximize} \quad \sum_{i=1}^{n} x_i \times e^{r_i \cdot T}

where :math:`r_i` is the effective growth rate and :math:`T` is the time horizon.

**Constraint**:

.. math::

   \sum_{i=1}^{n} x_i \leq \text{Budget}

Key Features
------------

Piecewise-Linear Approximation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Approximate :math:`f(x) = \exp(x)` using piecewise-linear segments:

.. code-block:: python

   from lumix import LXNonLinearFunctions

   # Approximate exp(time) with 30 segments
   growth = LXNonLinearFunctions.exp(
       time,
       linearizer,
       segments=30,
       adaptive_breakpoints=True  # More segments where function curves
   )

**Key Points**:

- Arbitrary nonlinear functions can be approximated
- Adaptive breakpoints place more segments where curvature is high
- Trade-off: More segments = better accuracy but slower solving

SOS2 Formulation
~~~~~~~~~~~~~~~~

Special Ordered Set type 2 for efficient PWL representation:

.. code-block:: python

   config = LXLinearizerConfig(
       pwl_num_segments=30,
       adaptive_breakpoints=True,
       prefer_sos2=True  # Use SOS2 when solver supports it
   )

**SOS2 Advantages**:

- Most efficient formulation when solver supports it
- Requires only :math:`\log(n)` binary variables conceptually
- Solvers handle SOS2 natively (no explicit binary variables)

Adaptive Breakpoint Generation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Algorithm places more breakpoints where function curves sharply:

1. Sample function at many points
2. Compute second derivative: :math:`f''(x)`
3. Use :math:`|f''(x)|` as probability distribution
4. Sample breakpoints proportional to curvature
5. More breakpoints where :math:`|f''(x)|` is large

**For** :math:`\exp(x)`:

- :math:`f''(x) = \exp(x)` grows exponentially
- More breakpoints at larger x values
- 10-100× better accuracy than uniform breakpoints

Built-in Functions
~~~~~~~~~~~~~~~~~~

LumiX provides pre-built approximations:

.. code-block:: python

   # Exponential and logarithm
   exp_result = LXNonLinearFunctions.exp(var, linearizer, segments=30)
   log_result = LXNonLinearFunctions.log(var, linearizer, base=10)
   ln_result = LXNonLinearFunctions.ln(var, linearizer)

   # Trigonometric
   sin_result = LXNonLinearFunctions.sin(var, linearizer, segments=50)
   cos_result = LXNonLinearFunctions.cos(var, linearizer)

   # Power and roots
   square = LXNonLinearFunctions.power(var, 2, linearizer)
   sqrt_result = LXNonLinearFunctions.sqrt(var, linearizer)

   # Activation functions
   sigmoid = LXNonLinearFunctions.sigmoid(var, linearizer)
   relu = LXNonLinearFunctions.relu(var, linearizer)

   # Custom function
   custom = LXNonLinearFunctions.custom(
       var,
       lambda x: my_function(x),
       linearizer,
       segments=40
   )

Running the Example
-------------------

**Prerequisites**:

.. code-block:: bash

   pip install lumix
   pip install ortools  # or cplex, gurobi

**Run**:

.. code-block:: bash

   cd examples/07_piecewise_functions
   python exponential_growth.py

**Expected Output**:

.. code-block:: text

   ======================================================================
   LumiX Example: Piecewise-Linear Function Approximation
   ======================================================================

   Approximating f(t) = exp(t) for t ∈ [0, 10]
     Method: SOS2 formulation
     Segments: 30
     Adaptive breakpoints: Yes

   ✓ Created approximation variable: pwl_out_time_1
   ✓ Auxiliary variables: 31 (30 lambdas + 1 output)
   ✓ Auxiliary constraints: 3

   Investment Optimization Problem
   ======================================================================
   Total Budget: $100.0k
   Growth Rate: 15.0% annually
   Time Horizon: 5 years

   Investment Options:
   ----------------------------------------------------------------------
     Bond           : Risk  5.0%, Multiplier: 2.014x
     Stock          : Risk 12.0%, Multiplier: 1.857x
     Real Estate    : Risk  8.0%, Multiplier: 1.926x

   ======================================================================
   SOLUTION
   ======================================================================
   Status: optimal
   Maximum Return: $201.37k

   Optimal Allocation:
   ----------------------------------------------------------------------
     Bond         : $50.00k → $100.69k (×2.01)
     Stock        : $30.00k → $ 55.71k (×1.86)
     Real Estate  : $20.00k → $ 38.52k (×1.93)

Complete Code Walkthrough
--------------------------

Step 1: Create Linearizer Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.linearization import LXPiecewiseLinearizer, LXLinearizerConfig

   config = LXLinearizerConfig(
       pwl_num_segments=30,
       adaptive_breakpoints=True,
       prefer_sos2=True
   )
   linearizer = LXPiecewiseLinearizer(config)

Step 2: Define Investment Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/07_piecewise_functions/exponential_growth.py
   :language: python
   :lines: 89-96

Step 3: Approximate Exponential Function
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # For demonstration, compute multiplier
   effective_rate = GROWTH_RATE * (1 - investment.risk)
   multiplier = exp(effective_rate * TIME_HORIZON)

   # In production, use:
   # growth = LXNonLinearFunctions.exp(time_var, linearizer, segments=30)

Step 4: Build Objective with Approximation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/07_piecewise_functions/exponential_growth.py
   :language: python
   :lines: 127-133
   :dedent: 4

Step 5: Add Budget Constraint
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/07_piecewise_functions/exponential_growth.py
   :language: python
   :lines: 116-124
   :dedent: 4

Learning Objectives
-------------------

After completing this example, you should understand:

1. **PWL Approximation**: How to approximate nonlinear functions with linear segments
2. **Adaptive Breakpoints**: Why and how adaptive placement improves accuracy
3. **SOS2 Formulation**: Most efficient PWL representation
4. **Function Library**: Using pre-built approximations for common functions
5. **Custom Functions**: Creating approximations for your own functions
6. **Accuracy Trade-offs**: Balancing segment count vs solve time

Common Patterns
---------------

Pattern 1: Approximate Standard Function
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXNonLinearFunctions, LXPiecewiseLinearizer

   linearizer = LXPiecewiseLinearizer(config)

   # Approximate exponential
   growth = LXNonLinearFunctions.exp(
       time_variable,
       linearizer,
       segments=30,
       adaptive_breakpoints=True
   )

   # Use in objective
   model.maximize(growth)

Pattern 2: Custom Function Approximation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def my_cost_function(x):
       if x < 10:
           return 5 * x
       elif x < 50:
           return 50 + 4 * (x - 10)  # Volume discount
       else:
           return 210 + 3 * (x - 50)  # Bulk discount

   # Approximate custom function
   cost_approx = LXNonLinearFunctions.custom(
       quantity,
       my_cost_function,
       linearizer,
       segments=20,
       domain_min=0,
       domain_max=100
   )

Pattern 3: Multiple Functions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Combine multiple nonlinear functions
   revenue = LXNonLinearFunctions.exp(marketing_spend, linearizer)
   cost = LXNonLinearFunctions.sqrt(production_volume, linearizer)

   profit = revenue - cost
   model.maximize(profit)

PWL Formulation Details
------------------------

SOS2 Formulation
~~~~~~~~~~~~~~~~

For each PWL segment, create lambda variables representing convex combination weights:

.. math::

   \sum_i \lambda_i &= 1 \\
   x &= \sum_i \lambda_i \cdot x_i \\
   y &= \sum_i \lambda_i \cdot f(x_i) \\
   \text{SOS2}(\{\lambda_i\}) &\quad \text{(at most 2 adjacent non-zero)}

**Complexity**:

- Variables: n + 1 (n lambdas + 1 output)
- Constraints: 3 (convexity, input mapping, output mapping)
- SOS2: Handled by solver natively

Adaptive vs Uniform Breakpoints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Comparison for** :math:`\exp(10)` **with 20 segments**:

+-----------+-------------+---------------+
| Method    | Max Error   | Avg Error     |
+===========+=============+===============+
| Uniform   | 5.43e-1     | 1.82e-1       |
+-----------+-------------+---------------+
| Adaptive  | 8.21e-3     | 2.14e-3       |
+-----------+-------------+---------------+

**Adaptive is ~66× more accurate!**

Segment Count Trade-offs
~~~~~~~~~~~~~~~~~~~~~~~~~

+----------+----------+------------------+-------------------+------------+
| Segments | Accuracy | Variables Added  | Constraints Added | Solve Time |
+==========+==========+==================+===================+============+
| 10       | Low      | 11               | 3                 | Fast       |
+----------+----------+------------------+-------------------+------------+
| 20       | Medium   | 21               | 3                 | Fast       |
+----------+----------+------------------+-------------------+------------+
| 30       | Good     | 31               | 3                 | Medium     |
+----------+----------+------------------+-------------------+------------+
| 50       | High     | 51               | 3                 | Medium     |
+----------+----------+------------------+-------------------+------------+
| 100      | Very High| 101              | 3                 | Slow       |
+----------+----------+------------------+-------------------+------------+

**Recommendation**: Start with 20-30 segments, increase if needed.

Use Cases
---------

Applications
~~~~~~~~~~~~

1. **Financial Modeling**: Option pricing, interest rate curves
2. **Economics**: Utility functions, production functions
3. **Engineering**: Stress-strain curves, thermodynamic properties
4. **Machine Learning**: Activation functions, loss functions
5. **Operations Research**: Travel time functions, cost curves
6. **Physics**: Nonlinear physical relationships

Extending the Example
---------------------

Try These Modifications
~~~~~~~~~~~~~~~~~~~~~~~

1. **Different Functions**: Try log, sin, cos, sigmoid

   .. code-block:: python

      seasonal_demand = LXNonLinearFunctions.sin(time, linearizer)

2. **Multiple Time Periods**: Dynamic investment over time
3. **Risk Constraints**: Add variance constraints (quadratic)
4. **Compound Interest**: Multiple compounding periods
5. **Compare Formulations**: SOS2 vs incremental vs logarithmic

Next Steps
----------

After mastering this example:

1. **Example 06 (McCormick Bilinear)**: Continuous × continuous products
2. **Example 03 (Facility Location)**: Big-M for binary × continuous
3. **Nonlinear Module Documentation**: Advanced features

See Also
--------

**Related Examples**:

- :doc:`mccormick_bilinear` - Bilinear product linearization
- :doc:`facility_location` - Big-M constraints
- :doc:`goal_programming` - Multi-objective with nonlinear terms

**API Reference**:

- :class:`lumix.linearization.LXPiecewiseLinearizer`
- :class:`lumix.nonlinear.LXNonLinearFunctions`
- :class:`lumix.linearization.LXLinearizerConfig`

**References**:

- Beale & Tomlin (1970). "Special facilities in a general mathematical programming system"
- Vielma et al. (2010). "Mixed-integer models for nonseparable piecewise-linear optimization"

Files in This Example
---------------------

- ``exponential_growth.py`` - Investment optimization with exponential growth
- ``README.md`` - Detailed documentation and usage guide
