# Goal Programming in LumiX

## Overview

LumiX provides built-in support for **Goal Programming**, allowing you to automatically convert Linear Programming (LP) problems into Goal Programming (GP) problems with soft constraints and multiple priority levels.

## What is Goal Programming?

Goal Programming is an optimization technique that:
- Allows **soft constraints** (goals) that can be violated with a penalty
- Supports **multiple conflicting objectives** through priority levels
- Minimizes **deviation** from target values rather than hard constraints

### Key Concepts

1. **Deviation Variables**: Each goal constraint gets two deviation variables:
   - **Positive deviation (d+)**: Amount by which the constraint exceeds its target
   - **Negative deviation (d-)**: Amount by which the constraint falls short of its target

2. **Constraint Relaxation**: A hard constraint is converted to a soft goal:
   ```
   Hard:    expr OP rhs
   Relaxed: expr + d- - d+ = rhs
   ```

3. **Objective Function**: Minimize undesired deviations based on constraint type:
   - `LE (≤)`: Minimize d+ (exceeding is bad)
   - `GE (≥)`: Minimize d- (falling short is bad)
   - `EQ (=)`: Minimize both d+ and d- (any deviation is bad)

4. **Priorities**: Goals can have different priorities (1=highest, 2=second, etc.)
   - Priority 0 is reserved for custom objective terms

## Features

✅ **Automatic LP-to-GP Conversion**: Mark constraints as goals with `.as_goal(priority, weight)`
✅ **Automatic Deviation Variables**: Created and managed automatically
✅ **Two Solving Modes**:
   - **Weighted**: Single solve with exponential priority weights
   - **Sequential**: Lexicographic (multiple solves, true preemptive)
✅ **Custom Objective Terms**: Use priority 0 for custom objectives
✅ **Indexed Goal Constraints**: Works with constraint families
✅ **Solution Analysis**: Check goal satisfaction and deviation values

## Quick Start

### Basic Example

```python
from lumix import LXModel, LXVariable, LXConstraint, LXLinearExpression, LXOptimizer

# Define variables
production = LXVariable[Product, float]("production").continuous().bounds(lower=0)

# Create model
model = LXModel("production_goals")
model.add_variable(production)

# Hard constraint (must be satisfied)
model.add_constraint(
    LXConstraint("capacity")
    .expression(LXLinearExpression().add_term(production, 1.0))
    .le()
    .rhs(100)
)

# Goal constraint (can be violated with penalty)
model.add_constraint(
    LXConstraint("production_target")
    .expression(LXLinearExpression().add_term(production, 1.0))
    .ge()
    .rhs(80)
    .as_goal(priority=1, weight=1.0)  # Soft constraint
)

# Set goal programming mode
model.set_goal_mode("weighted")  # or "sequential"

# Prepare and solve
model.prepare_goal_programming()
optimizer = LXOptimizer().use_solver("ortools")
solution = optimizer.solve(model)

# Check goal satisfaction
deviations = solution.get_goal_deviations("production_target")
satisfied = solution.is_goal_satisfied("production_target")
print(f"Goal satisfied: {satisfied}")
print(f"Negative deviation: {deviations['neg']}")  # Under-production
print(f"Positive deviation: {deviations['pos']}")  # Over-production
```

## Constraint Type Handling

### LE Constraint (≤)

```python
# Original: expr <= rhs
# Relaxed:  expr + d- - d+ = rhs
# Minimize: d+ (exceeding is undesired)

model.add_constraint(
    LXConstraint("overtime_limit")
    .expression(overtime_expr)
    .le()
    .rhs(40)
    .as_goal(priority=2, weight=1.0)
)
# If overtime = 50, then d+ = 10 (excess), d- = 0
```

### GE Constraint (≥)

```python
# Original: expr >= rhs
# Relaxed:  expr + d- - d+ = rhs
# Minimize: d- (falling short is undesired)

model.add_constraint(
    LXConstraint("demand_goal")
    .expression(production_expr)
    .ge()
    .rhs(100)
    .as_goal(priority=1, weight=1.0)
)
# If production = 90, then d- = 10 (shortfall), d+ = 0
```

