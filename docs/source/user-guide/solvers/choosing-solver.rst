Choosing a Solver
=================

This guide helps you choose the right solver for your optimization problem.

Quick Decision Tree
-------------------

.. mermaid::

   graph TD
       A[Start] --> B{Need Continuous Variables?}
       B -->|No| C{Budget/License?}
       B -->|Yes| D{Need Quadratic/SOCP?}

       C -->|Free| E[CP-SAT<br/>Best for Scheduling]
       C -->|Commercial OK| F{Academic?}

       D -->|Yes| G{License Available?}
       D -->|No| H{Problem Size?}

       F -->|Yes| I[Gurobi or CPLEX<br/>Free Academic License]
       F -->|No| I

       G -->|Yes| I
       G -->|No| J[Use Linearization<br/>+ OR-Tools]

       H -->|Small/Medium| K[OR-Tools<br/>Free, Good Performance]
       H -->|Large| L[Gurobi/CPLEX<br/>Best Performance]
       H -->|Very Small| M[GLPK<br/>Basic, Free]

       style E fill:#90EE90
       style I fill:#FFD700
       style J fill:#87CEEB
       style K fill:#90EE90
       style L fill:#FFD700
       style M fill:#DDA0DD

Decision Factors
----------------

1. Problem Type
~~~~~~~~~~~~~~~

**Linear Programming (LP)**

Only continuous variables, linear constraints:

.. code-block:: python

   # Example: Portfolio optimization
   max: profit_A * x_A + profit_B * x_B
   s.t.: x_A + x_B <= budget
         x_A, x_B >= 0  (continuous)

**Recommendation:**

- Best: Gurobi, CPLEX
- Good: OR-Tools
- Basic: GLPK

**Mixed-Integer Programming (MIP)**

Mix of continuous and integer/binary variables:

.. code-block:: python

   # Example: Facility location
   max: revenue - fixed_cost * is_open
   s.t.: is_open in {0, 1}  (binary)
         production >= 0     (continuous)

**Recommendation:**

- Best: Gurobi, CPLEX
- Good: OR-Tools
- Basic: GLPK (small problems), CP-SAT (integer only)

**Quadratic Programming (QP)**

Quadratic objective or constraints:

.. code-block:: python

   # Example: Variance minimization
   min: x^T * Covariance * x
   s.t.: sum(x) = 1

**Recommendation:**

- Best: Gurobi, CPLEX
- Alternative: OR-Tools with linearization

**Scheduling/Assignment**

Pure integer assignment problems:

.. code-block:: python

   # Example: Employee scheduling
   assign[worker, shift] in {0, 1}
   s.t.: sum(assign[w, s] for s in shifts) <= 5  # Max 5 shifts per worker

**Recommendation:**

- Best: CP-SAT (designed for this)
- Alternative: Gurobi, CPLEX, OR-Tools

2. Budget and Licensing
~~~~~~~~~~~~~~~~~~~~~~~~

**Free and Open-Source**

**OR-Tools**

- License: Apache 2.0 (permissive)
- Cost: Free
- Best for: Most LP/MIP problems
- Performance: Good

**GLPK**

- License: GPL v3 (copyleft)
- Cost: Free
- Best for: Small problems, teaching
- Performance: Moderate
- **Warning:** GPL license has viral copyleft provisions

**CP-SAT**

- License: Apache 2.0 (permissive)
- Cost: Free
- Best for: Integer programming, scheduling
- Performance: Excellent (for its domain)

**Commercial with Academic Licenses**

**Gurobi**

- License: Commercial (free academic)
- Cost: Free for academic use, commercial pricing for businesses
- Best for: Large-scale, production, research
- Performance: Excellent
- Get academic license: https://www.gurobi.com/academia/

**CPLEX**

- License: Commercial (free academic via IBM Academic Initiative)
- Cost: Free for academic use, commercial pricing for businesses
- Best for: Enterprise, academic research
- Performance: Excellent
- Get academic license: IBM Academic Initiative

3. Problem Size
~~~~~~~~~~~~~~~

**Small Problems** (<1000 variables, <1000 constraints)

All solvers work well:

- OR-Tools: Good default
- GLPK: Acceptable for simple problems
- CP-SAT: Excellent for integer problems
- Gurobi/CPLEX: Overkill but work perfectly

**Medium Problems** (1K-100K variables/constraints)

- **Best:** Gurobi, CPLEX
- **Good:** OR-Tools
- **Avoid:** GLPK (too slow)

**Large Problems** (>100K variables/constraints)

- **Best:** Gurobi, CPLEX (commercial features, parallel solving)
- **Acceptable:** OR-Tools (may be slower)
- **Avoid:** GLPK, CP-SAT

