Result Store
============

.. versionadded:: 0.3.0

:class:`~lumix.analysis.store.LXResultStore` writes every solve made by the scenario and
what-if analyzers to a database through SQLAlchemy, and reads the results back as plain
Python objects.

.. code-block:: python

   from lumix import LXResultStore, LXStoredRun

Why
---

Analyzer results normally live in memory (``analyzer.results``) and disappear when the
process ends. Storing them lets you:

- Keep a history of analyses and compare runs made on different days or data snapshots
- Share results with reports, dashboards or other services that read the database
- Inspect variable values, shadow prices and reduced costs of any run later, without
  re-solving
- Record exactly which modifications produced which outcome

Setup
-----

The store needs SQLAlchemy, which comes with the ``orm`` extra:

.. code-block:: bash

   pip install "lumix-opt[orm]"

SQLAlchemy is imported only when a store is created, so ``import lumix`` keeps working
without it; creating an ``LXResultStore`` without SQLAlchemy raises ``ImportError``.

Create the two tables once with :meth:`~lumix.analysis.store.LXResultStore.create_tables`
(it does nothing if they already exist), then create a store on a SQLAlchemy ``Session``:

.. code-block:: python

   from sqlalchemy import create_engine
   from sqlalchemy.orm import Session
   from lumix import LXResultStore

   engine = create_engine("sqlite:///results.db")   # or postgresql+psycopg://...
   LXResultStore.create_tables(engine)

   with Session(engine) as session:
       store = LXResultStore(session, analysis="q3-capacity")
       ...

``LXResultStore(session, analysis=None, include_sensitivity=False, commit=True)``:

``session``
   A SQLAlchemy ``Session``.
``analysis``
   A label written on every run, used to group and filter runs (for example one label per
   study or per day).
``include_sensitivity``
   Also store shadow prices and reduced costs (see `Schema`_).
``commit``
   Commit after each recorded run (default). See `Transactions`_.

Recording Scenarios and What-If Runs
------------------------------------

Pass the store to an analyzer with ``result_store=``. Every solve is then recorded, with
no further code:

- :class:`~lumix.analysis.scenario.LXScenarioAnalyzer`: the baseline (scenario name
  ``"baseline"``), each scenario (its name, with its modifications) and every
  ``sensitivity_to_parameter`` run (named ``f"{parameter}_{value}"``).
- :class:`~lumix.analysis.whatif.LXWhatIfAnalyzer`: the baseline when the analyzer
  computes it (not when you pass ``baseline_solution=``), then each what-if run. The
  scenario name is the what-if description (for example ``"Relax capacity RHS by 100"``)
  and the modifications are the applied changes as dictionaries.

The example builds models with a ``model_factory``, which works well with stored
results because every run starts from fresh data:

.. code-block:: python

   from sqlalchemy import create_engine
   from sqlalchemy.orm import Session
   from lumix import (LXOptimizer, LXResultStore, LXScenario, LXScenarioAnalyzer,
                      LXWhatIfAnalyzer)

   engine = create_engine("sqlite:///results.db")
   LXResultStore.create_tables(engine)
   optimizer = LXOptimizer().use_solver("ortools")

   def build_model():
       products = load_products()          # fresh data for every model
       return build_production_model(products)

   with Session(engine) as session:
       store = LXResultStore(session, analysis="q3-capacity")

       # Scenarios: one run for the baseline and one per scenario
       scenarios = LXScenarioAnalyzer(
           optimizer=optimizer, model_factory=build_model, result_store=store
       )
       scenarios.add_scenario(
           LXScenario("overtime").modify_constraint_rhs("capacity", multiply=1.2)
       )
       scenarios.add_scenario(
           LXScenario("maintenance").modify_constraint_rhs("capacity", add=-8)
       )
       scenarios.run_all_scenarios()

       # What-if: baseline + one run per question, same analysis label
       whatif = LXWhatIfAnalyzer(
           optimizer=optimizer, model_factory=build_model, result_store=store
       )
       whatif.relax_constraint("capacity", by=10)
       whatif.modify_variable_bound("production", upper=500)

