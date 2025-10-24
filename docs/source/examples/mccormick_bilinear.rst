McCormick Envelope Linearization Example
==========================================

Overview
--------

This example demonstrates the automatic linearization of **bilinear products** using **McCormick envelopes**, one of the most powerful techniques for linearizing continuous × continuous variable products.

The rectangle area maximization problem showcases how LumiX automatically converts nonlinear objectives into linear constraints that any linear solver can handle.

Problem Description
-------------------

Maximize the area of a rectangle subject to constraints.

**Objective**: Maximize area = length × width (bilinear product!).

**Constraints**:

- Minimum perimeter: ``2 × (length + width) >= 20``
- Dimension bounds: ``length ∈ [2, 10]``, ``width ∈ [2, 10]``

The objective ``area = length × width`` is a **bilinear product** requiring linearization for linear solvers.

Mathematical Formulation
------------------------

**Decision Variables**:

.. math::

   \text{length} &\in [2, 10] \\
   \text{width} &\in [2, 10]

**Objective Function** (Nonlinear):

.. math::

   \text{Maximize} \quad \text{length} \times \text{width}

**Constraint**:

.. math::

   2 \times (\text{length} + \text{width}) \geq 20

McCormick Envelope Theory
--------------------------

For :math:`z = x \times y` with :math:`x \in [x_L, x_U]` and :math:`y \in [y_L, y_U]`, the **McCormick envelope** creates four linear constraints forming the tightest convex relaxation:

.. math::

   z &\geq x_L \cdot y + y_L \cdot x - x_L \cdot y_L \\
   z &\geq x_U \cdot y + y_U \cdot x - x_U \cdot y_U \\
   z &\leq x_L \cdot y + y_U \cdot x - x_L \cdot y_U \\
   z &\leq x_U \cdot y + y_L \cdot x - x_U \cdot y_L

These four constraints:

- Form the **convex hull** (tightest linear relaxation)
- Require only finite variable bounds
- Add 1 auxiliary variable (z) and 4 constraints
- Are exact at the optimal solution for many problems

Key Features
------------

Bilinear Product in Objective
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Define the nonlinear objective naturally:

.. literalinclude:: ../../../examples/06_mccormick_bilinear/rectangle_area.py
   :language: python
   :lines: 108-111

**Key Point**: LumiX detects the bilinear product ``length × width`` and automatically linearizes it.

Automatic Linearization
~~~~~~~~~~~~~~~~~~~~~~~

Create linearizer and apply McCormick envelopes:

.. literalinclude:: ../../../examples/06_mccormick_bilinear/rectangle_area.py
   :language: python
   :lines: 146-167

The linearizer:

1. Detects bilinear products in objective/constraints
2. Creates auxiliary variable z for each product
3. Adds 4 McCormick envelope constraints
4. Replaces x × y with z in the model

Bounded Variables Required
~~~~~~~~~~~~~~~~~~~~~~~~~~~

McCormick envelopes **require** finite bounds:

.. literalinclude:: ../../../examples/06_mccormick_bilinear/rectangle_area.py
   :language: python
   :lines: 77-90

Without bounds, McCormick cannot compute the envelope coefficients.

Running the Example
-------------------

**Prerequisites**:

.. code-block:: bash

   pip install lumix
   pip install ortools  # or cplex, gurobi

**Run**:

.. code-block:: bash

   cd examples/06_mccormick_bilinear
   python rectangle_area.py

**Expected Output**:

.. code-block:: text

   ======================================================================
   LumiX Example: McCormick Envelope Linearization
   ======================================================================

   Problem: Maximize rectangle area (length × width)
     Subject to: 2×(length + width) >= 20
     Bounds: length ∈ [2.0, 10.0]
             width ∈ [2.0, 10.0]

   Linearization Statistics:
   ----------------------------------------------------------------------
     Bilinear terms linearized: 1
     Auxiliary variables added: 1
     Auxiliary constraints added: 4

   McCormick Envelope Constraints:
   ----------------------------------------------------------------------
     z >= 2.0*y + 2.0*x - 4.00
     z >= 10.0*y + 10.0*x - 100.00
     z <= 2.0*y + 10.0*x - 20.00
     z <= 10.0*y + 2.0*x - 20.00

   ======================================================================
   SOLUTION
   ======================================================================
   Status: optimal
   Maximum Area: 25.0000 m²

   Optimal Rectangle Dimensions:
   ----------------------------------------------------------------------
     Length: 5.0000 meters
     Width:  5.0000 meters
     Area:   25.0000 m²
     Perimeter: 20.0000 meters

Complete Code Walkthrough
--------------------------

Step 1: Create Bounded Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/06_mccormick_bilinear/rectangle_area.py
   :language: python
   :lines: 77-91

Step 2: Add Linear Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/06_mccormick_bilinear/rectangle_area.py
   :language: python
   :lines: 98-105

Step 3: Define Nonlinear Objective
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/06_mccormick_bilinear/rectangle_area.py
   :language: python
   :lines: 108-111

Step 4: Apply Linearization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.linearization import LXLinearizer, LXLinearizerConfig

   config = LXLinearizerConfig(
       mccormick_tighten_bounds=True,
       verbose_logging=True
   )
   linearizer = LXLinearizer(model, solver_capabilities, config)

   if linearizer.needs_linearization():
       linearized_model = linearizer.linearize_model()
       solution = optimizer.solve(linearized_model)

