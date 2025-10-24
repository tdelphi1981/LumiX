Sensitivity Analysis Example
=============================

Overview
--------

This example demonstrates LumiX's **sensitivity analysis** capabilities for understanding optimal solutions through shadow prices, reduced costs, and bottleneck identification.

Sensitivity analysis reveals which constraints are limiting profitability, which resources are most valuable, and how sensitive the solution is to parameter changes - essential for investment decisions and resource prioritization.

Problem Description
-------------------

After solving a production planning problem, a manufacturing company wants to understand:

**Shadow Prices**: What is the marginal value of each resource?

**Reduced Costs**: What is the opportunity cost of each variable?

**Bottlenecks**: Which constraints are limiting profitability?

**Investment Priorities**: Where should we invest to maximize ROI?

Mathematical Foundation
-----------------------

**Primal Problem**:

.. math::

   \text{Maximize} \quad c^T x \\
   \text{subject to} \quad Ax \leq b, \quad x \geq 0

**Dual Problem**:

.. math::

   \text{Minimize} \quad b^T y \\
   \text{subject to} \quad A^T y \geq c, \quad y \geq 0

**Shadow Prices** (:math:`y`): Dual variables representing marginal value of relaxing constraints.

**Reduced Costs**: Opportunity cost of forcing a variable to change from its optimal value.

Key Features
------------

Shadow Price Analysis
~~~~~~~~~~~~~~~~~~~~~~

Analyze marginal value of constraints:

.. literalinclude:: ../../../examples/09_sensitivity_analysis/sensitivity_analysis.py
   :language: python
   :lines: 133-143

**Interpretation**:

- Shadow price > 0: Constraint is binding (at capacity)
- Shadow price = 0: Constraint has slack (not binding)
- Shadow price = $2.50: Each additional unit increases profit by $2.50

Bottleneck Identification
~~~~~~~~~~~~~~~~~~~~~~~~~~

Find constraints limiting profitability:

.. literalinclude:: ../../../examples/09_sensitivity_analysis/sensitivity_analysis.py
   :language: python
   :lines: 164-174
   :dedent: 4

Bottlenecks are binding constraints with significant shadow prices.

Most Sensitive Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Rank constraints by sensitivity:

.. literalinclude:: ../../../examples/09_sensitivity_analysis/sensitivity_analysis.py
   :language: python
   :lines: 181-188
   :dedent: 4

Prioritize relaxing constraints with highest shadow prices.

Reduced Cost Analysis
~~~~~~~~~~~~~~~~~~~~~

Analyze variable opportunity costs:

.. literalinclude:: ../../../examples/09_sensitivity_analysis/sensitivity_analysis.py
   :language: python
   :lines: 198-203

**Interpretation**:

- Reduced cost = 0: Variable in optimal basis
- Reduced cost > 0: Increasing variable would decrease objective

Running the Example
-------------------

**Prerequisites**:

.. code-block:: bash

   pip install lumix
   pip install ortools  # or cplex, gurobi

**Run**:

.. code-block:: bash

   cd examples/09_sensitivity_analysis
   python sensitivity_analysis.py

**Expected Output**:

.. code-block:: text

   ====================================================================
   SENSITIVITY ANALYSIS: Production Planning Solution Insights
   ====================================================================

   OPTIMAL SOLUTION SUMMARY
   --------------------------------------------------------------------
   Status: optimal
   Objective: $12,345.68
   Solve time: 0.123s

   ====================================================================
   CONSTRAINT SENSITIVITY ANALYSIS
   ====================================================================

   capacity_Labor Hours:
     Shadow Price: $2.5000
     Binding: YES
     ➜ Interpretation: Each additional labor hour increases profit by $2.50

   capacity_Machine Hours:
     Shadow Price: $1.2500
     Binding: YES
     ➜ Interpretation: Each additional machine hour increases profit by $1.25

   capacity_Raw Materials:
     Shadow Price: $0.0000
     Binding: NO

   --------------------------------------------------------------------
   BINDING CONSTRAINTS (At Capacity)
   --------------------------------------------------------------------
   Found 2 binding constraints:
     • capacity_Labor Hours
       Shadow Price: $2.5000
     • capacity_Machine Hours
       Shadow Price: $1.2500

   --------------------------------------------------------------------
   TOP 5 MOST VALUABLE CONSTRAINTS TO RELAX
   --------------------------------------------------------------------
     1. capacity_Labor Hours
        Shadow Price: $2.5000
        Expected ROI: $2.50 per unit relaxation

     2. capacity_Machine Hours
        Shadow Price: $1.2500
        Expected ROI: $1.25 per unit relaxation

Complete Code Walkthrough
--------------------------

Step 1: Solve Model with Sensitivity Enabled
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/09_sensitivity_analysis/sensitivity_analysis.py
   :language: python
   :lines: 106-109
   :dedent: 4

**Note**: ``.enable_sensitivity()`` requests dual values from solver.

Step 2: Create Sensitivity Analyzer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/09_sensitivity_analysis/sensitivity_analysis.py
   :language: python
   :lines: 112
   :dedent: 4

Step 3: Analyze Individual Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/09_sensitivity_analysis/sensitivity_analysis.py
   :language: python
   :lines: 131-143
   :dedent: 4

Step 4: Identify Bottlenecks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/09_sensitivity_analysis/sensitivity_analysis.py
   :language: python
   :lines: 160-174
   :dedent: 4

