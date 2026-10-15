Bilinear Product Linearization
===============================

Guide for linearizing bilinear products (x × y) in optimization models.

Overview
--------

Bilinear products appear frequently in optimization:

- **Revenue**: price × quantity
- **Energy**: power × time
- **Logistics**: distance × flow
- **Finance**: return × allocation

The :class:`~lumix.linearization.techniques.bilinear.LXBilinearLinearizer` class
automatically selects the appropriate linearization technique based on variable types.

Variable Type Combinations
---------------------------

The linearization method depends on the types of the two variables. Every
product is exact except the product of two continuous variables:

.. list-table::
   :header-rows: 1
   :widths: 18 22 25 15 20

   * - Type 1
     - Type 2
     - Method
     - Result
     - Complexity
   * - Binary
     - Binary
     - AND logic (``b · b = b``)
     - Exact
     - 1 binary, 3 constraints
   * - Binary
     - Continuous or integer, bounded
     - Bound constraints
     - Exact
     - 1 variable, 4 constraints
   * - Binary
     - Unbounded
     - Bound constraints with ``big_m_value``; ``UserWarning``
     - Exact if ``|y| <= big_m_value``
     - 1 variable, 4 constraints
   * - Integer
     - Integer or continuous
     - Binary expansion of the integer factor
     - Exact
     - k binaries + k products with a binary
   * - Continuous
     - Continuous
     - McCormick envelopes; ``UserWarning``
     - **Relaxation** (``solution.relaxation``)
     - 1 variable, 4 constraints

.. versionchanged:: 0.3.0
   Products with an integer factor are exact (binary expansion); they used McCormick
   envelopes before. A product of two continuous variables issues a ``UserWarning``
   and sets ``solution.relaxation``; before 0.3.0 its bound was reported as the
   optimum. Two of the four binary × continuous constraints had wrong signs.

.. _product-vs-quadratic:

Products on Variable Families
-----------------------------

``add_product(x, y)`` on two variable families multiplies the instances **with the
same index key** and sums the results, like the other terms of an
``LXNonLinearExpression`` (see :doc:`engine`). The families must have the same
index keys; a single variable is broadcast to every instance. A quadratic
objective (:class:`~lumix.core.expressions.LXQuadraticExpression`) multiplies
all pairs instead:

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * -
     - ``LXNonLinearExpression().add_product(x, y)``
     - ``LXQuadraticExpression().add_quadratic(x, y)``
   * - Meaning
     - :math:`\sum_k c \, x_k y_k` (per instance)
     - :math:`\sum_i \sum_j c \, x_i y_j` (all pairs)
   * - Families
     - same index keys (or a single variable)
     - any two families
   * - Coefficient
     - a number
     - a number or ``coeff(a, b)`` per pair
   * - x, y over keys ``A``, ``B``
     - ``x[A]·y[A] + x[B]·y[B]``
     - ``x[A]·y[A] + x[A]·y[B] + x[B]·y[A] + x[B]·y[B]``
   * - Solvers
     - linearized on every solver (needs ``enable_linearization()``)
     - native on Gurobi and CPLEX; linearized with ``enable_linearization()`` on
       the others

For the per-instance square use ``add_squared(x)`` (:math:`\sum_i x_i^2`) in a
quadratic expression, or ``add_product(x, x)`` in a nonlinear one.

.. code-block:: python

   # Revenue of each product: sum over p of price[p] * quantity[p]
   revenue = LXNonLinearExpression().add_product(price, quantity)

   # Interaction of every pair (i, j): sum over i, j of w[i] * w[j]
   risk = LXQuadraticExpression().add_quadratic(w, w)

Binary × Binary (AND Logic)
----------------------------

Mathematical Formulation
~~~~~~~~~~~~~~~~~~~~~~~~

For z = x × y where x, y ∈ {0, 1}:

.. math::

   z \leq x \\
   z \leq y \\
   z \geq x + y - 1 \\
   z \in \{0, 1\}

**Logical Interpretation:**

- z = 1 if and only if both x = 1 and y = 1
- Implements logical AND operation

