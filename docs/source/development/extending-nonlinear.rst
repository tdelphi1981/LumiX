Extending Nonlinear Module
==========================

Guide for adding custom nonlinear term types to LumiX.

Overview
--------

You can extend the nonlinear module by:

1. **Adding New Term Types**: Define new dataclasses for additional nonlinear operations
2. **Custom Linearization**: Implement linearization methods for your terms
3. **Integration**: Register terms with the linearization engine

Adding New Term Types
---------------------

Step-by-Step Guide
~~~~~~~~~~~~~~~~~~

Example: Adding Cubic Terms
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Let's add support for cubic terms (x³):

**Step 1**: Define the dataclass in `src/lumix/nonlinear/terms.py`:

.. code-block:: python

   @dataclass
   class LXCubicTerm:
       """Cubic term: coefficient * x³.

       Represents the cube of a variable, linearized using piecewise-linear
       approximation or auxiliary variables.

       Attributes:
           var: The variable to cube.
           coefficient: Coefficient to multiply the cubic term by (default: 1.0).

       Example:
           Cubic cost function::

               volume = LXVariable[Container, float]("volume").continuous().bounds(0, 10)
               cubic_cost = LXCubicTerm(var=volume, coefficient=2.5)
       """

       var: LXVariable
       coefficient: float = 1.0

**Step 2**: Export from `__init__.py`:

.. code-block:: python

   from .terms import (
       LXAbsoluteTerm,
       LXBilinearTerm,
       LXCubicTerm,  # Add new term
       LXIndicatorTerm,
       LXMinMaxTerm,
       LXPiecewiseLinearTerm,
   )

   __all__ = [
       "LXAbsoluteTerm",
       "LXBilinearTerm",
       "LXCubicTerm",  # Add to exports
       "LXIndicatorTerm",
       "LXMinMaxTerm",
       "LXPiecewiseLinearTerm",
   ]

**Step 3**: Add linearization in `src/lumix/linearization/engine.py`:

.. code-block:: python

   def linearize_cubic(self, term: LXCubicTerm) -> ...:
       """Linearize x³ using piecewise-linear approximation."""
       # Get variable bounds
       x_min = term.var.lower_bound or 0
       x_max = term.var.upper_bound or 1

       # Create piecewise-linear approximation
       def cubic_func(x):
           return term.coefficient * (x ** 3)

       # Use existing piecewise linearization
       piecewise_term = LXPiecewiseLinearTerm(
           var=term.var,
           func=cubic_func,
           num_segments=20,
           x_min=x_min,
           x_max=x_max,
           adaptive=True
       )

       return self.linearize_piecewise(piecewise_term)

**Step 4**: Add tests:

.. code-block:: python

   def test_cubic_term():
       var = LXVariable[Item, float]("x").continuous().bounds(0, 10)
       term = LXCubicTerm(var=var, coefficient=2.0)

       assert term.var == var
       assert term.coefficient == 2.0

   def test_cubic_linearization():
       var = LXVariable[Item, float]("x").continuous().bounds(0, 10)
       term = LXCubicTerm(var=var, coefficient=1.0)

       linearizer = LXLinearizer()
       result = linearizer.linearize_cubic(term)
       # Verify linearization constraints

More Examples
~~~~~~~~~~~~~

Logical AND Term
^^^^^^^^^^^^^^^^

.. code-block:: python

   @dataclass
   class LXAndTerm:
       """Logical AND of multiple binary variables.

       z = x₁ AND x₂ AND ... AND xₙ

       Attributes:
           vars: List of binary variables to AND together.
       """
       vars: List[LXVariable]

   # Linearization (in engine):
   def linearize_and(self, term: LXAndTerm):
       """z = 1 iff all vars = 1."""
       z = self._create_aux_var("and", var_type=BINARY)

       # z <= xᵢ for all i
       for var in term.vars:
           self._add_constraint(z <= var)

       # z >= sum(xᵢ) - n + 1
       self._add_constraint(z >= sum(term.vars) - len(term.vars) + 1)

       return z

Absolute Difference
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   @dataclass
   class LXAbsDifferenceTerm:
       """Absolute difference between two variables: |x - y|.

       Attributes:
           var1: First variable.
           var2: Second variable.
           coefficient: Coefficient (default: 1.0).
       """
       var1: LXVariable
       var2: LXVariable
       coefficient: float = 1.0

   # Linearization:
   def linearize_abs_difference(self, term: LXAbsDifferenceTerm):
       """Linearize |x - y|."""
       # Create auxiliary for difference
       diff = self._create_aux_var("diff")
       self._add_constraint(diff == term.var1 - term.var2)

       # Use absolute value linearization
       abs_term = LXAbsoluteTerm(var=diff, coefficient=term.coefficient)
       return self.linearize_absolute(abs_term)

Custom Linearization Methods
-----------------------------

