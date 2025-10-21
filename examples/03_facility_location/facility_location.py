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

from lumix import (
    LXConstraint,
    LXIndexDimension,
    LXLinearExpression,
    LXModel,
    LXOptimizer,
    LXVariable,
)

from sample_data import (
    BIG_M,
    CUSTOMERS,
    WAREHOUSES,
    Customer,
    Warehouse,
    shipping_cost,
)


solver_to_use = "ortools"

# ==================== MODEL BUILDING ====================


def build_facility_location_model() -> LXModel:
    """Build the facility location optimization model."""

    # Decision Variable 1: Binary - Open warehouse or not
    open_warehouse = (
        LXVariable[Warehouse, int]("open_warehouse")
        .binary()
        .indexed_by(lambda w: w.id)
        .from_data(WAREHOUSES)
    )

    # Decision Variable 2: Continuous - Shipping quantities
    # Multi-indexed by (Warehouse, Customer) using cartesian product
    ship = (
        LXVariable[Tuple[Warehouse, Customer], float]("ship")
        .continuous()
        .indexed_by_product(
            LXIndexDimension(Warehouse, lambda w: w.id).from_data(WAREHOUSES),
            LXIndexDimension(Customer, lambda c: c.id).from_data(CUSTOMERS),
        )
        .bounds(lower=0, upper=max(c.demand for c in CUSTOMERS))  # Upper bound needed for CP-SAT
    )

    # Create model
    model = LXModel("facility_location").add_variables(open_warehouse, ship)

    # Objective: Minimize total cost (fixed + shipping)
    cost_expr = (
        LXLinearExpression()
        .add_term(open_warehouse, coeff=lambda w: w.fixed_cost)  # Fixed costs
        .add_multi_term(ship, coeff=lambda w, c: shipping_cost(w, c))  # Shipping costs
    )
    model.minimize(cost_expr)

    # Constraint 1: Satisfy customer demand
    # For each customer: sum(ship[w, c] over all w) >= demand[c]
    for customer in CUSTOMERS:
        demand_expr = LXLinearExpression().add_multi_term(
            ship,
            coeff=lambda w, c: 1.0,
            where=lambda w, c, cust=customer: c.id == cust.id,
        )
        model.add_constraint(
            LXConstraint(f"demand_{customer.name}")
            .expression(demand_expr)
            .ge()
            .rhs(customer.demand)
        )

    # Constraint 2: Warehouse capacity
    # For each warehouse: sum(ship[w, c] over all c) <= capacity[w] * open[w]
    # This is a conditional constraint: can't ship if not open
    for warehouse in WAREHOUSES:
        capacity_expr = (
            LXLinearExpression()
            .add_multi_term(
                ship,
                coeff=lambda w, c: 1.0,
                where=lambda w, c, wh=warehouse: w.id == wh.id,
            )
            .add_term(
                open_warehouse,
                coeff=lambda w, wh=warehouse: -wh.capacity if w.id == wh.id else 0,
            )
        )
        model.add_constraint(
            LXConstraint(f"capacity_{warehouse.name}").expression(capacity_expr).le().rhs(0)
        )

    # Constraint 3: Big-M - Can only ship from open warehouses
    # ship[w, c] <= M * open[w]
    for warehouse in WAREHOUSES:
        for customer in CUSTOMERS:
            bigm_expr = (
                LXLinearExpression()
                .add_multi_term(
                    ship,
                    coeff=lambda w, c: 1.0,
                    where=lambda w, c, wh=warehouse, cu=customer: w.id == wh.id and c.id == cu.id,
                )
                .add_term(
                    open_warehouse,
                    coeff=lambda w, wh=warehouse: -BIG_M if w.id == wh.id else 0,
                )
            )
            model.add_constraint(
                LXConstraint(f"bigm_{warehouse.name}_{customer.name}")
                .expression(bigm_expr)
                .le()
                .rhs(0)
            )

    return model


# ==================== SOLUTION DISPLAY ====================


def display_solution(model: LXModel):
    """Display the optimization results."""

    print("\n" + "=" * 70)
    print("SOLUTION")
    print("=" * 70)

    # Note: This problem uses irrational shipping costs (haversine formula), which are
    # problematic for CP-SAT. Use CPLEX, Gurobi, or OR-Tools LP instead for best results.
    optimizer = LXOptimizer().use_solver(solver_to_use)
    solution = optimizer.solve(model)

    if solution.is_optimal():
        print(f"Status: {solution.status}")
        print(f"Total Cost: ${solution.objective_value:,.2f}")

        # Calculate cost breakdown
        fixed_cost = sum(
            solution.variables["open_warehouse"][w.id] * w.fixed_cost
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
            is_open = solution.variables["open_warehouse"][warehouse.id]
            if is_open > 0.5:  # Binary variable
                # Count customers served
                customers_served = sum(
                    1 for c in CUSTOMERS
                    if solution.variables["ship"].get((warehouse.id, c.id), 0) > 0.01
                )
                print(f"  {warehouse.name}: Serving {customers_served} customers "
                      f"(fixed cost: ${warehouse.fixed_cost:,.2f})")

        # Show shipping plan
        print("\nShipping Plan:")
        print("-" * 70)
        for warehouse in WAREHOUSES:
            is_open = solution.variables["open_warehouse"][warehouse.id]
            if is_open < 0.5:
                continue

            for customer in CUSTOMERS:
                qty = solution.variables["ship"].get((warehouse.id, customer.id), 0)
                if qty > 0.01:
                    cost = shipping_cost(warehouse, customer) * qty
                    print(f"  {warehouse.name} → {customer.name}: {qty:.1f} units "
                          f"(${cost:.2f})")
    else:
        print(f"No optimal solution found. Status: {solution.status}")


# ==================== MAIN ====================


def main():
    """Run the facility location optimization."""

    print("=" * 70)
    print("LumiX Example: Facility Location Problem")
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
