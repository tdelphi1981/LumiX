Absolute Value Terms
====================

The :class:`~lumix.nonlinear.terms.LXAbsoluteTerm` represents absolute value operations |x|, commonly
used for minimizing deviations and handling penalties.

Overview
--------

Absolute value is a fundamental nonlinear operation in optimization:

.. math::

   |x| = \begin{cases}
   x & \text{if } x \geq 0 \\
   -x & \text{if } x < 0
   \end{cases}

**Common Use Cases:**

- Minimizing deviations from targets
- Robust optimization (L1 norm)
- Penalty terms in objective functions
- Total variation minimization

Linearization Method
--------------------

LumiX automatically linearizes |x| by introducing an auxiliary variable z:

.. math::

   \text{Minimize } z \text{ subject to:} \\
   z \geq x \\
   z \geq -x

**Result**: z equals |x| in the optimal solution.

**Key Properties:**

- Adds 1 auxiliary variable per absolute value term
- Adds 2 linear constraints per term
- Works for both continuous and integer variables
- No configuration required

Basic Usage
-----------

Simple Deviation Minimization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Minimize the absolute deviation from a target:

.. code-block:: python

   from lumix import LXModel, LXVariable, LXLinearExpression
   from lumix.nonlinear import LXAbsoluteTerm

   # Define variable
   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .bounds(lower=0, upper=1000)
       .from_data(products)
   )

   # Create absolute deviation term
   # Minimize |production - target|
   abs_deviation = LXAbsoluteTerm(
       var=production,
       coefficient=1.0
   )

   # Add to objective (linearization happens automatically)
   model = LXModel("minimize_deviation")
   # ... build expression and minimize ...

Weighted Penalty
~~~~~~~~~~~~~~~~

Apply different weights to different deviations:

.. code-block:: python

   # Heavily penalize deviations
   heavy_penalty = LXAbsoluteTerm(
       var=critical_var,
       coefficient=100.0  # 100x penalty
   )

   # Light penalty
   light_penalty = LXAbsoluteTerm(
       var=flexible_var,
       coefficient=1.0
   )

Complete Examples
-----------------

Example 1: Production Planning with Target Tracking
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Minimize deviation from production targets:

.. code-block:: python

   from dataclasses import dataclass
   from typing import List
   from lumix import LXModel, LXVariable, LXConstraint, LXLinearExpression
   from lumix.nonlinear import LXAbsoluteTerm

   @dataclass
   class Product:
       id: str
       target: float
       max_capacity: float

   products: List[Product] = [
       Product("A", target=100, max_capacity=150),
       Product("B", target=200, max_capacity=250),
       Product("C", target=150, max_capacity=200),
   ]

   # Decision variable: actual production
   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .bounds(lower=0)
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

   # Capacity constraints
   capacity = (
       LXConstraint[Product]("capacity")
       .expression(
           LXLinearExpression().add_term(production, 1.0)
       )
       .le()
       .rhs(lambda p: p.max_capacity)
       .from_data(products)
       .indexed_by(lambda p: p.id)
   )

   # Minimize absolute deviation from targets
   # Note: This is conceptual - actual integration with objective needs
   # to be done through the expression system
   deviations = [
       LXAbsoluteTerm(var=production, coefficient=1.0)
       for p in products
   ]

   model = (
       LXModel("production_targets")
       .add_variable(production)
       .add_constraint(capacity)
   )
   # Add deviations to objective through linearization

Example 2: Portfolio Rebalancing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Minimize transaction costs (absolute changes):

.. code-block:: python

   @dataclass
   class Asset:
       id: str
       current_holding: float
       target_holding: float

   assets = [...]  # Your portfolio

   # Decision: new holdings
   holdings = (
       LXVariable[Asset, float]("holdings")
       .continuous()
       .bounds(lower=0)
       .from_data(assets)
   )

   # Minimize |holdings - current| (transaction costs)
   transaction_costs = [
       LXAbsoluteTerm(var=holdings, coefficient=0.01)  # 1% transaction cost
       for asset in assets
   ]

   # Total value constraint
   total_value = (
       LXConstraint("total_value")
       .expression(
           LXLinearExpression().add_term(holdings, 1.0)
       )
       .eq()
       .rhs(1_000_000)  # Total portfolio value
   )

   model = LXModel("rebalance")
   # ... complete model ...

Example 3: Robust Regression (L1 Norm)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fit a line minimizing L1 norm of residuals:

.. code-block:: python

   @dataclass
   class DataPoint:
       id: int
       x: float
       y: float

   data_points = [...]  # Your data

   # Decision variables: slope and intercept
   slope = LXVariable("slope").continuous().bounds(-10, 10)
   intercept = LXVariable("intercept").continuous().bounds(-100, 100)

   # For each point, minimize |y - (slope*x + intercept)|
   # This requires computing the residual first
   # (simplified example - actual implementation needs expression building)
   residuals = [
       LXAbsoluteTerm(var=..., coefficient=1.0)  # residual variable
       for point in data_points
   ]

   model = LXModel("robust_regression")
   # ... complete model ...

Advanced Patterns
-----------------

Multiple Absolute Terms in Objective
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sum multiple absolute value terms:

.. code-block:: python

   # Minimize sum of absolute deviations
   deviation_terms = [
       LXAbsoluteTerm(var=production, coefficient=weight)
       for production, weight in zip(prod_vars, weights)
   ]

   # Build objective expression combining all terms
   # (requires integration with expression system)

Asymmetric Penalties
~~~~~~~~~~~~~~~~~~~~

Penalize positive and negative deviations differently:

.. code-block:: python

   # Use two separate terms with one-sided constraints

   # Positive deviation: max(0, x - target)
   pos_dev = LXVariable[Product, float]("pos_dev").continuous().bounds(0)
   # Add constraint: pos_dev >= production - target

   # Negative deviation: max(0, target - x)
   neg_dev = LXVariable[Product, float]("neg_dev").continuous().bounds(0)
   # Add constraint: neg_dev >= target - production

   # Different penalties
   pos_penalty = LXAbsoluteTerm(var=pos_dev, coefficient=2.0)  # Over-production
   neg_penalty = LXAbsoluteTerm(var=neg_dev, coefficient=5.0)  # Under-production

Integration with Expressions
-----------------------------

Absolute value of linear expression:

.. code-block:: python

   # Want: |2*x + 3*y - 10|

   # Step 1: Create auxiliary variable for the expression value
   expr_value = LXVariable("expr_value").continuous()

   # Step 2: Constrain expr_value = 2*x + 3*y - 10
   expr_constraint = LXConstraint("expr_def").expression(
       LXLinearExpression()
       .add_term(x, 2.0)
       .add_term(y, 3.0)
       .add_term(expr_value, -1.0)
   ).eq().rhs(10.0)

   # Step 3: Take absolute value of expr_value
   abs_expr = LXAbsoluteTerm(var=expr_value, coefficient=1.0)

Performance Considerations
--------------------------

Computational Cost
~~~~~~~~~~~~~~~~~~

- **Variables Added**: 1 auxiliary variable per term
- **Constraints Added**: 2 constraints per term
- **Solve Time**: Minimal overhead, standard LP relaxation

**Recommendation**: Absolute value terms are efficient and well-supported by all solvers.

Model Size
~~~~~~~~~~

For models with many absolute value terms:

.. code-block:: python

   # 1000 products → 1000 auxiliary vars + 2000 constraints
   deviations = [
       LXAbsoluteTerm(var=production, coefficient=1.0)
       for _ in range(1000)
   ]

   # This is still efficient for modern solvers

Alternative: Eliminate terms that are not needed:

.. code-block:: python

   # Only penalize significant deviations
   deviations = [
       LXAbsoluteTerm(var=prod, coefficient=weight)
       for prod, weight in zip(productions, weights)
       if weight > threshold  # Skip small penalties
   ]

Common Patterns
---------------

Minimize Total Absolute Deviation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   total_deviation = sum(
       LXAbsoluteTerm(var=var, coefficient=1.0)
       for var in decision_vars
   )

Weighted Deviations
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   weighted_deviation = sum(
       LXAbsoluteTerm(var=var, coefficient=weight)
       for var, weight in zip(decision_vars, weights)
   )

Robust Objective (L1 vs L2)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # L1 norm (absolute value) - robust to outliers
   l1_objective = sum(
       LXAbsoluteTerm(var=residual, coefficient=1.0)
       for residual in residuals
   )

   # L2 norm (squared) - sensitive to outliers
   # Use LXQuadraticExpression for L2

See Also
--------

- :class:`~lumix.nonlinear.terms.LXAbsoluteTerm` - API reference
- :doc:`/user-guide/core/expressions` - Building expressions
- :doc:`/user-guide/linearization/index` - Linearization details

Next Steps
----------

- :doc:`min-max` - Min/max operations
- :doc:`bilinear` - Products of variables
- :doc:`indicator` - Conditional constraints
