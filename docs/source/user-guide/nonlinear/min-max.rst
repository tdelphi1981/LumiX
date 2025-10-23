Min/Max Operations
==================

The :class:`~lumix.nonlinear.terms.LXMinMaxTerm` represents minimum and maximum operations over
multiple variables, useful for selection and optimization over alternatives.

Overview
--------

Min/max operations select the minimum or maximum value among a set of variables:

.. math::

   z = \min(x_1, x_2, \ldots, x_n) \\
   z = \max(x_1, x_2, \ldots, x_n)

**Common Use Cases:**

- Selecting minimum cost among alternatives
- Finding maximum capacity among resources
- Bottleneck identification (minimize the maximum)
- Min-max fairness objectives
- Robust optimization (worst-case scenarios)

Linearization Method
--------------------

Minimum
~~~~~~~

For z = min(x₁, x₂, ..., xₙ), introduce auxiliary variable z with constraints:

.. math::

   z \leq x_i \quad \forall i

When minimizing z in the objective, z will equal the minimum.

Maximum
~~~~~~~

For z = max(x₁, x₂, ..., xₙ), introduce auxiliary variable z with constraints:

.. math::

   z \geq x_i \quad \forall i

When maximizing z in the objective, z will equal the maximum.

**Key Properties:**

- Adds 1 auxiliary variable per min/max operation
- Adds n constraints (one per input variable)
- Requires appropriate objective sense (min for minimum, max for maximum)

Basic Usage
-----------

Minimum Cost Selection
~~~~~~~~~~~~~~~~~~~~~~

Select the minimum cost among alternatives:

.. code-block:: python

   from lumix import LXVariable
   from lumix.nonlinear import LXMinMaxTerm

   # Three cost alternatives
   cost_a = LXVariable[Option, float]("cost_a").continuous().from_data(options)
   cost_b = LXVariable[Option, float]("cost_b").continuous().from_data(options)
   cost_c = LXVariable[Option, float]("cost_c").continuous().from_data(options)

   # Select minimum cost
   min_cost = LXMinMaxTerm(
       vars=[cost_a, cost_b, cost_c],
       operation="min",
       coefficients=[1.0, 1.0, 1.0]
   )

   # Use in objective: minimize min_cost

Maximum Capacity
~~~~~~~~~~~~~~~~

Find maximum capacity among resources:

.. code-block:: python

   # Resource capacities
   capacity_1 = LXVariable[Resource, float]("cap1").continuous()
   capacity_2 = LXVariable[Resource, float]("cap2").continuous()

   # Find maximum available capacity
   max_capacity = LXMinMaxTerm(
       vars=[capacity_1, capacity_2],
       operation="max",
       coefficients=[1.0, 1.0]
   )

   # Use in constraints: demand <= max_capacity

Complete Examples
-----------------

Example 1: Multi-Modal Transportation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Choose the fastest transportation mode:

.. code-block:: python

   from dataclasses import dataclass
   from typing import List
   from lumix import LXModel, LXVariable
   from lumix.nonlinear import LXMinMaxTerm

   @dataclass
   class Route:
       id: str
       truck_time: float
       train_time: float
       ship_time: float

   routes: List[Route] = [...]

   # Travel time for each mode
   truck_time = (
       LXVariable[Route, float]("truck_time")
       .continuous()
       .from_data(routes)
   )

   train_time = (
       LXVariable[Route, float]("train_time")
       .continuous()
       .from_data(routes)
   )

   ship_time = (
       LXVariable[Route, float]("ship_time")
       .continuous()
       .from_data(routes)
   )

   # Minimize maximum time (minimize worst-case)
   min_max_time = LXMinMaxTerm(
       vars=[truck_time, train_time, ship_time],
       operation="min",
       coefficients=[1.0, 1.0, 1.0]
   )

   model = LXModel("fastest_route")
   # Use min_max_time in objective

Example 2: Load Balancing
~~~~~~~~~~~~~~~~~~~~~~~~~~

Balance load across servers (minimize maximum load):

.. code-block:: python

   @dataclass
   class Server:
       id: str
       max_capacity: float

   servers: List[Server] = [...]

   # Load on each server
   server_load = (
       LXVariable[Server, float]("load")
       .continuous()
       .bounds(lower=0)
       .from_data(servers)
   )

   # Minimize maximum load (load balancing)
   max_load = LXMinMaxTerm(
       vars=[server_load] * len(servers),
       operation="max",
       coefficients=[1.0] * len(servers)
   )

   # Objective: minimize max_load
   # This ensures loads are balanced

Example 3: Bottleneck Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Maximize throughput by improving the bottleneck:

.. code-block:: python

   @dataclass
   class Station:
       id: str
       capacity: float

   stations: List[Station] = [...]

   # Throughput at each station
   throughput = (
       LXVariable[Station, float]("throughput")
       .continuous()
       .bounds(lower=0)
       .from_data(stations)
   )

   # Maximize minimum throughput (bottleneck)
   min_throughput = LXMinMaxTerm(
       vars=[throughput] * len(stations),
       operation="min",
       coefficients=[1.0] * len(stations)
   )

   # Objective: maximize min_throughput
   # This improves the bottleneck station

