# Step 1: Basic Production Planning

## Overview

This is the first step in the Manufacturing Production Planning tutorial. It demonstrates how to build a production planning optimization model using LumiX with **continuous variables**.

The goal is to determine optimal production quantities for multiple products to maximize profit while respecting machine capacity, material availability, and demand constraints.

## Problem Description

A furniture factory produces three types of products (chairs, tables, desks). The factory must decide how many units of each product to manufacture each week to maximize profit.

The production plan must:

1. **Maximize total profit** from all products sold
2. **Respect machine capacity** - limited hours available on cutting and assembly machines
3. **Respect material availability** - limited quantities of wood, metal, and fabric
4. **Meet minimum demand** - customer commitments require minimum production
5. **Stay within maximum demand** - market can only absorb limited quantities

### Problem Data

- **3 Products**: Chair, Table, Desk
- **2 Machines**: Cutting Machine (80 hours/week), Assembly Station (100 hours/week)
- **3 Raw Materials**: Wood (500 bf), Metal (200 lbs), Fabric (150 yards)
- **Weekly planning horizon**

### Real-World Context

This type of problem appears in:
- Manufacturing production scheduling
- Ingredient blending (food, chemicals, oil refining)
- Diet optimization (minimize cost, meet nutritional requirements)
- Portfolio allocation (maximize return, limit risk)
- Agricultural crop planning (maximize profit, respect land/water limits)

## Mathematical Formulation

### Decision Variables

```
production[p] ≥ 0  (continuous, units of product p to manufacture)
```

Where:
- `p` ∈ Products
- `production[p]` is a **continuous variable** (can be fractional, e.g., 42.5 units)
- Lower bound: `min_demand[p]` (minimum units to produce)
- Upper bound: `max_demand[p]` (maximum units the market can absorb)

**Key Difference from Timetabling**: These are **continuous** variables representing quantities, not **binary** variables representing yes/no assignments!

### Objective Function

```
Maximize: Σ (profit[p] × production[p])  for all products p
```

**Maximize total profit** by choosing the right product mix.

### Constraints

**1. Machine Capacity** - Total machine hours used ≤ available hours:

```
Σ (hours_per_unit[p, m] × production[p]) ≤ available_hours[m]
  for each machine m, summing over all products p
```

Example for Cutting Machine:
```
0.5 × production[Chair] + 1.5 × production[Table] + 2.0 × production[Desk] ≤ 80 hours
```

**2. Material Availability** - Total material used ≤ available quantity:

```
Σ (material_per_unit[p, mat] × production[p]) ≤ available_quantity[mat]
  for each material mat, summing over all products p
```

Example for Wood:
```
8 × production[Chair] + 25 × production[Table] + 35 × production[Desk] ≤ 500 board feet
```

**3. Demand Bounds** - Production within market limits:

```
min_demand[p] ≤ production[p] ≤ max_demand[p]  for each product p
```

These are enforced through variable bounds (not separate constraints).

## Key LumiX Concepts

### 1. Continuous Variables (Not Binary!)

Variables represent **quantities** that can take any value within bounds:

```python
# In timetabling (binary variables):
assignment = LXVariable[Tuple[Lecture, TimeSlot, Classroom], int]("assignment")
    .binary()  # Values: 0 or 1 only

# In production planning (continuous variables):
production = LXVariable[Product, float]("production")
    .continuous()  # Values: any number ≥ 0
```

**Key Difference**:
- Binary: "Is lecture X assigned to slot Y?" → Yes (1) or No (0)
- Continuous: "How many chairs should we produce?" → Any amount (42.5 units)

### 2. Single-Dimensional Indexing

Variables indexed by **one model** only (Product):

```python
production = LXVariable[Product, float]("production").continuous()

for product in products:
    production.add_index(
        product,
        lower_bound=product.min_demand,  # Must produce at least this much
        upper_bound=product.max_demand   # Market limit
    )
```

**Comparison with Timetabling**:
- Timetabling: 3D indexing (Lecture × TimeSlot × Classroom)
- Production: 1D indexing (Product only)

### 3. Variable Bounds

Set lower and upper limits directly on variables:

```python
production.add_index(
    product,
    lower_bound=10.0,   # Minimum production (customer commitment)
    upper_bound=100.0   # Maximum production (market capacity)
)
```

This replaces explicit constraints like:
```python
# Not needed - bounds handle this automatically:
# production[p] ≥ 10
# production[p] ≤ 100
```

### 4. Profit Maximization Objective

Build a linear expression and maximize:

```python
profit_expr = LXLinearExpression()
for product in products:
    profit_expr.add_term(
        production,
        index=product,
        coeff=product.profit_per_unit  # $45 for chairs, $120 for tables, etc.
    )

model.set_objective(profit_expr, sense="max")  # Maximize!
```

