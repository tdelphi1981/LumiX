"""Basic Linear Programming Example: Diet Problem.

This is the SIMPLEST possible LumiX example, designed as an introduction to
the fundamental concepts of data-driven optimization modeling.

Problem Description:
    The classic Diet Problem: determine the most cost-effective combination
    of foods that meets daily nutritional requirements. This is one of the
    first practical applications of linear programming, dating back to 1945.

    Given:
        - A set of food items, each with cost and nutritional content
        - Daily minimum requirements for calories, protein, and calcium

    Find: The number of servings of each food that minimizes total cost
    while meeting all nutritional requirements.

Mathematical Formulation:
    Minimize:
        sum(cost[f] * servings[f] for f in foods)

    Subject to:
        - sum(calories[f] * servings[f]) >= MIN_CALORIES
        - sum(protein[f] * servings[f]) >= MIN_PROTEIN
        - sum(calcium[f] * servings[f]) >= MIN_CALCIUM
        - servings[f] >= 0 for all f

Key Features Demonstrated:
    - **Variable families**: One LXVariable expands to multiple solver variables
    - **Data-driven modeling**: Use .from_data() to auto-create variables
    - **Automatic expansion**: Expressions sum over all data automatically
    - **Type-safe coefficients**: Lambda functions extract data attributes
    - **Fluent API**: Chain method calls for readable model building
    - **Solution mapping**: Access results using original data indices

Learning Objectives:
    1. Understand variable families and how they expand from data
    2. Learn to use lambda functions for coefficient extraction
    3. Master the fluent API pattern for model building
    4. Practice reading solutions with type-safe indexing
    5. Recognize when to use continuous vs integer variables

Use Cases:
    This pattern applies to any resource allocation problem:
        - Diet and meal planning
        - Portfolio optimization
        - Advertising budget allocation
        - Ingredient blending and mixing
        - Resource allocation across projects

Prerequisites:
    This is the perfect starting point for LumiX. No prior knowledge required.
    After mastering this example, move to example 01 (production planning)
    for more complex single-model indexing patterns.

See Also:
    - Example 01 (production_planning): More complex single-model indexing
    - Example 02 (driver_scheduling): Multi-model indexing
    - User Guide: Variables and Expressions sections
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


solver_to_use = "cplex"

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

    # Create optimizer with OR-Tools
    print("Creating optimizer with CPLEX solver...")
    optimizer = LXOptimizer()
    optimizer.use_solver(solver_to_use)


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
