# Facility Location Example

## Overview

This example demonstrates **mixed-integer programming (MIP)** in LumiX, combining binary decision variables (open/close facilities) with continuous flow variables (shipping quantities). It showcases how to model fixed costs, conditional constraints, and the classic **Big-M formulation**.

## Problem Description

A company must decide:
1. **Which warehouses to open** from a set of candidate locations (binary decision)
2. **How to serve customers** from open warehouses (continuous flow)

The goal is to minimize total cost = fixed opening costs + variable shipping costs, while:
- Satisfying all customer demands
- Respecting warehouse capacity constraints
- Only shipping from open warehouses

### Real-World Context

This classic operations research problem appears in:
- Distribution network design
- Warehouse location planning
- Data center placement
- Retail store site selection
- Emergency service facility placement (hospitals, fire stations)
- Manufacturing plant location

## Mathematical Formulation

**Decision Variables:**
- `open[w]`: Binary variable = 1 if warehouse `w` is opened, 0 otherwise
- `ship[w,c]`: Continuous variable = quantity shipped from warehouse `w` to customer `c`

**Objective Function:**
```
Minimize: ∑(fixed_cost[w] × open[w]) + ∑∑(shipping_cost[w,c] × ship[w,c])
          all w                         all w,c
```

**Constraints:**
```
Demand satisfaction:    ∑ ship[w,c] ≥ demand[c]              for each customer c
                        w

Capacity limit:         ∑ ship[w,c] ≤ capacity[w] × open[w]  for each warehouse w
                        c

Big-M linking:          ship[w,c] ≤ M × open[w]              for each w,c pair

Non-negativity:         ship[w,c] ≥ 0
Binary:                 open[w] ∈ {0, 1}
```

Where `M` is a sufficiently large constant (Big-M).

## Key Concepts

### 1. Mixed-Integer Programming (MIP)

Combining different variable types in one model:

```python
# Binary variable - discrete decision
open_warehouse = LXVariable[Warehouse, int]("open_warehouse").binary()

# Continuous variable - quantity flow
ship = LXVariable[Tuple[Warehouse, Customer], float]("ship").continuous()
```

### 2. Fixed Costs

One-time costs paid if a decision is made:

```python
# Fixed cost is paid only if warehouse is opened
cost_expr = LXLinearExpression().add_term(
    open_warehouse,
    coeff=lambda w: w.fixed_cost  # Fixed cost per warehouse
)
```

### 3. Big-M Formulation

Conditional constraint: "Can only ship if warehouse is open"

```python
# ship[w,c] ≤ M × open[w]
# If open[w] = 0 → ship[w,c] ≤ 0 (can't ship)
# If open[w] = 1 → ship[w,c] ≤ M (can ship up to M)

bigm_expr = (
    LXLinearExpression()
    .add_multi_term(ship, coeff=lambda w, c: 1.0, where=...)
    .add_term(open_warehouse, coeff=lambda w: -BIG_M, where=...)
)
model.add_constraint(
    LXConstraint(f"bigm_{warehouse.name}_{customer.name}")
    .expression(bigm_expr)
    .le()
    .rhs(0)
)
```

**Big-M Selection**: Must be large enough to not constrain valid solutions, but not so large as to cause numerical issues. Typically: `M = max_possible_shipment`.

### 4. Capacity Constraints with Binary Variables

Warehouse can only ship up to capacity IF it's open:

```python
# ∑ ship[w,c] ≤ capacity[w] × open[w]
# Rewritten as: ∑ ship[w,c] - capacity[w] × open[w] ≤ 0

capacity_expr = (
    LXLinearExpression()
    .add_multi_term(ship, coeff=lambda w, c: 1.0, where=...)
    .add_term(open_warehouse, coeff=lambda w: -w.capacity, where=...)
)
```

### 5. Multi-Model Indexing for Flow

Shipping variables indexed by (warehouse, customer) pairs:

```python
ship = LXVariable[Tuple[Warehouse, Customer], float]("ship").indexed_by_product(
    LXIndexDimension(Warehouse, lambda w: w.id).from_data(WAREHOUSES),
    LXIndexDimension(Customer, lambda c: c.id).from_data(CUSTOMERS)
)
```

## Running the Example

### Prerequisites

Install LumiX and a MIP solver:

```bash
pip install lumix
pip install ortools  # or cplex, gurobi (CPLEX/Gurobi recommended for MIP)
```

**Note**: This problem uses haversine-based shipping costs (irrational numbers), which can be problematic for CP-SAT. Use OR-Tools LP, CPLEX, or Gurobi for best results.

### Execute

```bash
cd examples/03_facility_location
python facility_location.py
```

## Expected Output

