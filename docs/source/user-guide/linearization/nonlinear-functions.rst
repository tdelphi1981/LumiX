Pre-built Nonlinear Functions
==============================

Ready-to-use piecewise-linear approximations for common nonlinear functions.

Overview
--------

The :class:`~lumix.linearization.functions.LXNonLinearFunctions` class provides
pre-built approximations for frequently used nonlinear functions, eliminating
the need to manually configure piecewise-linear formulations.

Each function calls
:meth:`LXPiecewiseLinearizer.approximate_function
<lumix.linearization.techniques.piecewise.LXPiecewiseLinearizer.approximate_function>`
and returns the output variable; the input must be a **single variable** (a
scalar, or a family with one instance). For a variable family use
``LXNonLinearExpression().add_piecewise(x, func)``, which applies to every
instance (see :doc:`piecewise`).

Using the Output Variable
-------------------------

A function returns an output variable that equals the piecewise-linear
approximation only once the linearizer's auxiliary variables and constraints
are in the model. Add them before solving:

.. code-block:: python

   import math
   from lumix import LXLinearExpression, LXModel, LXOptimizer, LXVariable
   from lumix.linearization import LXNonLinearFunctions
   from lumix.linearization.config import LXLinearizerConfig
   from lumix.linearization.techniques import LXPiecewiseLinearizer

   x = LXVariable("x").continuous().bounds(lower=0, upper=3)

   linearizer = LXPiecewiseLinearizer(LXLinearizerConfig())
   exp_x = LXNonLinearFunctions.exp(x, linearizer)  # output variable: e**x

   model = LXModel("exp_demo").add_variable(x)
   for var in linearizer.auxiliary_vars:            # output and piecewise variables
       model.add_variable(var)
   for constraint in linearizer.auxiliary_constraints:
       model.add_constraint(constraint)

   # minimize e**x - 2x (the minimum is at x = ln 2)
   model.minimize(LXLinearExpression().add_term(exp_x, 1.0).add_term(x, -2.0))
   solution = LXOptimizer().use_solver("ortools").solve(model)

Without the two loops the output variable is free within its bounds, and the
solver returns a meaningless optimum. The piecewise formulation uses binary
variables, so the model needs a MIP solver.

The simpler alternative is a piecewise term in an expression; with
``enable_linearization()`` LumiX adds the auxiliary variables itself:

.. code-block:: python

   from lumix import LXNonLinearExpression

   model = LXModel("exp_demo").add_variable(x)
   model.minimize(
       LXNonLinearExpression()
       .add_piecewise(x, math.exp)
       .add_linear(LXLinearExpression().add_term(x, -2.0))
   )
   solution = LXOptimizer().use_solver("ortools").enable_linearization().solve(model)

.. note::

   The number of segments is the function's ``segments`` argument, and the
   breakpoint placement is fixed per function: adaptive for ``exp``, ``log``,
   ``sigmoid`` and ``tan``, uniform for ``sqrt``, ``sin`` and ``cos``, adaptive
   for ``power`` when ``|exponent| > 2``, and the ``adaptive`` argument for
   ``custom``. Of :class:`~lumix.linearization.config.LXLinearizerConfig`, only
   ``pwl_method`` applies to these functions.

Available Functions
-------------------

The snippets below assume ``linearizer`` from the previous section and add the
auxiliaries to the model as shown there.

Exponential Function
~~~~~~~~~~~~~~~~~~~~

.. py:staticmethod:: exp(var, linearizer, segments=30)

   Exponential function: e^x

   **Use Cases:**

   - Population growth models
   - Compound interest calculations
   - Decay processes

   **Example:**

   .. code-block:: python

      # Exponential growth
      growth = LXNonLinearFunctions.exp(time_var, linearizer, segments=50)

      # Use in model: profit_per_unit * e**time
      model.maximize(LXLinearExpression().add_term(growth, profit_per_unit))

Logarithm Function
~~~~~~~~~~~~~~~~~~

.. py:staticmethod:: log(var, linearizer, base=math.e, segments=30)

   Logarithm: log_base(x)

   **Use Cases:**

   - Utility functions in economics
   - Information entropy
   - Signal processing

   **Example:**

   .. code-block:: python

      # Natural logarithm
      ln_utility = LXNonLinearFunctions.log(consumption, linearizer)

      # Base-10 logarithm
      log10_signal = LXNonLinearFunctions.log(
          signal_power,
          linearizer,
          base=10
      )

      # Base-2 for information theory (bounds above 0, e.g. bounds(0.01, 1))
      entropy = LXNonLinearFunctions.log(probability, linearizer, base=2)