4. Required Features
~~~~~~~~~~~~~~~~~~~~

**Quadratic Programming**

- **Native support:** Gurobi, CPLEX only
- **Via linearization:** OR-Tools, GLPK (with LumiX linearization)

**Second-Order Cone Programming (SOCP)**

- **Supported:** Gurobi, CPLEX
- **Not supported:** OR-Tools, GLPK, CP-SAT

**Piecewise-Linear Functions**

- **Native:** Gurobi, CPLEX
- **Via linearization:** OR-Tools, GLPK (with LumiX)

**SOS Constraints (SOS1, SOS2)**

- **Supported:** Gurobi, CPLEX, OR-Tools
- **Not supported:** GLPK, CP-SAT

**Indicator Constraints**

- **Supported:** Gurobi, CPLEX, OR-Tools
- **Not supported:** GLPK

**Sensitivity Analysis**

- **Supported:** Gurobi, CPLEX, GLPK
- **Not supported:** OR-Tools, CP-SAT

**Callbacks (Lazy Constraints, Cuts)**

- **Supported:** Gurobi, CPLEX
- **Not supported:** OR-Tools, GLPK, CP-SAT

**Warm Start**

- **Supported:** Gurobi, CPLEX, OR-Tools, CP-SAT
- **Not supported:** GLPK

5. Performance Requirements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Interactive/Real-Time** (sub-second response)

- Gurobi, CPLEX (best)
- OR-Tools (good for smaller problems)
- CP-SAT (excellent for scheduling)

**Batch Processing** (minutes acceptable)

- Any solver works
- Consider OR-Tools to save licensing costs

**Production Systems** (reliability critical)

- Gurobi, CPLEX (proven, supported)
- OR-Tools (good, but less enterprise support)

Solver Comparison
-----------------

Feature Matrix
~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 15 15 20

   * - Feature
     - OR-Tools
     - Gurobi
     - CPLEX
     - GLPK
     - CP-SAT
   * - **Linear (LP)**
     - ✓
     - ✓
     - ✓
     - ✓
     - ✗
   * - **Integer (MIP)**
     - ✓
     - ✓
     - ✓
     - ✓
     - ✓ (only)
   * - **Quadratic**
     - ✗
     - ✓
     - ✓
     - ✗
     - ✗
   * - **SOCP**
     - ✗
     - ✓
     - ✓
     - ✗
     - ✗
   * - **SOS1/SOS2**
     - ✓
     - ✓
     - ✓
     - ✗
     - ✗
   * - **Indicator**
     - ✓
     - ✓
     - ✓
     - ✗
     - ✗
   * - **PWL**
     - ✗
     - ✓
     - ✓
     - ✗
     - ✗
   * - **Sensitivity**
     - ✗
     - ✓
     - ✓
     - ✓
     - ✗
   * - **Callbacks**
     - ✗
     - ✓
     - ✓
     - ✗
     - ✗
   * - **Warm Start**
     - ✓
     - ✓
     - ✓
     - ✗
     - ✓
   * - **Parallel**
     - ✓
     - ✓
     - ✓
     - ✗
     - ✓
   * - **License**
     - Free
     - Commercial
     - Commercial
     - Free (GPL)
     - Free

Performance Comparison
~~~~~~~~~~~~~~~~~~~~~~

Relative performance (problem-dependent):

.. list-table::
   :header-rows: 1
   :widths: 25 15 15 15 15 15

   * - Problem Type
     - OR-Tools
     - Gurobi
     - CPLEX
     - GLPK
     - CP-SAT
   * - Small LP
     - 9/10
     - 10/10
     - 10/10
     - 7/10
     - N/A
   * - Large LP
     - 7/10
     - 10/10
     - 10/10
     - 3/10
     - N/A
   * - Small MIP
     - 8/10
     - 10/10
     - 10/10
     - 6/10
     - 9/10
   * - Large MIP
     - 7/10
     - 10/10
     - 10/10
     - 2/10
     - 7/10
   * - Quadratic
     - N/A
     - 10/10
     - 10/10
     - N/A
     - N/A
   * - Scheduling
     - 7/10
     - 10/10
     - 10/10
     - 3/10
     - 10/10

Practical Recommendations
--------------------------

By Use Case
~~~~~~~~~~~

**Academic Research**

.. code-block:: python

   # Get free Gurobi academic license
   optimizer = LXOptimizer().use_solver("gurobi")

**Why?**

- Free for academic use
- Best performance
- Full features (sensitivity, callbacks)
- Industry-standard for publications

**Startup/Small Business**

.. code-block:: python

   # Start with OR-Tools
   optimizer = LXOptimizer().use_solver("ortools")

**Why?**

- No licensing costs
- Good performance for most problems
- Can upgrade to Gurobi/CPLEX later if needed

