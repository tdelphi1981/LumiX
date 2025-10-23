Core Architecture
=================

Deep dive into the core module's architecture and design patterns.

Design Philosophy
-----------------

The core module implements a **data-driven, type-safe** approach to optimization modeling
using three key patterns:

1. **Builder Pattern**: Fluent API with method chaining
2. **Family Pattern**: Variables/constraints as families, not individuals
3. **Late Binding**: Expansion happens during solving, not construction

Architecture Overview
---------------------

.. mermaid::

   classDiagram
       class LXModel {
           +name: str
           +variables: List[LXVariable]
           +constraints: List[LXConstraint]
           +objective_expr: Expression
           +add_variable(var)
           +add_constraint(const)
           +maximize(expr)
           +minimize(expr)
       }

       class LXVariable {
           +name: str
           +var_type: LXVarType
           +bounds: tuple
           +_data: List
           +continuous()
           +integer()
           +binary()
           +from_data(data)
           +indexed_by(func)
       }

       class LXConstraint {
           +name: str
           +lhs: Expression
           +sense: ConstraintSense
           +rhs_value: float
           +expression(expr)
           +le() / ge() / eq()
           +rhs(value)
           +from_data(data)
       }

       class LXLinearExpression {
           +terms: Dict
           +constant: float
           +add_term(var, coeff)
           +add_constant(value)
       }

       LXModel --> LXVariable
       LXModel --> LXConstraint
       LXConstraint --> LXLinearExpression
       LXLinearExpression --> LXVariable

Component Details
-----------------

LXVariable: The Family Pattern
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Key Insight**: An ``LXVariable`` is NOT a single variable - it's a template that expands
to multiple solver variables.

**Implementation**:

.. code-block:: python

   @dataclass
   class LXVariable(Generic[TModel, TValue]):
       name: str
       var_type: LXVarType
       _data: Optional[List[TModel]] = None
       index_func: Optional[Callable[[TModel], TIndex]] = None

       def get_instances(self) -> List[TModel]:
           """Get data instances for expansion."""
           if self._data is not None:
               return self._data
           # ... ORM query logic ...

**Expansion** (happens in solver):

.. code-block:: python

   # User creates ONE LXVariable
   production = LXVariable[Product, float]("production").from_data(products)

   # Solver expands to MANY solver variables
   for instance in production.get_instances():
       index = production.index_func(instance)
       solver_var = solver.create_var(f"{production.name}[{index}]")

**Benefits**:

- No manual loops in user code
- Type-safe coefficients via lambdas
- Automatic indexing
- Late binding (solver-agnostic)

LXConstraint: Indexed Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Similar family pattern for constraints:

.. code-block:: python

   @dataclass
   class LXConstraint(Generic[TModel]):
       name: str
       lhs: Optional[LXLinearExpression] = None
       sense: LXConstraintSense = LXConstraintSense.LE
       rhs_func: Optional[Callable[[TModel], float]] = None
       _data: Optional[List[TModel]] = None

**Single vs. Family**:

.. code-block:: python

   # Single constraint (no indexing)
   total_budget = LXConstraint("budget").expression(...).le().rhs(1000)

   # Constraint family (indexed by Resource)
   capacity = (
       LXConstraint[Resource]("capacity")
       .expression(...)
       .le()
       .rhs(lambda r: r.capacity)  # Data-driven RHS
       .from_data(resources)
   )

LXExpression: Coefficient Functions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Expressions store coefficient *functions*, not values:

.. code-block:: python

   @dataclass
   class LXLinearExpression(Generic[TModel]):
       terms: Dict[str, Tuple[LXVariable, Callable, Callable]]
       constant: float = 0.0

       def add_term(self, var, coeff, where=None):
           coeff_func = coeff if callable(coeff) else lambda _: coeff
           self.terms[var.name] = (var, coeff_func, where)

**Evaluation** (happens in solver):

.. code-block:: python

   # User provides lambda
   expr.add_term(production, lambda p: p.profit)

   # Solver evaluates for each instance
   for instance in production.get_instances():
       coefficient = coeff_func(instance)  # p.profit evaluated here
       solver_expr.add_term(solver_var, coefficient)

**Multi-Model Terms**:

When a constraint references multiple variable families:

.. code-block:: python

   # Lambda receives instances from BOTH dimensions
   .add_term(production, lambda p, r: p.usage[r.id])
   # p: from production variable
   # r: from constraint indexing

