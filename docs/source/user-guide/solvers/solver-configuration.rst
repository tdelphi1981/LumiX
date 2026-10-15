Solver Configuration
====================

This guide covers how to configure solver-specific parameters for optimal performance.

Overview
--------

All solvers support common parameters through the ``solve()`` method:

.. code-block:: python

   solution = optimizer.solve(
       model,
       time_limit=300,        # Common: time limit in seconds
       gap_tolerance=0.01,    # Common: MIP gap tolerance
       **solver_params         # Solver-specific parameters
   )

Common Parameters
-----------------

These parameters work across all solvers. Any other keyword argument is passed
to the selected solver; unknown names are ignored with a warning (enable LumiX's
log with ``lumix.enable_logging()`` to see it).

time_limit
~~~~~~~~~~

Maximum solve time in seconds:

.. code-block:: python

   # Stop after 5 minutes
   solution = optimizer.solve(model, time_limit=300)

**Type:** ``float`` or ``None``

**Default:** ``None`` (no limit)

**Recommendation:**

- Always set for MIP problems (can run indefinitely)
- LP problems usually solve quickly (time limit optional)

gap_tolerance
~~~~~~~~~~~~~

MIP gap tolerance (relative):

.. code-block:: python

   # Stop when within 1% of optimal
   solution = optimizer.solve(model, gap_tolerance=0.01)

**Type:** ``float`` or ``None``

**Default:** ``None`` (solver default, typically 0.0001 = 0.01%)

**Formula:** ``gap = |bestbound - bestobj| / |bestobj|``

**Recommendation:**

- 0.01 (1%) - Good for most practical problems
- 0.001 (0.1%) - When near-optimal solution needed
- 0.0001 (0.01%) - Default, prove optimality
- 0.05 (5%) - Quick feasible solution acceptable

enable_sensitivity
~~~~~~~~~~~~~~~~~~

Enable sensitivity analysis on the optimizer (not as a ``solve()`` argument):

.. code-block:: python

   optimizer = LXOptimizer().use_solver("ortools").enable_sensitivity()
   solution = optimizer.solve(model)

   # Access results
   shadow_prices = solution.shadow_prices
   reduced_costs = solution.reduced_costs

**Default:** off

**Note:** Shadow prices and reduced costs are reported for LPs by OR-Tools,
Gurobi, CPLEX and GLPK; CP-SAT and MIPs have none.

Solver-Specific Parameters
---------------------------

OR-Tools
~~~~~~~~

The ``"ortools"`` adapter (GLOP for LPs, SCIP for MIPs) takes one extra
parameter besides ``time_limit`` and ``gap_tolerance``:

.. code-block:: python

   solution = optimizer.solve(
       model,
       threads=4  # Number of threads
   )

Other names are ignored with a warning. CP-SAT parameters such as
``num_search_workers`` belong to the ``"cpsat"`` solver (see the CP-SAT section below).

Gurobi
~~~~~~

Gurobi has the most extensive parameter set. Use Gurobi parameter names directly.

.. versionchanged:: 0.3.0
   Gurobi's log is off by default; pass ``verbose=True`` or ``LogToConsole=1``
   (to ``solve()`` or ``use_solver("gurobi", ...)``) to print it.

Parameter names:

**Threading:**

.. code-block:: python

   solution = optimizer.solve(
       model,
       Threads=8  # Use 8 threads
   )

**MIP Focus:**

.. code-block:: python

   solution = optimizer.solve(
       model,
       MIPFocus=1  # 0=balanced, 1=feasibility, 2=optimality, 3=bound
   )

**Presolve:**

.. code-block:: python

   solution = optimizer.solve(
       model,
       Presolve=2  # -1=auto, 0=off, 1=conservative, 2=aggressive
   )

**Algorithm Selection:**

.. code-block:: python

   solution = optimizer.solve(
       model,
       Method=-1  # -1=auto, 0=primal simplex, 1=dual simplex, 2=barrier
   )

**Logging:**

.. code-block:: python

   solution = optimizer.solve(
       model,
       LogToConsole=1,  # 0=off, 1=on
       LogFile="solve.log"  # Write log to file
   )

