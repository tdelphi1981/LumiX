# McCormick Envelope Linearization Example

## Overview

This example demonstrates the automatic linearization of bilinear products using **McCormick envelopes**, one of the most powerful techniques for linearizing continuous × continuous variable products.

## Problem: Rectangle Area Maximization

Maximize the area of a rectangle subject to:
- Minimum perimeter constraint: `2 × (length + width) >= 20`
- Dimension bounds: `length ∈ [2, 10]`, `width ∈ [2, 10]`

The objective `area = length × width` is a **bilinear product** that requires linearization for linear solvers.

## McCormick Envelope Technique

For `z = x × y` with `x ∈ [xL, xU]` and `y ∈ [yL, yU]`, McCormick envelopes create four linear constraints that form the **convex hull** (tightest possible linear relaxation):

```
z >= xL*y + yL*x - xL*yL  (convex envelope 1)
z >= xU*y + yU*x - xU*yU  (convex envelope 2)
z <= xL*y + yU*x - xL*yU  (concave envelope 1)
z <= xU*y + yL*x - xU*yL  (concave envelope 2)
```

### Why McCormick Envelopes?

1. **Tightest relaxation**: Provides the convex hull of the bilinear function
2. **No approximation error**: Exact at the optimal solution for many problems
3. **Efficient**: Only 4 constraints and 1 auxiliary variable
4. **Automatic**: LumiX applies this automatically when bounds are available

## Mathematical Background

### The Bilinear Product Problem

A **bilinear product** is a term of the form `z = x × y` where both `x` and `y` are decision variables. This creates a **nonlinear** optimization problem that standard linear solvers cannot handle directly.

**Example**: Rectangle area = length × width (both are variables)

### McCormick Envelope Construction

For bounded variables `x ∈ [xL, xU]` and `y ∈ [yL, yU]`, the McCormick envelope constructs four linear inequalities that bound the bilinear product `z = x × y`:

**Lower bounds** (convex envelopes):
```
z ≥ xL × y + yL × x - xL × yL
z ≥ xU × y + yU × x - xU × yU
```

**Upper bounds** (concave envelopes):
```
z ≤ xL × y + yU × x - xL × yU
z ≤ xU × y + yL × x - xU × yL
```

These four constraints form the **tightest possible linear relaxation** (convex hull) of the bilinear term.

### Geometric Interpretation

In 3D space (x, y, z), the surface `z = x × y` is a hyperbolic paraboloid (saddle shape). The McCormick envelope creates a polyhedral approximation using four planes that:
- Bound the surface from above and below
- Form the tightest convex relaxation
- Meet exactly at the corners of the domain

## Running the Example

### Prerequisites

```bash
pip install lumix
pip install ortools  # or cplex, gurobi
```

### Execute

```bash
cd examples/06_mccormick_bilinear
python rectangle_area.py
```

## Expected Output

```
LumiX Example: McCormick Envelope Linearization
====================================================================

Problem: Maximize rectangle area (length × width)
  Subject to: 2×(length + width) >= 20
  Bounds: length ∈ [2.0, 10.0]
          width ∈ [2.0, 10.0]

Linearization Statistics:
--------------------------------------------------------------------
  Bilinear terms linearized: 1
  Auxiliary variables added: 1
  Auxiliary constraints added: 4

SOLUTION
====================================================================
Status: optimal
Maximum Area: 25.0000 m²

Optimal Rectangle Dimensions:
--------------------------------------------------------------------
  Length: 5.0000 meters
  Width:  5.0000 meters
  Area:   25.0000 m²
```

## Key Learnings

### 1. Bounds are Required

McCormick envelopes **require** finite variable bounds:

```python
# CORRECT: Bounded variables
length = LXVariable[None, float]("length").continuous().bounds(lower=2, upper=10)
width = LXVariable[None, float]("width").continuous().bounds(lower=2, upper=10)

# INCORRECT: Unbounded variables
length = LXVariable[None, float]("length").continuous()  # McCormick won't work!
```

### 2. Automatic Linearization

LumiX automatically detects and linearizes bilinear products:

```python
# Define the bilinear product in the objective
area = length * width  # Bilinear!

# Enable linearization
model.enable_linearization()

# LumiX automatically:
# 1. Creates auxiliary variable z
# 2. Adds McCormick constraints
# 3. Replaces length × width with z in objective
```

### 3. Exactness at Optimality

For **convex** or **concave** optimization problems, McCormick often provides the **exact** optimal solution:
- The LP relaxation is tight at the optimum
- No integrality gap
- No approximation error

For **non-convex** problems, McCormick provides a relaxation (lower/upper bound).

### 4. Efficiency

Overhead per bilinear term:
- **1 auxiliary variable** (z)
- **4 linear constraints** (McCormick envelope)
- **No binary variables** needed

This is much more efficient than other linearization techniques.

### 5. Tightness of Bounds

The quality of the McCormick relaxation depends on bound tightness:

```python
# Tight bounds → Good relaxation
x ∈ [5, 6], y ∈ [3, 4]  # Small domain, tight envelope

# Loose bounds → Weak relaxation
x ∈ [0, 100], y ∈ [0, 100]  # Large domain, loose envelope
```

