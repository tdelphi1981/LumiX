"""
Multi-Priority Weighted Goal Programming Example
=================================================

Demonstrates advanced goal programming features:
- Multiple priority levels (P1, P2, P3)
- Custom weights within priorities
- Indexed goal constraints
- Different constraint types (LE, GE, EQ)
- Custom objective terms (priority 0)

Problem:
--------
Supply chain planning with multiple conflicting goals:
- Priority 0: Maximize profit (custom objective)
- Priority 1: Meet customer demands (highest priority)
- Priority 2: Control inventory levels
- Priority 3: Minimize transportation costs

The weighted mode converts priorities to exponentially different weights
(P1 = 10^6, P2 = 10^5, P3 = 10^4) to ensure higher priorities dominate.
"""

from dataclasses import dataclass
from typing import List

from lumix import (
    LXConstraint,
    LXLinearExpression,
    LXModel,
    LXOptimizer,
    LXVariable,
)


# Data Models
@dataclass
class Customer:
    """Customer with demand requirements."""

    id: int
    name: str
    demand: float
    revenue_per_unit: float


@dataclass
class Warehouse:
    """Warehouse with inventory constraints."""

    id: int
    name: str
    capacity: float
    target_inventory: float  # Ideal inventory level
    holding_cost: float  # Cost per unit


# Sample Data
CUSTOMERS = [
    Customer(id=1, name="Customer A", demand=100, revenue_per_unit=50),
    Customer(id=2, name="Customer B", demand=150, revenue_per_unit=45),
    Customer(id=3, name="Customer C", demand=80, revenue_per_unit=55),
]

WAREHOUSES = [
    Warehouse(id=1, name="Warehouse 1", capacity=200, target_inventory=100, holding_cost=2.0),
    Warehouse(id=2, name="Warehouse 2", capacity=150, target_inventory=75, holding_cost=1.5),
]

# Costs
TRANSPORT_COST_PER_UNIT = 5.0
TARGET_TOTAL_TRANSPORT_COST = 1000.0

solver_to_use = "gurobi"


