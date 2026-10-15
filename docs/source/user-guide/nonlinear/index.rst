Nonlinear Terms
===============

This guide covers LumiX's nonlinear modeling capabilities and automatic linearization.

Introduction
------------

Real-world optimization problems often involve nonlinear relationships:

- Absolute deviations from targets
- Products of decision variables (e.g., price × quantity)
- Min/max operations over alternatives
- Conditional constraints (if-then logic)
- Complex nonlinear functions (exponential, logarithmic, etc.)

**Challenge**: Most practical solvers only handle linear constraints.

**Solution**: LumiX provides nonlinear term definitions that are **automatically linearized**
into equivalent linear formulations compatible with MIP solvers.

Philosophy
----------

Declarative Nonlinear Modeling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Instead of manually creating linearization constraints, you declare what you want:

.. code-block:: python

   # Traditional approach - manual linearization
   z = model.addVar()
   model.addConstr(z >= x)
   model.addConstr(z >= -x)
   # Remember to use z instead of |x| everywhere...

   # LumiX approach - declarative
   abs_x = LXAbsoluteTerm(var=x)
   # Linearization happens automatically!

**Benefits:**

- More readable and maintainable code
- Less error-prone
- Optimal linearization method selected automatically
- Easy to experiment with different formulations

Automatic Linearization
~~~~~~~~~~~~~~~~~~~~~~~

The linearization happens transparently when you build the model:

.. mermaid::

   sequenceDiagram
       participant User
       participant NonlinearTerm
       participant Linearizer
       participant Model
       participant Solver

       User->>NonlinearTerm: Create LXBilinearTerm(x, y)
       User->>Model: Add constraints with term
       User->>Solver: solve(model)
       Solver->>Linearizer: Linearize terms
       Linearizer->>NonlinearTerm: Analyze variable types
       Linearizer->>Model: Add auxiliary vars & constraints
       Model-->>Solver: Linear model
       Solver-->>User: Solution

Core Components
---------------

LumiX provides five nonlinear term types:

.. mermaid::

   graph LR
       A[Nonlinear Terms] --> B[LXAbsoluteTerm]
       A --> C[LXMinMaxTerm]
       A --> D[LXBilinearTerm]
       A --> E[LXIndicatorTerm]
       A --> F[LXPiecewiseLinearTerm]

       style A fill:#e1f5ff
       style B fill:#fff4e1
       style C fill:#ffe1e1
       style D fill:#e1ffe1
       style E fill:#f0e1ff
       style F fill:#ffe8e1

1. **Absolute Value** (:class:`~lumix.nonlinear.terms.LXAbsoluteTerm`)

   Represents |x| for minimizing deviations or handling penalties.

2. **Min/Max** (:class:`~lumix.nonlinear.terms.LXMinMaxTerm`)

   Minimum or maximum over multiple variables.

3. **Bilinear Products** (:class:`~lumix.nonlinear.terms.LXBilinearTerm`)

   Products of two variables (x * y), automatically linearized based on types.

4. **Indicator Constraints** (:class:`~lumix.nonlinear.terms.LXIndicatorTerm`)

   Conditional constraints: ``binary_var == condition`` ⇒ ``expr sense rhs``, with
   ``sense`` one of ``<=``, ``>=``, ``==``. M is computed from the bounds of
   ``expr``; ``big_m_value`` (with a ``UserWarning``) is used only when ``expr`` is
   unbounded. ``binary_var`` must be a single variable. See :doc:`indicator`.

5. **Piecewise-Linear** (:class:`~lumix.nonlinear.terms.LXPiecewiseLinearTerm`)

   Approximate arbitrary nonlinear functions with piecewise-linear segments.

Quick Start Example
-------------------

Here's a complete example using multiple nonlinear terms:

.. code-block:: python

   from dataclasses import dataclass
   from lumix import LXModel, LXVariable, LXConstraint
   from lumix.nonlinear import LXBilinearTerm, LXAbsoluteTerm, LXIndicatorTerm

   @dataclass
   class Facility:
       id: str
       capacity: float
       fixed_cost: float

   @dataclass
   class Product:
       id: str
       demand: float
       target: float

   facilities = [...]  # Your data
   products = [...]

   # Binary: is facility open?
   is_open = (
       LXVariable[Facility, int]("is_open")
       .binary()
       .indexed_by(lambda f: f.id)
       .from_data(facilities)
   )

   # Continuous: production quantity
   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .bounds(lower=0)
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

   # Nonlinear: actual_production = is_open * production
   # (only produce if facility is open)
   actual_production = LXBilinearTerm(
       var1=is_open,
       var2=production
   )

   # Nonlinear: minimize absolute deviation from target
   deviation = LXAbsoluteTerm(var=production, coefficient=1.0)

   # Nonlinear: if facility is open, must meet minimum capacity
   min_capacity = LXIndicatorTerm(
       binary_var=is_open,
       condition=True,
       linear_expr=production_expr,  # Define this expression
       sense='>=',
       rhs=100.0
   )

   # Build model (linearization happens automatically)
   model = LXModel("facility_planning")
   # ... add constraints and objective ...

Terms on Variable Families
--------------------------

.. versionchanged:: 0.3.0
   Terms apply per instance; before 0.3.0 a term on a family acted on the sum of
   the family.

Terms in an :class:`~lumix.core.expressions.LXNonLinearExpression` apply to every
instance of a variable family and the results are summed:

.. code-block:: python

   from lumix import LXNonLinearExpression

   expr = (
       LXNonLinearExpression()
       .add_abs(deviation)              # sum over i of |deviation[i]|
       .add_product(is_open, flow)      # sum over k of is_open[k] * flow[k]
       .add_max(load_a, load_b)         # sum over k of max(load_a[k], load_b[k])
   )

Families combined in one term must have the same index keys; a single variable
(scalar or one-instance family) is broadcast to every instance. The terms can be
used in the objective and, since 0.3.0, in constraints. See
:doc:`/user-guide/linearization/engine` for the details, including which uses need
binary variables and finite bounds.

Integration with Linearization Module
--------------------------------------

The nonlinear terms work seamlessly with the linearization module:

.. code-block:: python

   from lumix.linearization import LXLinearizer, LXLinearizerConfig
   from lumix.solvers import GLPK_CAPABILITIES, LXOptimizer

   # Configure linearization (optional - defaults are smart)
   config = LXLinearizerConfig(pwl_num_segments=30)

   # Linearization happens automatically during model solve
   optimizer = LXOptimizer().use_solver("glpk").enable_linearization(pwl_segments=30)
   solution = optimizer.solve(model)

   # Or linearize explicitly; the original model is not changed
   linear_model = LXLinearizer(model, GLPK_CAPABILITIES, config).linearize_model()

See :doc:`/user-guide/linearization/index` for details on linearization configuration.

Component Guides
----------------

Dive deeper into each nonlinear term type:

.. toctree::
   :maxdepth: 2

   absolute-value
   min-max
   bilinear
   indicator
   piecewise

Type Safety and IDE Support
----------------------------

All nonlinear terms are fully type-annotated dataclasses:

.. code-block:: python

   from lumix.nonlinear import LXBilinearTerm

   # Full IDE autocomplete and type checking
   bilinear = LXBilinearTerm(
       var1=price,      # Type: LXVariable
       var2=quantity,   # Type: LXVariable
       coefficient=0.9  # Type: float
   )

   # Type errors caught at development time
   bilinear = LXBilinearTerm(
       var1="not_a_variable"  # ✗ Type error!
   )

Linearization Methods
---------------------

