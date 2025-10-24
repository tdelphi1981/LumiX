# Production Planning Example

## Overview

This example demonstrates LumiX's **single-model indexing** feature, which allows variables and constraints to be indexed directly by data model instances rather than manual integer indices. This is one of the fundamental features that makes LumiX intuitive and type-safe.

## Problem Description

A manufacturing company produces multiple products, each requiring different amounts of limited resources (labor hours, machine hours, raw materials). The goal is to maximize total profit while:

- Respecting resource capacity constraints
- Meeting minimum production requirements for customer orders
- Ensuring non-negative production quantities

### Real-World Context

This type of problem is common in:
- Manufacturing operations planning
- Resource allocation in production facilities
- Portfolio optimization for product lines
- Supply chain optimization

## Mathematical Formulation

**Decision Variables:**
- `production[p]`: Quantity to produce of product `p`

**Objective Function:**
```
Maximize: ∑(profit_per_unit[p] × production[p]) for all products p
```

**Constraints:**
```
Resource capacity:    ∑(usage[p,r] × production[p]) ≤ capacity[r]  for all resources r
Minimum production:   production[p] ≥ min_production[p]             for all products p
Non-negativity:       production[p] ≥ 0                             for all products p
```

Where:
- `profit_per_unit[p] = selling_price[p] - unit_cost[p]`
- `usage[p,r]` = amount of resource `r` required per unit of product `p`

## Key Concepts

### 1. Single-Model Indexing

Instead of using manual integer indices, variables are indexed by actual data model instances:

```python
# Traditional approach (other libraries)
production = [model.add_var() for i in range(num_products)]
# Later: Which product is index 0? 1? 2?

# LumiX approach
production = (
    LXVariable[Product, float]("production")
    .continuous()
    .from_data(PRODUCTS)
    .indexed_by(lambda p: p.id)
)
# Solution access: solution.variables["production"][product.id]
```

### 2. Data-Driven Modeling

Coefficients are extracted directly from data using lambda functions:

```python
profit_expr = LXLinearExpression[Product]().add_term(
    production,
    coeff=lambda p: p.selling_price - p.unit_cost  # Data-driven!
)
```

### 3. Automatic Expression Expansion

Expressions automatically sum over all instances in the variable family:

```python
# No manual loops needed!
usage_expr = LXLinearExpression().add_term(
    production,
    coeff=lambda p, r=resource: get_resource_usage(p, r)
)
# Expands to: sum(usage[p,r] × production[p] for all p in PRODUCTS)
```

### 4. Constraint Families

Create multiple similar constraints indexed by data instances:

```python
model.add_constraint(
    LXConstraint[Product]("min_production")
    .expression(LXLinearExpression[Product]().add_term(production, 1.0))
    .ge()
    .rhs(lambda p: float(p.min_production))
    .from_data(PRODUCTS)  # One constraint per product
    .indexed_by(lambda p: p.name)
)
```

### 5. Type-Safe Solution Access

Solutions are accessed using the same keys as the original data:

```python
for product in PRODUCTS:
    qty = solution.variables["production"][product.id]
    # IDE knows the structure and provides autocomplete!
```

## Running the Example

### Prerequisites

Install LumiX and a solver:

```bash
pip install lumix
pip install ortools  # or cplex, gurobi
```

### Execute

```bash
cd examples/01_production_planning
python production_planning.py
```

## Expected Output

