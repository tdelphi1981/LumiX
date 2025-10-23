Nonlinear Module Architecture
==============================

Deep dive into the nonlinear module's architecture and design patterns.

Design Philosophy
-----------------

The nonlinear module follows a **declarative, type-safe** approach to nonlinear modeling:

1. **Separation of Concerns**: Term definitions are separate from linearization logic
2. **Dataclass Pattern**: All terms are immutable dataclasses
3. **Metadata Carriers**: Terms carry information about structure, not implementation
4. **Late Binding**: Linearization happens during model building, not at term creation

Architecture Overview
---------------------

.. mermaid::

   classDiagram
       class LXAbsoluteTerm {
           +var: LXVariable
           +coefficient: float
       }

       class LXMinMaxTerm {
           +vars: List[LXVariable]
           +operation: Literal["min", "max"]
           +coefficients: List[float]
       }

       class LXBilinearTerm {
           +var1: LXVariable
           +var2: LXVariable
           +coefficient: float
       }

       class LXIndicatorTerm {
           +binary_var: LXVariable
           +condition: bool
           +linear_expr: LXLinearExpression
           +sense: Literal["<=", ">=", "=="]
           +rhs: float
       }

       class LXPiecewiseLinearTerm {
           +var: LXVariable
           +func: Callable
           +num_segments: int
           +x_min: Optional[float]
           +x_max: Optional[float]
           +adaptive: bool
           +method: Literal["sos2", "incremental", "logarithmic"]
       }

       class LXLinearizer {
           +linearize_absolute(term)
           +linearize_minmax(term)
           +linearize_bilinear(term)
           +linearize_indicator(term)
           +linearize_piecewise(term)
       }

       LXLinearizer --> LXAbsoluteTerm
       LXLinearizer --> LXMinMaxTerm
       LXLinearizer --> LXBilinearTerm
       LXLinearizer --> LXIndicatorTerm
       LXLinearizer --> LXPiecewiseLinearTerm

Term Design Patterns
--------------------

Immutable Dataclasses
~~~~~~~~~~~~~~~~~~~~~

All terms are frozen dataclasses:

.. code-block:: python

   from dataclasses import dataclass

   @dataclass
   class LXAbsoluteTerm:
       """Immutable representation of |x|."""
       var: LXVariable
       coefficient: float = 1.0

**Benefits**:

- Thread-safe
- Hashable (can be used in sets/dicts)
- Clear intent (terms are data, not behavior)
- Easy to serialize

Metadata Carriers
~~~~~~~~~~~~~~~~~

Terms carry **what** to linearize, not **how**:

.. code-block:: python

   # User creates term (metadata)
   bilinear = LXBilinearTerm(var1=x, var2=y, coefficient=1.0)

   # Linearizer decides how based on variable types
   if x.var_type == BINARY and y.var_type == BINARY:
       linearizer.use_and_logic(bilinear)
   elif x.var_type == BINARY and y.var_type == CONTINUOUS:
       linearizer.use_big_m(bilinear)
   else:
       linearizer.use_mccormick(bilinear)

Type Safety
~~~~~~~~~~~

Full type annotations for compile-time checking:

.. code-block:: python

   from typing import Callable, Literal, Optional

   @dataclass
   class LXPiecewiseLinearTerm:
       var: LXVariable
       func: Callable[[float], float]  # Function signature
       num_segments: int = 20
       method: Literal["sos2", "incremental", "logarithmic"] = "sos2"
       # Literal types enforce valid values

Integration with Linearization
-------------------------------

Linearization Workflow
~~~~~~~~~~~~~~~~~~~~~~

.. mermaid::

   sequenceDiagram
       participant User
       participant Term
       participant Model
       participant Linearizer
       participant Solver

       User->>Term: Create LXBilinearTerm(x, y)
       User->>Model: Add constraints with term
       Model->>Linearizer: linearize_model()
       Linearizer->>Term: Inspect variable types
       Linearizer->>Linearizer: Select linearization method
       Linearizer->>Model: Add auxiliary variables
       Linearizer->>Model: Add linearization constraints
       Model->>Solver: Build solver-specific model

**Key Point**: Linearization is deferred until model building.

Linearization Methods
~~~~~~~~~~~~~~~~~~~~~

Each term type has a dedicated linearization method:

.. code-block:: python

   class LXLinearizer:
       def linearize_absolute(self, term: LXAbsoluteTerm) -> ...:
           """Linearize |x| using auxiliary variable."""
           aux_var = self._create_aux_var(f"abs_{term.var.name}")
           self._add_constraint(aux_var >= term.var)
           self._add_constraint(aux_var >= -term.var)
           return aux_var

       def linearize_bilinear(self, term: LXBilinearTerm) -> ...:
           """Linearize x*y based on variable types."""
           if self._is_binary_times_binary(term):
               return self._linearize_binary_and(term)
           elif self._is_binary_times_continuous(term):
               return self._linearize_big_m(term)
           else:
               return self._linearize_mccormick(term)