Square Root Function
~~~~~~~~~~~~~~~~~~~~

.. py:staticmethod:: sqrt(var, linearizer, segments=20)

   Square root: √x

   **Use Cases:**

   - Standard deviation calculations
   - Distance metrics
   - Flow velocity in pipes

   **Example:**

   .. code-block:: python

      # Standard deviation
      std_dev = LXNonLinearFunctions.sqrt(variance_var, linearizer)

      # Euclidean distance: the input must be one variable, so define
      # dist_sq == dx2 + dy2 first
      model.add_constraint(
          LXConstraint("dist_sq_def")
          .expression(
              LXLinearExpression()
              .add_term(dist_sq, 1.0)
              .add_term(dx2, -1.0)
              .add_term(dy2, -1.0)
          )
          .eq()
          .rhs(0)
      )
      distance = LXNonLinearFunctions.sqrt(dist_sq, linearizer, segments=25)

Power Function
~~~~~~~~~~~~~~

.. py:staticmethod:: power(var, exponent, linearizer, segments=25)

   Power function: x^n

   **Use Cases:**

   - Polynomial cost functions
   - Area/volume calculations
   - Cobb-Douglas production functions

   **Example:**

   .. code-block:: python

      # Cubic cost function
      cubic_cost = LXNonLinearFunctions.power(
          production,
          exponent=3,
          linearizer=linearizer,
          segments=30
      )

      # Quadratic relationship
      area = LXNonLinearFunctions.power(radius, 2, linearizer)

      # Fractional power (Cobb-Douglas)
      output = LXNonLinearFunctions.power(
          capital,
          exponent=0.3,
          linearizer=linearizer
      )

   An integer exponent works on the whole real line (``(-3)**2 = 9``,
   ``(-2)**3 = -8``). A fractional exponent is not real for negative inputs: if
   the variable's domain includes negative values, ``power`` raises
   ``ValueError`` ("not real"); bound the variable at 0 from below.

   .. versionchanged:: 0.3.0
      Negative inputs returned 0 before 0.3.0, so even powers of negative values
      were wrong.

Sigmoid Function
~~~~~~~~~~~~~~~~

.. py:staticmethod:: sigmoid(var, linearizer, segments=40)

   Sigmoid function: 1 / (1 + e^(-x))

   **Use Cases:**

   - Probability models
   - Market saturation curves
   - Learning curves

   **Example:**

   .. code-block:: python

      # Probability of success
      probability = LXNonLinearFunctions.sigmoid(score_var, linearizer)

      # Market saturation: capacity * sigmoid(time)
      saturation = LXNonLinearFunctions.sigmoid(time_var, linearizer, segments=50)
      market_share = LXLinearExpression().add_term(saturation, capacity)

Trigonometric Functions
~~~~~~~~~~~~~~~~~~~~~~~

.. py:staticmethod:: sin(var, linearizer, segments=50)
.. py:staticmethod:: cos(var, linearizer, segments=50)
.. py:staticmethod:: tan(var, linearizer, segments=40)

   Trigonometric functions: sin(x), cos(x), tan(x)

   **Use Cases:**

   - Seasonal demand patterns
   - Cyclical behavior
   - Engineering applications

   **Example:**

   .. code-block:: python

      import math

      # Seasonal demand (annual cycle): angle = 2*pi * day / 365
      day = LXVariable("day").continuous().bounds(0, 365)
      angle = LXVariable("angle").continuous().bounds(0, 2 * math.pi)
      model.add_constraint(
          LXConstraint("angle_def")
          .expression(
              LXLinearExpression()
              .add_term(angle, 1.0)
              .add_term(day, -2 * math.pi / 365)
          )
          .eq()
          .rhs(0)
      )
      seasonal_factor = LXNonLinearFunctions.sin(angle, linearizer, segments=50)

      # Daily temperature variation (hour_angle bounded to [0, 2*pi])
      temp_variation = LXNonLinearFunctions.cos(hour_angle, linearizer)

Custom Functions
~~~~~~~~~~~~~~~~

