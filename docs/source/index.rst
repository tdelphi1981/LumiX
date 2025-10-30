.. LumiX documentation master file

.. image:: _static/Lumix_Logo_1024.png
   :width: 200px
   :align: center
   :alt: LumiX Logo

Welcome to LumiX Documentation
===============================

.. image:: https://img.shields.io/badge/python-3.10+-blue.svg
   :target: https://www.python.org/downloads/
   :alt: Python Version

.. image:: https://img.shields.io/badge/license-AFL--3.0-green.svg
   :target: https://opensource.org/licenses/AFL-3.0
   :alt: License

**LumiX** is a modern, type-safe wrapper for optimization solvers that makes mathematical programming accessible, maintainable, and enjoyable.

Key Features
------------

🎯 **Type-Safe & IDE-Friendly**
   Full type hints and autocomplete support for a superior development experience

🔌 **Multi-Solver Support**
   Seamlessly switch between OR-Tools, Gurobi, CPLEX, GLPK, and CP-SAT

📊 **Data-Driven Modeling**
   Build models directly from your data with automatic indexing and mapping

🔄 **Automatic Linearization**
   Automatically linearize non-linear constraints (bilinear, absolute value, piecewise)

📈 **Advanced Analysis**
   Built-in sensitivity analysis, scenario analysis, and what-if analysis tools

🎯 **Goal Programming**
   Native support for multi-objective optimization with priorities and weights

⚡ **ORM Integration**
   Type-safe integration with SQLAlchemy, Django ORM, and other databases

🛠️ **Enhanced Logging**
   Domain-specific logging for tracking model building and solving progress

Quick Example
-------------

.. code-block:: python

   from lumix import LXModel, LXVariable, LXConstraint, LXLinearExpression, LXOptimizer

   # Define variables
   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .bounds(lower=0)
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

   # Build model
   model = (
       LXModel("production_plan")
       .add_variable(production)
       .maximize(
           LXLinearExpression()
           .add_term(production, lambda p: p.profit)
       )
   )

   # Solve
   optimizer = LXOptimizer().use_solver("gurobi")
   solution = optimizer.solve(model)

   print(f"Optimal profit: ${solution.objective_value:,.2f}")

Supported Solvers
-----------------

LumiX provides unified interfaces to multiple optimization solvers:

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 15 15 20

   * - Solver
     - Linear
     - Integer
     - Quadratic
     - Advanced
     - License
   * - **OR-Tools**
     - ✓
     - ✓
     - ✗
     - SOS, Indicator
     - Apache 2.0 (Free)
   * - **Gurobi**
     - ✓
     - ✓
     - ✓
     - SOCP, PWL, Callbacks
     - Commercial/Academic
   * - **CPLEX**
     - ✓
     - ✓
     - ✓
     - SOCP, PWL, Callbacks
     - Commercial/Academic
   * - **GLPK**
     - ✓
     - ✓
     - ✗
     - Basic
     - GPL (Free)
   * - **CP-SAT**
     - ✗
     - ✓
     - ✗
     - Constraint Programming
     - Apache 2.0 (Free)

.. seealso::
   See :doc:`getting-started/solvers` for detailed solver capabilities and installation instructions.

Table of Contents
-----------------

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   getting-started/installation
   getting-started/quickstart
   getting-started/solvers

.. toctree::
   :maxdepth: 2
   :caption: Tutorials

   tutorials/index

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   user-guide/index

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/index

.. toctree::
   :maxdepth: 2
   :caption: Development

   development/index

.. toctree::
   :maxdepth: 2
   :caption: Examples

   examples/index

Why LumiX?
----------

Traditional optimization libraries require verbose, error-prone code with limited IDE support.
LumiX changes that:

**Before (Traditional Approach)**

.. code-block:: python

   # Manual indexing, no type safety
   x = {}
   for i in range(len(products)):
       x[i] = model.addVar(name=f"x_{i}")

   # String-based error-prone expressions
   model.addConstr(sum(x[i] * data[i] for i in range(len(products))) <= capacity)

**After (LumiX)**

.. code-block:: python

   # Type-safe, data-driven, IDE-friendly
   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

   model.add_constraint(
       LXConstraint("capacity")
       .expression(
           LXLinearExpression().add_term(production, lambda p: p.usage)
       )
       .le()
       .rhs(capacity)
   )

Core Capabilities
-----------------

Model Building
~~~~~~~~~~~~~~

- **Variables**: Continuous, integer, binary with automatic indexing
- **Constraints**: Linear, quadratic, indicator, and more
- **Expressions**: Type-safe expression building with full IDE support
- **Multi-indexing**: Natural multi-dimensional indexing (e.g., Driver × Date × Shift)
- **Index Dimensions**: Flexible, filterable dimensions for single and multi-model indexing
- **Cartesian Products**: Type-safe multi-dimensional variable families

Linearization
~~~~~~~~~~~~~

Automatic linearization of non-linear terms:

- Bilinear products (x × y) using McCormick envelopes
- Absolute values (|x|)
- Min/max functions
- Piecewise-linear functions
- Indicator constraints

Analysis Tools
~~~~~~~~~~~~~~

- **Sensitivity Analysis**: Understand how changes in parameters affect the solution
- **Scenario Analysis**: Compare multiple scenarios side-by-side
- **What-If Analysis**: Quickly evaluate changes without rebuilding models

Utils Module
~~~~~~~~~~~~

Enhanced utilities for production-ready optimization:

- **LXModelLogger**: Domain-specific logging with automatic timing and formatted output
- **ORM Integration**: Type-safe queries with full IDE support for SQLAlchemy, Django ORM
- **Rational Conversion**: Float-to-rational conversion for integer-only solvers (GLPK)

Goal Programming
~~~~~~~~~~~~~~~~

Multi-objective optimization with:

- Weighted goal programming
- Sequential (lexicographic) goal programming
- Automatic constraint relaxation with deviation tracking

Community & Support
-------------------

- **Documentation**: https://lumix.readthedocs.io
- **Source Code**: https://github.com/tdelphi1981/LumiX
- **Issue Tracker**: https://github.com/tdelphi1981/LumiX/issues
- **License**: Academic Free License v3.0

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