You can also record a solution yourself:

.. code-block:: python

   solution = optimizer.solve(model)
   run_id = store.record("manual", solution, model=model,
                         modifications=[{"note": "hand-tuned"}])

``record(scenario, solution, model=None, modifications=())`` returns the new run id.
``model`` is needed to store shadow prices per constraint family (see `Schema`_).
Modification values that are not JSON types are stored as their ``repr``.

Reading Results Back
--------------------

:meth:`~lumix.analysis.store.LXResultStore.runs` returns
:class:`~lumix.analysis.store.LXStoredRun` objects in the order they were recorded,
optionally only those with one analysis label:

.. code-block:: python

   with Session(engine) as session:
       store = LXResultStore(session)

       for run in store.runs(analysis="q3-capacity"):
           print(run.id, run.scenario, run.status, run.objective, run.solve_time)
           for mod in run.modifications:
               print("   ", mod)

``LXStoredRun`` is a frozen dataclass with the fields ``id``, ``analysis``,
``scenario``, ``status``, ``objective`` (``None`` when the run was not feasible),
``solve_time``, ``modifications`` (a list of dictionaries) and ``created_at``.

For a scenario run, each modification looks like:

.. code-block:: python

   {"target_type": "constraint", "target_name": "capacity",
    "modification_type": "rhs_multiply", "value": 1.2}

For a what-if run it is the applied change, for example
``{"change_type": "variable_bound", "target_name": "production", "bound": "upper",
"original_value": None, "new_value": 500}``.

:meth:`~lumix.analysis.store.LXResultStore.values` returns the stored numbers of one run,
shaped like ``LXSolution.variables``:

.. code-block:: python

   values = store.values(run.id)                      # kind="value"
   # {"total": 8.0,                                   # scalar variable
   #  "production": {"widget": 2.0, "gadget": 6.0}}   # indexed family: {key: value}

   prices = store.values(run.id, kind="shadow_price")
   # {"total": 3.0, "capacity": {"widget": 0.0, "gadget": 2.0}}

   costs = store.values(run.id, kind="reduced_cost")

- Scalars map ``name -> value``; indexed families map ``name -> {key: value}``.
- ``kind`` is ``"value"`` (default), ``"shadow_price"`` or ``"reduced_cost"``; any other
  value raises ``ValueError``.
- A run with no rows of that kind returns ``{}`` (for example an infeasible run, or
  shadow prices recorded without ``include_sensitivity=True``).

Comparing two runs is then ordinary Python:

.. code-block:: python

   base, overtime = store.runs(analysis="q3-capacity")[:2]
   before = store.values(base.id)["production"]
   after = store.values(overtime.id)["production"]
   for key in before:
       print(key, before[key], "->", after[key])

Schema
------

The store uses two tables. They are created by ``create_tables`` and can be queried with
any SQL tool.

``lumix_runs``: one row per recorded solve.

.. list-table::
   :header-rows: 1
   :widths: 18 22 60

   * - Column
     - Type
     - Meaning
   * - ``id``
     - integer, primary key
     - Run id (returned by ``record``)
   * - ``analysis``
     - string(255), nullable, indexed
     - The store's ``analysis`` label
   * - ``scenario``
     - text
     - Scenario name, ``"baseline"``, or the what-if description
   * - ``status``
     - string(64)
     - Solution status, for example ``"optimal"`` or ``"infeasible"``
   * - ``objective``
     - float, nullable
     - Objective value; ``NULL`` when the run is not feasible
   * - ``solve_time``
     - float, nullable
     - Solve time in seconds
   * - ``modifications``
     - JSON
     - List of modification dictionaries (empty for a baseline)
   * - ``created_at``
     - timezone-aware datetime
     - When the run was recorded, in UTC

``lumix_run_values``: the numbers of each run.

