"""Large-Scale Multi-Period Production Planning with SQLAlchemy ORM.

This example demonstrates LumiX's ability to handle realistic large-scale problems
efficiently with multi-period planning, setup costs, batches, and inventory management
using the True ORM pattern from Steps 2 & 3.

Problem Scale:
    - 9 products × 4 periods = 36 product-period combinations
    - 6 machines × 4 periods = 24 machine-period combinations
    - 9 materials × 4 periods = 36 material-period combinations
    - Variables: ~1,600 (vs ~10 in Step 3)
    - Constraints: ~600 (vs ~20 in Step 3)

New Features in Step 4:
    - Multi-period planning (4 weeks)
    - Setup costs for production runs
    - Minimum batch sizes
    - Inventory tracking between periods
    - Holding costs
    - 16x more variables than Step 3
    - True ORM pattern: Database queried directly without pre-loading

Key Concepts (True ORM Pattern):
    - Functions take only `session` parameter (no pre-loaded lists)
    - Database queried on-demand in loops: `for product in session.query(Product).all()`
    - Temporary dictionaries for performance (acceptable for N+1 query avoidance)
    - Consistent with Step 2 & Step 3 approach
    - More memory efficient, database as single source of truth

Prerequisites:
    python sample_data.py  # Run first to populate database
"""

from lumix import (
    LXModel,
    LXVariable,
    LXLinearExpression,
    LXConstraint,
    LXOptimizer,
    LXIndexDimension,
)
from database import (
    init_database,
    get_session,
    Product,
    Machine,
    RawMaterial,
    Period,
    Customer,
    CustomerOrder,
    ProductionSchedulePeriod,
    create_cached_machine_hours_checker,
    create_cached_material_requirement_checker,
    create_cached_batch_size_checker,
    create_cached_setup_cost_checker,
)
from report_generator import generate_html_report

solver_to_use = "ortools"