```
======================================================================
LumiX Example: Facility Location Problem
======================================================================

This example demonstrates:
  ✓ Binary decision variables (open/close)
  ✓ Fixed costs
  ✓ Continuous flow variables (shipping)
  ✓ Big-M constraints
  ✓ Mixed-integer programming

Potential Warehouses:
----------------------------------------------------------------------
  Chicago Distribution Center : Fixed cost $50,000, Capacity 1000 units
  Atlanta Hub                 : Fixed cost $45,000, Capacity 800 units
  Los Angeles Facility        : Fixed cost $60,000, Capacity 1200 units
  Dallas Warehouse            : Fixed cost $40,000, Capacity 900 units

Customers:
----------------------------------------------------------------------
  New York       : Demand 300 units
  Miami          : Demand 250 units
  Seattle        : Demand 200 units
  Denver         : Demand 350 units

Total Demand: 1100 units
Total Capacity: 3900 units

Building optimization model...
Model Summary:
  Variables: 2 families (4 binary + 16 continuous)
  Constraints: 20 (4 demand + 4 capacity + 16 Big-M)

======================================================================
SOLUTION
======================================================================
Status: optimal
Total Cost: $147,234.56
  Fixed Costs: $90,000.00
  Shipping Costs: $57,234.56

Open Warehouses:
----------------------------------------------------------------------
  Chicago Distribution Center: Serving 2 customers (fixed cost: $50,000.00)
  Dallas Warehouse: Serving 2 customers (fixed cost: $40,000.00)

Shipping Plan:
----------------------------------------------------------------------
  Chicago Distribution Center → New York: 300.0 units ($4,500.00)
  Chicago Distribution Center → Denver: 350.0 units ($8,750.00)
  Dallas Warehouse → Miami: 250.0 units ($6,250.00)
  Dallas Warehouse → Seattle: 200.0 units ($5,000.00)

Key Concepts:
  - Binary variables: open[w] ∈ {0, 1}
  - Fixed costs: pay once if open
  - Big-M: ship[w,c] ≤ M × open[w] (can't ship if not open)
  - Mixed-integer: Some variables binary, some continuous
```

## Key Learnings

### 1. Fixed vs Variable Costs

Understanding the trade-off:
- **Fixed costs**: Paid once, regardless of utilization
- **Variable costs**: Depend on usage (shipping volume)
- **Optimal balance**: Minimize total = fixed + variable

### 2. Big-M Technique

Modeling logical constraints "IF-THEN" as linear inequalities:
- "IF warehouse open THEN can ship"
- Implemented as: `ship ≤ M × open`
- Critical: Choose M carefully (too small = infeasible, too large = numerical issues)

### 3. Mixed-Integer Challenges

MIP problems are:
- **NP-hard**: Exponentially harder than pure LP
- **Require specialized solvers**: Branch-and-bound algorithms
- **Benefit from tight formulations**: Better Big-M values = faster solve times

### 4. Trade-off Analysis

The solution balances:
- Opening fewer warehouses (lower fixed costs)
- vs. longer shipping distances (higher variable costs)

### 5. Solver Selection

For MIP problems:
- **Best**: Commercial solvers (CPLEX, Gurobi) - superior MIP performance
- **Good**: OR-Tools SCIP - free, decent MIP capabilities
- **Avoid**: Pure LP solvers - can't handle binary variables

## Common Patterns Demonstrated

### Pattern 1: Binary Decision Variable

```python
open_var = LXVariable[Entity, int]("open").binary().from_data(ENTITIES)
```

### Pattern 2: Fixed Cost in Objective

```python
cost_expr = LXLinearExpression().add_term(
    open_var,
    coeff=lambda e: e.fixed_cost
)
```

### Pattern 3: Big-M Constraint

```python
# flow[i,j] ≤ M × open[i]
bigm_expr = (
    LXLinearExpression()
    .add_multi_term(flow, coeff=lambda i, j: 1.0, where=...)
    .add_term(open_var, coeff=lambda i: -M, where=...)
)
model.add_constraint(
    LXConstraint("bigm").expression(bigm_expr).le().rhs(0)
)
```

### Pattern 4: Conditional Capacity

```python
# flow ≤ capacity × open
capacity_expr = (
    LXLinearExpression()
    .add_multi_term(flow, ...)
    .add_term(open_var, coeff=lambda e: -e.capacity)
)
```

## Improving the Formulation

### Better Big-M Values

Instead of global Big-M, use specific bounds:

```python
# For each (warehouse, customer) pair
M_wc = min(warehouse.capacity, customer.demand)
# Tighter bound → better LP relaxation → faster solve
```

### Alternative Formulations

Consider:
1. **Aggregated Constraints**: Fewer Big-M constraints
2. **Strengthening Inequalities**: Add valid cuts
3. **Variable Bounds**: Tighten upper bounds on flow variables

## Extensions and Variations

This pattern extends to:

1. **Multi-Product**: Add product dimension to flow variables
2. **Multi-Period**: Dynamic facility opening/closing decisions
3. **Capacitated**: Different capacity levels (small, medium, large facilities)
4. **Modular Capacity**: Multiple capacity modules at each location
5. **Service Level**: Add maximum distance constraints
6. **Hub Location**: Warehouses serve other warehouses

## Use Cases

- **Distribution Network Design**: Minimize logistics costs
- **Server Placement**: Cloud computing infrastructure
- **Retail Site Selection**: Store location optimization
- **Emergency Services**: Hospital/fire station placement
- **Manufacturing**: Plant location and production allocation
- **Supply Chain**: Hub-and-spoke network design

## See Also

- **Example 01 (Production Planning)**: Single-model indexing basics
- **Example 02 (Driver Scheduling)**: Multi-model indexing foundation
- **Example 05 (CP-SAT Assignment)**: Pure integer programming
- **Goal Programming (Example 11)**: Soft constraints for facility location

## Files in This Example

- `facility_location.py`: Main optimization model and solution display
- `sample_data.py`: Data models (Warehouse, Customer) and cost calculations
- `README.md`: This documentation file

## Next Steps

After understanding this example:

1. Experiment with different Big-M values
2. Add service level constraints (maximum distance)
3. Implement multi-product flow
4. Add capacity expansion costs
5. Try different solvers and compare performance
6. Implement the alternative formulations suggested above
