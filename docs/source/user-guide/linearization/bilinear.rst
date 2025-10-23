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

The linearization method depends on the types of the two variables:

.. list-table::
   :header-rows: 1
   :widths: 25 25 25 25

   * - Type 1
     - Type 2
     - Method
     - Complexity
   * - Binary
     - Binary
     - AND logic
     - 3 constraints
   * - Binary
     - Continuous
     - Big-M
     - 4 constraints
   * - Binary
     - Integer
     - Big-M
     - 4 constraints
   * - Continuous
     - Continuous
     - McCormick
     - 4 constraints
   * - Continuous
     - Integer
     - McCormick
     - 4 constraints
   * - Integer
     - Integer
     - McCormick
     - 4 constraints

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

   # Define binary variables
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

   z \leq M \cdot b \\
   z \geq m \cdot b \\
   z \leq x - m(1 - b) \\
   z \geq x - M(1 - b) \\
   z \in [m, M]

where M = upper bound of x, m = lower bound of x.

**Behavior:**

- When b = 0: z = 0 (forced by first two constraints)
- When b = 1: z = x (forced by last two constraints)

Example
~~~~~~~

.. code-block:: python

   # Binary variable: is facility open?
   is_open = (
       LXVariable[Facility, int]("is_open")
       .binary()
       .indexed_by(lambda f: f.id)
       .from_data(facilities)
   )

   # Continuous variable: flow amount
   flow = (
       LXVariable[Route, float]("flow")
       .continuous()
       .bounds(lower=0, upper=1000)
       .indexed_by(lambda r: r.id)
       .from_data(routes)
   )

   # Product: flow only if facility is open
   # z = is_open × flow
   term = LXBilinearTerm(var1=is_open, var2=flow, coefficient=1.0)

   config = LXLinearizerConfig(big_m_value=1000)
   linearizer = LXBilinearLinearizer(config)
   z = linearizer.linearize_bilinear(term)

Choosing Big-M Value
~~~~~~~~~~~~~~~~~~~~~

**Critical:** M must be large enough but not too large.

**Guidelines:**

1. **Use Variable Bounds:**

   .. code-block:: python

      flow = LXVariable[Route, float]("flow").bounds(lower=0, upper=1000)
      # M = 1000 (upper bound)

2. **Problem Knowledge:**

   .. code-block:: python

      # For normalized probabilities [0, 1]
      config = LXLinearizerConfig(big_m_value=1.0)

      # For prices up to $10,000
      config = LXLinearizerConfig(big_m_value=10000)

3. **Conservative Multiplier:**

   .. code-block:: python

      max_flow = 1000
      config = LXLinearizerConfig(big_m_value=10 * max_flow)

**Validation:**

.. code-block:: python

   # After solving, check that auxiliary variable doesn't hit M
   solution = optimizer.solve(linearized_model)

   for var_name, value in solution.variables.items():
       if "aux_prod" in var_name:
           assert value < 0.99 * config.big_m_value, \
               f"Variable {var_name} hit Big-M bound!"

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

.. note::

   McCormick envelopes provide the **tightest possible linear relaxation**
   of the bilinear term over the given bounds.

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

   # Product: revenue = price × quantity
   term = LXBilinearTerm(var1=price, var2=quantity, coefficient=1.0)

   config = LXLinearizerConfig(
       mccormick_tighten_bounds=True  # Improve relaxation
   )
   linearizer = LXBilinearLinearizer(config)
   revenue = linearizer.linearize_bilinear(term)

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

**Bound Tightening:**

Enable automatic bound tightening:

.. code-block:: python

   config = LXLinearizerConfig(
       mccormick_tighten_bounds=True,  # Apply preprocessing
       auto_detect_bounds=True  # Use variable bounds
   )

Use Cases
~~~~~~~~~

- **Revenue**: price × quantity
- **Energy**: power × time
- **Economics**: elasticity × demand
- **Engineering**: force × displacement

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

   from lumix import LXModel, LXVariable, LXConstraint
   from lumix.linearization import LXLinearizer, LXLinearizerConfig
   from lumix.solvers import LXOptimizer

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
   quantity = (
       LXVariable[Product, float]("quantity")
       .continuous()
       .indexed_by(lambda p: p.id)
       .bounds_func(lambda p: (p.min_quantity, p.max_quantity))
       .from_data(products)
   )

   price = (
       LXVariable[Product, float]("price")
       .continuous()
       .indexed_by(lambda p: p.id)
       .bounds_func(lambda p: (p.min_price, p.max_price))
       .from_data(products)
   )

   # Build model
   model = LXModel("production")

   # Objective: maximize revenue (bilinear: price × quantity)
   # This will be automatically linearized
   revenue_expr = price * quantity  # Nonlinear!
   model.maximize(revenue_expr)

   # Constraints
   # Total quantity constraint
   model.add_constraint(
       LXConstraint("total_quantity")
       .expression(quantity)
       .le()
       .rhs(1200)
   )

   # Configure linearization
   config = LXLinearizerConfig(
       default_method=LXLinearizationMethod.MCCORMICK,
       mccormick_tighten_bounds=True,
       verbose_logging=True
   )

   # Solve with linearization
   optimizer = LXOptimizer().use_solver("glpk")
   solver_capability = optimizer.get_capability()

   linearizer = LXLinearizer(model, solver_capability, config)
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

2. **Enable Bound Tightening**

   .. code-block:: python

      config = LXLinearizerConfig(mccormick_tighten_bounds=True)

3. **Use Appropriate Big-M**

   .. code-block:: python

      # Problem-specific, not default
      config = LXLinearizerConfig(big_m_value=1000)  # Not 1e6!

4. **Prefer Native Quadratic When Available**

   .. code-block:: python

      # For Gurobi/CPLEX with quadratic support,
      # solver may handle bilinear natively without linearization

See Also
--------

- :doc:`config` - Configuration guide
- :doc:`engine` - Linearization engine
- :doc:`/api/linearization/index` - API reference
- :doc:`/development/linearization-architecture` - Architecture details
