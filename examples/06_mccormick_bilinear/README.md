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

## Running the Example

```bash
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

1. **Bounds are required**: McCormick envelopes need variable bounds. Always specify `.bounds(lower=..., upper=...)`

2. **Automatic application**: LumiX detects bilinear products and applies McCormick automatically when using `.enable_linearization()`

3. **Exact solutions**: For many problems, McCormick provides the exact optimal solution, not just an approximation

4. **Efficiency**: Only adds 1 auxiliary variable and 4 constraints per bilinear term

## See Also

- **Binary × Binary products**: Use AND logic (3 constraints)
- **Binary × Continuous products**: Use Big-M method (4 constraints)
- **Piecewise functions**: See `examples/07_piecewise_functions/`
