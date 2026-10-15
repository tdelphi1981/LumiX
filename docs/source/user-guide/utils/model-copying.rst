Model Copying
=============

This guide explains what happens when a LumiX model is copied, which is what what-if and
scenario analysis do for every run, and how to work with models built from ORM
(Object-Relational Mapping) data sources.

.. versionchanged:: 0.3.0
   Model copies share data instances and callables with the original. Nothing is
   deep-copied or detached any more, for plain objects and ORM objects alike. ORM
   detaching is used only when a model is pickled.

Overview
--------

Why Model Copying is Needed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Many analysis workflows need modified versions of a model while the original stays
unchanged:

- **What-If Analysis**: Test parameter changes without affecting the original model
- **Scenario Analysis**: Compare multiple variations of the same base model
- **A/B Testing**: Compare different modeling approaches

:class:`~lumix.analysis.whatif.LXWhatIfAnalyzer` and
:class:`~lumix.analysis.scenario.LXScenarioAnalyzer` get those versions by copying the
model with ``copy.deepcopy``, unless you give them a ``model_factory`` (see
`Alternative: a Model Factory`_).

The Rule: Copies Share Data
---------------------------

``copy.deepcopy(model)`` copies the model's **structure** and shares its **data**:

.. list-table::
   :header-rows: 1
   :widths: 45 20 35

   * - Part of the model
     - In the copy
     - Consequence
   * - Variable families, constraint families, expressions, objective
     - New objects
     - Changing a bound or right-hand side in the copy does not affect the original
   * - Data lists (``from_data(products)``)
     - New ``list`` objects
     - Adding or removing items in the copy's list does not affect the original
   * - Data instances (the items in those lists), plain or ORM
     - Shared
     - The copy sees exactly the same objects as the original
   * - Callables (lambdas for coefficients, right-hand sides, indexing, filters)
     - Shared
     - Closures keep referring to your own objects

.. mermaid::

   graph LR
       subgraph Original
           A[LXModel] --> B[LXVariable production]
           B --> C[list]
       end
       subgraph Copy
           A2[LXModel] --> B2[LXVariable production]
           B2 --> C2[list]
       end
       C --> D[Product instances]
       C2 --> D
       B --> E[lambdas]
       B2 --> E

       style D fill:#e1ffe1
       style E fill:#e1ffe1

Why Sharing Matters
~~~~~~~~~~~~~~~~~~~

Lambdas often depend on the identity of data objects. Because instances and lambdas are
shared, these patterns behave in a copy exactly as in the original model:

.. code-block:: python

   from copy import deepcopy

   products = load_products()
   flagship = products[0]
   weights = {p: p.priority * 2.0 for p in products}   # keyed by instance

   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .bounds(lower=0)
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

   model = LXModel("plan").add_variable(production)
   model.add_constraint(
       LXConstraint("flagship_cap")
       .expression(LXLinearExpression().add_term(
           production, coeff=lambda p: 1.0 if p is flagship else 0.0))   # identity check
       .le()
       .rhs(100)
   )
   model.maximize(LXLinearExpression().add_term(production, lambda p: weights[p]))

   model_copy = deepcopy(model)
   # model_copy solves to the same optimum: "p is flagship" and weights[p] still
   # match, because model_copy holds the very same Product instances.

The copy is still independent where it matters for analysis:

.. code-block:: python

   model_copy.get_constraint("flagship_cap").rhs_value = 50
   assert model.get_constraint("flagship_cap").rhs_value == 100   # original untouched

.. note::

   Because data instances are shared, **mutating an instance** (``product.capacity = 0``)
   affects the original model and every copy. Express changes through scenario or
   what-if modifications (right-hand sides, bounds), not by editing data objects.

ORM Data Sources
----------------

Copies treat ORM objects like any other data instance: they are shared, not detached.

- A family bound with ``from_data(session.query(Product).all())`` holds a list of ORM
  instances; the copy gets a new list with the same instances.
- A family bound with ``from_model(Product, session=session)`` runs its query lazily.
  When the model is copied, the query runs **once, at copy time**, and the copy holds the
  resulting list of instances (no session reference of its own).
- Lambdas that read relationships (``p.category.factor``) load them through each
  instance's own session, exactly as in the original model.

So a copied ORM model works as long as the session that loaded the instances can still
serve whatever the lambdas read. If you eager-load what the lambdas need, or keep the
session open for the duration of the analysis, copying is all you need:

.. code-block:: python

   from sqlalchemy.orm import Session, joinedload

   with Session(engine) as session:
       products = session.query(Product).options(joinedload(Product.category)).all()
       model = build_model(products)

       analyzer = LXWhatIfAnalyzer(model, optimizer)
       result = analyzer.increase_constraint_rhs("capacity", by=100)

Alternative: a Model Factory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. versionadded:: 0.3.0

If the session may be closed before or during the analysis, give the analyzer a
``model_factory`` instead of a model. The factory is called for the base model and for
every run, so nothing is copied, and it can open a fresh session each time:

.. code-block:: python

   from sqlalchemy.orm import Session, selectinload

   def build_model():
       with Session(engine) as session:     # closed after loading
           products = (session.query(Product)
                       .options(selectinload(Product.category))   # what lambdas read
                       .all())
       return build_production_model(products)   # a new LXModel

   analyzer = LXScenarioAnalyzer(optimizer=optimizer, model_factory=build_model)
   # ... add and run scenarios ...