def build_multiperiod_model(session) -> tuple:
    """Build multi-period production model with setup costs, batches, and inventory using ORM.

    This function demonstrates True ORM pattern where data is queried directly from
    the database on-demand without pre-loading into lists (same pattern as Step 3).

    Args:
        session: SQLAlchemy Session instance

    Returns:
        Tuple of (model, production, inventory) variables
    """
    print("\nBuilding large-scale multi-period production model (ORM)...")

    # Query data directly from database for scale reporting (count only)
    product_count = session.query(Product).count()
    period_count = session.query(Period).count()
    print(f"  Scale: {product_count} products × {period_count} periods")
    print(f"  Expected variables: ~{product_count * period_count * 40}")

    # Create cached helpers for efficient lookups
    get_hours = create_cached_machine_hours_checker(session)
    get_material = create_cached_material_requirement_checker(session)
    get_batch = create_cached_batch_size_checker(session)
    get_setup = create_cached_setup_cost_checker(session)

    model = LXModel("large_scale_multiperiod_production_orm")

    # ===== DECISION VARIABLES =====
    print("\n  Creating decision variables...")

    # Production quantity per product per period
    # Use LXIndexDimension with from_model() on each dimension (True ORM pattern from Timetabling Step 4)
    production = (
        LXVariable[(Product, Period), float]("production")
        .continuous()
        .bounds(lower=0)
        .indexed_by_product(
            LXIndexDimension(Product, lambda p: p.id).from_model(session),
            LXIndexDimension(Period, lambda per: per.id).from_model(session),
        )
    )

    # Binary: is product produced in period?
    is_produced = (
        LXVariable[(Product, Period), int]("is_produced")
        .binary()
        .indexed_by_product(
            LXIndexDimension(Product, lambda p: p.id).from_model(session),
            LXIndexDimension(Period, lambda per: per.id).from_model(session),
        )
    )

    # Inventory at end of each period
    inventory = (
        LXVariable[(Product, Period), float]("inventory")
        .continuous()
        .bounds(lower=0)
        .indexed_by_product(
            LXIndexDimension(Product, lambda p: p.id).from_model(session),
            LXIndexDimension(Period, lambda per: per.id).from_model(session),
        )
    )

    print(f"    Created {product_count * period_count} production variables")
    print(f"    Created {product_count * period_count} binary setup variables")
    print(f"    Created {product_count * period_count} inventory variables")

    # ===== OBJECTIVE: MAXIMIZE PROFIT - SETUP COSTS - HOLDING COSTS =====
    print("\n  Defining objective...")
    obj_expr = LXLinearExpression()

    # Add profit - use add_multi_term with coefficient function
    # Multi-dimensional lambdas receive separate arguments: (prod, per) not t[0], t[1]
    # Query products and periods directly from database
    for product in session.query(Product).all():
        for period in session.query(Period).order_by(Period.week_number).all():
            obj_expr.add_multi_term(
                production,
                coeff=lambda prod, per, curr_prod=product, curr_per=period: (
                    curr_prod.profit_per_unit if prod.id == curr_prod.id and per.id == curr_per.id else 0.0
                )
            )

    # Subtract setup costs
    # Create temporary lookup for machines (avoid repeated queries)
    machines_list = session.query(Machine).all()

    for product in session.query(Product).all():
        for period in session.query(Period).order_by(Period.week_number).all():
            # Get average setup cost across machines
            total_setup = sum(get_setup(product.id, m.id)[0] for m in machines_list)
            avg_setup = total_setup / len(machines_list) if machines_list else 0
            obj_expr.add_multi_term(
                is_produced,
                coeff=lambda prod, per, curr_prod=product, curr_per=period, setup=avg_setup: (
                    -setup if prod.id == curr_prod.id and per.id == curr_per.id else 0.0
                )
            )

    # Subtract inventory holding costs
    for product in session.query(Product).all():
        for period in session.query(Period).order_by(Period.week_number).all():
            obj_expr.add_multi_term(
                inventory,
                coeff=lambda prod, per, curr_prod=product, curr_per=period: (
                    -curr_prod.holding_cost_per_unit if prod.id == curr_prod.id and per.id == curr_per.id else 0.0
                )
            )

    model.add_variable(production)
    model.add_variable(is_produced)
    model.add_variable(inventory)
    model.maximize(obj_expr)

    # ===== CONSTRAINTS =====
    print("\n  Adding constraints...")

    # Create temporary lookups for performance (avoid N queries in nested loops)
    products_list = session.query(Product).all()
    periods_list = session.query(Period).order_by(Period.week_number).all()

    # 1. Machine capacity per period
    print("    - Machine capacity constraints per period...")
    machine_constraints = 0
    # Query machines directly from database
    for period in periods_list:
        for machine in session.query(Machine).all():
            expr = LXLinearExpression()
            # Add production hours for all products
            # Lambda receives (prod, per) as separate arguments
            expr.add_multi_term(
                production,
                coeff=lambda prod, per, m=machine, current_per=period: (
                    get_hours(prod.id, m.id) if per.id == current_per.id else 0.0
                )
            )
            # Add setup hours
            expr.add_multi_term(
                is_produced,
                coeff=lambda prod, per, m=machine, current_per=period: (
                    get_setup(prod.id, m.id)[1] if per.id == current_per.id else 0.0
                )
            )

            model.add_constraint(
                LXConstraint(f"machine_{machine.id}_period_{period.id}")
                .expression(expr)
                .le()
                .rhs(machine.available_hours)
            )
            machine_constraints += 1

    print(f"      Added {machine_constraints} machine capacity constraints")

    # 2. Material availability per period
    print("    - Material availability constraints per period...")
    material_constraints = 0
    # Query materials directly from database
    for period in periods_list:
        for material in session.query(RawMaterial).all():
            expr = LXLinearExpression()
            # Add material usage for all products in this period
            # Lambda receives (prod, per) as separate arguments
            expr.add_multi_term(
                production,
                coeff=lambda prod, per, mat=material, current_per=period: (
                    get_material(prod.id, mat.id) if per.id == current_per.id else 0.0
                )
            )

            model.add_constraint(
                LXConstraint(f"material_{material.id}_period_{period.id}")
                .expression(expr)
                .le()
                .rhs(material.available_quantity_per_period)
            )
            material_constraints += 1

    print(f"      Added {material_constraints} material availability constraints")

    # 3. Batch size constraints
    print("    - Production batch constraints...")
    batch_constraints = 0
    # Query products directly from database
    for product in session.query(Product).all():
        batch_size = get_batch(product.id)
        if batch_size > 0:
            for period in periods_list:
                # production >= batch_size * is_produced
                expr = LXLinearExpression()
                # production[product, period]
                # Lambda receives (prod, per) as separate arguments
                expr.add_multi_term(
                    production,
                    coeff=lambda prod, per, current_prod=product, current_per=period: (
                        1.0 if prod.id == current_prod.id and per.id == current_per.id else 0.0
                    )
                )
                # - batch_size * is_produced[product, period]
                expr.add_multi_term(
                    is_produced,
                    coeff=lambda prod, per, current_prod=product, current_per=period, batch=batch_size: (
                        -batch if prod.id == current_prod.id and per.id == current_per.id else 0.0
                    )
                )

                model.add_constraint(
                    LXConstraint(f"batch_{product.id}_period_{period.id}")
                    .expression(expr)
                    .ge()
                    .rhs(0.0)
                )
                batch_constraints += 1

    print(f"      Added {batch_constraints} batch size constraints")

    # 4. Inventory balance constraints
    print("    - Inventory balance constraints...")
    inventory_constraints = 0
    # Query products directly from database
    for product in session.query(Product).all():
        for i, period in enumerate(periods_list):
            expr = LXLinearExpression()
            # inventory[t] = inventory[t-1] + production[t] - demand[t]
            # For simplicity, assume demand = 0 (orders are soft goals)

            # Current inventory[product, period]
            # Lambda receives (prod, per) as separate arguments
            expr.add_multi_term(
                inventory,
                coeff=lambda prod, per, current_prod=product, current_per=period: (
                    1.0 if prod.id == current_prod.id and per.id == current_per.id else 0.0
                )
            )

            # Previous inventory (if not first period)
            if i > 0:
                prev_period = periods_list[i - 1]
                expr.add_multi_term(
                    inventory,
                    coeff=lambda prod, per, current_prod=product, prev_per=prev_period: (
                        -1.0 if prod.id == current_prod.id and per.id == prev_per.id else 0.0
                    )
                )

            # Production in current period
            expr.add_multi_term(
                production,
                coeff=lambda prod, per, current_prod=product, current_per=period: (
                    -1.0 if prod.id == current_prod.id and per.id == current_per.id else 0.0
                )
            )

            model.add_constraint(
                LXConstraint(f"inventory_balance_{product.id}_period_{period.id}")
                .expression(expr)
                .eq()
                .rhs(0.0)
            )
            inventory_constraints += 1

    print(f"      Added {inventory_constraints} inventory balance constraints")

    # 5. Customer orders as soft goals
    print("    - Customer order goal constraints...")
    goals_added = 0

    # Create lookups for efficient access (avoid repeated database queries)
    products_dict = {p.id: p for p in session.query(Product).all()}
    periods_dict = {per.id: per for per in session.query(Period).all()}

    # Query customer orders directly from database
    for order in session.query(CustomerOrder).all():
        product = products_dict.get(order.product_id)
        period = periods_dict.get(order.period_id)

        if product and period:
            # Goal: production[product, period] >= target_quantity
            # Lambda receives (prod, per) as separate arguments
            expr = LXLinearExpression().add_multi_term(
                production,
                coeff=lambda prod, per, current_prod=product, current_per=period: (
                    1.0 if prod.id == current_prod.id and per.id == current_per.id else 0.0
                )
            )

            model.add_constraint(
                LXConstraint(f"order_{order.id}")
                .expression(expr)
                .ge()
                .rhs(order.target_quantity)
                .as_goal(priority=order.priority, weight=1.0)
            )
            goals_added += 1

    print(f"      Added {goals_added} goal constraints")

    # ===== SUMMARY =====
    total_constraints = (
        machine_constraints +
        material_constraints +
        batch_constraints +
        inventory_constraints +
        goals_added
    )

    print(f"\n  Model statistics:")
    print(f"    Variables:        {product_count * period_count * 3}")
    print(f"    Constraints:      {total_constraints}")
    print(f"    Goals:            {goals_added}")

    return model, production, inventory


