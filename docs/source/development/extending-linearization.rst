Extending Linearization
=======================

Guide for developers who want to add new linearization techniques or customize existing ones.

Overview
--------

The linearization module is designed to be extensible. You can:

1. **Add new linearization techniques** for different term types
2. **Customize existing techniques** with new formulations
3. **Add pre-built function approximations** to LXNonLinearFunctions
4. **Create custom configuration options** for your techniques

Adding a New Linearization Technique
-------------------------------------

Example: Linearizing Absolute Value Squared (abs(x)²)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Let's create a new linearizer for absolute value squared terms.

**Step 1: Define the Linearizer Class**

.. code-block:: python

   from typing import List
   from lumix.core.variables import LXVariable
   from lumix.core.constraints import LXConstraint
   from lumix.core.expressions import LXLinearExpression
   from lumix.linearization.config import LXLinearizerConfig

   class LXAbsSquaredLinearizer:
       """
       Linearize absolute value squared: z = |x|²

       Uses the reformulation:
       - t = |x| (linearized via standard absolute value)
       - z = t² (linearized via piecewise-linear or McCormick if bounded)
       """

       def __init__(self, config: LXLinearizerConfig):
           """
           Initialize the linearizer.

           Args:
               config: Linearization configuration
           """
           self.config = config
           self.auxiliary_vars: List[LXVariable] = []
           self.auxiliary_constraints: List[LXConstraint] = []
           self._aux_counter = 0

       def linearize_abs_squared(
           self,
           var: LXVariable,
           coefficient: float = 1.0
       ) -> LXVariable:
           """
           Linearize |x|² term.

           Args:
               var: Input variable
               coefficient: Multiplier

           Returns:
               Auxiliary variable representing |x|²

           Example:
               >>> linearizer = LXAbsSquaredLinearizer(config)
               >>> z = linearizer.linearize_abs_squared(x_var)
               >>> # z represents |x|²
           """
           # Step 1: Create auxiliary variable for |x|
           abs_name = f"aux_abs_{var.name}_{self._aux_counter}"
           self._aux_counter += 1

           t = (
               LXVariable[str, float](abs_name)
               .continuous()
               .bounds(lower=0, upper=None)  # |x| ≥ 0
               .indexed_by(lambda x: x)
               .from_data([abs_name])
           )
           self.auxiliary_vars.append(t)

           # Step 2: Add constraints for |x|
           # t ≥ x
           self.auxiliary_constraints.append(
               LXConstraint(f"{abs_name}_ge_x")
               .expression(
                   LXLinearExpression()
                   .add_term(t, 1.0)
                   .add_term(var, -1.0)
               )
               .ge()
               .rhs(0)
           )

           # t ≥ -x
           self.auxiliary_constraints.append(
               LXConstraint(f"{abs_name}_ge_neg_x")
               .expression(
                   LXLinearExpression()
                   .add_term(t, 1.0)
                   .add_term(var, 1.0)
               )
               .ge()
               .rhs(0)
           )

           # Step 3: Create auxiliary variable for t²
           # Use piecewise-linear approximation
           squared_name = f"aux_squared_{abs_name}_{self._aux_counter}"
           self._aux_counter += 1

           # Determine bounds for t²
           t_upper = None
           if var.upper_bound is not None and var.lower_bound is not None:
               t_upper = max(abs(var.lower_bound), abs(var.upper_bound))
               z_upper = t_upper ** 2
           else:
               z_upper = None

           z = (
               LXVariable[str, float](squared_name)
               .continuous()
               .bounds(lower=0, upper=z_upper)
               .indexed_by(lambda x: x)
               .from_data([squared_name])
           )
           self.auxiliary_vars.append(z)

           # Step 4: Add piecewise-linear constraints for z = t²
           # (This is simplified - in practice, use LXPiecewiseLinearizer)
           # For demonstration, we'll assume these are added elsewhere

           return z

**Step 2: Integrate into Main Engine**

