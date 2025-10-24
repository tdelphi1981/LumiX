# Driver Scheduling Example

## Overview

This is **THE MOST IMPORTANT LUMIX EXAMPLE** - it demonstrates LumiX's **multi-model indexing** feature, the killer capability that sets LumiX apart from traditional optimization libraries.

Variables are indexed by **cartesian products** of multiple data models: `duty[Driver, Date]`, allowing natural representation of relationships between entities.

## Problem Description

Schedule drivers over a week to minimize total cost while meeting daily coverage requirements. Each driver:
- Has a daily rate and availability constraints
- Can work a maximum number of days per week
- Has specific days off
- Costs more on weekends (overtime multiplier)

Each date requires a minimum number of drivers to maintain service levels.

### Real-World Context

This type of problem appears in:
- Workforce scheduling and shift planning
- Transportation and logistics operations
- Healthcare staff rostering
- Retail and service industry scheduling
- On-demand service platforms (rideshare, delivery)

## Mathematical Formulation

**Decision Variables:**
- `duty[d,t]`: Binary variable = 1 if driver `d` works on date `t`, 0 otherwise

**Objective Function:**
```
Minimize: ∑∑(cost[d,t] × duty[d,t]) for all drivers d and dates t
```

Where:
- `cost[d,t] = daily_rate[d] × overtime_multiplier[t]`
- `overtime_multiplier[t] = 1.0` for weekdays, `1.5` for weekends

**Constraints:**
```
Driver max days:     ∑ duty[d,t] ≤ max_days[d]             for each driver d (sum over all dates)
Daily coverage:      ∑ duty[d,t] ≥ min_drivers[t]          for each date t (sum over all drivers)
Availability:        duty[d,t] = 0                         if driver d is not available on date t
Non-negativity:      duty[d,t] ∈ {0, 1}                    binary decision
```

## Key Concepts

### 1. Multi-Model Indexing

Variables indexed by **tuples** of multiple models:

```python
# Traditional approach (other libraries)
duty = [[model.add_var() for date in dates] for driver in drivers]
# Access: duty[0][1] - which driver? which date? Lost context!

# LumiX approach - THE KEY FEATURE!
duty = LXVariable[Tuple[Driver, Date], int]("duty").indexed_by_product(
    LXIndexDimension(Driver, lambda d: d.id).from_data(DRIVERS),
    LXIndexDimension(Date, lambda dt: dt.date).from_data(DATES)
)
# Access: solution.variables["duty"][(driver.id, date.date)]
# IDE knows the structure! Type-safe!
```

### 2. Cartesian Product Indexing

`indexed_by_product()` creates variables for every combination of Driver × Date:

```python
.indexed_by_product(
    LXIndexDimension(Driver, lambda d: d.id).where(lambda d: d.is_active),
    LXIndexDimension(Date, lambda dt: dt.date)
)
# Creates: duty[d1,t1], duty[d1,t2], ..., duty[d2,t1], duty[d2,t2], ...
```

### 3. Multi-Index Coefficients

Coefficient functions receive **both** models:

```python
.cost_multi(lambda driver, date: calculate_cost(driver, date))
# Function has access to BOTH driver and date objects!
```

### 4. Multi-Index Filtering

Filter combinations based on relationships between models:

```python
.where_multi(lambda driver, date: is_driver_available(driver, date))
# Only create variables for valid (driver, date) combinations
```

### 5. Dimensional Summation

Sum over specific dimensions using filters:

```python
# Sum over all dates for a specific driver
driver_days_expr = LXLinearExpression().add_multi_term(
    duty,
    coeff=lambda d, dt: 1.0,
    where=lambda d, dt, drv=driver: d.id == drv.id  # Filter for this driver
)

# Sum over all drivers for a specific date
coverage_expr = LXLinearExpression().add_multi_term(
    duty,
    coeff=lambda d, dt: 1.0,
    where=lambda d, dt, date=date: dt.date == date.date  # Filter for this date
)
```

### 6. Type-Safe Solution Access

Solutions preserve the multi-dimensional structure:

```python
for driver in DRIVERS:
    for date in DATES:
        value = solution.variables["duty"].get((driver.id, date.date), 0)
        # Access using actual (driver_id, date) tuple!
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
cd examples/02_driver_scheduling
python driver_scheduling.py
```

## Expected Output