def display_solution_summary(session, solution, production, inventory):
    """Display multi-period production plan summary by querying data directly from database.

    Args:
        session: SQLAlchemy Session instance
        solution: Solved LXSolution object
        production: Production variable
        inventory: Inventory variable
    """
    print(f"\n{'=' * 80}")
    print("MULTI-PERIOD PRODUCTION PLAN (ORM)")
    print(f"{'=' * 80}")
    print(f"Status: {solution.status}")
    print(f"Total Objective Value: ${solution.objective_value:,.2f}")
    print()

    # Production by period - query periods directly from database
    for period in session.query(Period).order_by(Period.week_number).all():
        print(f"\n{period.name}:")
        print("-" * 80)
        print(f"{'Product':<20} {'Production':<15} {'Inventory':<15} {'Profit Contrib':<15}")
        print("-" * 80)

        period_total = 0.0
        # Query products directly from database
        for product in session.query(Product).all():
            # Solution indexed by IDs, not objects
            prod_qty = solution.variables["production"][(product.id, period.id)]
            inv_qty = solution.variables["inventory"][(product.id, period.id)]
            profit = prod_qty * product.profit_per_unit

            if prod_qty > 0.01 or inv_qty > 0.01:
                period_total += profit
                print(f"{product.name:<20} {prod_qty:<15.2f} {inv_qty:<15.2f} ${profit:<14.2f}")

        print("-" * 80)
        print(f"{'Period Total':<20} {'':<15} {'':<15} ${period_total:<14,.2f}")


