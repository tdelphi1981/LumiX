"""
Basic Linear Programming Example: Diet Problem
===============================================

This is the SIMPLEST possible LumiX example.
Learn the absolute basics of data-driven model building here.

Problem: Minimize cost of food while meeting nutritional requirements.

Key Features Demonstrated:
- Variable families (one Variable expands to multiple solver variables)
- Data-driven modeling with .from_data()
- Automatic expression expansion (no manual loops)
- Type-safe coefficients with lambda functions
- OR-Tools solver integration
"""

from dataclasses import dataclass
from typing import Tuple

from lumix import LXConstraint, LXLinearExpression, LXModel, LXOptimizer, LXVariable


# ==================== DATA DEFINITIONS ====================


@dataclass
class Food:
    """Represents a food item with nutritional information."""

    name: str
    cost_per_serving: float  # $ per serving
    calories: float  # calories per serving
    protein: float  # grams per serving
    calcium: float  # mg per serving


# Sample foods
FOODS = [
    Food("Oatmeal", 0.30, 110, 4, 2),
    Food("Chicken", 2.40, 205, 32, 12),
    Food("Eggs", 0.50, 160, 13, 60),
    Food("Milk", 0.60, 160, 8, 285),
    Food("Apple Pie", 1.60, 420, 4, 22),
    Food("Pork", 2.90, 260, 14, 10),
]

# Nutritional requirements (daily minimums)
MIN_CALORIES = 2000
MIN_PROTEIN = 50  # grams
MIN_CALCIUM = 800  # mg


# ==================== MODEL BUILDING ====================


def build_diet_model() -> Tuple[LXModel, LXVariable[Food, float]]:
    """
    Build the diet optimization model using data-driven approach.

    Returns:
        Tuple of (model, servings variable) for type-safe solution access
    """
    # Decision Variable: Servings of each food (variable family)
    # ONE LXVariable that expands to multiple solver variables automatically
    servings = (
        LXVariable[Food, float]("servings")
        .continuous()
        .bounds(lower=0)
        .indexed_by(lambda f: f.name)
        .from_data(FOODS)  # Data-driven: auto-expands to one var per food
    )

    # Create model and add the variable family
    model = LXModel("diet_problem").add_variable(servings)

    # Objective: Minimize total cost
    # Expression automatically sums over all foods
    cost_expr = LXLinearExpression().add_term(
        servings,
        coeff=lambda f: f.cost_per_serving
    )
    model.minimize(cost_expr) # TODO feels like optimization runs in this line, naming confusion

    # Constraint 1: Minimum calories
    # Expression automatically sums calories from all foods
    model.add_constraint(
        LXConstraint("min_calories")
        .expression(
            LXLinearExpression().add_term(servings, lambda f: f.calories)
        )
        .ge()
        .rhs(MIN_CALORIES)
    )

    # Constraint 2: Minimum protein
    model.add_constraint(
        LXConstraint("min_protein")
        .expression(
            LXLinearExpression().add_term(servings, lambda f: f.protein)
        )
        .ge()
        .rhs(MIN_PROTEIN)
    )

    # Constraint 3: Minimum calcium
    model.add_constraint(
        LXConstraint("min_calcium")
        .expression(
            LXLinearExpression().add_term(servings, lambda f: f.calcium)
        )
        .ge()
        .rhs(MIN_CALCIUM)
    )

    return model, servings


# ==================== MAIN ====================


def main():
    """Run the diet problem optimization."""

    print("=" * 60)
    print("LumiX Example: Basic Diet Problem")
    print("=" * 60)
    print()

    # Build model
    print("Building optimization model...")
    model, servings = build_diet_model()
    print(model.summary())
    print()

    # Create optimizer with CP-SAT (with auto-scaling for continuous variables)
    print("Creating optimizer with CP-SAT solver (auto-scaling enabled)...")
    from lumix.solvers.cpsat_solver import LXCPSATSolver

    optimizer = LXOptimizer()
    # Use CP-SAT with auto-scaling for continuous variables
    optimizer.solver_name = "cpsat"
    cpsat_solver = LXCPSATSolver(auto_scale_continuous=True, scaling_factor=1000)
    optimizer._solver = cpsat_solver
    print("  Note: Continuous variables will be automatically scaled to integers")
    print()

    # Solve the model
    print("Solving...")
    try:
        solution = optimizer.solve(model)
        print()

        # Display results
        print("=" * 60)
        print("SOLUTION")
        print("=" * 60)

        if solution.is_optimal():
            print(f"Status: {solution.status}")
            print(f"Optimal Cost: ${solution.objective_value:.2f}")
            print(f"Solve Time: {solution.solve_time:.3f}s")
            print()

            print("Optimal Diet Plan:")
            print("-" * 60)

            # Access solution using mapped values (indexed by food name)
            total_cost = 0.0
            total_calories = 0.0
            total_protein = 0.0
            total_calcium = 0.0

            # Create lookup dict for Food instances by name
            food_by_name = {f.name: f for f in FOODS}

            for food_name, servings_qty in solution.get_mapped(servings).items():
                if servings_qty > 0.01:  # Only show non-zero servings
                    # Look up the Food instance by name
                    food = food_by_name[food_name]

                    cost = food.cost_per_serving * servings_qty
                    total_cost += cost
                    total_calories += food.calories * servings_qty
                    total_protein += food.protein * servings_qty
                    total_calcium += food.calcium * servings_qty

                    print(
                        f"  {food.name:12s}: {servings_qty:6.2f} servings  "
                        f"(cost: ${cost:5.2f})"
                    )
                    # Note: We look up Food instance using the index key

            print()
            print("Nutritional Totals:")
            print("-" * 60)
            print(f"  Total Cost:    ${total_cost:.2f}")
            print(f"  Calories:      {total_calories:6.1f} (min: {MIN_CALORIES})")
            print(f"  Protein:       {total_protein:6.1f}g (min: {MIN_PROTEIN}g)")
            print(f"  Calcium:       {total_calcium:6.1f}mg (min: {MIN_CALCIUM}mg)")

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
