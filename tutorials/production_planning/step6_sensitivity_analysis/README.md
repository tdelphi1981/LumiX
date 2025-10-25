# Step 6: Multi-Period Production Planning with Sensitivity Analysis

## Overview

Step 6 demonstrates LumiX's **sensitivity analysis** capabilities by extending Step 4's multi-period production planning model with comprehensive analysis of the optimal solution's economic structure.

This step shows how to extract actionable business insights from optimization solutions, including shadow prices, reduced costs, bottleneck identification, and investment recommendations.

## 💡 Key Innovation: LP Relaxation for Sensitivity Analysis

**This tutorial uses LP relaxation** to enable full sensitivity analysis while still modeling setup costs:

### Binary vs Continuous Formulation

| Aspect | Step 4 (MIP) | Step 6 (LP Relaxation) |
|--------|-------------|------------------------|
| Setup Variable | `is_produced ∈ {0, 1}` (binary) | `is_produced ∈ [0, 1]` (continuous) |
| Problem Type | Mixed Integer Program | Pure Linear Program |
| Sensitivity Analysis | ❌ Not available | ✅ Fully available |
| Shadow Prices | None | Real values |
| Reduced Costs | None | Real values |
| Interpretation | Exact binary decision | Threshold-based (>= 0.5 = produced) |

### Why LP Relaxation?

**Sensitivity analysis requires continuous variables**. By relaxing the binary requirement from `{0, 1}` to `[0, 1]`:
- We get **full sensitivity analysis** (shadow prices, reduced costs)
- The optimizer often pushes values to 0 or 1 **naturally** due to cost structure
- We can interpret intermediate values using a **threshold** (>= 0.5 = produced)
- We enable **investment decision support** based on marginal values

### Setup Variable Interpretation

```python
# Continuous [0, 1] variable with threshold interpretation
is_produced[product, period] ∈ [0, 1]

# Interpretation rules:
if is_produced >= 0.5:
    decision = "Product IS produced in period (setup cost incurred)"
elif is_produced < 0.5:
    decision = "Product NOT produced in period (no setup cost)"
```

**In practice**: The optimizer typically pushes these to extremes (0.0 or 1.0) naturally, making the relaxation nearly equivalent to the binary formulation while enabling sensitivity analysis!

## What's New in Step 6

### Building on Step 4

Step 6 extends Step 4 with these key changes:
- **Same problem structure**: 9 products × 4 periods, machines, materials
- **LP Relaxation**: Binary `is_produced` → Continuous `[0, 1]` with threshold
- **Pure LP formulation**: All variables continuous (enables sensitivity analysis)
- **Setup costs**: Still modeled, using continuous relaxation
- **Batch constraints**: Still enforced, using continuous setup variable
- **Inventory management**: Identical to Step 4
- **Goal programming**: Same customer order priorities

### New Features: Full Sensitivity Analysis

| Feature | Description | Business Value | Status |
|---------|-------------|----------------|--------|
| **Shadow Prices** | Marginal value of relaxing each constraint | Resource investment prioritization | ✅ Working |
| **Reduced Costs** | Opportunity cost of changing variable values | Understanding optimal production mix | ✅ Working |
| **Binding Constraints** | Identification of constraints at capacity | Bottleneck detection | ✅ Working |
| **Bottleneck Ranking** | Top N constraints limiting profitability | Capacity expansion priorities | ✅ Working |
| **Investment Recommendations** | ROI estimates for capacity expansion | Data-driven capital allocation | ✅ Working |
| **Risk Assessment** | Solution sensitivity to parameter changes | Robustness evaluation | ✅ Working |

## Mathematical Foundation

### Shadow Prices (Dual Values)

For a constraint `∑ aᵢxᵢ ≤ b`, the **shadow price** λ satisfies:

```
∂f*/∂b = λ
```

Where `f*` is the optimal objective value.

**Interpretation**: If labor capacity has shadow price = $2.50:
- Increasing labor by 1 hour → Profit increases by $2.50
- Decreasing labor by 1 hour → Profit decreases by $2.50
- Shadow price = maximum value to pay for 1 more unit

### Reduced Costs

For a variable `x` at its bound, the **reduced cost** `r` represents:

```
r = opportunity cost of forcing x to increase by 1 unit
```

