# What-If Analysis Example

## Overview

This example demonstrates LumiX's **what-if analysis** capabilities for quick, interactive exploration of parameter changes and their impact on optimal solutions.

## Problem: Interactive Decision Support

A manufacturing company needs quick answers to tactical questions:

- **What if** we get 200 more labor hours?
- **What if** machine capacity is reduced by 100 hours?
- **What if** we relax minimum production requirements?
- **Which resources** are most valuable to expand?
- **What is the ROI** of different capacity investments?

## Key Features Demonstrated

### 1. Constraint Modification

```python
whatif = LXWhatIfAnalyzer(model, optimizer)

# Increase capacity
result = whatif.increase_constraint_rhs("capacity_Labor Hours", by=200)
print(f"Impact: ${result.delta_objective:,.2f}")

# Decrease capacity
result = whatif.decrease_constraint_rhs("capacity_Machine Hours", by=100)

# Set to specific value
result = whatif.increase_constraint_rhs("capacity_Labor Hours", to=1500)
```

### 2. Relaxing and Tightening Constraints

```python
# Relax constraint (make less restrictive)
result = whatif.relax_constraint("min_production", by_percent=0.5)

# Tighten constraint (make more restrictive)
result = whatif.tighten_constraint("capacity_Raw Materials", by_percent=0.2)
```

### 3. Bottleneck Discovery

```python
# Test small changes to find bottlenecks
bottlenecks = whatif.find_bottlenecks(test_amount=10.0, top_n=5)

for name, improvement_per_unit in bottlenecks:
    print(f"{name}: ${improvement_per_unit:.2f} per unit")
```

### 4. Sensitivity Range Analysis

```python
# Analyze objective across range of values
sensitivity = whatif.sensitivity_range(
    "capacity_Labor Hours",
    min_value=700,
    max_value=1300,
    num_points=13
)

for labor, profit in sensitivity:
    print(f"Labor: {labor} → Profit: ${profit:,.2f}")
```

### 5. Comparing Multiple Changes

```python
# Compare different investment options
changes = [
    ("capacity_Labor Hours", "increase", 100),
    ("capacity_Labor Hours", "increase", 200),
    ("capacity_Machine Hours", "increase", 100),
]

results = whatif.compare_changes(changes)
```

## Running the Example

```bash
cd examples/10_whatif_analysis
python whatif_analysis.py
```

## Expected Output

```
WHAT-IF ANALYSIS: Quick Impact Assessment
====================================================================

Solving baseline model...
Baseline Profit: $12,345.67

--------------------------------------------------------------------------------
WHAT-IF #1: Increase Labor Hours by 200
--------------------------------------------------------------------------------

Original Profit:  $12,345.67
New Profit:       $12,845.67
Change:           $500.00 (+4.05%)

Interpretation: Adding 200 labor hours would increase profit by $500.00
Marginal value:  $2.50 per labor hour

--------------------------------------------------------------------------------
WHAT-IF #2: Decrease Machine Hours by 100 (Equipment Failure)
--------------------------------------------------------------------------------

Original Profit:  $12,345.67
New Profit:       $12,220.67
Change:           -$125.00 (-1.01%)

⚠ Risk Assessment: Machine failure would cost $125.00 in lost profit

BOTTLENECK IDENTIFICATION
====================================================================

Resource                       Improvement          Per Unit       Priority
--------------------------------------------------------------------------------
Labor Hours                    $25.00               $2.50          HIGH
Machine Hours                  $12.50               $1.25          MEDIUM
Raw Materials                  $0.00                $0.00          LOW
```

## Analysis Types

### 1. Basic What-If Questions

Quick assessment of simple changes:

```python
# Add 200 labor hours
result = whatif.increase_constraint_rhs("capacity_Labor Hours", by=200)

# Reduce machine capacity by 15%
result = whatif.decrease_constraint_rhs("capacity_Machine Hours", by_percent=0.15)
```

**Use Cases**:
- Quick operational decisions
- Emergency response planning
- Resource reallocation

### 2. Bottleneck Identification

Systematically test all constraints to find bottlenecks:

```python
bottlenecks = whatif.find_bottlenecks(test_amount=10.0, top_n=5)
```

**Use Cases**:
- Capacity planning
- Investment prioritization
- Process improvement

### 3. Sensitivity Ranges

Analyze how objective varies across parameter range:

```python
sensitivity = whatif.sensitivity_range(
    "capacity_Labor Hours",
    min_value=800,
    max_value=1200,
    num_points=10
)
```

**Use Cases**:
- Understanding parameter impact curves
- Identifying diminishing returns
- Optimal capacity sizing

### 4. Investment Comparison

Compare ROI of different capacity investments:

```python
results = whatif.compare_changes([
    ("capacity_Labor Hours", "increase", 100),
    ("capacity_Labor Hours", "increase", 200),
    ("capacity_Machine Hours", "increase", 100),
])
```

