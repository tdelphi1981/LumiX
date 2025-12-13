"""
Basic Goal Programming Example
================================

Demonstrates automatic LP-to-Goal Programming conversion with:
- Simple production planning problem
- Goal constraints for demand targets
- Automatic deviation variable creation
- Weighted goal programming (single solve)

Problem:
--------
A company produces two products with limited resources.
Goals (soft constraints):
1. Meet minimum production targets (>=)
2. Limit overtime hours (<=)
3. Achieve target profit (==)

Hard constraints:
- Total hours <= capacity
"""

from dataclasses import dataclass

from lumix import (
    LXConstraint,
    LXLinearExpression,
    LXModel,
    LXOptimizer,
    LXSolution,
    LXVariable,
)


# Data Models
@dataclass
class Product:
    """Product with production targets."""

    id: int
    name: str
    target_production: float  # Minimum production goal
    hours_per_unit: float
    profit_per_unit: float


# Sample Data
PRODUCTS = [
    Product(id=1, name="Product A", target_production=100, hours_per_unit=2.0, profit_per_unit=10.0),
    Product(id=2, name="Product B", target_production=80, hours_per_unit=3.0, profit_per_unit=15.0),
]

# Resource constraints
MAX_HOURS = 400  # Hard capacity limit
TARGET_PROFIT = 1800  # Profit goal
MAX_OVERTIME = 50  # Overtime hour limit goal

solver_to_use = "ortools"


