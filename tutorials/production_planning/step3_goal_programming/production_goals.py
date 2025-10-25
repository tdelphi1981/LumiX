"""Production Planning with Goal Programming using SQLAlchemy ORM.

This example extends Step 2 by adding customer orders as soft constraints (goals).
Customer orders have priorities based on customer tier (Gold/Silver/Bronze), and
the optimization tries to satisfy high-priority orders first while still maximizing
profit and respecting hard constraints (capacity, materials).

Key Concepts:
    - Hard constraints: MUST be satisfied (capacity, materials)
    - Soft goals: SHOULD be satisfied, but can be violated (customer orders)
    - Priority levels: Gold > Silver > Bronze customers
    - Goal programming: Minimize goal violations weighted by priority

Mathematical Formulation:
    Decision Variables:
        production[p] ≥ 0  (continuous, units to produce)

    Objective:
        Maximize: profit - weighted_goal_violations

    Hard Constraints:
        - Machine capacity: Σ (hours × production) ≤ available_hours
        - Material availability: Σ (material × production) ≤ available_material

    Soft Goals (Customer Orders):
        - production[p] ≥ target_quantity (goal, can be violated)
        - Priority: 1 (Gold), 2 (Silver), 3 (Bronze)
        - Weight: Based on priority level

Prerequisites:
    Before running this script, populate the database:

    >>> python sample_data.py

Learning Objectives:
    1. How to use goal programming with LumiX
    2. How to model soft constraints vs hard constraints
    3. Priority-based optimization
    4. Customer order fulfillment analysis
"""

from lumix import (
    LXModel,
    LXVariable,
    LXLinearExpression,
    LXConstraint,
    LXOptimizer,
)
from database import (
    init_database,
    get_session,
    Product,
    Machine,
    RawMaterial,
    Customer,
    CustomerOrder,
    ProductionSchedule,
    create_cached_machine_hours_checker,
    create_cached_material_requirement_checker,
)

solver_to_use = "ortools"


