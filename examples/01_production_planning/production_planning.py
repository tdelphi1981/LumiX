"""Production Planning Example: Single-Model Indexing.

This example demonstrates LumiX's single-model indexing feature, which allows
variables and constraints to be indexed directly by data model instances rather
than manual integer indices.

Problem Description:
    A manufacturing company produces multiple products, each requiring different
    amounts of limited resources (labor hours, machine hours, raw materials).
    The goal is to maximize total profit while:
        - Respecting resource capacity constraints
        - Meeting minimum production requirements for customer orders
        - Ensuring non-negative production quantities

Mathematical Formulation:
    Maximize:
        sum(profit_per_unit[p] * production[p] for p in products)

    Subject to:
        - Resource capacity: sum(usage[p,r] * production[p]) <= capacity[r] for all r
        - Minimum production: production[p] >= min_production[p] for all p
        - Non-negativity: production[p] >= 0 for all p

Key Features Demonstrated:
    - **Single-model indexing**: Variables indexed by Product instances
    - **Data-driven modeling**: Coefficients extracted from data using lambdas
    - **Type-safe solution access**: Solutions indexed by model instances
    - **Automatic expansion**: Variable families expand to one var per product
    - **Constraint families**: Multiple constraints indexed by data instances

Use Cases:
    This pattern is ideal for:
        - Production planning and scheduling
        - Resource allocation problems
        - Portfolio optimization
        - Supply chain optimization
        - Any problem with homogeneous decision variables indexed by entities

Learning Objectives:
    1. How to create variable families indexed by data models
    2. How to use lambda functions for data-driven coefficient extraction
    3. How to build expressions that automatically sum over all instances
    4. How to create constraint families for similar constraints
    5. How to access solutions using the same index as the original data

See Also:
    - Example 02 (driver_scheduling): Multi-model indexing with cartesian products
    - Example 04 (basic_lp): Simpler introduction to LumiX basics
    - User Guide: Single-Model Indexing section
"""

from lumix import LXConstraint, LXLinearExpression, LXModel, LXOptimizer, LXVariable

from sample_data import PRODUCTS, RESOURCES, Product, Resource, get_resource_usage


solver_to_use = "cplex"

# ==================== MODEL BUILDING ====================


def build_production_model() -> LXModel:
    """Build the production planning optimization model.

    This function constructs a linear programming model to maximize profit
    from production while respecting resource capacity constraints and minimum
    production requirements.

    The model uses single-model indexing where variables are indexed directly
    by Product instances, eliminating the need for manual index management.

    Returns:
        An LXModel instance containing:
            - Variables: production[p] for each product p
            - Objective: Maximize total profit
            - Constraints: Resource capacity limits and minimum production

    Example:
        >>> model = build_production_model()
        >>> print(model.summary())
        >>> optimizer = LXOptimizer().use_solver("ortools")
        >>> solution = optimizer.solve(model)

    Notes:
        The data-driven approach means all coefficients are extracted from
        the PRODUCTS and RESOURCES data using lambda functions, making the
        model automatically adapt to changes in the data.
    """

    # Decision Variable: Production quantity for each product
    # KEY: LXVariable family that auto-expands to one var per product!
    production = (
        LXVariable[Product, float]("production")
        .continuous()
        .bounds(lower=0)
        .indexed_by(lambda p: p.id)  # Index by product ID
        .from_data(PRODUCTS)  # Provide data directly - NO manual loops!
    )

    # Create model
    model = LXModel[Product]("production_planning").add_variable(production)

    # Objective: Maximize total profit
    # The expression automatically sums over ALL products in the variable family
    profit_expr = (
        LXLinearExpression[Product]()
        .add_term(
            production,
            coeff=lambda p: p.selling_price - p.unit_cost  # Profit per unit
        )
    )
    model.maximize(profit_expr)

    # Constraints: Resource capacity limits
    # For each resource, sum(usage * production) <= capacity
    for resource in RESOURCES:
        # Build expression that sums over all products automatically
        usage_expr = (
            LXLinearExpression()
            .add_term(
                production,
                coeff=lambda p, r=resource: get_resource_usage(p, r)
            )
        )

        # Add capacity constraint for this resource
        model.add_constraint(
            LXConstraint(f"capacity_{resource.name}")
            .expression(usage_expr)
            .le()
            .rhs(resource.capacity)
        )

    # Constraints: Minimum production requirements
    # For each product, production[product] >= min_production
    # Create constraint family indexed by Product
    model.add_constraint(
        LXConstraint[Product]("min_production")
        .expression(
            LXLinearExpression[Product]().add_term(production, 1.0)
        )
        .ge()
        .rhs(lambda p: float(p.min_production))
        .from_data(PRODUCTS)  # One constraint per product
        .indexed_by(lambda p: p.name)
    )

    return model


