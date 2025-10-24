User Guide
==========

Comprehensive guides for using LumiX effectively in your optimization projects.

.. toctree::
   :maxdepth: 2
   :caption: User Guide Topics

   core/index
   solvers/index
   indexing/index
   nonlinear/index
   linearization/index
   utils/index
   solution/index
   analysis/index
   goal_programming/index

Core Module
-----------

The :doc:`core/index` section covers the fundamental concepts and components.

**Topics Covered:**

- Data-driven modeling philosophy
- Variable families and indexing
- Constraint definition and expansion
- Expression building (linear, quadratic, non-linear)
- Model construction and solving

Solvers Module
--------------

The :doc:`solvers/index` section covers using LumiX's unified solver interface.

**Topics Covered:**

- Using the LXOptimizer class
- Choosing the right solver for your problem
- Configuring solver parameters
- Understanding solver capabilities
- Advanced features (warm start, callbacks, sensitivity analysis)
- Switching between solvers seamlessly

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

Solution Module
---------------

The :doc:`solution/index` section covers working with optimization solutions.

**Topics Covered:**

- Accessing variable values and solution metadata
- Goal programming solution handling
- Mapping solution values to ORM models
- Solution validation and export

Analysis Module
---------------

The :doc:`analysis/index` section covers post-optimization analysis and decision support tools.

**Topics Covered:**

- Sensitivity analysis with shadow prices and reduced costs
- Scenario analysis for systematic comparison of alternatives
- What-if analysis for interactive parameter exploration
- Bottleneck identification and resource allocation
- Multi-parameter analysis and trade-off exploration

Goal Programming Module
------------------------

The :doc:`goal_programming/index` section covers multi-objective optimization using goal programming.

**Topics Covered:**

- Converting hard constraints to soft constraints (goals)
- Weighted goal programming (single solve with priority weights)
- Sequential goal programming (lexicographic optimization)
- Constraint relaxation and deviation variables
- Building and combining goal programming objectives
- Working with goal programming solutions

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
- Read the API documentation
- Open an issue if you need specific guidance
