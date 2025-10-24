# Sensitivity Analysis Example

## Overview

This example demonstrates LumiX's **sensitivity analysis** capabilities for understanding optimal solutions through shadow prices, reduced costs, and bottleneck identification.

## Problem: Understanding Solution Sensitivity

After solving a production planning optimization problem, a manufacturing company wants to understand:

- **Shadow Prices**: What is the marginal value of each resource?
- **Reduced Costs**: What is the opportunity cost of each variable?
- **Bottlenecks**: Which constraints are limiting profitability?
- **Investment Priorities**: Where should we invest to maximize ROI?

## Key Features Demonstrated

### 1. Shadow Price Analysis

```python
analyzer = LXSensitivityAnalyzer(model, solution)

# Analyze constraint sensitivity
sens = analyzer.analyze_constraint("capacity_Labor Hours")
print(f"Shadow Price: ${sens.shadow_price:.2f}")
print(f"Binding: {sens.is_binding}")
```

**Shadow Price Interpretation**:
- Shadow price = marginal value of relaxing constraint by 1 unit
- Positive shadow price → constraint is binding (at capacity)
- Zero shadow price → constraint has slack (not binding)

### 2. Reduced Cost Analysis

```python
# Analyze variable sensitivity
var_sens = analyzer.analyze_variable("production")
print(f"Reduced Cost: ${var_sens.reduced_cost:.6f}")
print(f"In Basis: {var_sens.is_basic}")
```

**Reduced Cost Interpretation**:
- Reduced cost = opportunity cost of forcing variable to increase
- Zero reduced cost → variable is in optimal basis
- Non-zero → variable at bound, not economical to change

### 3. Bottleneck Identification

```python
# Find binding constraints
bottlenecks = analyzer.identify_bottlenecks()
for name in bottlenecks:
    print(f"Bottleneck: {name}")

# Get most sensitive constraints
top_constraints = analyzer.get_most_sensitive_constraints(top_n=5)
```

### 4. Comprehensive Reports

```python
# Generate full sensitivity report
print(analyzer.generate_report())

# Generate brief summary
print(analyzer.generate_summary())
```

## Running the Example

### Prerequisites

```bash
pip install lumix
pip install ortools  # or cplex, gurobi
```

### Execute

```bash
cd examples/09_sensitivity_analysis
python sensitivity_analysis.py
```

## Expected Output

```
SENSITIVITY ANALYSIS: Production Planning Solution Insights
====================================================================

OPTIMAL SOLUTION SUMMARY
--------------------------------------------------------------------
Status: optimal
Objective: 12345.678900
Solve time: 0.123s
Non-zero variables: 5/5

CONSTRAINT SENSITIVITY ANALYSIS
====================================================================
Constraint                     Shadow Price         Status
--------------------------------------------------------------------------------
capacity_Labor Hours                  2.5000    Binding
capacity_Machine Hours                1.2500    Binding
capacity_Raw Materials                0.0000    Non-binding

BOTTLENECK IDENTIFICATION
--------------------------------------------------------------------
Identified 2 bottlenecks:

  capacity_Labor Hours:
    Shadow Price: $2.5000
    Impact: Relaxing by 1 unit → +$2.50 profit

  capacity_Machine Hours:
    Shadow Price: $1.2500
    Impact: Relaxing by 1 unit → +$1.25 profit

TOP 5 MOST VALUABLE CONSTRAINTS TO RELAX
--------------------------------------------------------------------
  1. capacity_Labor Hours
     Shadow Price: $2.5000
     Expected ROI: $2.50 per unit relaxation

  2. capacity_Machine Hours
     Shadow Price: $1.2500
     Expected ROI: $1.25 per unit relaxation
```

## Sensitivity Metrics Explained

### Shadow Prices (Dual Values)

**Definition**: The marginal value of relaxing a constraint by one unit

**Example**: If labor capacity has shadow price = $2.50
- Increasing labor by 1 hour → Profit increases by $2.50
- Decreasing labor by 1 hour → Profit decreases by $2.50

**Business Decisions**:
- If hiring cost < shadow price → Hire more workers
- Shadow price = maximum you should pay for 1 more unit
- Prioritize resources with highest shadow prices

### Reduced Costs

**Definition**: The opportunity cost of forcing a variable to change

