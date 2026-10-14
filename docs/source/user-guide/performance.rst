Performance Considerations
==========================

LumiX builds the solver model by expanding every expression term over the
instances of its variable family. This page explains what that costs, how to
keep large models fast, and what the library does for you.

.. contents:: On this page
   :local:
   :depth: 1

How model building scales
-------------------------

A term written with ``where`` is a filter: for **every constraint row** the
solver adapter walks **all** instances of the variable family and calls the
filter on each one. The work per row is proportional to the size of the
family, so the total is

.. math::

   \text{build cost} \;\propto\; \text{rows} \times \text{instances per family}

For a transportation model with ``n`` plants and ``n`` customers
(``x`` over plants × customers, one supply row per plant and one demand row per
customer, all written with ``where``) that is :math:`2n \cdot n^2`, i.e. cubic
in ``n``:

.. list-table:: Model build time with ``where`` (OR-Tools, LumiX 0.1.2)
   :header-rows: 1

   * - n
     - rows
     - variables
     - build time
   * - 60
     - 120
     - 3,600
     - 0.05 s
   * - 90
     - 180
     - 8,100
     - 0.15 s
   * - 200
     - 400
     - 40,000
     - 1.47 s
   * - 300
     - 600
     - 90,000
     - 4.78 s

Small and medium models are unaffected; the cost becomes visible from a few
hundred rows over families of tens of thousands of instances.

Selecting instances by key: ``keys=``
-------------------------------------

.. versionadded:: 0.2.0

When you already know **which** instances a row uses, pass their index keys
instead of a filter. The adapter then looks them up directly, so the work per
row is proportional to the number of keys:

.. code-block:: python

   # Filter: scans all plants x customers for every plant row
   expr.add_multi_term(flow, where=lambda p, c, pid=plant.id: p.id == pid)

   # Keys: touches only this plant's |customers| instances
   expr.add_multi_term(flow, keys=[(plant.id, c.id) for c in customers])

``keys`` works with :meth:`~lumix.core.expressions.LXLinearExpression.add_term`,
:meth:`~lumix.core.expressions.LXLinearExpression.add_multi_term` and
:meth:`~lumix.core.expressions.LXLinearExpression.sum_over`.

**Key format.** A key is what :meth:`~lumix.core.variables.LXVariable.index_key`
returns for an instance: ``index_func(instance)`` for a family built with
``indexed_by``, and the tuple of dimension keys for ``indexed_by_product``
(``(plant.id, customer.id)`` above).

**Same model, guaranteed.** ``keys=K`` builds exactly the model that
``where=lambda inst: index_key(inst) in K`` builds: the same terms in the same
order. Keys that are not in the family match nothing; repeated keys count once.
You can switch a term from ``where`` to ``keys`` without changing results.

**Rules.**

- ``where`` and ``keys`` cannot be combined in one term (``ValueError``).
- ``keys`` must be an iterable of keys; a single string raises ``TypeError``
  (write ``keys=["a"]``, not ``keys="a"``).
- Keys are fixed per term. For a constraint family defined with
  ``.from_data(...)`` whose rows need different keys, build the rows in a loop
  (as in the example above) or keep ``where``.

The same transportation model, LumiX 0.2.0:

.. list-table:: Model build time, LumiX 0.2.0 (OR-Tools)
   :header-rows: 1

   * - n
     - rows
     - variables
     - ``where``
     - ``keys``
   * - 60
     - 120
     - 3,600
     - 0.03 s
     - 0.01 s
   * - 90
     - 180
     - 8,100
     - 0.10 s
     - 0.03 s
   * - 200
     - 400
     - 40,000
     - 0.89 s
     - 0.17 s
   * - 300
     - 600
     - 90,000
     - 2.88 s
     - 0.43 s

With ``keys`` the build time grows with the number of nonzeros instead of
rows × instances, so the gap widens as models grow.

What LumiX does for you
-----------------------

.. versionchanged:: 0.2.0

- **Instances are fetched once per build.** Each adapter calls
  ``get_instances()`` once per variable family per ``build_model`` instead of
  once per row. This alone makes ``where`` terms 1.6× faster on the model above.
  Families backed by an ORM query are therefore queried once per build. The
  cache is cleared at the start of every build, so changing data and solving
  again with the same optimizer uses the new data.
- **Key lookups are indexed.** For ``keys=`` terms the adapter builds a
  key → instance index once per family per build.

Practical advice
----------------

- Prefer ``keys=`` for terms over large families, especially sums over one
  dimension of a two- or three-dimensional family.
- Precompute keys once (for example a dict from plant to its customers' keys)
  instead of rebuilding lists inside nested loops.
- Keep cross-dimension filters (``.filter(...)`` on a cartesian product) for
  sparsity that is part of the model, not for selecting the terms of one row.
- Linearization adds auxiliary variables and constraints: McCormick adds one
  variable and four constraints per product, piecewise terms add one variable
  per breakpoint. Check :meth:`~lumix.linearization.LXLinearizer.get_statistics`
  on large nonlinear models.
- Adding two expressions that contain the same variable (or calling
  ``add_term`` twice for it) merges the terms into one combined filter; merged
  terms keep their meaning but do not use the keyed fast path. Use one
  ``keys=`` term per variable where speed matters.

Known limitations
-----------------

- Keys that depend on the row of a data-driven constraint family
  (``keys=lambda row: ...``) are not supported yet.
- The keyed path is exercised by the test suite with OR-Tools, CP-SAT and
  Gurobi. The CPLEX and GLPK adapters use the same shared code path but are
  not run in CI.

Measuring your own model
------------------------

The numbers above come from ``tests/test_build_performance.py`` and the
``transport`` model in ``tests/test_instance_cache.py``. Run the benchmark
with::

   pytest tests/test_build_performance.py -s -m slow
