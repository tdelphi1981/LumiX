Extending Linearization
=======================

Guide for developers who want to add new linearization techniques or customize existing ones.

Overview
--------

The linearization module is designed to be extensible. You can:

1. **Add new linearization techniques** for new nonlinear term kinds
2. **Change an existing technique** (a pure function in ``lumix/linearization/techniques/``)
3. **Add pre-built function approximations** to LXNonLinearFunctions
4. **Add configuration options** that your technique reads

How the engine is organized
~~~~~~~~~~~~~~~~~~~~~~~~~~~

A nonlinear term never reaches a technique directly. The pipeline is:

1. ``LXCanonicalBuilder.nonlinear`` (``lumix/core/canonical.py``) expands every
   term of an ``LXNonLinearExpression`` into per-instance items
   ``LXCanonicalNonlinear(kind, variables, coeff, params, term, key)``. It is an
   ``isinstance`` chain over the term classes; an unknown term raises
   ``ValueError("Unsupported nonlinear term type: ...")``.
2. ``LXLinearizer._linearize_items`` (``lumix/linearization/engine.py``) names one
   auxiliary tag per term from ``_TAG[item.kind]`` and calls
   ``LXLinearizer._technique`` once per item.
3. ``_technique`` dispatches on ``item.kind`` to a **pure function** that creates
   variables and rows only through ``LXAuxFactory.var`` / ``LXAuxFactory.row``
   (``lumix/linearization/refs.py``) and returns an ``LXVarRef`` to the variable
   that stands for the item's value. The engine adds ``coeff * <that variable>``
   to the row or objective the term came from.

The linearizer never changes the user's model: ``linearize_model()`` builds a new
model each time. It runs inside ``LXOptimizer`` when ``enable_linearization()`` is
set, or when you call ``LXLinearizer(model, capability, config).linearize_model()``
yourself.

Adding a New Linearization Technique
-------------------------------------

Example: Positive Part (max(x, 0))
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The example adds a term ``z = max(x, 0)`` with its own item kind ``"pos"``. It
takes three steps in the library, plus the term class itself (see
:doc:`extending-nonlinear` for writing term classes).

**Step 1: Emit a canonical item**

In ``LXCanonicalBuilder.nonlinear`` (``lumix/core/canonical.py``), add a branch
before the final ``else``. ``_aligned`` yields one ``(key, positions)`` pair per
instance of the term's variable families (``key`` is ``None`` for a single
variable):

.. code-block:: python

   elif isinstance(term, LXPositivePartTerm):
       for key, ps in self._aligned([term.var], where):
           items.append(LXCanonicalNonlinear("pos", ps, float(term.coefficient), {},
                                             index, key))

The same items appear in ``LXModel.to_canonical()`` (``objective_nonlinear``), so
the new kind is visible to every consumer of the canonical form.

**Step 2: Name the auxiliaries**

Add the kind to ``_TAG`` in ``lumix/linearization/engine.py``. The value is the
short name used in auxiliary families (``aux_pos_x_1_z``):

.. code-block:: python

   _TAG = {"abs": "abs", "min": "min", "max": "max", "product": "prod",
           "piecewise": "pwl", "pos": "pos"}

**Step 3: Write the technique and dispatch to it**

A technique is a function ``f(aux, tag, key, *refs, ...) -> LXVarRef``. It
receives the factory, the term's tag, the item's instance key and one
``LXVarRef`` per variable (``lower``/``upper`` are the bounds as floats, ``±inf``
when open). It must create everything through ``aux.var`` and ``aux.row`` and
pass ``key`` through unchanged, so the auxiliaries form families indexed by the
term's instance keys (a term on a single variable gets scalar auxiliaries):

