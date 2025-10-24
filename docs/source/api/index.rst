API Reference
=============

Complete API documentation for all LumiX modules with auto-generated documentation from source code.

.. toctree::
   :maxdepth: 2
   :caption: API Modules

   core/index
   solvers/index
   indexing/index
   nonlinear/index
   linearization/index
   utils/index
   solution/index

Core Module
-----------

The :doc:`core/index` module provides the fundamental building blocks for optimization models:

- :class:`~lumix.core.model.LXModel` - Model builder with fluent API
- :class:`~lumix.core.variables.LXVariable` - Type-safe variable families
- :class:`~lumix.core.constraints.LXConstraint` - Data-driven constraints
- :class:`~lumix.core.expressions.LXLinearExpression` - Linear expressions
- :class:`~lumix.core.expressions.LXQuadraticExpression` - Quadratic expressions
- :class:`~lumix.core.enums.LXVarType` - Variable type enumeration
- :class:`~lumix.core.enums.LXConstraintSense` - Constraint sense enumeration
- :class:`~lumix.core.enums.LXObjectiveSense` - Objective sense enumeration

Solvers Module
--------------

The :doc:`solvers/index` module provides a unified interface to multiple optimization solvers:

- :class:`~lumix.solvers.base.LXOptimizer` - Main optimizer interface
- :class:`~lumix.solvers.base.LXSolverInterface` - Base solver interface
- :class:`~lumix.solvers.capabilities.LXSolverCapability` - Solver capability descriptions
- :class:`~lumix.solvers.capabilities.LXSolverFeature` - Solver feature flags

Supported solvers: OR-Tools, Gurobi, CPLEX, GLPK, CP-SAT

Indexing Module
---------------

The :doc:`indexing/index` module provides multi-dimensional indexing capabilities:

- :class:`~lumix.indexing.dimensions.LXIndexDimension` - Single dimension with filtering
- :class:`~lumix.indexing.cartesian.LXCartesianProduct` - Multi-dimensional cartesian products

Nonlinear Module
----------------

The :doc:`nonlinear/index` module provides nonlinear term definitions:

- :class:`~lumix.nonlinear.terms.LXAbsoluteTerm` - Absolute value operations |x|
- :class:`~lumix.nonlinear.terms.LXMinMaxTerm` - Min/max over multiple variables
- :class:`~lumix.nonlinear.terms.LXBilinearTerm` - Products of two variables x*y
- :class:`~lumix.nonlinear.terms.LXIndicatorTerm` - Conditional (if-then) constraints
- :class:`~lumix.nonlinear.terms.LXPiecewiseLinearTerm` - Piecewise-linear function approximations

Linearization Module
--------------------

The :doc:`linearization/index` module provides automatic linearization of nonlinear terms:

- :class:`~lumix.linearization.engine.LXLinearizer` - Main linearization engine
- :class:`~lumix.linearization.config.LXLinearizerConfig` - Configuration settings
- :class:`~lumix.linearization.config.LXLinearizationMethod` - Available methods
- :class:`~lumix.linearization.functions.LXNonLinearFunctions` - Pre-built function approximations
- :class:`~lumix.linearization.techniques.LXBilinearLinearizer` - Bilinear product linearization
- :class:`~lumix.linearization.techniques.LXPiecewiseLinearizer` - Piecewise-linear approximation

Utils Module
------------

The :doc:`utils/index` module provides utility classes for enhanced functionality:

- :class:`~lumix.utils.logger.LXModelLogger` - Enhanced logging for optimization models
- :class:`~lumix.utils.orm.LXORMContext` - Type-safe ORM query interface
- :class:`~lumix.utils.orm.LXTypedQuery` - Fluent query builder with type safety
- :class:`~lumix.utils.rational.LXRationalConverter` - Float-to-rational conversion

Solution Module
---------------

The :doc:`solution/index` module provides solution handling and mapping utilities:

- :class:`~lumix.solution.solution.LXSolution` - Solution container with variable values and metadata
- :class:`~lumix.solution.mapping.LXSolutionMapper` - Utilities for mapping solutions to model instances

Quick Links
-----------

**Most Commonly Used Classes**

Core:
  - :class:`lumix.core.model.LXModel` - Start here to build models
  - :class:`lumix.core.variables.LXVariable` - Define decision variables
  - :class:`lumix.core.constraints.LXConstraint` - Add constraints
  - :class:`lumix.core.expressions.LXLinearExpression` - Build expressions

Solvers:
  - :class:`lumix.solvers.base.LXOptimizer` - Solve models with any solver
  - :class:`lumix.solvers.capabilities.LXSolverCapability` - Query solver capabilities

Indexing:
  - :class:`lumix.indexing.dimensions.LXIndexDimension` - Single dimension indexing
  - :class:`lumix.indexing.cartesian.LXCartesianProduct` - Multi-dimensional products

Nonlinear:
  - :class:`lumix.nonlinear.terms.LXAbsoluteTerm` - Absolute value terms
  - :class:`lumix.nonlinear.terms.LXBilinearTerm` - Bilinear products
  - :class:`lumix.nonlinear.terms.LXPiecewiseLinearTerm` - Piecewise-linear approximations

Linearization:
  - :class:`lumix.linearization.engine.LXLinearizer` - Automatic linearization engine
  - :class:`lumix.linearization.config.LXLinearizerConfig` - Linearization configuration
  - :class:`lumix.linearization.functions.LXNonLinearFunctions` - Pre-built functions

Utils:
  - :class:`lumix.utils.logger.LXModelLogger` - Model logging utilities
  - :class:`lumix.utils.orm.LXORMContext` - ORM integration
  - :class:`lumix.utils.rational.LXRationalConverter` - Rational conversion

Solution:
  - :class:`lumix.solution.solution.LXSolution` - Solution container and access
  - :class:`lumix.solution.mapping.LXSolutionMapper` - Solution mapping utilities

Planned Sections
----------------

The following sections will be added in future updates:

Analysis Module
~~~~~~~~~~~~~~~

- ``LXSensitivityAnalyzer`` - Sensitivity analysis
- ``LXScenarioAnalyzer`` - Scenario analysis
- ``LXWhatIfAnalyzer`` - What-if analysis
- ``LXVariableSensitivity`` - Variable sensitivity results
- ``LXConstraintSensitivity`` - Constraint sensitivity results

Goal Programming Module
~~~~~~~~~~~~~~~~~~~~~~~~

- ``LXGoalProgrammingSolver`` - Goal programming solver
- ``LXGoal`` - Goal definition
- ``LXGoalMode`` - Weighted vs. sequential
- ``LXGoalMetadata`` - Goal metadata

Quick Reference
---------------

While we build the full API documentation, you can:

1. **Use IDE Autocomplete**: LumiX is fully type-annotated
2. **Check Docstrings**: All classes and methods have comprehensive docstrings
3. **Browse Source**: The source code is well-documented
4. **See Examples**: The examples directory shows practical usage

Example: Getting Help
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXModel

   # In Python, use help() to see docstrings
   help(LXModel)

.. code-block:: text

   # Or in IPython/Jupyter
   LXModel?

   # For method signatures
   LXModel.add_variable?

Coming Soon
-----------

Full auto-generated API documentation with:

- Complete class hierarchies
- Method signatures with types
- Comprehensive parameter descriptions
- Return value documentation
- Usage examples
- Cross-references
