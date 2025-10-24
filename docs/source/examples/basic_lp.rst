Basic Linear Programming Example
==================================

Overview
--------

This is the **SIMPLEST** LumiX example - perfect for learning the absolute basics of data-driven optimization modeling. If you're new to LumiX, **start here**!

This example demonstrates the classic **Diet Problem**: finding the minimum-cost combination of foods that meets nutritional requirements. It's one of the first practical applications of linear programming, solved by George Stigler in 1945.

Problem Description
-------------------

A person wants to plan their daily diet to minimize food costs while meeting minimum nutritional requirements.

**Objective**: Minimize total food cost.

**Nutritional Requirements**:

- Calories (energy): At least 2000 per day
- Protein (muscle building): At least 50g per day
- Calcium (bone health): At least 800mg per day

**Available Foods**: Each food has cost per serving and nutritional content.

**Decision**: How many servings of each food to consume?

Mathematical Formulation
------------------------

**Decision Variables**:

.. math::

   x_f \geq 0, \quad \forall f \in \text{Foods}

where :math:`x_f` represents the number of servings of food :math:`f`.

**Objective Function**:

.. math::

   \text{Minimize} \quad \sum_{f \in \text{Foods}} \text{cost}_f \cdot x_f

**Constraints**:

1. **Minimum Calories**:

   .. math::

      \sum_{f \in \text{Foods}} \text{calories}_f \cdot x_f \geq 2000

2. **Minimum Protein**:

   .. math::

      \sum_{f \in \text{Foods}} \text{protein}_f \cdot x_f \geq 50

3. **Minimum Calcium**:

   .. math::

      \sum_{f \in \text{Foods}} \text{calcium}_f \cdot x_f \geq 800

Key Features
------------

Variable Families from Data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

ONE variable declaration expands to multiple solver variables:

.. literalinclude:: ../../../examples/04_basic_lp/basic_lp.py
   :language: python
   :lines: 112-118
   :dedent: 4

**Key Points**:

- ``LXVariable[Food, float]`` creates a variable family typed by Food
- ``.continuous()`` specifies continuous (non-integer) variables
- ``.bounds(lower=0)`` sets non-negativity constraint
- ``.indexed_by(lambda f: f.name)`` specifies how to index each variable
- ``.from_data(FOODS)`` auto-creates one variable per food item

Data-Driven Coefficients
~~~~~~~~~~~~~~~~~~~~~~~~~

Coefficients extracted from data using lambda functions:

.. literalinclude:: ../../../examples/04_basic_lp/basic_lp.py
   :language: python
   :lines: 125-128
   :dedent: 4

The lambda function ``lambda f: f.cost_per_serving`` extracts the cost attribute from each Food instance.

Automatic Expression Expansion
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Expressions automatically sum over all indexed data:

.. literalinclude:: ../../../examples/04_basic_lp/basic_lp.py
   :language: python
   :lines: 133-140
   :dedent: 4

This constraint expands to: :math:`\sum_f \text{calories}_f \cdot x_f \geq 2000` automatically.

Type-Safe Solution Access
~~~~~~~~~~~~~~~~~~~~~~~~~~

Access solutions using the index keys:

.. code-block:: python

   # Get mapped solution (dictionary indexed by food name)
   solution_dict = solution.get_mapped(servings)

   for food_name, qty in solution_dict.items():
       if qty > 0.01:  # Only non-zero servings
           food = food_by_name[food_name]
           cost = food.cost_per_serving * qty
           print(f"{food.name}: {qty:.2f} servings (${cost:.2f})")

Running the Example
-------------------

**Prerequisites**:

.. code-block:: bash

   pip install lumix[ortools]  # or cplex, gurobi, glpk

**Run**:

.. code-block:: bash

   cd examples/04_basic_lp
   python basic_lp.py

**Expected Output**:

.. code-block:: text

   ============================================================
   LumiX Example: Basic Diet Problem
   ============================================================

   Building optimization model...
   Model Summary:
     Variables: 1 family (6 decision variables)
     Constraints: 3 (calories, protein, calcium)
     Objective: Minimize total cost

   Solving...

   ============================================================
   SOLUTION
   ============================================================
   Status: optimal
   Optimal Cost: $3.15
   Solve Time: 0.042s

   Optimal Diet Plan:
   ------------------------------------------------------------
     Oatmeal      :   4.00 servings  (cost: $1.20)
     Eggs         :   2.50 servings  (cost: $1.25)
     Milk         :   1.25 servings  (cost: $0.75)

   Nutritional Totals:
   ------------------------------------------------------------
     Total Cost:    $3.15
     Calories:      2000.0 (min: 2000)
     Protein:       51.5g (min: 50g)
     Calcium:       811.3mg (min: 800mg)

Complete Code Walkthrough
--------------------------

Step 1: Define Data Model
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   @dataclass
   class Food:
       """Represents a food item with nutritional information."""
       name: str
       cost_per_serving: float  # $ per serving
       calories: float          # calories per serving
       protein: float           # grams per serving
       calcium: float           # mg per serving

   FOODS = [
       Food("Oatmeal", 0.30, 110, 4, 2),
       Food("Chicken", 2.40, 205, 32, 12),
       Food("Eggs", 0.50, 160, 13, 60),
       Food("Milk", 0.60, 160, 8, 285),
       Food("Apple Pie", 1.60, 420, 4, 22),
       Food("Pork", 2.90, 260, 14, 10),
   ]

Step 2: Create Variable Family
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/04_basic_lp/basic_lp.py
   :language: python
   :lines: 112-118
   :dedent: 4

Step 3: Set Objective Function
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/04_basic_lp/basic_lp.py
   :language: python
   :lines: 123-129
   :dedent: 4

Step 4: Add Nutritional Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/04_basic_lp/basic_lp.py
   :language: python
   :lines: 132-160
   :dedent: 4

Step 5: Solve and Interpret Solution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   optimizer = LXOptimizer().use_solver("ortools")
   solution = optimizer.solve(model)

   if solution.is_optimal():
       for food_name, qty in solution.get_mapped(servings).items():
           print(f"{food_name}: {qty:.2f} servings")

Learning Objectives
-------------------

After completing this example, you should understand:

1. **Variable Families**: How one ``LXVariable`` expands to multiple solver variables
2. **Data-Driven Modeling**: Using ``.from_data()`` to auto-create variables
3. **Lambda Coefficients**: Extracting data attributes for model coefficients
4. **Automatic Summation**: How expressions expand over all indexed instances
5. **Fluent API**: Chaining method calls for readable model building
6. **Solution Access**: Using ``.get_mapped()`` for type-safe solution retrieval

Common Patterns
---------------

Pattern 1: Single-Model Variable Family
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   variable = (
       LXVariable[DataModel, VarType]("var_name")
       .continuous()  # or .integer(), .binary()
       .bounds(lower=0, upper=None)
       .indexed_by(lambda m: m.key)
       .from_data(DATA)
   )

Pattern 2: Data-Driven Objective
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   cost_expr = LXLinearExpression().add_term(
       variable,
       coeff=lambda m: m.cost_attribute
   )
   model.minimize(cost_expr)  # or .maximize()

Pattern 3: Resource Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   model.add_constraint(
       LXConstraint("resource_name")
       .expression(
           LXLinearExpression().add_term(
               variable,
               coeff=lambda m: m.resource_usage
           )
       )
       .ge()  # or .le(), .eq()
       .rhs(MINIMUM_REQUIREMENT)
   )

Understanding the Solution
---------------------------

Why This Diet?
~~~~~~~~~~~~~~

The optimal solution chose:

- **Oatmeal (4.00 servings)**: Cheapest source of calories
- **Eggs (2.50 servings)**: Good protein-to-cost ratio
- **Milk (1.25 servings)**: Excellent calcium source

It avoided:

- **Chicken, Pork**: Too expensive for the nutrition provided
- **Apple Pie**: High cost, low nutritional value relative to needs

Solution Characteristics
~~~~~~~~~~~~~~~~~~~~~~~~

The solution is at a **vertex** of the feasible region where exactly 3 constraints are **binding** (satisfied with equality):

1. Calories constraint: Exactly 2000 (at minimum)
2. Protein constraint: ~51.5g (slightly above minimum)
3. Calcium constraint: ~811mg (slightly above minimum)

This is typical of linear programming: optimal solutions occur at vertices where constraint boundaries intersect.

Linear Programming Basics
--------------------------

Key Properties
~~~~~~~~~~~~~~

LP problems have several important characteristics:

- **Linear objective**: No products of variables, only weighted sums
- **Linear constraints**: All constraint expressions are linear
- **Continuous variables**: Can take any non-negative value (not just integers)
- **Convex feasible region**: The set of feasible solutions is convex
- **Vertex optimality**: Optimal solution occurs at a vertex
- **Polynomial-time solvable**: Efficiently solved with simplex or interior-point methods

Why Linear Programming?
~~~~~~~~~~~~~~~~~~~~~~~~

LP is useful when:

- **Divisibility**: Resources can be fractionally allocated (e.g., servings)
- **Additivity**: Total effect equals sum of individual effects
- **Proportionality**: Effect is proportional to amount (doubling input doubles output)
- **Deterministic**: All parameters are known with certainty

Extending the Example
---------------------

Try These Modifications
~~~~~~~~~~~~~~~~~~~~~~~

1. **Add Upper Bounds**: Limit maximum servings per food

   .. code-block:: python

      .bounds(lower=0, upper=5)  # At most 5 servings

2. **Add Food Groups**: Ensure variety from different food groups

   .. code-block:: python

      # At least 2 servings from dairy
      dairy_expr = LXLinearExpression().add_term(
          servings,
          coeff=lambda f: 1.0 if f.group == "dairy" else 0.0
      )
      model.add_constraint(
          LXConstraint("min_dairy").expression(dairy_expr).ge().rhs(2.0)
      )

3. **Add Maximum Constraints**: Limit sugar, fat, sodium

   .. code-block:: python

      model.add_constraint(
          LXConstraint("max_sugar")
          .expression(sugar_expr)
          .le()
          .rhs(MAX_SUGAR)
      )

4. **Multiple Nutrients**: Add vitamins, minerals, fiber
5. **Binary Choices**: Include or exclude foods entirely (convert to MIP)
6. **Multi-Day Planning**: Add time dimension for weekly meal planning

Comparison with Traditional Libraries
--------------------------------------

PuLP / Pyomo Approach
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Traditional approach - manual dictionary creation
   servings = {f.name: LpVariable(f"servings_{f.name}", lowBound=0)
               for f in FOODS}
   cost = lpSum([f.cost_per_serving * servings[f.name] for f in FOODS])

LumiX Approach
~~~~~~~~~~~~~~

.. code-block:: python

   # LumiX approach - automatic from data
   servings = (
       LXVariable[Food, float]("servings")
       .continuous()
       .from_data(FOODS)
   )
   cost = LXLinearExpression().add_term(
       servings,
       coeff=lambda f: f.cost_per_serving
   )

**Advantages**:

- Type-safe: ``servings`` is typed as ``LXVariable[Food, float]``
- Data-driven: Automatically expands from ``FOODS``
- No manual dictionaries
- IDE autocomplete and type checking
- Cleaner, more maintainable code

Next Steps
----------

After mastering this example:

1. **Example 01 (Production Planning)**: More complex single-model indexing
2. **Example 02 (Driver Scheduling)**: Multi-model indexing (THE KEY FEATURE)
3. **Example 03 (Facility Location)**: Mixed-integer programming
4. **Example 09 (Sensitivity Analysis)**: Understanding shadow prices

See Also
--------

**Related Examples**:

- :doc:`production_planning` - More complex single-model indexing
- :doc:`driver_scheduling` - Multi-model indexing introduction
- :doc:`facility_location` - Mixed-integer programming with binary variables

**API Reference**:

- :class:`lumix.core.variables.LXVariable`
- :class:`lumix.core.model.LXModel`
- :class:`lumix.core.constraints.LXConstraint`
- :class:`lumix.core.expressions.LXLinearExpression`

**User Guide**:

- :doc:`../getting-started/quickstart` - Getting started guide
- :doc:`../user-guide/core/variables` - Variable types and families
- :doc:`../user-guide/core/constraints` - Constraint modeling

Files in This Example
---------------------

- ``basic_lp.py`` - Main optimization model and solution display
- ``README.md`` - Detailed documentation and usage guide