.. code-block:: python

   # In lumix/linearization/engine.py

   from .techniques.abs_squared import LXAbsSquaredLinearizer

   class LXLinearizer:
       def __init__(self, model, solver_capability, config=None):
           # ... existing code ...
           self._abs_squared_linearizer = LXAbsSquaredLinearizer(self.config)

       def _linearize_expression(self, expr):
           # ... existing code ...

           # Handle absolute value squared terms
           elif isinstance(term, LXAbsSquaredTerm):
               aux_var = self._abs_squared_linearizer.linearize_abs_squared(
                   term.var,
                   term.coefficient
               )
               linear_expr = linear_expr + LXLinearExpression().add_term(
                   aux_var, 1.0
               )

       def linearize_model(self):
           # ... existing code ...

           # Collect auxiliary elements from abs_squared linearizer
           for aux_var in self._abs_squared_linearizer.auxiliary_vars:
               if aux_var not in self.auxiliary_vars:
                   linearized.add_variable(aux_var)
                   self.auxiliary_vars.append(aux_var)

           for aux_constraint in self._abs_squared_linearizer.auxiliary_constraints:
               if aux_constraint not in self.auxiliary_constraints:
                   linearized.add_constraint(aux_constraint)
                   self.auxiliary_constraints.append(aux_constraint)

           # ... existing code ...

**Step 3: Add Configuration Options**

.. code-block:: python

   # In lumix/linearization/config.py

   @dataclass
   class LXLinearizerConfig:
       # ... existing fields ...

       # Absolute value squared settings
       abs_squared_pwl_segments: int = 25  # For t² approximation
       abs_squared_use_mccormick: bool = False  # Alternative formulation

**Step 4: Add Tests**

.. code-block:: python

   # tests/linearization/test_abs_squared.py

   def test_abs_squared_linearization():
       """Test linearization of |x|² term."""
       config = LXLinearizerConfig(abs_squared_pwl_segments=30)
       linearizer = LXAbsSquaredLinearizer(config)

       # Create variable
       x = LXVariable[Model, float]("x").bounds(lower=-10, upper=10)

       # Linearize
       z = linearizer.linearize_abs_squared(x)

       # Verify
       assert z is not None
       assert len(linearizer.auxiliary_vars) >= 2  # t and z
       assert len(linearizer.auxiliary_constraints) >= 2  # |x| constraints

   def test_abs_squared_accuracy():
       """Test approximation accuracy."""
       import numpy as np

       config = LXLinearizerConfig(abs_squared_pwl_segments=50)
       linearizer = LXAbsSquaredLinearizer(config)

       x_test = np.linspace(-10, 10, 100)
       max_error = 0

       for x_val in x_test:
           true_value = abs(x_val) ** 2
           # Evaluate linearized approximation
           approx_value = evaluate_linearization(linearizer, x_val)
           error = abs(true_value - approx_value) / (true_value + 1e-10)
           max_error = max(max_error, error)

       assert max_error < 0.02, f"Error too large: {max_error}"

Adding Pre-built Functions
---------------------------

Example: Hyperbolic Tangent (tanh)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add to ``lumix/linearization/functions.py``:

.. code-block:: python

   class LXNonLinearFunctions:
       # ... existing methods ...

       @staticmethod
       def tanh(
           var: LXVariable,
           linearizer: LXPiecewiseLinearizer,
           segments: int = 40
       ) -> LXVariable:
           """
           Hyperbolic tangent function: tanh(x) = (e^x - e^(-x)) / (e^x + e^(-x))

           Use Cases:
               - Activation functions in neural networks
               - Saturation curves
               - Signal processing

           Args:
               var: Input variable
               linearizer: Piecewise linearizer instance
               segments: Number of segments (default: 40 for smooth approximation)

           Returns:
               Output variable representing tanh(var) ∈ [-1, 1]

           Example:
               >>> # Activation function
               >>> activation = LXNonLinearFunctions.tanh(
               ...     net_input,
               ...     linearizer,
               ...     segments=50
               ... )
           """
           return linearizer.approximate_function(
               lambda x: math.tanh(x),
               var,
               num_segments=segments,
               adaptive=True  # tanh curves sharply around x=0
           )

       @staticmethod
       def relu(
           var: LXVariable,
           linearizer: LXPiecewiseLinearizer,
           segments: int = 2  # ReLU is piecewise linear with 2 segments
       ) -> LXVariable:
           """
           Rectified Linear Unit: ReLU(x) = max(0, x)

           Use Cases:
               - Neural network activation
               - Non-negative constraints with smooth approximation

           Args:
               var: Input variable
               linearizer: Piecewise linearizer instance
               segments: Number of segments (default: 2, exact for ReLU)

           Returns:
               Output variable representing max(0, var)

           Example:
               >>> # Non-negative activation
               >>> output = LXNonLinearFunctions.relu(
               ...     weighted_sum,
               ...     linearizer
               ... )
           """
           def relu_func(x: float) -> float:
               return max(0, x)

           return linearizer.approximate_function(
               relu_func,
               var,
               num_segments=segments,
               adaptive=False  # ReLU is piecewise linear, uniform is fine
           )

