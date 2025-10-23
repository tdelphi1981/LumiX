Utils Module API
================

The utils module provides utility classes and protocols for enhanced functionality in LumiX,
including logging, ORM integration, and rational number conversion.

Overview
--------

The utils module consists of three main components:

.. mermaid::

   graph TD
       A[Utils Module] --> B[LXModelLogger]
       A --> C[ORM Integration]
       A --> D[LXRationalConverter]
       C --> E[LXORMModel]
       C --> F[LXORMContext]
       C --> G[LXTypedQuery]
       C --> H[LXNumeric]

       style A fill:#e1f5ff
       style B fill:#fff4e1
       style C fill:#ffe1e1
       style D fill:#e1ffe1
       style E fill:#f0e1ff
       style F fill:#f0e1ff
       style G fill:#f0e1ff
       style H fill:#f0e1ff

Components
----------

Logging
~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.utils.logger.LXModelLogger

The :class:`~lumix.utils.logger.LXModelLogger` provides optimization-specific logging
capabilities for tracking model construction, solving progress, and solution analysis.

**Key Features:**

- Automatic solve time tracking
- Specialized logging methods for optimization events
- Configurable logging levels
- Integration with Python's logging system

ORM Integration
~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.utils.orm.LXORMModel
   lumix.utils.orm.LXORMContext
   lumix.utils.orm.LXTypedQuery
   lumix.utils.orm.LXNumeric

ORM integration components enable type-safe database queries and seamless integration
with ORM libraries like SQLAlchemy, Django ORM, and Peewee.

**Key Features:**

- Structural typing via Protocol (PEP 544)
- Type-safe query builders
- Full IDE autocomplete support
- ORM-agnostic design

Rational Conversion
~~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.utils.rational.LXRationalConverter

The :class:`~lumix.utils.rational.LXRationalConverter` converts floating-point coefficients
to rational numbers for use with integer-only solvers.

**Key Features:**

- Three approximation algorithms (Farey, Continued Fraction, Stern-Brocot)
- Configurable precision control
- Batch coefficient conversion
- Error tracking and comparison

Detailed API Reference
-----------------------

Logging Module
~~~~~~~~~~~~~~

.. automodule:: lumix.utils.logger
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource

ORM Module
~~~~~~~~~~

.. automodule:: lumix.utils.orm
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource

Rational Conversion Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: lumix.utils.rational
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource

Quick Reference
---------------

**Most Commonly Used Classes**

- :class:`lumix.utils.logger.LXModelLogger` - Enhanced logging for optimization
- :class:`lumix.utils.orm.LXORMContext` - Type-safe ORM query interface
- :class:`lumix.utils.orm.LXTypedQuery` - Fluent query builder
- :class:`lumix.utils.rational.LXRationalConverter` - Float-to-rational conversion

Usage Examples
--------------

Model Logging
~~~~~~~~~~~~~

Quick example of using the model logger::

    from lumix.utils import LXModelLogger
    import logging

    logger = LXModelLogger(name="production_model", level=logging.INFO)
    logger.log_model_creation("ProductionPlan", num_vars=100, num_constraints=50)
    logger.log_solve_start("Gurobi")
    # ... solving happens ...
    logger.log_solve_end("Optimal", objective_value=42500.0)

ORM Integration
~~~~~~~~~~~~~~~

Type-safe ORM queries::

    from lumix.utils import LXORMContext
    from lumix import LXVariable

    # Create ORM context
    ctx = LXORMContext(session)

    # Query with type safety
    products = ctx.query(Product).filter(lambda p: p.active).all()

    # Use in optimization model
    production = (
        LXVariable[Product, float]("production")
        .continuous()
        .from_data(products)
        .indexed_by(lambda p: p.id)
    )

Rational Conversion
~~~~~~~~~~~~~~~~~~~

Convert floats to rationals::

    from lumix.utils import LXRationalConverter

    converter = LXRationalConverter(max_denominator=10000)

    # Single conversion
    frac = converter.to_rational(3.14159)  # Fraction(355, 113)

    # Batch conversion
    coeffs = {"x1": 3.5, "x2": 2.333, "x3": 1.25}
    int_coeffs, denom = converter.convert_coefficients(coeffs)

See Also
--------

- :doc:`/user-guide/utils/index` - Utils module usage guide
- :doc:`/development/utils-architecture` - Utils architecture details
- :doc:`/api/core/index` - Core module API reference
