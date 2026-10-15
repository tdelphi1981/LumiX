Indicator Constraints
=====================

The :class:`~lumix.nonlinear.terms.LXIndicatorTerm` represents conditional constraints:
"if binary_var equals condition, then constraint holds".

Overview
--------

Indicator constraints express if-then logic:

.. math::

   b = \text{condition} \;\Rightarrow\; \text{expr} \;\square\; \text{rhs},
   \qquad \square \in \{\leq, \geq, =\}

``LXIndicatorTerm(binary_var=b, condition=True, linear_expr=expr, sense=">=", rhs=100)``
means "if b = 1 then expr ≥ 100"; with ``condition=False`` the constraint applies
when b = 0. When the condition does not hold, the constraint is not enforced.

**Common Use Cases:**

- Conditional capacity constraints
- Minimum order quantities
- Fixed charges and activation
- Logical implications in scheduling
- Resource dependencies

.. versionchanged:: 0.3.0
   ``>=`` and ``==`` indicators work (they crashed), the Big-M rows have the
   right signs, the constant of ``linear_expr`` is kept (it was dropped), and M is
   computed from the bounds of the expression (it was always ``big_m_value``).

Linearization Method (Big-M)
-----------------------------

Let a = 1 − b when ``condition=True`` and a = b when ``condition=False``, so that
a = 0 exactly when the constraint must hold. LumiX adds

.. math::

   \text{expr} \leq \text{rhs} + M^{+} a \quad \text{for } \leq \text{ and } = \\
   \text{expr} \geq \text{rhs} - M^{-} a \quad \text{for } \geq \text{ and } =

with :math:`M^{+} = \max(\text{expr}) - \text{rhs}` and
:math:`M^{-} = \text{rhs} - \min(\text{expr})`, where the maximum and minimum of
``expr`` (constant included) come from the bounds of its variables. A row whose M
is not positive is left out, because it holds whatever b is.

If ``expr`` is unbounded in the needed direction, ``big_m_value`` from
:class:`~lumix.linearization.config.LXLinearizerConfig` (default 1e6) is used and a
``UserWarning`` is issued; the indicator is then correct only if
:math:`|\text{expr} - \text{rhs}|` stays within ``big_m_value``. Bounding the
variables avoids this.

**Key Properties:**

- No auxiliary variables needed
- 1 constraint per indicator term (2 for ``==``)
- M computed from variable bounds
- ``binary_var`` must be a **single** binary variable: a scalar, or a family with
  one instance. A family with several instances raises ``ValueError`` ("single
  variable"). ``linear_expr`` may use any variables; select one instance of a
  family with ``add_term(var, coeff, keys=[key])``.

Using Indicators in a Model
---------------------------

An indicator is a constraint, not a value. Add it to an
:class:`~lumix.core.expressions.LXNonLinearExpression` with ``add_nonlinear_term``;
wherever that expression is used (the objective or a constraint), linearization
adds the indicator's rows to the model, and the indicator contributes nothing to
the expression's value:

.. code-block:: python

   objective = LXNonLinearExpression().add_linear(costs)
   objective.add_nonlinear_term(min_order)      # a constraint, not a cost
   model.minimize(objective)

   solution = LXOptimizer().use_solver("ortools").enable_linearization().solve(model)

``add_indicator(b, condition, expr)`` is a shorthand for
``LXIndicatorTerm(b, condition, expr)`` with the defaults ``sense="<="`` and
``rhs=0.0`` (``b = condition ⇒ expr ≤ 0``); use ``LXIndicatorTerm`` for another
sense or right-hand side.

A model with indicators must be linearized before it is solved
(``enable_linearization()`` or :class:`~lumix.linearization.engine.LXLinearizer`);
``model.to_canonical()`` raises ``ValueError`` for an objective with indicator
terms.

Basic Usage
-----------

Minimum Order Quantity
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXVariable, LXLinearExpression
   from lumix.nonlinear import LXIndicatorTerm

   # Binary: order placed? (a single variable)
   order_placed = LXVariable[Product, int]("ordered").binary()

   # Continuous: order quantity
   quantity = LXVariable[Product, float]("quantity").continuous().bounds(0, 1000)

   # If order_placed = 1, then quantity >= 100 (M = 100 - 0)
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

   # If facility is open, flow <= 500
   capacity_limit = LXIndicatorTerm(
       binary_var=is_open,
       condition=True,
       linear_expr=LXLinearExpression().add_term(flow, 1.0),
       sense='<=',
       rhs=500.0
   )

   # If facility is closed, flow == 0
   no_flow = LXIndicatorTerm(
       binary_var=is_open,
       condition=False,
       linear_expr=LXLinearExpression().add_term(flow, 1.0),
       sense='==',
       rhs=0.0
   )

Complete Examples
-----------------

Example 1: Facility Location with Minimum Throughput
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dataclasses import dataclass
   from lumix import (LXConstraint, LXLinearExpression, LXModel,
                      LXNonLinearExpression, LXOptimizer, LXVariable)
   from lumix.nonlinear import LXIndicatorTerm

   @dataclass
   class Facility:
       id: str
       min_throughput: float
       max_throughput: float
       fixed_cost: float

   facilities = [Facility("A", 40, 100, 500), Facility("B", 60, 80, 300)]

   throughput = (
       LXVariable[Facility, float]("throughput")
       .continuous()
       .bounds(lower=0, upper=100)
       .indexed_by(lambda f: f.id)
       .from_data(facilities)
   )

   # One binary per facility: an indicator needs a single variable
   is_open = {f.id: LXVariable[None, int](f"is_open_{f.id}").binary() for f in facilities}

   objective = LXNonLinearExpression()
   for f in facilities:
       flow_f = LXLinearExpression().add_term(throughput, 1.0, keys=[f.id])
       # If open: min_throughput <= throughput[f] <= max_throughput
       objective.add_nonlinear_term(
           LXIndicatorTerm(is_open[f.id], True, flow_f, ">=", f.min_throughput))
       objective.add_nonlinear_term(
           LXIndicatorTerm(is_open[f.id], True, flow_f, "<=", f.max_throughput))
       # If closed: throughput[f] == 0
       objective.add_nonlinear_term(
           LXIndicatorTerm(is_open[f.id], False, flow_f, "==", 0.0))

   # Linear part of the objective: fixed costs minus revenue
   costs = LXLinearExpression().add_term(throughput, -10.0)
   for f in facilities:
       costs.add_term(is_open[f.id], f.fixed_cost)
   objective.add_linear(costs)

   model = LXModel("facilities").add_variable(throughput)
   for var in is_open.values():
       model.add_variable(var)
   model.add_constraint(
       LXConstraint("demand")
       .expression(LXLinearExpression().add_term(throughput, 1.0))
       .le()
       .rhs(150)
   )
   model.minimize(objective)

   solution = LXOptimizer().use_solver("ortools").enable_linearization().solve(model)
   # objective -700: both open, throughput {"A": 70, "B": 80}

See Also
--------

- :class:`~lumix.nonlinear.terms.LXIndicatorTerm` - API reference
- :doc:`bilinear` - Bilinear products
- :doc:`piecewise` - Piecewise-linear functions
- :doc:`/user-guide/linearization/config` - ``big_m_value``
