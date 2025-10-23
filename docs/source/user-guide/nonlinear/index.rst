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

   Conditional constraints: "if binary_var then constraint holds".

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

Integration with Linearization Module
--------------------------------------

The nonlinear terms work seamlessly with the linearization module:

.. code-block:: python

   from lumix.linearization import LXLinearizer, LXLinearizerConfig
   from lumix.linearization import LXLinearizationMethod

   # Configure linearization (optional - defaults are smart)
   config = LXLinearizerConfig(
       bilinear_method=LXLinearizationMethod.MCCORMICK,
       piecewise_segments=30,
       auto_detect_bounds=True
   )

   # Linearization happens automatically during model solve
   linearizer = LXLinearizer(config=config)
   linear_model = linearizer.linearize(model)

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
     - Auxiliary variable + constraints
     - None
   * - Min/Max
     - Auxiliary variable + bounding constraints
     - None
   * - Bilinear (Binary × Binary)
     - AND logic
     - None
   * - Bilinear (Binary × Continuous)
     - Big-M
     - M value (auto-computed)
   * - Bilinear (Continuous × Continuous)
     - McCormick envelopes
     - Variable bounds (required)
   * - Indicator
     - Big-M
     - M value (auto-computed)
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
