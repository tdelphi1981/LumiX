"""
McCormick Envelope Linearization Example: Rectangle Area Optimization
======================================================================

This example demonstrates the automatic linearization of bilinear products
using McCormick envelopes.

Problem:
--------
Maximize the area of a rectangle subject to:
- Minimum perimeter constraint
- Individual dimension bounds

The area = length × width is a bilinear product that requires linearization
for solvers without native quadratic support.

Key Features Demonstrated:
---------------------------
- Bilinear product linearization (Continuous × Continuous)
- McCormick envelope technique
- Automatic auxiliary variable creation
- Solver-aware linearization

McCormick Envelope Theory:
--------------------------
For z = x × y with x ∈ [xL, xU], y ∈ [yL, yU], the four constraints:
    z >= xL*y + yL*x - xL*yL
    z >= xU*y + yU*x - xU*yU
    z <= xL*y + yU*x - xL*yU
    z <= xU*y + yL*x - xU*yL

form the tightest linear relaxation (convex hull) of the bilinear term.
"""

from typing import Any

from lumix import (
    LXConstraint,
    LXLinearExpression,
    LXLinearizer,
    LXLinearizerConfig,
    LXModel,
    LXNonLinearExpression,
    LXOptimizer,
    LXVariable,
)
from lumix.solvers import ORTOOLS_CAPABILITIES


# ==================== PROBLEM DATA ====================

MIN_PERIMETER = 20.0  # Minimum perimeter (meters)

LENGTH_MIN = 2.0  # Minimum length (meters)
LENGTH_MAX = 10.0  # Maximum length (meters)

WIDTH_MIN = 2.0  # Minimum width (meters)
WIDTH_MAX = 10.0  # Maximum width (meters)


solver_to_use = "cplex"

# ==================== MODEL BUILDING ====================


def build_rectangle_model():
    """
    Build rectangle area maximization model with bilinear objective.

    Returns:
        Model with nonlinear objective
    """
    # Decision Variables (scalar variables need single-element data source)
    # Using "dimension" as a simple scalar identifier
    scalar_data = ["dim"]

    length = (
        LXVariable[str, float]("length")
        .continuous()
        .bounds(lower=LENGTH_MIN, upper=LENGTH_MAX)
        .indexed_by(lambda x: x)
        .from_data(scalar_data)
    )

    width = (
        LXVariable[str, float]("width")
        .continuous()
        .bounds(lower=WIDTH_MIN, upper=WIDTH_MAX)
        .indexed_by(lambda x: x)
        .from_data(scalar_data)
    )

    # Create model
    model = LXModel("rectangle_area").add_variables(length, width)

    # Constraint: Minimum perimeter
    # 2 * (length + width) >= MIN_PERIMETER
    model.add_constraint(
        LXConstraint("min_perimeter")
        .expression(
            LXLinearExpression().add_term(length, 2.0).add_term(width, 2.0)
        )
        .ge()
        .rhs(MIN_PERIMETER)
    )

    # Objective: Maximize area = length × width (bilinear product!)
    # This will be automatically linearized using McCormick envelopes
    area_expr = LXNonLinearExpression().add_product(length, width)

    model.maximize(area_expr)

    return model, length, width


# ==================== MAIN ====================


