Correctness Notes
=================

.. versionadded:: 0.3.0

This page lists what LumiX solves exactly, what it approximates, and where it
asks you to decide. Every item here is covered by tests that compare LumiX with
an independent reference (brute-force enumeration, a model written directly in
the solver's API, or a closed-form answer).

.. contents:: On this page
   :local:
   :depth: 1

Linear models
-------------
- Every solver adapter builds rows from one canonical form
  (:meth:`LXModel.to_canonical`): constants move to the right-hand side,
  repeated terms are summed, binary and integer bounds are kept (integer bounds
  rounded inward). A model therefore means the same thing on every solver.
- Same-type rows are narrowed only for one-argument coefficients and filters
  (:doc:`core/constraints`).

Nonlinear terms
---------------
.. list-table::
   :header-rows: 1

   * - Term
     - How it is solved
   * - ``|x|``, ``min``, ``max`` where the objective or row direction makes them convex
     - Exact, no binaries
   * - ``|x|``, ``min``, ``max`` otherwise (maximized ``|x|``, ``==`` rows, …)
     - Exact with binaries; needs finite bounds
   * - binary × bounded variable
     - Exact (4 rows)
   * - integer × integer or continuous
     - Exact (binary expansion of the integer, ``binary_expansion_bits``)
   * - continuous × continuous
     - **Relaxation** (McCormick envelopes): ``UserWarning`` and
       ``solution.relaxation is True``; the objective is a bound. In an
       objective on Gurobi or CPLEX, write it with ``add_quadratic`` to solve it
       exactly.
   * - piecewise-linear ``f(x)``
     - Exact at the breakpoints (SOS2, incremental or logarithmic); between
       breakpoints the linear interpolation of ``f``
   * - indicator
     - Exact with Big-M from the expression's bounds; a ``UserWarning`` when the
       expression is unbounded and ``big_m_value`` is used

CP-SAT
------
- Coefficients are converted to fractions and each row is scaled to integers.
  A coefficient that ``max_denom`` cannot represent within 1e-9 relative error
  raises ``ValueError``; pass ``approximate_coefficients=True`` to accept the
  approximation.
- Continuous variables (with rational conversion) live on a grid; an equality
  with no grid solution is re-solved as a band, and the largest deviation is logged.

Goal programming
----------------
- Sequential mode is lexicographic: each priority is bounded at its optimum
  before the next is solved (``SEQUENTIAL_TOLERANCE`` relaxes the bound).
- Weighted mode multiplies priorities by ``10 ** (7 - priority)``; priorities
  7 and higher do not dominate the model objective.

Sensitivity analysis
--------------------
- Shadow prices and reduced costs exist only for LPs. OR-Tools (SCIP) and
  CP-SAT report none for MIPs; LumiX does not invent zeros.
- ``find_bottlenecks`` measures improvement per unit of right-hand side in the
  sense the model is solved, moving equalities in both directions.

What is verified how
--------------------
- OR-Tools, Gurobi, GLPK and CP-SAT run the test suite; CPLEX runs it where the
  ``cplex`` package is installed.
- Each fixed defect of the 0.3.0 audit has a regression test named after its
  catalog ID (``test_a1_...``); see the changelog.
