Utils Module Guide
==================

Comprehensive guide to using LumiX's utility modules for enhanced functionality.

Introduction
------------

The utils module provides four categories of utilities to enhance your LumiX experience:

1. **Logging**: Enhanced logging specifically designed for optimization models
2. **ORM Integration**: Type-safe integration with database ORMs
3. **Rational Conversion**: Float-to-rational conversion for integer-only solvers
4. **Model Copying**: ORM-safe model copying for what-if and scenario analysis

These utilities are designed to integrate seamlessly with the core LumiX functionality
while remaining optional - you can use whichever components fit your workflow.

.. mermaid::

   graph LR
       A[Your Application] --> B[LXModelLogger]
       A --> C[ORM Integration]
       A --> D[LXRationalConverter]
       B --> E[Optimization Model]
       C --> E
       D --> E
       E --> F[Solver]

       style A fill:#e8f4f8
       style E fill:#e1f5ff
       style B fill:#fff4e1
       style C fill:#ffe1e1
       style D fill:#e1ffe1
       style F fill:#f0e1ff

Module Components
-----------------

.. toctree::
   :maxdepth: 2

   logging
   orm-integration
   rational-conversion
   model-copying

Logging Utilities
~~~~~~~~~~~~~~~~~

The :doc:`logging` guide covers the LXModelLogger class:

- **Purpose**: Domain-specific logging for optimization models
- **Key Features**: Automatic timing, formatted output, solve tracking
- **When to Use**: Track model building, solving progress, and solution analysis

**Quick Example:**

.. code-block:: python

   from lumix.utils import LXModelLogger

   logger = LXModelLogger(name="my_model")
   logger.log_model_creation("Production", num_vars=100, num_constraints=50)
   logger.log_solve_start("Gurobi")
   # ... solving ...
   logger.log_solve_end("Optimal", objective_value=42500.0)

ORM Integration
~~~~~~~~~~~~~~~

The :doc:`orm-integration` guide covers type-safe ORM integration:

- **Purpose**: Seamlessly integrate database models with optimization
- **Key Features**: Structural typing, full IDE support, ORM-agnostic
- **When to Use**: Build models from database data with type safety

**Quick Example:**

.. code-block:: python

   from lumix.utils import LXORMContext
   from lumix import LXVariable

   # Query with type safety
   ctx = LXORMContext(session)
   products = ctx.query(Product).filter(lambda p: p.active).all()

   # Use in model
   production = (
       LXVariable[Product, float]("production")
       .from_data(products)
       .indexed_by(lambda p: p.id)
   )

Rational Conversion
~~~~~~~~~~~~~~~~~~~

The :doc:`rational-conversion` guide covers float-to-rational conversion:

- **Purpose**: Convert floating-point coefficients to exact rationals
- **Key Features**: Multiple algorithms, configurable precision, batch conversion
- **When to Use**: Working with integer-only solvers (GLPK), exact arithmetic needs

**Quick Example:**

.. code-block:: python

   from lumix.utils import LXRationalConverter

   converter = LXRationalConverter(max_denominator=10000)

   # Convert coefficients
   coeffs = {"x1": 3.5, "x2": 2.333, "x3": 1.25}
   int_coeffs, denom = converter.convert_coefficients(coeffs)

Model Copying
~~~~~~~~~~~~~

The :doc:`model-copying` guide covers ORM-safe model copying:

- **Purpose**: Safely copy models with ORM data sources for analysis
- **Key Features**: Automatic ORM detachment, session independence, lambda closure handling
- **When to Use**: What-if analysis, scenario analysis, any workflow requiring model copies

**Quick Example:**

.. code-block:: python

   from copy import deepcopy
   from lumix import LXModel, LXVariable

   # Build model with SQLAlchemy data
   production = LXVariable[Product, float]("production")
       .from_model(session)  # Uses ORM session

   model = LXModel("production").add_variable(production)

   # Copy works automatically! ORM objects detached
   modified_model = deepcopy(model)  # ✓ Success

   # Use for what-if analysis
   from lumix.analysis import LXWhatIfAnalyzer
   analyzer = LXWhatIfAnalyzer(model, optimizer)
   result = analyzer.increase_constraint_rhs("capacity", by=100)

Common Use Cases
----------------

Production Model Logging
~~~~~~~~~~~~~~~~~~~~~~~~

Track model building and solving in production environments:

.. code-block:: python

   import logging
   from lumix import LXModel, LXVariable, LXOptimizer
   from lumix.utils import LXModelLogger

   # Set up logging
   logger = LXModelLogger(name="production", level=logging.INFO)

   # Build model (with logging)
   logger.info("Building production planning model")
   model = LXModel("production_plan")

   logger.log_variable_creation("production", "continuous", count=50)
   production = LXVariable[Product, float]("production").from_data(products)
   model.add_variable(production)

   # Solve (with timing)
   logger.log_solve_start("Gurobi")
   optimizer = LXOptimizer().use_solver("gurobi")
   solution = optimizer.solve(model)
   logger.log_solve_end(solution.status, solution.objective_value)