Step 5: Generate Business Insights
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/09_sensitivity_analysis/sensitivity_analysis.py
   :language: python
   :lines: 249-265
   :dedent: 4

Learning Objectives
-------------------

After completing this example, you should understand:

1. **Shadow Prices**: Marginal value of relaxing constraints
2. **Reduced Costs**: Opportunity cost of changing variables
3. **Binding Constraints**: Identifying active constraints (bottlenecks)
4. **Duality Theory**: Relationship between primal and dual problems
5. **Investment Analysis**: Using sensitivity for ROI calculations
6. **Complementary Slackness**: Why slack constraints have zero shadow price

Common Patterns
---------------

Pattern 1: Constraint Sensitivity Check
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   sens = analyzer.analyze_constraint("constraint_name")

   if sens.is_binding:
       print(f"Bottleneck: ${sens.shadow_price:.2f} per unit")
   else:
       print(f"Has slack: {sens.slack:.2f} units available")

Pattern 2: Investment Decision
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   labor_sens = analyzer.analyze_constraint("capacity_Labor")

   # Decision logic
   if labor_sens.shadow_price > hiring_cost_per_hour:
       print("✓ HIRE: Shadow price exceeds cost")
       roi = labor_sens.shadow_price - hiring_cost_per_hour
       print(f"  Expected profit: ${roi:.2f} per hour")
   else:
       print("✗ DON'T HIRE: Cost exceeds value")

Pattern 3: Prioritize Improvements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get top constraints to relax
   top_constraints = analyzer.get_most_sensitive_constraints(top_n=5)

   for i, (name, sens) in enumerate(top_constraints, 1):
       print(f"{i}. {name}: ${sens.shadow_price:.2f} per unit")

Business Insights Generated
----------------------------

Resource Investment Priorities
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   Based on shadow prices, prioritize investment in:

   1. Labor Hours
      Marginal Value: $2.50 per unit
      Status: BINDING (at capacity)
      ✓ HIGH PRIORITY: Strong ROI expected

   2. Machine Hours
      Marginal Value: $1.25 per unit
      Status: BINDING (at capacity)
      → MODERATE PRIORITY: Positive ROI

   3. Raw Materials
      Marginal Value: $0.00 per unit
      Status: NOT BINDING (excess capacity)
      ✗ LOW PRIORITY: No value from expansion

Hiring Recommendation
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   ► HIRING RECOMMENDATION:
     - Labor capacity is constraining profit
     - Each additional labor hour adds $2.50 profit
     - Consider hiring if cost per hour < $2.50

Risk Assessment
~~~~~~~~~~~~~~~

.. code-block:: text

   ⚠ HIGH SENSITIVITY:
     - 2 constraints are binding
     - Solution highly sensitive to parameter changes
     - Small capacity variations significantly impact profit
     - Recommendation: Build buffer capacity

Sensitivity Metrics Explained
------------------------------

Shadow Prices (Dual Values)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Definition**: Marginal value of relaxing a constraint by one unit.

**Example**: Labor has shadow price = $2.50

- Increasing labor by 1 hour → Profit increases by $2.50
- Decreasing labor by 1 hour → Profit decreases by $2.50

**Business Use**:

- Maximum price to pay for one more unit
- Value of capacity expansion
- Investment prioritization

Reduced Costs
~~~~~~~~~~~~~

**Definition**: Opportunity cost of forcing a variable to change.

**Example**: Production variable has reduced cost = $0.50

- Forcing production up by 1 unit → Profit decreases by $0.50
- Variable currently at lower bound
- Not economical to increase

**Business Use**:

- Identify products worth producing more
- Understand why some products not produced
- Product portfolio decisions

Complementary Slackness
~~~~~~~~~~~~~~~~~~~~~~~~

At optimality:

- If constraint has slack → Shadow price = 0
- If shadow price > 0 → Constraint is binding (no slack)
- If variable at bound → Reduced cost may be non-zero
- If reduced cost = 0 → Variable in basis (not at bound)

Extending the Example
---------------------

Try These Modifications
~~~~~~~~~~~~~~~~~~~~~~~

1. **Multi-Period**: Analyze sensitivity over time
2. **Stochastic**: Probabilistic sensitivity analysis
3. **Range Analysis**: Valid ranges for shadow prices
4. **Parametric**: How shadow prices change with RHS
5. **Interactive Dashboard**: Real-time sensitivity visualization

Next Steps
----------

After mastering this example:

1. **Example 08 (Scenario Analysis)**: Strategic planning scenarios
2. **Example 10 (What-If Analysis)**: Quick tactical decisions
3. **Advanced Duality Theory**: Linear programming duality

See Also
--------

**Related Examples**:

- :doc:`scenario_analysis` - Testing multiple scenarios
- :doc:`whatif_analysis` - Quick parameter changes
- :doc:`production_planning` - Base model for analysis

**API Reference**:

- :class:`lumix.analysis.LXSensitivityAnalyzer`
- :class:`lumix.solution.LXSolution`
- :class:`lumix.core.model.LXModel`

Files in This Example
---------------------

- ``sensitivity_analysis.py`` - Main sensitivity analysis demonstration
- ``sample_data.py`` - Data models (Product, Resource) and sample data
- ``README.md`` - Detailed documentation and usage guide
