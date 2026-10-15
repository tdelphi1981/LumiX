Linearization Engine
====================

Guide for using the main linearization engine to automatically convert nonlinear models.

Overview
--------

The :class:`~lumix.linearization.engine.LXLinearizer` class orchestrates the entire
linearization process:

1. **Scan** the objective and the constraints for nonlinear terms
2. **Expand** every term into one item per variable instance
3. **Select** a technique for each item (from the variable types and from how the
   item is used)
4. **Build** a new, linear model with auxiliary variables and constraints

The model you pass in is never changed.

Basic Usage
-----------

Simple Linearization Workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXModel
   from lumix.linearization import LXLinearizer, LXLinearizerConfig
   from lumix.solvers import GLPK_CAPABILITIES, LXOptimizer

   # Build model with nonlinear terms (naturally!)
   model = build_your_model()  # May contain bilinear, abs, etc.

   # Configure linearization
   config = LXLinearizerConfig(
       pwl_num_segments=30,
       adaptive_breakpoints=True
   )

   optimizer = LXOptimizer().use_solver("glpk")

   # Create linearizer (the capability constant of the solver you use)
   linearizer = LXLinearizer(model, GLPK_CAPABILITIES, config)

   # Check if linearization is needed
   if linearizer.needs_linearization():
       # Linearize the model
       linearized_model = linearizer.linearize_model()

       # Solve linearized model
       solution = optimizer.solve(linearized_model)
   else:
       # Model is already linear
       solution = optimizer.solve(model)