### EQ Constraint (=)

```python
# Original: expr = rhs
# Relaxed:  expr + d- - d+ = rhs
# Minimize: d- AND d+ (both deviations are undesired)

model.add_constraint(
    LXConstraint("exact_target")
    .expression(inventory_expr)
    .eq()
    .rhs(50)
    .as_goal(priority=2, weight=1.0)
)
# Any deviation from 50 is penalized
```

## Priority Levels

### Weighted Mode (Single Solve)

Priorities are converted to exponentially different weights:
- Priority 1: weight = 10^6
- Priority 2: weight = 10^5
- Priority 3: weight = 10^4
- ...

This ensures higher priorities dominate lower priorities in a single objective function.

```python
# Priority 1 goals (most important)
model.add_constraint(
    LXConstraint("critical_demand")
    .expression(expr1)
    .ge()
    .rhs(100)
    .as_goal(priority=1, weight=1.0)
)

# Priority 2 goals (less important)
model.add_constraint(
    LXConstraint("preferred_inventory")
    .expression(expr2)
    .eq()
    .rhs(50)
    .as_goal(priority=2, weight=1.0)
)

# Priority 3 goals (least important)
model.add_constraint(
    LXConstraint("nice_to_have")
    .expression(expr3)
    .le()
    .rhs(20)
    .as_goal(priority=3, weight=0.5)  # Lower weight within priority
)

model.set_goal_mode("weighted")
```

### Sequential Mode (Multiple Solves)

**Note**: Sequential mode is planned but not yet fully implemented. It will solve priorities lexicographically:
1. Solve Priority 1, get optimal d1*
2. Fix d1 = d1*, solve Priority 2, get optimal d2*
3. Fix d2 = d2*, solve Priority 3, etc.

```python
model.set_goal_mode("sequential")
# This will perform true preemptive goal programming
```

## Custom Objectives (Priority 0)

Use priority 0 to incorporate custom objective terms alongside goal deviations:

```python
# Maximize profit (priority 0 = custom objective)
model.add_constraint(
    LXConstraint("profit")
    .expression(profit_expr)
    .ge()
    .rhs(0)
    .as_goal(priority=0, weight=1.0)
)

# High priority demand goal (priority 1)
model.add_constraint(
    LXConstraint("demand")
    .expression(demand_expr)
    .ge()
    .rhs(1000)
    .as_goal(priority=1, weight=1.0)
)

# Final objective: maximize profit while minimizing goal deviations
```

## Working with Indexed Goals

Goal programming works seamlessly with indexed constraint families:

```python
# Goal for EACH product
for product in PRODUCTS:
    expr = LXLinearExpression().add_term(
        production,
        coeff=lambda p, prod=product: 1.0 if p.id == prod.id else 0.0
    )

    # Different weights based on product priority
    weight = product.priority_factor

    model.add_constraint(
        LXConstraint(f"production_goal_{product.id}")
        .expression(expr)
        .ge()
        .rhs(product.target)
        .as_goal(priority=1, weight=weight)
    )
```

## Solution Analysis

### Check Goal Satisfaction

```python
# Check if goal is satisfied
satisfied = solution.is_goal_satisfied("demand_goal", tolerance=1e-6)

# Get deviation values
deviations = solution.get_goal_deviations("demand_goal")
pos_dev = deviations["pos"]  # Over-achievement
neg_dev = deviations["neg"]  # Under-achievement

# Get total deviation
total = solution.get_total_deviation("demand_goal")
```

### Indexed Goals

```python
# For indexed goals, deviations are dictionaries
for product in PRODUCTS:
    goal_name = f"production_goal_{product.id}"
    deviations = solution.get_goal_deviations(goal_name)

    # Access by index
    neg_dev = deviations["neg"]  # Dict[product_id, value]
    pos_dev = deviations["pos"]  # Dict[product_id, value]

    print(f"Product {product.name}:")
    print(f"  Shortfall: {neg_dev.get(product.id, 0):.2f}")
    print(f"  Excess: {pos_dev.get(product.id, 0):.2f}")
```

## Examples

### Example 1: Basic Goal Programming
**File**: `01_basic_goal_programming.py`