# ==================== SOLUTION DISPLAY ====================


def display_solution(model: LXModel):
    """Solve the optimization model and display results.

    This function solves the production planning model and presents the results
    in a human-readable format, including the production plan, profit breakdown,
    and resource utilization.

    Args:
        model: The LXModel instance to solve, typically from build_production_model().

    Example:
        >>> model = build_production_model()
        >>> display_solution(model)
        ============================================================
        SOLUTION
        ============================================================
        Status: optimal
        Optimal Profit: $12,345.67
        ...

    Notes:
        The function demonstrates how to access solution values using the same
        index keys (product IDs) that were used to define the variables.
    """

    print("\n" + "=" * 60)
    print("SOLUTION")
    print("=" * 60)

    optimizer = LXOptimizer().use_solver(solver_to_use)
    solution = optimizer.solve(model)

    if solution.is_optimal():
        print(f"Status: {solution.status}")
        print(f"Optimal Profit: ${solution.objective_value:,.2f}")
        print()

        print("Production Plan:")
        print("-" * 60)
        for product in PRODUCTS:
            # Get production quantity for this product
            qty = solution.variables["production"][product.id]
            if qty > 0.01:
                profit = (product.selling_price - product.unit_cost) * qty
                print(f"  {product.name:15s}: {qty:6.1f} units  "
                      f"(profit: ${profit:,.2f})")

        print()
        print("Resource Utilization:")
        print("-" * 60)
        for resource in RESOURCES:
            # Calculate total usage
            used = sum(
                solution.variables["production"][p.id] *
                get_resource_usage(p, resource)
                for p in PRODUCTS
            )
            pct = (used / resource.capacity) * 100
            print(f"  {resource.name:15s}: {used:6.1f}/{resource.capacity:6.1f} "
                  f"({pct:.1f}%)")
    else:
        print(f"No optimal solution found. Status: {solution.status}")


# ==================== MAIN ====================


def main():
    """Run the complete production planning example.

    This function orchestrates the entire optimization workflow:
        1. Display problem data (products and resources)
        2. Build the optimization model
        3. Solve the model
        4. Display and interpret results

    The workflow demonstrates best practices for using LumiX in production:
        - Clear separation between data, model building, and solving
        - Comprehensive result reporting
        - Type-safe solution access

    Example:
        Run this example from the command line::

            $ python production_planning.py

        Or import and run programmatically::

            >>> from production_planning import main
            >>> main()
    """

    print("=" * 60)
    print("OptiXNG Example: Production Planning")
    print("=" * 60)
    print()
    print("This example demonstrates:")
    print("  ✓ Single-model indexing (LXVariable[Product])")
    print("  ✓ Data-driven modeling")
    print("  ✓ Multiple resource constraints")
    print("  ✓ Type-safe solution mapping")
    print()

    # Display problem data
    print("Products:")
    print("-" * 60)
    for p in PRODUCTS:
        profit = p.selling_price - p.unit_cost
        print(f"  {p.name:15s}: ${p.selling_price:6.2f} - ${p.unit_cost:6.2f} "
              f"= ${profit:6.2f} profit/unit")
    print()

    print("Resources:")
    print("-" * 60)
    for r in RESOURCES:
        print(f"  {r.name:15s}: {r.capacity:6.1f} available")
    print()

    # Build model
    print("Building optimization model...")
    model = build_production_model()
    print(model.summary())

    # Solve and display solution
    display_solution(model)


if __name__ == "__main__":
    main()
