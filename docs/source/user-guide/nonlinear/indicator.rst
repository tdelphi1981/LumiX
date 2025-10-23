Indicator Constraints
=====================

The :class:`~lumix.nonlinear.terms.LXIndicatorTerm` represents conditional constraints:
"if binary_var equals condition, then constraint holds".

Overview
--------

Indicator constraints express if-then logic:

.. math::

   \text{if } b = 1 \text{ then } ax \leq c

**Common Use Cases:**

- Conditional capacity constraints
- Minimum order quantities
- Fixed charges and activation
- Logical implications in scheduling
- Resource dependencies

Linearization Method (Big-M)
-----------------------------

For constraint "if b = condition then expr ≤ rhs", linearize as:

.. math::

   \text{expr} \leq \text{rhs} + M \cdot (1 - b) \quad \text{if condition = True} \\
   \text{expr} \leq \text{rhs} + M \cdot b \quad \text{if condition = False}

Where M is a sufficiently large constant (Big-M).

**Key Properties:**

- No auxiliary variables needed
- 1 constraint per indicator term
- Requires computing appropriate M value
- M computed from variable bounds

Basic Usage
-----------

Minimum Order Quantity
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXVariable, LXLinearExpression
   from lumix.nonlinear import LXIndicatorTerm

   # Binary: order placed?
   order_placed = LXVariable[Product, int]("ordered").binary()

   # Continuous: order quantity
   quantity = LXVariable[Product, float]("quantity").continuous().bounds(0, 1000)

   # If order_placed = 1, then quantity >= 100
   min_order = LXIndicatorTerm(
       binary_var=order_placed,
       condition=True,
       linear_expr=LXLinearExpression().add_term(quantity, 1.0),
       sense='>=',
       rhs=100.0
   )

Facility Capacity
~~~~~~~~~~~~~~~~~

.. code-block:: python

   # If facility is open, capacity <= max_capacity
   capacity_limit = LXIndicatorTerm(
       binary_var=is_open,
       condition=True,
       linear_expr=LXLinearExpression().add_term(flow, 1.0),
       sense='<=',
       rhs=500.0
   )

Complete Examples
-----------------

Example 1: Facility Location with Minimum Throughput
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dataclasses import dataclass
   from lumix import LXModel, LXVariable, LXLinearExpression
   from lumix.nonlinear import LXIndicatorTerm

   @dataclass
   class Facility:
       id: str
       min_throughput: float
       max_throughput: float

   facilities = [...]

   is_open = LXVariable[Facility, int]("is_open").binary().from_data(facilities)
   throughput = LXVariable[Facility, float]("throughput").continuous().bounds(0).from_data(facilities)

   # If open, throughput >= min_throughput
   min_throughput_constraints = [
       LXIndicatorTerm(
           binary_var=is_open,
           condition=True,
           linear_expr=LXLinearExpression().add_term(throughput, 1.0),
           sense='>=',
           rhs=f.min_throughput
       )
       for f in facilities
   ]

See full documentation for more examples.

See Also
--------

- :class:`~lumix.nonlinear.terms.LXIndicatorTerm` - API reference
- :doc:`bilinear` - Bilinear products
- :doc:`piecewise` - Piecewise-linear functions