**Interpretation**:
- `r = 0` → Variable is in optimal basis
- `r > 0` → Variable at lower bound, not economical to increase
- `r < 0` → Variable at upper bound, not economical to decrease

### Complementary Slackness

At optimality, these conditions hold:
- If constraint has slack → shadow price = 0
- If shadow price > 0 → constraint is binding (no slack)

## Key Sensitivity Concepts

### 1. Shadow Price Analysis

**Definition**: Marginal value of relaxing a constraint by one unit

**Business Decisions**:
```python
# Example: Labor capacity has shadow price = $2.50/hour
if hiring_cost_per_hour < 2.50:
    decision = "HIRE MORE WORKERS"
    expected_roi = 2.50 - hiring_cost_per_hour
else:
    decision = "DO NOT EXPAND LABOR"
```

**Use Cases**:
- Resource procurement: Set maximum purchase prices
- Capacity planning: Prioritize expansion investments
- Contract negotiation: Value of constraint relaxations
- Budget allocation: Rank resource needs by marginal value

### 2. Binding Constraint Identification

**Definition**: Constraints satisfied with equality at optimum (no slack)

**Characteristics**:
- Operating at full capacity
- Has non-zero shadow price
- Limiting the objective value

**Business Implications**:
- These are your bottlenecks
- Relaxing increases profit
- Tightening decreases profit
- Focus improvement efforts here

### 3. Bottleneck Detection

**Definition**: Binding constraints with high shadow prices

**Priority Levels**:
| Shadow Price | Priority | Recommendation |
|--------------|----------|----------------|
| > $1.00 | HIGH | Strong ROI expected, expand ASAP |
| $0.10 - $1.00 | MEDIUM | Positive ROI, consider expansion |
| < $0.10 | LOW | Minimal impact, low priority |

### 4. Risk Assessment

**Solution Sensitivity**:
| Binding Constraints | Risk Level | Implication |
|---------------------|------------|-------------|
| ≥ 10 | HIGH | Highly sensitive, small changes impact profit significantly |
| 5-9 | MODERATE | Several bottlenecks, focus on top constraints |
| < 5 | LOW | Robust solution, good capacity buffer |

## Running the Example

### Step 1: Populate the Database

```bash
cd tutorials/production_planning/step6_sensitivity_analysis
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

### Step 2: Run the Optimization with Sensitivity Analysis

```bash
python production_sensitivity.py
```

The program will:
1. Initialize database and create ORM session
2. Load all data using ORM
3. Build multi-period model (same as Step 4)
4. **Enable sensitivity analysis** in optimizer
5. Solve using goal programming
6. **Create sensitivity analyzer**
7. **Analyze shadow prices for all constraints**
8. **Identify binding constraints and bottlenecks**
9. **Rank constraints by sensitivity**
10. **Generate investment recommendations**
11. Display comprehensive sensitivity analysis
12. Save solution to database
13. Generate enhanced HTML report with sensitivity insights

**Expected solve time**: 10-30 seconds

### Step 3: View the Enhanced HTML Report

After running the optimization, open the generated report:

```bash
open production_sensitivity_report.html  # macOS
xdg-open production_sensitivity_report.html  # Linux
start production_sensitivity_report.html  # Windows
```

**Report Features** (from Step 4):
- Summary Dashboard: Key metrics, profit by period
- Production Schedule: Weekly production grid
- Resource Utilization: Machine & material analysis
- Order Fulfillment: Customer order tracking

**New Report Sections** (Step 6):
- **Sensitivity Analysis Dashboard**: Key sensitivity metrics and risk assessment
- **Shadow Price Analysis**: Marginal value table for all constraints
- **Bottleneck Identification**: Ranked list of capacity expansion opportunities
- **Investment Recommendations**: Top 3 priorities with ROI estimates

## Console Output Walkthrough

### 1. Model Building

```
Building large-scale multi-period production model (ORM)...
  Scale: 9 products × 4 periods

  Creating decision variables...
    Created 36 production variables
    Created 36 setup variables (continuous [0,1] for LP relaxation)
    Created 36 inventory variables
    NOTE: All variables are continuous → Pure LP → Sensitivity analysis available!
```

### 2. Solution Summary with Setup Interpretation

```
================================================================================
MULTI-PERIOD PRODUCTION PLAN
================================================================================
Status: optimal
Total Objective Value: $45,234.56