.. code-block:: python

   # lumix/linearization/techniques/positive.py
   from typing import Any

   from ..refs import LXAuxFactory, LXVarRef, value_kind


   def positive_part(aux: LXAuxFactory, tag: str, key: Any, x: LXVarRef,
                     convex: bool) -> LXVarRef:
       """``z = max(x, 0)``. ``convex``: z is pushed down where it is used, so
       ``z >= x, z >= 0`` is exact; otherwise a binary makes it exact (needs finite
       bounds)."""
       z = aux.var(tag, "z", key, value_kind([x]), 0.0, max(0.0, x.upper))
       aux.row(tag, "ge_x", key, [(z, 1.0), (x, -1.0)], ">=", 0.0)       # z >= x
       if convex:
           return z
       if not x.bounded:
           raise ValueError(f"max({x.label}, 0) must be exact here; that needs "
                            f"finite bounds on '{x.var.name}'")
       on = aux.var(tag, "on", key, "binary")                            # 1 when x >= 0
       aux.row(tag, "le_x", key, [(z, 1.0), (x, -1.0), (on, -x.lower)],
               "<=", -x.lower)                                           # z <= x - lo (1 - on)
       aux.row(tag, "le_on", key, [(z, 1.0), (on, -x.upper)], "<=", 0.0) # z <= hi on
       return z

``aux.var(tag, role, key, kind, lower, upper)`` returns a reference to the
instance ``key`` of family ``<tag>_<role>`` (``kind`` is ``"continuous"``,
``"integer"`` or ``"binary"``); ``aux.row(tag, role, key, terms, sense, rhs)``
adds ``sum(c * ref) <sense> rhs`` for ``terms = [(ref, c), ...]``.
``value_kind`` makes the auxiliary integer when the inputs are integral, so
solvers without continuous variables (CP-SAT) still accept the model.

Then add a branch to ``LXLinearizer._technique``. ``sign`` is ``+1`` where the
value is pushed down (minimized objective, ``<=`` row), ``-1`` where it is pushed
up and ``0`` in equalities, so ``sign * item.coeff > 0`` means the cheap form is
exact, as for ``abs``:

.. code-block:: python

   if item.kind == "pos":
       self._counts["positive"] += 1
       return positive_part(self._aux, tag, key, refs[0],
                            convex=sign * item.coeff > 0)

``_counts`` has a fixed set of keys: add ``"positive"`` in ``_reset`` and report
it in ``get_statistics()``. If an item with weight 0 should create nothing (as for
``abs`` and ``product``), add the kind to the zero-weight check in
``_linearize_items``.

**Step 4: Add Tests**

Tests are flat files under ``tests/`` (for example
``tests/test_w4_linearization.py``). Solve the linearized model and compare it
with the known optimum; check both the cheap and the exact use:

.. code-block:: python

   from lumix import LXLinearizer, LXModel, LXNonLinearExpression, LXVariable
   from lumix.solvers import ORTOOLS_CAPABILITIES


   def test_positive_part_is_exact_when_maximized():
       x = LXVariable[str, float]("x").continuous().bounds(lower=-5, upper=3)
       model = LXModel("m").add_variable(x)
       model.maximize(LXNonLinearExpression().add_nonlinear_term(LXPositivePartTerm(x)))

       linearized = LXLinearizer(model, ORTOOLS_CAPABILITIES).linearize_model()
       # solve `linearized` and assert objective_value == 3

Adding Pre-built Functions
---------------------------

Example: Hyperbolic Tangent (tanh)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add to ``lumix/linearization/functions.py``:

.. code-block:: python

   class LXNonLinearFunctions:
       # ... existing methods ...

       @staticmethod
       def tanh(
           var: LXVariable,
           linearizer: LXPiecewiseLinearizer,
           segments: int = 40
       ) -> LXVariable:
           """
           Hyperbolic tangent function: tanh(x) = (e^x - e^(-x)) / (e^x + e^(-x))

           Use Cases:
               - Activation functions in neural networks
               - Saturation curves
               - Signal processing

           Args:
               var: Input variable
               linearizer: Piecewise linearizer instance
               segments: Number of segments (default: 40 for smooth approximation)

           Returns:
               Output variable representing tanh(var) ∈ [-1, 1]

           Example:
               >>> # Activation function
               >>> activation = LXNonLinearFunctions.tanh(
               ...     net_input,
               ...     linearizer,
               ...     segments=50
               ... )
           """
           return linearizer.approximate_function(
               lambda x: math.tanh(x),
               var,
               num_segments=segments,
               adaptive=True  # tanh curves sharply around x=0
           )

       @staticmethod
       def relu(var: LXVariable, linearizer: LXPiecewiseLinearizer) -> LXVariable:
           """
           Rectified Linear Unit: ReLU(x) = max(0, x)

           Use Cases:
               - Neural network activation

           Args:
               var: Input variable with finite bounds lower < 0 < upper
               linearizer: Piecewise linearizer instance

           Returns:
               Output variable representing max(0, var)

           Example:
               >>> output = LXNonLinearFunctions.relu(weighted_sum, linearizer)
           """
           # ReLU is piecewise linear: explicit breakpoints at the bounds and
           # at the kink make the approximation exact (uniform segments are
           # exact only when 0 happens to be a breakpoint).
           return linearizer.approximate_function(
               lambda x: max(0.0, x),
               var,
               breakpoints=[var.lower_bound, 0.0, var.upper_bound],
           )

Customizing Existing Techniques
--------------------------------

The techniques are plain functions, not classes with overridable hooks, so there is
nothing to subclass. To change a formulation, edit the function (or add a new one)
and keep its contract:

- create variables and rows only with ``aux.var`` / ``aux.row``, and pass ``key``
  through unchanged;
- return the ``LXVarRef`` that equals the item's value;
- read bounds from the ``LXVarRef`` arguments (``lower``, ``upper``, ``bounded``);
  raise ``ValueError`` when an exact formulation needs bounds that are missing;
- when the result is a relaxation rather than exact, record it as ``_mccormick``
  does: append a label to the ``relaxation`` list the engine passes in (it sets
  ``solution.relaxation``) and warn with ``lumix.utils._warn.warn_user(...,
  UserWarning)`` so the warning points at the user's code.

Example: Stronger rows for a continuous product
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``product`` in ``lumix/linearization/techniques/bilinear.py`` picks one of
``_and`` (binary × binary), ``_binary_times`` (binary × bounded),
``_expansion`` (integer × anything) and ``_mccormick`` (continuous × continuous).
Extra cuts for the continuous case belong in ``_mccormick`` itself, after the four
envelope rows and before ``return z``:

.. code-block:: python

   # a * x + b * y - z >= c, with a, b, c computed from the bounds
   aux.row(tag, "cut1", key, [(z, -1.0), (x, a), (y, b)], ">=", c)

Each new row must be valid for every ``(x, y)`` in the bounds; otherwise the
"relaxation" cuts off feasible points.

Creating Custom Formulations
-----------------------------

Example: A new piecewise-linear method
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``piecewise`` in ``lumix/linearization/techniques/piecewise.py`` dispatches on the
method name to ``_sos2``, ``_incremental`` and ``_logarithmic``. A new method is
one more function with the same signature, ``f(aux, tag, key, x, bps, values) ->
LXVarRef``, and one more branch in ``piecewise``. The helper ``_lambdas`` already
builds the convex-combination weights and the output variable:

.. code-block:: python

   def _convex_hull(aux, tag, key, x, bps, values):
       """Weights only, no segment binaries: exact for a convex function that is
       minimized (a relaxation otherwise)."""
       lam, y = _lambdas(aux, tag, key, x, bps, values)
       return y

   # in piecewise():
   if method == "convex_hull":
       return _convex_hull(aux, tag, key, x, list(breakpoints), list(values))

Also accept the new name where methods are typed (``Literal["sos2", "incremental",
"logarithmic"]`` in ``LXPiecewiseLinearTerm``, ``LXLinearizerConfig.pwl_method``
and ``LXPiecewiseLinearizer.approximate_function``).

Testing Custom Extensions
--------------------------

Unit Tests
~~~~~~~~~~

