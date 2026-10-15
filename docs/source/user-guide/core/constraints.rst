Constraints Guide
=================

Constraints define the feasible region of your optimization model.

Overview
--------

Constraints restrict the values that variables can take. In LumiX, :class:`~lumix.core.constraints.LXConstraint`
represents constraint **families** that expand automatically based on data.

Constraint Structure
--------------------

Every constraint has three parts:

.. code-block:: python

   LXConstraint("name")
       .expression(lhs_expr)  # Left-hand side
       .le()                  # Sense: <=, >=, or ==
       .rhs(value)            # Right-hand side

**Mathematical Form**: ``LHS {<=, >=, ==} RHS``

Constraint names must be unique within a model; duals, row activity and the
analysis tools look rows up by name.

.. versionchanged:: 0.3.0
   ``LXModel.add_constraint`` raises ``ValueError`` for a second constraint with
   an existing name (before, the second one hid the first from duals, activity
   and analysis).

Constraint Senses
-----------------

Less-Than-Or-Equal (<=)
~~~~~~~~~~~~~~~~~~~~~~~

For upper limits and capacity constraints:

.. code-block:: python

   capacity = (
       LXConstraint("capacity")
       .expression(
           LXLinearExpression().add_term(production, lambda p: p.resource_usage)
       )
       .le()  # <=
       .rhs(max_capacity)
   )

**Use for**: Capacity limits, maximum bounds, budget constraints

Greater-Than-Or-Equal (>=)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

For lower limits and requirements:

.. code-block:: python

   demand = (
       LXConstraint("demand")
       .expression(
           LXLinearExpression().add_term(production, 1.0)
       )
       .ge()  # >=
       .rhs(minimum_demand)
   )

**Use for**: Minimum requirements, demand satisfaction, quotas

Equality (==)
~~~~~~~~~~~~~

For exact requirements and balance equations:

.. code-block:: python

   flow_balance = (
       LXConstraint("balance")
       .expression(
           LXLinearExpression()
           .add_term(inflow, 1.0)
           .add_term(outflow, -1.0)
       )
       .eq()  # ==
       .rhs(0)
   )

**Use for**: Flow conservation, balance equations, exact targets

Single vs. Family Constraints
------------------------------

Single Constraint
~~~~~~~~~~~~~~~~~

One constraint for the entire model:

.. code-block:: python

   total_budget = (
       LXConstraint("budget")
       .expression(
           LXLinearExpression().add_term(production, lambda p: p.cost)
       )
       .le()
       .rhs(max_budget)
   )

Constraint Family
~~~~~~~~~~~~~~~~~

One constraint per data instance:

.. code-block:: python

   resource_limits = (
       LXConstraint[Resource]("capacity")
       .expression(
           LXLinearExpression()
           .add_term(production, lambda p, r: p.usage[r.id])
       )
       .le()
       .rhs(lambda r: r.capacity)  # Data-driven RHS
       .from_data(resources)
       .indexed_by(lambda r: r.id)
   )

This creates one constraint per resource.

.. versionchanged:: 0.3.0
   A constraint with data (``from_data`` / ``from_model``) must also call
   ``indexed_by``; without it LumiX raises ``ValueError`` instead of silently
   building one combined row.

.. versionchanged:: 0.3.0
   When a constraint family is defined over the same data as a variable, a term
   on that variable is narrowed to the row's own instance only if its coefficient
   and filter take one argument. Give the coefficient two arguments
   (``lambda var_instance, row_instance: ...``) to reach other instances, for
   example ``inv[t-1]`` in an inventory balance. See :doc:`/development/canonical-model`.

.. note::
   Narrowing applies to terms whose variable family has the row's own data type.
   In a row, a term on a multi-part variable (``indexed_by_product`` or
   ``indexed_by_join``) is **not** narrowed to the row's part: it covers every
   instance unless you select them. Give ``where`` two arguments, the instance
   (a tuple of its parts) and the row, for example

   .. code-block:: python

      # supply[s]: the flows that leave supplier s
      LXLinearExpression().add_term(flow, 1.0, where=lambda f, s: f[0].id == s.id)

   or pick the instances with ``keys=`` (see :doc:`/user-guide/performance`).


