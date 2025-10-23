Pre-built Nonlinear Functions
==============================

Ready-to-use piecewise-linear approximations for common nonlinear functions.

Overview
--------

The :class:`~lumix.linearization.functions.LXNonLinearFunctions` class provides
pre-built approximations for frequently used nonlinear functions, eliminating
the need to manually configure piecewise-linear formulations.

Available Functions
-------------------

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

      from lumix.linearization import LXNonLinearFunctions
      from lumix.linearization.techniques import LXPiecewiseLinearizer

      linearizer = LXPiecewiseLinearizer(config)

      # Exponential growth
      growth = LXNonLinearFunctions.exp(time_var, linearizer, segments=50)

      # Use in model
      model.maximize(profit * growth)

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

      # Base-2 for information theory
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

      # Euclidean distance component
      distance = LXNonLinearFunctions.sqrt(
          x_squared + y_squared,
          linearizer,
          segments=25
      )

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

      # Market saturation
      market_share = capacity * LXNonLinearFunctions.sigmoid(
          time_var,
          linearizer,
          segments=50
      )

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

      # Seasonal demand (annual cycle)
      day_angle = day_of_year * 2 * math.pi / 365
      seasonal_factor = LXNonLinearFunctions.sin(
          day_angle_var,
          linearizer,
          segments=50
      )

      # Daily temperature variation
      hour_angle = hour * 2 * math.pi / 24
      temp_variation = LXNonLinearFunctions.cos(
          hour_angle_var,
          linearizer
      )

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

   from lumix import LXModel, LXVariable
   from lumix.linearization import LXNonLinearFunctions
   from lumix.linearization.techniques import LXPiecewiseLinearizer
   from lumix.linearization.config import LXLinearizerConfig

   # Cobb-Douglas production function: Q = A * L^α * K^β
   # where α + β = 1 (constant returns to scale)

   A = 100  # Total factor productivity
   alpha = 0.7
   beta = 0.3

   # Variables
   labor = LXVariable[Factory, float]("labor").continuous().bounds(0, 1000)
   capital = LXVariable[Factory, float]("capital").continuous().bounds(0, 5000)

   # Configure linearizer
   config = LXLinearizerConfig(
       pwl_method="sos2",
       pwl_num_segments=30,
       adaptive_breakpoints=True
   )
   linearizer = LXPiecewiseLinearizer(config)

   # Approximate L^α and K^β
   labor_component = LXNonLinearFunctions.power(
       labor,
       exponent=alpha,
       linearizer=linearizer,
       segments=30
   )

   capital_component = LXNonLinearFunctions.power(
       capital,
       exponent=beta,
       linearizer=linearizer,
       segments=30
   )

   # Production output (A is constant, components are linearized)
   # Q = A * labor_component * capital_component
   # (This will require bilinear linearization for the product)

Example 2: Seasonal Demand Model
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import math
   from lumix.linearization import LXNonLinearFunctions

   # Seasonal demand: D(t) = baseline + amplitude * sin(2π*t/period)

   baseline = 1000  # Base demand
   amplitude = 300  # Seasonal variation
   period = 365  # Annual cycle

   # Time variable (day of year)
   day = LXVariable[Period, float]("day").continuous().bounds(0, 365)

   # Configure
   config = LXLinearizerConfig(pwl_num_segments=50)
   linearizer = LXPiecewiseLinearizer(config)

   # Seasonal component
   # Note: Need to transform day → angle in constraint/expression
   # angle = 2π * day / 365

   # For simplicity, assume angle_var is pre-computed
   angle_var = (2 * math.pi / period) * day

   seasonal_component = LXNonLinearFunctions.sin(
       angle_var,
       linearizer,
       segments=50  # Cover full cycle smoothly
   )

   # Total demand
   demand = baseline + amplitude * seasonal_component

Example 3: Utility Maximization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Maximize consumer utility: U = ln(x₁) + ln(x₂)
   # Subject to budget constraint: p₁*x₁ + p₂*x₂ ≤ income

   # Consumption variables
   consumption_1 = LXVariable[Good, float]("c1").continuous().bounds(1, 100)
   consumption_2 = LXVariable[Good, float]("c2").continuous().bounds(1, 100)

   # Prices and income
   p1, p2 = 10, 20
   income = 1000

   # Configure
   config = LXLinearizerConfig(
       pwl_method="sos2",
       pwl_num_segments=35,
       adaptive_breakpoints=True  # Log curves near 0
   )
   linearizer = LXPiecewiseLinearizer(config)

   # Utility components
   utility_1 = LXNonLinearFunctions.log(consumption_1, linearizer)
   utility_2 = LXNonLinearFunctions.log(consumption_2, linearizer)

   # Total utility
   total_utility = utility_1 + utility_2

   # Model
   model = LXModel("utility_maximization")
   model.maximize(total_utility)

   # Budget constraint
   model.add_constraint(
       LXConstraint("budget")
       .expression(p1 * consumption_1 + p2 * consumption_2)
       .le()
       .rhs(income)
   )

Best Practices
--------------

1. **Choose Appropriate Segments**

   .. code-block:: python

      # Smooth functions: fewer segments
      sqrt_var = LXNonLinearFunctions.sqrt(x, linearizer, segments=15)

      # Curved functions: more segments
      exp_var = LXNonLinearFunctions.exp(x, linearizer, segments=50)

2. **Use Adaptive for Curved Functions**

   .. code-block:: python

      # Exponential, log, sigmoid: use adaptive
      config = LXLinearizerConfig(adaptive_breakpoints=True)

      # Smooth functions: uniform is fine
      config = LXLinearizerConfig(adaptive_breakpoints=False)

3. **Set Appropriate Domain Bounds**

   .. code-block:: python

      # For logarithm: avoid x ≤ 0
      x = LXVariable[Model, float]("x").bounds(lower=1, upper=1000)
      log_x = LXNonLinearFunctions.log(x, linearizer)

      # For sqrt: x ≥ 0
      x = LXVariable[Model, float]("x").bounds(lower=0, upper=100)
      sqrt_x = LXNonLinearFunctions.sqrt(x, linearizer)

4. **Validate Approximation Accuracy**

   .. code-block:: python

      import numpy as np

      # Test points
      x_vals = np.linspace(0, 10, 50)

      for x in x_vals:
          true_value = math.exp(x)
          # Get approximation from solved model
          approx_value = get_solution_value(f"lambda_{x}_...")

          error = abs(true_value - approx_value) / true_value
          assert error < 0.01, f"Error too large: {error:.2%}"

See Also
--------

- :doc:`piecewise` - Piecewise-linear approximation details
- :doc:`config` - Configuration options
- :doc:`engine` - Linearization engine usage
- :doc:`/api/linearization/index` - API reference