Setup Variables Interpretation (continuous [0,1] with threshold 0.5):
  >= 0.5 → Product IS produced in period (setup incurred)
  < 0.5  → Product NOT produced in period (no setup)

Week 1:
--------------------------------------------------------------------------------
Product              Production      Setup [0,1]     Inventory       Profit
--------------------------------------------------------------------------------
Chair                50.00           1.000 ✓         0.00            $2,250.00
Table                25.00           1.000 ✓         5.00            $3,000.00
Desk                 15.00           0.950 ✓         0.00            $3,000.00
...
```

### 3. Constraint Sensitivity Analysis (WORKING!)

```
================================================================================
SENSITIVITY ANALYSIS: Solution Insights
================================================================================

This is a PURE LP problem (all variables continuous).
Shadow prices and reduced costs are fully available and valid!

--------------------------------------------------------------------------------
CONSTRAINT SENSITIVITY ANALYSIS (Shadow Prices)
--------------------------------------------------------------------------------

Machine Capacity Constraints:
Machine                   Period     Shadow Price       Status
--------------------------------------------------------------------------------
Cutting Machine           Week 1          $2.5000      BINDING
Cutting Machine           Week 2          $0.0000        Slack
Assembly Station          Week 1          $1.2500      BINDING
Finishing Station         Week 1          $0.8000      BINDING
...

Material Availability Constraints:
Material                  Period     Shadow Price       Status
--------------------------------------------------------------------------------
Wood                      Week 1          $0.7500      BINDING
Metal                     Week 1          $0.0000        Slack
Fabric                    Week 2          $1.1000      BINDING
...
```

### 4. Binding Constraints

```
--------------------------------------------------------------------------------
BINDING CONSTRAINTS (At Capacity)
--------------------------------------------------------------------------------

Found 12 binding constraints:
  • machine_1_period_1
    Shadow Price: $2.5000
    Interpretation: Each additional unit relaxes this constraint, increasing profit by $2.50
  • machine_3_period_1
    Shadow Price: $1.2500
    ...
```

### 5. Bottleneck Identification

```
--------------------------------------------------------------------------------
BOTTLENECK IDENTIFICATION
--------------------------------------------------------------------------------

Identified 8 bottlenecks:

These constraints are limiting profitability:

  machine_1_period_1:
    Shadow Price: $2.5000
    Impact: Relaxing by 1 unit → +$2.50 profit

  machine_3_period_1:
    Shadow Price: $1.2500
    Impact: Relaxing by 1 unit → +$1.25 profit
  ...
```

### 6. Top Sensitive Constraints

```
--------------------------------------------------------------------------------
TOP 10 MOST VALUABLE CONSTRAINTS TO RELAX
--------------------------------------------------------------------------------

Prioritize relaxing these constraints for maximum profit impact:

  1. machine_1_period_1
     Shadow Price: $2.5000
     Expected ROI: $2.50 per unit relaxation

  2. machine_3_period_1
     Shadow Price: $1.2500
     Expected ROI: $1.25 per unit relaxation
  ...
```

### 7. Business Insights & Investment Recommendations

```
================================================================================
BUSINESS INSIGHTS & INVESTMENT RECOMMENDATIONS
================================================================================

1. RESOURCE INVESTMENT PRIORITIES
--------------------------------------------------------------------------------

Based on shadow prices, prioritize investment in:

  1. machine_1_period_1
     Marginal Value: $2.50 per unit
     Status: BINDING (at capacity)
     [HIGH PRIORITY]: Strong ROI expected from capacity expansion

  2. machine_3_period_1
     Marginal Value: $1.25 per unit
     Status: BINDING (at capacity)
     [MODERATE PRIORITY]: Positive ROI from expansion
  ...

2. RISK ASSESSMENT
--------------------------------------------------------------------------------

  ⚡ MODERATE SENSITIVITY:
    - 12 binding constraints identified
    - Focus on relaxing the top binding constraints
    - Some resources have slack capacity