A technique can be tested without a model: build an ``LXAuxFactory`` and
``LXVarRef`` arguments by hand and inspect what it created.

.. code-block:: python

   from lumix import LXVariable
   from lumix.core.canonical import canonical_bounds
   from lumix.linearization.refs import LXAuxFactory, LXVarRef


   def test_positive_part_rows():
       x = LXVariable[str, float]("x").continuous().bounds(lower=-5, upper=3)
       ref = LXVarRef(x, None, *canonical_bounds(x), x.var_type)
       aux = LXAuxFactory()

       z = positive_part(aux, aux.tag("pos", ["x"]), None, ref, convex=False)

       assert (z.lower, z.upper) == (0.0, 3.0)
       assert len(aux.variables) == 2          # z and the binary
       assert len(aux.constraints) == 3

Integration Tests
~~~~~~~~~~~~~~~~~

.. code-block:: python

   def test_custom_term_in_model():
       model = build_test_model()             # uses the new term

       linearizer = LXLinearizer(model, ORTOOLS_CAPABILITIES, LXLinearizerConfig())
       linearized = linearizer.linearize_model()

       assert linearized.name.endswith("_linearized")
       assert linearizer.get_statistics()["auxiliary_constraints"] > 0

       solution = LXOptimizer().use_solver("ortools").solve(linearized)
       assert solution.is_optimal()

Best Practices
--------------

1. **Follow the naming scheme**

   Let the factory name things. ``aux.tag(kind, names)`` gives every term its own
   tag (``aux_<kind>_<vars>_<n>``) and ``aux.var(tag, role, ...)`` the family
   ``<tag>_<role>``, so two terms on the same variables never clash. Use short,
   descriptive roles (``"z"``, ``"pick0"``, ``"bit3"``).

2. **Keep techniques pure**

   A technique has no state of its own. Everything it creates goes through the
   ``LXAuxFactory`` it is given; the engine collects ``aux.variables`` and
   ``aux.constraints`` into the new model.

3. **Document the formulation**

   .. code-block:: python

      def positive_part(aux, tag, key, x, convex):
          """``z = max(x, 0)``.

          Rows: ``z >= x``; when not ``convex``, also ``z <= x - lo (1 - on)``
          and ``z <= hi on`` with one binary ``on``. Needs finite bounds then.
          """

4. **Handle edge cases**

   - Read bounds from the ``LXVarRef`` (``x.lower``, ``x.upper``, ``x.bounded``),
     not from the variable: they are already intersected and rounded by
     ``canonical_bounds``.
   - Raise ``ValueError`` naming the variable when an exact formulation needs
     finite bounds. Use ``config.big_m_value`` only as a documented fallback and
     warn when you do (``_binary_times`` and ``_indicator`` do this).
   - Items with weight 0 of kind ``abs`` and ``product`` are skipped by the engine;
     add your kind to that check if the same holds for it. Do not compare
     coefficients against ``LXLinearizerConfig.tolerance``: it is a deprecated
     field with no effect.

5. **Add configuration options only when a technique reads them**

   A new ``LXLinearizerConfig`` field must be read by a technique (the engine
   passes ``self.config`` where it is needed, as for ``product``). A field that no
   technique reads belongs in ``_UNUSED`` in ``lumix/linearization/config.py``,
   so setting it issues a ``DeprecationWarning`` instead of silently doing nothing.

Documentation
-------------

Document your extension in the appropriate places:

1. **Docstrings**: Add Google-style docstrings to new functions and classes
2. **User Guide**: Add usage examples to the user guide
3. **API Reference**: Ensure autodoc picks up public classes
4. **Development Guide**: Update :doc:`linearization-architecture` (dispatch,
   cost table)

See Also
--------

- :doc:`linearization-architecture` - Architecture overview
- :doc:`extending-nonlinear` - Adding new nonlinear term classes
- :doc:`design-decisions` - Design rationale
- :doc:`/user-guide/linearization/index` - User guide
- :doc:`/api/linearization/index` - API reference