Demonstrates:
- Simple production planning with goals
- Different constraint types (LE, GE, EQ)
- Goal satisfaction analysis

### Example 2: Multi-Priority Weighted
**File**: `02_multi_priority_weighted.py`

Demonstrates:
- Multiple priority levels (P0-P3)
- Custom objective (priority 0)
- Indexed goal constraints
- Custom weights within priorities
- Comprehensive goal satisfaction reporting

## API Reference

### LXConstraint Methods

```python
.as_goal(priority: int, weight: float = 1.0) -> Self
```
Mark constraint as a goal with specified priority and weight.

```python
.is_goal() -> bool
```
Check if constraint is marked as a goal.

### LXModel Methods

```python
.set_goal_mode(mode: str) -> Self
```
Set goal programming mode ("weighted" or "sequential").

```python
.prepare_goal_programming() -> Self
```
Prepare model for goal programming (relax goals, add deviation variables, build objective). Called automatically by solver.

```python
.has_goals() -> bool
```
Check if model has any goal constraints.

### LXSolution Methods

```python
.get_goal_deviations(goal_name: str) -> Dict[str, Union[float, Dict[Any, float]]]
```
Get deviation values for a goal (returns dict with 'pos' and 'neg' keys).

```python
.is_goal_satisfied(goal_name: str, tolerance: float = 1e-6) -> bool
```
Check if goal is satisfied within tolerance.

```python
.get_total_deviation(goal_name: str) -> float
```
Get total absolute deviation for a goal.

## Implementation Details

### Automatic Relaxation

When you call `.prepare_goal_programming()`:

1. **Identify Goals**: Find all constraints marked with `.as_goal()`
2. **Create Deviation Variables**: For each goal, create `pos_dev` and `neg_dev`
3. **Relax Constraints**: Transform:
   ```
   expr OP rhs  →  expr + neg_dev - pos_dev = rhs
   ```
4. **Build Objective**: Minimize weighted sum of undesired deviations
5. **Add to Model**: Add deviation variables and replace constraints

### Deviation Variable Naming

Deviation variables are automatically named:
- Positive: `{constraint_name}_pos_dev`
- Negative: `{constraint_name}_neg_dev`

### Weight Calculation

For weighted mode:
```python
priority_weight = 10 ** (6 - priority)
combined_weight = priority_weight * goal_weight
```

Example:
- Priority 1, weight 1.0: combined = 10^6 * 1.0 = 1,000,000
- Priority 2, weight 0.5: combined = 10^5 * 0.5 = 50,000
- Priority 3, weight 2.0: combined = 10^4 * 2.0 = 20,000

## Best Practices

1. **Use Priority 1 for Critical Goals**: Reserve highest priority for must-achieve goals
2. **Assign Meaningful Weights**: Use weights to differentiate importance within a priority
3. **Start with Weighted Mode**: Simpler and faster than sequential
4. **Check Goal Satisfaction**: Always analyze which goals were achieved
5. **Combine with Hard Constraints**: Use regular constraints for absolute limits
6. **Test Different Priority Schemes**: Experiment with priority assignments

## Limitations

1. **Sequential Mode**: Not yet fully implemented (use weighted mode)
2. **Quadratic Objectives**: Goal programming currently supports linear objectives only
3. **Manual Combination**: Combining custom objectives with goals requires priority 0

## Future Enhancements

- [ ] Full sequential/lexicographic solver
- [ ] Automatic priority inference
- [ ] Goal relaxation tolerance settings
- [ ] Interactive goal adjustment
- [ ] Goal programming reports
- [ ] Sensitivity analysis for goal priorities

## Contributing

To extend goal programming functionality, see:
- `src/lumix/goal_programming/` - Core implementation
- `src/lumix/core/constraints.py` - Constraint extensions
- `src/lumix/core/model.py` - Model extensions
- `src/lumix/solution/solution.py` - Solution extensions

## References

- Charnes, A., & Cooper, W. W. (1961). Management Models and Industrial Applications of Linear Programming
- Ignizio, J. P. (1976). Goal Programming and Extensions
- Romero, C. (1991). Handbook of Critical Issues in Goal Programming
