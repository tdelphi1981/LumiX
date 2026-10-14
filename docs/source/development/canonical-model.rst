Canonical Model
===============

.. versionadded:: 0.3.0

:meth:`LXModel.to_canonical() <lumix.core.model.LXModel.to_canonical>` returns a
solver-independent form of a model. Every solver adapter builds its native model
from it, so all solvers see the same rows; engines outside LumiX can read it
instead of LumiX internals.

.. code-block:: python

   canon = model.to_canonical()
   for row in canon.rows:
       print(row.name, row.sense, row.rhs, {canon.variables[i].name: c for i, c in row.coeffs.items()})

Structure (``schema_version`` 1):

- ``variables``: one :class:`~lumix.core.canonical.LXCanonicalVariable` per variable
  instance, in model and instance order (``family``, ``key``, ``name``,
  ``var_type``, ``lower``, ``upper``; open bounds are ``±inf``; integer bounds are
  rounded inward, binary bounds intersected with [0, 1]).
- ``families``: ``{family: {index_key: position}}``; an empty family maps to ``{}``.
- ``rows``: one :class:`~lumix.core.canonical.LXCanonicalRow` per constraint row with
  coefficients summed per variable instance and the expression constant moved to
  ``rhs``.
- ``objective``, ``objective_constant``, ``sense`` (``None`` when there is no
  objective).

Adding fields keeps the schema version; changing or removing fields increments it.

Row semantics
-------------

- Terms on the same variable instance are summed (``x + x`` is ``2x``).
- A constraint family defined over the variable's own data narrows a term to the
  row's own instance only when the term's coefficient and filter take **one**
  argument. A coefficient or filter that takes two arguments
  (``lambda var_instance, row_instance: ...``) sees the whole family, which is what
  balance equations such as ``inv[t] - inv[t-1]`` need.
- For ``add_multi_term`` / ``sum_over`` on ``indexed_by_product`` families,
  coefficients and filters receive one argument per dimension; on single-index
  families they receive the instance (tuples and NamedTuples are not unpacked).

Scalar and empty families
-------------------------

- A variable without a data source (no ``from_data``, ``from_model``,
  ``indexed_by``, ``indexed_by_product`` or join) is a scalar: one canonical
  variable named after the family with key ``None``, listed in
  ``scalar_families``. Its solution value is a number, not a dict.
- A family whose data is empty (``from_data([])``, an ORM query with no rows)
  has no variables; its terms contribute nothing and a warning is logged on the
  ``lumix.core.canonical`` logger. Before 0.3.0 such a family silently became one
  unindexed variable.
