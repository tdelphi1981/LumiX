"""
Facility Location Example: Binary Variables and Fixed Costs
===========================================================

This example demonstrates:
- Binary decision variables (open warehouse or not)
- Fixed costs (one-time opening cost)
- Continuous flow variables (shipping quantities)
- Big-M constraints (ship only from open warehouses)
- Mixed-integer programming

Problem: Decide which warehouses to open and how to serve customers
to minimize total cost (fixed opening costs + variable shipping costs).
"""

from typing import Dict, Tuple

from optixng import Constraint, LinearExpression, Model, Optimizer, Variable

from sample_data import (
    BIG_M,
    CUSTOMERS,
    WAREHOUSES,
    Customer,
    Warehouse,
    shipping_cost,
)


# ==================== MODEL BUILDING ====================


def build_facility_location_model() -> Model:
    """Build the facility location optimization model."""

    # Decision Variable 1: Binary - Open warehouse or not
    open_warehouse = {}
    for warehouse in WAREHOUSES:
        var = (
            Variable[Warehouse, int](f"open_{warehouse.name}")
            .binary()
            .cost(warehouse.fixed_cost)  # Fixed cost if opened
        )
        open_warehouse[warehouse.id] = var

    # Decision Variable 2: Continuous - Shipping quantities
    # This could be multi-indexed by (Warehouse, Customer)
    # For simplicity, using dict of dicts here
    ship = {}
    for warehouse in WAREHOUSES:
        for customer in CUSTOMERS:
            cost = shipping_cost(warehouse, customer)
            var = (
                Variable[Tuple[Warehouse, Customer], float](
                    f"ship_{warehouse.name}_to_{customer.name}"
                )
                .continuous()
                .bounds(lower=0, upper=customer.demand)
            )
            ship[(warehouse.id, customer.id)] = var

    # Create model
    model = Model("facility_location")

    # Add variables
    for var in open_warehouse.values():
        model.add_variable(var)
    for var in ship.values():
        model.add_variable(var)

    # Objective: Minimize total cost (fixed + shipping)
    cost_expr = LinearExpression()

    # Fixed costs
    for warehouse in WAREHOUSES:
        var = open_warehouse[warehouse.id]
        cost_expr.add_term(var, warehouse.fixed_cost)

    # Shipping costs
    for warehouse in WAREHOUSES:
        for customer in CUSTOMERS:
            var = ship[(warehouse.id, customer.id)]
            cost = shipping_cost(warehouse, customer)
            cost_expr.add_term(var, cost)

    model.minimize(cost_expr)

    # Constraint 1: Satisfy customer demand
    # For each customer: sum(ship[w, c] over all w) >= demand[c]
    for customer in CUSTOMERS:
        demand_expr = LinearExpression()
        for warehouse in WAREHOUSES:
            var = ship[(warehouse.id, customer.id)]
            demand_expr.add_term(var, 1.0)

        model.add_constraint(
            Constraint(f"demand_{customer.name}")
            .expression(demand_expr)
            .ge()
            .rhs(customer.demand)
        )

    # Constraint 2: Warehouse capacity
    # For each warehouse: sum(ship[w, c] over all c) <= capacity[w] * open[w]
    # This is a conditional constraint: can't ship if not open
    for warehouse in WAREHOUSES:
        capacity_expr = LinearExpression()
        for customer in CUSTOMERS:
            var = ship[(warehouse.id, customer.id)]
            capacity_expr.add_term(var, 1.0)

        # Add term: -capacity * open
        open_var = open_warehouse[warehouse.id]
        capacity_expr.add_term(open_var, -warehouse.capacity)

        model.add_constraint(
            Constraint(f"capacity_{warehouse.name}").expression(capacity_expr).le().rhs(0)
        )

    # Constraint 3: Big-M - Can only ship from open warehouses
    # ship[w, c] <= M * open[w]
    for warehouse in WAREHOUSES:
        for customer in CUSTOMERS:
            bigm_expr = LinearExpression()
            ship_var = ship[(warehouse.id, customer.id)]
            open_var = open_warehouse[warehouse.id]

            bigm_expr.add_term(ship_var, 1.0)
            bigm_expr.add_term(open_var, -BIG_M)

            model.add_constraint(
                Constraint(f"bigm_{warehouse.name}_{customer.name}")
                .expression(bigm_expr)
                .le()
                .rhs(0)
            )

    return model


