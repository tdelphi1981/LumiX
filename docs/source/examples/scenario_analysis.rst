Scenario Analysis Example
==========================

Overview
--------

This example demonstrates LumiX's **scenario analysis** capabilities for exploring different business conditions and strategic decisions through systematic what-if analysis.

The production planning scenario analysis helps companies understand how different market conditions, resource availability, and strategic investments affect optimal production plans and profitability.

Problem Description
-------------------

A manufacturing company wants to understand how different business scenarios affect their optimal production plan and profitability.

**Scenarios to Explore**:

- Optimistic: Market expansion with increased resource capacity
- Pessimistic: Resource constraints due to supply chain issues
- Realistic: Moderate growth with balanced expansion
- Strategic: Labor investment, automation, material procurement

**Objective**: Compare multiple scenarios to identify best strategies and assess risks.

Mathematical Formulation
------------------------

**Base Model** (Production Planning):

.. math::

   \text{Maximize} \quad \sum_{p \in \text{Products}} \text{profit}_p \cdot x_p

**Subject to**:

.. math::

   \sum_{p} \text{usage}_{p,r} \cdot x_p &\leq \text{capacity}_r, \quad \forall r \in \text{Resources} \\
   x_p &\geq \text{min}_p, \quad \forall p \in \text{Products}

**Scenario Modifications**: Each scenario modifies constraint RHS values (capacities, minimums).

Key Features
------------

Scenario Creation
~~~~~~~~~~~~~~~~~

Define scenarios with constraint modifications:

.. literalinclude:: ../../../examples/08_scenario_analysis/scenario_analysis.py
   :language: python
   :lines: 121-128
   :dedent: 4

**Key Points**:

- ``.modify_constraint_rhs()`` changes right-hand side of constraints
- ``multiply=1.30`` increases capacity by 30%
- ``.describe()`` adds explanation for reporting

Batch Scenario Execution
~~~~~~~~~~~~~~~~~~~~~~~~~

Run multiple scenarios efficiently:

.. literalinclude:: ../../../examples/08_scenario_analysis/scenario_analysis.py
   :language: python
   :lines: 108-110
   :dedent: 4

**Features**:

- ``include_baseline=True`` adds current model as baseline scenario
- ``run_all_scenarios()`` solves all scenarios in batch
- Returns dictionary mapping scenario names to solutions

Scenario Comparison
~~~~~~~~~~~~~~~~~~~

Compare results across scenarios:

.. literalinclude:: ../../../examples/08_scenario_analysis/scenario_analysis.py
   :language: python
   :lines: 204-210
   :dedent: 4

**Outputs**:

- Tabular comparison of objective values
- Status for each scenario
- Percentage change vs baseline
- Best/worst scenario identification

Parameter Sensitivity
~~~~~~~~~~~~~~~~~~~~~

Analyze sensitivity to parameter ranges:

.. literalinclude:: ../../../examples/08_scenario_analysis/scenario_analysis.py
   :language: python
   :lines: 228-233
   :dedent: 4

Tests objective value across range of parameter values.

Running the Example
-------------------

**Prerequisites**:

.. code-block:: bash

   pip install lumix
   pip install ortools  # or cplex, gurobi

**Run**:

.. code-block:: bash

   cd examples/08_scenario_analysis
   python scenario_analysis.py

**Expected Output**:

.. code-block:: text

   ====================================================================
   SCENARIO ANALYSIS: Production Planning Under Different Conditions
   ====================================================================

   CREATING BUSINESS SCENARIOS
   --------------------------------------------------------------------

   1. OPTIMISTIC SCENARIO: Market Expansion
      - Hire more workers (+30% labor capacity)
      - Purchase new machines (+20% machine capacity)
      - Increase material procurement (+25% materials)

   2. PESSIMISTIC SCENARIO: Resource Constraints
      - Labor shortage (-20% labor capacity)
      - Supply chain issues (-15% material availability)

   ====================================================================
   SCENARIO COMPARISON RESULTS
   ====================================================================

   Scenario                Status      Objective       vs Baseline
   --------------------------------------------------------------------
   market_expansion        optimal     $15,234.89      +23.4%
   moderate_growth         optimal     $13,456.78      +9.0%
   labor_investment        optimal     $13,234.56      +7.2%
   automation              optimal     $12,987.65      +5.2%
   baseline                optimal     $12,345.67      -
   resource_constraints    optimal     $10,123.45      -18.0%

   --------------------------------------------------------------------
   BEST SCENARIO: market_expansion
   --------------------------------------------------------------------
   Objective Value: $15,234.89
   Improvement over baseline: $2,889.22 (23.4%)

   ====================================================================
   SENSITIVITY ANALYSIS: Labor Capacity Impact
   ====================================================================

   Multiplier   Labor Hours     Objective Value      vs Baseline
   --------------------------------------------------------------------
   0.7          700             $10,542.13          -14.6%
   0.8          800             $11,234.56          -9.0%
   0.9          900             $11,890.23          -3.7%
   1.0          1000            $12,345.67          +0.0%
   1.1          1100            $12,891.34          +4.4%
   1.2          1200            $13,432.89          +8.8%
   1.3          1300            $13,974.45          +13.2%

