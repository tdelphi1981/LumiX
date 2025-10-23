Bilinear Products
=================

The :class:`~lumix.nonlinear.terms.LXBilinearTerm` represents products of two decision variables
(x * y), automatically linearized based on variable types.

Overview
--------

Bilinear terms are products of two variables:

.. math::

   z = x \cdot y

**Common Use Cases:**

- Facility activation × flow amount
- Price × quantity (revenue)
- Area calculations (length × width)
- Resource selection × usage
- On/off controls for continuous flows

Linearization Methods
---------------------

LumiX automatically selects the appropriate linearization based on variable types:

Binary × Binary (AND Logic)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For binary variables x, y ∈ {0, 1}, introduce z with constraints:

.. math::

   z \leq x \\
   z \leq y \\
   z \geq x + y - 1

**Properties:**
- Exact linearization
- 3 constraints
- No auxiliary variables beyond z
- Very efficient

Binary × Continuous (Big-M)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For binary x ∈ {0, 1} and continuous y ∈ [L, U] (with finite bounds L and U), introduce z with:

.. math::

   z \leq U \cdot x \\
   z \geq L \cdot x \\
   z \leq y - L \cdot (1-x) \\
   z \geq y - U \cdot (1-x)

**Properties:**
- 4 constraints
- Requires finite bounds on y
- M = max(\|L\|, \|U\|)
- Tighter bounds → better performance

Continuous × Continuous (McCormick Envelopes)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For continuous x ∈ [xL, xU] and y ∈ [yL, yU], introduce z with:

.. math::

   z \geq xL \cdot y + yL \cdot x - xL \cdot yL \\
   z \geq xU \cdot y + yU \cdot x - xU \cdot yU \\
   z \leq xL \cdot y + yU \cdot x - xL \cdot yU \\
   z \leq xU \cdot y + yL \cdot x - xU \cdot yL

**Properties:**
- 4 constraints (convex and concave envelopes)
- Relaxation (not exact unless at vertices)
- REQUIRES finite bounds on both variables
- Tighter bounds → tighter relaxation

Basic Usage
-----------

Facility Activation × Flow
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Flow is only active when facility is open:

.. code-block:: python

   from lumix import LXVariable
   from lumix.nonlinear import LXBilinearTerm

   # Binary: is facility open?
   is_open = (
       LXVariable[Facility, int]("is_open")
       .binary()
       .from_data(facilities)
   )

   # Continuous: potential flow
   flow_amount = (
       LXVariable[Facility, float]("flow")
       .continuous()
       .bounds(lower=0, upper=1000)
       .from_data(facilities)
   )

   # Bilinear: actual flow = is_open * flow_amount
   actual_flow = LXBilinearTerm(
       var1=is_open,
       var2=flow_amount,
       coefficient=1.0
   )

Rectangle Area
~~~~~~~~~~~~~~

Calculate area from dimensions:

.. code-block:: python

   # Dimensions (both continuous)
   length = (
       LXVariable[Shape, float]("length")
       .continuous()
       .bounds(lower=1, upper=10)
   )

   width = (
       LXVariable[Shape, float]("width")
       .continuous()
       .bounds(lower=1, upper=10)
   )

   # Area = length * width
   area = LXBilinearTerm(
       var1=length,
       var2=width,
       coefficient=1.0
   )

Complete Examples
-----------------

Example 1: Production with Setup Costs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Production is only possible if setup is done:

.. code-block:: python

   from dataclasses import dataclass
   from typing import List
   from lumix import LXModel, LXVariable, LXConstraint
   from lumix.nonlinear import LXBilinearTerm

   @dataclass
   class Product:
       id: str
       unit_cost: float
       setup_cost: float
       max_production: float

   products: List[Product] = [...]

   # Binary: setup done?
   setup = (
       LXVariable[Product, int]("setup")
       .binary()
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

   # Continuous: production quantity
   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .bounds(lower=0)
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

   # Actual production = setup * production
   actual_production = LXBilinearTerm(
       var1=setup,
       var2=production,
       coefficient=1.0
   )

   # Capacity constraint on actual production
   capacity = (
       LXConstraint[Product]("capacity")
       .expression(...)  # Use actual_production
       .le()
       .rhs(lambda p: p.max_production)
       .from_data(products)
       .indexed_by(lambda p: p.id)
   )

   model = LXModel("production_setup")

Example 2: Dynamic Pricing (Price × Quantity)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Optimize both price and quantity:

.. code-block:: python

   @dataclass
   class Product:
       id: str
       min_price: float
       max_price: float
       max_demand: float

   products: List[Product] = [...]

   # Decision: price
   price = (
       LXVariable[Product, float]("price")
       .continuous()
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

   # Decision: quantity sold
   quantity = (
       LXVariable[Product, float]("quantity")
       .continuous()
       .bounds(lower=0)
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

   # Revenue = price * quantity
   revenue = LXBilinearTerm(
       var1=price,
       var2=quantity,
       coefficient=1.0
   )

   # Price bounds (set via constraints or variable bounds)
   # Quantity demand curve (add constraint: quantity <= f(price))

   model = LXModel("dynamic_pricing")
   # Maximize revenue

Example 3: Binary Selection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Select resources and allocate amounts:

.. code-block:: python

   # Binary: resource selected?
   selected = (
       LXVariable[Resource, int]("selected")
       .binary()
       .from_data(resources)
   )

   # Continuous: allocation amount
   allocation = (
       LXVariable[Resource, float]("allocation")
       .continuous()
       .bounds(lower=0, upper=100)
       .from_data(resources)
   )

   # Actual allocation = selected * allocation
   actual_alloc = LXBilinearTerm(
       var1=selected,
       var2=allocation,
       coefficient=1.0
   )

Advanced Patterns
-----------------

Multiple Products in Single Expression
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sum multiple bilinear terms:

.. code-block:: python

   # Total revenue = sum of (price_i * quantity_i)
   total_revenue_terms = [
       LXBilinearTerm(var1=price, var2=quantity, coefficient=1.0)
       for price, quantity in zip(prices, quantities)
   ]

Weighted Products
~~~~~~~~~~~~~~~~~

Apply coefficients to products:

.. code-block:: python

   # Discounted revenue = 0.9 * price * quantity
   discounted_revenue = LXBilinearTerm(
       var1=price,
       var2=quantity,
       coefficient=0.9
   )

Bounds Management
-----------------

Importance of Bounds
~~~~~~~~~~~~~~~~~~~~

**Critical**: Bilinear linearization REQUIRES finite bounds!

.. code-block:: python

   # ✗ WRONG: No bounds
   price = LXVariable[Product, float]("price").continuous()
   quantity = LXVariable[Product, float]("quantity").continuous()
   revenue = LXBilinearTerm(var1=price, var2=quantity)
   # → Linearization will FAIL or use default (bad) bounds

   # ✓ CORRECT: Explicit bounds
   price = LXVariable[Product, float]("price").continuous().bounds(10, 100)
   quantity = LXVariable[Product, float]("quantity").continuous().bounds(0, 1000)
   revenue = LXBilinearTerm(var1=price, var2=quantity)
   # → Linearization uses proper McCormick envelopes

Tightening Bounds
~~~~~~~~~~~~~~~~~

Tighter bounds → better linearization relaxation:

.. code-block:: python

   # Loose bounds (poor relaxation)
   price = LXVariable("price").continuous().bounds(0, 1000)
   quantity = LXVariable("quantity").continuous().bounds(0, 10000)
   # → Large McCormick envelope, weak relaxation

   # Tight bounds (good relaxation)
   price = LXVariable("price").continuous().bounds(50, 150)
   quantity = LXVariable("quantity").continuous().bounds(100, 500)
   # → Tight McCormick envelope, strong relaxation

Dynamic Bounds
~~~~~~~~~~~~~~

Compute bounds from data:

.. code-block:: python

   @dataclass
   class Product:
       min_price: float
       max_price: float
       max_demand: float

   # Use data-driven bounds
   price = (
       LXVariable[Product, float]("price")
       .continuous()
       # Bounds computed per instance via constraints or manually
       .from_data(products)
   )

Performance Considerations
--------------------------

Linearization Overhead
~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 20 20 20

   * - Variable Types
     - Aux Vars
     - Constraints
     - Quality
   * - Binary × Binary
     - 1
     - 3
     - Exact
   * - Binary × Continuous
     - 1
     - 4
     - Exact
   * - Continuous × Continuous
     - 1
     - 4
     - Relaxation

Model Size Impact
~~~~~~~~~~~~~~~~~

.. code-block:: python

   # 1000 bilinear terms → 1000 aux vars + 3000-4000 constraints
   products = [...]  # 1000 products

   revenues = [
       LXBilinearTerm(var1=price[i], var2=qty[i], coefficient=1.0)
       for i in range(1000)
   ]

   # Modern solvers handle this efficiently

Solver Performance
~~~~~~~~~~~~~~~~~~

**Binary × Continuous** and **Binary × Binary**: Exact, solves efficiently

**Continuous × Continuous**: Relaxation, may need branching

.. code-block:: python

   # For cont × cont, consider tightening bounds or using SOS2 variables
   # if the problem structure allows

Common Pitfalls
---------------

Missing Bounds
~~~~~~~~~~~~~~

.. code-block:: python

   # ✗ ERROR
   x = LXVariable("x").continuous()  # No bounds!
   y = LXVariable("y").continuous()  # No bounds!
   product = LXBilinearTerm(var1=x, var2=y)
   # → Linearization fails or uses bad default bounds

Unbounded Variables
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # ✗ VERY BAD
   x = LXVariable("x").continuous().bounds(-1e9, 1e9)
   y = LXVariable("y").continuous().bounds(-1e9, 1e9)
   product = LXBilinearTerm(var1=x, var2=y)
   # → Huge M values, poor numerics

Wrong Variable Order
~~~~~~~~~~~~~~~~~~~~

For Binary × Continuous, put binary first (though LumiX should handle automatically):

.. code-block:: python

   # Preferred order
   product = LXBilinearTerm(var1=binary_var, var2=continuous_var)

Integration with Expressions
-----------------------------

Using in Linear Expressions
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXLinearExpression

   # Build expression with bilinear term
   # (requires linearization engine to expand)
   expr = LXLinearExpression()
   # Add bilinear terms via linearization auxiliary variables

See Also
--------

- :class:`~lumix.nonlinear.terms.LXBilinearTerm` - API reference
- :doc:`/user-guide/linearization/bilinear` - Bilinear linearization details
- :doc:`/user-guide/core/variables` - Variable bounds

Next Steps
----------

- :doc:`indicator` - Conditional constraints
- :doc:`piecewise` - Piecewise-linear functions
- :doc:`/user-guide/linearization/index` - Linearization configuration