# ==================== SOLUTION DISPLAY ====================


def display_solution(model: Model):
    """Display the optimization results (when solver is implemented)."""

    print("\n" + "=" * 70)
    print("SOLUTION")
    print("=" * 70)

    # This is what you'll do when solvers are implemented:
    """
    optimizer = Optimizer()
    solution = optimizer.solve(model)

    if solution.is_optimal():
        print(f"Status: {solution.status}")
        print(f"Total Cost: ${solution.objective_value:,.2f}")

        # Calculate cost breakdown
        fixed_cost = sum(
            solution.variables[f"open_{w.name}"] * w.fixed_cost
            for w in WAREHOUSES
        )
        shipping_cost_total = solution.objective_value - fixed_cost

        print(f"  Fixed Costs: ${fixed_cost:,.2f}")
        print(f"  Shipping Costs: ${shipping_cost_total:,.2f}")
        print()

        # Show which warehouses are open
        print("Open Warehouses:")
        print("-" * 70)
        for warehouse in WAREHOUSES:
            is_open = solution.variables[f"open_{warehouse.name}"]
            if is_open > 0.5:  # Binary variable
                # Count customers served
                customers_served = sum(
                    1 for c in CUSTOMERS
                    if solution.variables[f"ship_{warehouse.name}_to_{c.name}"] > 0.01
                )
                print(f"  {warehouse.name}: Serving {customers_served} customers "
                      f"(fixed cost: ${warehouse.fixed_cost:,.2f})")

        # Show shipping plan
        print("\nShipping Plan:")
        print("-" * 70)
        for warehouse in WAREHOUSES:
            is_open = solution.variables[f"open_{warehouse.name}"]
            if is_open < 0.5:
                continue

            for customer in CUSTOMERS:
                qty = solution.variables[f"ship_{warehouse.name}_to_{customer.name}"]
                if qty > 0.01:
                    cost = shipping_cost(warehouse, customer) * qty
                    print(f"  {warehouse.name} → {customer.name}: {qty:.1f} units "
                          f"(${cost:.2f})")
    else:
        print(f"No optimal solution found. Status: {solution.status}")
    """

    print("\nNOTE: Solver implementations not yet complete.")
    print("Above shows how binary variables and fixed costs work.")


# ==================== MAIN ====================


def main():
    """Run the facility location optimization."""

    print("=" * 70)
    print("OptiXNG Example: Facility Location Problem")
    print("=" * 70)
    print()
    print("This example demonstrates:")
    print("  ✓ Binary decision variables (open/close)")
    print("  ✓ Fixed costs")
    print("  ✓ Continuous flow variables (shipping)")
    print("  ✓ Big-M constraints")
    print("  ✓ Mixed-integer programming")
    print()

    # Display problem data
    print("Potential Warehouses:")
    print("-" * 70)
    for w in WAREHOUSES:
        print(
            f"  {w.name:25s}: Fixed cost ${w.fixed_cost:,}, "
            f"Capacity {w.capacity} units"
        )
    print()

    print("Customers:")
    print("-" * 70)
    for c in CUSTOMERS:
        print(f"  {c.name:15s}: Demand {c.demand} units")
    print()

    total_demand = sum(c.demand for c in CUSTOMERS)
    total_capacity = sum(w.capacity for w in WAREHOUSES)
    print(f"Total Demand: {total_demand} units")
    print(f"Total Capacity: {total_capacity} units")
    print()

    # Build model
    print("Building optimization model...")
    model = build_facility_location_model()
    print(model.summary())

    # Display would-be solution
    display_solution(model)

    print()
    print("Key Concepts:")
    print("  - Binary variables: open[w] ∈ {0, 1}")
    print("  - Fixed costs: pay once if open")
    print("  - Big-M: ship[w,c] ≤ M × open[w] (can't ship if not open)")
    print("  - Mixed-integer: Some variables binary, some continuous")


if __name__ == "__main__":
    main()