**Use Cases**:
- Capital budgeting
- Resource allocation
- Strategic planning

## What-If Result Structure

Each what-if analysis returns a `LXWhatIfResult` with:

```python
result.description           # Description of change
result.original_objective    # Baseline objective value
result.new_objective         # New objective value
result.delta_objective       # Change in objective
result.delta_percentage      # Percentage change
result.original_solution     # Baseline solution
result.new_solution         # New solution
result.changes_applied      # List of modifications
```

## Business Decision Examples

### Example 1: Hiring Decision

```python
result = whatif.increase_constraint_rhs("capacity_Labor Hours", by=100)

# Decision logic
hourly_cost = 25.0  # $ per hour
total_cost = hourly_cost * 100
roi = result.delta_objective - total_cost

if roi > 0:
    print(f"✓ HIRE: ROI = ${roi:.2f}")
else:
    print(f"✗ DON'T HIRE: Loss = ${abs(roi):.2f}")
```

### Example 2: Equipment Investment

```python
result = whatif.increase_constraint_rhs("capacity_Machine Hours", by=200)

# Equipment cost
equipment_cost = 10000.0
annual_profit_increase = result.delta_objective * 52  # weeks per year
payback_years = equipment_cost / annual_profit_increase

print(f"Payback period: {payback_years:.1f} years")
```

### Example 3: Risk Assessment

```python
# Supply chain disruption scenario
result = whatif.decrease_constraint_rhs("capacity_Raw Materials", by_percent=0.3)

expected_loss = abs(result.delta_objective)
print(f"⚠ 30% material shortage would cost ${expected_loss:,.2f}")
```

## Key Insights from Example

### Bottleneck Priorities

The example identifies:

1. **Labor Hours**: $2.50 per unit marginal value
   - **Action**: Prioritize labor expansion
   - **ROI**: High return on hiring

2. **Machine Hours**: $1.25 per unit marginal value
   - **Action**: Consider equipment investment
   - **ROI**: Moderate return

3. **Raw Materials**: $0.00 per unit marginal value
   - **Action**: No need to expand
   - **Status**: Excess capacity

### Sensitivity Curves

Labor capacity sensitivity shows:
- Linear increase up to 1200 hours
- Diminishing returns above 1200
- Optimal capacity around 1200-1300 hours

### Investment Comparison

Comparing $10,000 investments:
- **Labor (400 hours @ $25/hr)**: +$1,000 profit
- **Machines (100 hours @ $100/hr)**: +$125 profit
- **Recommendation**: Invest in labor

## Advantages of What-If Analysis

### 1. Speed
- Quick assessment without full scenario setup
- Immediate feedback on changes
- Interactive exploration

### 2. Simplicity
- Simple API for common changes
- No need to understand model structure
- Intuitive constraint manipulation

### 3. Flexibility
- Test any parameter change
- Compare multiple options
- Customize to specific needs

### 4. Decision Support
- Clear ROI calculations
- Risk quantification
- Investment prioritization

## When to Use What-If vs Scenario Analysis

### Use **What-If Analysis** when:
- Need quick tactical decisions
- Testing single parameter changes
- Exploring sensitivity ranges
- Finding bottlenecks
- Time-sensitive decisions

### Use **Scenario Analysis** when:
- Complex multi-parameter changes
- Strategic planning
- Comparing business scenarios
- Formal reporting required
- Need reproducible scenarios

## Key Learnings

1. **Marginal Analysis**: What-if shows marginal value of changes
2. **Bottleneck Discovery**: Systematic testing reveals constraints
3. **ROI Assessment**: Compare profit impact to investment cost
4. **Risk Quantification**: Measure downside of adverse changes
5. **Trade-offs**: Understand opportunity costs

## Use Cases

1. **Tactical Decisions**: Quick operational adjustments
2. **Resource Allocation**: Prioritize resource investments
3. **Risk Management**: Assess impact of disruptions
4. **Capacity Planning**: Determine optimal capacities
5. **Negotiation**: Understand value of constraint relaxations
6. **Emergency Response**: Evaluate mitigation options
7. **Investment Analysis**: Compare ROI of different options

## Advanced Features

### Automatic Direction Detection

```python
# Relax automatically determines direction based on constraint type
result = whatif.relax_constraint("capacity")  # increases RHS for LE
result = whatif.relax_constraint("minimum")   # decreases RHS for GE
```

### Percentage Changes

```python
# Use percentage for relative changes
result = whatif.increase_constraint_rhs("capacity", by_percent=0.2)  # +20%
```

### Baseline Caching

```python
# Baseline solution is cached for efficiency
whatif.get_baseline_solution()  # Computed once
whatif.get_baseline_solution()  # Retrieved from cache
```

## See Also

- **Scenario Analysis**: `examples/08_scenario_analysis/`
- **Sensitivity Analysis**: `examples/09_sensitivity_analysis/`
- **Production Planning**: `examples/01_production_planning/`