### 5. Resource Aggregation Constraints

Sum resource consumption across products:

```python
# Machine capacity constraint
machine_hours_expr = LXLinearExpression()
for product in products:
    hours_required = get_machine_hours_required(product.id, machine.id)
    if hours_required > 0:
        machine_hours_expr.add_term(
            production,
            index=product,
            coeff=hours_required  # Hours per unit
        )

model.add_constraint(
    LXConstraint("machine_capacity_cutting")
    .expression(machine_hours_expr)
    .le()
    .rhs(machine.available_hours)  # Total hours available
)
```

## Running the Example

### Prerequisites

Install LumiX and OR-Tools:

```bash
pip install lumix
pip install ortools
```

### Execute

```bash
cd tutorials/production_planning/step1_basic_production
python production.py
```

## Expected Output

The program will display:

1. **Model Building Information**:
   - Number of variables created (3 continuous variables)
   - Number of constraints added (11 total: 2 machines + 3 materials + 6 demand bounds)

2. **Solution Status**:
   - Optimal solution found
   - Total profit achieved

3. **Production Plan**:
   - Exact quantities to produce for each product
   - Profit per unit and total profit per product

4. **Machine Utilization**:
   - Hours used vs. available for each machine
   - Utilization percentage

5. **Material Consumption**:
   - Quantity used vs. available for each material
   - Remaining inventory

6. **Demand Analysis**:
   - Whether production is at minimum, maximum, or within range

### Example Output

```
================================================================================
LumiX Tutorial: Manufacturing Production Planning - Step 1
================================================================================

This example demonstrates:
  ✓ Continuous variables (production quantities)
  ✓ Resource consumption constraints
  ✓ Profit maximization objective
  ✓ Single-dimensional indexing (by Product)

Building production planning model...

Creating decision variables...
  Created 3 continuous variables (one per product)

Defining objective function (maximize profit)...
  Objective: Maximize Σ (profit × production)
  Profit coefficients: ['$45.0', '$120.0', '$200.0']

Adding machine capacity constraints...
  Added 2 machine capacity constraints

Adding material availability constraints...
  Added 3 material availability constraints

Model built successfully!
  Variables: 3 continuous
  Constraints: 11 total
    - Machine capacity: 2
    - Material availability: 3
    - Demand bounds: 6

Solving...

================================================================================
PRODUCTION PLAN
================================================================================
Status: optimal
Total Profit: $2,735.71

PRODUCTION QUANTITIES:
--------------------------------------------------------------------------------
Product              Quantity        Profit/Unit     Total Profit
--------------------------------------------------------------------------------
Chair                10.00           $45.00          $450.00
Table                5.00            $120.00         $600.00
Desk                 8.43            $200.00         $1,685.71
--------------------------------------------------------------------------------
TOTAL                                                $2,735.71

MACHINE UTILIZATION:
--------------------------------------------------------------------------------
Machine                   Hours Used      Available       Utilization
--------------------------------------------------------------------------------
Cutting Machine           29.36           80.00           36.7%
Assembly Station          52.00           100.00          52.0%

MATERIAL CONSUMPTION:
--------------------------------------------------------------------------------
Material                       Used            Available       Remaining
--------------------------------------------------------------------------------
Wood (board feet)              500.00          500.00          0.00
Metal (pounds)                 112.43          200.00          87.57
Fabric (yards)                 20.00           150.00          130.00

DEMAND ANALYSIS:
--------------------------------------------------------------------------------
Product              Produced        Min Demand      Max Demand      Status
--------------------------------------------------------------------------------
Chair                10.00           10.00           100.00          At Minimum
Table                5.00            5.00            50.00           At Minimum
Desk                 8.43            3.00            30.00           Within Range

================================================================================
Tutorial Step 1 Complete!
================================================================================

Key Learnings:
  → Continuous variables represent quantities (not binary assignments)
  → Resource constraints aggregate consumption across products
  → Profit maximization drives optimal production mix
  → Solution shows exact production quantities (e.g., 18.75 units)

Next Steps:
  → Step 2: Add SQLite database for persistent storage
  → Step 3: Add customer orders with goal programming
  → Step 4: Multi-period planning with setup costs
```

## Files in This Example

- **`sample_data.py`**: Data models (Product, Machine, RawMaterial, etc.) and sample data
- **`production.py`**: Main optimization model, solver, and solution display
- **`README.md`**: This documentation file

## Key Learnings

### 1. Continuous vs. Binary Variables

The fundamental difference between production planning and timetabling:

| Aspect | Timetabling (Binary) | Production (Continuous) |
|--------|---------------------|------------------------|
| **Question** | "Should we assign this?" | "How much should we make?" |
| **Variable Type** | Binary (0 or 1) | Continuous (≥ 0) |
| **Example Value** | assignment = 1 | production = 42.5 |
| **Use Case** | Scheduling, routing | Quantities, blending, allocation |

