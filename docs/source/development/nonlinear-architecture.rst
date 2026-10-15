Nonlinear Module Architecture
==============================

Deep dive into the nonlinear module's architecture and design patterns.

Design Philosophy
-----------------

The nonlinear module follows a **declarative, type-safe** approach to nonlinear modeling:

1. **Separation of Concerns**: Term definitions are separate from linearization logic
2. **Dataclass Pattern**: All terms are plain (mutable) dataclasses
3. **Metadata Carriers**: Terms carry information about structure, not implementation
4. **Late Binding**: Linearization happens at solve time (``LXOptimizer`` with
   ``enable_linearization()``) or in an explicit ``LXLinearizer.linearize_model()``
   call, never at term creation

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
           +num_segments: Optional[int]
           +x_min: Optional[float]
           +x_max: Optional[float]
           +adaptive: Optional[bool]
           +method: Optional[Literal]
           +breakpoints: Optional[List[float]]
       }

       class LXCanonicalBuilder {
           +nonlinear(expr, where) List~LXCanonicalNonlinear~
       }

       class LXLinearizer {
           +linearize_model() LXModel
           +get_statistics() dict
           -_technique(item, refs, tag, sign)
           -_indicator(builder, term)
       }

       LXCanonicalBuilder --> LXAbsoluteTerm
       LXCanonicalBuilder --> LXMinMaxTerm
       LXCanonicalBuilder --> LXBilinearTerm
       LXCanonicalBuilder --> LXPiecewiseLinearTerm
       LXLinearizer --> LXCanonicalBuilder
       LXLinearizer --> LXIndicatorTerm

``LXCanonicalBuilder.nonlinear`` turns every term except indicators into
per-instance items ``LXCanonicalNonlinear(kind, variables, coeff, params, term,
key)``; the linearizer replaces each item by an auxiliary variable. Indicator terms
add rows and are handled by ``LXLinearizer._indicator`` directly.

Term Design Patterns
--------------------

Plain Dataclasses
~~~~~~~~~~~~~~~~~

All terms are plain ``@dataclass`` classes (not frozen):

.. code-block:: python

   from dataclasses import dataclass

   @dataclass
   class LXAbsoluteTerm:
       var: LXVariable
       coefficient: float = 1.0

**Consequences**:

- Terms are data, not behavior: they hold no linearization logic
- Fields can be changed after creation, so treat a term as owned by the
  expression it was added to; changing it changes the model
- Terms are not hashable; the linearizer identifies a term by its position in
  the expression (``LXCanonicalNonlinear.term``)

Metadata Carriers
~~~~~~~~~~~~~~~~~

Terms carry **what** to linearize, not **how**:

.. code-block:: python

   # User creates term (metadata)
   expr = LXNonLinearExpression().add_product(x, y)   # an LXBilinearTerm

   # At linearization, the "product" item goes to techniques.bilinear.product,
   # which picks the formulation from the variable types:
   #   binary  x binary   -> _and          (exact)
   #   binary  x bounded  -> _binary_times (exact)
   #   integer x any      -> _expansion    (exact, binary expansion)
   #   continuous x continuous -> _mccormick (relaxation, UserWarning)

Type Safety
~~~~~~~~~~~

Full type annotations for compile-time checking:

.. code-block:: python

   from typing import Callable, Literal, Optional

   @dataclass
   class LXPiecewiseLinearTerm:
       var: LXVariable
       func: Callable[[float], float]  # Function signature
       num_segments: Optional[int] = None
       x_min: Optional[float] = None
       x_max: Optional[float] = None
       adaptive: Optional[bool] = None
       method: Optional[Literal["sos2", "incremental", "logarithmic"]] = None
       breakpoints: Optional[List[float]] = None

Fields left at ``None`` are filled from ``LXLinearizerConfig``
(``pwl_num_segments``, ``adaptive_breakpoints``, ``pwl_method``) and from the
variable's bounds when the term is expanded. ``breakpoints=`` gives explicit,
strictly increasing breakpoints and replaces ``num_segments``, ``adaptive``,
``x_min`` and ``x_max``.

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
       Model->>Linearizer: solve() with enable_linearization(), or linearize_model()
       Linearizer->>Linearizer: Expand terms into per-instance items
       Linearizer->>Linearizer: _technique(item) picks the formulation
       Linearizer->>Model: Build a NEW model with auxiliary variables and rows
       Model->>Solver: Build solver-specific model

**Key Point**: Linearization is deferred until solve time (``LXOptimizer._solve_once``
when ``enable_linearization()`` is set) or an explicit ``linearize_model()`` call,
and it never modifies the user's model.

Linearization Methods
~~~~~~~~~~~~~~~~~~~~~

``LXLinearizer._technique`` dispatches on the item kind to a pure function in
``lumix/linearization/techniques/``. Each function creates variables and rows only
through ``LXAuxFactory.var`` / ``LXAuxFactory.row`` and returns an ``LXVarRef`` to
the variable that equals the item's value:

.. code-block:: python

   # lumix/linearization/engine.py (abridged)
   def _technique(self, item, refs, tag, sign):
       key = item.key
       if item.kind == "abs":
           return absolute(self._aux, tag, key, refs[0], convex=sign * item.coeff > 0)
       if item.kind in ("min", "max"):
           convex = sign < 0 if item.kind == "min" else sign > 0
           return minmax(self._aux, tag, key, item.kind, refs,
                         item.params["coefficients"], convex)
       if item.kind == "product":
           return product(self._aux, tag, key, refs[0], refs[1], self.config,
                          self.relaxation_terms)
       if item.kind == "piecewise":
           return piecewise(self._aux, tag, key, refs[0], item.params["breakpoints"],
                            item.params["values"], item.params["method"])
       raise ValueError(f"Unsupported nonlinear item: {item.kind}")

``sign`` is ``+1`` where the value is pushed down (minimized objective, ``<=``
row), ``-1`` where it is pushed up and ``0`` in equalities; where the cheap
epigraph form is exact (``convex``) no binaries are added. Items of kind ``abs``
and ``product`` with weight 0 are skipped.

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

3. **Add Linearization**: emit an ``LXCanonicalNonlinear`` item for the term in
   ``LXCanonicalBuilder.nonlinear`` (``lumix/core/canonical.py``). Reuse an
   existing kind when it fits (a function of one variable can be emitted as a
   ``"piecewise"`` item); for a new kind, add it to ``_TAG`` and add a branch in
   ``LXLinearizer._technique`` (``lumix/linearization/engine.py``) that calls a
   pure technique function. See :doc:`extending-linearization`.

4. **Add Tests**:

.. code-block:: python

   def test_quadratic_term():
       term = LXQuadraticTerm(var=x, a=2.0, b=1.0, c=0.5)
       assert term.a == 2.0

See :doc:`extending-nonlinear` for detailed guide.

Custom Linearization Methods
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``LXLinearizer`` has no per-term methods to override. A different formulation is
a change to (or a new) technique function and its branch in ``_technique``; see
:doc:`extending-linearization`.

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

Counts are per instance of the term (``n`` arguments of a min/max, ``k`` bits of
an integer factor, ``s`` piecewise segments). ``LXLinearizer.get_statistics()``
reports the totals of a run.

.. list-table::
   :header-rows: 1
   :widths: 30 20 20 30

   * - Term Type
     - Aux Vars
     - Constraints
     - Notes
   * - Absolute (convex use)
     - 1
     - 2
     - Minimized, or ``<=`` with positive weight
   * - Absolute (exact)
     - 2 (1 binary)
     - 4
     - Other uses; needs finite bounds
   * - Min/Max (convex use)
     - 1
     - n
     - Min pushed up / max pushed down
   * - Min/Max (exact)
     - 1 + n binaries
     - 2n + 1
     - Other uses; needs finite bounds
   * - Bilinear (Bin×Bin)
     - 1
     - 3
     - Exact (AND logic)
   * - Bilinear (Bin×bounded)
     - 1
     - 4
     - Exact; ``big_m_value`` only for open bounds (UserWarning)
   * - Bilinear (Int×any)
     - 2k + 1 (k binaries)
     - 4k + 2
     - Exact; k = bits of ``upper - lower``, at most ``binary_expansion_bits``
   * - Bilinear (Cont×Cont)
     - 1
     - 4
     - McCormick relaxation: UserWarning, ``solution.relaxation`` is True
   * - Indicator
     - 0
     - 1 (``<=``, ``>=``) / 2 (``==``)
     - Big-M from the expression bounds; ``big_m_value`` only when unbounded
   * - Piecewise (``sos2``)
     - 2s + 2 (s binaries)
     - s + 5
     - Weights with segment binaries, no native SOS2 (s >= 2; one segment needs no binaries)
   * - Piecewise (``incremental``)
     - 2s + 1 (s binaries)
     - s + 3
     - One binary and one fill variable per segment
   * - Piecewise (``logarithmic``)
     - P + 2 + log2(P)
     - 3 + 2 log2(P)
     - P = s rounded up to a power of two

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

   from lumix.linearization import LXLinearizerConfig
   from lumix.linearization.techniques import LXBilinearLinearizer

   def test_bilinear_linearization():
       x = LXVariable[str, float]("x").binary()
       y = LXVariable[str, float]("y").continuous().bounds(lower=0, upper=10)
       term = LXBilinearTerm(var1=x, var2=y)

       linearizer = LXBilinearLinearizer(LXLinearizerConfig())
       z = linearizer.linearize_bilinear(term)   # the product variable
       assert len(linearizer.auxiliary_constraints) == 4  # binary x bounded

For a whole model, use ``LXLinearizer(model, capability).linearize_model()`` and
check ``get_statistics()``.

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
2. Do not rely on terms being changed after they are added to an expression
3. Full type annotations
4. Document linearization method in docstring
5. Provide usage examples

Next Steps
----------

- :doc:`extending-nonlinear` - How to add new nonlinear terms
- :doc:`linearization-architecture` - Linearization engine design
- :doc:`design-decisions` - Overall design philosophy
