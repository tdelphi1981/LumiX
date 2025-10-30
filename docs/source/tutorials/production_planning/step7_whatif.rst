Step 7: What-If Analysis
========================

In this final step, we extend Step 4's multi-period production planning model with comprehensive **what-if analysis** capabilities for interactive tactical decision support.

Overview
--------

What-if analysis enables quick exploration of "what if we changed this parameter?" questions without setting up full scenarios. This is ideal for tactical decision-making, investment planning, and risk assessment.

What's New in Step 7
--------------------

Building on Step 4
~~~~~~~~~~~~~~~~~~

Step 7 uses the **same optimization model** as Step 4 (multi-period production planning) but adds comprehensive what-if analysis on top:

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Aspect
     - Step 4
     - Step 7
   * - **Optimization Model**
     - Multi-period with setup costs
     - Same model
   * - **Problem Scale**
     - 9 products × 4 periods (~1,600 vars)
     - Same scale
   * - **After Optimization**
     - Display results, save to DB
     - + Extensive what-if analysis
   * - **HTML Report**
     - 4 tabs (Summary, Schedule, etc.)
     - 5 tabs (+ What-If Analysis)
   * - **Business Insights**
     - Operational (what to produce)
     - + Tactical (investments, scenarios)

New Features
~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 40 30

   * - Feature
     - Description
     - Business Value
   * - **Capacity Change Scenarios**
     - Test impact of adding/removing resources
     - Quick ROI assessment
   * - **Bottleneck Identification**
     - Systematically test all resources
     - Investment prioritization
   * - **Sensitivity Ranges**
     - Show profit vs capacity curves
     - Optimal capacity sizing
   * - **Investment Comparison**
     - Compare ROI of different options
     - Capital allocation
   * - **Risk Assessment**
     - Test downside scenarios
     - Contingency planning

Key Business Questions Answered
--------------------------------

Step 7 helps answer tactical questions like:

1. **What if we add 50 hours to cutting machine capacity?**

   - How much will profit increase?
   - What's the marginal value per hour?

2. **Which resource is the biggest bottleneck?**

   - Which capacity expansion gives best ROI?
   - Where should we invest first?

3. **How sensitive is profit to capacity changes?**

   - At what capacity do we see diminishing returns?
   - What's the optimal capacity level?

4. **What if we lose machine capacity (equipment failure)?**

   - How much profit would we lose?
   - Which failures are most costly?

5. **Should we invest in machines or materials?**

   - Which gives better ROI per dollar?
   - How do different investment amounts compare?

Running the Example
-------------------

Step 1: Populate the Database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   cd tutorials/production_planning/step7_whatif_analysis
   python sample_data.py

**Output:**

.. code-block:: text

   ================================================================================
   PRODUCTION PLANNING DATABASE SETUP - STEP 7 (WHAT-IF ANALYSIS)
   ================================================================================

   Scale: 9 products × 6 machines × 9 materials × 4 periods
   Expected variables: ~1,600

   [Database population details...]

   Database populated successfully!

Step 2: Run Optimization with What-If Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   python production_whatif.py

The program will:

1. Initialize database and create ORM session
2. Build multi-period production model (same as Step 4)
3. Solve for baseline optimal solution
4. **Run comprehensive what-if analysis**:

   - Test machine capacity changes
   - Test material availability changes
   - Identify all bottlenecks systematically
   - Generate sensitivity ranges
   - Compare investment options
   - Assess downside risk scenarios

5. Display all results to console
6. Save baseline solution to database
7. Generate enhanced HTML report with what-if visualizations

**Expected solve time**: 10-30 seconds for baseline + 30-60 seconds for what-if analysis

Step 3: View the Enhanced HTML Report
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # macOS
   open production_whatif_report.html

   # Linux
   xdg-open production_whatif_report.html

   # Windows
   start production_whatif_report.html

**Report Features** (5 tabs):

1. **Summary Dashboard** (from Step 4)

   - Total profit and key metrics
   - Profit by period
   - Resource efficiency gauges
   - Order fulfillment by priority

2. **What-If Analysis** (NEW)

   - Capacity change scenarios table
   - Bottleneck identification and ranking
   - Sensitivity ranges with charts
   - Investment ROI comparison
   - Risk assessment matrix
   - Key insights and recommendations

3. **Production Schedule** (from Step 4)
4. **Resource Utilization** (from Step 4)
5. **Customer Orders** (from Step 4)

Console Output Walkthrough
--------------------------