Type System
-----------

Generics for Type Safety
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   TModel = TypeVar("TModel")  # Data model type
   TValue = TypeVar("TValue", int, float)  # Variable value type

   class LXVariable(Generic[TModel, TValue]):
       ...

   # Usage
   production = LXVariable[Product, float]("production")
   # TModel = Product
   # TValue = float

**Benefits**:

- IDE autocomplete in lambdas
- mypy type checking
- Self-documenting code

Fluent API Implementation
~~~~~~~~~~~~~~~~~~~~~~~~~

All methods return ``Self`` for chaining:

.. code-block:: python

   from typing_extensions import Self

   class LXVariable:
       def continuous(self) -> Self:
           self.var_type = LXVarType.CONTINUOUS
           return self

       def bounds(self, lower, upper) -> Self:
           self.lower_bound = lower
           self.upper_bound = upper
           return self

**Usage**:

.. code-block:: python

   production = (
       LXVariable[Product, float]("production")
       .continuous()     # Returns self
       .bounds(lower=0)  # Returns self
       .from_data(data)  # Returns self
   )

Data Flow
---------

Model Building Phase
~~~~~~~~~~~~~~~~~~~~

.. mermaid::

   sequenceDiagram
       participant User
       participant Variable
       participant Expression
       participant Model

       User->>Variable: from_data(products)
       Note over Variable: Stores data reference
       User->>Expression: add_term(var, lambda)
       Note over Expression: Stores lambda
       User->>Model: add_variable(var)
       Note over Model: Stores variable family
       User->>Model: add_constraint(expr)
       Note over Model: Stores constraint

**Key Point**: Nothing is expanded yet. We only store *templates*.

Solving Phase
~~~~~~~~~~~~~

.. mermaid::

   sequenceDiagram
       participant Solver
       participant Model
       participant Variable
       participant Expression

       Solver->>Model: solve(model)
       Model->>Variable: get_instances()
       Variable-->>Model: [product1, product2, ...]
       loop For each instance
           Solver->>Solver: Create solver variable
           Solver->>Expression: Evaluate lambda(instance)
           Expression-->>Solver: coefficient value
       end

**Key Point**: Expansion and evaluation happen here.

Extension Points
----------------

Custom Variable Types
~~~~~~~~~~~~~~~~~~~~~

Subclass ``LXVariable`` for specialized behavior:

.. code-block:: python

   class LXSemiContinuousVariable(LXVariable[TModel, float]):
       """Variable that is either 0 or in [L, U]."""

       def __init__(self, name: str):
           super().__init__(name)
           self.var_type = LXVarType.CONTINUOUS

       def semi_continuous(self, lower: float, upper: float) -> Self:
           # Implementation
           return self

Custom Expressions
~~~~~~~~~~~~~~~~~~

Subclass expression classes for new term types:

.. code-block:: python

   class LXConicExpression(LXLinearExpression):
       """Second-order cone expression."""

       def add_cone(self, vars: List[LXVariable]) -> Self:
           # Implementation
           return self

Performance Considerations
--------------------------

Late Binding Overhead
~~~~~~~~~~~~~~~~~~~~~

**Trade-off**: Late binding adds overhead but provides flexibility.

**Mitigation**:

- Lambda evaluation is cached where possible
- Data is stored as references, not copied
- Expansion happens once per solve

Memory Usage
~~~~~~~~~~~~

**Family Storage**:

- Storing families (metadata) is cheap
- Actual solver variables created only during solving
- Large models: Memory scales with data, not code

**Optimization**:

- Use filters (``where()``) to reduce expansion
- Index efficiently (simple keys better than complex tuples)

Testing Strategy
----------------

Unit Tests
~~~~~~~~~~

Test individual components:

.. code-block:: python

   def test_variable_continuous():
       var = LXVariable[Product, float]("x").continuous()
       assert var.var_type == LXVarType.CONTINUOUS

Integration Tests
~~~~~~~~~~~~~~~~~

Test end-to-end workflows:

.. code-block:: python

   def test_production_model():
       model = build_production_model(products)
       solution = optimizer.solve(model)
       assert solution.is_optimal()

Type Tests
~~~~~~~~~~

Use mypy for static type checking:

.. code-block:: bash

   mypy src/lumix/core

Next Steps
----------

- :doc:`extending-core` - How to add new features
- :doc:`design-decisions` - Why things work this way
- :doc:`/api/core/index` - Full API reference