Module Structure
----------------

File Organization
~~~~~~~~~~~~~~~~~

.. code-block:: text

   src/lumix/nonlinear/
   ├── __init__.py      # Module exports and documentation
   └── terms.py         # All term dataclass definitions

**Design Decision**: Single `terms.py` file keeps related definitions together.

Dependencies
~~~~~~~~~~~~

.. mermaid::

   graph TD
       A[nonlinear] --> B[core.variables]
       A --> C[core.expressions]
       D[linearization] --> A
       E[solvers] --> D

       style A fill:#e1f5ff
       style D fill:#fff4e1

**Dependency Direction**:

- Nonlinear module depends only on core (variables, expressions)
- Linearization module depends on nonlinear (consumes terms)
- Solvers depend on linearization (receives linearized models)

This ensures clean separation of concerns.

Extension Points
----------------

Adding New Term Types
~~~~~~~~~~~~~~~~~~~~~

To add a new nonlinear term:

1. **Define Dataclass** in `terms.py`:

.. code-block:: python

   @dataclass
   class LXQuadraticTerm:
       """Quadratic term: a*x^2 + b*x + c."""
       var: LXVariable
       a: float
       b: float = 0.0
       c: float = 0.0

2. **Export** from `__init__.py`:

.. code-block:: python

   from .terms import LXQuadraticTerm

   __all__ = [..., "LXQuadraticTerm"]

3. **Add Linearization** in `lumix/linearization/engine.py`:

.. code-block:: python

   def linearize_quadratic(self, term: LXQuadraticTerm):
       # Linearization logic here
       pass

4. **Add Tests**:

.. code-block:: python

   def test_quadratic_term():
       term = LXQuadraticTerm(var=x, a=2.0, b=1.0, c=0.5)
       assert term.a == 2.0

See :doc:`extending-nonlinear` for detailed guide.

Custom Linearization Methods
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Subclass `LXLinearizer` to customize linearization:

.. code-block:: python

   from lumix.linearization import LXLinearizer

   class CustomLinearizer(LXLinearizer):
       def linearize_bilinear(self, term: LXBilinearTerm):
           # Use custom McCormick with tighter bounds
           return self._custom_mccormick(term)

Performance Considerations
--------------------------

Memory Footprint
~~~~~~~~~~~~~~~~

Terms are lightweight dataclasses:

.. code-block:: python

   import sys

   term = LXAbsoluteTerm(var=x, coefficient=1.0)
   print(sys.getsizeof(term))  # ~64 bytes

**Implication**: Creating thousands of terms is cheap.

Linearization Cost
~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 20 20 30

   * - Term Type
     - Aux Vars
     - Constraints
     - Notes
   * - Absolute
     - 1
     - 2
     - Very efficient
   * - Min/Max
     - 1
     - n (inputs)
     - Scales with inputs
   * - Bilinear (Bin×Bin)
     - 1
     - 3
     - Exact, efficient
   * - Bilinear (Bin×Cont)
     - 1
     - 4
     - Exact, Big-M
   * - Bilinear (Cont×Cont)
     - 1
     - 4
     - Relaxation
   * - Indicator
     - 0
     - 1
     - Big-M
   * - Piecewise (SOS2)
     - n+1
     - n
     - Best with SOS2 support

Testing Strategy
----------------

Unit Tests
~~~~~~~~~~

Test term creation and properties:

.. code-block:: python

   def test_absolute_term_creation():
       var = LXVariable[Product, float]("x").continuous()
       term = LXAbsoluteTerm(var=var, coefficient=2.0)
       assert term.coefficient == 2.0
       assert term.var == var

Integration Tests
~~~~~~~~~~~~~~~~~

Test with linearization engine:

.. code-block:: python

   def test_bilinear_linearization():
       x = LXVariable("x").binary()
       y = LXVariable("y").continuous().bounds(0, 10)
       term = LXBilinearTerm(var1=x, var2=y)

       linearizer = LXLinearizer()
       result = linearizer.linearize_bilinear(term)
       assert len(result.constraints) == 4  # Big-M

Type Tests
~~~~~~~~~~

Use mypy for type checking:

.. code-block:: bash

   mypy src/lumix/nonlinear

Future Directions
-----------------

Planned Extensions
~~~~~~~~~~~~~~~~~~

- **Higher-order terms**: Cubic, polynomial
- **Multi-variate terms**: f(x, y, z) with multiple inputs
- **Logical terms**: AND, OR, NOT combinations
- **Cardinality constraints**: AtMost, AtLeast, Exactly

Design Considerations
~~~~~~~~~~~~~~~~~~~~~

For new terms:

1. Keep terms as pure data (no methods beyond dataclass)
2. Maintain immutability
3. Full type annotations
4. Document linearization method in docstring
5. Provide usage examples

Next Steps
----------

- :doc:`extending-nonlinear` - How to add new nonlinear terms
- :doc:`linearization-architecture` - Linearization engine design
- :doc:`design-decisions` - Overall design philosophy
