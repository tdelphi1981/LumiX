Available Solvers
=================

LumiX provides a unified interface to multiple optimization solvers, allowing you to switch between them with a single line of code. This page provides an overview of each supported solver, their capabilities, and when to use them.

Solver Overview
---------------

LumiX currently supports five solvers:

1. **OR-Tools** - Google's free, open-source solver
2. **Gurobi** - Leading commercial solver with academic licenses
3. **CPLEX** - IBM's commercial solver with academic licenses
4. **GLPK** - GNU Linear Programming Kit (free, open-source)
5. **CP-SAT** - OR-Tools' constraint programming solver

Quick Comparison
----------------

.. list-table::
   :header-rows: 1
   :widths: 15 10 10 10 15 15 15 10

   * - Solver
     - Linear
     - Integer
     - Quadratic
     - Advanced Features
     - Performance
     - License
     - Best For
   * - **OR-Tools**
     - ✓
     - ✓
     - ✗
     - SOS1, SOS2, Indicator
     - Good
     - Free
     - General LP/MIP, Learning
   * - **Gurobi**
     - ✓
     - ✓
     - ✓
     - SOCP, PWL, Callbacks, IIS
     - Excellent
     - Commercial
     - Large-scale, Production
   * - **CPLEX**
     - ✓
     - ✓
     - ✓
     - SOCP, PWL, Callbacks, IIS
     - Excellent
     - Commercial
     - Large-scale, Production
   * - **GLPK**
     - ✓
     - ✓
     - ✗
     - Basic
     - Moderate
     - Free
     - Small problems, Teaching
   * - **CP-SAT**
     - ✗
     - ✓
     - ✗
     - Constraint Programming
     - Excellent
     - Free
     - Scheduling, Assignment

OR-Tools
--------

**Google's Operations Research Tools**

OR-Tools is Google's free, open-source optimization solver that provides a good balance of features and performance.

Key Features
~~~~~~~~~~~~

- **Linear Programming (LP)**: Continuous variable optimization
- **Mixed-Integer Programming (MIP)**: Integer and binary variables
- **Special Ordered Sets**: SOS1 and SOS2 constraints
- **Indicator Constraints**: Conditional constraints
- **Warm Start**: Use previous solutions to speed up solving
- **Parallel Solving**: Multi-threaded solution

Capabilities
~~~~~~~~~~~~

.. code-block:: python

   from lumix import ORTOOLS_CAPABILITIES

   print(ORTOOLS_CAPABILITIES.description())
   # OR-Tools: Linear Programming, Mixed-Integer Programming

Supported Features:

- ✓ Linear constraints
- ✓ Integer variables
- ✓ Binary variables
- ✓ SOS1 constraints
- ✓ SOS2 constraints
- ✓ Indicator constraints
- ✗ Quadratic programming
- ✗ Second-order cone programming
- ✗ Callbacks

Installation
~~~~~~~~~~~~

.. code-block:: bash

   pip install lumix[ortools]

Usage
~~~~~

.. code-block:: python

   from lumix import LXOptimizer

   optimizer = LXOptimizer().use_solver("ortools")
   solution = optimizer.solve(model)

When to Use
~~~~~~~~~~~

**Good For:**

- Learning optimization
- Prototyping models
- Small to medium-sized problems
- Budget-constrained projects
- Open-source requirements

**Not Ideal For:**

- Quadratic programming
- Very large-scale problems requiring maximum performance
- Problems requiring advanced callbacks

License
~~~~~~~

Apache License 2.0 (Free and open-source)

Gurobi
------

**The Leading Commercial Optimization Solver**

Gurobi is one of the fastest and most feature-rich commercial solvers available, with free academic licenses.

Key Features
~~~~~~~~~~~~

- **Linear Programming**: Industry-leading LP solver
- **Quadratic Programming**: Both convex and non-convex QP
- **Second-Order Cone Programming (SOCP)**: Advanced convex optimization
- **Piecewise-Linear Functions**: Native PWL support
- **Callbacks**: Custom heuristics and cuts
- **Irreducible Inconsistent Subsystem (IIS)**: Debugging infeasible models
- **Conflict Refinement**: Find minimal conflicts
- **Sensitivity Analysis**: Built-in sensitivity reporting

Capabilities
~~~~~~~~~~~~

.. code-block:: python

   from lumix import GUROBI_CAPABILITIES

   print(GUROBI_CAPABILITIES.description())
   # Gurobi: Linear Programming, Mixed-Integer Programming, Quadratic Programming,
   #         Second-Order Cone Programming

Supported Features:

- ✓ All linear features
- ✓ Quadratic (convex and non-convex)
- ✓ Second-order cone programming
- ✓ Piecewise-linear functions
- ✓ SOS1 and SOS2
- ✓ Indicator constraints
- ✓ Lazy constraints
- ✓ User cuts
- ✓ IIS and conflict refinement
- ✓ Sensitivity analysis
- ✓ Callbacks