**Common Configurations:**

**Fast Feasible Solution:**

.. code-block:: python

   solution = optimizer.solve(
       model,
       MIPFocus=1,          # Focus on feasibility
       Heuristics=0.5,      # 50% time on heuristics
       Presolve=2,          # Aggressive presolve
       Cuts=0,              # Disable cuts
       gap_tolerance=0.05,  # Accept 5% gap
   )

**Prove Optimality:**

.. code-block:: python

   solution = optimizer.solve(
       model,
       MIPFocus=2,          # Focus on optimality
       Heuristics=0.01,     # Minimal heuristics
       Presolve=2,          # Aggressive presolve
       Cuts=2,              # Aggressive cuts
       gap_tolerance=0.0001,
   )

**Large-Scale Parallel:**

.. code-block:: python

   solution = optimizer.solve(
       model,
       Threads=32,          # Use all cores
       Method=2,            # Barrier method for LP
       Crossover=0,         # Skip crossover (barrier only)
       BarConvTol=1e-4,     # Barrier convergence
   )

**Full Parameter List:**

.. code-block:: python

   solution = optimizer.solve(
       model,
       # Performance
       Threads=8,
       Method=-1,
       Presolve=2,

       # MIP Settings
       MIPFocus=0,
       Heuristics=0.05,
       Cuts=2,
       NodeMethod=1,

       # Tolerances
       MIPGap=0.0001,
       IntFeasTol=1e-5,
       FeasibilityTol=1e-6,
       OptimalityTol=1e-6,

       # Logging
       LogToConsole=1,
       LogFile="gurobi.log",
       DisplayInterval=5,

       # Advanced
       ImproveStartTime=600,
       ImproveStartGap=0.1,
   )

CPLEX
~~~~~

CPLEX parameters are named by their path in ``cplex.Cplex().parameters``
with ``_`` for ``.``: ``mip_limits_cutsfactor`` sets
``parameters.mip.limits.cutsfactor`` and ``emphasis_mip`` sets
``parameters.emphasis.mip``. Pass ``verbose=True`` to print the CPLEX log
(``output_clonelog`` controls clone log files and does not show the log).

**Threading:**

.. code-block:: python

   solution = optimizer.solve(
       model,
       threads=8  # Number of threads
   )

**MIP Emphasis:**

.. code-block:: python

   solution = optimizer.solve(
       model,
       emphasis_mip=1  # 0=balanced, 1=feasibility, 2=optimality, 3=bound, 4=hidden
   )

**Presolve:**

.. code-block:: python

   solution = optimizer.solve(
       model,
       preprocessing_presolve=1  # 0=off, 1=on
   )

**Algorithm:**

.. code-block:: python

   solution = optimizer.solve(
       model,
       lpmethod=0  # 0=auto, 1=primal, 2=dual, 3=network, 4=barrier
   )

**Common Configurations:**

**Fast Feasible:**

.. code-block:: python

   solution = optimizer.solve(
       model,
       emphasis_mip=1,              # Feasibility
       preprocessing_presolve=1,    # Presolve on
       mip_limits_cutsfactor=0,     # No cuts
       gap_tolerance=0.05,
   )

**Prove Optimality:**

.. code-block:: python

   solution = optimizer.solve(
       model,
       emphasis_mip=2,              # Optimality
       preprocessing_presolve=1,
       mip_cuts_mircut=2,           # Aggressive MIR cuts
       gap_tolerance=0.0001,
   )

GLPK
~~~~

GLPK has limited configurability. Use the common ``time_limit`` and
``gap_tolerance`` parameters; the GLPK-specific ones are ``msg_lev``,
``presolve`` and ``method``:

**Basic Parameters:**

.. code-block:: python

   import swiglpk as glpk

   solution = optimizer.solve(
       model,
       time_limit=300,              # seconds
       gap_tolerance=0.01,          # MIP gap tolerance
       msg_lev=glpk.GLP_MSG_ON,     # GLPK log (default: glpk.GLP_MSG_OFF)
       presolve=True,               # default
   )

CP-SAT
~~~~~~