**Tip**: Use problem-specific bounds, not arbitrary large values.

## LumiX Implementation

### Using Bilinear Products

```python
from lumix import LXVariable, LXModel, LXOptimizer

# Define bounded continuous variables
length = LXVariable[None, float]("length").continuous().bounds(lower=2, upper=10)
width = LXVariable[None, float]("width").continuous().bounds(lower=2, upper=10)

# Create model
model = LXModel("rectangle").add_variables(length, width)

# Use bilinear product in objective (or constraints)
area = length * width
model.maximize(area)

# Add constraints
perimeter_expr = 2 * (length + width)
model.add_constraint(
    LXConstraint("min_perimeter").expression(perimeter_expr).ge().rhs(20)
)

# Enable automatic linearization
model.enable_linearization()

# Solve with linear solver
optimizer = LXOptimizer().use_solver("ortools")
solution = optimizer.solve(model)
```

### What Happens Under the Hood

1. **Detection**: LumiX scans objective and constraints for `x × y` terms
2. **Auxiliary Variable**: Creates `z = x × y`
3. **McCormick Constraints**: Adds 4 linear inequalities
4. **Substitution**: Replaces `x × y` with `z` in model
5. **Solve**: Sends linearized model to LP solver

## Types of Bilinear Products

LumiX supports different variable type combinations:

### 1. Continuous × Continuous (This Example)

**Linearization**: McCormick envelopes (4 constraints)

```python
area = continuous_x * continuous_y
```

### 2. Binary × Binary

**Linearization**: AND logic (3 constraints)

```python
and_result = binary_x * binary_y
# Equivalent to: and_result = 1 if both x=1 and y=1, else 0
```

### 3. Binary × Continuous

**Linearization**: Big-M method (4 constraints)

```python
conditional_flow = binary_open * continuous_flow
# Flow is active only if binary_open = 1
```

### 4. Integer × Integer

**Linearization**: Discretization or McCormick (depending on bounds)

```python
product = integer_x * integer_y
```

## Common Use Cases

### 1. Area/Volume Calculations

```python
area = length * width
volume = length * width * height  # Multiple bilinear products
```

### 2. Revenue Optimization

```python
revenue = price * quantity  # Both variables
# Price elasticity: quantity depends on price
```

### 3. Portfolio Optimization

```python
variance = weight_i * weight_j * covariance[i,j]
# Markowitz mean-variance optimization
```

### 4. Blending Problems

```python
concentration = fraction_x * property_x + fraction_y * property_y
# Where fractions and properties may both be variables
```

### 5. Facility Location

```python
shipping_cost = open[facility] * distance[facility, customer]
# Conditional shipping based on facility opening
```

## Advanced Topics

### Tightening the Relaxation

Improve McCormick bounds by:

1. **Variable Bounds Tightening**: Use optimization to find tighter bounds
2. **Auxiliary Constraints**: Add valid inequalities
3. **Partitioning**: Divide domain into smaller regions (piecewise McCormick)

### Multiple Bilinear Terms

For `z = x₁ × x₂ + x₃ × x₄ + ...`:
- LumiX applies McCormick to **each** bilinear term
- Creates one auxiliary variable per product
- Overhead scales linearly with number of products

### Non-Convex Optimization

For non-convex problems:
- McCormick provides a relaxation (bound)
- May need **global optimization** techniques
- Consider **spatial branch-and-bound** for guarantees

## Comparison with Other Techniques

| Technique | Variables | Constraints | Exactness | Applicability |
|-----------|-----------|-------------|-----------|---------------|
| **McCormick** | +1 | +4 | Tight for convex | Continuous × Continuous |
| **Logarithmic** | +1 | +O(log n) | Approximate | Integer × Integer |
| **Binary Expansion** | +2log(n) | +O(log n) | Exact | Integer × Integer |
| **Big-M** | +1 | +4 | Exact | Binary × Continuous |
| **AND Logic** | 0 | +3 | Exact | Binary × Binary |

## Limitations

1. **Requires Finite Bounds**: Variables must have upper and lower bounds
2. **Relaxation Quality**: Depends on bound tightness
3. **Convexity**: Exact only for certain problem classes
4. **Multiple Products**: Each product adds overhead

## See Also

- **Example 07 (Piecewise Functions)**: Nonlinear function approximation
- **Example 03 (Facility Location)**: Big-M technique for binary × continuous
- **Goal Programming (Example 11)**: Combining linear and bilinear objectives
- **LumiX Documentation**: Nonlinear module reference

## Files in This Example

- `rectangle_area.py`: Main optimization model demonstrating McCormick
- `README.md`: This documentation file

## References

- McCormick, G. P. (1976). "Computability of global solutions to factorable nonconvex programs"
- Tawarmalani, M., & Sahinidis, N. V. (2005). "A polyhedral branch-and-cut approach to global optimization"

## Next Steps

1. Experiment with different bound ranges
2. Add multiple bilinear terms to the objective
3. Try bilinear constraints (not just objective)
4. Compare solve times with/without linearization
5. Implement piecewise McCormick for tighter relaxations
