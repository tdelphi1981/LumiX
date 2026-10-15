Piecewise-Linear Functions
===========================

The :class:`~lumix.nonlinear.terms.LXPiecewiseLinearTerm` approximates arbitrary nonlinear
functions using piecewise-linear segments.

Overview
--------

Approximate any univariate nonlinear function f(x) with a piecewise-linear function.

**Common Use Cases:**

- Exponential/logarithmic costs
- Tiered pricing and discounts
- Sigmoid activation functions
- Nonlinear utility functions
- Step functions

Linearization Methods
---------------------

Three formulation methods available, all exact for the piecewise-linear function
through the breakpoints:

1. **SOS2**: Convex-combination weights, adjacency enforced with segment binaries
2. **Incremental**: Binary selection variables
3. **Logarithmic**: Gray code encoding (log₂ binaries, efficient for many segments)

Pass ``breakpoints=[...]`` to use your own breakpoints (for a function given by
data points), and note that the domain constrains the variable; see
:doc:`/user-guide/linearization/piecewise`.

``num_segments``, ``adaptive`` and ``method`` default to ``None``: the values of
:class:`~lumix.linearization.config.LXLinearizerConfig` apply (``pwl_num_segments``
20, ``adaptive_breakpoints`` ``True``, ``pwl_method`` ``"sos2"``), and a value given
on the term wins. Adaptive breakpoints are deterministic. On a variable family the
term applies to every instance: ``add_piecewise(x, f)`` is :math:`\sum_i f(x_i)`.

.. versionchanged:: 0.3.0
   The term defaults are ``None`` (taken from the configuration), adaptive
   breakpoints are deterministic, and a term on a family applies per instance.

Basic Usage
-----------

Exponential Function
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import math
   from lumix import LXVariable
   from lumix.nonlinear import LXPiecewiseLinearTerm

   time = LXVariable[Task, float]("time").continuous().bounds(0, 5)

   exp_cost = LXPiecewiseLinearTerm(
       var=time,
       func=lambda t: math.exp(t),
       num_segments=30,
       adaptive=True,
       method="sos2"
   )

Tiered Discount
~~~~~~~~~~~~~~~

.. code-block:: python

   quantity = LXVariable[Order, float]("qty").continuous().bounds(0, 2000)

   def discount_func(q):
       if q < 100:
           return 1.0
       elif q < 1000:
           return 0.9
       else:
           return 0.8

   discount = LXPiecewiseLinearTerm(
       var=quantity,
       func=discount_func,
       num_segments=50
   )

See Also
--------

- :class:`~lumix.nonlinear.terms.LXPiecewiseLinearTerm` - API reference
- :doc:`/user-guide/linearization/piecewise` - Piecewise linearization details
- :doc:`/user-guide/linearization/nonlinear-functions` - Pre-built functions
