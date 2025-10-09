"""
Basic Linear Programming Example: Diet Problem
===============================================

This is the SIMPLEST possible OptiXNG example.
Learn the absolute basics of data-driven model building here.

Problem: Minimize cost of food while meeting nutritional requirements.

Key Features Demonstrated:
- Variable families (one Variable expands to multiple solver variables)
- Data-driven modeling with .from_data()
- Automatic expression expansion (no manual loops)
- Type-safe coefficients with lambda functions
"""

from dataclasses import dataclass

from optixng import LXConstraint, LXLinearExpression, LXModel, LXOptimizer, LXVariable


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


def build_diet_model() -> LXModel:
    """Build the diet optimization model using data-driven approach."""

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
    model.minimize(cost_expr)

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

    return model


# ==================== MAIN ====================


def main():
    """Run the diet problem optimization."""

    print("=" * 60)
    print("OptiXNG Example: Basic Diet Problem")
    print("=" * 60)
    print()

    # Build model
    print("Building optimization model...")
    model = build_diet_model()
    print(model.summary())
    print()

    # Create optimizer
    print("Creating optimizer...")
    optimizer = LXOptimizer()
    print("NOTE: Solver implementations not yet complete.")
    print("This example demonstrates the API for model building.")
    print()

    # Would solve like this with data-driven mapping:
    # solution = optimizer.solve(model)
    # print(f"Status: {solution.status}")
    # print(f"Optimal Cost: ${solution.objective_value:.2f}")
    # print("\nDiet Plan:")
    # for food, servings_qty in solution.get_mapped(servings).items():
    #     if servings_qty > 0.01:
    #         print(f"  {food.name}: {servings_qty:.1f} servings")
    #         # Note: food is Food type, IDE knows about food.name, food.cost_per_serving, etc.

    print("Model built successfully!")
    print("Next steps:")
    print("  1. Implement solver backend (OR-Tools/Gurobi/CPLEX)")
    print("  2. Call optimizer.solve(model)")
    print("  3. Access solution.variables to get results")


if __name__ == "__main__":
    main()