1. Baseline Optimization
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   ================================================================================
   LumiX Tutorial: Production Planning - Step 7 (WHAT-IF ANALYSIS)
   ================================================================================

   Building large-scale multi-period production model (ORM)...
     Scale: 9 products × 4 periods

   Solving baseline model with ortools...

   ================================================================================
   MULTI-PERIOD PRODUCTION PLAN (BASELINE)
   ================================================================================
   Status: optimal
   Total Objective Value: $45,234.56

   Week 1:
   --------------------------------------------------------------------------------
   Product              Production      Inventory       Profit Contrib
   --------------------------------------------------------------------------------
   Chair                50.00           0.00            $2,250.00
   Table                25.00           5.00            $3,000.00
   ...

2. Machine Capacity What-If
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   --------------------------------------------------------------------------------
   1. MACHINE CAPACITY WHAT-IF SCENARIOS
   --------------------------------------------------------------------------------

   What if we add 50 hours to Cutting Machine in Week 1?
     Original Profit:  $45,234.56
     New Profit:       $45,734.56
     Change:           $500.00 (+1.11%)
     Marginal Value:   $10.00 per hour

   Interpretation: Adding 50 hours of cutting machine capacity would increase
   profit by $500, yielding $10 per hour marginal value.

3. Bottleneck Identification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   --------------------------------------------------------------------------------
   3. BOTTLENECK IDENTIFICATION
   --------------------------------------------------------------------------------

   Testing impact of adding 10 units to each resource constraint...

   Resource                                 Marginal Value       Priority
   --------------------------------------------------------------------------------
   Cutting Machine (Week 1)                 $10.00              HIGH
   Assembly Station (Week 1)                $5.50               HIGH
   Wood (Week 1)                            $3.25               MEDIUM
   Finishing Station (Week 2)               $2.10               MEDIUM
   Metal (Week 1)                           $0.00               LOW
   ...

   Top bottleneck: Cutting Machine (Week 1) with $10/unit marginal value
   Recommendation: Prioritize expanding cutting machine capacity

4. Sensitivity Range Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   --------------------------------------------------------------------------------
   4. SENSITIVITY RANGE ANALYSIS
   --------------------------------------------------------------------------------

   Analyzing sensitivity: Cutting Machine capacity in Week 1
   Range: 100 - 250 hours (baseline: 160)

   Capacity (hrs)       Profit               vs Baseline
   --------------------------------------------------------------------------------
   100                  $42,234.56           -6.64%
   120                  $43,434.56           -3.98%
   140                  $44,334.56           -1.99%
   160                  $45,234.56           +0.00% (baseline)
   180                  $46,034.56           +1.77%
   200                  $46,734.56           +3.32%
   220                  $47,234.56           +4.42%
   240                  $47,534.56           +5.08%

   Observation: Linear increase up to 200 hours, then diminishing returns

5. Investment Comparison
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   --------------------------------------------------------------------------------
   5. INVESTMENT COMPARISON
   --------------------------------------------------------------------------------

   Comparing different capacity expansion options:

   Investment Option                                  Profit Increase      ROI/Unit
   --------------------------------------------------------------------------------
   Cutting Machine +50hrs (Week 1)                    $500.00             $10.00
   Cutting Machine +100hrs (Week 1)                   $900.00             $9.00
   Assembly Station +50hrs (Week 1)                   $275.00             $5.50
   Wood +100 units (Week 1)                           $325.00             $3.25
   Wood +200 units (Week 1)                           $550.00             $2.75

   --------------------------------------------------------------------------------
   INVESTMENT RECOMMENDATION
   --------------------------------------------------------------------------------

   Best Investment Option:
     Cutting Machine +50hrs (Week 1)
     Profit Impact: $500.00
     ROI: $10.00 per unit

   If cost per hour < $10, this investment is profitable.

6. Risk Assessment
~~~~~~~~~~~~~~~~~~

.. code-block:: text

   --------------------------------------------------------------------------------
   6. RISK ASSESSMENT (Downside Scenarios)
   --------------------------------------------------------------------------------

   What if Cutting Machine loses 50 hours in Week 1 (equipment failure)?
     Original Profit:  $45,234.56
     New Profit:       $44,734.56
     Loss:             -$500.00 (-1.11%)
     ⚠ Risk: Equipment failure would cost $500.00

   What if Wood supply decreases by 20% in Week 1?
     Original Profit:  $45,234.56
     New Profit:       $44,584.56
     Loss:             -$650.00 (-1.44%)
     ⚠ Supply Risk: 20% shortage would cost $650.00

   Recommendation: Prepare contingency plans for cutting machine backup
   and wood supply diversification.

