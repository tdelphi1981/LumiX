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

Selecting Instances by Key
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. versionadded:: 0.2.0

Instead of a ``where`` filter you can list the index keys of the instances a
term uses. The result is the same model; large models build much faster.

.. code-block:: python

   # Only plants "TRB" and "SAM"
   expr.add_term(open_plant, coeff=lambda p: p.fixed_cost, keys=["TRB", "SAM"])

See :doc:`../performance` for the key format and the rules.

Quadratic Expressions
---------------------

For quadratic objectives (risk, portfolio optimization):

.. code-block:: python

   from lumix import LXQuadraticExpression

   # Portfolio variance: 0.5 * w^T * Cov * w
   risk_expr = LXQuadraticExpression().add_quadratic(
       weights, weights, coeff=lambda a, b: 0.5 * cov[a.id][b.id]
   )

   # Add linear terms (expected returns)
   risk_expr.linear_terms.add_term(weights, lambda a: a.expected_return)

   model.minimize(risk_expr)

.. versionchanged:: 0.3.0

   Quadratic terms work on whole variable families:

   - ``add_quadratic(var1, var2, coeff)`` adds ``coeff * var1[a] * var2[b]`` for
     **every pair** of instances ``(a, b)``. ``coeff`` is a number or a function
     ``coeff(a, b)`` of the two instances.
   - ``add_squared(var, coeff)`` adds ``coeff * var[a]**2`` for every instance
     ``a`` (the diagonal only). ``coeff`` is a number or ``coeff(a)``.
   - ``add_quadratic_term(var1, var2, coefficient)`` is an alias of
     ``add_quadratic``.

   Quadratic expressions are allowed **only in the objective**; a quadratic
   constraint raises ``ValueError``. Gurobi and CPLEX solve quadratic objectives
   natively, including nonconvex ones. OR-Tools, CP-SAT and GLPK raise a clear
   error; with ``LXOptimizer().enable_linearization()`` products of single
   variables (one instance each) are linearized instead.

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

.. versionchanged:: 0.3.0

   ``+``, ``-`` and ``*`` return a **new** expression and leave their operands
   unchanged (before 0.3.0, ``+`` and ``*`` modified the left operand). Use
   ``+=`` and ``*=`` to change an expression in place. Constants may be any real
   number, including NumPy scalars.

Addition and Subtraction
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   total = revenue_expr + cost_expr   # new expression
   total = expr + 100                 # add a constant
   margin = revenue_expr - cost_expr  # subtraction and negation (-expr)
   total = sum([e1, e2, e3])          # sum() works too
   expr += other_expr                 # in place

Adding a quadratic expression to a linear one gives a quadratic expression.

Multiplication
~~~~~~~~~~~~~~

.. code-block:: python

   scaled = expr * 2.0  # Scale by constant (also 2.0 * expr)
   expr *= 2.0          # in place

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