Different nonlinear terms use different linearization techniques:

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Term Type
     - Linearization Method
     - Key Parameters
   * - Absolute Value
     - Auxiliary variable + constraints; one binary per instance where the plain
       form is not exact (e.g. maximized)
     - Variable bounds (required for the exact form)
   * - Min/Max
     - Auxiliary variable + bounding constraints; selection binaries where the
       plain form is not exact (e.g. a minimized min)
     - Variable bounds (required for the exact form)
   * - Bilinear (Binary × Binary)
     - AND logic (exact)
     - None
   * - Bilinear (Binary × Continuous)
     - Bound constraints (exact)
     - Variable bounds (else ``big_m_value``)
   * - Bilinear (Integer × Integer or Continuous)
     - Binary expansion (exact)
     - Integer bounds, ``binary_expansion_bits``
   * - Bilinear (Continuous × Continuous)
     - McCormick envelopes (a relaxation; ``solution.relaxation``)
     - Variable bounds (required)
   * - Indicator
     - Big-M
     - M from the expression bounds (else ``big_m_value``)
   * - Piecewise-Linear
     - SOS2, Incremental, or Logarithmic
     - Segments, method, adaptive

See :doc:`/development/nonlinear-architecture` for implementation details.

Best Practices
--------------

Variable Bounds
~~~~~~~~~~~~~~~

**Always define bounds for continuous variables** used in nonlinear terms:

.. code-block:: python

   # Good - bounds defined
   price = LXVariable[Product, float]("price").continuous().bounds(10, 100)
   quantity = LXVariable[Product, float]("qty").continuous().bounds(0, 1000)
   revenue = LXBilinearTerm(var1=price, var2=quantity)

   # Bad - no bounds (linearization may fail)
   price = LXVariable[Product, float]("price").continuous()
   revenue = LXBilinearTerm(var1=price, var2=quantity)  # ✗ Error!

Big-M Selection
~~~~~~~~~~~~~~~

For Big-M linearizations (indicator constraints, binary × continuous), tighter bounds
lead to better performance:

.. code-block:: python

   # Tight bounds → smaller M → better numerics
   flow = LXVariable[Route, float]("flow").continuous().bounds(0, 500)

   # Loose bounds → larger M → numerical issues
   flow = LXVariable[Route, float]("flow").continuous().bounds(0, 1e9)  # ✗ Avoid

Piecewise Segments
~~~~~~~~~~~~~~~~~~

Balance accuracy vs. model size:

.. code-block:: python

   # More segments = better accuracy but slower
   exp_term = LXPiecewiseLinearTerm(
       var=time,
       func=lambda t: math.exp(t),
       num_segments=50  # High accuracy
   )

   # Fewer segments = faster but less accurate
   exp_term = LXPiecewiseLinearTerm(
       var=time,
       func=lambda t: math.exp(t),
       num_segments=10  # Fast, may be sufficient
   )

Use adaptive segmentation for non-uniform functions:

.. code-block:: python

   # Adaptive places more segments where function curves sharply
   sigmoid_approx = LXPiecewiseLinearTerm(
       var=x,
       func=lambda x: 1 / (1 + math.exp(-x)),
       num_segments=30,
       adaptive=True  # More segments near inflection point
   )

Next Steps
----------

**Learn each term type:**

- :doc:`absolute-value` - Absolute value operations and deviation minimization
- :doc:`min-max` - Min/max operations over alternatives
- :doc:`bilinear` - Products of variables and automatic linearization
- :doc:`indicator` - Conditional constraints and if-then logic
- :doc:`piecewise` - Approximating arbitrary nonlinear functions

**Advanced topics:**

- :doc:`/user-guide/linearization/index` - Linearization configuration and methods
- :doc:`/development/nonlinear-architecture` - Implementation details
- :doc:`/development/extending-nonlinear` - Adding custom nonlinear terms

**Related modules:**

- :doc:`/user-guide/core/index` - Core modeling concepts
- :doc:`/api/nonlinear/index` - Complete API reference