def build_production_model_with_goals(session) -> LXModel:
    """Build production model with goal programming for customer orders using ORM.

    This function demonstrates LumiX's goal programming feature integrated with
    SQLAlchemy ORM. Data is queried directly from the database on-demand without
    pre-loading into lists (True ORM pattern).

    Args:
        session: SQLAlchemy Session instance

    Returns:
        LXModel with hard constraints and soft goals
    """
    print("\nBuilding production model with goal programming (ORM)...")

    # Create cached checkers for efficient lookups
    get_hours = create_cached_machine_hours_checker(session)
    get_material_qty = create_cached_material_requirement_checker(session)

    # ========================================================================
    # Decision Variables
    # ========================================================================

    print("  Creating decision variables...")

    # Decision variable: production[product]
    # LumiX queries the database directly using from_model()
    production = (
        LXVariable[Product, float]("production")
        .continuous()
        .bounds(lower=0)  # Global lower bound (non-negative production)
        .indexed_by(lambda p: p.id)
        .from_model(Product, session)
    )

    # Report data counts (query count only for reporting)
    print(f"    Created {session.query(Product).count()} continuous variables")

    # ========================================================================
    # Objective: Maximize Profit
    # ========================================================================

    print("  Defining objective function (maximize profit)...")
    profit_expr = LXLinearExpression().add_multi_term(
        production,
        coeff=lambda p: p.profit_per_unit
    )

    model = LXModel("production_planning_goals_orm")
    model.add_variable(production)
    model.maximize(profit_expr)
    print("    Objective: Maximize total profit")

    # ========================================================================
    # Hard Constraints
    # ========================================================================

    print("  Adding hard constraints (MUST satisfy)...")

    # Max Demand Constraints (customer orders become soft goals instead of min demand)
    print("    - Maximum demand constraints")
    demand_constraints = 0

    # Query products directly from database
    for product in session.query(Product).all():
        # Maximum demand constraint: production[p] <= max_demand
        max_expr = LXLinearExpression().add_multi_term(
            production,
            coeff=lambda p, current_product=product: 1.0 if p.id == current_product.id else 0.0
        )
        model.add_constraint(
            LXConstraint(f"max_demand_{product.name.replace(' ', '_')}")
            .expression(max_expr)
            .le()
            .rhs(product.max_demand)
        )
        demand_constraints += 1

    print(f"      Added {demand_constraints} maximum demand constraints")

    # Machine Capacity Constraints
    print("    - Machine capacity constraints")
    machine_constraints = 0

    # Query machines directly from database
    for machine in session.query(Machine).all():
        machine_hours_expr = LXLinearExpression().add_multi_term(
            production,
            coeff=lambda p, m=machine: get_hours(p.id, m.id)
        )

        model.add_constraint(
            LXConstraint(f"machine_capacity_{machine.name.replace(' ', '_')}")
            .expression(machine_hours_expr)
            .le()
            .rhs(machine.available_hours)
        )
        machine_constraints += 1

    print(f"      Added {machine_constraints} machine capacity constraints")

    # Material Availability Constraints
    print("    - Material availability constraints")
    material_constraints = 0

    # Query materials directly from database
    for material in session.query(RawMaterial).all():
        material_usage_expr = LXLinearExpression().add_multi_term(
            production,
            coeff=lambda p, mat=material: get_material_qty(p.id, mat.id)
        )

        model.add_constraint(
            LXConstraint(f"material_{material.name.replace(' ', '_').replace('(', '').replace(')', '')}")
            .expression(material_usage_expr)
            .le()
            .rhs(material.available_quantity)
        )
        material_constraints += 1

    print(f"      Added {material_constraints} material availability constraints")

    # ========================================================================
    # Soft Goals: Customer Orders (CAN be violated)
    # ========================================================================

    print("\n  Adding soft goal constraints (SHOULD satisfy)...")
    goals_added = 0

    # Create lookups for efficient access (avoid repeated database queries)
    products_dict = {p.id: p for p in session.query(Product).all()}
    customers_dict = {c.id: c for c in session.query(Customer).all()}

    # Query customer orders directly from database
    for order in session.query(CustomerOrder).all():
        # Find the product for this order using lookup
        product = products_dict.get(order.product_id)
        if not product:
            continue

        # Get customer info using lookup
        customer = customers_dict.get(order.customer_id)
        if not customer:
            continue

        # Goal: production[product] ≥ target_quantity
        # This is a soft constraint - we want to meet it, but can violate if necessary
        order_expr = LXLinearExpression().add_multi_term(
            production,
            coeff=lambda p, current_product=product: 1.0 if p.id == current_product.id else 0.0
        )

        # Add as goal constraint with priority
        model.add_constraint(
            LXConstraint(f"order_{order.id}_{customer.name.replace(' ', '_')}")
            .expression(order_expr)
            .ge()
            .rhs(order.target_quantity)
            .as_goal(priority=order.priority, weight=1.0)  # Mark as goal
        )
        goals_added += 1

        print(f"    [P{order.priority}] {customer.tier}: {order.target_quantity} {product.name}s for {customer.name}")

    print(f"\n  Added {goals_added} goal constraints")

    # ========================================================================
    # Summary
    # ========================================================================

    total_hard = demand_constraints + machine_constraints + material_constraints

    print(f"\nModel built successfully!")
    print(f"  Variables: {session.query(Product).count()} continuous")
    print(f"  Hard constraints: {total_hard}")
    print(f"    - Maximum demand: {demand_constraints}")
    print(f"    - Machine capacity: {machine_constraints}")
    print(f"    - Material availability: {material_constraints}")
    print(f"  Soft goals: {goals_added}")

    return model