.. py:staticmethod:: custom(var, func, linearizer, segments=30, adaptive=True)

   Custom user-defined function

   **Use Cases:**

   - Proprietary cost curves
   - Domain-specific relationships
   - Complex piecewise functions

   **Example:**

   .. code-block:: python

      # Custom discount curve
      def discount_curve(quantity):
          if quantity < 100:
              return 1.0  # No discount
          elif quantity < 1000:
              return 0.9  # 10% discount
          else:
              return 0.8  # 20% discount

      discount_factor = LXNonLinearFunctions.custom(
          quantity_var,
          discount_curve,
          linearizer,
          segments=50,
          adaptive=False  # Uniform for piecewise
      )

Complete Examples
-----------------

Example 1: Economic Production Function
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXLinearExpression, LXModel, LXOptimizer, LXVariable
   from lumix.linearization import LXNonLinearFunctions
   from lumix.linearization.config import LXLinearizerConfig
   from lumix.linearization.techniques import LXPiecewiseLinearizer

   # Cobb-Douglas production Q = A * L^alpha * K^beta with capital fixed at K0:
   # choose labor L to maximize price * Q - wage * L
   A, alpha, beta = 10.0, 0.5, 0.5
   K0 = 4.0             # fixed capital
   price, wage = 1.0, 1.0

   labor = LXVariable("labor").continuous().bounds(0, 400)

   linearizer = LXPiecewiseLinearizer(LXLinearizerConfig(pwl_method="sos2"))
   labor_component = LXNonLinearFunctions.power(labor, exponent=alpha,
                                                linearizer=linearizer, segments=40)

   model = LXModel("cobb_douglas").add_variable(labor)
   for var in linearizer.auxiliary_vars:
       model.add_variable(var)
   for constraint in linearizer.auxiliary_constraints:
       model.add_constraint(constraint)

   scale = A * K0 ** beta  # constant part of Q
   model.maximize(
       LXLinearExpression()
       .add_term(labor_component, price * scale)
       .add_term(labor, -wage)
   )

   solution = LXOptimizer().use_solver("ortools").solve(model)
   print(f"labor = {solution.variables['labor']:.1f}, profit = {solution.objective_value:.2f}")
   # labor = 100.0, profit = 100.00 (the exact optimum)

With both factors variable, ``Q`` is a product of two output variables, which
the bilinear linearizer can only relax (McCormick envelopes, see
:doc:`bilinear`). Maximizing ``ln Q = ln A + alpha ln L + beta ln K`` instead
keeps the model separable, as in Example 3.

Example 2: Seasonal Demand Model
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import math
   from lumix import LXConstraint, LXLinearExpression, LXModel, LXOptimizer, LXVariable
   from lumix.linearization import LXNonLinearFunctions
   from lumix.linearization.config import LXLinearizerConfig
   from lumix.linearization.techniques import LXPiecewiseLinearizer

   # Seasonal demand D(t) = baseline + amplitude * sin(2*pi*t / period):
   # find the day of peak demand
   baseline = 1000  # Base demand
   amplitude = 300  # Seasonal variation
   period = 365     # Annual cycle

   day = LXVariable("day").continuous().bounds(0, period)
   angle = LXVariable("angle").continuous().bounds(0, 2 * math.pi)

   linearizer = LXPiecewiseLinearizer(LXLinearizerConfig())
   seasonal = LXNonLinearFunctions.sin(angle, linearizer, segments=50)

   model = LXModel("seasonal_demand").add_variable(day).add_variable(angle)
   for var in linearizer.auxiliary_vars:
       model.add_variable(var)
   for constraint in linearizer.auxiliary_constraints:
       model.add_constraint(constraint)

   # angle = 2*pi * day / period (the input of sin must be one variable)
   model.add_constraint(
       LXConstraint("angle_def")
       .expression(
           LXLinearExpression()
           .add_term(angle, 1.0)
           .add_term(day, -2 * math.pi / period)
       )
       .eq()
       .rhs(0)
   )

   demand = LXLinearExpression().add_term(seasonal, amplitude).add_constant(baseline)
   model.maximize(demand)

   solution = LXOptimizer().use_solver("ortools").solve(model)
   print(f"peak on day {solution.variables['day']:.0f}: demand {solution.objective_value:.0f}")
   # peak on day 95: demand 1299 (exact: day 91.25, demand 1300; the
   # approximation peaks at a breakpoint near pi/2)