Most models do not need the linearizer directly:
``LXOptimizer().enable_linearization()`` runs it inside ``solve()`` with the
solver's capabilities and sets :attr:`solution.relaxation
<lumix.solution.solution.LXSolution.relaxation>`:

.. code-block:: python

   optimizer = LXOptimizer().use_solver("glpk").enable_linearization(pwl_segments=30)
   solution = optimizer.solve(model)

Key Methods
-----------

Constructor
~~~~~~~~~~~

.. py:method:: __init__(model, solver_capability, config=None)

   Initialize the linearization engine.

   **Parameters:**

   - ``model`` (LXModel): Model to linearize
   - ``solver_capability`` (LXSolverCapability): Solver capability information
   - ``config`` (LXLinearizerConfig, optional): Configuration (default: LXLinearizerConfig())

   **Example:**

   .. code-block:: python

      from lumix.linearization import LXLinearizer, LXLinearizerConfig
      from lumix.solvers import GLPK_CAPABILITIES

      linearizer = LXLinearizer(
          model=my_model,
          solver_capability=GLPK_CAPABILITIES,
          config=LXLinearizerConfig()
      )

Checking for Nonlinearity
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:method:: needs_linearization()

   Check if model contains nonlinear terms requiring linearization.

   **Returns:**

   - ``bool``: True if linearization is needed

   **Example:**

   .. code-block:: python

      if linearizer.needs_linearization():
          print("Model contains nonlinear terms")
          linearized = linearizer.linearize_model()
      else:
          print("Model is already linear")

Linearizing the Model
~~~~~~~~~~~~~~~~~~~~~

.. py:method:: linearize_model()

   Linearize the entire model.

   **Returns:**

   - ``LXModel``: New linearized model with auxiliary variables and constraints

   **What Happens:**

   1. Expands the nonlinear terms of the objective and of every constraint into
      one item per variable instance (see `Terms on Variable Families`_)
   2. For each item:

      - Determines variable types and bounds
      - Determines whether the item is pushed down, pushed up, or fixed by an
        equality (see `Cheap and Exact Forms`_)
      - Creates auxiliary variables and constraints
   3. Builds a new model with the original variables, the rewritten objective and
      constraints, and all auxiliary elements

   **Example:**

   .. code-block:: python

      linearized_model = linearizer.linearize_model()

      # Original model remains unchanged
      assert model.name == "original"

      # Linearized model has suffix
      assert linearized_model.name == "original_linearized"

   .. versionchanged:: 0.3.0
      The user's model and expressions are never modified, and every call starts
      afresh: calling ``linearize_model()`` twice, or solving the same model
      several times with ``enable_linearization()``, gives the same model. Before
      0.3.0 the linearizer wrote into the objective expression, so repeated solves
      drifted and a second call created duplicate auxiliary variables.

.. note::

   The linearized model keeps the objective sense of the original model.
   Before 0.1.2 every linearized model was minimized, so maximized nonlinear
   objectives returned wrong optima.

Getting Statistics
~~~~~~~~~~~~~~~~~~

.. py:method:: get_statistics()

   Get linearization statistics.

   **Returns:**

   - ``dict``: Dictionary with linearization statistics

   **Statistics Included** (of the last ``linearize_model()`` call):

   - ``bilinear_terms``: Number of products linearized (one per instance)
   - ``piecewise_terms``: Number of piecewise-linear approximations (one per instance)
   - ``absolute_terms``: Number of absolute values (one per instance)
   - ``minmax_terms``: Number of min/max items (one per instance)
   - ``indicator_terms``: Number of indicator constraints
   - ``auxiliary_variables``: Number of auxiliary variable families
   - ``auxiliary_constraints``: Number of auxiliary constraint rows

   **Example:**

   .. code-block:: python

      stats = linearizer.get_statistics()

      print(f"Linearization Statistics:")
      print(f"  Bilinear terms: {stats['bilinear_terms']}")
      print(f"  PWL approximations: {stats['piecewise_terms']}")
      print(f"  Auxiliary variables: {stats['auxiliary_variables']}")
      print(f"  Auxiliary constraints: {stats['auxiliary_constraints']}")

Supported Nonlinear Terms
--------------------------

The engine automatically detects and linearizes:

Bilinear Products
~~~~~~~~~~~~~~~~~

**Term Type:** ``LXBilinearTerm``

**Example:**

.. code-block:: python

   # In model: revenue = price * quantity
   # Automatically detected and linearized

**Techniques:**

- Binary × Binary → AND logic (exact)
- Binary × bounded variable → four bound constraints (exact)
- Integer × integer or continuous → binary expansion of the integer factor (exact)
- Continuous × Continuous → McCormick envelopes, a **relaxation** (``UserWarning``,
  ``solution.relaxation`` is ``True``)

See :doc:`bilinear` for details.

Piecewise-Linear Functions
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Term Type:** ``LXPiecewiseLinearTerm``

**Example:**

.. code-block:: python

   # In model: cost = piecewise_function(quantity)
   # Automatically approximated

**Techniques:**

- SOS2 formulation (default)
- Incremental formulation
- Logarithmic formulation

See :doc:`piecewise` for details.

Absolute Values
~~~~~~~~~~~~~~~

**Term Type:** ``LXAbsoluteTerm``

**Example:**

.. code-block:: python

   # In model: deviation = |actual - target|
   # Automatically linearized

**Technique:**

- Auxiliary variable with two constraints:
  - z ≥ x
  - z ≥ -x
- Where these are not enough (``|x|`` maximized, with a negative weight, or in
  a ``>=`` or ``==`` constraint), one binary per instance and two more
  constraints make z equal to ``|x|`` (see `Cheap and Exact Forms`_)

Min/Max Functions
~~~~~~~~~~~~~~~~~

**Term Type:** ``LXMinMaxTerm``

**Example:**

.. code-block:: python

   # In model: bottleneck = max(process1_time, process2_time, process3_time)
   # Automatically linearized

**Technique:**

- min(x₁, ..., xₙ): z ≤ xᵢ for all i, exact when z is pushed up (maximized)
- max(x₁, ..., xₙ): z ≥ xᵢ for all i, exact when z is pushed down (minimized)
- Other uses add one selection binary per argument, so that z equals the chosen
  argument (see `Cheap and Exact Forms`_)

Indicator Constraints
~~~~~~~~~~~~~~~~~~~~~

**Term Type:** ``LXIndicatorTerm``

**Example:**

.. code-block:: python

   # In model: if is_open == 1 then flow >= min_flow
   # Automatically linearized using Big-M

**Technique:**

- Big-M constraints; M is computed from the bounds of the expression
  (see :doc:`/user-guide/nonlinear/indicator`)

Terms on Variable Families
--------------------------

.. versionchanged:: 0.3.0
   Before 0.3.0 a term on a variable family acted on the sum of the family
   (``|x[p] + x[q]|``) or on an arbitrary instance.

The terms of an :class:`~lumix.core.expressions.LXNonLinearExpression`
(``add_abs``, ``add_min``, ``add_max``, ``add_product``, ``add_piecewise``) apply
to **every instance** of a variable family, and the results are summed:

- ``add_abs(x)`` is :math:`\sum_i |x_i|`
- ``add_product(x, y)`` is :math:`\sum_k x_k \cdot y_k`
- ``add_max(a, b)`` is :math:`\sum_k \max(a_k, b_k)`
- ``add_piecewise(x, f)`` is :math:`\sum_i f(x_i)`

When a term combines several families, they must have the **same index keys**;
the instances with the same key are combined. Families over different keys raise
``ValueError`` ("different index keys"). A single variable (a scalar, or a family
with one instance) is broadcast to every instance of the other families:
``add_min(x, cap)`` with a scalar ``cap`` is :math:`\sum_k \min(x_k, cap)`.

.. note::

   :class:`~lumix.core.expressions.LXQuadraticExpression` follows a different
   rule: ``add_quadratic(x, y)`` multiplies **all pairs**
   :math:`\sum_i \sum_j x_i y_j`, and ``add_squared(x)`` is the per-instance
   diagonal :math:`\sum_i x_i^2`. See :ref:`product-vs-quadratic`.

Cheap and Exact Forms
---------------------

.. versionchanged:: 0.3.0
   Absolute values, min and max get binary variables where the plain form is
   not exact. Before 0.3.0 a maximized ``|x|``, a minimized ``min`` or a
   maximized ``max`` used the plain form and returned wrong (often unbounded)
   results.

The plain epigraph form of ``|x|``, ``min`` and ``max`` (``z ≥ x, z ≥ -x``;
``z ≤ xᵢ``; ``z ≥ xᵢ``) is exact only when the optimizer pushes ``z`` in the right
direction. LumiX decides this for each use:

- In the objective, a term in a **minimized** objective with a positive weight
  is pushed down; in a **maximized** objective it is pushed up. A negative
  weight reverses the direction.
- In a constraint, a ``<=`` row pushes its terms down (like minimizing), a ``>=``
  row pushes them up (like maximizing), and an ``==`` row fixes them.

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Term
     - Plain form (no binaries)
     - Exact form (binaries, needs finite bounds)
   * - ``|x|``
     - pushed down: minimized with a positive weight, maximized with a
       negative weight, in a ``<=`` row
     - pushed up (maximized with a positive weight, minimized with a negative
       weight, in a ``>=`` row) and every ``==`` row
   * - ``max(...)``
     - pushed down: minimized, in a ``<=`` row
     - pushed up: maximized, in a ``>=`` row; every ``==`` row
   * - ``min(...)``
     - pushed up: maximized, in a ``>=`` row
     - pushed down: minimized, in a ``<=`` row; every ``==`` row

The exact form adds one binary per instance for ``|x|`` and one selection binary
per argument for ``min``/``max``; both forms are exact, the plain form is just
smaller. The exact form needs finite bounds on the variables involved and raises
``ValueError`` (mentioning "finite bounds") otherwise. Variables in the plain form
may be unbounded.

.. code-block:: python

   # Maximize |x| over x in [-5, 2]: exact form, returns 5
   x = LXVariable[None, float]("x").continuous().bounds(lower=-5, upper=2)
   model = LXModel("m").add_variable(x)
   model.maximize(LXNonLinearExpression().add_abs(x))

Nonlinear Terms in Constraints
------------------------------

.. versionchanged:: 0.3.0
   Nonlinear terms in constraints are linearized; they used to crash.

A constraint whose expression is an ``LXNonLinearExpression`` is linearized like
the objective, with the direction taken from the constraint sense (table above):

.. code-block:: python

   # |x[a]| + |x[b]| <= 2
   model.add_constraint(
       LXConstraint("abs_budget")
       .expression(LXNonLinearExpression().add_abs(x))
       .le()
       .rhs(2)
   )

In an **indexed** constraint, terms follow the same narrowing rule as
one-argument linear terms (see :doc:`/development/canonical-model`):

- A row that is an instance of the term's family uses only that instance's item:
  ``max(x[p], s) <= cap[p]`` for each product ``p``.
- A row built from other data sees all instances: a budget row
  ``|x[a]| + |x[b]| <= budget[r]``.

.. code-block:: python

   # One row per product p: max(x[p], s) <= p.cap   (s is a scalar variable)
   model.add_constraint(
       LXConstraint[Product]("cap")
       .expression(LXNonLinearExpression().add_max(x, s))
       .le()
       .rhs(lambda p: p.cap)
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

Auxiliary Variables and Their Values
------------------------------------

Each term gets its own auxiliary variable families, named

``aux_<kind>_<variables>_<n>_<role>``

where ``<kind>`` is ``abs``, ``min``, ``max``, ``prod``, ``pwl`` or ``ind``,
``<variables>`` are the names of the term's variables, ``<n>`` numbers the terms
of one linearization run (so two terms on the same variables never share a name),
and ``<role>`` names the variable's role (``z`` for the term's value, ``pos``,
``pick0``, ``bit0``, ``lam0``, ``out`` ...). A family is indexed by the instance keys
of the term; auxiliary constraints are named ``aux_<kind>_<variables>_<n>_<role>[<key>]``.

The values appear in ``solution.variables`` like any other family:

.. code-block:: python

   # x is a family over keys "p" and "q", fixed to x[p] = 3 and x[q] = -4
   model.minimize(LXNonLinearExpression().add_abs(x))
   solution = LXOptimizer().use_solver("ortools").enable_linearization().solve(model)

   solution.objective_value              # 7.0
   solution.variables["aux_abs_x_1_z"]   # {"p": 3.0, "q": 4.0}

The names depend on the order of the terms in the model; to look them up, use
``linearizer.auxiliary_vars`` after ``linearize_model()``.

Solver Capabilities
-------------------

.. versionchanged:: 0.2.1
   Every nonlinear term is linearized, whatever the solver. Earlier versions skipped
   the terms Gurobi and CPLEX declare native support for (products, absolute values,
   min/max, piecewise-linear functions), but no solver adapter translates those terms,
   so they silently disappeared from the objective.

The engine linearizes every bilinear, piecewise-linear, absolute-value, min/max and
indicator term, so the linearized model is purely linear and solves the same way on
every solver. Passing native SOS2 or general constraints to the solver is not
supported yet.

**Quadratic objectives** (:class:`~lumix.core.expressions.LXQuadraticExpression`)
are different: Gurobi and CPLEX solve them natively, and they stay native even with
``enable_linearization()``. On solvers without quadratic support (OR-Tools, GLPK,
CP-SAT) ``enable_linearization()`` linearizes each product of the objective with
the rules of :doc:`bilinear`: products with a binary or an integer factor are exact,
products of two continuous variables use McCormick envelopes and are a flagged
relaxation.

CP-SAT has no continuous variables. The auxiliary variables of ``abs``, ``min``,
``max`` and of products are integer when every variable they combine is integer or
binary (and the coefficients are whole numbers), so these terms work on CP-SAT;
piecewise terms and McCormick envelopes use continuous auxiliaries and need a MIP
solver (OR-Tools SCIP, GLPK, Gurobi, CPLEX).

.. versionchanged:: 0.3.0
   Quadratic objectives on variable families, with integer factors, or with two
   continuous factors are linearized on solvers without quadratic support. Before
   0.3.0 only products of two single variables with a binary factor were.

Complete Examples
-----------------

Example 1: Production Planning with Nonlinear Costs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXModel, LXVariable, LXConstraint
   from lumix.linearization import LXLinearizer, LXLinearizerConfig
   from lumix.solvers import GLPK_CAPABILITIES, LXOptimizer
   import math

   # Define variables
   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .bounds(lower=0, upper=1000)
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

   # Build model with nonlinear objective
   model = LXModel("production")

   # Nonlinear objective: minimize quadratic cost
   # cost = a * production² + b * production + c
   # (Simplified example - would use quadratic expression in practice)

   # Add constraints
   model.add_constraint(
       LXConstraint("capacity")
       .expression(production)
       .le()
       .rhs(5000)
   )

   # Configure linearization
   config = LXLinearizerConfig(pwl_num_segments=25)

   # Solve with linearization
   optimizer = LXOptimizer().use_solver("glpk")

   linearizer = LXLinearizer(model, GLPK_CAPABILITIES, config)

   if linearizer.needs_linearization():
       print("Linearizing model...")
       linearized = linearizer.linearize_model()

       # Print statistics
       stats = linearizer.get_statistics()
       print(f"Added {stats['auxiliary_variables']} auxiliary variables")
       print(f"Added {stats['auxiliary_constraints']} auxiliary constraints")

       # Solve
       solution = optimizer.solve(linearized)
   else:
       solution = optimizer.solve(model)

   print(f"Optimal cost: ${solution.objective_value:,.2f}")

Example 2: Revenue Maximization with Price-Quantity Product
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dataclasses import dataclass

   from lumix import LXModel, LXNonLinearExpression, LXVariable
   from lumix.linearization import LXLinearizer, LXLinearizerConfig
   from lumix.solvers import GLPK_CAPABILITIES, LXOptimizer

   @dataclass
   class Product:
       id: str
       min_price: float
       max_price: float
       min_quantity: float
       max_quantity: float

   products = [
       Product("A", 10, 100, 0, 1000),
       Product("B", 20, 150, 0, 500),
   ]

   # Variables
   price = (
       LXVariable[Product, float]("price")
       .continuous()
       .bounds(lower=10, upper=150)
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

   quantity = (
       LXVariable[Product, float]("quantity")
       .continuous()
       .bounds(lower=0, upper=1000)
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

   # Model
   model = LXModel("revenue_maximization")

   model.add_variables(price, quantity)

   # Bilinear objective: maximize revenue = sum over p of price[p] * quantity[p]
   model.maximize(LXNonLinearExpression().add_product(price, quantity))

   # Linearize and solve. Both factors are continuous, so the products use
   # McCormick envelopes: a UserWarning is issued and the result is a bound.
   optimizer = LXOptimizer().use_solver("glpk")
   linearizer = LXLinearizer(model, GLPK_CAPABILITIES, LXLinearizerConfig())

   linearized = linearizer.linearize_model()
   solution = optimizer.solve(linearized)

   # The same through the optimizer, which also sets the relaxation flag
   solution = optimizer.enable_linearization().solve(model)
   assert solution.relaxation  # the objective value is an upper bound

To get the exact optimum, make one factor integer (for example a price on a
grid of cents) or binary, or solve a quadratic objective on Gurobi or CPLEX.

Debugging and Validation
-------------------------

Warnings
~~~~~~~~

The linearizer reports approximations with a ``UserWarning``:

- a product of two continuous variables uses McCormick envelopes, a relaxation
  (the message contains "McCormick"; ``solution.relaxation`` is ``True``);
- a product of a binary and an unbounded variable, or an indicator whose
  expression is unbounded, uses ``big_m_value`` (``LXLinearizerConfig``) as the
  bound.

Turn them into errors to make sure a model is linearized exactly:

.. code-block:: python

   import warnings

   with warnings.catch_warnings():
       warnings.simplefilter("error", UserWarning)
       linearized = linearizer.linearize_model()

Inspecting Auxiliary Elements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   linearized = linearizer.linearize_model()

   # Inspect auxiliary variables
   for var in linearizer.auxiliary_vars:
       print(f"Auxiliary variable: {var.name}")
       print(f"  Type: {var.var_type}")
       print(f"  Bounds: [{var.lower_bound}, {var.upper_bound}]")

   # Inspect auxiliary constraints
   for constraint in linearizer.auxiliary_constraints:
       print(f"Auxiliary constraint: {constraint.name}")
       print(f"  Sense: {constraint.sense}")

Validating Results
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Solve both original and linearized models
   original_solution = optimizer.solve(model)  # May fail if nonlinear
   linearized_solution = optimizer.solve(linearized)

   # Compare objectives (should be close)
   obj_diff = abs(original_solution.objective_value -
                  linearized_solution.objective_value)

   print(f"Objective difference: {obj_diff}")
   assert obj_diff < 1e-3, "Linearization error too large!"

Performance Considerations
--------------------------

Model Size Growth
~~~~~~~~~~~~~~~~~

Linearization adds auxiliary variables and constraints:

.. code-block:: python

   print(f"Original model:")
   print(f"  Variables: {len(model.variables)}")
   print(f"  Constraints: {len(model.constraints)}")

   linearized = linearizer.linearize_model()

   print(f"Linearized model:")
   print(f"  Variables: {len(linearized.variables)}")
   print(f"  Constraints: {len(linearized.constraints)}")

   stats = linearizer.get_statistics()
   print(f"Added: {stats['auxiliary_variables']} vars, "
         f"{stats['auxiliary_constraints']} constraints")

Balancing Accuracy and Speed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # High accuracy (slower)
   high_accuracy_config = LXLinearizerConfig(
       pwl_num_segments=50,
       adaptive_breakpoints=True
   )

   # Faster solving (lower accuracy)
   fast_config = LXLinearizerConfig(
       pwl_num_segments=15,
       adaptive_breakpoints=False
   )

See Also
--------

- :doc:`config` - Configuration options
- :doc:`bilinear` - Bilinear linearization
- :doc:`piecewise` - Piecewise-linear approximation
- :doc:`nonlinear-functions` - Pre-built functions
- :doc:`/api/linearization/index` - API reference
