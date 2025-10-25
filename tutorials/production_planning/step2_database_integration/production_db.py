"""Production Planning with SQLAlchemy ORM Integration.

This example extends Step 1 by integrating SQLAlchemy ORM for data storage
and demonstrates LumiX's `from_model()` method for direct ORM integration.

Problem Description:
    Same as Step 1 - determine optimal production quantities to maximize profit
    while respecting machine capacity, material availability, and demand constraints.
    The key difference is ORM integration:
        - SQLAlchemy declarative models instead of raw SQL
        - LumiX queries database directly using `from_model(session)`
        - Type-safe database operations with IDE support
        - Solution saved back to database using ORM

Key Features Demonstrated:
    - **ORM Integration**: SQLAlchemy declarative models
    - **from_model() usage**: LumiX queries database directly
    - **Type Safety**: IDE autocomplete for model attributes
    - **Solution Persistence**: Save results using ORM session
    - **Session Management**: Proper database transaction handling

Prerequisites:
    Before running this script, populate the database:

    >>> python sample_data.py

Learning Objectives:
    1. How to use LumiX's `from_model()` with SQLAlchemy
    2. How LumiX integrates with ORM sessions
    3. How to persist optimization solutions via ORM
    4. Type-safe database operations
    5. Performance optimization with cached helpers
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
    ProductionSchedule,
    ResourceUtilization,
    create_cached_machine_hours_checker,
    create_cached_material_requirement_checker,
)

solver_to_use = "ortools"


def build_production_model(session) -> LXModel:
    """Build production model using ORM and from_model().

    This function demonstrates LumiX's ORM integration. Instead of manually
    querying the database and using from_data(), we use from_model(session)
    to let LumiX query the database directly.

    Args:
        session: SQLAlchemy Session instance

    Returns:
        An LXModel instance ready to be solved
    """
    print("\nBuilding production planning model with ORM integration...")
    print("  Using LumiX's from_model() for direct database querying")

    # Create cached checkers for efficient lookups (avoids redundant DB queries)
    get_hours = create_cached_machine_hours_checker(session)
    get_material_qty = create_cached_material_requirement_checker(session)

    # ========== DECISION VARIABLES ==========
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
    print(f"  Loaded {session.query(Machine).count()} machines")
    print(f"  Loaded {session.query(RawMaterial).count()} materials")

    # ========== OBJECTIVE: MAXIMIZE PROFIT ==========
    print("  Defining objective function...")
    profit_expr = LXLinearExpression().add_multi_term(
        production,
        coeff=lambda p: p.profit_per_unit
    )

    model = LXModel("production_planning_orm")
    model.add_variable(production)
    model.maximize(profit_expr)
    print("    Objective: Maximize total profit")

    # ========== HARD CONSTRAINTS ==========
    print("  Adding hard constraints...")

    # Demand Constraints (min/max production per product)
    print("    - Demand constraints")
    demand_constraints = 0

    # Query products directly from database
    for product in session.query(Product).all():
        # Minimum demand constraint: production[p] >= min_demand
        if product.min_demand > 0:
            min_expr = LXLinearExpression().add_multi_term(
                production,
                coeff=lambda p, current_product=product: 1.0 if p.id == current_product.id else 0.0
            )
            model.add_constraint(
                LXConstraint(f"min_demand_{product.name.replace(' ', '_')}")
                .expression(min_expr)
                .ge()
                .rhs(product.min_demand)
            )
            demand_constraints += 1

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

    print(f"      Added {demand_constraints} demand constraints")

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

    print(f"\nModel built successfully!")
    print(f"  Variables: {session.query(Product).count()}")
    print(f"  Constraints: {demand_constraints + machine_constraints + material_constraints}")

    return model


def save_solution_to_database(session, solution):
    """Save optimization solution to database using ORM.

    Extracts production quantities and resource utilization from the solution
    and stores them in the database using SQLAlchemy ORM. Queries data directly
    from the database on-demand without pre-loading into lists.

    Args:
        session: SQLAlchemy Session instance
        solution: LXSolution object
    """
    if not solution.is_optimal() and not solution.is_feasible():
        print("\n❌ No solution to save!")
        return

    print("\nSaving solution to database using ORM...")

    # Create cached helpers for efficient lookups
    get_hours = create_cached_machine_hours_checker(session)
    get_material_qty = create_cached_material_requirement_checker(session)

    # Clear previous solutions
    session.query(ResourceUtilization).delete()
    session.query(ProductionSchedule).delete()

    # Save production quantities
    production_saved = 0
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
        production_saved += 1

    session.add_all(schedules)
    print(f"  Saved {production_saved} production schedule entries")

    # Save machine utilization
    machine_util_saved = 0
    machine_utils = []
    # Query machines directly from database
    for machine in session.query(Machine).all():
        hours_used = 0.0
        # Query products for each machine
        for product in session.query(Product).all():
            quantity = solution.variables["production"][product.id]
            hours_required = get_hours(product.id, machine.id)
            hours_used += quantity * hours_required

        utilization_pct = (hours_used / machine.available_hours * 100) if machine.available_hours > 0 else 0.0

        util = ResourceUtilization(
            resource_type="machine",
            resource_id=machine.id,
            resource_name=machine.name,
            used=hours_used,
            available=machine.available_hours,
            utilization_pct=utilization_pct
        )
        machine_utils.append(util)
        machine_util_saved += 1

    session.add_all(machine_utils)
    print(f"  Saved {machine_util_saved} machine utilization records")

    # Save material consumption
    material_util_saved = 0
    material_utils = []
    # Query materials directly from database
    for material in session.query(RawMaterial).all():
        used = 0.0
        # Query products for each material
        for product in session.query(Product).all():
            quantity = solution.variables["production"][product.id]
            material_required = get_material_qty(product.id, material.id)
            used += quantity * material_required

        utilization_pct = (used / material.available_quantity * 100) if material.available_quantity > 0 else 0.0

        util = ResourceUtilization(
            resource_type="material",
            resource_id=material.id,
            resource_name=material.name,
            used=used,
            available=material.available_quantity,
            utilization_pct=utilization_pct
        )
        material_utils.append(util)
        material_util_saved += 1

    session.add_all(material_utils)
    print(f"  Saved {material_util_saved} material utilization records")

    session.commit()


def display_solution(session, solution):
    """Display the complete solution by querying data directly from database."""
    if not solution.is_optimal() and not solution.is_feasible():
        print("\n❌ No feasible solution found!")
        return

    print(f"\n{'=' * 80}")
    print("PRODUCTION PLAN (ORM-based)")
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


def main():
    """Run the ORM-integrated production planning example."""
    print("=" * 80)
    print("LumiX Tutorial: Manufacturing Production Planning - Step 2")
    print("=" * 80)
    print("\nThis example demonstrates:")
    print("  ✓ SQLAlchemy ORM declarative models")
    print("  ✓ LumiX's from_model(session) for direct database querying")
    print("  ✓ Type-safe ORM operations with IDE support")
    print("  ✓ Saving solutions using ORM session")
    print("  ✓ Performance optimization with cached helpers")

    # Initialize database and create session
    engine = init_database("sqlite:///production.db")
    session = get_session(engine)

    try:
        # Verify database is populated (query count only, no loading)
        print("\nVerifying database...")
        if session.query(Product).count() == 0:
            print("\n❌ Database is empty! Please run sample_data.py first:")
            print("   python sample_data.py")
            return

        print(f"  Found {session.query(Product).count()} products")
        print(f"  Found {session.query(Machine).count()} machines")
        print(f"  Found {session.query(RawMaterial).count()} materials")

        # Build and solve model (queries database directly)
        model = build_production_model(session)
        optimizer = LXOptimizer().use_solver(solver_to_use)

        print(f"\nSolving with {solver_to_use}...")
        solution = optimizer.solve(model)

        # Display results (queries database directly)
        display_solution(session, solution)

        # Save solution to database using ORM (queries database directly)
        save_solution_to_database(session, solution)

        print("\n" + "=" * 80)
        print("Tutorial Step 2 Complete!")
        print("=" * 80)
        print("\nWhat changed from Step 1:")
        print("  → SQLAlchemy ORM models instead of Python lists")
        print("  → from_model(session) instead of from_data()")
        print("  → LumiX queries database directly")
        print("  → Type-safe ORM operations")
        print("\nORM Benefits:")
        print("  ✓ No manual SQL queries")
        print("  ✓ IDE autocomplete for model attributes")
        print("  ✓ Automatic foreign key validation")
        print("  ✓ Type-safe database operations")
        print("\nNext Steps:")
        print("  → Step 3: Add customer orders with goal programming")

    finally:
        session.close()


if __name__ == "__main__":
    main()
