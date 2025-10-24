# Basic Linear Programming Example

## Overview

This is the **SIMPLEST** LumiX example - perfect for learning the absolute basics of data-driven optimization modeling. If you're new to LumiX, start here!

This example demonstrates the classic **Diet Problem**: finding the minimum-cost combination of foods that meets nutritional requirements.

## Problem Description

A person wants to plan their daily diet to minimize food costs while meeting minimum nutritional requirements for:
- Calories (energy)
- Protein (muscle building)
- Calcium (bone health)

Each food item has:
- A cost per serving
- Nutritional content (calories, protein, calcium)

The challenge is to find how many servings of each food to consume to minimize total cost while meeting all nutritional needs.

### Real-World Context

This type of problem appears in:
- Meal planning and nutrition optimization
- Animal feed formulation (agriculture)
- Military ration planning
- Hospital dietary planning
- Cost-conscious nutrition programs

### Historical Significance

The Diet Problem was one of the first practical applications of linear programming, solved by George Stigler in 1945 (before modern computers!) to find the cheapest way to meet nutritional requirements during WWII.

## Mathematical Formulation

**Decision Variables:**
- `servings[f]`: Number of servings of food `f` to consume

**Objective Function:**
```
Minimize: ∑(cost_per_serving[f] × servings[f]) for all foods f
```

**Constraints:**
```
Minimum calories:    ∑(calories[f] × servings[f]) ≥ MIN_CALORIES
Minimum protein:     ∑(protein[f] × servings[f]) ≥ MIN_PROTEIN
Minimum calcium:     ∑(calcium[f] × servings[f]) ≥ MIN_CALCIUM
Non-negativity:      servings[f] ≥ 0 for all foods f
```

### Example Data

```
Foods:
  Oatmeal:     $0.30/serving, 110 cal, 4g protein, 2mg calcium
  Chicken:     $2.40/serving, 205 cal, 32g protein, 12mg calcium
  Eggs:        $0.50/serving, 160 cal, 13g protein, 60mg calcium
  Milk:        $0.60/serving, 160 cal, 8g protein, 285mg calcium
  Apple Pie:   $1.60/serving, 420 cal, 4g protein, 22mg calcium
  Pork:        $2.90/serving, 260 cal, 14g protein, 10mg calcium

Daily Requirements:
  Calories: ≥ 2000
  Protein:  ≥ 50g
  Calcium:  ≥ 800mg
```

## Key Concepts

### 1. Variable Families

ONE variable declaration expands to multiple solver variables:

```python
servings = (
    LXVariable[Food, float]("servings")
    .continuous()
    .bounds(lower=0)
    .indexed_by(lambda f: f.name)
    .from_data(FOODS)  # Expands to one variable per food!
)
# Creates: servings[Oatmeal], servings[Chicken], servings[Eggs], ...
```

### 2. Data-Driven Modeling

Coefficients come directly from data:

```python
cost_expr = LXLinearExpression().add_term(
    servings,
    coeff=lambda f: f.cost_per_serving  # Data-driven coefficient!
)
```

### 3. Automatic Expression Expansion

No manual loops needed:

```python
# This automatically sums over ALL foods
model.add_constraint(
    LXConstraint("min_calories")
    .expression(LXLinearExpression().add_term(servings, lambda f: f.calories))
    .ge()
    .rhs(MIN_CALORIES)
)
# Expands to: sum(f.calories × servings[f] for all f in FOODS) ≥ MIN_CALORIES
```

### 4. Type-Safe Solution Access

Access solutions using the index keys:

```python
for food_name, qty in solution.get_mapped(servings).items():
    print(f"{food_name}: {qty:.2f} servings")
# food_name is the name of the food (string)
# qty is the optimal number of servings (float)
```

### 5. Linear Programming Basics

Key properties of LP problems:
- **Linear objective**: Coefficients are constants, no products of variables
- **Linear constraints**: All constraint expressions are linear
- **Continuous variables**: Can take any non-negative value (not just integers)
- **Convex feasible region**: Optimal solution at a vertex
- **Polynomial-time solvable**: Efficiently solved with simplex or interior-point methods

## Running the Example

### Prerequisites

Install LumiX and a solver:

```bash
pip install lumix
pip install ortools  # or cplex, gurobi
```

### Execute

```bash
cd examples/04_basic_lp
python basic_lp.py
```

## Expected Output

```
============================================================
LumiX Example: Basic Diet Problem
============================================================

Building optimization model...
Model Summary:
  Variables: 1 family (6 decision variables)
  Constraints: 3 (calories, protein, calcium)
  Objective: Minimize total cost

Creating optimizer with CPLEX solver...

Solving...

============================================================
SOLUTION
============================================================
Status: optimal
Optimal Cost: $3.15
Solve Time: 0.042s

Optimal Diet Plan:
------------------------------------------------------------
  Oatmeal      :   4.00 servings  (cost: $1.20)
  Eggs         :   2.50 servings  (cost: $1.25)
  Milk         :   1.25 servings  (cost: $0.75)

Nutritional Totals:
------------------------------------------------------------
  Total Cost:    $3.15
  Calories:      2000.0 (min: 2000)
  Protein:       51.5g (min: 50g)
  Calcium:       811.3mg (min: 800mg)
```

## Key Learnings

### 1. Separation of Data and Model