What-If Analysis Types
----------------------

1. Capacity Change Scenarios
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Quick assessment of resource changes:

.. code-block:: python

   from lumix import LXWhatIfAnalyzer

   # Create analyzer
   whatif = LXWhatIfAnalyzer(model, optimizer, baseline_solution=baseline)

   # Add 50 hours to machine capacity
   result = whatif.increase_constraint_rhs("machine_1_period_1", by=50)
   print(f"Profit increase: ${result.delta_objective:,.2f}")

   # Increase material by 100 units
   result = whatif.increase_constraint_rhs("material_3_period_1", by=100)

**Use Cases:**

- Quick tactical decisions (should we add overtime?)
- ROI analysis (is capacity expansion worth it?)
- Resource reallocation (move resources between periods?)

2. Bottleneck Identification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Systematically test all constraints to find bottlenecks:

.. code-block:: python

   # Test adding 10 units to every resource
   test_amount = 10.0
   improvements = []

   for machine in machines:
       for period in periods:
           constraint_name = f"machine_{machine.id}_period_{period.id}"
           result = whatif.increase_constraint_rhs(constraint_name, by=test_amount)
           marginal_value = result.delta_objective / test_amount
           improvements.append((constraint_name, marginal_value))

   # Sort by marginal value
   bottlenecks = sorted(improvements, key=lambda x: x[1], reverse=True)

**Use Cases:**

- Investment prioritization (which capacity to expand first?)
- Process improvement (where to focus efforts?)
- Capacity planning (long-term expansion strategy)

3. Sensitivity Range Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Analyze how profit varies across range of capacity values:

.. code-block:: python

   # Test multiple capacity levels
   capacity_values = [100, 120, 140, 160, 180, 200, 220, 240]

   for capacity in capacity_values:
       result = whatif.increase_constraint_rhs("machine_1_period_1", to=capacity)
       print(f"Capacity: {capacity}, Profit: ${result.new_objective:,.2f}")

**Use Cases:**

- Optimal capacity sizing (where are diminishing returns?)
- Understanding profit elasticity
- Budget allocation (how much capacity is enough?)

4. Investment Comparison
~~~~~~~~~~~~~~~~~~~~~~~~

Compare ROI of different capacity investments:

.. code-block:: python

   investment_options = [
       ("machine_1", 50, "Cutting Machine +50hrs"),
       ("machine_1", 100, "Cutting Machine +100hrs"),
       ("material_1", 100, "Wood +100 units"),
   ]

   for constraint, amount, description in investment_options:
       result = whatif.increase_constraint_rhs(constraint, by=amount)
       roi_per_unit = result.delta_objective / amount
       print(f"{description}: ROI = ${roi_per_unit:.2f}/unit")

**Use Cases:**

- Capital budgeting (limited investment budget)
- Trade-off analysis (machines vs materials vs labor)
- Strategic planning (multi-year investment roadmap)

5. Risk Assessment
~~~~~~~~~~~~~~~~~~

Test downside scenarios (capacity reduction):

.. code-block:: python

   # Equipment failure scenario
   result = whatif.decrease_constraint_rhs("machine_1_period_1", by=50)
   print(f"Equipment failure would cost: ${abs(result.delta_objective):,.2f}")

   # Supply chain disruption
   result = whatif.tighten_constraint("material_3_period_1", by_percent=0.2)
   print(f"20% supply shortage would cost: ${abs(result.delta_objective):,.2f}")

**Use Cases:**

- Contingency planning (what if equipment fails?)
- Risk quantification (how much would disruption cost?)
- Mitigation priorities (which risks to address first?)

Key LumiX What-If Features
--------------------------

Create What-If Analyzer
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXWhatIfAnalyzer

   # Create analyzer with model and optimizer
   whatif = LXWhatIfAnalyzer(model, optimizer, baseline_solution=baseline)

   # Get baseline (cached automatically)
   baseline = whatif.get_baseline_solution()

Increase Constraint RHS
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Add 50 units
   result = whatif.increase_constraint_rhs("capacity_labor", by=50)

   # Set to specific value
   result = whatif.increase_constraint_rhs("capacity_labor", to=1500)

   # Increase by percentage
   result = whatif.increase_constraint_rhs("capacity_labor", by_percent=0.2)

Decrease Constraint RHS
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Subtract 50 units
   result = whatif.decrease_constraint_rhs("capacity_machine", by=50)

   # Decrease by percentage
   result = whatif.decrease_constraint_rhs("capacity_machine", by_percent=0.15)

