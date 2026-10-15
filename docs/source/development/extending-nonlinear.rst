Extending Nonlinear Module
==========================

Guide for adding custom nonlinear term types to LumiX.

Overview
--------

You can extend the nonlinear module by:

1. **Adding New Term Types**: Define new dataclasses for additional nonlinear operations
2. **Integration**: Expand your terms into canonical items that the linearizer
   understands
3. **Custom Linearization**: Add technique functions for new item kinds

Adding New Term Types
---------------------

Step-by-Step Guide
~~~~~~~~~~~~~~~~~~

Example: Adding Cubic Terms
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Let's add support for cubic terms (x³):

**Step 1**: Define the dataclass in `src/lumix/nonlinear/terms.py`:

.. code-block:: python

   @dataclass
   class LXCubicTerm:
       """Cubic term: coefficient * x³.

       Represents the cube of a variable, linearized using piecewise-linear
       approximation or auxiliary variables.

       Attributes:
           var: The variable to cube.
           coefficient: Coefficient to multiply the cubic term by (default: 1.0).

       Example:
           Cubic cost function::

               volume = LXVariable[Container, float]("volume").continuous().bounds(0, 10)
               cubic_cost = LXCubicTerm(var=volume, coefficient=2.5)
       """

       var: LXVariable
       coefficient: float = 1.0

**Step 2**: Export from `__init__.py`:

.. code-block:: python

   from .terms import (
       LXAbsoluteTerm,
       LXBilinearTerm,
       LXCubicTerm,  # Add new term
       LXIndicatorTerm,
       LXMinMaxTerm,
       LXPiecewiseLinearTerm,
   )

   __all__ = [
       "LXAbsoluteTerm",
       "LXBilinearTerm",
       "LXCubicTerm",  # Add to exports
       "LXIndicatorTerm",
       "LXMinMaxTerm",
       "LXPiecewiseLinearTerm",
   ]

**Step 3**: Hook the term into linearization.

The linearizer does not see term classes. ``LXCanonicalBuilder.nonlinear``
(``src/lumix/core/canonical.py``) expands each term into per-instance items
``LXCanonicalNonlinear(kind, variables, coeff, params, term, key)``, and
``LXLinearizer._technique`` (``src/lumix/linearization/engine.py``) dispatches on
``item.kind``. A term with no branch in ``nonlinear`` raises
``ValueError("Unsupported nonlinear term type: ...")``. There are three steps:

a. emit an item for the term in ``LXCanonicalBuilder.nonlinear``;
b. if the item has a new ``kind``, add the kind to ``_TAG`` in ``engine.py``
   (the short name used in auxiliary variable names);
c. for a new kind, add a branch in ``LXLinearizer._technique`` that calls a pure
   function ``f(aux, tag, key, *refs, ...) -> LXVarRef`` written with
   ``LXAuxFactory.var`` / ``LXAuxFactory.row``.

A cubic term is a function of one variable, so it can reuse the existing
``"piecewise"`` kind and needs step (a) only. Add a branch before the final
``else`` in ``nonlinear``; ``_piecewise_params`` fills the open fields from
``LXLinearizerConfig`` and the variable's bounds, and ``_aligned`` yields one item
per instance of the variable family:

.. code-block:: python

   elif isinstance(term, LXCubicTerm):
       params = self._piecewise_params(
           LXPiecewiseLinearTerm(term.var, lambda t: t ** 3))
       for key, ps in self._aligned([term.var], where):
           items.append(LXCanonicalNonlinear("piecewise", ps, float(term.coefficient),
                                             params, index, key))

The engine adds ``coeff * y`` for the piecewise output ``y`` of each item, so the
coefficient stays outside the function. The variable needs finite bounds (or the
term needs ``x_min`` / ``x_max``) for the breakpoints.

**Step 4**: Add tests (flat files under ``tests/``, e.g.
``tests/test_w4_linearization.py``):

.. code-block:: python

   from lumix import LXLinearizer, LXModel, LXNonLinearExpression, LXVariable
   from lumix.solvers import ORTOOLS_CAPABILITIES

   def test_cubic_term():
       var = LXVariable[str, float]("x").continuous().bounds(lower=0, upper=10)
       term = LXCubicTerm(var=var, coefficient=2.0)

       assert term.var is var
       assert term.coefficient == 2.0

   def test_cubic_linearization():
       var = LXVariable[str, float]("x").continuous().bounds(lower=0, upper=10)
       model = LXModel("m").add_variable(var)
       model.minimize(LXNonLinearExpression().add_nonlinear_term(LXCubicTerm(var=var)))

       linearizer = LXLinearizer(model, ORTOOLS_CAPABILITIES)
       linearized = linearizer.linearize_model()
       assert linearizer.get_statistics()["piecewise_terms"] == 1

More Examples
~~~~~~~~~~~~~

Both examples need a new item kind, so they use all three steps.

Logical AND Term
^^^^^^^^^^^^^^^^

.. code-block:: python

   @dataclass
   class LXAndTerm:
       """Logical AND of multiple binary variables.

       z = x₁ AND x₂ AND ... AND xₙ

       Attributes:
           vars: List of binary variables to AND together.
           coefficient: Weight of z (default: 1.0).
       """
       vars: List[LXVariable]
       coefficient: float = 1.0

   # (a) in LXCanonicalBuilder.nonlinear
   elif isinstance(term, LXAndTerm):
       for key, ps in self._aligned(term.vars, where):
           items.append(LXCanonicalNonlinear("and", ps, float(term.coefficient), {},
                                             index, key))

   # (b) in engine.py:  _TAG["and"] = "and"

   # (c) the technique, and a branch in LXLinearizer._technique
   def logical_and(aux, tag, key, refs):
       """z = 1 iff every ref is 1."""
       z = aux.var(tag, "z", key, "binary")
       for i, r in enumerate(refs):                                    # z <= x_i
           aux.row(tag, f"le{i}", key, [(z, 1.0), (r, -1.0)], "<=", 0.0)
       aux.row(tag, "ge_sum", key, [(z, 1.0)] + [(r, -1.0) for r in refs],
               ">=", 1.0 - len(refs))                                  # z >= sum(x_i) - n + 1
       return z

   if item.kind == "and":
       return logical_and(self._aux, tag, key, refs)