Example
~~~~~~~

.. code-block:: python

   from lumix import LXModel, LXVariable
   from lumix.linearization.techniques import LXBilinearLinearizer
   from lumix.linearization.config import LXLinearizerConfig
   from lumix.nonlinear.terms import LXBilinearTerm

   # Define binary variables (linearize_bilinear takes single variables)
   is_open = LXVariable[Facility, int]("is_open").binary()
   is_served = LXVariable[Customer, int]("is_served").binary()

   # Create bilinear term: facility_open AND customer_served
   term = LXBilinearTerm(
       var1=is_open,
       var2=is_served,
       coefficient=1.0
   )

   # Linearize
   config = LXLinearizerConfig()
   linearizer = LXBilinearLinearizer(config)
   z = linearizer.linearize_bilinear(term)

   # z represents is_open AND is_served

Use Cases
~~~~~~~~~

- **Facility Location**: Open facility AND serve customer
- **Scheduling**: Assign shift AND assign driver
- **Logic**: Boolean AND operations in constraints

Binary × Continuous (Big-M Method)
-----------------------------------

Mathematical Formulation
~~~~~~~~~~~~~~~~~~~~~~~~

For z = b × x where b ∈ {0, 1}, x ∈ [L, U]:

.. math::

   z \leq U \cdot b \\
   z \geq L \cdot b \\
   z \leq x - L(1 - b) \\
   z \geq x - U(1 - b) \\
   z \in [\min(L, 0), \max(U, 0)]

where L and U are the bounds of x. When x has no finite bound, ``big_m_value``
(:doc:`config`) replaces the missing bound and a ``UserWarning`` is issued; the
product is then exact only if ``|x|`` stays within ``big_m_value``.

**Behavior:**

- When b = 0: z = 0 (forced by first two constraints)
- When b = 1: z = x (forced by last two constraints)

Example
~~~~~~~

.. code-block:: python

   # Binary variable: is the route open?
   is_open = (
       LXVariable[Route, int]("is_open")
       .binary()
       .indexed_by(lambda r: r.id)
       .from_data(routes)
   )

   # Continuous variable: flow amount
   flow = (
       LXVariable[Route, float]("flow")
       .continuous()
       .bounds(lower=0, upper=1000)
       .indexed_by(lambda r: r.id)
       .from_data(routes)
   )

   # Product per route: flow[r] counts only if route r is open
   expr = LXNonLinearExpression().add_product(is_open, flow)

Choosing Big-M Value
~~~~~~~~~~~~~~~~~~~~~

The constants come from the variable's bounds, so the best Big-M is a tight bound
on the variable:

.. code-block:: python

   flow = LXVariable[Route, float]("flow").continuous().bounds(lower=0, upper=1000)
   # z <= 1000 b, z >= flow - 1000 (1 - b): no big_m_value needed

``big_m_value`` is used only when the variable has no finite bound. It must then be
at least the largest ``|x|`` of any solution, but not much larger (numerics):

.. code-block:: python

   # For an unbounded flow that never exceeds 10,000
   config = LXLinearizerConfig(big_m_value=1e4)

Use Cases
~~~~~~~~~

- **Conditional Flow**: Flow only if route is open
- **Pricing**: Revenue only if product is sold
- **Scheduling**: Work hours only if worker is assigned

Continuous × Continuous (McCormick Envelopes)
----------------------------------------------

Mathematical Formulation
~~~~~~~~~~~~~~~~~~~~~~~~

For z = x × y where x ∈ [xL, xU], y ∈ [yL, yU]:

.. math::

   z \geq x_L \cdot y + y_L \cdot x - x_L \cdot y_L \\
   z \geq x_U \cdot y + y_U \cdot x - x_U \cdot y_U \\
   z \leq x_L \cdot y + y_U \cdot x - x_L \cdot y_U \\
   z \leq x_U \cdot y + y_L \cdot x - x_U \cdot y_L

**Geometric Interpretation:**

These four constraints form the convex hull of the bilinear function
over the box [xL, xU] × [yL, yU].

