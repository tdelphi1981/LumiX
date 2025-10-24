Solvers Module API
==================

The solvers module provides a unified interface to multiple optimization solvers, enabling you to switch between different solvers with a single line of code.

Overview
--------

The solvers module implements a **solver-agnostic optimization interface** through three main components:

.. mermaid::

   graph TD
       A[LXOptimizer] --> B[LXSolverInterface]
       B --> C[LXORToolsSolver]
       B --> D[LXGurobiSolver]
       B --> E[LXCPLEXSolver]
       B --> F[LXGLPKSolver]
       B --> G[LXCPSATSolver]
       H[LXSolverCapability] --> B
       I[LXSolverFeature] --> H

       style A fill:#e1f5ff
       style B fill:#fff4e1
       style C fill:#e1ffe1
       style D fill:#e1ffe1
       style E fill:#e1ffe1
       style F fill:#e1ffe1
       style G fill:#e1ffe1
       style H fill:#ffe1e1
       style I fill:#f0e1ff

Components
----------

Optimizer
~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.solvers.base.LXOptimizer

The :class:`~lumix.solvers.base.LXOptimizer` class provides the high-level interface for solving optimization models with configurable solver selection and options.

Solver Interface
~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.solvers.base.LXSolverInterface

The :class:`~lumix.solvers.base.LXSolverInterface` abstract base class defines the contract that all solver implementations must follow.

Solver Implementations
~~~~~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.solvers.ortools_solver.LXORToolsSolver
   lumix.solvers.gurobi_solver.LXGurobiSolver
   lumix.solvers.cplex_solver.LXCPLEXSolver
   lumix.solvers.glpk_solver.LXGLPKSolver
   lumix.solvers.cpsat_solver.LXCPSATSolver

Solver implementations for different optimization engines:

- :class:`~lumix.solvers.ortools_solver.LXORToolsSolver` - Google OR-Tools solver (free)
- :class:`~lumix.solvers.gurobi_solver.LXGurobiSolver` - Gurobi commercial solver
- :class:`~lumix.solvers.cplex_solver.LXCPLEXSolver` - IBM CPLEX commercial solver
- :class:`~lumix.solvers.glpk_solver.LXGLPKSolver` - GNU Linear Programming Kit (free)
- :class:`~lumix.solvers.cpsat_solver.LXCPSATSolver` - OR-Tools CP-SAT constraint programming solver

Capability Management
~~~~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.solvers.capabilities.LXSolverCapability
   lumix.solvers.capabilities.LXSolverFeature

Capability detection and feature flags:

- :class:`~lumix.solvers.capabilities.LXSolverCapability` - Describes solver capabilities
- :class:`~lumix.solvers.capabilities.LXSolverFeature` - Feature flags for solver capabilities

Pre-defined Capabilities
~~~~~~~~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.solvers.capabilities.ORTOOLS_CAPABILITIES
   lumix.solvers.capabilities.GUROBI_CAPABILITIES
   lumix.solvers.capabilities.CPLEX_CAPABILITIES
   lumix.solvers.capabilities.GLPK_CAPABILITIES
   lumix.solvers.capabilities.CPSAT_CAPABILITIES

Pre-configured capability objects for each supported solver.

Detailed API Reference
----------------------

Optimizer
~~~~~~~~~

.. automodule:: lumix.solvers.base
   :members: LXOptimizer
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

Solver Interface
~~~~~~~~~~~~~~~~

.. automodule:: lumix.solvers.base
   :members: LXSolverInterface
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

OR-Tools Solver
~~~~~~~~~~~~~~~

.. automodule:: lumix.solvers.ortools_solver
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

Gurobi Solver
~~~~~~~~~~~~~

.. automodule:: lumix.solvers.gurobi_solver
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

CPLEX Solver
~~~~~~~~~~~~

.. automodule:: lumix.solvers.cplex_solver
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

GLPK Solver
~~~~~~~~~~~

.. automodule:: lumix.solvers.glpk_solver
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

CP-SAT Solver
~~~~~~~~~~~~~

.. automodule:: lumix.solvers.cpsat_solver
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

Capabilities
~~~~~~~~~~~~

.. automodule:: lumix.solvers.capabilities
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:
