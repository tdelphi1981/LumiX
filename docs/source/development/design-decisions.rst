Design Decisions
================

Understanding the "why" behind LumiX's design.

Variable Families vs. Individual Variables
-------------------------------------------

**Decision**: Variables are families that expand automatically.

Traditional Approach
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Manual loops, error-prone
   x = {}
   for i, product in enumerate(products):
       x[i] = model.addVar(name=f"x_{i}")

LumiX Approach
~~~~~~~~~~~~~~

.. code-block:: python

   # Declarative, type-safe
   production = LXVariable[Product, float]("production").from_data(products)

**Rationale**:

1. **Elimination of Manual Loops**: Reduces boilerplate and bugs
2. **Type Safety**: Lambda parameters are typed (IDE autocomplete)
3. **Data-Driven**: Variables naturally map to business entities
4. **Solver Agnostic**: Expansion logic separated from declaration
5. **Maintainability**: Changes to data structure don't require code changes

**Trade-offs**:

- ✗ Slightly more memory for storing families
- ✗ Learning curve for family concept
- ✓ Far fewer bugs from manual indexing
- ✓ Much more readable code
- ✓ Better IDE support

Late Binding (Lazy Expansion)
------------------------------

**Decision**: Variables/constraints expand during solving, not construction.

Why Late Binding?
~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Construction phase - only stores template
   production = LXVariable[Product, float]("production").from_data(products)

   # Solving phase - expands to solver variables
   solution = optimizer.solve(model)

**Rationale**:

1. **Solver Independence**: Same model works with any solver
2. **Flexibility**: Can modify data before solving
3. **Memory Efficiency**: Don't create solver vars until needed
4. **Testing**: Can validate model structure without solver

**Trade-offs**:

- ✗ Can't inspect solver variables before solving
- ✓ Models are portable across solvers
- ✓ Can validate logic without solver
- ✓ Reduced memory footprint

Lambda Functions for Coefficients
----------------------------------

**Decision**: Coefficients are lambdas, not values.

Example
~~~~~~~

.. code-block:: python

   # Lambda evaluated for each product
   expr.add_term(production, lambda p: p.unit_cost * p.tax_rate)

**Rationale**:

1. **Type Safety**: IDE knows `p` is a `Product`
2. **Expressiveness**: Complex calculations inline
3. **Data-Driven**: Coefficients come from data
4. **Lazy Evaluation**: Computed only when needed

**Alternatives Considered**:

Dictionary Approach
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Rejected: Verbose, error-prone
   coeffs = {p.id: p.unit_cost * p.tax_rate for p in products}
   expr.add_term(production, coeffs)

**Why lambdas won**:

- ✓ Type-safe (mypy checks lambda body)
- ✓ Concise (one line vs. two)
- ✓ Fewer opportunities for index mismatches

Method Chaining (Fluent API)
-----------------------------

**Decision**: All core classes use fluent API.

Example
~~~~~~~

.. code-block:: python

   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .bounds(lower=0)
       .from_data(products)
   )

**Rationale**:

1. **Readability**: Reads like a sentence
2. **Discoverability**: IDE suggests next methods
3. **Immutability-Like**: Each method returns modified self
4. **Consistency**: Same pattern across all classes

**Alternatives Considered**:

Named Arguments
^^^^^^^^^^^^^^^

.. code-block:: python

   # Rejected: Less discoverable
   production = LXVariable(
       name="production",
       var_type=VarType.CONTINUOUS,
       lower_bound=0,
       data=products
   )

**Why fluent API won**:

- ✓ Better IDE support (suggests next method)
- ✓ More flexible (methods can have complex logic)
- ✓ Easier to extend (add new methods)

Generic Type Parameters
-----------------------

**Decision**: Extensive use of Generic[TModel, TValue].

Example
~~~~~~~

.. code-block:: python

   production = LXVariable[Product, float]("production")
   # TModel = Product, TValue = float

**Rationale**:

1. **IDE Autocomplete**: In lambdas, IDE knows types
2. **Static Typing**: mypy catches errors
3. **Self-Documenting**: Types explicit in code
4. **Refactoring**: Safer to rename attributes

**Trade-offs**:

- ✗ More verbose type annotations
- ✗ Generic syntax can be intimidating
- ✓ Catches errors at development time
- ✓ Makes code self-documenting
- ✓ Excellent IDE experience

Data-Driven vs. Imperative
---------------------------

**Decision**: Prefer data-driven declarative style.

Data-Driven (LumiX)
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Declare what you want
   production = LXVariable[Product, float]("production").from_data(products)

   capacity = LXConstraint[Resource]("capacity")\\
       .expression(...)\\
       .le()\\
       .rhs(lambda r: r.capacity)\\
       .from_data(resources)