Relax/Tighten Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Make constraint less restrictive
   result = whatif.relax_constraint("capacity", by=100)

   # Make constraint more restrictive
   result = whatif.tighten_constraint("capacity", by_percent=0.2)

Access Results
~~~~~~~~~~~~~~

.. code-block:: python

   result.description           # Description of change
   result.original_objective    # Baseline profit
   result.new_objective        # New profit after change
   result.delta_objective      # Change in profit
   result.delta_percentage     # Percentage change
   result.original_solution    # Baseline solution
   result.new_solution         # New solution

Model Copying with ORM Detachment
----------------------------------

Critical Implementation Detail
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

What-if analysis requires **copying the model** to apply changes without affecting the original. When using ORM (SQLAlchemy/Django), this presents a challenge:

**Problem**: ORM objects are bound to database sessions and cannot be pickled/deep copied directly.

**Solution**: LumiX implements an **ORM detachment strategy** in ``__deepcopy__`` methods:

.. code-block:: python

   from copy import deepcopy

   # This works even with ORM data!
   modified_model = deepcopy(model)

How It Works
~~~~~~~~~~~~

1. **Detect ORM Objects**: Check for SQLAlchemy (``_sa_instance_state``) or Django (``_state``, ``_meta``) markers

2. **Materialize Data**: Force-load lazy relationships before copying

3. **Detach from Session**: Create plain Python objects with same attributes

4. **Handle Lambda Closures**: Inspect function closures for captured ORM objects and detach them

5. **Deep Copy**: Use standard ``deepcopy`` with detached objects

Implementation
~~~~~~~~~~~~~~

The strategy is implemented in:

- ``lumix.utils.copy_utils``: Utility functions for ORM detachment
- ``LXModel.__deepcopy__``: Model-level copying
- ``LXVariable.__deepcopy__``: Variable-level copying with closure handling
- ``LXConstraint.__deepcopy__``: Constraint-level copying

Example:

.. code-block:: python

   from lumix.utils.copy_utils import detach_orm_object

   # Detach single ORM object
   product = session.query(Product).first()
   detached = detach_orm_object(product)
   # Now safe to pickle/deepcopy

   # Automatically handled in model copying
   modified_model = deepcopy(model)  # Works with ORM data

For complete details, see :doc:`/user-guide/utils/model-copying`.

Business Decision Examples
--------------------------

Example 1: Capacity Investment Decision
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Test capacity increase
   result = whatif.increase_constraint_rhs("machine_1_period_1", by=50)

   # Decision logic
   cost_per_hour = 100.0  # Equipment rental cost
   total_cost = cost_per_hour * 50
   roi = result.delta_objective - total_cost

   if roi > 0:
       print(f"✓ INVEST: ROI = ${roi:,.2f}")
       print(f"  Payback: {total_cost / result.delta_objective:.1f} periods")
   else:
       print(f"✗ DON'T INVEST: Loss = ${abs(roi):,.2f}")

Example 2: Bottleneck Prioritization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Find top bottleneck
   bottlenecks = sorted(
       [(name, marginal_value) for name, marginal_value in all_constraints],
       key=lambda x: x[1],
       reverse=True
   )

   top_bottleneck = bottlenecks[0]
   print(f"Priority 1: {top_bottleneck[0]}")
   print(f"  Marginal Value: ${top_bottleneck[1]:.2f}/unit")
   print(f"  Action: Expand this resource first")

Example 3: Risk Mitigation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Test equipment failure scenario
   result = whatif.decrease_constraint_rhs("machine_1_period_1", by=50)

   expected_loss = abs(result.delta_objective)
   insurance_cost = 200.0  # Annual insurance premium

   if insurance_cost < expected_loss:
       print(f"✓ BUY INSURANCE: Net benefit = ${expected_loss - insurance_cost:.2f}")
   else:
       print(f"✗ SELF-INSURE: Insurance too expensive")

Comparison: Step 4 vs Step 7
-----------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Aspect
     - Step 4
     - Step 7
   * - **Problem Type**
     - Multi-period production planning
     - Same
   * - **Optimization**
     - Solve once, display results
     - Solve + extensive what-if
   * - **Analysis Time**
     - 10-30 seconds
     - 10-30s baseline + 30-60s what-if
   * - **Console Output**
     - Production plan
     - + What-if scenarios, bottlenecks, ROI
   * - **HTML Report**
     - 4 tabs
     - 5 tabs (+ What-If Analysis)
   * - **Business Value**
     - Operational plan
     - + Tactical decisions, investments
   * - **Use Case**
     - What to produce
     - + Where to invest, what-if questions
   * - **Time Horizon**
     - Weekly execution
     - Weekly + tactical planning