Example 3: Utility Maximization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXConstraint, LXLinearExpression, LXModel, LXOptimizer, LXVariable
   from lumix.linearization import LXNonLinearFunctions
   from lumix.linearization.config import LXLinearizerConfig
   from lumix.linearization.techniques import LXPiecewiseLinearizer

   # Maximize consumer utility U = ln(c1) + ln(c2)
   # subject to the budget p1*c1 + p2*c2 <= income

   # Consumption variables (bounded away from 0, where ln is undefined)
   c1 = LXVariable("c1").continuous().bounds(1, 100)
   c2 = LXVariable("c2").continuous().bounds(1, 100)

   # Prices and income
   p1, p2 = 10, 20
   income = 1000

   linearizer = LXPiecewiseLinearizer(LXLinearizerConfig(pwl_method="sos2"))
   utility_1 = LXNonLinearFunctions.log(c1, linearizer, segments=35)
   utility_2 = LXNonLinearFunctions.log(c2, linearizer, segments=35)

   model = LXModel("utility_maximization").add_variable(c1).add_variable(c2)
   for var in linearizer.auxiliary_vars:
       model.add_variable(var)
   for constraint in linearizer.auxiliary_constraints:
       model.add_constraint(constraint)

   # Total utility: the sum of the two output variables
   model.maximize(LXLinearExpression().add_term(utility_1, 1.0).add_term(utility_2, 1.0))

   # Budget constraint
   model.add_constraint(
       LXConstraint("budget")
       .expression(LXLinearExpression().add_term(c1, p1).add_term(c2, p2))
       .le()
       .rhs(income)
   )

   solution = LXOptimizer().use_solver("ortools").solve(model)
   print(f"c1 = {solution.variables['c1']:.1f}, c2 = {solution.variables['c2']:.1f}, "
         f"utility = {solution.objective_value:.3f}")
   # c1 = 51.5, c2 = 24.2, utility = 7.129
   # (exact: c1 = 50, c2 = 25, utility = ln 50 + ln 25 = 7.131)

The same model with piecewise terms and ``enable_linearization()``:

.. code-block:: python

   import math
   from lumix import LXNonLinearExpression

   model = LXModel("utility_maximization").add_variable(c1).add_variable(c2)
   model.add_constraint(
       LXConstraint("budget")
       .expression(LXLinearExpression().add_term(c1, p1).add_term(c2, p2))
       .le()
       .rhs(income)
   )
   model.maximize(
       LXNonLinearExpression()
       .add_piecewise(c1, math.log, num_segments=35)
       .add_piecewise(c2, math.log, num_segments=35)
   )
   solution = LXOptimizer().use_solver("ortools").enable_linearization().solve(model)

Best Practices
--------------

1. **Choose Appropriate Segments**

   .. code-block:: python

      # Smooth functions: fewer segments
      sqrt_var = LXNonLinearFunctions.sqrt(x, linearizer, segments=15)

      # Curved functions: more segments
      exp_var = LXNonLinearFunctions.exp(x, linearizer, segments=50)

2. **Use Adaptive Breakpoints for Curved Functions**

   The built-in functions fix the placement (see the note above). For your own
   function, choose it with ``custom``:

   .. code-block:: python

      # Sharp curvature: adaptive breakpoints
      y = LXNonLinearFunctions.custom(x, lambda v: v ** 4, linearizer, adaptive=True)

      # Gentle curvature: uniform breakpoints are fine
      y = LXNonLinearFunctions.custom(x, lambda v: v ** 1.5, linearizer, adaptive=False)

3. **Set Appropriate Domain Bounds**

   .. code-block:: python

      # For logarithm: avoid x ≤ 0
      x = LXVariable("x").continuous().bounds(lower=1, upper=1000)
      log_x = LXNonLinearFunctions.log(x, linearizer)

      # For sqrt: x ≥ 0
      y = LXVariable("y").continuous().bounds(lower=0, upper=100)
      sqrt_y = LXNonLinearFunctions.sqrt(y, linearizer)

4. **Validate Approximation Accuracy**

   .. code-block:: python

      # After solving the model of "Using the Output Variable"
      x_val = solution.variables["x"]
      approx_value = solution.variables[exp_x.name]  # the output variable

      error = abs(math.exp(x_val) - approx_value) / math.exp(x_val)
      print(f"relative error at x = {x_val:.3f}: {error:.2%}")

See Also
--------

- :doc:`piecewise` - Piecewise-linear approximation details
- :doc:`config` - Configuration options
- :doc:`engine` - Linearization engine usage
- :doc:`/api/linearization/index` - API reference