Installation
~~~~~~~~~~~~

.. code-block:: bash

   pip install lumix[gurobi]

.. note::
   Requires a valid Gurobi license. Academic licenses are free and available at:
   https://www.gurobi.com/academia/

License Setup
~~~~~~~~~~~~~

1. Register for an academic license at https://www.gurobi.com/academia/
2. Download your license file
3. Activate the license:

   .. code-block:: bash

      grbgetkey YOUR-LICENSE-KEY

Usage
~~~~~

.. code-block:: python

   from lumix import LXOptimizer

   optimizer = LXOptimizer().use_solver("gurobi")
   solution = optimizer.solve(model)

When to Use
~~~~~~~~~~~

**Good For:**

- Production environments
- Large-scale optimization
- Quadratic programming
- Problems requiring maximum performance
- Advanced features (callbacks, IIS)
- Academic research (with free license)

**Not Ideal For:**

- Budget-constrained commercial projects
- Open-source distribution requirements

License
~~~~~~~

Commercial (free academic licenses available)

CPLEX
-----

**IBM's Flagship Optimization Solver**

CPLEX is IBM's commercial solver, comparable to Gurobi in features and performance, with free academic licenses.

Key Features
~~~~~~~~~~~~

Similar to Gurobi, CPLEX offers:

- **Linear Programming**: High-performance LP
- **Quadratic Programming**: Convex and non-convex QP
- **Second-Order Cone Programming**
- **Piecewise-Linear Functions**
- **Callbacks and Advanced Features**
- **IIS and Conflict Refinement**
- **Sensitivity Analysis**

Capabilities
~~~~~~~~~~~~

.. code-block:: python

   from lumix import CPLEX_CAPABILITIES

   print(CPLEX_CAPABILITIES.description())
   # CPLEX: Linear Programming, Mixed-Integer Programming, Quadratic Programming,
   #        Second-Order Cone Programming

Supported Features:

- ✓ All features similar to Gurobi
- ✓ Quadratic programming
- ✓ SOCP
- ✓ Callbacks
- ✓ IIS
- ✓ Sensitivity analysis

Installation
~~~~~~~~~~~~

.. code-block:: bash

   pip install lumix[cplex]

.. note::
   Requires a valid CPLEX license. Academic licenses are available through IBM Academic Initiative.

License Setup
~~~~~~~~~~~~~

1. Register for IBM Academic Initiative
2. Download and install CPLEX
3. The Python API will be available after installation

Usage
~~~~~

.. code-block:: python

   from lumix import LXOptimizer

   optimizer = LXOptimizer().use_solver("cplex")
   solution = optimizer.solve(model)

When to Use
~~~~~~~~~~~

**Good For:**

- Enterprise environments (especially if already using IBM tools)
- Large-scale optimization
- Academic research
- Advanced quadratic programming

**Not Ideal For:**

- Open-source projects
- Budget-constrained projects (without academic license)

License
~~~~~~~

Commercial (free academic licenses available through IBM Academic Initiative)

GLPK
----

**GNU Linear Programming Kit**

GLPK is a free, open-source solver suitable for small to medium-sized linear and integer programming problems.

Key Features
~~~~~~~~~~~~

- **Linear Programming**: Basic LP solver
- **Mixed-Integer Programming**: Integer and binary variables
- **Sensitivity Analysis**: Post-optimal analysis

Capabilities
~~~~~~~~~~~~

.. code-block:: python

   from lumix import GLPK_CAPABILITIES

   print(GLPK_CAPABILITIES.description())
   # GLPK: Linear Programming, Mixed-Integer Programming

Supported Features:

- ✓ Linear programming
- ✓ Integer variables
- ✓ Binary variables
- ✓ Sensitivity analysis
- ✗ Quadratic programming
- ✗ Advanced features (SOS, callbacks, etc.)
- ✗ Parallel solving

Installation
~~~~~~~~~~~~

.. code-block:: bash

   pip install lumix[glpk]

Usage
~~~~~

.. code-block:: python

   from lumix import LXOptimizer

   optimizer = LXOptimizer().use_solver("glpk")
   solution = optimizer.solve(model)

When to Use
~~~~~~~~~~~

**Good For:**

- Educational purposes
- Small problems
- GPL-compatible projects
- Proof-of-concept work

**Not Ideal For:**

- Large-scale problems
- Production environments requiring performance
- Quadratic programming
- Problems requiring parallel solving

License
~~~~~~~

GNU General Public License (GPL) - Free and open-source

.. warning::
   GLPK uses GPL license, which has viral copyleft provisions. Ensure compatibility with your project's license.

CP-SAT
------

**OR-Tools Constraint Programming Solver**