CP-SAT (Constraint Programming):

**Threading:**

.. code-block:: python

   solution = optimizer.solve(
       model,
       num_search_workers=8  # Parallel workers
   )

**Search Strategy:**

.. code-block:: python

   from ortools.sat.python import cp_model

   solution = optimizer.solve(
       model,
       search_branching=cp_model.AUTOMATIC_SEARCH,  # or FIXED_SEARCH, PORTFOLIO_SEARCH
       log_search_progress=True,
   )

**Solution Hints (Warm Start):**

LumiX does not pass solution hints or warm starts to the solvers yet; the
``supports_warmstart`` capability flag only records what the solver itself offers.

Performance Tuning
------------------

General Guidelines
~~~~~~~~~~~~~~~~~~

**1. Threading**

More threads ≠ always faster:

.. code-block:: python

   # Test different thread counts
   for threads in [1, 2, 4, 8, 16]:
       solution = optimizer.solve(
           model,
           time_limit=60,
           Threads=threads  # Gurobi example
       )
       print(f"Threads={threads}: {solution.solve_time:.2f}s")

**Recommendation:**

- Small problems: 1-4 threads
- Medium problems: 4-8 threads
- Large problems: 8-32 threads (diminishing returns beyond 16)

**2. Presolve**

Presolve simplifies model before solving:

.. code-block:: python

   # Aggressive presolve (may help large models)
   solution = optimizer.solve(model, Presolve=2)

   # Disable presolve (if presolve takes too long)
   solution = optimizer.solve(model, Presolve=0)

**When to disable:**

- Very large models where presolve takes hours
- Models that solve quickly anyway

**3. MIP Focus**

For MIP problems, choose focus:

.. code-block:: python

   # Finding ANY feasible solution quickly
   solution = optimizer.solve(model, MIPFocus=1)

   # Proving optimality
   solution = optimizer.solve(model, MIPFocus=2)

   # Improving best bound
   solution = optimizer.solve(model, MIPFocus=3)

**4. Cuts**

Cutting planes can help or hurt:

.. code-block:: python

   # Disable cuts (faster, may get worse bound)
   solution = optimizer.solve(model, Cuts=0)

   # Aggressive cuts (slower, better bound)
   solution = optimizer.solve(model, Cuts=2)

**Recommendation:**

- Try default first
- Disable cuts if solving takes too long and gap tolerance is relaxed
- Aggressive cuts if you need to prove optimality

Problem-Specific Tuning
~~~~~~~~~~~~~~~~~~~~~~~

**Large-Scale LP**

.. code-block:: python

   # Gurobi
   solution = optimizer.solve(
       model,
       Method=2,        # Barrier method
       Crossover=0,     # Skip crossover
       Threads=32,      # Use all cores
       BarConvTol=1e-4, # Relaxed convergence
   )

**Hard MIP (Slow to Solve)**

.. code-block:: python

   # Gurobi
   solution = optimizer.solve(
       model,
       Threads=16,
       MIPFocus=1,          # Find feasible solutions
       Heuristics=0.2,      # 20% time on heuristics
       ImproveStartTime=300, # Start polishing after 5 min
       gap_tolerance=0.01,  # Accept 1% gap
   )

**Need Optimal Proof**

.. code-block:: python

   # Gurobi
   solution = optimizer.solve(
       model,
       Threads=16,
       MIPFocus=2,      # Prove optimality
       Cuts=2,          # Aggressive cuts
       Presolve=2,      # Aggressive presolve
       gap_tolerance=0.0001,
   )

**Scheduling Problem (CP-SAT)**

.. code-block:: python

   solution = optimizer.solve(
       model,
       num_search_workers=8,
       log_search_progress=True,
       max_time_in_seconds=300,
   )

Debugging Configuration
-----------------------

Enable Logging
~~~~~~~~~~~~~~

**Gurobi:**

.. code-block:: python

   solution = optimizer.solve(
       model,
       LogToConsole=1,
       LogFile="solve.log",
       DisplayInterval=1  # Log every second
   )

**CPLEX:**

.. code-block:: python

   solution = optimizer.solve(
       model,
       verbose=True  # Print the CPLEX log
   )