```

## HTML Report Sections

### 1. Summary Dashboard

Same as Step 4:
- Total profit and key metrics
- Profit by period (bar chart)
- Resource efficiency gauges
- Order fulfillment by priority

### 2. Sensitivity Analysis Dashboard (NEW)

![Sensitivity Dashboard](screenshots/sensitivity_dashboard.png)

**Key Metrics**:
- Number of binding constraints
- Number of bottlenecks
- Average shadow price
- **Sensitivity risk assessment** (HIGH/MODERATE/LOW)

**Shadow Price Interpretation Box**:
- What shadow prices mean
- How to use them for investment decisions

### 3. Shadow Price Analysis (NEW)

![Shadow Prices](screenshots/shadow_prices.png)

**Features**:
- Table of all constraint shadow prices
- Color-coded by magnitude (high/medium/low)
- Binding indicator (🔴 for binding constraints)
- Hover tooltips with detailed info
- Average shadow price per resource

**Interpretation Guide**:
- Legend explaining color coding
- Business meaning of shadow prices

### 4. Bottleneck Identification (NEW)

![Bottlenecks](screenshots/bottlenecks.png)

**Features**:
- Top 10 bottlenecks ranked by shadow price
- Priority badges (HIGH/MEDIUM/LOW)
- Expected profit impact per unit
- **Investment recommendation cards** (top 3)
  - Marginal value
  - ROI estimate
  - Expansion recommendation

### 5. Production Schedule

Same as Step 4:
- Multi-period production plan
- Inventory levels
- Total production and profit

### 6. Resource Utilization

Same as Step 4:
- Machine capacity utilization
- Material consumption

### 7. Customer Orders

Same as Step 4:
- Order fulfillment by priority
- Fulfillment status

## Key LumiX Sensitivity Analysis Features

### 1. Enable Sensitivity Analysis

```python
# Enable sensitivity analysis in optimizer
optimizer = LXOptimizer().use_solver("ortools").enable_sensitivity()
solution = optimizer.solve(model)
```

**Requirements**:
- Solver must support dual values (OR-Tools, CPLEX, Gurobi)
- Only works with LP models (not MIP with binary variables)

### 2. Create Sensitivity Analyzer

```python
from lumix import LXSensitivityAnalyzer

# After solving
analyzer = LXSensitivityAnalyzer(model, solution)
```

### 3. Analyze Individual Constraints

```python
# Get shadow price and binding status
sens = analyzer.analyze_constraint("machine_1_period_1")

print(f"Shadow Price: ${sens.shadow_price:.2f}")
print(f"Binding: {sens.is_binding}")
```

### 4. Analyze Individual Variables

```python
# Get reduced cost and basis status
var_sens = analyzer.analyze_variable("production")

print(f"Reduced Cost: ${var_sens.reduced_cost:.6f}")
print(f"In Basis: {var_sens.is_basic}")
print(f"At Bound: {var_sens.is_at_bound}")
```

### 5. Get Binding Constraints

```python
# Find all binding constraints (at capacity)
binding = analyzer.get_binding_constraints()

for name, sens in binding.items():
    print(f"{name}: shadow price = {sens.shadow_price:.4f}")
```

### 6. Identify Bottlenecks

```python
# Find bottlenecks (binding with high shadow prices)
bottlenecks = analyzer.identify_bottlenecks(shadow_price_threshold=0.01)

print(f"Found {len(bottlenecks)} bottlenecks")
for name in bottlenecks:
    print(f"  - {name}")
```

### 7. Get Top Sensitive Constraints

```python
# Rank constraints by shadow price magnitude
top_constraints = analyzer.get_most_sensitive_constraints(top_n=10)

for i, (name, sens) in enumerate(top_constraints, 1):
    print(f"{i}. {name}: ${sens.shadow_price:.2f}")
```

### 8. Generate Comprehensive Report

```python
# Full sensitivity report
print(analyzer.generate_report(
    include_variables=True,
    include_constraints=True,
    top_n=10
))

# Brief summary
print(analyzer.generate_summary())
```

## Business Use Cases

### 1. Resource Valuation

**Problem**: How much should we pay for additional capacity?

**Solution**: Use shadow prices as maximum willingness to pay

```python
labor_shadow_price = 2.50  # $/hour from sensitivity analysis

if supplier_quote_per_hour < labor_shadow_price:
    decision = "ACCEPT - Profitable to expand"
else:
    decision = "REJECT - Not economical"