Absolute Difference
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   @dataclass
   class LXAbsDifferenceTerm:
       """Absolute difference between two variables: |x - y|.

       Attributes:
           var1: First variable.
           var2: Second variable.
           coefficient: Coefficient (default: 1.0).
       """
       var1: LXVariable
       var2: LXVariable
       coefficient: float = 1.0

   # (a) emit LXCanonicalNonlinear("absdiff", ps, float(term.coefficient), {}, index, key)
   #     for key, ps in self._aligned([term.var1, term.var2], where)
   # (b) _TAG["absdiff"] = "absdiff"
   # (c) the technique (convex use only: |x - y| minimized, or in a <= row
   #     with a positive weight; see techniques/absminmax.py for the exact form)
   def abs_difference(aux, tag, key, x, y):
       span = max(abs(x.upper - y.lower), abs(y.upper - x.lower))
       z = aux.var(tag, "z", key, "continuous", 0.0, span)
       aux.row(tag, "ge_pos", key, [(z, 1.0), (x, -1.0), (y, 1.0)], ">=", 0.0)
       aux.row(tag, "ge_neg", key, [(z, 1.0), (x, 1.0), (y, -1.0)], ">=", 0.0)
       return z

   if item.kind == "absdiff":
       if not sign * item.coeff > 0:
           raise ValueError("|x - y| is only supported where it is pushed down")
       return abs_difference(self._aux, tag, key, refs[0], refs[1])

``sign`` is ``+1`` where the value is pushed down (minimized objective, ``<=``
row), ``-1`` where it is pushed up and ``0`` in equalities.

Custom Linearization Methods
-----------------------------

``LXLinearizer`` has no per-term methods to override and no configuration switch
that selects a formulation for products; ``product`` in
``src/lumix/linearization/techniques/bilinear.py`` chooses it from the variable
types. To change or add a formulation, edit or add a technique function and its
branch in ``_technique``. :doc:`extending-linearization` walks through it.

Testing Custom Terms
--------------------

Unit Tests
~~~~~~~~~~

.. code-block:: python

   def test_custom_term_creation():
       var = LXVariable[Data, float]("x").continuous()
       term = LXCubicTerm(var=var, coefficient=2.0)
       assert isinstance(term, LXCubicTerm)
       assert term.coefficient == 2.0

Integration Tests
~~~~~~~~~~~~~~~~~

.. code-block:: python

   def test_custom_term_in_model():
       var = LXVariable[str, float]("x").continuous().bounds(lower=0, upper=10)
       model = LXModel("test").add_variable(var)
       model.minimize(LXNonLinearExpression().add_nonlinear_term(LXCubicTerm(var=var)))

       linear_model = LXLinearizer(model, ORTOOLS_CAPABILITIES,
                                   LXLinearizerConfig()).linearize_model()

       assert len(linear_model.constraints) > 0
       solution = LXOptimizer().use_solver("ortools").solve(linear_model)
       assert solution.is_optimal()

Best Practices
--------------

Term Design
~~~~~~~~~~~

1. **Plain dataclasses**: Use ``@dataclass`` with no methods (LumiX terms are
   not frozen)
2. **Type annotations**: Full typing for all attributes
3. **Default values**: Provide sensible defaults where appropriate
4. **Documentation**: Comprehensive docstrings with examples

Linearization Implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Validate inputs**: Check variable bounds before linearization
2. **Efficient formulations**: Minimize auxiliary variables and constraints
3. **Numerical stability**: Avoid large M values
4. **Error handling**: Raise informative errors for invalid inputs

Example: Validation
^^^^^^^^^^^^^^^^^^^

Validate inside the technique, from the ``LXVarRef`` bounds (``±inf`` when open,
already intersected and rounded by ``canonical_bounds``):

.. code-block:: python

   def my_technique(aux, tag, key, x):
       if not x.bounded:
           raise ValueError(
               f"Variable '{x.var.name}' must have finite bounds for this term")
       ...

A coefficient of zero is not an error. The engine skips ``abs`` and ``product``
items with weight 0 (they contribute nothing and need no bounds); add a new kind
to that check in ``LXLinearizer._linearize_items`` if the same holds for it.

Documentation
~~~~~~~~~~~~~

Document your custom terms:

.. code-block:: python

   @dataclass
   class LXCustomTerm:
       """One-line summary.

       Detailed description of the term, including:
       - Mathematical formulation
       - Use cases
       - Linearization approach

       Attributes:
           var: Description of variable.
           param: Description of parameter.

       Example:
           Basic usage::

               var = LXVariable[Data, float]("x").continuous()
               term = LXCustomTerm(var=var, param=1.0)

       Note:
           Important notes about usage, requirements, or limitations.
       """
       var: LXVariable
       param: float = 1.0

Contributing to LumiX
---------------------

If you develop useful custom terms, consider contributing them to LumiX:

1. Fork the repository
2. Add your term following the guidelines above
3. Include comprehensive tests
4. Update documentation
5. Submit a pull request

See Also
--------

- :doc:`nonlinear-architecture` - Nonlinear module architecture
- :doc:`linearization-architecture` - Linearization engine architecture
- :doc:`extending-core` - Extending core components