def analyze_goal_satisfaction(session, solution):
    """Analyze which customer orders were satisfied using ORM.

    Args:
        session: SQLAlchemy Session instance
        solution: Solved LXSolution object
    """
    print(f"\n{'=' * 80}")
    print("GOAL SATISFACTION ANALYSIS")
    print(f"{'=' * 80}\n")

    # Create lookups for efficient access (avoid repeated database queries)
    products_dict = {p.id: p for p in session.query(Product).all()}
    customers_dict = {c.id: c for c in session.query(Customer).all()}

    # Group orders by priority
    orders_by_priority = {}
    # Query customer orders directly from database
    for order in session.query(CustomerOrder).all():
        if order.priority not in orders_by_priority:
            orders_by_priority[order.priority] = []
        orders_by_priority[order.priority].append(order)

    # Analyze each priority level (standard GP: 1=highest, 3=lowest)
    for priority in sorted(orders_by_priority.keys()):  # Low to high (1, 2, 3)
        tier_name = "GOLD" if priority == 1 else "SILVER" if priority == 2 else "BRONZE"
        print(f"Priority {priority} ({tier_name} customers):")
        print("-" * 80)

        orders = orders_by_priority[priority]
        satisfied_count = 0

        for order in orders:
            product = products_dict.get(order.product_id)
            if not product:
                continue

            # Get customer info using lookup
            customer = customers_dict.get(order.customer_id)
            if not customer:
                continue

            actual_production = solution.variables["production"][product.id]

            # Check if order is satisfied (within tolerance)
            satisfied = actual_production >= order.target_quantity - 0.01
            shortfall = max(0, order.target_quantity - actual_production)

            if satisfied:
                status = "✓ SATISFIED"
                satisfied_count += 1
            else:
                status = "✗ NOT SATISFIED"

            print(f"  {status}: {customer.name}")
            print(f"    Order: {order.target_quantity} {product.name}s")
            print(f"    Actual: {actual_production:.2f} {product.name}s")
            if not satisfied:
                print(f"    Shortfall: {shortfall:.2f} units")
            print()

        print(f"Priority {priority} Summary: {satisfied_count}/{len(orders)} orders satisfied\n")

    print(f"{'=' * 80}\n")


def display_solution(session, solution):
    """Display solution by querying data directly from database."""
    print(f"{'=' * 80}")
    print("PRODUCTION PLAN (with Goal Programming)")
    print(f"{'=' * 80}")
    print(f"Status: {solution.status}")
    print(f"Total Profit: ${solution.objective_value:,.2f}")
    print()

    # Create cached helpers
    get_hours = create_cached_machine_hours_checker(session)
    get_material_qty = create_cached_material_requirement_checker(session)

    # Production Quantities
    print("PRODUCTION QUANTITIES:")
    print("-" * 80)
    print(f"{'Product':<20} {'Quantity':<15} {'Profit/Unit':<15} {'Total Profit':<15}")
    print("-" * 80)

    production_values = {}
    # Query products directly from database
    for product in session.query(Product).all():
        quantity = solution.variables["production"][product.id]
        production_values[product.id] = quantity
        total_profit = quantity * product.profit_per_unit
        print(f"{product.name:<20} {quantity:<15.2f} ${product.profit_per_unit:<14.2f} ${total_profit:<14.2f}")

    print("-" * 80)
    print(f"{'TOTAL':<20} {'':<15} {'':<15} ${solution.objective_value:<14,.2f}")
    print()

    # Machine Utilization
    print("MACHINE UTILIZATION:")
    print("-" * 80)
    print(f"{'Machine':<25} {'Hours Used':<15} {'Available':<15} {'Utilization':<15}")
    print("-" * 80)

    # Query machines directly from database
    for machine in session.query(Machine).all():
        hours_used = 0.0
        for product_id, quantity in production_values.items():
            hours_required = get_hours(product_id, machine.id)
            hours_used += quantity * hours_required

        utilization = (hours_used / machine.available_hours) * 100 if machine.available_hours > 0 else 0
        print(f"{machine.name:<25} {hours_used:<15.2f} {machine.available_hours:<15.2f} {utilization:<14.1f}%")

    print()

    # Material Consumption
    print("MATERIAL CONSUMPTION:")
    print("-" * 80)
    print(f"{'Material':<30} {'Used':<15} {'Available':<15} {'Remaining':<15}")
    print("-" * 80)

    # Query materials directly from database
    for material in session.query(RawMaterial).all():
        used = 0.0
        for product_id, quantity in production_values.items():
            material_required = get_material_qty(product_id, material.id)
            used += quantity * material_required

        remaining = material.available_quantity - used
        print(f"{material.name:<30} {used:<15.2f} {material.available_quantity:<15.2f} {remaining:<15.2f}")

    print()


