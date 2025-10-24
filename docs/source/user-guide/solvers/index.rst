Using Solvers
=============

This guide covers how to use LumiX's unified solver interface to solve optimization models with different solvers.

Introduction
------------

LumiX provides a **solver-agnostic interface** that allows you to:

- Switch between solvers with a single line of code
- Leverage solver-specific features when needed
- Use the same model with different solvers
- Automatically detect solver capabilities

Philosophy
----------

Traditional Approach (Solver-Specific)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Traditional optimization libraries require solver-specific code:

.. code-block:: python

   # Gurobi-specific code
   import gurobipy as gp
   m = gp.Model()
   x = m.addVar(name="x")
   m.setObjective(x, GRB.MAXIMIZE)
   m.optimize()

   # Can't easily switch to CPLEX without rewriting

LumiX Approach (Solver-Agnostic)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

LumiX uses a unified interface:

.. code-block:: python

   from lumix import LXModel, LXOptimizer

   # Build model once
   model = LXModel("example").add_variable(x).maximize(obj)

   # Switch solvers with one line
   optimizer = LXOptimizer().use_solver("gurobi")
   # optimizer = LXOptimizer().use_solver("ortools")
   # optimizer = LXOptimizer().use_solver("cplex")

   solution = optimizer.solve(model)

**Benefits:**

- ✓ Write once, solve anywhere
- ✓ Easy to compare solver performance
- ✓ Graceful degradation (free → commercial)
- ✓ Capability-aware automatic linearization

Core Components
---------------

The solvers module consists of three main components:

.. mermaid::

   graph LR
       A[Your Model] --> B[LXOptimizer]
       B --> C[LXSolverInterface]
       C --> D[Solver Implementation]
       E[LXSolverCapability] --> C

       style A fill:#e8f4f8
       style B fill:#e1f5ff
       style C fill:#fff4e1
       style D fill:#e1ffe1
       style E fill:#ffe1e1

1. **LXOptimizer**: High-level interface for configuring and solving models
2. **LXSolverInterface**: Abstract base class defining solver contract
3. **Solver Implementations**: Concrete implementations for each solver (OR-Tools, Gurobi, CPLEX, GLPK, CP-SAT)
4. **LXSolverCapability**: Describes what features each solver supports

Quick Start
-----------

Basic Usage
~~~~~~~~~~~

.. code-block:: python

   from lumix import LXModel, LXOptimizer

   # Build your model
   model = build_production_model(products)

   # Create optimizer and select solver
   optimizer = LXOptimizer().use_solver("ortools")

   # Solve
   solution = optimizer.solve(model)

   # Access results
   if solution.is_optimal():
       print(f"Objective: {solution.objective_value}")
       for var_name, value in solution.variable_values.items():
           print(f"{var_name} = {value}")

Solver Selection
~~~~~~~~~~~~~~~~

Choose a solver based on your needs:

.. code-block:: python

   # Free, open-source (good for most problems)
   optimizer = LXOptimizer().use_solver("ortools")

   # Commercial, high-performance (best for large problems)
   optimizer = LXOptimizer().use_solver("gurobi")
   optimizer = LXOptimizer().use_solver("cplex")

   # Free, basic (small problems only)
   optimizer = LXOptimizer().use_solver("glpk")

   # Constraint programming (scheduling/assignment)
   optimizer = LXOptimizer().use_solver("cpsat")

Solver Parameters
~~~~~~~~~~~~~~~~~

Pass solver-specific parameters:

.. code-block:: python

   # Gurobi example
   solution = optimizer.solve(
       model,
       time_limit=300,        # 5 minutes
       gap_tolerance=0.01,    # 1% gap
       Threads=4,             # Use 4 threads
       MIPFocus=1,            # Focus on feasibility
       LogToConsole=1,        # Show solver log
   )

Components Details
------------------

LXOptimizer
~~~~~~~~~~~

The main interface for solving models:

**Key Methods:**

- ``use_solver(name)``: Select solver ("ortools", "gurobi", "cplex", "glpk", "cpsat")
- ``enable_rational_conversion()``: Convert floats to rationals for integer solvers
- ``enable_linearization()``: Automatically linearize nonlinear terms
- ``enable_sensitivity()``: Enable sensitivity analysis
- ``solve(model, **params)``: Solve the model

**Example:**

.. code-block:: python

   optimizer = (
       LXOptimizer()
       .use_solver("gurobi")
       .enable_sensitivity()
       .enable_rational_conversion()
   )

   solution = optimizer.solve(model, time_limit=600)

Solver Capabilities
~~~~~~~~~~~~~~~~~~~

Query what features a solver supports:

.. code-block:: python

   from lumix import GUROBI_CAPABILITIES, ORTOOLS_CAPABILITIES

   # Check capabilities
   print(GUROBI_CAPABILITIES.description())
   # Gurobi: Linear Programming, Mixed-Integer Programming,
   #         Quadratic Programming, Second-Order Cone Programming

   # Check specific features
   if GUROBI_CAPABILITIES.can_solve_quadratic():
       print("Gurobi supports quadratic programming")

   if ORTOOLS_CAPABILITIES.needs_linearization_for_bilinear():
       print("OR-Tools needs linearization for x*y products")

Automatic Linearization
~~~~~~~~~~~~~~~~~~~~~~~

LumiX can automatically linearize nonlinear terms for solvers that don't support them:

.. code-block:: python

   from lumix import LXOptimizer

   # Model with bilinear terms (x * y)
   model = build_model_with_bilinear_terms()

   # Enable automatic linearization
   optimizer = (
       LXOptimizer()
       .use_solver("ortools")  # Doesn't support quadratic
       .enable_linearization(
           big_m=1e6,
           pwl_segments=20,
           mccormick_tighten_bounds=True
       )
   )

   # Solver automatically linearizes bilinear terms
   solution = optimizer.solve(model)

Guide Sections
--------------

.. toctree::
   :maxdepth: 2

   using-optimizer
   choosing-solver
   solver-configuration
   solver-capabilities
   advanced-features

Next Steps
----------

- :doc:`using-optimizer` - Detailed guide on using the LXOptimizer class
- :doc:`choosing-solver` - How to choose the right solver for your problem
- :doc:`solver-configuration` - Configuring solver parameters
- :doc:`solver-capabilities` - Understanding solver capabilities
- :doc:`advanced-features` - Advanced features (warm start, callbacks, sensitivity)
- :doc:`/getting-started/solvers` - Solver comparison and installation
- :doc:`/api/solvers/index` - Complete API reference
