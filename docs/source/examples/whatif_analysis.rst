What-If Analysis Example
=========================

Overview
--------

This example demonstrates LumiX's **what-if analysis** capabilities for quick, interactive exploration of parameter changes and their impact on optimal solutions.

What-if analysis provides immediate answers to tactical questions without requiring full scenario setup - perfect for rapid decision support and operational planning.

Problem Description
-------------------

A manufacturing company needs quick answers to tactical questions:

- **What if** we get 200 more labor hours?
- **What if** machine capacity is reduced by 100 hours (equipment failure)?
- **What if** we relax minimum production requirements?
- **Which resources** are most valuable to expand?
- **What is the ROI** of different capacity investments?

**Objective**: Quickly assess impact of parameter changes on profitability.

Mathematical Foundation
-----------------------

**Base Model**:

.. math::

   \text{Maximize} \quad c^T x \\
   \text{subject to} \quad Ax \leq b, \quad x \geq 0

**What-If Modification**: Change constraint RHS from :math:`b` to :math:`b'`:

.. math::

   Ax \leq b + \Delta b

Analyze impact: :math:`\Delta \text{objective} = f(x^*_{new}) - f(x^*_{old})`

Key Features
------------

Constraint Modification
~~~~~~~~~~~~~~~~~~~~~~~

Quickly modify and resolve:

.. literalinclude:: ../../../examples/10_whatif_analysis/whatif_analysis.py
   :language: python
   :lines: 123-128

**Key Points**:

- ``.increase_constraint_rhs()`` increases right-hand side
- ``by=200`` adds 200 units
- Returns result object with impact analysis

Multiple Modification Types
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Various ways to modify constraints:

.. code-block:: python

   # Increase by absolute amount
   result = whatif.increase_constraint_rhs("capacity", by=200)

   # Decrease by absolute amount
   result = whatif.decrease_constraint_rhs("capacity", by=100)

   # Set to specific value
   result = whatif.increase_constraint_rhs("capacity", to=1500)

   # Relax by percentage (make less restrictive)
   result = whatif.relax_constraint("minimum", by_percent=0.5)

   # Tighten by percentage (make more restrictive)
   result = whatif.tighten_constraint("capacity", by_percent=0.2)

Bottleneck Discovery
~~~~~~~~~~~~~~~~~~~~

Test all constraints to find bottlenecks:

.. literalinclude:: ../../../examples/10_whatif_analysis/whatif_analysis.py
   :language: python
   :lines: 204-206

Sensitivity Range Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Analyze objective across parameter range:

.. literalinclude:: ../../../examples/10_whatif_analysis/whatif_analysis.py
   :language: python
   :lines: 260-265

Investment Comparison
~~~~~~~~~~~~~~~~~~~~~

Compare multiple investment options:

.. literalinclude:: ../../../examples/10_whatif_analysis/whatif_analysis.py
   :language: python
   :lines: 316-327

Running the Example
-------------------

**Prerequisites**:

.. code-block:: bash

   pip install lumix
   pip install ortools  # or cplex, gurobi

**Run**:

.. code-block:: bash

   cd examples/10_whatif_analysis
   python whatif_analysis.py

**Expected Output**:

.. code-block:: text

   ====================================================================
   WHAT-IF ANALYSIS: Quick Impact Assessment
   ====================================================================

   Solving baseline model...
   Baseline Profit: $12,345.67

   --------------------------------------------------------------------
   WHAT-IF #1: Increase Labor Hours by 200
   --------------------------------------------------------------------
   Original Profit:  $12,345.67
   New Profit:       $12,845.67
   Change:           $500.00 (+4.05%)

   Interpretation: Adding 200 labor hours increases profit by $500.00
   Marginal value:  $2.50 per labor hour

   --------------------------------------------------------------------
   WHAT-IF #2: Decrease Machine Hours by 100 (Equipment Failure)
   --------------------------------------------------------------------
   Original Profit:  $12,345.67
   New Profit:       $12,220.67
   Change:           -$125.00 (-1.01%)

   ⚠ Risk Assessment: Machine failure would cost $125.00 in lost profit

   ====================================================================
   BOTTLENECK IDENTIFICATION: Testing Resource Constraints
   ====================================================================

   Resource                       Improvement      Per Unit       Priority
   --------------------------------------------------------------------
   Labor Hours                    $25.00           $2.50          HIGH
   Machine Hours                  $12.50           $1.25          MEDIUM
   Raw Materials                  $0.00            $0.00          LOW

   ► Primary Bottleneck: Labor Hours
     Marginal Value: $2.50 per unit
     Recommendation: Prioritize expanding this resource

Complete Code Walkthrough
--------------------------

Step 1: Create What-If Analyzer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/10_whatif_analysis/whatif_analysis.py
   :language: python
   :lines: 109-111

Step 2: Test Parameter Changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/10_whatif_analysis/whatif_analysis.py
   :language: python
   :lines: 119-156

Step 3: Identify Bottlenecks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/10_whatif_analysis/whatif_analysis.py
   :language: python
   :lines: 195-242

Step 4: Analyze Sensitivity Ranges
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/10_whatif_analysis/whatif_analysis.py
   :language: python
   :lines: 256-298

Step 5: Compare Investment Options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/10_whatif_analysis/whatif_analysis.py
   :language: python
   :lines: 309-354

Learning Objectives
-------------------

After completing this example, you should understand:

1. **Quick Impact Assessment**: Rapidly evaluate parameter changes
2. **Bottleneck Discovery**: Systematically find most valuable resources
3. **ROI Calculation**: Compare profit impact to investment cost
4. **Risk Quantification**: Measure downside of adverse changes
5. **Investment Prioritization**: Rank opportunities by marginal value
6. **Interactive Analysis**: Enable agile decision making

