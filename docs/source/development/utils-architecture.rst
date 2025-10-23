Utils Module Architecture
=========================

Deep dive into the utils module's architecture, design patterns, and implementation details.

Design Philosophy
-----------------

The utils module follows these key principles:

1. **Optional Enhancement**: All utils are optional - core LumiX works without them
2. **Structural Typing**: Use Protocol (PEP 544) instead of inheritance
3. **Type Safety**: Full type hints for IDE support and mypy checking
4. **Single Responsibility**: Each component has one clear purpose
5. **Minimal Dependencies**: Avoid external dependencies where possible

Module Overview
---------------

The utils module consists of three independent components:

.. mermaid::

   graph TD
       A[utils Module] --> B[logger.py]
       A --> C[orm.py]
       A --> D[rational.py]

       B --> E[LXModelLogger]
       C --> F[LXORMModel]
       C --> G[LXORMContext]
       C --> H[LXTypedQuery]
       C --> I[LXNumeric]
       D --> J[LXRationalConverter]

       style A fill:#e1f5ff
       style B fill:#fff4e1
       style C fill:#ffe1e1
       style D fill:#e1ffe1

Component Architecture
----------------------

Logger (logger.py)
~~~~~~~~~~~~~~~~~~

**Design Pattern**: Wrapper around Python's logging module

**Key Design Decisions:**

1. **Composition over Inheritance**: Wraps ``logging.Logger`` instead of inheriting
2. **Domain-Specific Methods**: Specialized methods for optimization events
3. **Automatic Timing**: Built-in timestamp tracking for solve operations

**Implementation:**

.. code-block:: python

   class LXModelLogger:
       """Wraps Python logger with optimization-specific methods."""

       def __init__(self, name: str = "lumix", level: int = logging.INFO):
           self.logger = logging.getLogger(name)  # Composition
           self.start_time: Optional[datetime] = None

       def log_solve_start(self, solver_name: str) -> None:
           self.start_time = datetime.now()  # Auto timing
           self.logger.info(f"Starting solve with {solver_name}...")

**Benefits:**

- Delegates to standard logging for core functionality
- Easy to test - just check log output
- No breaking changes when Python logging evolves

ORM Integration (orm.py)
~~~~~~~~~~~~~~~~~~~~~~~~~

**Design Pattern**: Structural typing with Protocol

**Key Design Decisions:**

1. **Protocol over ABC**: Use runtime-checkable Protocol for structural typing
2. **Generic Types**: Full generic support for type safety
3. **ORM Agnostic**: Works with any ORM via duck typing

**Implementation:**

.. code-block:: python

   @runtime_checkable
   class LXORMModel(Protocol):
       """Structural protocol - no inheritance needed."""
       id: Any

       def __getattribute__(self, name: str) -> Any:
           ...

   class LXORMContext(Generic[TModel]):
       """Generic context for type-safe queries."""

       def __init__(self, session: Any):
           self.session = session  # Works with any ORM session

       def query(self, model: Type[TModel]) -> "LXTypedQuery[TModel]":
           return LXTypedQuery(self.session, model)

**Type Flow:**

.. mermaid::

   sequenceDiagram
       participant User
       participant Context
       participant TypedQuery
       participant ORM

       User->>Context: query(Product)
       Context->>TypedQuery: LXTypedQuery[Product]
       User->>TypedQuery: filter(lambda p: ...)
       Note over User: IDE knows p is Product
       TypedQuery->>ORM: session.query(Product).all()
       ORM-->>TypedQuery: List[Product]
       TypedQuery-->>User: List[Product]

**Benefits:**

- No inheritance - works with existing ORM models
- Full IDE autocomplete in lambdas
- Runtime type checking via isinstance()

Rational Conversion (rational.py)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Design Pattern**: Strategy pattern for algorithms

**Key Design Decisions:**

1. **Multiple Algorithms**: Support three different approximation methods
2. **Configurable Precision**: User controls max denominator
3. **Immutable Configuration**: Converter settings don't change after init
4. **Self-Contained**: No external dependencies (uses only stdlib)

**Implementation:**

.. code-block:: python

   class LXRationalConverter:
       """Immutable converter with configurable algorithm."""

       def __init__(
           self,
           max_denominator: int = 10000,
           method: Literal["farey", "continued_fraction", "stern_brocot"] = "farey",
           float_tolerance: float = 1e-9,
       ):
           self.max_denominator = max_denominator
           self.method = method
           self.float_tolerance = float_tolerance

       def to_rational(self, value: float, ...) -> Fraction:
           # Strategy pattern - dispatch to appropriate method
           if self.method == "farey":
               num, den, error = self._farey_approximation(value)
           elif self.method == "continued_fraction":
               num, den, error = self._continued_fraction_approximation(value)
           elif self.method == "stern_brocot":
               num, den, error = self._stern_brocot_approximation(value)

**Algorithm Architecture:**

.. mermaid::

   graph LR
       A[to_rational] --> B{method?}
       B -->|farey| C[_farey_approximation]
       B -->|continued_fraction| D[_continued_fraction_approximation]
       B -->|stern_brocot| E[_stern_brocot_approximation]
       C --> F[Return Fraction]
       D --> F
       E --> F