Advanced Patterns
-----------------

Weighted Min/Max
~~~~~~~~~~~~~~~~

Apply different weights to alternatives:

.. code-block:: python

   # Weighted costs (e.g., adjusted for quality)
   weighted_min_cost = LXMinMaxTerm(
       vars=[cost_a, cost_b, cost_c],
       operation="min",
       coefficients=[1.0, 0.9, 1.1]  # cost_b is preferred
   )

Cascading Min/Max
~~~~~~~~~~~~~~~~~

Nested min/max operations:

.. code-block:: python

   # Inner: max capacity per region
   region1_max = LXMinMaxTerm(
       vars=[cap_a, cap_b],
       operation="max",
       coefficients=[1.0, 1.0]
   )

   region2_max = LXMinMaxTerm(
       vars=[cap_c, cap_d],
       operation="max",
       coefficients=[1.0, 1.0]
   )

   # Outer: min of regional maxes
   # (requires auxiliary variables for inner terms)

Min-Max Fairness
~~~~~~~~~~~~~~~~

Ensure fair allocation by maximizing the minimum:

.. code-block:: python

   # Allocation to each user
   allocations = [
       LXVariable[User, float](f"alloc_{i}").continuous()
       for i in range(num_users)
   ]

   # Maximize minimum allocation (fairness)
   min_allocation = LXMinMaxTerm(
       vars=allocations,
       operation="min",
       coefficients=[1.0] * num_users
   )

   # Objective: maximize min_allocation

Robust Optimization
-------------------

Min-max for worst-case optimization:

.. code-block:: python

   # Scenario-based costs
   scenario_costs = [
       LXVariable[Scenario, float](f"cost_{s}").continuous()
       for s in scenarios
   ]

   # Minimize worst-case (maximum) cost
   worst_case_cost = LXMinMaxTerm(
       vars=scenario_costs,
       operation="max",
       coefficients=[1.0] * len(scenarios)
   )

   # Objective: minimize worst_case_cost
   # This gives a robust solution

Integration with Objective
---------------------------

Minimization Problems
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Minimize the minimum cost (unusual but possible)
   min_of_costs = LXMinMaxTerm(
       vars=[cost_a, cost_b, cost_c],
       operation="min",
       coefficients=[1.0, 1.0, 1.0]
   )

   # Objective: minimize min_of_costs
   # Result: z = min(cost_a, cost_b, cost_c)

   # Minimize the maximum cost (more common - minimax)
   max_of_costs = LXMinMaxTerm(
       vars=[cost_a, cost_b, cost_c],
       operation="max",
       coefficients=[1.0, 1.0, 1.0]
   )

   # Objective: minimize max_of_costs
   # Result: reduces the worst case

Maximization Problems
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Maximize the minimum benefit (fairness)
   min_benefit = LXMinMaxTerm(
       vars=[benefit_a, benefit_b, benefit_c],
       operation="min",
       coefficients=[1.0, 1.0, 1.0]
   )

   # Objective: maximize min_benefit
   # Result: improves the worst-off alternative

Performance Considerations
--------------------------

Computational Cost
~~~~~~~~~~~~~~~~~~

- **Variables Added**: 1 auxiliary variable per term
- **Constraints Added**: n constraints (n = number of input variables)
- **Solve Time**: Minimal overhead

**Recommendation**: Min/max terms are efficient and well-supported.

Model Size
~~~~~~~~~~

For large numbers of alternatives:

.. code-block:: python

   # 100 alternatives → 1 auxiliary var + 100 constraints
   many_alternatives = LXMinMaxTerm(
       vars=cost_vars,  # 100 variables
       operation="min",
       coefficients=[1.0] * 100
   )

   # Still efficient for modern solvers

Common Pitfalls
---------------

Wrong Objective Sense
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # ✗ WRONG: Minimizing a "max" term without proper objective
   max_cost = LXMinMaxTerm(vars=[...], operation="max", coefficients=[...])
   # If you minimize, you get the correct max
   # If you maximize, the result is unbounded!

   # ✓ CORRECT: Match operation with objective sense
   # minimize max_cost → minimax (reduce worst case)
   # maximize min_benefit → maximin (improve worst case)

Missing Coefficients
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # ✗ WRONG: Mismatched lengths
   min_cost = LXMinMaxTerm(
       vars=[cost_a, cost_b, cost_c],  # 3 variables
       operation="min",
       coefficients=[1.0, 1.0]  # Only 2 coefficients!
   )

   # ✓ CORRECT: Same length
   min_cost = LXMinMaxTerm(
       vars=[cost_a, cost_b, cost_c],
       operation="min",
       coefficients=[1.0, 1.0, 1.0]
   )

See Also
--------

- :class:`~lumix.nonlinear.terms.LXMinMaxTerm` - API reference
- :doc:`absolute-value` - Absolute value terms
- :doc:`/user-guide/core/expressions` - Building expressions

Next Steps
----------

- :doc:`bilinear` - Products of variables
- :doc:`indicator` - Conditional constraints
- :doc:`piecewise` - Piecewise-linear functions