CP-SAT is a specialized constraint programming solver, excellent for scheduling and assignment problems.

Key Features
~~~~~~~~~~~~

- **Integer Programming**: Integer and binary variables only (no continuous)
- **Constraint Programming**: Advanced CP techniques
- **Excellent for Scheduling**: Built for assignment and scheduling
- **Parallel Search**: Highly parallel solution strategies
- **Solution Hints**: Warm-start with previous solutions

Capabilities
~~~~~~~~~~~~

.. code-block:: python

   from lumix import CPSAT_CAPABILITIES

   print(CPSAT_CAPABILITIES.description())
   # OR-Tools CP-SAT: Mixed-Integer Programming

Supported Features:

- ✓ Integer variables
- ✓ Binary variables
- ✓ Warm start (solution hints)
- ✓ Parallel solving
- ✗ Continuous variables
- ✗ Quadratic programming

Installation
~~~~~~~~~~~~

.. code-block:: bash

   pip install lumix[ortools]

CP-SAT is included with OR-Tools.

Usage
~~~~~

.. code-block:: python

   from lumix import LXOptimizer

   optimizer = LXOptimizer().use_solver("cpsat")
   solution = optimizer.solve(model)

When to Use
~~~~~~~~~~~

**Good For:**

- Scheduling problems
- Assignment problems
- Pure integer/binary problems
- Problems with complex logical constraints

**Not Ideal For:**

- Problems with continuous variables
- Linear relaxations
- Quadratic programming

License
~~~~~~~

Apache License 2.0 (Free and open-source)

Solver Selection Guide
----------------------

Choose the right solver for your problem:

.. mermaid::

   graph TD
       A[Start] --> B{Need Continuous Variables?}
       B -->|No| C{Free or Commercial?}
       B -->|Yes| D{Need Quadratic?}

       C -->|Free| E[CP-SAT]
       C -->|Commercial OK| F{Budget?}

       D -->|Yes| G{License Available?}
       D -->|No| H{Problem Size?}

       F -->|Academic| I[Gurobi/CPLEX]
       F -->|Commercial| I

       G -->|Yes| I
       G -->|No| J[Use Linearization<br/>+ OR-Tools]

       H -->|Small/Medium| K[OR-Tools]
       H -->|Large| L[Gurobi/CPLEX<br/>if possible]
       H -->|Very Small| M[GLPK]

By Problem Type
~~~~~~~~~~~~~~~

**Linear Programming (LP)**

- Best: Gurobi, CPLEX
- Good: OR-Tools
- Basic: GLPK

**Mixed-Integer Programming (MIP)**

- Best: Gurobi, CPLEX
- Good: OR-Tools
- Basic: GLPK, CP-SAT

**Quadratic Programming (QP)**

- Best: Gurobi, CPLEX
- Alternative: Use LumiX linearization + OR-Tools

**Scheduling/Assignment**

- Best: CP-SAT
- Alternative: OR-Tools, Gurobi, CPLEX

**Large-Scale Production**

- Best: Gurobi, CPLEX
- Budget-Friendly: OR-Tools

Performance Comparison
----------------------

General performance characteristics (problem-dependent):

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 20 20

   * - Problem Type
     - Gurobi/CPLEX
     - OR-Tools
     - GLPK
     - CP-SAT
   * - Small LP
     - Excellent
     - Excellent
     - Good
     - N/A
   * - Large LP
     - Excellent
     - Good
     - Poor
     - N/A
   * - Small MIP
     - Excellent
     - Good
     - Moderate
     - Excellent
   * - Large MIP
     - Excellent
     - Good
     - Poor
     - Good
   * - Quadratic
     - Excellent
     - N/A
     - N/A
     - N/A
   * - Scheduling
     - Excellent
     - Good
     - Poor
     - Excellent

.. note::
   Performance is highly problem-dependent. Always benchmark with your specific problem.

Automatic Linearization
-----------------------

LumiX can automatically linearize non-linear terms for solvers that don't support them natively:

.. code-block:: python

   from lumix import LXLinearizer, LXLinearizerConfig

   # Configure linearization
   config = LXLinearizerConfig(
       method="mccormick",  # For bilinear terms
       num_segments=10,     # For piecewise-linear approximations
   )

   linearizer = LXLinearizer(config)
   linear_model = linearizer.linearize(model)

   # Now solve with any solver
   optimizer = LXOptimizer().use_solver("ortools")
   solution = optimizer.solve(linear_model)

This allows you to use free solvers even for problems with non-linear terms.

Detailed Usage Guides
---------------------

.. note::
   Detailed solver-specific usage guides, configuration options, and advanced features will be added in future documentation updates.

Next Steps
----------

- :doc:`installation` - Install your chosen solver
- :doc:`quickstart` - Build your first model
- **Examples** - See solver-specific examples in the repository
