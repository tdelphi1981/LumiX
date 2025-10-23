Extending Core Components
=========================

Guide for extending LumiX's core functionality.

Adding New Variable Types
--------------------------

Semi-Continuous Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~

Variables that are either 0 or within [L, U]:

.. code-block:: python

   from lumix.core import LXVariable, LXVarType
   from typing_extensions import Self

   class LXSemiContinuousVariable(LXVariable[TModel, float]):
       """Variable that is 0 or in [lower, upper]."""

       def semi_continuous(self, lower: float, upper: float) -> Self:
           """Set as semi-continuous variable."""
           self.var_type = LXVarType.CONTINUOUS
           self.lower_bound = lower
           self.upper_bound = upper
           # Mark for special handling in solver
           self._is_semi_continuous = True
           return self

Special Ordered Sets
~~~~~~~~~~~~~~~~~~~~

SOS1 or SOS2 variables:

.. code-block:: python

   class LXSOSVariable(LXVariable[TModel, float]):
       """Special Ordered Set variable."""

       def sos1(self) -> Self:
           """Mark as SOS1 (at most one non-zero)."""
           self._sos_type = "SOS1"
           return self

       def sos2(self) -> Self:
           """Mark as SOS2 (at most two non-zero, adjacent)."""
           self._sos_type = "SOS2"
           return self

Adding New Expression Types
----------------------------

Conic Expressions
~~~~~~~~~~~~~~~~~

For second-order cone programming:

.. code-block:: python

   from lumix.core.expressions import LXLinearExpression
   from dataclasses import dataclass, field

   @dataclass
   class LXConicExpression:
       """Second-order cone expression: ||Ax + b|| <= c^T x + d"""

       A_matrix: List[List[float]] = field(default_factory=list)
       b_vector: List[float] = field(default_factory=list)
       c_vector: List[float] = field(default_factory=list)
       d_scalar: float = 0.0

       def add_to_cone(self, var: LXVariable, coeff: float) -> Self:
           """Add variable to cone constraint."""
           # Implementation
           return self

Custom Objective Types
~~~~~~~~~~~~~~~~~~~~~~

For specialized objectives:

.. code-block:: python

   @dataclass
   class LXRobustExpression:
       """Robust optimization expression."""

       nominal: LXLinearExpression
       uncertainty_set: Dict[str, Tuple[float, float]]

       def add_robust_term(self, var: LXVariable, nominal: float,
                           uncertainty: float) -> Self:
           """Add term with uncertainty."""
           return self

Adding New Constraint Types
----------------------------

Indicator Constraints
~~~~~~~~~~~~~~~~~~~~~

Conditional constraints:

.. code-block:: python

   from lumix.core.constraints import LXConstraint

   class LXIndicatorConstraint(LXConstraint[TModel]):
       """If binary_var == 1, then linear_expr <= rhs."""

       def __init__(self, name: str):
           super().__init__(name)
           self.binary_var: Optional[LXVariable] = None
           self.indicator_value: int = 1

       def indicator(self, var: LXVariable, value: int = 1) -> Self:
           """Set indicator variable and value."""
           self.binary_var = var
           self.indicator_value = value
           return self

Complementarity Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For equilibrium problems:

.. code-block:: python

   class LXComplementarityConstraint(LXConstraint[TModel]):
       """Complementarity: x >= 0, y >= 0, x * y = 0"""

       def complementary_to(self, other_var: LXVariable) -> Self:
           """Set complementary variable."""
           self._complementary_var = other_var
           return self

Extending the Model
-------------------

Adding Model Metadata
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.core.model import LXModel

   class LXModelWithMetadata(LXModel[TModel]):
       """Model with additional metadata."""

       def __init__(self, name: str):
           super().__init__(name)
           self.description: str = ""
           self.author: str = ""
           self.created_at: datetime = datetime.now()

       def set_description(self, desc: str) -> Self:
           """Set model description."""
           self.description = desc
           return self

Model Validation
~~~~~~~~~~~~~~~~