.. list-table::
   :header-rows: 1
   :widths: 18 22 60

   * - Column
     - Type
     - Meaning
   * - ``id``
     - integer, primary key
     - Row id
   * - ``run_id``
     - integer, foreign key to ``lumix_runs.id`` (``ON DELETE CASCADE``), indexed
     - The run the value belongs to
   * - ``kind``
     - string(16)
     - ``"value"``, ``"shadow_price"`` or ``"reduced_cost"``
   * - ``name``
     - text
     - Variable name (values, reduced costs) or constraint name (shadow prices)
   * - ``indexed``
     - boolean
     - Whether ``name`` is an indexed family (then ``key`` identifies the instance or row)
   * - ``key``
     - JSON, nullable
     - Index key of the instance or row; ``NULL`` for scalars
   * - ``value``
     - float, nullable
     - The number

What gets written:

- ``kind="value"``: one row per variable instance, only for **feasible** runs.
- ``kind="reduced_cost"`` and ``kind="shadow_price"``: only with
  ``include_sensitivity=True`` and when the solver reported them, which means an LP
  solved with ``LXOptimizer().enable_sensitivity()``. Shadow prices are grouped by
  constraint family (``name="capacity"``, ``key=3``) when the analyzer passes the model,
  which the built-in analyzers always do.

**Key encoding** in the ``key`` column:

.. list-table::
   :header-rows: 1
   :widths: 35 30 35

   * - Index key in Python
     - Stored as JSON
     - Read back by ``values()`` as
   * - ``None``, ``bool``, ``int``, ``float``, ``str``
     - The same value
     - The same value
   * - ``tuple`` (also nested)
     - A JSON list
     - A ``tuple``
   * - Any other object (for example a dataclass)
     - ``str(key)``
     - That string

So ``("a", 1)`` round-trips to ``("a", 1)``, while a key such as ``K(id=3)`` comes back as
the string ``"K(id=3)"``. Use plain keys (``indexed_by(lambda p: p.id)``) if you want them
back unchanged.

Transactions
------------

With ``commit=True`` (the default) the store commits the session after each recorded run,
so every run is visible to other sessions right away and a later failure does not lose
earlier runs.

.. note::
   ``session.commit()`` commits **everything** pending in the session, not only LumiX's
   rows, and with SQLAlchemy's default ``expire_on_commit=True`` it expires every instance
   loaded in that session (the next attribute access reloads it). Give the store a session
   of its own, as in the examples on this page, rather than the session your model reads
   its data from. If you must share one, pass ``commit=False`` and commit yourself, or
   create the session with ``expire_on_commit=False``.

With ``commit=False`` the store only flushes. The rows are visible inside the session,
and you decide when to commit or roll back:

.. code-block:: python

   with Session(engine) as session:
       store = LXResultStore(session, analysis="nightly", commit=False)
       analyzer = LXScenarioAnalyzer(model, optimizer, result_store=store)
       analyzer.add_scenarios(*scenarios)
       try:
           analyzer.run_all_scenarios()
           session.commit()          # all runs or none
       except Exception:
           session.rollback()
           raise

Limitations
-----------

- **SQLAlchemy only.** Django's ORM is not supported.
- **One schema.** The table names ``lumix_runs`` and ``lumix_run_values`` are fixed, and
  there are no migrations; ``create_tables`` creates missing tables but does not alter
  existing ones.
- **Numbers only.** Solutions are stored as variable values (and optionally shadow prices
  and reduced costs); the model itself is not stored.
- **Non-JSON keys** are stored as ``str(key)`` (see `Schema`_) and come back as strings;
  two keys with the same ``str()`` come back as one entry (the last value). Index by a
  JSON-friendly id (``lambda p: p.id``).
- **Infeasible runs** keep their status but no objective and no values.
- **Sensitivity data** requires an LP solved with ``enable_sensitivity()``; MIP solves
  usually have no shadow prices or reduced costs.
- **Analysis labels** longer than 255 characters do not fit the ``analysis`` column on
  databases that enforce the length.

See Also
--------

- :doc:`scenario` - Scenario analysis (``result_store=``, ``model_factory=``)
- :doc:`whatif` - What-if analysis (``result_store=``, ``model_factory=``)
- :doc:`/api/analysis/index` - API reference