Customizing Existing Techniques
--------------------------------

Example: Custom McCormick with Additional Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Extend the bilinear linearizer to add custom bound tightening:

.. code-block:: python

   from lumix.linearization.techniques.bilinear import LXBilinearLinearizer

   class LXTightMcCormickLinearizer(LXBilinearLinearizer):
       """
       Enhanced McCormick linearizer with additional bound tightening.
       """

       def _mccormick_envelope(self, x, y, coeff):
           """
           Override to add custom bound tightening before McCormick.
           """
           # Step 1: Apply custom bound tightening
           x_tight = self._tighten_bounds(x)
           y_tight = self._tighten_bounds(y)

           # Step 2: Call parent McCormick with tightened bounds
           z = super()._mccormick_envelope(x_tight, y_tight, coeff)

           # Step 3: Add custom strengthening constraints
           self._add_strengthening_constraints(z, x_tight, y_tight)

           return z

       def _tighten_bounds(self, var: LXVariable) -> LXVariable:
           """
           Custom bound tightening logic.

           Args:
               var: Variable to tighten

           Returns:
               Variable with tightened bounds
           """
           # Implement custom bound tightening
           # This could use constraint propagation, domain reduction, etc.
           ...

       def _add_strengthening_constraints(self, z, x, y):
           """
           Add custom constraints to strengthen McCormick relaxation.

           Args:
               z: Product variable
               x: First variable
               y: Second variable
           """
           # Add custom constraints
           # For example, additional cuts based on problem structure
           ...

Creating Custom Formulations
-----------------------------

Example: Custom PWL Formulation Using Convex Combination
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.linearization.techniques.piecewise import LXPiecewiseLinearizer

   class LXCustomPWLLinearizer(LXPiecewiseLinearizer):
       """
       Custom piecewise-linear linearizer with specialized formulation.
       """

       def _custom_convex_formulation(
           self,
           var: LXVariable,
           breakpoints: List[float],
           values: List[float]
       ) -> LXVariable:
           """
           Custom convex combination formulation.

           Similar to SOS2 but with additional constraints for specific
           problem structures.

           Args:
               var: Input variable
               breakpoints: Breakpoint x-coordinates
               values: Function values at breakpoints

           Returns:
               Output variable
           """
           n = len(breakpoints)

           # Lambda variables
           lambda_vars = []
           for i in range(n):
               lambda_name = f"lambda_custom_{var.name}_{i}"
               lambda_var = (
                   LXVariable[str, float](lambda_name)
                   .continuous()
                   .bounds(lower=0, upper=1)
                   .indexed_by(lambda x: x)
                   .from_data([lambda_name])
               )
               lambda_vars.append(lambda_var)
           self.auxiliary_vars.extend(lambda_vars)

           # Output variable
           output_name = f"pwl_custom_{var.name}_{self._aux_counter}"
           self._aux_counter += 1
           output = (
               LXVariable[str, float](output_name)
               .continuous()
               .bounds(lower=min(values), upper=max(values))
               .indexed_by(lambda x: x)
               .from_data([output_name])
           )
           self.auxiliary_vars.append(output)

           # Standard convexity constraint
           convex_expr = LXLinearExpression()
           for lv in lambda_vars:
               convex_expr.add_term(lv, 1.0)
           self.auxiliary_constraints.append(
               LXConstraint(f"custom_convex_{output_name}")
               .expression(convex_expr)
               .eq()
               .rhs(1.0)
           )

           # Custom adjacency constraints (instead of SOS2)
           # Force at most 2 adjacent lambdas to be positive
           for i in range(n - 2):
               # λ[i] + λ[i+1] + λ[i+2] ≤ 1 would be too restrictive
               # Instead, use binary variables to select active segment
               pass  # Implement custom logic

           # x and y definitions
           # ... similar to SOS2 formulation ...

           return output

       def approximate_function(self, func, var, **kwargs):
           """
           Override to use custom formulation.
           """
           # Generate breakpoints
           breakpoints = ...
           values = ...

           # Use custom formulation
           return self._custom_convex_formulation(var, breakpoints, values)

