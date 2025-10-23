Core Concepts
=============

This guide covers the fundamental concepts and components of LumiX's core module.

Introduction
------------

The core module implements a **data-driven, type-safe approach** to optimization modeling.
Instead of manually creating solver variables in loops, you define *variable families* and
*constraint families* that automatically expand based on your data.

Philosophy
----------

Traditional Approach (Manual)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Traditional optimization libraries require manual loops and index management:

.. code-block:: python

   # Traditional approach - error-prone, verbose
   x = {}
   for i in range(len(products)):
       x[i] = model.addVar(name=f"x_{i}")

   model.addConstr(
       sum(x[i] * costs[i] for i in range(len(products))) <= budget
   )

LumiX Approach (Data-Driven)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

LumiX uses data-driven variable families that expand automatically:

.. code-block:: python

   # LumiX approach - type-safe, concise
   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

   model.add_constraint(
       LXConstraint("budget")
       .expression(
           LXLinearExpression()
           .add_term(production, lambda p: p.cost)
       )
       .le()
       .rhs(budget)
   )

**Benefits:**

- ✓ Full IDE autocomplete
- ✓ Type checking catches errors early
- ✓ No manual indexing
- ✓ Data-driven coefficients
- ✓ Readable, maintainable code

Core Components
---------------

The core module consists of five main components:

.. mermaid::

   graph LR
       A[Your Data Models] --> B[LXVariable]
       A --> C[LXConstraint]
       B --> D[LXExpression]
       C --> D
       D --> E[LXModel]
       F[LXEnums] --> B
       F --> C
       F --> E

       style A fill:#e8f4f8
       style E fill:#e1f5ff
       style B fill:#fff4e1
       style C fill:#ffe1e1
       style D fill:#e1ffe1
       style F fill:#f0e1ff

1. **Data Models**: Your business entities (Product, Route, Driver, etc.)
2. **Variables** (:class:`~lumix.core.variables.LXVariable`): Decision variables indexed by data
3. **Constraints** (:class:`~lumix.core.constraints.LXConstraint`): Constraints indexed by data
4. **Expressions** (:class:`~lumix.core.expressions.LXLinearExpression`): Mathematical expressions
5. **Model** (:class:`~lumix.core.model.LXModel`): Container for the complete optimization problem

Component Details
-----------------

Variables
~~~~~~~~~

Variables represent decisions to be made. See :doc:`variables` for detailed guide.

**Key Concepts:**

- Variables are *families*, not individual variables
- Automatically indexed by data
- Support continuous, integer, and binary types
- Can be filtered with `where()` clauses

**Quick Example:**

.. code-block:: python

   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .bounds(lower=0)
       .indexed_by(lambda p: p.id)
       .where(lambda p: p.is_active)  # Filter
       .from_data(products)
   )

Constraints
~~~~~~~~~~~

Constraints define the feasible region. See :doc:`constraints` for detailed guide.

**Key Concepts:**

- Constraints are *families* that expand based on data
- Support LE (<=), GE (>=), and EQ (==) senses
- RHS can be constant or data-driven
- Can be marked as goals for multi-objective optimization

**Quick Example:**

.. code-block:: python

   capacity = (
       LXConstraint[Resource]("capacity")
       .expression(
           LXLinearExpression()
           .add_term(production, lambda p, r: p.usage[r.id])
       )
       .le()
       .rhs(lambda r: r.capacity)
       .from_data(resources)
       .indexed_by(lambda r: r.id)
   )

Expressions
~~~~~~~~~~~

Expressions build mathematical formulas. See :doc:`expressions` for detailed guide.

**Types:**

- **Linear**: Sum of terms with coefficients
- **Quadratic**: Includes x*y products
- **Non-linear**: Absolute value, min/max, piecewise

**Quick Example:**

.. code-block:: python

   profit_expr = (
       LXLinearExpression()
       .add_term(production, lambda p: p.selling_price - p.cost)
       .add_constant(-fixed_cost)
   )

Models
~~~~~~

Models tie everything together. See :doc:`models` for detailed guide.

**Quick Example:**

.. code-block:: python

   model = (
       LXModel("production_plan")
       .add_variable(production)
       .add_constraint(capacity)
       .maximize(profit_expr)
   )

Data Flow
---------

Understanding how data flows through LumiX:

.. mermaid::

   sequenceDiagram
       participant User
       participant Variable
       participant Expression
       participant Model
       participant Solver

       User->>Variable: Define with .from_data(products)
       User->>Expression: Build with lambda p: p.cost
       User->>Model: Add variables & constraints
       User->>Solver: solve(model)
       Solver->>Variable: Expand families to solver vars
       Solver->>Expression: Evaluate lambdas for each instance
       Solver->>Model: Build solver-specific model
       Solver-->>User: Return solution

**Key Points:**

1. You provide data when defining variables/constraints
2. Coefficients are lambda functions that receive data instances
3. Expansion happens automatically during solving
4. Lambdas are evaluated for each data instance

Type Safety
-----------

LumiX uses Python's type system for compile-time checking:

.. code-block:: python

   from dataclasses import dataclass

   @dataclass
   class Product:
       id: str
       cost: float
       profit: float

   # Type-safe: IDE knows 'p' is a Product
   production = LXVariable[Product, float]("production")

   # IDE autocomplete works here!
   expr.add_term(production, lambda p: p.profit)  # ✓ Autocomplete
   expr.add_term(production, lambda p: p.foo)     # ✗ Type error

**Benefits:**

- IDE autocomplete for all lambda parameters
- mypy catches type errors before runtime
- Self-documenting code
- Refactoring is safer

Fluent API
----------

All core classes use fluent API (method chaining):

.. code-block:: python

   # Each method returns self, enabling chaining
   production = (
       LXVariable[Product, float]("production")
       .continuous()              # Returns self
       .bounds(lower=0)           # Returns self
       .indexed_by(lambda p: p.id)# Returns self
       .cost(lambda p: p.profit)  # Returns self
       .from_data(products)       # Returns self
   )

   model = (
       LXModel("plan")
       .add_variable(production)  # Returns self
       .add_constraint(capacity)  # Returns self
       .maximize(objective)       # Returns self
   )

**Style Guide:**

- Use parentheses to enable multi-line chains
- One method per line for readability
- Align dots vertically

Next Steps
----------

Dive deeper into each component:

.. toctree::
   :maxdepth: 2

   variables
   constraints
   expressions
   models

Or continue to:

- :doc:`/getting-started/quickstart` - Build your first model
- :doc:`/api/core/index` - Detailed API reference
- :doc:`/examples/index` - Working examples