```
============================================================
OptiXNG Example: Production Planning
============================================================

This example demonstrates:
  ✓ Single-model indexing (LXVariable[Product])
  ✓ Data-driven modeling
  ✓ Multiple resource constraints
  ✓ Type-safe solution mapping

Products:
------------------------------------------------------------
  Widget A       : $50.00 - $20.00 = $30.00 profit/unit
  Widget B       : $80.00 - $35.00 = $45.00 profit/unit
  Gadget X       : $120.00 - $50.00 = $70.00 profit/unit
  ...

Resources:
------------------------------------------------------------
  Labor Hours    : 1000.0 available
  Machine Hours  : 800.0 available
  Raw Materials  : 500.0 available

Building optimization model...
Model Summary:
  Variables: 1 family (5 decision variables)
  Constraints: 8 (5 resource + 3 minimum production)
  Objective: Maximize total profit

============================================================
SOLUTION
============================================================
Status: optimal
Optimal Profit: $12,345.67

Production Plan:
------------------------------------------------------------
  Widget A       :   50.0 units  (profit: $1,500.00)
  Widget B       :  100.0 units  (profit: $4,500.00)
  Gadget X       :   85.0 units  (profit: $5,950.00)
  ...

Resource Utilization:
------------------------------------------------------------
  Labor Hours    :  950.0/1000.0 (95.0%)
  Machine Hours  :  800.0/800.0 (100.0%)
  Raw Materials  :  425.0/500.0 (85.0%)
```

## Key Learnings

### 1. Model Structure Preservation

LumiX preserves the relationship between your data models and optimization variables. You never lose track of what each variable represents.

### 2. No Index Management

No need to maintain manual mappings between products and indices. The data model IS the index.

### 3. IDE Support

Because types are preserved, your IDE can provide:
- Autocomplete for variable access
- Type checking
- Documentation tooltips

### 4. Maintainable Code

When data changes (add/remove products), the model automatically adapts without code changes.

### 5. Lambda-Based Coefficients

Lambda functions allow coefficients to be computed from data at model-building time, keeping the model declaration clean and data-driven.

## Common Patterns Demonstrated

### Pattern 1: Variable Family

```python
# ONE variable declaration expands to multiple solver variables
production = LXVariable[Product, float]("production").from_data(PRODUCTS)
```

### Pattern 2: Resource Constraints

```python
for resource in RESOURCES:
    usage_expr = LXLinearExpression().add_term(
        production,
        coeff=lambda p, r=resource: get_resource_usage(p, r)
    )
    model.add_constraint(
        LXConstraint(f"capacity_{resource.name}")
        .expression(usage_expr)
        .le()
        .rhs(resource.capacity)
    )
```

### Pattern 3: Minimum Requirements

```python
model.add_constraint(
    LXConstraint[Product]("min_production")
    .expression(LXLinearExpression[Product]().add_term(production, 1.0))
    .ge()
    .rhs(lambda p: float(p.min_production))
    .from_data(PRODUCTS)
)
```

## Extensions and Variations

This example can be extended to include:

1. **Time Periods**: Add time dimension for multi-period planning
2. **Inventory**: Track inventory levels across periods
3. **Backorders**: Allow demand to be backordered with penalties
4. **Multiple Facilities**: Expand to multiple production locations
5. **Alternative Resources**: Model resource substitution
6. **Setup Costs**: Add fixed costs for production runs
7. **Batching**: Enforce minimum batch sizes

## See Also

- **Example 02 (Driver Scheduling)**: Multi-model indexing with cartesian products
- **Example 03 (Facility Location)**: Binary variables and fixed costs
- **Example 04 (Basic LP)**: Simpler introduction to LumiX basics
- **Example 08 (Scenario Analysis)**: Testing different business scenarios
- **Example 09 (Sensitivity Analysis)**: Understanding shadow prices and bottlenecks

## Files in This Example

- `production_planning.py`: Main optimization model and solution display
- `sample_data.py`: Data models (Product, Resource) and sample data
- `README.md`: This documentation file

## Next Steps

After understanding this example:

1. Modify `sample_data.py` to add your own products and resources
2. Experiment with different objective functions (e.g., minimize cost)
3. Add new constraint types (e.g., storage limits, labor regulations)
4. Try different solvers (CPLEX, Gurobi, OR-Tools)
5. Move on to Example 02 for multi-model indexing