**Enterprise**

.. code-block:: python

   # Use Gurobi or CPLEX
   optimizer = LXOptimizer().use_solver("gurobi")

**Why?**

- Best performance
- Professional support
- Proven reliability
- Worth the cost for business-critical applications

**Open-Source Project**

.. code-block:: python

   # Use OR-Tools (Apache 2.0 license)
   optimizer = LXOptimizer().use_solver("ortools")

**Why?**

- Permissive license (no copyleft)
- No commercial restrictions
- Avoid GLPK's GPL restrictions

**Teaching/Learning**

.. code-block:: python

   # OR-Tools or GLPK
   optimizer = LXOptimizer().use_solver("ortools")

**Why?**

- Free
- Easy to install
- Good for learning concepts

**Scheduling/Rostering**

.. code-block:: python

   # Use CP-SAT
   optimizer = LXOptimizer().use_solver("cpsat")

**Why?**

- Designed for scheduling problems
- Excellent performance
- Free
- Handles complex logical constraints

Migration Strategy
~~~~~~~~~~~~~~~~~~

Start Small, Scale Up
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Phase 1: Prototype with OR-Tools (free)
   optimizer = LXOptimizer().use_solver("ortools")
   solution = optimizer.solve(prototype_model)

   # Phase 2: Test with Gurobi academic license
   optimizer = LXOptimizer().use_solver("gurobi")
   solution = optimizer.solve(full_model)

   # Phase 3: Production with commercial Gurobi
   optimizer = LXOptimizer().use_solver("gurobi")
   solution = optimizer.solve(production_model, Threads=32)

Graceful Degradation
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   def get_best_available_solver():
       """Try solvers in order of preference."""
       try:
           return LXOptimizer().use_solver("gurobi")
       except ImportError:
           try:
               return LXOptimizer().use_solver("cplex")
           except ImportError:
               # Fall back to free solver
               return LXOptimizer().use_solver("ortools")

   optimizer = get_best_available_solver()

Benchmarking
~~~~~~~~~~~~

Always benchmark with your specific problem:

.. code-block:: python

   import time

   solvers = ["ortools", "gurobi", "cplex"]
   results = {}

   for solver_name in solvers:
       try:
           optimizer = LXOptimizer().use_solver(solver_name)
           start = time.time()
           solution = optimizer.solve(model, time_limit=300)
           elapsed = time.time() - start

           results[solver_name] = {
               "time": elapsed,
               "objective": solution.objective_value,
               "status": solution.status
           }
       except ImportError:
           print(f"{solver_name} not available")

   # Compare results
   for solver, result in results.items():
       print(f"{solver}: {result['time']:.2f}s, obj={result['objective']:.2f}")

Common Scenarios
----------------

Scenario 1: Student Project
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Requirements:**

- Free
- Learn optimization
- Small problems

**Recommendation:** OR-Tools

.. code-block:: python

   optimizer = LXOptimizer().use_solver("ortools")

Scenario 2: PhD Research
~~~~~~~~~~~~~~~~~~~~~~~~~

**Requirements:**

- Academic use
- Need best performance
- Publish results

**Recommendation:** Gurobi (free academic license)

.. code-block:: python

   optimizer = LXOptimizer().use_solver("gurobi")

Scenario 3: SaaS Product
~~~~~~~~~~~~~~~~~~~~~~~~~

**Requirements:**

- Cost-sensitive
- Medium-scale problems
- Need reliability

**Recommendation:** OR-Tools initially, evaluate Gurobi if performance becomes issue

.. code-block:: python

   # Start with OR-Tools
   optimizer = LXOptimizer().use_solver("ortools")

   # Upgrade path if needed:
   # optimizer = LXOptimizer().use_solver("gurobi")

Scenario 4: Enterprise Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Requirements:**

- Large-scale
- Production-critical
- Need support

**Recommendation:** Gurobi or CPLEX

.. code-block:: python

   optimizer = LXOptimizer().use_solver("gurobi")
   solution = optimizer.solve(model, Threads=64, time_limit=3600)

Scenario 5: Employee Scheduling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Requirements:**

- Complex logical constraints
- Integer variables only
- Free solution preferred

**Recommendation:** CP-SAT

.. code-block:: python

   optimizer = (
       LXOptimizer()
       .use_solver("cpsat")
       .enable_rational_conversion()  # For any float coefficients
   )

Next Steps
----------

- :doc:`using-optimizer` - How to use the optimizer
- :doc:`solver-configuration` - Configure solver parameters
- :doc:`solver-capabilities` - Understanding capabilities
- :doc:`/getting-started/solvers` - Installation and setup
- :doc:`/api/solvers/index` - API reference
