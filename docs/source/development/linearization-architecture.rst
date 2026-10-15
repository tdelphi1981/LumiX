Linearization Architecture
==========================

Deep dive into the linearization module's architecture and design patterns.

.. versionchanged:: 0.3.0
   The linearizer was rebuilt on the canonical expansion of the model: terms are
   expanded per variable instance, each item is linearized by a pure technique
   function on references to single solver variables, and the user's model is never
   modified. The sections below describe this design.

Design Philosophy
-----------------

The linearization module follows these key principles:

1. **Automatic Detection**: Scan models for nonlinear terms without user intervention
2. **One Expansion**: Nonlinear terms are expanded per instance by the same
   canonical builder that :meth:`LXModel.to_canonical()
   <lumix.core.model.LXModel.to_canonical>` uses, so the linearizer and external
   engines see the same items
3. **Type- and Use-Based Selection**: Choose techniques from the variable types and
   from the direction in which each item is used (pushed down, pushed up, fixed)
4. **Exact by Default**: Every technique is exact except McCormick envelopes for
   continuous × continuous products, which are reported as a relaxation
5. **No Side Effects**: The user's model and expressions are never modified; every
   ``linearize_model()`` call starts afresh

Architecture Overview
---------------------

.. mermaid::

   classDiagram
       class LXLinearizer {
           +model: LXModel
           +capability: LXSolverCapability
           +config: LXLinearizerConfig
           +auxiliary_vars: List
           +auxiliary_constraints: List
           +relaxation_terms: List
           +needs_linearization() bool
           +linearize_model() LXModel
           +get_statistics() dict
           -_linearize_items(items, sign) List
           -_technique(item, refs, tag, sign) LXVarRef
           -_indicator(builder, term) None
       }

       class LXCanonicalBuilder {
           +prepare() List
           +nonlinear(expr, where) List
           +quadratic_items(expr) List
           +linear_row(expr, row, where) Tuple
       }

       class LXCanonicalNonlinear {
           +kind: str
           +variables: Tuple
           +coeff: float
           +params: Dict
           +term: int
           +key: Any
       }

       class LXVarRef {
           +var: LXVariable
           +key: Any
           +lower: float
           +upper: float
           +var_type: LXVarType
           +add_to(expr, coeff)
       }

       class LXAuxFactory {
           +variables: List
           +constraints: List
           +tag(kind, names) str
           +var(tag, role, key, kind, lower, upper) LXVarRef
           +row(tag, role, key, terms, sense, rhs) None
       }

       class Techniques {
           <<module functions>>
           +absolute(aux, tag, key, x, convex)
           +minmax(aux, tag, key, op, refs, coefficients, convex)
           +product(aux, tag, key, x, y, config, relaxation)
           +piecewise(aux, tag, key, x, breakpoints, values, method)
       }

       LXLinearizer --> LXCanonicalBuilder
       LXCanonicalBuilder --> LXCanonicalNonlinear
       LXLinearizer --> LXVarRef
       LXLinearizer --> LXAuxFactory
       LXLinearizer --> Techniques
       Techniques --> LXAuxFactory

Component Details
-----------------

LXLinearizer: The Main Engine
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:class:`~lumix.linearization.engine.LXLinearizer` (``lumix/linearization/engine.py``)
orchestrates one run:

1. ``_reset()`` creates a new :class:`~lumix.linearization.refs.LXAuxFactory`, so
   auxiliary names, counters and relaxation records never carry over between calls.
2. An :class:`~lumix.core.canonical.LXCanonicalBuilder` is built on the user's model;
   ``builder.prepare()`` lists every variable instance, and each becomes an
   :class:`~lumix.linearization.refs.LXVarRef` (family, index key, bounds, type).
3. The objective and every constraint are rewritten into new expressions:

   - ``builder.nonlinear(expr, where)`` expands the nonlinear terms into
     :class:`~lumix.core.canonical.LXCanonicalNonlinear` items;
   - ``_linearize_items(items, sign)`` returns one output reference per item;
   - the new expression is the linear part, the constant, and
     ``coeff * output`` for each item.

   A quadratic objective is rewritten the same way from
   ``builder.quadratic_items(expr)`` when the solver cannot solve it natively.