def main():
    """Run multi-priority weighted goal programming example."""
    print("=" * 80)
    print("Multi-Priority Weighted Goal Programming Example")
    print("=" * 80)

    # Define variables
    shipment = (
        LXVariable[Customer, float]("shipment")
        .continuous()
        .bounds(lower=0)
        .indexed_by(lambda c: c.id)
        .from_data(CUSTOMERS)
    )

    inventory = (
        LXVariable[Warehouse, float]("inventory")
        .continuous()
        .bounds(lower=0)
        .indexed_by(lambda w: w.id)
        .from_data(WAREHOUSES)
    )

    # Build model
    model = LXModel("supply_chain_goals")
    model.add_variables(shipment, inventory)

    # Hard constraint: Warehouse capacity limits
    for warehouse in WAREHOUSES:
        inv_expr = LXLinearExpression()
        inv_expr.add_term(
            inventory,
            coeff=lambda w, wh=warehouse: 1.0 if w.id == wh.id else 0.0
        )

        model.add_constraint(
            LXConstraint(f"capacity_{warehouse.id}")
            .expression(inv_expr)
            .le()
            .rhs(warehouse.capacity)
        )

    # Priority 0: Maximize profit (custom objective as goal)
    # This will be included in the objective function
    revenue_expr = LXLinearExpression()
    revenue_expr.add_term(shipment, lambda c: c.revenue_per_unit)

    holding_cost_expr = LXLinearExpression()
    holding_cost_expr.add_term(inventory, lambda w: -w.holding_cost)

    profit_expr = LXLinearExpression()
    profit_expr.terms = revenue_expr.terms.copy()
    for var_name, term in holding_cost_expr.terms.items():
        profit_expr.terms[var_name] = term

    model.add_constraint(
        LXConstraint("maximize_profit")
        .expression(profit_expr)
        .ge()
        .rhs(0)  # Want to maximize, so any positive value is good
        .as_goal(priority=0, weight=1.0)  # Custom objective
    )

    # Priority 1: Meet customer demands (HIGHEST PRIORITY)
    # shipment >= demand for each customer
    for customer in CUSTOMERS:
        ship_expr = LXLinearExpression()
        ship_expr.add_term(
            shipment,
            coeff=lambda c, cust=customer: 1.0 if c.id == cust.id else 0.0
        )

        # Higher weight for high-revenue customers
        weight = customer.revenue_per_unit / 50.0  # Normalize to ~1.0

        model.add_constraint(
            LXConstraint(f"demand_{customer.id}")
            .expression(ship_expr)
            .ge()
            .rhs(customer.demand)
            .as_goal(priority=1, weight=weight)  # Highest priority with custom weights
        )

    # Priority 2: Maintain target inventory levels
    # inventory == target_inventory for each warehouse
    for warehouse in WAREHOUSES:
        inv_expr = LXLinearExpression()
        inv_expr.add_term(
            inventory,
            coeff=lambda w, wh=warehouse: 1.0 if w.id == wh.id else 0.0
        )

        model.add_constraint(
            LXConstraint(f"inventory_target_{warehouse.id}")
            .expression(inv_expr)
            .eq()  # Equality goal - both over and under are bad
            .rhs(warehouse.target_inventory)
            .as_goal(priority=2, weight=1.0)  # Medium priority
        )

    # Priority 3: Control transportation costs
    # total_transport_cost <= target
    transport_expr = LXLinearExpression()
    transport_expr.add_term(shipment, coeff=TRANSPORT_COST_PER_UNIT)

    model.add_constraint(
        LXConstraint("transport_cost")
        .expression(transport_expr)
        .le()
        .rhs(TARGET_TOTAL_TRANSPORT_COST)
        .as_goal(priority=3, weight=1.0)  # Lowest priority
    )

    # Set goal programming mode
    model.set_goal_mode("weighted")
    model.prepare_goal_programming()

    print("\nModel Summary:")
    print(model.summary())
    print(f"\nTotal constraints: {len(model.constraints)}")
    print(f"Total variables: {len(model.variables)}")

    # Solve
    print("\nSolving...")
    optimizer = LXOptimizer().use_solver(solver_to_use)
    solution = optimizer.solve(model)

    # Display results
    print("\n" + "=" * 80)
    print("Solution")
    print("=" * 80)
    print(solution.summary())

    # Shipment plan
    print("\n" + "-" * 80)
    print("Shipment Plan:")
    print("-" * 80)
    print(f"{'Customer':<20} {'Demand':>10} {'Shipped':>10} {'Status':>15}")
    print("-" * 80)

    for customer in CUSTOMERS:
        shipped = solution.get_mapped(shipment).get(customer.id, 0)
        status = "✓" if shipped >= customer.demand - 1e-6 else "✗ Short"
        print(
            f"{customer.name:<20} {customer.demand:>10.2f} {shipped:>10.2f} {status:>15}"
        )

    # Inventory levels
    print("\n" + "-" * 80)
    print("Inventory Levels:")
    print("-" * 80)
    print(f"{'Warehouse':<20} {'Target':>10} {'Actual':>10} {'Deviation':>12}")
    print("-" * 80)

    for warehouse in WAREHOUSES:
        inv_level = solution.get_mapped(inventory).get(warehouse.id, 0)
        deviation = inv_level - warehouse.target_inventory
        print(
            f"{warehouse.name:<20} {warehouse.target_inventory:>10.2f} "
            f"{inv_level:>10.2f} {deviation:>+12.2f}"
        )

    # Cost analysis
    print("\n" + "-" * 80)
    print("Cost Analysis:")
    print("-" * 80)

    total_transport = sum(
        solution.get_mapped(shipment).get(c.id, 0) * TRANSPORT_COST_PER_UNIT
        for c in CUSTOMERS
    )
    total_holding = sum(
        solution.get_mapped(inventory).get(w.id, 0) * w.holding_cost
        for w in WAREHOUSES
    )
    total_revenue = sum(
        solution.get_mapped(shipment).get(c.id, 0) * c.revenue_per_unit
        for c in CUSTOMERS
    )
    total_profit = total_revenue - total_holding

    print(f"Total Revenue:          ${total_revenue:>10.2f}")
    print(f"Total Holding Cost:     ${total_holding:>10.2f}")
    print(f"Total Transport Cost:   ${total_transport:>10.2f}")
    print(f"Total Profit:           ${total_profit:>10.2f}")

    # Goal satisfaction by priority
    print("\n" + "=" * 80)
    print("Goal Satisfaction by Priority")
    print("=" * 80)

    # Priority 0
    print("\nPriority 0 (Custom Objective - Maximize Profit):")
    print("-" * 80)
    deviations = solution.get_goal_deviations("maximize_profit")
    if deviations:
        print(f"Profit achieved: ${total_profit:.2f}")

    # Priority 1
    print("\nPriority 1 (Meet Customer Demands):")
    print("-" * 80)
    satisfied_p1 = 0
    total_p1 = 0

    for customer in CUSTOMERS:
        goal_name = f"demand_{customer.id}"
        deviations = solution.get_goal_deviations(goal_name)
        if deviations:
            total_p1 += 1

            # Extract deviation values (indexed by goal ID)
            neg_dev_dict = deviations.get("neg", {})
            goal_id = f"{goal_name}_{customer.id}"
            neg_dev = neg_dev_dict.get(goal_id, 0) if isinstance(neg_dev_dict, dict) else neg_dev_dict

            satisfied = solution.is_goal_satisfied(goal_name, tolerance=1e-6)
            if satisfied:
                satisfied_p1 += 1
            status = "✓" if satisfied else "✗"
            print(f"{status} {customer.name}: Shortfall = {neg_dev:.2f} units")

    print(f"\nP1 Goals Satisfied: {satisfied_p1}/{total_p1}")

    # Priority 2
    print("\nPriority 2 (Inventory Targets):")
    print("-" * 80)
    satisfied_p2 = 0
    total_p2 = 0

    for warehouse in WAREHOUSES:
        goal_name = f"inventory_target_{warehouse.id}"
        deviations = solution.get_goal_deviations(goal_name)
        if deviations:
            total_p2 += 1

            # Extract deviation values (indexed by goal ID)
            neg_dev_dict = deviations.get("neg", {})
            pos_dev_dict = deviations.get("pos", {})
            goal_id = f"{goal_name}_{warehouse.id}"
            neg_dev = neg_dev_dict.get(goal_id, 0) if isinstance(neg_dev_dict, dict) else neg_dev_dict
            pos_dev = pos_dev_dict.get(goal_id, 0) if isinstance(pos_dev_dict, dict) else pos_dev_dict

            satisfied = solution.is_goal_satisfied(goal_name, tolerance=1e-6)
            if satisfied:
                satisfied_p2 += 1
            status = "✓" if satisfied else "✗"
            print(
                f"{status} {warehouse.name}: "
                f"Under = {neg_dev:.2f}, Over = {pos_dev:.2f}"
            )

    print(f"\nP2 Goals Satisfied: {satisfied_p2}/{total_p2}")

    # Priority 3
    print("\nPriority 3 (Transportation Cost Limit):")
    print("-" * 80)
    deviations = solution.get_goal_deviations("transport_cost")
    if deviations:
        # Extract deviation value (non-indexed goal has single entry)
        pos_dev_dict = deviations.get("pos", {})
        goal_id = "transport_cost"
        pos_dev = pos_dev_dict.get(goal_id, 0) if isinstance(pos_dev_dict, dict) else pos_dev_dict

        satisfied = solution.is_goal_satisfied("transport_cost", tolerance=1e-6)
        status = "✓" if satisfied else "✗"
        print(
            f"{status} Transport Cost: "
            f"Target = ${TARGET_TOTAL_TRANSPORT_COST:.2f}, "
            f"Actual = ${total_transport:.2f}, "
            f"Excess = ${pos_dev:.2f}"
        )

    print("\n" + "=" * 80)
    print("\nNote: Higher priorities (P1) dominate lower priorities (P2, P3)")
    print("due to exponential weight scaling (P1=10^6, P2=10^5, P3=10^4)")
    print("=" * 80)


if __name__ == "__main__":
    main()