Key Learnings
-------------

1. What-If vs Scenario Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**What-If Analysis** (Step 7):

- Quick tactical changes
- Single parameter at a time
- Interactive exploration
- Minutes to hours decisions
- ROI-focused

**Scenario Analysis** (Step 5):

- Strategic planning
- Multiple coordinated changes
- Pre-defined scenarios
- Long-term decisions
- Comprehensive comparison

**When to use What-If**: Quick tactical decisions, testing specific changes, finding bottlenecks, ROI assessment

**When to use Scenario**: Strategic planning, complex multi-parameter changes, formal reporting

2. Marginal Value for Investment Decisions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Marginal value** = profit increase per unit of resource

Use marginal value to:

- Set maximum willingness to pay for capacity
- Compare investment options
- Prioritize resource expansion
- Assess ROI

**Rule of thumb**: If cost per unit < marginal value → profitable investment

3. Bottleneck Discovery
~~~~~~~~~~~~~~~~~~~~~~~

- Test all constraints systematically
- Rank by marginal value
- Focus on high marginal value constraints first
- Non-bottlenecks have zero marginal value (excess capacity)

4. Diminishing Returns
~~~~~~~~~~~~~~~~~~~~~~

Sensitivity ranges reveal:

- Linear region (constant marginal value)
- Diminishing returns region (decreasing marginal value)
- Saturation point (zero marginal value)

**Use this to**: Determine optimal capacity levels, avoid over-investment

5. Risk Quantification
~~~~~~~~~~~~~~~~~~~~~~

Test downside scenarios to:

- Quantify potential losses
- Prioritize mitigation efforts
- Justify insurance/contingency costs
- Build resilience

Troubleshooting
---------------

What-If Analysis Takes Too Long
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptom**: What-if analysis takes > 2 minutes

**Possible Causes**:

- Too many scenarios tested
- Solver not optimized
- Large model

**Solutions**:

- Test fewer scenarios
- Use faster solver (CPLEX, Gurobi)
- Reduce model size for exploratory analysis

Marginal Values Are Zero
~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptom**: All bottlenecks have zero marginal value

**Possible Causes**:

- Constraints are not binding (excess capacity)
- Goal constraints are limiting profit
- Test amount is too small

**Solutions**:

- Check resource utilization
- Relax goal constraints
- Increase test amount (10 → 50 units)

Results Don't Match Expectations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptom**: What-if results contradict intuition

**Possible Causes**:

- Other constraints become binding
- Non-linear effects from binary variables
- Goal programming trade-offs

**Solutions**:

- Check which constraints are binding
- Examine solution details
- Test multiple increment sizes

Use Cases
---------

1. **Tactical Capacity Planning**: Should we rent additional equipment?
2. **Overtime Decision**: Should we run overtime shifts?
3. **Supply Chain Negotiation**: Maximum price for additional materials?
4. **Equipment Investment**: Which machine to upgrade first?
5. **Risk Management**: What's the cost of equipment downtime?
6. **Budget Allocation**: How to allocate $100K investment budget?

Next Steps
----------

You've completed the Production Planning tutorial with what-if analysis!

✅ **Step 1**: Basic linear programming
✅ **Step 2**: Database integration with SQLAlchemy ORM
✅ **Step 3**: Goal programming with customer orders
✅ **Step 4**: Large-scale multi-period planning
✅ **Step 5**: Scenario analysis (if completed)
✅ **Step 6**: Sensitivity analysis (if completed)
✅ **Step 7**: What-if analysis and tactical decision support

**Advanced Topics to Explore**:

- Combine what-if with Monte Carlo simulation
- Build interactive dashboards with what-if capabilities
- Automate what-if analysis for recurring decisions
- Integrate what-if into decision support systems

**Related Documentation**:

- :doc:`/examples/whatif_analysis` - Standalone what-if example
- :doc:`/user-guide/analysis/whatif` - What-if analysis guide
- :doc:`/user-guide/utils/model-copying` - ORM-safe copying guide
- :doc:`../timetabling/step4_scaled` - Large-scale scheduling

See Also
--------

- :doc:`step6_sensitivity` - Sensitivity analysis with shadow prices
- :doc:`step5_scenario` - Strategic scenario comparison
- :doc:`/user-guide/analysis/index` - Analysis tools overview
- :doc:`/api/analysis/index` - Complete API reference