Step 5: Solve and Verify
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   solution = optimizer.solve(linearized_model)

   if solution.is_optimal():
       length_val = solution.get_mapped(length)["dim"]
       width_val = solution.get_mapped(width)["dim"]
       actual_product = length_val * width_val

       print(f"Length: {length_val:.4f} meters")
       print(f"Width:  {width_val:.4f} meters")
       print(f"Area:   {actual_product:.4f} m²")

Learning Objectives
-------------------

After completing this example, you should understand:

1. **Bilinear Products**: Identifying x × y terms in models
2. **McCormick Envelopes**: How they form the tightest linear relaxation
3. **Automatic Linearization**: How LumiX detects and linearizes products
4. **Bounded Variables**: Why McCormick requires finite bounds
5. **Auxiliary Variables**: How z replaces x × y in the linearized model
6. **Exactness**: When McCormick provides exact optimal solutions

Common Patterns
---------------

Pattern 1: Bilinear Product Variable
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Define bounded continuous variables
   x = LXVariable[None, float]("x").continuous().bounds(lower=0, upper=10)
   y = LXVariable[None, float]("y").continuous().bounds(lower=0, upper=10)

   # Use bilinear product in objective or constraints
   product = x * y
   model.maximize(product)

Pattern 2: Multiple Bilinear Terms
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # z = x₁ × x₂ + x₃ × x₄ + ...
   # LumiX applies McCormick to each bilinear term
   objective = x1 * x2 + x3 * x4
   model.maximize(objective)

Pattern 3: Bilinear Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Bilinear products can appear in constraints too
   model.add_constraint(
       LXConstraint("bilinear_constraint")
       .expression(x * y)
       .le()
       .rhs(50.0)
   )

Types of Bilinear Products
---------------------------

LumiX Supports Different Variable Types
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**1. Continuous × Continuous** (This Example):

- Linearization: McCormick envelopes (4 constraints)
- Example: ``area = length * width``

**2. Binary × Binary**:

- Linearization: AND logic (3 constraints)
- Example: ``and_result = binary_x * binary_y``

**3. Binary × Continuous**:

- Linearization: Big-M method (4 constraints)
- Example: ``flow = binary_open * continuous_amount``

**4. Integer × Integer**:

- Linearization: Discretization or McCormick
- Example: ``product = integer_x * integer_y``

Use Cases
---------

Common Applications
~~~~~~~~~~~~~~~~~~~

1. **Area/Volume Calculations**: ``area = length * width``
2. **Revenue Optimization**: ``revenue = price * quantity`` (both variables)
3. **Portfolio Optimization**: ``variance = weight_i * weight_j * covariance``
4. **Blending Problems**: ``concentration = fraction * property``
5. **Power Systems**: ``power = voltage * current``

McCormick Quality Factors
--------------------------

Bound Tightness Impact
~~~~~~~~~~~~~~~~~~~~~~~

The quality of McCormick relaxation depends on bound tightness:

.. code-block:: text

   # Tight bounds → Good relaxation
   x in [5, 6], y in [3, 4]  # Small domain, tight envelope

   # Loose bounds → Weak relaxation
   x in [0, 100], y in [0, 100]  # Large domain, loose envelope

**Tip**: Use problem-specific bounds, not arbitrary large values.

Improving Relaxations
~~~~~~~~~~~~~~~~~~~~~~

1. **Variable Bounds Tightening**: Use optimization to find tighter bounds
2. **Auxiliary Constraints**: Add valid inequalities
3. **Partitioning**: Divide domain into smaller regions (piecewise McCormick)

Extending the Example
---------------------

Try These Modifications
~~~~~~~~~~~~~~~~~~~~~~~

1. **Multiple Products**: Add more bilinear terms

   .. code-block:: python

      objective = length * width + height * depth

2. **Bilinear Constraints**: Use products in constraints
3. **Three-Dimensional**: Extend to volume = length × width × height
4. **Different Bounds**: Experiment with various bound ranges
5. **Compare Solvers**: Test with/without native quadratic support

Next Steps
----------

After mastering this example:

1. **Example 07 (Piecewise Functions)**: Nonlinear function approximation
2. **Example 03 (Facility Location)**: Big-M for binary × continuous
3. **Nonlinear Module Documentation**: Advanced nonlinear features

See Also
--------

**Related Examples**:

- :doc:`piecewise_functions` - Piecewise-linear approximation
- :doc:`facility_location` - Big-M technique
- :doc:`goal_programming` - Multi-objective with bilinear terms

**API Reference**:

- :class:`lumix.linearization.LXLinearizer`
- :class:`lumix.linearization.LXLinearizerConfig`
- :class:`lumix.core.expressions.LXNonLinearExpression`

**References**:

- McCormick, G. P. (1976). "Computability of global solutions to factorable nonconvex programs"
- Tawarmalani, M., & Sahinidis, N. V. (2005). "A polyhedral branch-and-cut approach"

Files in This Example
---------------------

- ``rectangle_area.py`` - Main optimization with McCormick linearization
- ``README.md`` - Detailed documentation and usage guide
