# Step 7: Multi-Period Production Planning with What-If Analysis

## Overview

Step 7 demonstrates LumiX's **what-if analysis** capabilities by extending Step 4's multi-period production planning model with interactive exploration of parameter changes and their impact on optimal solutions.

This step shows how to use what-if analysis for tactical decision-making, investment planning, and risk assessment by answering key business questions quickly without full scenario setup.

## What's New in Step 7

### Building on Step 4

Step 7 uses the same optimization model as Step 4 (multi-period production planning) but adds comprehensive what-if analysis on top:

| Aspect | Step 4 | Step 7 |
|--------|--------|--------|
| **Optimization Model** | Multi-period planning with setup costs | Same model |
| **Problem Scale** | 9 products × 4 periods (~1,600 variables) | Same scale |
| **After Optimization** | Display results, save to database | + Extensive what-if analysis |
| **HTML Report** | 4 tabs (Summary, Schedule, Resources, Orders) | 5 tabs (+ What-If Analysis) |
| **Business Insights** | Operational (what to produce) | + Tactical (what-if scenarios, investments) |

### New Features: Comprehensive What-If Analysis

| Feature | Description | Business Value |
|---------|-------------|----------------|
| **Capacity Change Scenarios** | Test impact of adding/removing resources | Quick ROI assessment |
| **Bottleneck Identification** | Systematically test all resources to find bottlenecks | Investment prioritization |
| **Sensitivity Ranges** | Show how profit varies with capacity | Optimal capacity sizing |
| **Investment Comparison** | Compare ROI of different expansion options | Capital allocation |
| **Risk Assessment** | Test downside scenarios (failures, disruptions) | Contingency planning |

## Key Business Questions Answered

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
   - Which gives better ROI per dollar invested?
   - How do different investment amounts compare?

## Running the Example

### Step 1: Populate the Database

```bash
cd tutorials/production_planning/step7_whatif_analysis
python sample_data.py
```

**Output**:
```
================================================================================
PRODUCTION PLANNING DATABASE SETUP - STEP 4 (LARGE-SCALE with ORM)
================================================================================

Scale: 9 products × 6 machines × 9 materials × 4 periods
Expected variables: ~1,600 (16x Step 3)

[Database population details...]

Database populated successfully!
```

### Step 2: Run Optimization with What-If Analysis

```bash
python production_whatif.py
```

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

### Step 3: View the Enhanced HTML Report

After running the optimization, open the generated report:

```bash
open production_whatif_report.html  # macOS
xdg-open production_whatif_report.html  # Linux
start production_whatif_report.html  # Windows
```

**Report Features** (5 tabs):

1. **Summary Dashboard** (from Step 4)
   - Total profit and key metrics
   - Profit by period
   - Resource efficiency gauges
   - Order fulfillment by priority

2. **What-If Analysis** (NEW)
   - Capacity change scenarios table
   - Bottleneck identification and ranking
   - Sensitivity ranges
   - Investment ROI comparison
   - Risk assessment matrix
   - Key insights and recommendations

3. **Production Schedule** (from Step 4)
   - Weekly production grid
   - Inventory tracking

4. **Resource Utilization** (from Step 4)
   - Machine capacity analysis
   - Material consumption

5. **Customer Orders** (from Step 4)
   - Order fulfillment by priority

## Console Output Walkthrough

### 1. Baseline Optimization

```
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
```

### 2. Machine Capacity What-If

```
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
```

### 3. Bottleneck Identification

```
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
```

### 4. Sensitivity Range Analysis

```
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
```

### 5. Investment Comparison

```
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
```

### 6. Risk Assessment

```
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
```

## What-If Analysis Types

### 1. Capacity Change Scenarios

**Quick assessment of resource changes:**

```python
# Add 50 hours to machine capacity
result = whatif.increase_constraint_rhs("machine_1_period_1", by=50)

# Increase material by 100 units
result = whatif.increase_constraint_rhs("material_3_period_1", by=100)
```

