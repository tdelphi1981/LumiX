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

Three formulation methods available:

1. **SOS2**: Special Ordered Set Type 2 (best when solver supports)
2. **Incremental**: Binary selection variables
3. **Logarithmic**: Gray code encoding (efficient for many segments)

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