def main():
    """Run the basic goal programming example with automatic constraint relaxation.

    This function demonstrates LumiX's automatic LP-to-Goal Programming conversion
    feature, which transforms hard constraints into soft goals with deviation
    variables. The workflow includes:
        1. Building a production planning model with hard and soft constraints
        2. Marking constraints as goals with priorities and weights
        3. Automatically preparing goal programming (creates deviation variables)
        4. Solving with weighted goal programming (single optimization)
        5. Analyzing goal satisfaction and deviations

    The example uses a simple production planning problem with three goals:
        - Priority 1 (highest): Meet production targets
        - Priority 2 (medium): Limit overtime hours
        - Priority 3 (lowest): Achieve target profit

    Returns:
        None. Results are printed to console including:
            - Model summary with variables and constraints
            - Optimal solution with production quantities
            - Goal satisfaction status for each goal
            - Deviation analysis (under/over for each goal)

    Example:
        Run this example from the command line::

            $ python 01_basic_goal_programming.py

        Or import and run programmatically::

            >>> from examples.goal_programming.basic_goal_programming import main
            >>> main()

        Expected output::

            ====================================================================
            Basic Goal Programming Example
            ====================================================================

            Model Summary:
            ...

            Production Plan:
            Product A       :   100.00 units (Target: 100.00)
            Product B       :    80.00 units (Target: 80.00)
            ...

            Goal Satisfaction:
            Production Goal Product A: [SATISFIED]
              Under-production: 0.00
              Over-production:  0.00
            ...

    Notes:
        Goal Programming concepts demonstrated:
            - Hard constraints: Must be satisfied (e.g., capacity limits)
            - Soft constraints (goals): Can be violated with penalty
            - Deviation variables: neg (under) and pos (over) deviation
            - Priorities: Higher priority goals are more important
            - Weights: Relative importance within same priority level

        The .as_goal() method marks a constraint as a goal:
            - .as_goal(priority=1, weight=1.0): Highest priority
            - Higher priorities dominate lower priorities in weighted mode
            - Within same priority, weights determine relative importance

        Weighted mode converts priorities to exponentially different weights:
            - Priority 1: weight * 10^6
            - Priority 2: weight * 10^5
            - Priority 3: weight * 10^4

        This ensures higher priorities are always satisfied first before
        considering lower priority goals.

        The .prepare_goal_programming() method automatically:
            - Creates deviation variables (neg, pos) for each goal
            - Replaces goal constraints with relaxed versions
            - Adds deviation terms to objective function
            - Maintains the original model structure
    """
    print("=" * 70)
    print("Basic Goal Programming Example")
    print("=" * 70)

    # Define variables
    production = (
        LXVariable[Product, float]("production")
        .continuous()
        .bounds(lower=0)
        .indexed_by(lambda p: p.id)
        .from_data(PRODUCTS)
    )

    # Scalar variable needs a data source - use single element
    overtime = (
        LXVariable[int, float]("overtime")
        .continuous()
        .bounds(lower=0)
        .indexed_by(lambda x: x)
        .from_data([1])  # Single instance for scalar variable
    )

    # Build model
    model = LXModel("goal_programming_basic")
    model.add_variables(production, overtime)

    # Hard constraint: Total hours <= capacity + overtime
    hours_expr = LXLinearExpression()
    hours_expr.add_term(production, lambda p: p.hours_per_unit)
    hours_expr.add_term(overtime, coeff=-1.0)  # Subtract overtime

    model.add_constraint(
        LXConstraint("capacity").expression(hours_expr).le().rhs(MAX_HOURS)
    )

    # Goal 1: Meet production targets (Priority 1, highest)
    # For each product, production >= target_production
    for product in PRODUCTS:
        prod_expr = LXLinearExpression()
        prod_expr.add_term(
            production,
            coeff=lambda p, prod=product: 1.0 if p.id == prod.id else 0.0
        )

        model.add_constraint(
            LXConstraint(f"production_goal_{product.id}")
            .expression(prod_expr)
            .ge()
            .rhs(product.target_production)
            .as_goal(priority=1, weight=1.0)  # Highest priority
        )

    # Goal 2: Limit overtime (Priority 2, medium)
    # overtime <= MAX_OVERTIME
    overtime_expr = LXLinearExpression().add_term(overtime, coeff=1.0)

    model.add_constraint(
        LXConstraint("overtime_goal")
        .expression(overtime_expr)
        .le()
        .rhs(MAX_OVERTIME)
        .as_goal(priority=2, weight=1.0)  # Medium priority
    )

    # Goal 3: Achieve target profit (Priority 3, lowest)
    # sum(production * profit) == TARGET_PROFIT
    profit_expr = LXLinearExpression()
    profit_expr.add_term(production, lambda p: p.profit_per_unit)

    model.add_constraint(
        LXConstraint("profit_goal")
        .expression(profit_expr)
        .eq()
        .rhs(TARGET_PROFIT)
        .as_goal(priority=3, weight=1.0)  # Lowest priority
    )

    # Set goal programming mode (weighted = single solve)
    model.set_goal_mode("weighted")

    # Prepare goal programming (automatic relaxation)
    model.prepare_goal_programming()

    print("\nModel Summary:")
    print(model.summary())

    # Solve
    print("\nSolving...")
    optimizer = LXOptimizer().use_solver(solver_to_use)
    solution = optimizer.solve(model)

    # Display results
    print("\n" + "=" * 70)
    print("Solution")
    print("=" * 70)
    print(solution.summary())

    print("\n" + "-" * 70)
    print("Production Plan:")
    print("-" * 70)
    for product in PRODUCTS:
        prod_value = solution.get_mapped(production).get(product.id, 0)
        print(
            f"{product.name:15s}: {prod_value:8.2f} units "
            f"(Target: {product.target_production:.2f})"
        )

    # Get overtime value (indexed by single element [1])
    overtime_value = solution.get_mapped(overtime).get(1, 0)
    print(f"\n{'Overtime':15s}: {overtime_value:8.2f} hours (Target: <={MAX_OVERTIME:.2f})")

    # Calculate actual profit
    actual_profit = sum(
        solution.get_mapped(production).get(p.id, 0) * p.profit_per_unit
        for p in PRODUCTS
    )
    print(f"{'Total Profit':15s}: ${actual_profit:8.2f} (Target: ${TARGET_PROFIT:.2f})")

    # Goal satisfaction analysis
    print("\n" + "-" * 70)
    print("Goal Satisfaction:")
    print("-" * 70)

    for product in PRODUCTS:
        goal_name = f"production_goal_{product.id}"
        deviations = solution.get_goal_deviations(goal_name)
        if deviations:
            # Get deviation values (they're indexed by goal ID)
            neg_dev_dict = deviations.get("neg", {})
            pos_dev_dict = deviations.get("pos", {})

            # Extract the value for this product's goal
            goal_id = f"{goal_name}_{product.id}"
            neg_dev = neg_dev_dict.get(goal_id, 0) if isinstance(neg_dev_dict, dict) else neg_dev_dict
            pos_dev = pos_dev_dict.get(goal_id, 0) if isinstance(pos_dev_dict, dict) else pos_dev_dict

            satisfied = solution.is_goal_satisfied(goal_name, tolerance=1e-6)
            status = "[SATISFIED]" if satisfied else "[NOT SATISFIED]"
            print(
                f"Production Goal {product.name}: {status}\n"
                f"  Under-production: {neg_dev:.2f}\n"
                f"  Over-production:  {pos_dev:.2f}"
            )

    # Overtime goal (non-indexed, single value)
    deviations = solution.get_goal_deviations("overtime_goal")
    if deviations:
        neg_dev_val = deviations.get("neg", {})
        pos_dev_val = deviations.get("pos", {})

        # Extract scalar value (indexed by goal ID)
        goal_id = "overtime_goal"
        neg_dev = neg_dev_val.get(goal_id, 0) if isinstance(neg_dev_val, dict) else neg_dev_val
        pos_dev = pos_dev_val.get(goal_id, 0) if isinstance(pos_dev_val, dict) else pos_dev_val

        satisfied = solution.is_goal_satisfied("overtime_goal")
        status = "[SATISFIED]" if satisfied else "[NOT SATISFIED]"
        print(
            f"\nOvertime Goal: {status}\n"
            f"  Under limit:  {neg_dev:.2f}\n"
            f"  Over limit:   {pos_dev:.2f}"
        )

    # Profit goal (non-indexed, single value)
    deviations = solution.get_goal_deviations("profit_goal")
    if deviations:
        neg_dev_val = deviations.get("neg", {})
        pos_dev_val = deviations.get("pos", {})

        # Extract scalar value (indexed by goal ID)
        goal_id = "profit_goal"
        neg_dev = neg_dev_val.get(goal_id, 0) if isinstance(neg_dev_val, dict) else neg_dev_val
        pos_dev = pos_dev_val.get(goal_id, 0) if isinstance(pos_dev_val, dict) else pos_dev_val

        satisfied = solution.is_goal_satisfied("profit_goal")
        status = "[SATISFIED]" if satisfied else "[NOT SATISFIED]"
        print(
            f"\nProfit Goal: {status}\n"
            f"  Under target: ${neg_dev:.2f}\n"
            f"  Over target:  ${pos_dev:.2f}"
        )

    # Visualize goals
    visualize_goals(model, solution)

    print("\n" + "=" * 70)


def visualize_goals(model: LXModel, solution: LXSolution) -> None:
    """Visualize goal programming results interactively.

    Creates interactive charts showing goal satisfaction status
    and deviation analysis.

    Args:
        model: The optimization model
        solution: The solution to visualize

    Requires:
        pip install lumix-opt[viz]
    """
    try:
        from lumix.visualization import LXGoalProgressChart

        print("\n" + "=" * 70)
        print("INTERACTIVE VISUALIZATION")
        print("=" * 70)

        viz = LXGoalProgressChart(solution)
        viz.show()

    except ImportError:
        print("\nVisualization skipped (install with: pip install lumix-opt[viz])")


if __name__ == "__main__":
    main()