**Use Cases**:
- Quick tactical decisions (should we add overtime?)
- ROI analysis (is capacity expansion worth it?)
- Resource reallocation (move resources between periods?)

### 2. Bottleneck Identification

**Systematically test all constraints to find bottlenecks:**

The example tests adding 10 units to every resource constraint and ranks them by marginal value (profit increase per unit).

**Use Cases**:
- Investment prioritization (which capacity to expand first?)
- Process improvement (where to focus efforts?)
- Capacity planning (long-term expansion strategy)

### 3. Sensitivity Range Analysis

**Analyze how profit varies across range of capacity values:**

Tests multiple capacity levels (e.g., 100, 120, 140, ... 240 hours) to show profit curve.

**Use Cases**:
- Optimal capacity sizing (where are diminishing returns?)
- Understanding profit elasticity
- Budget allocation (how much capacity is enough?)

### 4. Investment Comparison

**Compare ROI of different capacity investments:**

Tests multiple expansion options side-by-side (e.g., +50 vs +100 hours, machine vs material).

**Use Cases**:
- Capital budgeting (limited investment budget)
- Trade-off analysis (machines vs materials vs labor)
- Strategic planning (multi-year investment roadmap)

### 5. Risk Assessment

**Test downside scenarios (capacity reduction):**

```python
# Equipment failure scenario
result = whatif.decrease_constraint_rhs("machine_1_period_1", by=50)

# Supply chain disruption
result = whatif.tighten_constraint("material_3_period_1", by_percent=0.2)
```

**Use Cases**:
- Contingency planning (what if equipment fails?)
- Risk quantification (how much would disruption cost?)
- Mitigation priorities (which risks to address first?)

## Key LumiX What-If Analysis Features

### 1. Create What-If Analyzer

```python
from lumix import LXWhatIfAnalyzer

# Create analyzer with model and optimizer
whatif = LXWhatIfAnalyzer(model, optimizer, baseline_solution=baseline)
```

### 2. Increase Constraint RHS

```python
# Add 50 units
result = whatif.increase_constraint_rhs("capacity_labor", by=50)

# Set to specific value
result = whatif.increase_constraint_rhs("capacity_labor", to=1500)

# Increase by percentage
result = whatif.increase_constraint_rhs("capacity_labor", by_percent=0.2)
```

### 3. Decrease Constraint RHS

```python
# Subtract 50 units
result = whatif.decrease_constraint_rhs("capacity_machine", by=50)

# Decrease by percentage
result = whatif.decrease_constraint_rhs("capacity_machine", by_percent=0.15)
```

### 4. Relax/Tighten Constraints

```python
# Make constraint less restrictive (easier to satisfy)
result = whatif.relax_constraint("capacity", by=100)

# Make constraint more restrictive (harder to satisfy)
result = whatif.tighten_constraint("capacity", by_percent=0.2)
```

### 5. Access Results

```python
result.description           # Description of change
result.original_objective    # Baseline profit
result.new_objective        # New profit after change
result.delta_objective      # Change in profit
result.delta_percentage     # Percentage change
result.original_solution    # Baseline solution
result.new_solution         # New solution
```

## Business Decision Examples

### Example 1: Capacity Investment Decision

```python
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
```

### Example 2: Bottleneck Prioritization

```python
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
```

### Example 3: Risk Mitigation

```python
# Test equipment failure scenario
result = whatif.decrease_constraint_rhs("machine_1_period_1", by=50)

expected_loss = abs(result.delta_objective)
insurance_cost = 200.0  # Annual insurance premium

if insurance_cost < expected_loss:
    print(f"✓ BUY INSURANCE: Net benefit = ${expected_loss - insurance_cost:.2f}")
else:
    print(f"✗ SELF-INSURE: Insurance too expensive")
```

## HTML Report Details

### What-If Analysis Tab