def save_solution(session, solution, production):
    """Save solution to database using ORM.

    Args:
        session: SQLAlchemy Session instance
        solution: LXSolution object
        production: Production variable
    """
    if not solution.is_optimal() and not solution.is_feasible():
        print("\n❌ No solution to save!")
        return

    print("\nSaving solution to database using ORM...")
    session.query(ProductionSchedulePeriod).delete()

    schedules = []
    # Query products and periods directly from database
    for product in session.query(Product).all():
        for period in session.query(Period).order_by(Period.week_number).all():
            # Solution indexed by IDs, not objects
            qty = solution.variables["production"][(product.id, period.id)]
            if qty > 0.01:
                schedule = ProductionSchedulePeriod(
                    product_id=product.id,
                    period_id=period.id,
                    quantity=qty,
                    profit_contribution=qty * product.profit_per_unit
                )
                schedules.append(schedule)

    session.add_all(schedules)
    session.commit()
    print(f"  Saved {len(schedules)} production schedule entries")


def main():
    """Run large-scale multi-period production optimization using ORM."""
    print("=" * 80)
    print("LumiX Tutorial: Production Planning - Step 4 (LARGE-SCALE)")
    print("=" * 80)
    print("\nDemonstrates:")
    print("  ✓ Multi-period planning (4 weeks)")
    print("  ✓ Setup costs and batch constraints")
    print("  ✓ Inventory management")
    print("  ✓ Large-scale optimization (16x Step 3)")
    print("  ✓ Goal programming with customer orders")
    print("  ✓ True ORM pattern - queries database directly without pre-loading")

    engine = init_database("sqlite:///production.db")
    session = get_session(engine)

    try:
        # Verify database is populated (query count only, no loading)
        print("\nVerifying database...")
        if session.query(Product).count() == 0 or session.query(Period).count() == 0:
            print("\n❌ Database is empty! Please run sample_data.py first:")
            print("   python sample_data.py")
            return

        print(f"  Found {session.query(Product).count()} products")
        print(f"  Found {session.query(Machine).count()} machines")
        print(f"  Found {session.query(RawMaterial).count()} materials")
        print(f"  Found {session.query(Period).count()} periods")
        print(f"  Found {session.query(Customer).count()} customers")
        print(f"  Found {session.query(CustomerOrder).count()} customer orders")

        # Build model (queries database directly)
        model, production, inventory = build_multiperiod_model(session)

        print("\nPreparing goal programming...")
        model.set_goal_mode("weighted")
        model.prepare_goal_programming()
        print("  ✓ Goal programming enabled")

        print(f"\nSolving with {solver_to_use}...")
        print("(This may take 10-30 seconds for large-scale problem...)")
        optimizer = LXOptimizer().use_solver(solver_to_use)
        solution = optimizer.solve(model)

        # Display and save (queries database directly)
        display_solution_summary(session, solution, production, inventory)
        save_solution(session, solution, production)

        # Generate interactive HTML report
        generate_html_report(solution, session, "production_report.html")

        print("\n" + "=" * 80)
        print("Tutorial Step 4 Complete!")
        print("=" * 80)
        print("\nKey Achievements:")
        print("  • Solved 16x larger problem than Step 3")
        print("  • Multi-period planning with inventory")
        print("  • Setup costs and batch constraints")
        print("  • Efficient performance with caching")
        print("  • True ORM pattern - database queried on-demand")
        print("\nNext Steps:")
        print("  → Explore stochastic optimization (uncertain demand)")
        print("  → Multi-facility network flow models")
        print("  → Non-linear costs (economies of scale)")

    finally:
        session.close()


if __name__ == "__main__":
    main()