Common Patterns
---------------

Pattern 1: Quick Test
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   whatif = LXWhatIfAnalyzer(model, optimizer)

   # Test single change
   result = whatif.increase_constraint_rhs("capacity", by=100)

   if result.delta_objective > 0:
       print(f"Benefit: ${result.delta_objective:.2f}")
       roi_per_unit = result.delta_objective / 100
       print(f"ROI: ${roi_per_unit:.2f} per unit")

Pattern 2: Decision Logic
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   result = whatif.increase_constraint_rhs("labor", by=100)

   cost = 25.0 * 100  # $25/hour × 100 hours
   benefit = result.delta_objective
   net = benefit - cost

   if net > 0:
       print(f"✓ INVEST: Net benefit = ${net:.2f}")
   else:
       print(f"✗ DON'T INVEST: Net loss = ${abs(net):.2f}")

Pattern 3: Systematic Testing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Test all resource constraints
   resources = ["Labor", "Machine", "Material"]

   for resource in resources:
       constraint_name = f"capacity_{resource}"
       result = whatif.relax_constraint(constraint_name, by=10.0)
       marginal = result.delta_objective / 10.0
       print(f"{resource}: ${marginal:.2f} per unit")

Business Decision Examples
---------------------------

Hiring Decision
~~~~~~~~~~~~~~~

.. code-block:: python

   # Test hiring 4 new workers (40 hours/week each)
   result = whatif.increase_constraint_rhs("capacity_Labor", by=160)

   # Cost analysis
   hourly_wage = 25.0
   total_cost = hourly_wage * 160
   profit_increase = result.delta_objective
   net_benefit = profit_increase - total_cost

   print(f"Cost: ${total_cost:.2f}")
   print(f"Benefit: ${profit_increase:.2f}")
   print(f"Net: ${net_benefit:.2f}")

   if net_benefit > 0:
       payback_weeks = total_cost / (profit_increase / 52)
       print(f"Payback: {payback_weeks:.1f} weeks")

Equipment Investment
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Test purchasing new machine (200 additional hours/week)
   result = whatif.increase_constraint_rhs("capacity_Machine", by=200)

   equipment_cost = 50000.0  # One-time cost
   annual_benefit = result.delta_objective * 52  # 52 weeks/year
   payback_years = equipment_cost / annual_benefit

   print(f"Equipment Cost: ${equipment_cost:,.0f}")
   print(f"Annual Benefit: ${annual_benefit:,.0f}")
   print(f"Payback Period: {payback_years:.1f} years")

Risk Assessment
~~~~~~~~~~~~~~~

.. code-block:: python

   # Test supply chain disruption (30% material shortage)
   result = whatif.tighten_constraint("capacity_Materials", by_percent=0.3)

   expected_loss = abs(result.delta_objective)
   loss_percent = abs(result.delta_percentage)

   print(f"⚠ Risk: 30% material shortage")
   print(f"Expected Loss: ${expected_loss:,.2f} ({loss_percent:.1f}%)")

What-If Result Structure
-------------------------

Each analysis returns ``LXWhatIfResult``:

.. code-block:: python

   result.description            # Description of change
   result.original_objective     # Baseline objective
   result.new_objective          # New objective after change
   result.delta_objective        # Change in objective
   result.delta_percentage       # Percentage change
   result.original_solution      # Baseline solution
   result.new_solution          # New solution
   result.changes_applied       # List of modifications

What-If vs Scenario Analysis
-----------------------------

**Use What-If Analysis when**:

- Need quick tactical decisions
- Testing single parameter changes
- Exploring sensitivity ranges
- Finding bottlenecks
- Time-sensitive decisions

**Use Scenario Analysis when**:

- Complex multi-parameter changes
- Strategic planning (long-term)
- Comparing business scenarios
- Formal reporting required
- Need reproducible scenarios

Advantages of What-If
----------------------

Speed
~~~~~

- Immediate feedback on changes
- No scenario setup required
- Interactive exploration
- Quick iteration

Simplicity
~~~~~~~~~~

- Simple API for common changes
- Intuitive constraint manipulation
- No model structure knowledge needed

Flexibility
~~~~~~~~~~~

- Test any parameter change
- Compare multiple options
- Customize to specific needs

Decision Support
~~~~~~~~~~~~~~~~

- Clear ROI calculations
- Risk quantification
- Investment prioritization
- Actionable insights

Extending the Example
---------------------

Try These Modifications
~~~~~~~~~~~~~~~~~~~~~~~

1. **Variable Bounds**: Modify variable upper/lower bounds
2. **Cost Changes**: Test objective coefficient changes
3. **Multiple Changes**: Combine several parameter modifications
4. **Time Series**: Analyze changes over multiple periods
5. **Probabilistic**: Add Monte Carlo for risk assessment

Next Steps
----------

After mastering this example:

1. **Example 08 (Scenario Analysis)**: Strategic planning scenarios
2. **Example 09 (Sensitivity Analysis)**: Shadow prices and reduced costs
3. **Interactive Dashboards**: Build real-time decision support tools

See Also
--------

**Related Examples**:

- :doc:`scenario_analysis` - Strategic planning with scenarios
- :doc:`sensitivity_analysis` - Understanding shadow prices
- :doc:`production_planning` - Base model for what-if

**API Reference**:

- :class:`lumix.analysis.LXWhatIfAnalyzer`
- :class:`lumix.analysis.LXWhatIfResult`
- :class:`lumix.core.model.LXModel`

Files in This Example
---------------------

- ``whatif_analysis.py`` - Main what-if analysis demonstration
- ``sample_data.py`` - Data models (Product, Resource) and sample data
- ``README.md`` - Detailed documentation and usage guide