### 2. Profit Maximization vs. Feasibility

- **Timetabling**: Find any valid schedule (feasibility problem)
- **Production Planning**: Find the **best** production mix (optimization problem)

The objective function drives the solution toward higher profit, not just any feasible plan.

### 3. Resource Constraints

Production planning features **aggregation constraints**:
- Sum resource usage across all products
- Compare total to available capacity
- Each product contributes proportionally to its production quantity

### 4. Fractional Solutions

Continuous variables can produce fractional results:
- `production[Desk] = 18.75 units` means "produce 18.75 desks"
- In practice, this might mean:
  - 18 complete desks + partial assembly of one more
  - Average production over multiple weeks
  - Round to 19 desks (slight rounding adjustment)

### 5. Binding Constraints

Notice in the output:
- **Cutting Machine**: 36.7% utilized (non-binding)
- **Assembly Station**: 52.0% utilized (non-binding)
- **Wood**: Fully consumed (binding constraint - limits production)
- **Metal**: 87.57 lbs remaining (non-binding)
- **Fabric**: 130 yards remaining (non-binding)
- **Min Demand for Chair**: At minimum (binding constraint)
- **Min Demand for Table**: At minimum (binding constraint)

**Binding constraints** limit profit. To increase profit, we'd need more wood or be able to reduce minimum demand requirements for chairs and tables. Additional machine capacity or metal wouldn't help since these resources are not fully utilized.

## Common Patterns Demonstrated

### Pattern 1: Continuous Variable with Bounds

```python
var = LXVariable[ModelType, float]("var_name").continuous()
for item in items:
    var.add_index(item, lower_bound=min_val, upper_bound=max_val)
```

### Pattern 2: Profit/Cost Objective

```python
expr = LXLinearExpression()
for item in items:
    expr.add_term(var, index=item, coeff=profit_or_cost[item])
model.set_objective(expr, sense="max")  # or "min"
```

### Pattern 3: Resource Aggregation Constraint

```python
resource_expr = LXLinearExpression()
for item in items:
    resource_expr.add_term(var, index=item, coeff=resource_per_unit[item])
model.add_constraint(
    LXConstraint("resource_limit")
    .expression(resource_expr)
    .le()
    .rhs(total_available)
)
```

## Extensions and Variations

This basic production model can be extended with:

1. **Product Families**: Group products and add family-level constraints
2. **Multi-Period Planning**: Extend to multiple weeks with inventory (Step 4)
3. **Setup Costs**: Add binary variables for setup decisions (Step 4)
4. **Overtime**: Allow machine overtime at higher cost
5. **Material Substitution**: Allow alternative materials for products
6. **Quality Constraints**: Minimum quality levels for product mix
7. **Customer Orders**: Soft constraints for specific order quantities (Step 3)

## Next Steps

After completing Step 1, proceed to:

- **Step 2**: Add SQLite database integration for persistent data storage
- **Step 3**: Add customer orders with goal programming and priorities

## See Also

- **Timetabling Step 1**: Comparison with binary variable problems
- **LumiX Documentation**: Continuous variables guide
- **Linear Programming**: General LP theory and applications

## Troubleshooting

### Infeasible Solution

If the model returns infeasible:

1. **Check demand bounds**: Are minimum demands achievable with available resources?
2. **Check machine capacity**: Is there enough machine time for minimum production?
3. **Check material availability**: Are there enough materials for minimum production?
4. **Reduce minimum demands**: Lower `min_demand` values in sample_data.py

Example: If chairs require 10 minimum but use all the fabric, and tables also need fabric, the problem becomes infeasible.

### Unbounded Solution

If the solver reports unbounded:

1. **Check variable bounds**: Ensure `max_demand` is set (not infinity)
2. **Check constraints**: Make sure resource limits are present
3. **Check objective**: Verify profit coefficients are reasonable

### Unexpected Production Mix

If the solution seems wrong:

1. **Verify profit margins**: Higher profit products should dominate (if resources allow)
2. **Check resource consumption**: Products using less resources per profit are favored
3. **Review demand bounds**: Binding minimum demands force suboptimal production
4. **Calculate "profit per bottleneck resource"**: Most profitable product per scarce resource

Example:
- Desk: $200 profit / 3.5 assembly hours = $57.14 per hour
- Table: $120 profit / 2.5 assembly hours = $48.00 per hour
- Chair: $45 profit / 1.0 assembly hours = $45.00 per hour

→ Desks are most profitable per assembly hour, so produce as many as possible!

---

**Tutorial Step 1 Complete!**

You've learned how to build a basic production planning model with continuous variables. Now move on to Step 2 to add database integration for persistent storage.
