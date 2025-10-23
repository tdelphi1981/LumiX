Expressions Guide
=================

Expressions build mathematical formulas for objectives and constraints.

Expression Types
----------------

LumiX provides three expression types:

1. **Linear**: ``sum(coeff * var) + constant``
2. **Quadratic**: ``sum(coeff * var1 * var2) + linear + constant``
3. **Non-linear**: Absolute value, min/max, piecewise, etc.

Linear Expressions
------------------

Most common type for objectives and constraints:

.. code-block:: python

   from lumix import LXLinearExpression

   expr = (
       LXLinearExpression()
       .add_term(production, lambda p: p.profit)
       .add_term(inventory, lambda i: -i.holding_cost)
       .add_constant(100)
   )

Adding Terms
~~~~~~~~~~~~

.. code-block:: python

   # Constant coefficient
   expr.add_term(production, 1.0)

   # Data-driven coefficient
   expr.add_term(production, lambda p: p.profit)

   # Conditional coefficient
   expr.add_term(production, lambda p: p.profit if p.is_premium else 0)

Quadratic Expressions
---------------------

For quadratic objectives (risk, portfolio optimization):

.. code-block:: python

   from lumix import LXQuadraticExpression

   # Portfolio variance: 0.5 * w^T * Cov * w
   risk_expr = LXQuadraticExpression()

   for i, asset_i in enumerate(assets):
       for j, asset_j in enumerate(assets):
           covariance = cov_matrix[i][j]
           risk_expr.add_quadratic(
               weights[i],
               weights[j],
               coeff=0.5 * covariance
           )

   # Add linear terms (expected returns)
   risk_expr.linear_terms.add_term(weights, lambda a: a.expected_return)

Non-Linear Expressions
----------------------

Automatically linearized by LumiX:

Absolute Value
~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXNonLinearExpression

   expr = LXNonLinearExpression()
   expr.add_abs(deviation, coeff=1.0)  # |deviation|

Min/Max Functions
~~~~~~~~~~~~~~~~~

.. code-block:: python

   expr = LXNonLinearExpression()
   expr.add_min(x, y, z)  # min(x, y, z)
   expr.add_max(x, y)     # max(x, y)

Piecewise Linear
~~~~~~~~~~~~~~~~

.. code-block:: python

   expr = LXNonLinearExpression()
   expr.add_piecewise(
       var=time,
       breakpoints=[0, 40, 60],
       slopes=[1.0, 1.5, 2.0]  # Overtime rates
   )

Expression Operations
---------------------

Addition
~~~~~~~~

.. code-block:: python

   total = revenue_expr + cost_expr
   total = expr + 100  # Add constant

Multiplication
~~~~~~~~~~~~~~

.. code-block:: python

   scaled = expr * 2.0  # Scale by constant

Copying
~~~~~~~

.. code-block:: python

   expr_copy = expr.copy()

Common Patterns
---------------

Profit Objective
~~~~~~~~~~~~~~~~

.. code-block:: python

   profit = (
       LXLinearExpression()
       .add_term(production, lambda p: p.selling_price)
       .add_term(production, lambda p: -p.unit_cost)
       .add_constant(-fixed_cost)
   )

   model.maximize(profit)

Cost Minimization
~~~~~~~~~~~~~~~~~

.. code-block:: python

   cost = (
       LXLinearExpression()
       .add_term(shipment, lambda s: s.transport_cost)
       .add_term(inventory, lambda i: i.holding_cost)
   )

   model.minimize(cost)

Resource Usage
~~~~~~~~~~~~~~

.. code-block:: python

   usage = (
       LXLinearExpression()
       .add_term(production, lambda p: p.resource_usage)
   )

   model.add_constraint(
       LXConstraint("capacity").expression(usage).le().rhs(max_capacity)
   )

Multi-Variable Expressions
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   balance = (
       LXLinearExpression()
       .add_term(production, 1.0)
       .add_term(inventory_start, 1.0)
       .add_term(sales, -1.0)
       .add_term(inventory_end, -1.0)
   )

Best Practices
--------------

1. **Use Descriptive Variables**

   .. code-block:: python

      # Good
      total_profit = LXLinearExpression().add_term(...)

      # Bad
      e = LXLinearExpression().add_term(...)

2. **Break Down Complex Expressions**

   .. code-block:: python

      # Good: Readable
      revenue = LXLinearExpression().add_term(sales, lambda s: s.price)
      costs = LXLinearExpression().add_term(production, lambda p: p.cost)
      profit = revenue + costs * -1

      # Less readable: Everything in one
      profit = LXLinearExpression().add_term(...).add_term(...)...

3. **Use Appropriate Type**

   - Linear when possible (fastest)
   - Quadratic only when needed
   - Non-linear as last resort (automatically linearized)

4. **Leverage Lambdas**

   .. code-block:: python

      # Good: Data-driven
      .add_term(production, lambda p: p.profit_margin * p.base_price)

      # Less flexible: Hard-coded
      .add_term(production, 50.0)

Next Steps
----------

- :doc:`models` - Use expressions in models
- :doc:`/examples/index` - See examples
- :doc:`/api/core/index` - Full API reference