LumiX encourages clean separation:
```python
# Data layer
@dataclass
class Food:
    name: str
    cost_per_serving: float
    calories: float
    # ...

# Model layer
servings = LXVariable[Food, float]("servings").from_data(FOODS)
```

### 2. Declarative Modeling

You declare **what** you want, not **how** to compute it:
```python
model.minimize(cost_expr)  # Declare objective
model.add_constraint(...)  # Declare constraints
# LumiX handles the rest!
```

### 3. Lambda Functions for Coefficients

Lambda functions extract data at the right time:
```python
coeff=lambda f: f.cost_per_serving
# f is a Food instance from FOODS
# Coefficient computed when building model
```

### 4. Variable Bounds

Set bounds directly on variables:
```python
.bounds(lower=0)  # Can't consume negative food!
# Could also set upper bounds: .bounds(lower=0, upper=10)
```

### 5. Constraint Types

LumiX supports:
- `.le()` - Less than or equal (≤)
- `.ge()` - Greater than or equal (≥)
- `.eq()` - Equal (=)

```python
model.add_constraint(
    LXConstraint("min_calories")
    .expression(calorie_expr)
    .ge()  # Greater than or equal
    .rhs(MIN_CALORIES)
)
```

## Understanding the Solution

### Why This Diet?

The optimal solution chose:
- **Oatmeal**: Cheap calories
- **Eggs**: Good protein-to-cost ratio
- **Milk**: Excellent calcium source

It avoided:
- **Chicken, Pork**: Too expensive for the nutrition provided
- **Apple Pie**: High cost, low nutritional value

### Solution Characteristics

The solution is at a **vertex** of the feasible region where exactly 3 constraints are **binding** (satisfied with equality):
1. Calories constraint: Exactly 2000 (at minimum)
2. Protein constraint: ~51.5g (slightly above minimum)
3. Calcium constraint: ~811mg (slightly above minimum)

### Shadow Prices

Each constraint has a **shadow price** (marginal value):
- If we relax "minimum calories by 1", cost decreases by X cents
- If we relax "minimum calcium by 1mg", cost decreases by Y cents
(See Example 09: Sensitivity Analysis for details)

## Common Patterns Demonstrated

### Pattern 1: Single-Model Variable Family

```python
var = (
    LXVariable[DataModel, VarType]("name")
    .continuous()  # or .binary(), .integer()
    .bounds(lower=0, upper=None)
    .indexed_by(lambda m: m.key)
    .from_data(DATA)
)
```

### Pattern 2: Data-Driven Objective

```python
expr = LXLinearExpression().add_term(var, coeff=lambda m: m.cost)
model.minimize(expr)  # or .maximize(expr)
```

### Pattern 3: Resource Constraints

```python
model.add_constraint(
    LXConstraint("resource_name")
    .expression(LXLinearExpression().add_term(var, coeff=lambda m: m.usage))
    .ge()  # or .le(), .eq()
    .rhs(MINIMUM)  # or MAXIMUM, TARGET
)
```

## Extensions and Variations

This basic example can be extended to include:

1. **Maximum Servings**: Add upper bounds on servings per food
   ```python
   .bounds(lower=0, upper=5)  # At most 5 servings
   ```

2. **Food Groups**: Ensure variety (min/max from each group)
   ```python
   # At least 2 servings from dairy group
   dairy_expr = LXLinearExpression().add_term(
       servings,
       coeff=lambda f: 1.0 if f.group == "dairy" else 0.0
   )
   ```

3. **Multiple Nutrients**: Add vitamins, minerals, fiber, etc.

4. **Maximum Constraints**: Limit sugar, fat, sodium
   ```python
   .expression(sugar_expr).le().rhs(MAX_SUGAR)
   ```

5. **Binary Choices**: Either include food or don't (no fractional servings)
   ```python
   servings = LXVariable[Food, int]("servings").binary()
   ```

6. **Multi-Day Planning**: Add time dimension
   ```python
   servings = LXVariable[Tuple[Food, Day], float]("servings")
   ```

## Comparison with Traditional Libraries

### PuLP / Pyomo

```python
# Traditional approach
servings = {f.name: LpVariable(f"servings_{f.name}", lowBound=0) for f in FOODS}
cost = lpSum([f.cost_per_serving * servings[f.name] for f in FOODS])
```

### LumiX

```python
# LumiX approach
servings = LXVariable[Food, float]("servings").continuous().from_data(FOODS)
cost = LXLinearExpression().add_term(servings, coeff=lambda f: f.cost_per_serving)
```

**Advantages**:
- Type-safe: `servings` is typed as `LXVariable[Food, float]`
- Data-driven: Automatically expands from `FOODS`
- No manual dictionary creation
- IDE autocomplete and type checking

## See Also

- **Example 01 (Production Planning)**: More complex single-model indexing
- **Example 02 (Driver Scheduling)**: Multi-model indexing introduction
- **Example 03 (Facility Location)**: Mixed-integer programming
- **Example 09 (Sensitivity Analysis)**: Understanding shadow prices
- **Example 11 (Goal Programming)**: Soft constraints for diet flexibility

## Files in This Example

- `basic_lp.py`: Main optimization model and solution display
- `README.md`: This documentation file

## Next Steps

After understanding this example:

1. Modify the data (add new foods, change costs/nutrition)
2. Add new constraints (food groups, variety, preferences)
3. Change the objective (maximize protein while limiting cost)
4. Make it interactive (user inputs their requirements)
5. Add upper bounds on servings
6. Move on to Example 01 for more advanced features