Overriding Default Linearization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create custom linearizer subclass:

.. code-block:: python

   from lumix.linearization import LXLinearizer, LXLinearizerConfig
   from lumix.nonlinear import LXBilinearTerm

   class TightBoundsLinearizer(LXLinearizer):
       """Linearizer with improved bound computation."""

       def linearize_bilinear(self, term: LXBilinearTerm):
           """Custom McCormick with tighter bounds."""
           # Compute tighter bounds using problem structure
           tight_bounds = self._compute_tight_bounds(term)

           # Apply custom McCormick
           return self._mccormick_with_bounds(term, tight_bounds)

       def _compute_tight_bounds(self, term):
           # Custom logic to compute tighter bounds
           pass

Alternative Formulations
~~~~~~~~~~~~~~~~~~~~~~~~

Provide multiple linearization strategies:

.. code-block:: python

   class FlexibleLinearizer(LXLinearizer):
       def __init__(self, config: LXLinearizerConfig):
           super().__init__(config)
           self.bilinear_method = config.bilinear_method

       def linearize_bilinear(self, term: LXBilinearTerm):
           if self.bilinear_method == "mccormick":
               return self._mccormick(term)
           elif self.bilinear_method == "logarithmic":
               return self._logarithmic_formulation(term)
           else:
               return super().linearize_bilinear(term)

Integration with Model Builder
-------------------------------

Automatic Detection
~~~~~~~~~~~~~~~~~~~

Register term types for automatic linearization:

.. code-block:: python

   # In linearization engine
   TERM_HANDLERS = {
       LXAbsoluteTerm: linearize_absolute,
       LXBilinearTerm: linearize_bilinear,
       LXCubicTerm: linearize_cubic,  # New handler
       # ...
   }

   def linearize_term(self, term):
       """Dispatch to appropriate handler."""
       handler = TERM_HANDLERS.get(type(term))
       if handler is None:
           raise ValueError(f"No handler for {type(term)}")
       return handler(self, term)

Testing Custom Terms
--------------------

Unit Tests
~~~~~~~~~~

.. code-block:: python

   def test_custom_term_creation():
       var = LXVariable[Data, float]("x").continuous()
       term = LXCubicTerm(var=var, coefficient=2.0)
       assert isinstance(term, LXCubicTerm)
       assert term.coefficient == 2.0

Integration Tests
~~~~~~~~~~~~~~~~~

.. code-block:: python

   def test_custom_term_in_model():
       var = LXVariable[Data, float]("x").continuous().bounds(0, 10)
       term = LXCubicTerm(var=var)

       model = LXModel("test")
       model.add_variable(var)
       # Add term to objective or constraint

       linearizer = CustomLinearizer()
       linear_model = linearizer.linearize(model)

       # Verify linearization
       assert len(linear_model.constraints) > 0

Best Practices
--------------

Term Design
~~~~~~~~~~~

1. **Immutable dataclasses**: Use `@dataclass` with no methods
2. **Type annotations**: Full typing for all attributes
3. **Default values**: Provide sensible defaults where appropriate
4. **Documentation**: Comprehensive docstrings with examples

Linearization Implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Validate inputs**: Check variable bounds before linearization
2. **Efficient formulations**: Minimize auxiliary variables and constraints
3. **Numerical stability**: Avoid large M values
4. **Error handling**: Raise informative errors for invalid inputs

Example: Validation
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   def linearize_cubic(self, term: LXCubicTerm):
       """Linearize x³."""
       # Validate bounds
       if term.var.lower_bound is None or term.var.upper_bound is None:
           raise ValueError(
               f"Variable '{term.var.name}' must have finite bounds "
               f"for cubic linearization"
           )

       # Validate coefficient
       if term.coefficient == 0:
           raise ValueError("Coefficient cannot be zero")

       # Proceed with linearization
       ...

Documentation
~~~~~~~~~~~~~

Document your custom terms:

.. code-block:: python

   @dataclass
   class LXCustomTerm:
       """One-line summary.

       Detailed description of the term, including:
       - Mathematical formulation
       - Use cases
       - Linearization approach

       Attributes:
           var: Description of variable.
           param: Description of parameter.

       Example:
           Basic usage::

               var = LXVariable[Data, float]("x").continuous()
               term = LXCustomTerm(var=var, param=1.0)

       Note:
           Important notes about usage, requirements, or limitations.
       """
       var: LXVariable
       param: float = 1.0

Contributing to LumiX
---------------------

If you develop useful custom terms, consider contributing them to LumiX:

1. Fork the repository
2. Add your term following the guidelines above
3. Include comprehensive tests
4. Update documentation
5. Submit a pull request

See Also
--------

- :doc:`nonlinear-architecture` - Nonlinear module architecture
- :doc:`linearization-architecture` - Linearization engine architecture
- :doc:`extending-core` - Extending core components