.. warning::

   McCormick envelopes are a **relaxation**: they are the tightest linear
   relaxation of the product over the given bounds, but ``z`` can differ from
   ``x · y`` inside the box. The reported optimum is a bound (an upper bound when
   maximizing, a lower bound when minimizing) and may not be attainable. LumiX
   issues a ``UserWarning`` containing "McCormick" and sets
   ``solution.relaxation`` to ``True`` (see
   :doc:`/user-guide/solution/accessing-solutions`).

   For an exact result, make one factor integer or binary, or use a quadratic
   objective (:class:`~lumix.core.expressions.LXQuadraticExpression`) on Gurobi
   or CPLEX, which solve it natively.

Both variables need finite bounds; otherwise ``ValueError`` is raised.

Example
~~~~~~~

.. code-block:: python

   # Continuous variable: price ($/unit)
   price = (
       LXVariable[Product, float]("price")
       .continuous()
       .bounds(lower=10, upper=100)
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

   # Continuous variable: quantity (units)
   quantity = (
       LXVariable[Product, float]("quantity")
       .continuous()
       .bounds(lower=0, upper=1000)
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

   # Product per product p: revenue = price[p] × quantity[p]
   revenue = LXNonLinearExpression().add_product(price, quantity)
   # UserWarning: ... McCormick envelopes, a relaxation ...

Importance of Tight Bounds
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Tighter bounds = stronger relaxation = faster solving**

Example of bound impact:

.. code-block:: python

   # Wide bounds (weak relaxation)
   x = LXVariable[Model, float]("x").bounds(lower=0, upper=1000)
   y = LXVariable[Model, float]("y").bounds(lower=0, upper=1000)
   # McCormick creates large convex hull

   # Tight bounds (strong relaxation)
   x = LXVariable[Model, float]("x").bounds(lower=10, upper=50)
   y = LXVariable[Model, float]("y").bounds(lower=5, upper=20)
   # McCormick creates tight convex hull

LumiX uses the bounds as given; it does not tighten them (the
``mccormick_tighten_bounds`` and ``auto_detect_bounds`` settings have no effect and
are deprecated, see :doc:`config`).

Use Cases
~~~~~~~~~

- **Revenue**: price × quantity
- **Energy**: power × time
- **Economics**: elasticity × demand
- **Engineering**: force × displacement

Integer × Integer or Continuous (Binary Expansion)
---------------------------------------------------

.. versionadded:: 0.3.0

Mathematical Formulation
~~~~~~~~~~~~~~~~~~~~~~~~

An integer variable x ∈ [L, U] is written in binary digits,

.. math::

   x = L + \sum_{k=0}^{K-1} 2^k d_k, \qquad d_k \in \{0, 1\}

so that

.. math::

   x \cdot y = L \cdot y + \sum_{k=0}^{K-1} 2^k (d_k \cdot y)

and each :math:`d_k \cdot y` is an exact binary × variable product. K is the number
of bits of U − L. When both factors are integer, the one with the smaller range is
expanded.

**Requirements:**

- The integer factor needs finite bounds; fractional bounds are rounded inward
  (``[0.5, 3.7]`` becomes ``[1, 3]``).
- K must not exceed ``LXLinearizerConfig.binary_expansion_bits`` (default 10, that
  is at most 1024 values); otherwise ``ValueError`` is raised. Raise the setting, or
  use Gurobi or CPLEX for a quadratic objective.
- The other factor should be bounded; it is multiplied by binaries (see above).

.. code-block:: python

   units = LXVariable[Product, int]("units").integer().bounds(lower=0, upper=3)
   price = LXVariable[Product, float]("price").continuous().bounds(lower=0, upper=4)
   # Exact: units = d0 + 2 d1, units * price = d0 * price + 2 (d1 * price)
   revenue = LXNonLinearExpression().add_product(units, price)

Advanced: Multi-dimensional Products
-------------------------------------

For products of more than two variables, apply linearization recursively:

.. code-block:: python

   # For x × y × z:
   # Step 1: w = x × y (linearize)
   # Step 2: result = w × z (linearize)

   from lumix.linearization.techniques import LXBilinearLinearizer

   config = LXLinearizerConfig()
   linearizer = LXBilinearLinearizer(config)

   # First product: w = x × y
   term_xy = LXBilinearTerm(var1=x, var2=y, coefficient=1.0)
   w = linearizer.linearize_bilinear(term_xy)

   # Second product: result = w × z
   term_wz = LXBilinearTerm(var1=w, var2=z, coefficient=1.0)
   result = linearizer.linearize_bilinear(term_wz)

   # Add all auxiliary elements to model
   for var in linearizer.auxiliary_vars:
       model.add_variable(var)
   for constraint in linearizer.auxiliary_constraints:
       model.add_constraint(constraint)

Complete Example
----------------

Production Planning with Revenue Maximization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dataclasses import dataclass

   from lumix import (LXConstraint, LXLinearExpression, LXModel,
                      LXNonLinearExpression, LXVariable)
   from lumix.linearization import LXLinearizer, LXLinearizerConfig
   from lumix.solvers import GLPK_CAPABILITIES, LXOptimizer

   # Define data
   @dataclass
   class Product:
       id: str
       min_quantity: float
       max_quantity: float
       min_price: float
       max_price: float

   products = [
       Product("A", 0, 1000, 10, 100),
       Product("B", 0, 500, 20, 150),
   ]

   # Define variables
   # Integer quantity: the product with a continuous price is exact
   quantity = (
       LXVariable[Product, int]("quantity")
       .integer()
       .bounds(lower=0, upper=1000)
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

   price = (
       LXVariable[Product, float]("price")
       .continuous()
       .bounds(lower=10, upper=150)
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

   # Build model
   model = LXModel("production").add_variables(quantity, price)

   # Objective: maximize revenue, sum over p of price[p] × quantity[p]
   # This will be automatically linearized
   model.maximize(LXNonLinearExpression().add_product(price, quantity))

   # Constraints
   # Total quantity constraint
   model.add_constraint(
       LXConstraint("total_quantity")
       .expression(LXLinearExpression().add_term(quantity, 1.0))
       .le()
       .rhs(1200)
   )

   # Solve with linearization
   optimizer = LXOptimizer().use_solver("glpk")

   linearizer = LXLinearizer(model, GLPK_CAPABILITIES, LXLinearizerConfig())
   linearized_model = linearizer.linearize_model()

   # Get statistics
   stats = linearizer.get_statistics()
   print(f"Linearization added:")
   print(f"  - {stats['auxiliary_variables']} variables")
   print(f"  - {stats['auxiliary_constraints']} constraints")

   # Solve
   solution = optimizer.solve(linearized_model)
   print(f"Optimal revenue: ${solution.objective_value:,.2f}")

Performance Tips
----------------

1. **Always Provide Bounds**

   .. code-block:: python

      # Good: McCormick will be tight
      x = LXVariable[Model, float]("x").bounds(lower=0, upper=100)

      # Bad: Wide default bounds, weak relaxation
      x = LXVariable[Model, float]("x")  # No bounds!

2. **Use Appropriate Big-M**

   Only needed for binary × unbounded products:

   .. code-block:: python

      # Problem-specific, not default
      config = LXLinearizerConfig(big_m_value=1000)  # Not 1e6!

3. **McCormick Envelopes Are a Relaxation**

   A continuous × continuous product of an ``LXNonLinearExpression`` is replaced by
   its McCormick envelope on every solver, so the linearized optimum is a bound, not
   necessarily the true optimum; check ``solution.relaxation``. Tight variable
   bounds make the envelope tighter. A quadratic objective
   (``LXQuadraticExpression``) is solved natively by Gurobi and CPLEX.

4. **Keep Integer Ranges Small**

   The binary expansion adds one binary and one binary product per bit of the
   integer range; ``binary_expansion_bits`` caps it.

See Also
--------

- :doc:`config` - Configuration guide
- :doc:`engine` - Linearization engine
- :doc:`/api/linearization/index` - API reference
- :doc:`/development/linearization-architecture` - Architecture details