Complete Code Walkthrough
--------------------------

Step 1: Create Scenario Analyzer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/08_scenario_analysis/scenario_analysis.py
   :language: python
   :lines: 104-109
   :dedent: 4

Step 2: Define Business Scenarios
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/08_scenario_analysis/scenario_analysis.py
   :language: python
   :lines: 116-154
   :dedent: 4

Step 3: Run All Scenarios
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/08_scenario_analysis/scenario_analysis.py
   :language: python
   :lines: 194-198
   :dedent: 4

Step 4: Compare and Analyze Results
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/08_scenario_analysis/scenario_analysis.py
   :language: python
   :lines: 201-220
   :dedent: 4

Step 5: Parameter Sensitivity Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/08_scenario_analysis/scenario_analysis.py
   :language: python
   :lines: 223-248
   :dedent: 4

Learning Objectives
-------------------

After completing this example, you should understand:

1. **Scenario Modeling**: How to define business scenarios with parameter changes
2. **Batch Execution**: Running multiple scenarios efficiently
3. **Result Comparison**: Analyzing and comparing scenario outcomes
4. **Parameter Sensitivity**: Testing ranges of parameter values
5. **Risk Assessment**: Quantifying downside risks and upside opportunities
6. **Strategic Planning**: Using scenarios for decision support

Common Patterns
---------------

Pattern 1: Resource Capacity Scenario
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   scenario = (
       LXScenario[Model]("scenario_name")
       .modify_constraint_rhs("capacity_Resource1", multiply=1.2)
       .modify_constraint_rhs("capacity_Resource2", multiply=0.9)
       .describe("Increase Resource1, decrease Resource2")
   )

Pattern 2: Demand Scenario
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   high_demand = (
       LXScenario[Product]("high_demand")
       .modify_constraint_rhs("min_production_A", multiply=1.5)
       .modify_constraint_rhs("min_production_B", multiply=1.3)
       .describe("50% increase in product A demand")
   )

Pattern 3: Multi-Parameter Scenario
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   complex_scenario = (
       LXScenario[Model]("complex")
       .modify_constraint_rhs("capacity_Labor", multiply=1.3)
       .modify_constraint_rhs("capacity_Machine", multiply=0.8)
       .modify_constraint_rhs("min_production", to=150.0)
       .describe("Labor expansion with machine constraints")
   )

Scenario Types
--------------

Optimistic Scenarios
~~~~~~~~~~~~~~~~~~~~

Test best-case outcomes:

- Market expansion
- Resource abundance
- High efficiency
- **Use**: Understand maximum potential

Pessimistic Scenarios
~~~~~~~~~~~~~~~~~~~~~

Test worst-case outcomes:

- Resource constraints
- Supply chain disruptions
- Market downturns
- **Use**: Risk assessment and contingency planning

Realistic Scenarios
~~~~~~~~~~~~~~~~~~~

Test expected outcomes:

- Moderate growth
- Balanced changes
- Historical trends
- **Use**: Most likely planning baseline

Strategic Scenarios
~~~~~~~~~~~~~~~~~~~

Test specific strategic decisions:

- Investment options (labor vs automation)
- Market focus (product mix changes)
- Process improvements
- **Use**: Evaluate strategic alternatives

Business Insights
-----------------

The example generates actionable insights:

**Resource Impact Analysis**:

- Labor capacity: Highest marginal value (+$X per hour)
- Machine capacity: Second most impactful
- Materials: Adequate current capacity

**Investment Priorities**:

1. Labor expansion: Best ROI
2. Automation: Long-term efficiency gains
3. Material procurement: Lower priority

**Risk Exposure**:

- Downside risk: -18% profit under resource constraints
- Upside potential: +23% profit with market expansion
- Recommendation: Build buffer capacity

Extending the Example
---------------------

Try These Modifications
~~~~~~~~~~~~~~~~~~~~~~~

1. **Price Scenarios**: Vary product prices and costs
2. **Demand Scenarios**: Different demand patterns
3. **Multi-Stage**: Sequential decision scenarios
4. **Monte Carlo**: Probabilistic scenario generation
5. **Conditional**: Scenario trees with dependencies

Next Steps
----------

After mastering this example:

1. **Example 09 (Sensitivity Analysis)**: Understanding shadow prices
2. **Example 10 (What-If Analysis)**: Quick tactical decisions
3. **Scenario Tree Modeling**: Sequential decision making

See Also
--------

**Related Examples**:

- :doc:`sensitivity_analysis` - Shadow prices and reduced costs
- :doc:`whatif_analysis` - Quick parameter changes
- :doc:`production_planning` - Base model for scenarios

**API Reference**:

- :class:`lumix.analysis.LXScenario`
- :class:`lumix.analysis.LXScenarioAnalyzer`
- :class:`lumix.core.model.LXModel`

Files in This Example
---------------------

- ``scenario_analysis.py`` - Main scenario analysis demonstration
- ``sample_data.py`` - Data models (Product, Resource) and sample data
- ``README.md`` - Detailed documentation and usage guide