Imperative (Traditional)
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Describe how to build it
   x = {}
   for i, product in enumerate(products):
       x[i] = model.addVar()

   for j, resource in enumerate(resources):
       model.addConstr(
           sum(x[i] * usage[i][j] for i in range(len(products)))
           <= resource.capacity
       )

**Rationale**:

1. **Clarity**: What vs. How
2. **Maintainability**: Less code to break
3. **Testability**: Easier to unit test
4. **Separation**: Model logic separate from data

Single Module Import
--------------------

**Decision**: Import everything from top-level `lumix`.

Example
~~~~~~~

.. code-block:: python

   from lumix import (
       LXModel,
       LXVariable,
       LXConstraint,
       LXLinearExpression,
   )

**Rationale**:

1. **Simplicity**: One import location
2. **Discoverability**: IDE shows all available items
3. **Stability**: Can reorganize internals without breaking imports

**Implementation**:

All public classes exported via `__init__.py`:

.. code-block:: python

   # src/lumix/__init__.py
   from .core import LXModel, LXVariable, LXConstraint
   from .solvers import LXOptimizer
   # ...

Solver Abstraction
------------------

**Decision**: Unified interface across all solvers.

Interface
~~~~~~~~~

.. code-block:: python

   class LXSolverInterface:
       def create_model(self, lx_model: LXModel) -> Any:
           """Create solver-specific model."""

       def solve(self) -> LXSolution:
           """Solve and return solution."""

**Rationale**:

1. **Portability**: Switch solvers with one line
2. **Testing**: Test with free solver, deploy with commercial
3. **Comparison**: Easy to benchmark different solvers
4. **Future-Proof**: Add new solvers without changing user code

**Trade-offs**:

- ✗ Can't use solver-specific features directly
- ✗ Interface must support lowest common denominator
- ✓ Models are portable
- ✓ Easy to add new solvers
- ✓ Users not locked to one solver

Automatic Linearization
------------------------

**Decision**: Provide automatic linearization for non-linear terms.

Example
~~~~~~~

.. code-block:: python

   # User writes non-linear
   expr = LXNonLinearExpression()
   expr.add_product(x, y)  # Bilinear

   # LumiX linearizes automatically
   linearized = linearizer.linearize(expr)

**Rationale**:

1. **Accessibility**: Use free solvers for non-linear problems
2. **Transparency**: Users don't need to know linearization techniques
3. **Correctness**: Implemented once, tested thoroughly
4. **Performance**: Optimized implementations

**Alternatives**:

Manual linearization
^^^^^^^^^^^^^^^^^^^^

Rejected because:

- ✗ Error-prone (McCormick envelopes are tricky)
- ✗ Verbose (many auxiliary variables and constraints)
- ✗ Non-portable (different techniques for different terms)

Performance Considerations
---------------------------

Late Binding Overhead
~~~~~~~~~~~~~~~~~~~~~

**Concern**: Storing lambdas and evaluating them has overhead.

**Analysis**:

- Lambda evaluation: ~10-100 ns
- Model building time: Usually <1% of solve time
- Large models (10,000+ variables): Overhead ~10-50ms

**Decision**: Trade-off acceptable because:

- Solve time dominates (seconds to hours)
- User productivity gain is huge
- Can optimize hot paths if needed

Memory Usage
~~~~~~~~~~~~

**Concern**: Storing families uses more memory than direct arrays.

**Analysis**:

- Family metadata: ~500 bytes per family
- Typical model: 5-20 families
- Overhead: <10 KB

**Decision**: Negligible compared to:

- Solver memory (MB to GB)
- Data storage (typically larger)

Future Directions
-----------------

Planned Improvements
~~~~~~~~~~~~~~~~~~~~

1. **Compile-time validation**: Detect errors before running
2. **JIT compilation**: Compile lambdas for performance
3. **Incremental solving**: Modify and re-solve efficiently
4. **Parallel expansion**: Multi-threaded variable creation
5. **Symbolic differentiation**: Auto-compute gradients

Research Questions
~~~~~~~~~~~~~~~~~~

1. Can we infer index structure from data relationships?
2. How to best support streaming/online optimization?
3. What's the right abstraction for stochastic programming?

Summary
-------

LumiX's design prioritizes:

1. **User Experience**: Type safety, IDE support, readability
2. **Maintainability**: Less code, fewer bugs, easier refactoring
3. **Portability**: Solver-agnostic models
4. **Correctness**: Tested implementations of complex techniques

The trade-offs (slight overhead, learning curve) are worth it for the
dramatic improvement in development experience and code quality.

Next Steps
----------

- :doc:`core-architecture` - See how it's implemented
- :doc:`extending-core` - Build on these principles
- :doc:`/user-guide/core/index` - Use the features