.. code-block:: python

   class LXValidatedModel(LXModel[TModel]):
       """Model with validation."""

       def validate(self) -> List[str]:
           """Validate model and return errors."""
           errors = []

           if not self.variables:
               errors.append("Model has no variables")

           if not self.constraints:
               errors.append("Model has no constraints")

           if self.objective_expr is None:
               errors.append("Model has no objective")

           return errors

       def validate_or_raise(self):
           """Validate and raise if errors."""
           errors = self.validate()
           if errors:
               raise ValueError(f"Invalid model: {errors}")

Creating Custom Indexing
-------------------------

Custom Index Dimensions
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.indexing import LXIndexDimension

   class LXTimeIndexDimension(LXIndexDimension[TModel]):
       """Time-based indexing with periods."""

       def __init__(self, model: Type[TModel], key_func: Callable):
           super().__init__(model, key_func)
           self.time_periods: List[int] = []

       def for_periods(self, periods: List[int]) -> Self:
           """Restrict to specific time periods."""
           self.time_periods = periods
           return self

Sparse Indexing
~~~~~~~~~~~~~~~

For efficient sparse variable creation:

.. code-block:: python

   class LXSparseCartesianProduct:
       """Cartesian product with sparsity pattern."""

       def __init__(self, *dimensions):
           self.dimensions = dimensions
           self.sparsity_matrix: Optional[np.ndarray] = None

       def set_sparsity(self, matrix: np.ndarray) -> Self:
           """Set sparsity pattern (1 = create, 0 = skip)."""
           self.sparsity_matrix = matrix
           return self

Testing Extensions
------------------

Unit Tests
~~~~~~~~~~

.. code-block:: python

   import pytest
   from lumix.core import LXModel

   def test_custom_variable_type():
       var = LXSemiContinuousVariable[Product, float]("x")
       var.semi_continuous(lower=10, upper=100)

       assert var.lower_bound == 10
       assert var.upper_bound == 100
       assert var._is_semi_continuous

Integration Tests
~~~~~~~~~~~~~~~~~

.. code-block:: python

   def test_custom_expression_in_model():
       model = LXModel("test")
       conic_expr = LXConicExpression()

       # Build and solve
       model.add_constraint(...)
       solution = optimizer.solve(model)

       assert solution.is_optimal()

Type Checking
~~~~~~~~~~~~~

Ensure extensions maintain type safety:

.. code-block:: python

   # Your extension should pass mypy
   var: LXSemiContinuousVariable[Product, float] = \\
       LXSemiContinuousVariable("x")

Documentation
-------------

Docstring Template
~~~~~~~~~~~~~~~~~~

Use Google-style docstrings:

.. code-block:: python

   class LXCustomVariable(LXVariable[TModel, TValue]):
       """One-line summary.

       Longer description explaining the variable type,
       when to use it, and any special considerations.

       Args:
           name: Variable name

       Examples:
           Basic usage::

               custom_var = (
                   LXCustomVariable[Product, float]("var")
                   .custom_method()
                   .from_data(products)
               )

       Note:
           Any important notes or warnings.

       See Also:
           - :class:`~lumix.core.variables.LXVariable`
           - Related documentation
       """

Adding to Documentation
~~~~~~~~~~~~~~~~~~~~~~~

1. Add autodoc to ``docs/source/api/``
2. Add usage examples to ``docs/source/user-guide/``
3. Update main index files

Contributing Guidelines
-----------------------

Code Style
~~~~~~~~~~

Follow existing patterns:

- Use Google-style docstrings
- Type all function signatures
- Use fluent API (return ``Self``)
- Name consistently (``LX`` prefix for core classes)

Testing Requirements
~~~~~~~~~~~~~~~~~~~~

All extensions must have:

- Unit tests (>90% coverage)
- Integration tests
- Type annotations
- Docstrings

Pull Request Process
~~~~~~~~~~~~~~~~~~~~~

1. Fork the repository
2. Create feature branch
3. Add tests and documentation
4. Run full test suite
5. Submit PR with description

Next Steps
----------

- :doc:`design-decisions` - Understand the rationale
- :doc:`core-architecture` - Deep dive into architecture
- :doc:`/api/core/index` - Full API reference