.. important::

   Close the session inside the factory, after eager-loading every relationship your
   lambdas read (``selectinload`` / ``joinedload``). Loaded attributes stay readable on
   the instances after the session closes, and the connection goes back to the pool.
   A session left open per model holds one pooled connection each, so with SQLAlchemy's
   default pool (5 + 10 overflow) the 16th run would wait for a connection and fail.

The factory must return a new model on every call. See
:doc:`/user-guide/analysis/scenario` and :doc:`/user-guide/analysis/whatif`.

Pickling and ORM Detachment
---------------------------

Detaching ORM objects from their session is used only when a model is **pickled**
(``__getstate__``). When an ORM-backed family (``from_model(..., session=...)``) is
pickled, its query is materialized and each instance is replaced by a detached copy made
with ``detach_orm_object``; the session reference is dropped.

.. code-block:: python

   import pickle

   pickled = pickle.dumps(model)        # __getstate__ detaches ORM instances
   restored = pickle.loads(pickled)

.. note::

   The standard :mod:`pickle` module cannot serialize lambdas. Models that use lambdas
   (most LumiX models do) need a serializer that supports them, such as ``cloudpickle``
   or ``dill``.

detach_orm_object
~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.utils.copy_utils import detach_orm_object

   product = session.query(Product).first()
   detached = detach_orm_object(product)
   # detached is a plain object of the same class, with no session

   session.close()
   print(detached.name)            # ✓ column values were copied
   print(detached.category.name)   # ✓ relationship loaded while the session was open

   # Plain objects are returned unchanged
   assert detach_orm_object(plain_product) is plain_product

How it works for SQLAlchemy:

1. Create a new instance of the same class (``cls.__new__(cls)``) with a plain
   ``__dict__``.
2. Copy every column attribute value.
3. Copy relationship attributes that are already loaded.
4. Load relationship attributes that are **not** loaded yet, while the instance still has a
   session.
5. If the instance has no session, or loading fails, emit a ``UserWarning``: accessing
   that relationship on the detached copy will fail.

.. versionchanged:: 0.3.0
   Unloaded (lazy) relationships are loaded while the object still has a session; they
   used to be left out silently.

For Django models, field values are copied to a new instance (relations are not copied).

Other Helpers
~~~~~~~~~~~~~

``lumix.utils.copy_utils`` also provides ``materialize_and_detach_list`` (detach and copy
each item of a list) and ``copy_function_detaching_closure`` (rebuild a function whose
closure holds ORM objects with detached copies). LumiX no longer uses them when copying a
model; they remain available for your own serialization code.

Troubleshooting
---------------

Lazy-Loading Errors in a Copy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptom**: ``DetachedInstanceError`` or "session is closed" errors while what-if or
scenario analysis solves a copied model.

**Cause**: The copy shares the ORM instances, and a lambda reads a relationship that was
never loaded after the session was closed.

**Solution**: Use a ``model_factory`` with a fresh session, keep the session open during
the analysis, or eager-load the relationships before building the model.

Copy Gives a Different Result Than the Original
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Since 0.3.0 this should not happen because of identity checks or instance-keyed
dictionaries, since copies share instances and lambdas. If it does, check whether code
mutates data instances between solves; such changes are visible to every copy.

Pickling Errors
~~~~~~~~~~~~~~~

**Symptom**: ``PicklingError`` mentioning a lambda or a session.

**Solution**: Use a serializer that supports lambdas (``cloudpickle``, ``dill``) and avoid
capturing sessions in lambdas:

.. code-block:: python

   # Problem: lambda captures the session
   bad_func = lambda p: session.query(Cost).filter_by(product_id=p.id).one().value  # ❌

   # Better: read attributes of the instance
   good_func = lambda p: p.cost  # ✓

Best Practices
--------------

1. **Let the analyzers copy for you.** ``LXWhatIfAnalyzer`` and ``LXScenarioAnalyzer``
   never modify the model you pass in.
2. **Do not mutate data instances** to express a scenario; use right-hand-side and bound
   modifications.
3. **For ORM data whose session may close, use** ``model_factory``.
4. **Eager-load** relationships that lambdas read, to avoid one query per row.

See Also
--------

- :doc:`/user-guide/analysis/whatif` - What-if analysis
- :doc:`/user-guide/analysis/scenario` - Scenario analysis
- :doc:`orm-integration` - ORM integration overview
- :doc:`/tutorials/production_planning/step7_whatif` - Tutorial with ORM data

API Reference
~~~~~~~~~~~~~

See the docstrings of:

- ``lumix.utils.copy_utils.detach_orm_object``
- ``lumix.utils.copy_utils.materialize_and_detach_list``
- ``lumix.utils.copy_utils.copy_function_detaching_closure``

References
----------

- **SQLAlchemy Session**: https://docs.sqlalchemy.org/en/latest/orm/session.html
- **Django ORM**: https://docs.djangoproject.com/en/stable/topics/db/queries/
- **Python copy module**: https://docs.python.org/3/library/copy.html