4. A new ``LXModel`` named ``<name>_linearized`` receives the original variables,
   the rewritten objective and constraints, and the auxiliary variables and
   constraints. ``relaxation_terms`` lists the McCormick products; the optimizer
   sets ``solution.relaxation`` from it.

**Direction (``sign``):** ``_linearize_items`` receives where the items' values are
pushed: ``+1`` pushed down (a minimized objective, a ``<=`` row), ``-1`` pushed up
(a maximized objective, a ``>=`` row), ``0`` fixed (an ``==`` row; a quadratic
objective, whose products are always exact or McCormick). ``_technique`` combines
the sign with the item's coefficient to choose the cheap or the exact form:

.. code-block:: python

   if item.kind == "abs":
       return absolute(aux, tag, key, refs[0], convex=sign * item.coeff > 0)
   if item.kind in ("min", "max"):
       convex = sign < 0 if item.kind == "min" else sign > 0
       return minmax(aux, tag, key, item.kind, refs, item.params["coefficients"], convex)

**Indexed constraints:** for a constraint with ``indexed_by``, ``_row_terms`` adds
the outputs with row-dependent coefficients: a row that is an instance of the term's
family takes only that instance's item; a row from other data takes all items (the
narrowing rule of :doc:`canonical-model`). The row is matched against every
multi-instance variable family of the term, not only the first, so the result does
not depend on the order of the arguments. A row of a family's own data type that is
not one of its instances takes nothing, and the ``lumix.linearization.engine``
logger reports it once per family.

**Indicators** are not items: ``_indicator`` turns each
:class:`~lumix.nonlinear.terms.LXIndicatorTerm` into Big-M rows, with M from the
bounds of the expression (``linear_row`` + ``scaled_bounds``).

Canonical Expansion
~~~~~~~~~~~~~~~~~~~

``LXCanonicalBuilder.nonlinear`` (``lumix/core/canonical.py``) applies the
per-instance rule: for every term it aligns the term's families by index key
(``_aligned``), raises ``ValueError`` for families with different keys, and
broadcasts single variables. Each item carries the positions of its variables,
the term's position (``term``) and the instance key (``key``). Piecewise items get
numeric ``breakpoints`` and ``values``, with the settings the term leaves as
``None`` taken from the configuration (``piecewise_points``). The same items fill
``LXCanonicalModel.objective_nonlinear``; see :doc:`canonical-model`.

LXVarRef and LXAuxFactory
~~~~~~~~~~~~~~~~~~~~~~~~~

``lumix/linearization/refs.py`` holds the two building blocks of the techniques.

- ``LXVarRef`` is one solver variable: an instance (``key``) of a family
  (``var``), with its bounds (±inf when open) and type. ``add_to(expr, coeff)``
  adds it to a linear expression with ``keys=[key]``. ``LXVarRef.single(var, what)``
  makes a reference to a variable with exactly one instance (used by the public
  wrappers and by indicators).
- ``LXAuxFactory`` creates the auxiliary elements of one run. ``tag(kind, names)``
  numbers a term (``aux_abs_x_1``); ``var(tag, role, key, ...)`` adds an instance
  ``key`` to the family ``<tag>_<role>`` and returns its reference; ``row(tag, role,
  key, terms, sense, rhs)`` adds the constraint ``<tag>_<role>[<key>]``. An
  auxiliary family is indexed by the instance keys of its term, so the solution
  reports ``{"p": 3.0, "q": 4.0}`` for ``aux_abs_x_1_z``. A term on a single variable
  gets scalar auxiliary variables.

Techniques
~~~~~~~~~~

The techniques are pure functions on references; they create elements only through
the factory and return the reference of the item's value:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Function
     - Formulation
   * - ``absminmax.absolute``
     - ``z >= x``, ``z >= -x``; when not ``convex``, a binary and two rows
       ``z <= ±x + M(...)`` make it exact (needs finite bounds)
   * - ``absminmax.minmax``
     - ``z <= c_i x_i`` (min) / ``z >= c_i x_i`` (max); when not ``convex``, one
       selection binary per argument
   * - ``bilinear.product``
     - binary × binary: AND; binary × variable: four bound rows (``big_m_value``
       for open bounds, with a warning); integer factor: binary expansion; two
       continuous: McCormick, appended to ``relaxation`` with a warning
   * - ``piecewise.piecewise``
     - SOS2 (segment binaries), incremental, or logarithmic, from numeric
       breakpoints and values