def save_solution_to_database(session, solution):
    """Save optimization solution to database using ORM.

    Args:
        session: SQLAlchemy Session instance
        solution: LXSolution object
    """
    if not solution.is_optimal() and not solution.is_feasible():
        return

    # Clear previous solutions
    session.query(ProductionSchedule).delete()

    # Save production quantities
    schedules = []
    # Query products directly from database
    for product in session.query(Product).all():
        quantity = solution.variables["production"][product.id]
        profit_contribution = quantity * product.profit_per_unit

        schedule = ProductionSchedule(
            product_id=product.id,
            quantity=quantity,
            profit_contribution=profit_contribution
        )
        schedules.append(schedule)

    session.add_all(schedules)
    session.commit()


def main():
    """Run the ORM-integrated production planning with goal programming."""
    print("=" * 80)
    print("LumiX Tutorial: Manufacturing Production Planning - Step 3")
    print("=" * 80)
    print("\nThis example demonstrates:")
    print("  ✓ Goal programming with customer orders (ORM-based)")
    print("  ✓ Priority-based optimization (customer tier determines priority)")
    print("  ✓ Mixed hard constraints + soft goals")
    print("  ✓ Order fulfillment analysis")
    print("  ✓ True ORM pattern - queries database directly without pre-loading")

    # Initialize database and create session
    engine = init_database("sqlite:///production.db")
    session = get_session(engine)

    try:
        # Verify database is populated (query count only, no loading)
        print("\nVerifying database...")
        if session.query(Product).count() == 0 or session.query(CustomerOrder).count() == 0:
            print("\n❌ Database is empty! Please run sample_data.py first:")
            print("   python sample_data.py")
            return

        print(f"  Found {session.query(Product).count()} products")
        print(f"  Found {session.query(Machine).count()} machines")
        print(f"  Found {session.query(RawMaterial).count()} materials")
        print(f"  Found {session.query(Customer).count()} customers")
        print(f"  Found {session.query(CustomerOrder).count()} customer orders")

        # Build model with goals (queries database directly)
        model = build_production_model_with_goals(session)

        # Enable goal programming
        print("\nPreparing goal programming...")
        model.set_goal_mode("weighted")  # Weighted sum approach
        model.prepare_goal_programming()  # CRITICAL: Must call before solving
        print("  ✓ Goal programming enabled")

        # Solve
        print(f"\nSolving with {solver_to_use}...")
        optimizer = LXOptimizer().use_solver(solver_to_use)
        solution = optimizer.solve(model)

        # Display solution (queries database directly)
        display_solution(session, solution)

        # Analyze goal satisfaction (queries database directly)
        analyze_goal_satisfaction(session, solution)

        # Save solution (queries database directly)
        save_solution_to_database(session, solution)

        print("=" * 80)
        print("Tutorial Step 3 Complete!")
        print("=" * 80)
        print("\nWhat's new in Step 3:")
        print("  → Customer orders as soft goal constraints")
        print("  → Priority levels based on customer tier (Gold/Silver/Bronze)")
        print("  → Goal programming: minimize order violations")
        print("  → Comprehensive goal satisfaction analysis")
        print("  → True ORM pattern - database queried on-demand")
        print("\nKey Insights:")
        print("  • High-priority customers' orders are prioritized")
        print("  • Hard constraints always satisfied (capacity, materials)")
        print("  • Soft goals minimized based on priority")
        print("  • Trade-offs visible in satisfaction report")
        print("\nNext Steps:")
        print("  → Step 4: Large-scale multi-period planning with setup costs")

    finally:
        session.close()


if __name__ == "__main__":
    main()