**CP-SAT:**

.. code-block:: python

   solution = optimizer.solve(
       model,
       log_search_progress=True
   )

The ``"ortools"`` (GLOP/SCIP) adapter has no log option.

Check Solver Statistics
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   solution = optimizer.solve(model, LogToConsole=1)

   print(f"Status: {solution.status}")
   print(f"Objective: {solution.objective_value}")
   print(f"Solve time: {solution.solve_time:.2f}s")
   print(f"Gap: {solution.gap}")  # MIP gap; None for LPs

Configuration Best Practices
-----------------------------

1. **Start Simple**

   .. code-block:: python

      # Start with defaults
      solution = optimizer.solve(model)

      # Add configuration only if needed
      solution = optimizer.solve(model, time_limit=300)

2. **Profile Before Tuning**

   .. code-block:: python

      # See where time is spent
      solution = optimizer.solve(model, LogToConsole=1)
      # Check log: presolve time, root relaxation, node processing

3. **Tune Incrementally**

   .. code-block:: python

      # Test one parameter at a time
      configs = [
          {},
          {"Threads": 8},
          {"Threads": 8, "Presolve": 2},
          {"Threads": 8, "Presolve": 2, "Cuts": 2},
      ]

      for config in configs:
          solution = optimizer.solve(model, time_limit=60, **config)
          print(f"{config}: {solution.solve_time:.2f}s")

4. **Document Configuration**

   .. code-block:: python

      # Document why you chose these settings
      PRODUCTION_CONFIG = {
          "Threads": 16,        # Using dedicated server with 16 cores
          "MIPFocus": 1,        # Need feasible solutions quickly
          "gap_tolerance": 0.01,  # 1% gap acceptable for business
          "time_limit": 600,    # Maximum 10 min for real-time updates
      }

      solution = optimizer.solve(model, **PRODUCTION_CONFIG)

Example: Complete Tuning Workflow
----------------------------------

.. code-block:: python

   from lumix import LXOptimizer
   import time

   # Build model
   model = build_large_mip_model()

   optimizer = LXOptimizer().use_solver("gurobi")

   # Baseline
   print("Baseline (defaults):")
   solution = optimizer.solve(model, time_limit=300, LogToConsole=1)
   print(f"  Time: {solution.solve_time:.2f}s")
   print(f"  Gap: {solution.gap:.4f}")
   print(f"  Objective: {solution.objective_value:.2f}")

   # Test threading
   print("\nTesting threading:")
   for threads in [1, 4, 8, 16]:
       solution = optimizer.solve(model, time_limit=300, Threads=threads)
       print(f"  Threads={threads}: {solution.solve_time:.2f}s")

   # Test MIP focus
   print("\nTesting MIP focus:")
   for focus in [0, 1, 2, 3]:
       solution = optimizer.solve(model, time_limit=300, Threads=8, MIPFocus=focus)
       print(f"  MIPFocus={focus}: gap={solution.gap:.4f}")

   # Test gap tolerance
   print("\nTesting gap tolerance:")
   for gap in [0.05, 0.01, 0.001]:
       solution = optimizer.solve(
           model,
           time_limit=300,
           Threads=8,
           MIPFocus=1,
           gap_tolerance=gap
       )
       print(f"  Gap={gap}: {solution.solve_time:.2f}s")

   # Final configuration
   print("\nFinal configuration:")
   solution = optimizer.solve(
       model,
       Threads=8,
       MIPFocus=1,
       gap_tolerance=0.01,
       Presolve=2,
       Heuristics=0.1,
       time_limit=600,
   )
   print(f"  Time: {solution.solve_time:.2f}s")
   print(f"  Objective: {solution.objective_value:.2f}")

Next Steps
----------

- :doc:`solver-capabilities` - Understanding what each solver supports
- :doc:`advanced-features` - Callbacks, warm start, solution pools
- :doc:`using-optimizer` - Using the optimizer API
- Gurobi Parameter Reference: https://www.gurobi.com/documentation/
- CPLEX Parameter Reference: https://www.ibm.com/docs/en/icos/