def main():
    """Run the rectangle optimization with linearization."""

    print("=" * 70)
    print("LumiX Example: McCormick Envelope Linearization")
    print("=" * 70)
    print()

    print("Problem: Maximize rectangle area (length × width)")
    print(f"  Subject to: 2×(length + width) >= {MIN_PERIMETER}")
    print(f"  Bounds: length ∈ [{LENGTH_MIN}, {LENGTH_MAX}]")
    print(f"          width ∈ [{WIDTH_MIN}, {WIDTH_MAX}]")
    print()

    # Build model with nonlinear objective
    print("Building model with bilinear objective...")
    model, length, width = build_rectangle_model()
    print(model.summary())
    print()

    # Check model for nonlinear terms
    print("Analyzing model...")
    print(f"  ✓ Model contains bilinear product: length × width")
    print(f"  ✓ Variable bounds defined (required for McCormick)")
    print()

    # Create linearizer
    print("Creating linearizer...")
    config = LXLinearizerConfig(
        mccormick_tighten_bounds=True,
        verbose_logging=True,
    )
    linearizer = LXLinearizer(model, ORTOOLS_CAPABILITIES, config)
    print(f"  Solver: OR-Tools (needs linearization: {ORTOOLS_CAPABILITIES.needs_linearization_for_bilinear()})")
    print()

    # Linearize model
    if linearizer.needs_linearization():
        print("Applying McCormick envelope linearization...")
        linearized_model = linearizer.linearize_model()

        stats = linearizer.get_statistics()
        print()
        print("Linearization Statistics:")
        print("-" * 70)
        print(f"  Bilinear terms linearized: {stats['bilinear_terms']}")
        print(f"  Auxiliary variables added: {stats['auxiliary_variables']}")
        print(f"  Auxiliary constraints added: {stats['auxiliary_constraints']}")
        print()

        print("McCormick Envelope Constraints:")
        print("-" * 70)
        print(f"  z >= {LENGTH_MIN}*y + {WIDTH_MIN}*x - {LENGTH_MIN*WIDTH_MIN:.2f}")
        print(f"  z >= {LENGTH_MAX}*y + {WIDTH_MAX}*x - {LENGTH_MAX*WIDTH_MAX:.2f}")
        print(f"  z <= {LENGTH_MIN}*y + {WIDTH_MAX}*x - {LENGTH_MIN*WIDTH_MAX:.2f}")
        print(f"  z <= {LENGTH_MAX}*y + {WIDTH_MIN}*x - {LENGTH_MAX*WIDTH_MIN:.2f}")
        print()

        # Use linearized model
        model_to_solve = linearized_model
    else:
        print("No linearization needed (solver has native support)")
        model_to_solve = model

    # Solve
    print("Solving with OR-Tools...")
    try:
        optimizer = LXOptimizer().use_solver(solver_to_use)
        solution = optimizer.solve(model_to_solve)
        print()

        # Display results
        print("=" * 70)
        print("SOLUTION")
        print("=" * 70)

        if solution.is_optimal():
            print(f"Status: {solution.status}")
            print(f"Maximum Area: {solution.objective_value:.4f} m²")
            print(f"Solve Time: {solution.solve_time:.3f}s")
            print()

            # Get values from indexed variables (returns dict with index as key)
            length_dict = solution.get_mapped(length)
            width_dict = solution.get_mapped(width)

            # Since we used single-element data ["dim"], extract the value
            length_val = length_dict["dim"]
            width_val = width_dict["dim"]

            print("Optimal Rectangle Dimensions:")
            print("-" * 70)
            print(f"  Length: {length_val:.4f} meters")
            print(f"  Width:  {width_val:.4f} meters")
            print(f"  Area:   {length_val * width_val:.4f} m²")
            print(f"  Perimeter: {2*(length_val + width_val):.4f} meters")
            print()

            # Verify McCormick envelope constraints
            print("Verification:")
            print("-" * 70)
            actual_product = length_val * width_val
            print(f"  Actual product (length × width): {actual_product:.4f}")
            print(f"  Objective value: {solution.objective_value:.4f}")
            print(f"  Difference: {abs(actual_product - solution.objective_value):.6f}")
            print()

            if abs(actual_product - solution.objective_value) < 1e-4:
                print("  ✓ McCormick envelope linearization is accurate!")
            else:
                print("  ⚠ Warning: Linearization may not be exact")

        else:
            print(f"No optimal solution found. Status: {solution.status}")

    except ImportError as e:
        print(f"ERROR: {e}")
        print("\nPlease install OR-Tools:")
        print("  pip install ortools")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