Public Wrappers
~~~~~~~~~~~~~~~

:class:`~lumix.linearization.techniques.bilinear.LXBilinearLinearizer` and
:class:`~lumix.linearization.techniques.piecewise.LXPiecewiseLinearizer` keep the
public API for direct use. Each owns an ``LXAuxFactory`` whose lists are exposed as
``auxiliary_vars`` / ``auxiliary_constraints``; ``linearize_bilinear(term)`` and
``approximate_function(func, var, ...)`` take **single** variables
(``LXVarRef.single``), call ``product`` / ``piecewise``, and return the output
variable. The engine does not use them.

LXLinearizerConfig: Configuration Management
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Design Pattern:** Dataclass with sensible defaults

.. code-block:: python

   @dataclass
   class LXLinearizerConfig:
       big_m_value: float = 1e6            # open bounds in binary products, indicators
       pwl_num_segments: int = 20          # piecewise terms with num_segments=None
       pwl_method: str = "sos2"            # piecewise terms with method=None
       adaptive_breakpoints: bool = True   # piecewise terms with adaptive=None
       binary_expansion_bits: int = 10     # largest integer factor in a product
       # default_method, tolerance, verbose_logging, prefer_sos2,
       # auto_detect_bounds, mccormick_tighten_bounds: no effect,
       # DeprecationWarning when set (removed in 0.4.0)

Data Flow
---------

Linearization Process
~~~~~~~~~~~~~~~~~~~~~

.. mermaid::

   sequenceDiagram
       participant User
       participant Linearizer
       participant Builder as LXCanonicalBuilder
       participant Techniques
       participant Factory as LXAuxFactory

       User->>Linearizer: linearize_model()
       Linearizer->>Factory: new factory (fresh state)
       Linearizer->>Builder: prepare()
       Builder-->>Linearizer: variable instances (LXVarRef)
       Linearizer->>Builder: nonlinear(objective)
       Builder-->>Linearizer: items (kind, variables, coeff, params, term, key)
       loop For each item
           Linearizer->>Techniques: technique(item refs, sign)
           Techniques->>Factory: var() / row()
           Techniques-->>Linearizer: output LXVarRef
       end
       Linearizer->>Linearizer: same for each constraint (sign from its sense)
       Linearizer-->>User: new LXModel (original model unchanged)

Extension Points
----------------

Adding New Linearization Techniques
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To add a new kind of term:

1. **Expand it into items** in ``LXCanonicalBuilder.nonlinear`` (a new ``kind``,
   its variables aligned with ``_aligned``, numeric ``params``).

2. **Write a technique function** on references:

.. code-block:: python

   from lumix.linearization.refs import LXAuxFactory, LXVarRef

   def square_root(aux: LXAuxFactory, tag: str, key, x: LXVarRef) -> LXVarRef:
       """z = sqrt(x), exact on the breakpoints."""
       z = aux.var(tag, "z", key, "continuous", 0.0, x.upper ** 0.5)
       # ... aux.row(tag, "...", key, [(z, 1.0), (x, -c)], "<=", rhs) ...
       return z

3. **Dispatch it** in ``LXLinearizer._technique`` and add a tag in ``_TAG`` (the
   ``<kind>`` part of the auxiliary names).

4. **Add Configuration** only for settings a technique reads:

.. code-block:: python

   @dataclass
   class LXLinearizerConfig:
       # ... existing fields ...

       # Conic settings
       conic_approximation_order: int = 2

Custom Function Approximations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add to ``LXNonLinearFunctions``:

.. code-block:: python

   class LXNonLinearFunctions:
       # ... existing methods ...

       @staticmethod
       def tanh(var, linearizer, segments=40):
           """Hyperbolic tangent: tanh(x)"""
           return linearizer.approximate_function(
               lambda x: math.tanh(x),
               var,
               num_segments=segments,
               adaptive=True
           )