**Example**: If production variable has reduced cost = $0.50
- Forcing production up by 1 unit → Profit decreases by $0.50
- Variable is at its bound (lower or upper)
- Not economical to change this variable

**Business Decisions**:
- Zero reduced cost → Variable is in optimal solution
- Positive reduced cost → Don't increase this variable
- Focus on variables with zero reduced cost

### Binding Constraints

**Definition**: Constraints that are "tight" at the optimal solution

**Characteristics**:
- Constraint is satisfied with equality (no slack)
- Has non-zero shadow price
- Limiting the objective value

**Business Implications**:
- These are your bottlenecks
- Relaxing these constraints improves profit
- Tightening these constraints hurts profit

## Business Insights Generated

The example provides actionable insights:

### 1. Resource Investment Priorities
```
Based on shadow prices, prioritize investment in:
  1. Labor Hours
     Marginal Value: $2.50 per unit
     Status: BINDING (at capacity)
     ✓ HIGH PRIORITY: Strong ROI expected from capacity expansion
```

### 2. Bottleneck Mitigation
```
Identified 2 critical bottlenecks:
  • Labor Hours
    Current Status: Operating at capacity
    Cost of Constraint: $2.50 per unit shortage
    Recommendation: Expand capacity or optimize usage
```

### 3. Strategic Recommendations
```
► HIRING RECOMMENDATION:
  - Labor capacity is constraining profit
  - Each additional labor hour adds $2.50 profit
  - Consider hiring if cost per hour < $2.50
```

### 4. Risk Assessment
```
⚠ HIGH SENSITIVITY:
  - 2 constraints are binding
  - Solution is highly sensitive to parameter changes
  - Small variations in capacity can significantly impact profit
  - Recommendation: Build buffer capacity or diversify resources
```

## Key Learnings

### 1. Duality Theory in Practice
- Every linear program has a dual problem
- Shadow prices are the dual variables
- Understanding duality provides powerful insights

### 2. Investment Decision Support
- Shadow prices reveal marginal value of resources
- Use for ROI analysis of capacity expansions
- Prioritize investments with highest shadow prices

### 3. Bottleneck Management
- Binding constraints are bottlenecks
- Focus improvement efforts on bottlenecks
- Non-binding constraints have excess capacity

### 4. Robust Decision Making
- Understand sensitivity to parameter changes
- Identify risks from binding constraints
- Plan for parameter variations

## Use Cases

1. **Resource Valuation**: Determine marginal value of each resource
2. **Investment Analysis**: Evaluate ROI of capacity expansions
3. **Procurement**: Set maximum prices for additional resources
4. **Capacity Planning**: Identify and prioritize bottlenecks
5. **Risk Management**: Assess solution robustness
6. **Negotiation**: Understand value of constraint relaxations

## Mathematical Foundation

### Shadow Prices (Lagrange Multipliers)

For constraint `∑ aᵢxᵢ ≤ b`, the shadow price λ satisfies:

```
∂f*/∂b = λ
```

Where f* is the optimal objective value.

### Complementary Slackness

At optimality:
- If constraint has slack → shadow price = 0
- If shadow price > 0 → constraint is binding

## Advanced Features

The example also demonstrates:

- **Constraint Analysis**: Individual constraint sensitivity
- **Variable Analysis**: Individual variable sensitivity
- **Ranking**: Top N most sensitive parameters
- **Filtering**: Binding vs non-binding constraints
- **Reporting**: Comprehensive and summary reports

## See Also

- **Example 08 (Scenario Analysis)**: Testing different business scenarios
- **Example 10 (What-If Analysis)**: Quick tactical decision support
- **Example 01 (Production Planning)**: Base model for sensitivity analysis
- **Goal Programming (Example 11)**: Multi-objective optimization and trade-offs

## Files in This Example

- `sensitivity_analysis.py`: Main sensitivity analysis demonstration
- `sample_data.py`: Data models (Product, Resource) and sample data
- `README.md`: This documentation file

## Next Steps

1. Analyze your own optimization models for sensitivity
2. Use shadow prices for pricing decisions (e.g., resource procurement)
3. Identify and address bottlenecks in your operations
4. Build dashboards showing sensitivity metrics
5. Integrate sensitivity analysis into decision support systems
6. Compare sensitivity across different scenarios