Right-Hand Side (RHS)
---------------------

Constant RHS
~~~~~~~~~~~~

.. code-block:: python

   .rhs(100)  # Fixed value

Data-Driven RHS
~~~~~~~~~~~~~~~

.. code-block:: python

   .rhs(lambda r: r.capacity)  # From data attribute

Expression RHS
~~~~~~~~~~~~~~

.. code-block:: python

   .rhs(lambda r: r.base_capacity * r.efficiency_factor)

.. versionchanged:: 0.3.0
   When ``rhs`` is called more than once, the last call wins, whether it gives a
   value or a function.

Multi-Model Constraints
-----------------------

Constraints can reference multiple variable families:

.. code-block:: python

   # Balance constraint: production + inventory_start = demand + inventory_end
   balance = (
       LXConstraint[Product]("balance")
       .expression(
           LXLinearExpression()
           .add_term(production, 1.0)
           .add_term(inventory_start, 1.0)
           .add_term(demand_var, -1.0)
           .add_term(inventory_end, -1.0)
       )
       .eq()
       .rhs(0)
       .from_data(products)
       .indexed_by(lambda p: p.id)
   )

.. tip::

   For constraints built in a loop over one dimension of a multi-indexed
   variable, pass ``keys=[(row.id, other.id) for other in others]`` instead of a
   ``where`` filter. See :doc:`../performance`.

Goal Programming
----------------

Mark constraints as goals for multi-objective optimization:

.. code-block:: python

   profit_goal = (
       LXConstraint("profit")
       .expression(profit_expr)
       .ge()
       .rhs(target_profit)
       .as_goal(priority=1, weight=1.0)  # High priority goal
   )

   quality_goal = (
       LXConstraint("quality")
       .expression(quality_expr)
       .ge()
       .rhs(target_quality)
       .as_goal(priority=2, weight=0.5)  # Lower priority
   )

**See**: :doc:`/examples/index` for goal programming examples

Common Patterns
---------------

Resource Capacity
~~~~~~~~~~~~~~~~~

.. code-block:: python

   LXConstraint[Resource]("capacity")
       .expression(
           LXLinearExpression()
           .add_term(production, lambda p, r: p.resource_usage[r.id])
       )
       .le()
       .rhs(lambda r: r.capacity)
       .from_data(resources)
       .indexed_by(lambda r: r.id)

Demand Satisfaction
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   LXConstraint[Customer]("demand")
       .expression(
           LXLinearExpression()
           .add_term(shipment, lambda s, c: 1.0 if s.destination == c else 0)
       )
       .ge()
       .rhs(lambda c: c.demand)
       .from_data(customers)
       .indexed_by(lambda c: c.id)

Assignment Constraints
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Each task assigned to exactly one worker
   LXConstraint[Task]("assign_task")
       .expression(
           LXLinearExpression()
           .add_multi_term(assignment, lambda w, t2, t1=task: 1.0 if t1 == t2 else 0)
       )
       .eq()
       .rhs(1)
       .from_data(tasks)
       .indexed_by(lambda t: t.id)

Best Practices
--------------

1. **Use Descriptive Names**

   .. code-block:: python

      # Good
      resource_capacity = LXConstraint[Resource]("resource_capacity")

      # Bad
      c1 = LXConstraint("c1")

2. **Choose Appropriate Sense**

   - Use LE for upper limits
   - Use GE for lower limits
   - Use EQ only when necessary (more restrictive)

3. **Index by Data**

   .. code-block:: python

      # Good: One constraint per resource
      .from_data(resources).indexed_by(lambda r: r.id)

      # Bad: Manual loops

4. **Data-Driven RHS**

   .. code-block:: python

      # Good: RHS from data
      .rhs(lambda r: r.capacity)

      # Less flexible: Hard-coded
      .rhs(1000)

Next Steps
----------

- :doc:`expressions` - Build constraint expressions
- :doc:`models` - Add constraints to models
- :doc:`/api/core/index` - Full API reference