Testing Strategy
----------------

Unit Tests
~~~~~~~~~~

Test individual linearization techniques:

.. code-block:: python

   def test_mccormick_relaxation():
       """Test McCormick envelope for continuous × continuous."""
       config = LXLinearizerConfig()
       linearizer = LXBilinearLinearizer(config)

       # Create bilinear term on two single variables
       x = LXVariable[None, float]("x").continuous().bounds(lower=0, upper=10)
       y = LXVariable[None, float]("y").continuous().bounds(lower=0, upper=5)
       term = LXBilinearTerm(x, y, 1.0)

       # Linearize
       with pytest.warns(UserWarning, match="McCormick"):
           z = linearizer.linearize_bilinear(term)

       # Verify
       assert z is not None
       assert len(linearizer.auxiliary_vars) == 1
       assert len(linearizer.auxiliary_constraints) == 4  # McCormick
       assert linearizer.relaxation_terms == ["x * y"]

Integration Tests
~~~~~~~~~~~~~~~~~

Test end-to-end linearization, and compare small models with a brute-force
enumeration (``tests/test_w4_linearization.py`` does this for random models on
every available solver):

.. code-block:: python

   def test_linearize_production_model():
       """Test linearization of production planning model."""
       model = build_production_model()  # Contains bilinear revenue

       linearizer = LXLinearizer(model, GLPK_CAPABILITIES, LXLinearizerConfig())

       # Linearize
       linearized = linearizer.linearize_model()

       # Verify structure
       assert linearized.name == "production_linearized"
       assert len(linearized.variables) > len(model.variables)

       # Solve
       solution = LXOptimizer().use_solver("glpk").solve(linearized)
       assert solution.is_optimal()

Accuracy Tests
~~~~~~~~~~~~~~

Validate approximation accuracy:

.. code-block:: python

   def test_pwl_approximation_accuracy():
       """Test piecewise-linear approximation accuracy."""
       import numpy as np
       from lumix.linearization.techniques.piecewise import adaptive_breakpoints

       points = adaptive_breakpoints(math.exp, 0.0, 5.0, 50)
       values = [math.exp(p) for p in points]

       # Compare the interpolation with the function between the breakpoints
       x_test = np.linspace(0, 5, 1000)
       approx = np.interp(x_test, points, values)
       max_error = float(np.max(np.abs(approx - np.exp(x_test)) / np.exp(x_test)))

       # Verify accuracy
       assert max_error < 0.01, f"Approximation error too large: {max_error}"

Performance Considerations
--------------------------

Memory Management
~~~~~~~~~~~~~~~~~

**Auxiliary Variable Storage:**

- One ``LXAuxFactory`` per run holds all auxiliary elements
- The auxiliary elements of one term and role form one family indexed by the
  instance keys, so a term on a large family adds a few families, not one
  variable object per instance

Computational Complexity
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Operation
     - Complexity
     - Notes
   * - Expand terms
     - O(instances)
     - One item per instance of each term
   * - Bilinear linearization
     - O(1) per item
     - O(K) for an integer factor with K digits
   * - Abs / min / max
     - O(n) per item
     - n = number of arguments
   * - PWL (SOS2)
     - O(n) per item
     - n = num_segments
   * - PWL (incremental)
     - O(n) per item
     - More variables than SOS2
   * - Adaptive breakpoints
     - O(n) per term
     - 10 n + 1 function evaluations

Future Enhancements
-------------------

Planned Features
~~~~~~~~~~~~~~~~

1. **Native Solver Features**: Pass SOS2 sets, indicator and general constraints to
   solvers that support them
2. **Bound Tightening**: Automatic bound propagation for McCormick
3. **Conic Constraints**: Linearization of second-order cone constraints
4. **Custom SOS Types**: Support for SOS1 and higher-order SOS

See Also
--------

- :doc:`extending-linearization` - How to extend linearization
- :doc:`canonical-model` - Canonical model and nonlinear items
- :doc:`design-decisions` - Design rationale
- :doc:`/user-guide/linearization/index` - User guide
- :doc:`/api/linearization/index` - API reference