Testing Custom Extensions
--------------------------

Unit Tests
~~~~~~~~~~

.. code-block:: python

   import pytest
   from lumix.linearization.config import LXLinearizerConfig

   class TestCustomLinearizer:
       @pytest.fixture
       def linearizer(self):
           config = LXLinearizerConfig()
           return LXCustomLinearizer(config)

       def test_creation(self, linearizer):
           """Test linearizer can be created."""
           assert linearizer is not None
           assert linearizer.auxiliary_vars == []

       def test_linearize_custom_term(self, linearizer):
           """Test custom linearization."""
           x = LXVariable[Model, float]("x").bounds(0, 100)
           result = linearizer.linearize_custom_term(x)

           assert result is not None
           assert len(linearizer.auxiliary_vars) > 0

       def test_accuracy(self, linearizer):
           """Test approximation accuracy."""
           # Implement accuracy validation
           pass

Integration Tests
~~~~~~~~~~~~~~~~~

.. code-block:: python

   def test_custom_linearizer_in_model():
       """Test custom linearizer in full model."""
       # Build model
       model = build_test_model()

       # Configure with custom linearizer
       config = LXLinearizerConfig()
       # ... configure custom settings ...

       # Linearize
       linearizer = LXLinearizer(model, solver_cap, config)
       linearized = linearizer.linearize_model()

       # Verify
       assert linearized.name.endswith("_linearized")

       # Solve
       solution = optimizer.solve(linearized)
       assert solution.is_optimal()

Best Practices
--------------

1. **Follow Naming Conventions**

   .. code-block:: python

      # Good
      class LXYourFeatureLinearizer:
          def linearize_your_feature(self, term):
              aux_name = f"aux_your_feature_{var.name}_{self._aux_counter}"

      # Avoid
      class MyCustomThing:
          def do_it(self, x):
              temp = f"tmp_{x}"

2. **Maintain Auxiliary Element Lists**

   .. code-block:: python

      # Always append to auxiliary lists
      self.auxiliary_vars.append(new_var)
      self.auxiliary_constraints.append(new_constraint)

3. **Document Thoroughly**

   .. code-block:: python

      def linearize_custom(self, term):
          """
          Linearize custom term using XYZ method.

          Mathematical Formulation:
              Given: ...
              Creates: ...
              Constraints: ...

          Args:
              term: Custom term to linearize

          Returns:
              Auxiliary variable representing linearized term

          Example:
              >>> linearizer = LXCustomLinearizer(config)
              >>> z = linearizer.linearize_custom(term)
          """

4. **Handle Edge Cases**

   .. code-block:: python

      def linearize_term(self, term):
          # Validate inputs
          if term.var.lower_bound is None:
              raise ValueError("Variable must have lower bound")

          # Handle zero coefficient
          if abs(term.coefficient) < self.config.tolerance:
              return None  # Skip linearization

          # Continue with linearization
          ...

5. **Add Configuration Options**

   .. code-block:: python

      @dataclass
      class LXLinearizerConfig:
          # Add settings for your technique
          custom_method: str = "default"
          custom_precision: float = 1e-6
          custom_use_advanced: bool = True

Documentation
-------------

Document your extension in the appropriate places:

1. **Docstrings**: Add Google-style docstrings to all classes and methods
2. **User Guide**: Add usage examples to user guide
3. **API Reference**: Ensure autodoc picks up your classes
4. **Development Guide**: Document architecture and design decisions

Example Documentation Structure:

.. code-block:: rst

   Custom Linearization Technique
   ===============================

   Overview
   --------

   Description of your technique...

   Mathematical Background
   -----------------------

   Formulation details...

   Usage
   -----

   .. code-block:: python

      from lumix.linearization.techniques import LXCustomLinearizer

      linearizer = LXCustomLinearizer(config)
      result = linearizer.linearize_custom(term)

   See Also
   --------

   - :doc:`/api/linearization/index` - API reference

See Also
--------

- :doc:`linearization-architecture` - Architecture overview
- :doc:`design-decisions` - Design rationale
- :doc:`/user-guide/linearization/index` - User guide
- :doc:`/api/linearization/index` - API reference