**Benefits:**

- Easy to add new algorithms
- No runtime dependencies
- Testable algorithms in isolation

Type System Design
------------------

Protocol Usage
~~~~~~~~~~~~~~

Protocols enable structural typing without inheritance:

.. code-block:: python

   from typing import Protocol, runtime_checkable

   @runtime_checkable
   class LXORMModel(Protocol):
       id: Any

   # Any class with 'id' automatically satisfies protocol
   class Product:
       id: int = 1

   assert isinstance(Product(), LXORMModel)  # True!

**Advantages:**

- Works with existing code (no refactoring)
- Runtime type checking
- Gradual typing - can adopt incrementally

Generic Types
~~~~~~~~~~~~~

Full generic support for type safety:

.. code-block:: python

   from typing import Generic, TypeVar

   TModel = TypeVar("TModel")

   class LXORMContext(Generic[TModel]):
       def query(self, model: Type[TModel]) -> "LXTypedQuery[TModel]":
           ...

**Type Propagation:**

.. code-block:: python

   ctx = LXORMContext(session)
   query: LXTypedQuery[Product] = ctx.query(Product)
   products: List[Product] = query.all()  # Type propagates!

**Benefits:**

- IDE autocomplete
- mypy type checking
- Self-documenting code

Performance Considerations
--------------------------

Logger Performance
~~~~~~~~~~~~~~~~~~

**Design Choice**: Use conditional logging for expensive operations

.. code-block:: python

   # Good: Check level before expensive computation
   if logger.logger.isEnabledFor(logging.DEBUG):
       expensive_message = compute_detailed_stats()
       logger.debug(expensive_message)

**Overhead:**

- INFO level: ~1-2μs per call
- DEBUG level: ~2-5μs per call (if enabled)
- Negligible for model building/solving

ORM Query Performance
~~~~~~~~~~~~~~~~~~~~~

**Design Choice**: Filter in Python (not at database level)

.. code-block:: python

   def filter(self, predicate: Callable[[TModel], bool]) -> Self:
       self._filters.append(predicate)  # Store for later
       return self

   def all(self) -> List[TModel]:
       results = self.session.query(self.model).all()  # Fetch all
       for predicate in self._filters:
           results = [r for r in results if predicate(r)]  # Filter in Python
       return results

**Trade-off:**

- Pro: Type-safe lambdas with full IDE support
- Con: Fetches all data then filters
- Mitigation: Use ORM filters first for large datasets

Rational Conversion Performance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Algorithm Complexity:**

- Farey: O(log(max_denominator))
- Continued Fraction: O(log(value))
- Stern-Brocot: O(log(max_denominator))

**Benchmarks** (typical):

- Small denominators (<1000): ~5-10μs
- Medium denominators (~10000): ~15-25μs
- Large denominators (>100000): ~50-100μs

Testing Strategy
----------------

Unit Tests
~~~~~~~~~~

Each component has comprehensive unit tests:

.. code-block:: python

   # Test logger
   def test_log_model_creation(caplog):
       logger = LXModelLogger()
       logger.log_model_creation("TestModel", num_vars=10, num_constraints=5)
       assert "TestModel" in caplog.text
       assert "10 variables" in caplog.text

   # Test ORM protocol
   def test_orm_protocol():
       @dataclass
       class Product:
           id: int

       assert isinstance(Product(1), LXORMModel)

   # Test rational conversion
   def test_farey_approximation():
       converter = LXRationalConverter(method="farey")
       frac = converter.to_rational(3.14159)
       assert abs(float(frac) - 3.14159) < 1e-4

Type Tests
~~~~~~~~~~

Use mypy for static type checking:

.. code-block:: bash

   mypy src/lumix/utils

Integration Tests
~~~~~~~~~~~~~~~~~

Test interaction with core LumiX:

.. code-block:: python

   def test_orm_with_variable():
       products = [Product(id=1, profit=10.0)]
       production = LXVariable[Product, float]("x").from_data(products)
       assert len(production.get_instances()) == 1

Extension Points
----------------

Custom Logger Methods
~~~~~~~~~~~~~~~~~~~~~

Subclass for domain-specific logging:

.. code-block:: python

   class LXTransportLogger(LXModelLogger):
       """Specialized for transportation models."""

       def log_route_creation(self, origin: str, dest: str, count: int):
           self.logger.debug(f"Created {count} route(s): {origin} → {dest}")

Custom ORM Protocols
~~~~~~~~~~~~~~~~~~~~

Define additional protocols for specific needs:

.. code-block:: python

   class LXTimestampedModel(Protocol):
       """Protocol for models with timestamps."""
       id: Any
       created_at: datetime
       updated_at: datetime

New Conversion Algorithms
~~~~~~~~~~~~~~~~~~~~~~~~~~

Add new rational approximation methods:

.. code-block:: python

   class LXRationalConverter:
       def _custom_approximation(self, x: float) -> Tuple[int, int, float]:
           """Implement custom algorithm here."""
           # ...
           return numerator, denominator, error

See Also
--------

- :doc:`extending-utils` - How to extend utils components
- :doc:`core-architecture` - Core module architecture
- :doc:`/api/utils/index` - Utils API reference