```
======================================================================
LumiX Example: Driver Scheduling (Multi-Model Indexing)
======================================================================

⭐⭐⭐ THIS IS THE KEY LUMIX FEATURE! ⭐⭐⭐

This example demonstrates:
  ✓ Multi-model indexing: LXVariable[Tuple[Driver, Date]]
  ✓ LXIndexDimension with filters
  ✓ CartesianProduct (Driver × Date)
  ✓ cost_multi() - cost function receives both models
  ✓ where_multi() - filter based on both models
  ✓ Cross-model constraints (sum over specific dimensions)
  ✓ Type-safe solution mapping

Drivers:
----------------------------------------------------------------------
  Alice     : $120.00/day, max 5 days/week  [Active] (off: Sat, Sun)
  Bob       : $100.00/day, max 6 days/week  [Active] (off: Sun)
  Charlie   : $150.00/day, max 4 days/week  [Active] (off: Wed)
  ...

Dates:
----------------------------------------------------------------------
  Monday Jun 01: 2 drivers required (cost multiplier: 1.0x)
  Tuesday Jun 02: 2 drivers required (cost multiplier: 1.0x)
  ...
  Saturday Jun 06: 3 drivers required (cost multiplier: 1.5x)
  Sunday Jun 07: 3 drivers required (cost multiplier: 1.5x)

Building multi-model indexed optimization model...
Model Summary:
  Variables: 1 family (35 binary variables from 7 drivers × 7 dates)
  Constraints: 14 (7 max days + 7 coverage)

======================================================================
SOLUTION
======================================================================
Status: optimal
Optimal Cost: $2,450.00

Schedule by Date:
----------------------------------------------------------------------

Monday Jun 01, 2024:
  - Bob        ($100.00)
  - Charlie    ($150.00)
  Daily Cost: $250.00

Tuesday Jun 02, 2024:
  - Alice      ($120.00)
  - Bob        ($100.00)
  Daily Cost: $220.00

...

Saturday Jun 06, 2024 (1.5x):
  - Bob        ($150.00)
  - David      ($127.50)
  - Eve        ($135.00)
  Daily Cost: $412.50

Driver Summary:
----------------------------------------------------------------------
  Alice     : 4 days (Mon 06/01, Tue 06/02, Thu 06/04, Fri 06/05) = $480.00
  Bob       : 6 days (Mon 06/01, Tue 06/02, Wed 06/03, ...) = $650.00
  Charlie   : 3 days (Mon 06/01, Thu 06/04, Fri 06/05) = $450.00
  ...

======================================================================
Why This Matters:
======================================================================

Traditional libraries force numerical indices:
  duty[0][1] = 1  # Which driver? Which date? IDE doesn't know!

LumiX preserves model relationships:
  solution.variables['duty'][(driver.id, date.date)]
      # Indexed by actual data model keys
      # IDE knows the structure and types
      # Type-safe access to solution values

This is optimization that feels like normal programming!
```

## Key Learnings

### 1. Natural Problem Representation

Multi-model indexing allows you to express relationships naturally:
- `duty[driver, date]` instead of `duty[i][j]`
- `cost[warehouse, customer]` instead of `cost[i][j]`
- `flow[source, destination, time]` instead of `flow[i][j][k]`

### 2. Preserved Context

You never lose track of what indices represent. The data models carry all context.

### 3. Dimensional Reasoning

Constraints naturally express dimensional operations:
- Sum over all dates for each driver (driver capacity)
- Sum over all drivers for each date (daily coverage)

### 4. Cross-Model Relationships

Lambda functions have access to both (or all) models in the product, enabling complex relationship modeling.

### 5. Automatic Cartesian Product

No manual nested loops needed - `indexed_by_product()` handles the cartesian product automatically.

## Common Patterns Demonstrated

### Pattern 1: Multi-Model Variable

```python
decision = LXVariable[Tuple[ModelA, ModelB], type]("name").indexed_by_product(
    LXIndexDimension(ModelA, key_func).from_data(DATA_A),
    LXIndexDimension(ModelB, key_func).from_data(DATA_B)
)
```

### Pattern 2: Cross-Model Filtering

```python
.where_multi(lambda a, b: is_valid_combination(a, b))
```

### Pattern 3: Cross-Model Coefficients

```python
.cost_multi(lambda a, b: compute_cost(a, b))
```

### Pattern 4: Sum Over One Dimension

```python
# For each A, sum over all B
for a in DATA_A:
    expr = LXLinearExpression().add_multi_term(
        decision,
        coeff=lambda a_var, b_var: 1.0,
        where=lambda a_var, b_var, current_a=a: a_var.id == current_a.id
    )
```

### Pattern 5: Closure Capture

```python
# IMPORTANT: Capture loop variables by value!
where=lambda d, dt, drv=driver: d.id == drv.id
# NOT: where=lambda d, dt: d.id == driver.id  # WRONG! Captures reference
```

## Why This is LumiX's Killer Feature

### Traditional Libraries

```python
# Pulp, Pyomo, CVXPY, etc.
duty = {}
for i, driver in enumerate(drivers):
    for j, date in enumerate(dates):
        duty[i, j] = model.add_var(name=f"duty_{i}_{j}")

# Later: duty[0, 3] - which driver is 0? which date is 3?
# Lost all context! Must maintain separate mapping dictionaries.
```

### LumiX Approach

```python
duty = LXVariable[Tuple[Driver, Date], int]("duty").indexed_by_product(...)

# Later: solution.variables["duty"][(driver.id, date.date)]
# Full context preserved! IDE autocomplete! Type safety!
```

## Extensions and Variations

This pattern extends to:

1. **Triple Products**: `LXVariable[Tuple[A, B, C], type]` for 3-way relationships
2. **Supply Chain**: `ship[warehouse, customer, product]`
3. **Multi-Period**: `production[product, facility, time_period]`
4. **Network Flow**: `flow[origin, destination, commodity]`
5. **Assignment**: `assign[task, worker, time_slot]`

## See Also

- **Example 01 (Production Planning)**: Single-model indexing foundation
- **Example 03 (Facility Location)**: Binary variables with multi-model indexing
- **Example 05 (CP-SAT Assignment)**: Worker-task assignment problem
- **User Guide**: Multi-Model Indexing section

## Files in This Example

- `driver_scheduling.py`: Main optimization model and solution display
- `sample_data.py`: Data models (Driver, Date) and helper functions
- `README.md`: This documentation file

## Next Steps

After mastering this example:

1. Add a third dimension (e.g., shifts within days)
2. Add constraints linking consecutive days (rest requirements)
3. Implement preference-based scheduling
4. Add skill-based matching (drivers qualified for specific routes)
5. Extend to monthly or annual planning horizons