```

### 2. Investment Prioritization

**Problem**: Which capacity expansion has highest ROI?

**Solution**: Rank resources by shadow price

```
Priority 1: Cutting Machine (shadow price = $2.50/hour)
Priority 2: Assembly Station (shadow price = $1.25/hour)
Priority 3: Material Wood (shadow price = $0.75/unit)
```

**Investment Strategy**: Focus on Priority 1 first for maximum profit impact.

### 3. Capacity Planning

**Problem**: Where are the bottlenecks?

**Solution**: Identify binding constraints

```
Bottlenecks Identified:
✓ Cutting Machine (Week 1) - BINDING
✓ Assembly Station (Week 1) - BINDING
✗ Painting Booth (Week 1) - Has slack capacity

Recommendation: Expand cutting and assembly capacity first.
```

### 4. Contract Negotiation

**Problem**: Supplier offers to increase material supply for $X/unit. Accept?

**Solution**: Compare price to shadow price

```python
material_shadow_price = 0.75  # $/unit from analysis
supplier_price = 0.60  # $/unit quoted

if supplier_price < material_shadow_price:
    expected_roi = material_shadow_price - supplier_price
    decision = f"ACCEPT - ROI = ${expected_roi:.2f}/unit"
```

### 5. Risk Management

**Problem**: How robust is our solution to parameter changes?

**Solution**: Assess number of binding constraints

```
Risk Assessment:
- Binding Constraints: 12
- Risk Level: MODERATE
- Implication: Solution is moderately sensitive to capacity changes
- Recommendation: Build buffer capacity in top 3 bottleneck resources
```

## Key Learnings

### 1. Duality Theory in Practice

- Every linear program has a dual problem
- Shadow prices are the dual variables
- Primal solution (production quantities) + Dual solution (shadow prices) = complete picture
- Understanding duality provides powerful business insights

### 2. Shadow Prices Guide Investment

- Shadow price = marginal value of relaxing constraint
- Use for ROI analysis of capacity expansions
- Prioritize investments with highest shadow prices
- Valid only within basis stability range

### 3. Bottleneck Management

- Binding constraints are bottlenecks
- Focus improvement efforts on bottlenecks first
- Non-binding constraints have excess capacity
- System performance limited by weakest link (binding constraints)

### 4. Solution Robustness

- More binding constraints → higher sensitivity
- Assess risk based on number of binding constraints
- Plan for parameter variations
- Build buffer capacity in high-sensitivity solutions

### 5. Reduced Costs for Product Mix

- Zero reduced cost → product in optimal mix
- Positive reduced cost → product at lower bound, not economical
- Helps understand why certain products not produced

## Comparison: Step 4 vs Step 6

| Aspect | Step 4 (MIP) | Step 6 (LP Relaxation) |
|--------|--------------|------------------------|
| **Problem Type** | Mixed Integer Program | Pure Linear Program |
| **Setup Variables** | Binary {0, 1} | Continuous [0, 1] with threshold |
| **Optimization Model** | Multi-period planning | Same structure, LP formulation |
| **Solution Quality** | Exact integer solution | Upper bound (for max), often similar |
| **Execution Suitability** | ✓ Exact binary decisions | Threshold interpretation |
| **Console Output** | Production plan | + Sensitivity analysis |
| **HTML Report Tabs** | 4 tabs | 7 tabs (+ sensitivity) |
| **Business Insights** | Operational (what to produce) | + Strategic (where to invest) |
| **Resource Valuation** | ❌ Not available (MIP) | ✓ Shadow prices (LP) |
| **Bottleneck Detection** | Manual inspection | ✓ Automated ranking |
| **Investment Guidance** | ❌ No marginal values | ✓ ROI estimates from shadow prices |
| **Risk Assessment** | - | ✓ Sensitivity-based |
| **Best Use Case** | Final execution schedules | Strategic planning & investment |

## Advanced Topics

### Sensitivity Ranges (Not Computed)

While LumiX provides shadow prices and reduced costs, computing **sensitivity ranges** (allowable increase/decrease before basis change) requires solver-specific APIs. These ranges define the validity region of shadow prices.

**Future Enhancement**: Integration with solver-specific sensitivity range extraction.

### Parametric Analysis

For systematic parameter variation studies, see:
- **Step 5**: Scenario Analysis (discrete scenarios)
- **Example 10**: What-If Analysis (quick tactical changes)

### Multi-Objective Sensitivity

When using goal programming (as in this step), sensitivity analysis reveals:
- Which goals are binding (fully achieved)
- Marginal value of goal relaxation
- Trade-offs between conflicting goals

## Troubleshooting

### Understanding LP Relaxation Results

**Q: Why are some setup values not exactly 0 or 1?**

A: You're using **LP relaxation**, where setup variables are continuous `[0, 1]` instead of binary `{0, 1}`. This is intentional to enable sensitivity analysis.

**Interpretation**:
- `is_produced = 0.0` → Product definitely NOT produced (no setup)
- `is_produced = 1.0` → Product definitely IS produced (setup incurred)
- `is_produced = 0.7` → Interpret as produced (>= 0.5 threshold)
- `is_produced = 0.3` → Interpret as not produced (< 0.5 threshold)

**In practice**: The optimizer usually pushes these to 0.0 or 1.0 due to cost structure, making the relaxation nearly equivalent to binary.

### Sensitivity Values Look Reasonable?

**Q: Are shadow prices from LP relaxation valid?**

A: **Yes!** Shadow prices from the LP relaxation provide valuable economic insights:
- They represent marginal values in the continuous relaxation
- They guide investment decisions (where to expand capacity)
- They identify bottlenecks accurately
- They're commonly used in practice for strategic planning

**Limitation**: Shadow prices are only valid **within the basis stability range**. Large parameter changes may change the optimal basis and invalidate shadow prices.

### Comparing Step 4 (MIP) vs Step 6 (LP)

**Q: Will Step 6 give the exact same solution as Step 4?**

A: **Objective values will be similar**, but not always identical:
- LP relaxation provides an **upper bound** on the MIP objective (for maximization)
- Setup variables may have fractional values (though often 0 or 1)
- Production quantities should be very similar
- The LP solution is **valid and practical** for sensitivity analysis purposes

**When they're identical**: If all setup variables are naturally 0 or 1 in the LP solution, the solutions are equivalent!

### Shadow Prices vs. Marginal Values

**Note**: In maximization problems:
- Positive shadow price → Increasing RHS increases profit
- For minimization, signs are reversed

### LP Relaxation Best Practices

**When to use LP relaxation (Step 6)**:
- Strategic planning and investment decisions (shadow prices guide capacity expansion)
- Sensitivity analysis and what-if scenarios
- Understanding bottlenecks and resource values
- Problems where exact binary solutions are less critical than marginal value insights

**When to use MIP (Step 4)**:
- Operational planning where exact binary decisions are required
- When setup costs must be exactly 0 or 1 (no intermediate values)
- Final production schedules for execution
- When integer feasibility is more important than sensitivity insights

**Best of both worlds**: Solve Step 4 for execution, then solve Step 6 for strategic insights!

## Next Steps

You've completed the Production Planning tutorial with sensitivity analysis! You've learned:

✅ **Step 1**: Basic linear programming
✅ **Step 2**: Database integration with SQLAlchemy ORM
✅ **Step 3**: Goal programming with customer orders
✅ **Step 4**: Large-scale multi-period planning
✅ **Step 5**: Scenario analysis (if completed)
✅ **Step 6**: Sensitivity analysis and investment insights

**Advanced Topics to Explore**:
- Stochastic optimization (uncertain demand)
- Network flow models (multi-facility)
- Non-linear costs (economies of scale)
- Rolling horizon planning (continuous replanning)
- Robust optimization (worst-case scenarios)

**Related Examples**:
- **Example 09**: Sensitivity Analysis (standalone example)
- **Example 08**: Scenario Analysis (discrete scenarios)
- **Example 10**: What-If Analysis (quick tactical decisions)

## See Also

- **Timetabling Step 4**: Large-scale with room type constraints
- **LumiX Documentation**: Sensitivity Analysis guide
- **Duality Theory**: Linear programming duality
- **SQLAlchemy Documentation**: https://docs.sqlalchemy.org/

---

**Tutorial Complete!**

You've mastered production planning optimization from basic to production-ready scale with comprehensive sensitivity analysis using LumiX and SQLAlchemy ORM. These techniques apply to real-world manufacturing, supply chain, resource allocation, and strategic investment planning problems.