The new "What-If Analysis" tab includes:

**1. Baseline & Key Metrics**
- Baseline profit (optimal solution)
- Number of scenarios tested
- Number of bottlenecks found

**2. Capacity Change Scenarios Table**
- Each scenario tested
- Original vs new profit
- Delta ($ and %)
- Marginal value per unit

**3. Bottleneck Identification & Ranking**
- All resources ranked by marginal value
- Type (machine vs material)
- Priority (HIGH/MEDIUM/LOW)
- Top 15 bottlenecks displayed

**4. Sensitivity Analysis**
- Profit vs capacity table
- Shows first analyzed resource
- Baseline marked
- Percentage changes vs baseline

**5. Investment ROI Comparison**
- All investment options tested
- Sorted by ROI per unit
- Best option highlighted
- Recommendations

**6. Risk Assessment (Downside Scenarios)**
- Equipment failure scenarios
- Supply disruption scenarios
- Profit loss quantified
- Severity ratings (HIGH/MEDIUM/LOW)

**7. Key Insights & Recommendations**
- Top bottleneck identified
- Best investment highlighted
- Highest risk scenario
- Actionable recommendations

## Comparison: Step 4 vs Step 7

| Aspect | Step 4 | Step 7 |
|--------|--------|--------|
| **Problem Type** | Multi-period production planning | Same |
| **Optimization** | Solve once, display results | Solve once + extensive what-if |
| **Analysis Time** | 10-30 seconds | 10-30s baseline + 30-60s what-if |
| **Console Output** | Production plan | + What-if scenarios, bottlenecks, ROI |
| **HTML Report** | 4 tabs | 5 tabs (+ What-If Analysis) |
| **Business Value** | Operational plan | + Tactical decisions, investments |
| **Use Case** | What to produce | + Where to invest, what-if questions |
| **Time Horizon** | Weekly execution | Weekly execution + tactical planning |

## Key Learnings

### 1. What-If vs Scenario Analysis

**What-If Analysis (Step 7)**:
- Quick tactical changes
- Single parameter at a time
- Interactive exploration
- Minutes to hours decisions
- ROI-focused

**Scenario Analysis (Step 5)**:
- Strategic planning
- Multiple coordinated changes
- Pre-defined scenarios
- Long-term decisions
- Comprehensive comparison

**When to use What-If**: Quick tactical decisions, testing specific changes, finding bottlenecks, ROI assessment

**When to use Scenario**: Strategic planning, complex multi-parameter changes, formal reporting

### 2. Marginal Value for Investment Decisions

**Marginal value = profit increase per unit of resource**

Use marginal value to:
- Set maximum willingness to pay for capacity
- Compare investment options
- Prioritize resource expansion
- Assess ROI

**Rule of thumb**: If cost per unit < marginal value → profitable investment

### 3. Bottleneck Discovery

- Test all constraints systematically
- Rank by marginal value
- Focus on high marginal value constraints first
- Non-bottlenecks have zero marginal value (excess capacity)

### 4. Diminishing Returns

Sensitivity ranges reveal:
- Linear region (constant marginal value)
- Diminishing returns region (decreasing marginal value)
- Saturation point (zero marginal value)

**Use this to**: Determine optimal capacity levels, avoid over-investment

### 5. Risk Quantification

Test downside scenarios to:
- Quantify potential losses
- Prioritize mitigation efforts
- Justify insurance/contingency costs
- Build resilience

## Advanced Topics

### Combining What-If with Sensitivity Analysis

- **What-If** (Step 7): Test specific parameter changes, quick ROI
- **Sensitivity** (Step 6): Marginal values from LP duals, mathematical guarantees

**Best practice**: Use sensitivity analysis (Step 6) for marginal values, then what-if analysis (Step 7) for exploring specific scenarios

### Multi-Resource What-If

Test changing multiple resources simultaneously:

```python
# Create modified model with multiple changes
# (Not directly supported by current API, would require manual model modification)
```

### What-If with Goal Programming

When using goal programming (as in this example):
- What-if can test relaxing/tightening goal constraints
- Assess trade-offs between competing goals
- Find Pareto improvements

### Automated What-If Loops

For systematic exploration:

```python
for capacity in range(100, 300, 20):
    result = whatif.increase_constraint_rhs("machine_1_period_1", to=capacity)
    print(f"Capacity: {capacity}, Profit: {result.new_objective}")
```

## Troubleshooting

### What-If Analysis Takes Too Long

**Symptom**: What-if analysis takes > 2 minutes

**Possible Causes**:
- Too many scenarios tested
- Solver not optimized
- Large model

**Solutions**:
- Test fewer scenarios
- Use faster solver (CPLEX, Gurobi)
- Reduce model size for exploratory analysis

### Marginal Values Are Zero

**Symptom**: All bottlenecks have zero marginal value

**Possible Causes**:
- Constraints are not binding (excess capacity)
- Goal constraints are limiting profit
- Test amount is too small

**Solutions**:
- Check resource utilization
- Relax goal constraints
- Increase test amount (10 → 50 units)

### Results Don't Match Expectations

**Symptom**: What-if results contradict intuition

**Possible Causes**:
- Other constraints become binding
- Non-linear effects from binary variables
- Goal programming trade-offs

**Solutions**:
- Check which constraints are binding
- Examine solution details
- Test multiple increment sizes

## Use Cases

### 1. Tactical Capacity Planning
**Question**: Should we rent additional equipment for next month?

**Analysis**: Test capacity increase, compare profit gain to rental cost

### 2. Overtime Decision
**Question**: Should we run overtime shifts this week?

**Analysis**: Test labor hour increase, compare to overtime cost

### 3. Supply Chain Negotiation
**Question**: How much should we pay for additional raw materials?

**Analysis**: Find marginal value of materials, use as maximum price

### 4. Equipment Investment
**Question**: Which machine to upgrade first?

**Analysis**: Compare marginal values, prioritize highest ROI

### 5. Risk Management
**Question**: What's the cost of equipment downtime?

**Analysis**: Test capacity reduction scenarios, quantify losses

### 6. Budget Allocation
**Question**: How to allocate $100K investment budget?

**Analysis**: Compare ROI of different capacity expansions

## Next Steps

You've completed the Production Planning tutorial with what-if analysis! You've learned:

✅ **Step 1**: Basic linear programming
✅ **Step 2**: Database integration with SQLAlchemy ORM
✅ **Step 3**: Goal programming with customer orders
✅ **Step 4**: Large-scale multi-period planning
✅ **Step 5**: Scenario analysis (if completed)
✅ **Step 6**: Sensitivity analysis (if completed)
✅ **Step 7**: What-if analysis and tactical decision support

**Advanced Topics to Explore**:
- Combine what-if with Monte Carlo simulation (stochastic analysis)
- Build interactive dashboards with what-if capabilities
- Automate what-if analysis for recurring decisions
- Integrate what-if into decision support systems
- Real-time what-if for operational adjustments

**Related Examples**:
- **Example 10 (What-If Analysis)**: Standalone what-if example
- **Example 08 (Scenario Analysis)**: Strategic scenario comparison
- **Example 09 (Sensitivity Analysis)**: Shadow prices and reduced costs

## See Also

- **Timetabling Step 4**: Large-scale scheduling with what-if
- **LumiX Documentation**: What-If Analysis guide
- **Example 10**: What-If Analysis standalone example
- **SQLAlchemy Documentation**: https://docs.sqlalchemy.org/

---

**Tutorial Complete!**

You've mastered production planning optimization from basic to production-ready scale with comprehensive what-if analysis using LumiX and SQLAlchemy ORM. These techniques apply to real-world manufacturing, supply chain, resource allocation, and tactical decision-making problems.
