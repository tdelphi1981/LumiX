User Guide
==========

Comprehensive guides for using LumiX effectively in your optimization projects.

.. toctree::
   :maxdepth: 2
   :caption: User Guide Topics

   core/index
   indexing/index
   nonlinear/index
   linearization/index
   utils/index

Core Module
-----------

The :doc:`core/index` section covers the fundamental concepts and components.

**Topics Covered:**

- Data-driven modeling philosophy
- Variable families and indexing
- Constraint definition and expansion
- Expression building (linear, quadratic, non-linear)
- Model construction and solving

Indexing Module
---------------

The :doc:`indexing/index` section covers multi-dimensional indexing capabilities.

**Topics Covered:**

- Single-model and multi-model indexing
- Index dimensions and cartesian products
- Filtering strategies (per-dimension and cross-dimension)
- Type-safe multi-dimensional variables
- Sparse indexing patterns

Nonlinear Module
----------------

The :doc:`nonlinear/index` section covers nonlinear term definitions and modeling.

**Topics Covered:**

- Absolute value terms for deviation minimization
- Min/max operations over alternatives
- Bilinear products (x * y) with automatic linearization
- Indicator (conditional) constraints
- Piecewise-linear approximations of nonlinear functions
- Integration with automatic linearization

Linearization Module
--------------------

The :doc:`linearization/index` section covers automatic linearization of nonlinear terms.

**Topics Covered:**

- Automatic detection and linearization of nonlinear terms
- Bilinear product linearization (McCormick, Big-M, Binary AND)
- Piecewise-linear function approximation (SOS2, Incremental)
- Pre-built nonlinear functions (exp, log, sqrt, power, sigmoid, trig)
- Configuration and accuracy tuning
- Integration with solver capabilities

Utils Module
------------

The :doc:`utils/index` section covers utility components for enhanced functionality.

**Topics Covered:**

- Enhanced logging for optimization models
- Type-safe ORM integration (SQLAlchemy, Django)
- Float-to-rational conversion for integer solvers
- Integration patterns and best practices

Quick Start
-----------

New to LumiX? Start here:

1. :doc:`/getting-started/installation` - Install LumiX
2. :doc:`/getting-started/quickstart` - Build your first model
3. :doc:`core/index` - Understand core concepts
4. :doc:`/examples/index` - See working examples

Coming Soon
-----------

The following sections will be added in future updates:

Coming Soon
-----------

This section will include detailed guides on:

Analysis Tools
~~~~~~~~~~~~~~

- Sensitivity analysis workflows
- Scenario comparison
- What-if analysis for decision support

Goal Programming
~~~~~~~~~~~~~~~~

- Weighted goal programming
- Sequential (lexicographic) goal programming
- Constraint relaxation

Advanced Topics
~~~~~~~~~~~~~~~

- ORM integration patterns
- Custom solver configuration
- Performance optimization
- Debugging infeasible models

Stay Tuned
----------

We're actively working on expanding this documentation. Check back soon or:

- Browse the examples in the repository
- Read the API documentation (coming soon)
- Open an issue if you need specific guidance