Database-Driven Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Build optimization models directly from database queries:

.. code-block:: python

   from sqlalchemy.orm import Session
   from lumix import LXModel, LXVariable, LXConstraint, LXLinearExpression
   from lumix.utils import LXORMContext

   # Database models
   class Product(Base):
       __tablename__ = 'products'
       id = Column(Integer, primary_key=True)
       profit = Column(Float)
       cost = Column(Float)

   class Resource(Base):
       __tablename__ = 'resources'
       id = Column(Integer, primary_key=True)
       capacity = Column(Float)

   # Query with type safety
   session = Session()
   ctx = LXORMContext(session)

   products = ctx.query(Product).filter(lambda p: p.profit > 10).all()
   resources = ctx.query(Resource).all()

   # Build model from database data
   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .bounds(lower=0)
       .from_data(products)
       .indexed_by(lambda p: p.id)
   )

   # Objective from database
   model = (
       LXModel("db_driven")
       .add_variable(production)
       .maximize(
           LXLinearExpression().add_term(production, lambda p: p.profit)
       )
   )

Integer Solver Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use GLPK or other integer-only solvers with rational conversion:

.. code-block:: python

   from lumix import LXModel, LXVariable, LXLinearExpression
   from lumix.utils import LXRationalConverter

   # Build model with float coefficients
   model = LXModel("integer_model")
   production = LXVariable[Product, float]("x").from_data(products)
   model.add_variable(production)

   # Objective with float coefficients
   model.maximize(
       LXLinearExpression().add_term(production, lambda p: p.profit)
   )

   # Convert to rationals for GLPK
   converter = LXRationalConverter(max_denominator=10000)

   # Extract and convert coefficients
   obj_coeffs = {p.id: p.profit for p in products}
   int_coeffs, denom = converter.convert_coefficients(obj_coeffs)

   # Use integer coefficients with solver
   # (solver-specific code here)

Best Practices
--------------

Logging
~~~~~~~

1. **Use Consistent Names**: Use descriptive logger names for each model
2. **Set Appropriate Levels**: Use DEBUG for development, INFO for production
3. **Log Key Events**: Focus on model creation, solve start/end, and key milestones
4. **Custom Messages**: Use generic logging methods (info, warning, error) for custom events

ORM Integration
~~~~~~~~~~~~~~~

1. **Filter Early**: Apply ORM-specific filters before using LXTypedQuery
2. **Eager Loading**: Use ORM eager loading to avoid N+1 queries
3. **Type Safety**: Always specify type parameters for full IDE support
4. **Session Management**: Properly manage ORM sessions (use context managers)

Rational Conversion
~~~~~~~~~~~~~~~~~~~

1. **Choose Appropriate Max Denominator**: Balance accuracy vs. denominator size
2. **Use Farey Method**: Default Farey method is fastest and recommended
3. **Check Approximation Error**: Use return_error=True to monitor accuracy
4. **Batch Convert**: Use convert_coefficients() for multiple values

Performance Considerations
--------------------------

Logging Overhead
~~~~~~~~~~~~~~~~

- Logging has minimal overhead at INFO level
- DEBUG level can slow down model building significantly
- Use conditional logging for performance-critical sections
- Consider disabling logging in inner loops

ORM Query Performance
~~~~~~~~~~~~~~~~~~~~~

- LXTypedQuery applies filters in Python, not at database level
- For large datasets, use ORM-specific filtering first
- Consider caching query results for repeated model builds
- Use database indexes for frequently filtered columns

Rational Conversion Speed
~~~~~~~~~~~~~~~~~~~~~~~~~

- Farey method is fastest (recommended)
- Continued fraction has similar performance
- Stern-Brocot is equivalent to Farey but different framing
- Larger max_denominator increases computation time

Next Steps
----------

Explore each component in detail:

- :doc:`logging` - Complete logging guide
- :doc:`orm-integration` - ORM integration patterns
- :doc:`rational-conversion` - Rational conversion algorithms
- :doc:`model-copying` - ORM-safe model copying strategy

Or continue to:

- :doc:`/api/utils/index` - Detailed API reference
- :doc:`/user-guide/analysis/whatif` - What-if analysis guide (uses model copying)
- :doc:`/tutorials/production_planning/step7_whatif` - Tutorial with model copying
- :doc:`/development/utils-architecture` - Architecture details
- :doc:`/examples/index` - Working examples
