"""
Production Planning Example: Single-Model Indexing
==================================================

This example demonstrates OptiXNG's single-model indexing feature.
Variables and constraints are indexed by Product and Resource models.

Problem: Maximize profit while respecting resource capacity constraints.

Key Features:
- Variables indexed by Product (production[product])
- Constraints indexed by Resource (capacity[resource])
- Data-driven modeling (costs and requirements from data)
- Type-safe solution mapping
"""

from lumix import LXConstraint, LXLinearExpression, LXModel, LXOptimizer, LXVariable

from sample_data import PRODUCTS, RESOURCES, Product, Resource, get_resource_usage


# ==================== MODEL BUILDING ====================


def build_production_model() -> LXModel:
    """Build the production planning optimization model using data-driven approach."""

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
    """Display the optimization results."""

    print("\n" + "=" * 60)
    print("SOLUTION")
    print("=" * 60)

    optimizer = LXOptimizer().use_solver("cplex")
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
    """Run the production planning optimization."""

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
