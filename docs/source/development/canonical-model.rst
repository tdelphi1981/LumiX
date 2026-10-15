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
- ``objective_quadratic``: ``{(i, j): c}`` with ``i <= j``, the objective term
  ``c * x_i * x_j`` of a quadratic objective.
- ``objective_nonlinear``: the nonlinear terms of an ``LXNonLinearExpression``
  objective, one :class:`~lumix.core.canonical.LXCanonicalNonlinear` per variable
  instance (see `Nonlinear objective items`_).
- ``goal_stages``: the stage objectives of sequential goal programming, empty
  otherwise (see `Goal programming`_).

Adding fields keeps the schema version; changing or removing fields increments it.

Nonlinear objective items
-------------------------

.. versionchanged:: 0.3.0
   ``objective_nonlinear`` is filled (it was always empty), the items have the new
   fields ``term`` and ``key``, and the constant of an ``LXNonLinearExpression`` is
   kept in ``objective_constant`` (it was dropped). ``schema_version`` stays 1.

Each term of the objective expression is expanded per instance, with the same
rule the linearizer uses (see :doc:`/user-guide/linearization/engine`): a term on
variable families gives one item per index key, the families of one term must have
the same keys, and a single variable is broadcast to every key. The item for a key
is the term's contribution for that instance; the objective is the linear part
plus the sum of all items.

Fields of :class:`~lumix.core.canonical.LXCanonicalNonlinear`:

- ``kind``: ``"abs"``, ``"min"``, ``"max"``, ``"product"`` or ``"piecewise"``
- ``variables``: positions in ``variables`` (a tuple)
- ``coeff``: the factor the item's value is multiplied by
- ``params``: kind-specific data (below)
- ``term``: position of the source term in the expression's ``nonlinear_terms``;
  the items of one term share it
- ``key``: index key of the instance the item applies to, ``None`` when every
  variable of the term is single (a scalar or a one-instance family)

.. list-table::
   :header-rows: 1
   :widths: 14 26 20 40

   * - ``kind``
     - ``variables``
     - ``coeff``
     - ``params``
   * - ``abs``
     - ``(i,)``
     - term coefficient
     - ``{}``; value ``coeff * |x_i|``
   * - ``min`` / ``max``
     - the term's variables, in order
     - ``1.0``
     - ``{"coefficients": (c_1, ..., c_n)}``; value ``min(c_k * x_k)`` /
       ``max(c_k * x_k)``
   * - ``product``
     - ``(i, j)``
     - term coefficient
     - ``{}``; value ``coeff * x_i * x_j``
   * - ``piecewise``
     - ``(i,)``
     - ``1.0``
     - ``{"breakpoints": (...), "values": (...), "method": "sos2" | "incremental"
       | "logarithmic"}``; the breakpoints are numbers (generated ones resolved
       with ``LXLinearizerConfig``), value the piecewise-linear interpolation

.. code-block:: python

   # x is a family over keys "p", "q"
   model.minimize(LXNonLinearExpression().add_abs(x, coeff=2.0))
   model.to_canonical().objective_nonlinear
   # (LXCanonicalNonlinear(kind='abs', variables=(0,), coeff=2.0, params={}, term=0, key='p'),
   #  LXCanonicalNonlinear(kind='abs', variables=(1,), coeff=2.0, params={}, term=0, key='q'))

Indicator terms are constraints, not objective values: ``to_canonical()`` raises
``ValueError`` for an objective that contains them. A nonlinear term in a
constraint also raises, because ``rows`` are linear; such a model is solved through
the linearizer, whose output is linear.

Solver adapters do not read ``objective_nonlinear``: an objective with nonlinear
terms raises ``ValueError`` asking for ``enable_linearization()``. The items are
for engines outside LumiX and for the linearizer, which builds its auxiliary
variables from the same expansion.

Row semantics
-------------

- Terms on the same variable instance are summed (``x + x`` is ``2x``); a sum
  that cancels to floating-point noise (``0.1 + 0.2 - 0.3``) is 0, and so is a
  right-hand side that differs from the constant only by such noise.
- Index keys must be unique within a variable family and within a constraint
  family; a repeated key raises ``ValueError``.
- A constraint family defined over the variable's own data narrows a term to the
  row's own instance only when the term's coefficient and filter take **one**
  required argument (parameters with a default value, as in
  ``lambda item, g=g: ...``, do not count). The rule is applied to every
  ``add_term`` separately, also after expressions are added or scaled. A coefficient or filter that takes two arguments
  (``lambda var_instance, row_instance: ...``) sees the whole family, which is what
  balance equations such as ``inv[t] - inv[t-1]`` need.
- For ``add_multi_term`` / ``sum_over`` on ``indexed_by_product`` families,
  coefficients and filters receive one argument per dimension; on single-index
  families they receive the instance (tuples and NamedTuples are not unpacked).
- A filter of type :class:`~lumix.core.expressions.LXRowKeyFilter` keeps, in each
  row, only the instance whose index key is ``row_key(row)``. The builder looks
  that instance up by key instead of testing every instance, so an indexed
  constraint whose rows each use one instance of another family builds in linear
  time. Goal relaxation uses it to give every row of an indexed goal its own
  deviation variables.

Goal programming
----------------

.. versionadded:: 0.3.0

A model with goals (constraints marked with ``.as_goal()``) is relaxed in the
canonical form; the model itself is not changed (see
:doc:`/user-guide/goal_programming/index`):

- the deviation variables appear in ``variables`` (families ``<goal>_pos_dev`` and
  ``<goal>_neg_dev``, keyed by the goal instance id: the goal name for a single
  goal, ``<goal>_<key>`` for each row of an indexed goal);
- each goal row of priority 1 or lower is an ``EQ`` row with its deviations;
  priority 0 goals are objective terms, not rows.

The objective depends on the goal mode:

- **Weighted** (the default): ``objective`` is the weighted sum of the undesired
  deviations plus the model's own objective and the priority 0 goals, in
  minimization form; ``goal_stages`` is ``()``.
- **Sequential**: ``goal_stages`` is a tuple of objective coefficient dicts
  (``{position: coeff}``, the weighted undesired deviations of one priority), one
  per priority in solve order (priority 1 first). ``objective`` holds the final
  stage: the model's own objective together with the priority 0 goals, empty when
  there is neither. An engine solves the stages in order and bounds each solved
  stage by its optimum before the next one.

.. code-block:: python

   model.set_goal_mode("sequential")
   canon = model.to_canonical()
   for coeffs in canon.goal_stages:
       print({canon.variables[i].name: c for i, c in coeffs.items()})

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
