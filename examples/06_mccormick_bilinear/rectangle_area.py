"""McCormick Envelope Linearization: Rectangle Area Optimization.

This example demonstrates automatic linearization of bilinear products using
McCormick envelopes, a fundamental technique for solving nonlinear optimization
problems with linear programming solvers.

Problem Description:
    Maximize the area of a rectangle subject to:
        - Minimum perimeter constraint (2×(length + width) >= MIN_PERIMETER)
        - Individual dimension bounds (length, width in [MIN, MAX])

    The area = length × width is a bilinear product that requires linearization
    for solvers without native quadratic programming support.

Mathematical Formulation:
    Maximize:
        area = length × width (bilinear product)

    Subject to:
        - 2×(length + width) >= MIN_PERIMETER
        - LENGTH_MIN <= length <= LENGTH_MAX
        - WIDTH_MIN <= width <= WIDTH_MAX

McCormick Envelope Theory:
    For z = x × y with x in [xL, xU], y in [yL, yU], the tightest linear
    relaxation (convex hull) is defined by four linear constraints::

        z >= xL*y + yL*x - xL*yL
        z >= xU*y + yU*x - xU*yU
        z <= xL*y + yU*x - xL*yU
        z <= xU*y + yL*x - xU*yL

    These constraints form the convex hull of the bilinear term, providing
    the tightest possible linear approximation.

Key Features Demonstrated:
    - **Bilinear product linearization**: Continuous × Continuous variables
    - **McCormick envelope technique**: Convex hull relaxation
    - **Automatic auxiliary variable creation**: z = x × y becomes linear
    - **Solver-aware linearization**: Detects when linearization is needed
    - **Bound tightening**: Optional refinement of McCormick constraints

Technical Details:
    The linearizer automatically:
        1. Detects bilinear products in the objective/constraints
        2. Creates auxiliary variable z to represent the product
        3. Adds four McCormick envelope constraints
        4. Replaces x×y with z throughout the model
        5. Maintains variable bounds for tightness

Use Cases:
    McCormick linearization applies to:
        - Area/volume optimization problems
        - Pooling and blending problems
        - Bilinear cost functions
        - Network flow with fixed charges
        - Any problem with x×y where both are decision variables

Learning Objectives:
    1. Understand when and why linearization is needed
    2. Learn McCormick envelope construction
    3. Master automatic linearization with LXLinearizer
    4. Recognize impact of variable bounds on approximation quality
    5. Interpret linearized model structure and auxiliary variables

See Also:
    - Example 07 (piecewise_functions): Nonlinear function approximation
    - LumiX documentation: Linearization module
    - LXLinearizer API: Configuration and usage
    - LXNonLinearExpression: Building nonlinear objectives

Prerequisites:
    Understanding of basic linear programming. Knowledge of quadratic
    programming is helpful but not required.

Notes:
    Tighter variable bounds lead to better McCormick approximations.
    For solvers with native QP support (Gurobi, CPLEX), linearization
    may not be necessary, but this technique works with any LP solver.
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
    """Build rectangle area maximization model with bilinear objective.

    This function constructs a nonlinear optimization model with a bilinear
    objective function (area = length × width) and linear constraints.

    The model demonstrates:
        - Scalar variable definition using single-element data sources
        - Bilinear product in objective function
        - Linear perimeter constraint
        - Variable bounds for McCormick envelope construction

    Returns:
        A tuple containing:
            - LXModel: Model with nonlinear objective
            - LXVariable: Length variable for solution access
            - LXVariable: Width variable for solution access

    Example:
        >>> model, length, width = build_rectangle_model()
        >>> print(model.summary())
        >>> # Check if linearization is needed
        >>> from lumix.solvers import ORTOOLS_CAPABILITIES
        >>> needs_lin = ORTOOLS_CAPABILITIES.needs_linearization_for_bilinear()
        >>> print(f"Needs linearization: {needs_lin}")

    Notes:
        The bilinear objective will be automatically linearized by LXLinearizer
        when using solvers that don't support quadratic programming natively.

        Variable bounds are critical for McCormick envelope quality. Tighter
        bounds result in better approximations of the bilinear product.
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
    """Run the rectangle optimization example with linearization.

    This function demonstrates the complete workflow for solving a problem
    with bilinear terms:
        1. Build model with nonlinear objective
        2. Check if linearization is needed for the solver
        3. Apply McCormick envelope linearization
        4. Solve the linearized model
        5. Verify the linearization accuracy

    The workflow shows best practices for:
        - Detecting linearization requirements
        - Configuring the linearizer
        - Analyzing linearization statistics
        - Validating the approximation quality

    Example:
        Run this example from the command line::

            $ python rectangle_area.py

        Or import and run programmatically::

            >>> from rectangle_area import main
            >>> main()

    Notes:
        The example displays detailed information about:
            - McCormick envelope constraints generated
            - Auxiliary variables and constraints added
            - Linearization accuracy verification
            - Comparison between exact product and linearized value
    """

    print("=" * 70)
    print("LumiX Example: McCormick Envelope Linearization")
    print("=" * 70)
    print()

    print("Problem: Maximize rectangle area (length × width)")
    print(f"  Subject to: 2×(length + width) >= {MIN_PERIMETER}")
    print(f"  Bounds: length in [{LENGTH_MIN}, {LENGTH_MAX}]")
    print(f"          width in [{WIDTH_MIN}, {WIDTH_MAX}]")
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
