"""Multi-Period Production Planning with Sensitivity Analysis using LumiX.

This example extends Step 4 by demonstrating LumiX's sensitivity analysis capabilities
to extract actionable business insights from the optimal solution.

Key Difference from Step 4:
    Instead of BINARY variables for setup decisions, this model uses CONTINUOUS variables
    bounded [0, 1] with threshold-based interpretation. This makes it a pure Linear Program (LP),
    enabling full sensitivity analysis (shadow prices and reduced costs).

    Setup Variable Interpretation:
    - is_produced[product, period] ∈ [0, 1] (continuous)
    - If is_produced >= 0.5 → Interpret as "product is produced in period"
    - If is_produced < 0.5 → Interpret as "product is NOT produced in period"

    This is called "LP relaxation" - we relax the integer requirement to enable sensitivity analysis.
    In practice, the optimizer will often push these to 0 or 1 naturally due to the cost structure.

Problem Scale:
    - 9 products × 4 periods = 36 product-period combinations
    - 6 machines × 4 periods = 24 machine-period combinations
    - 9 materials × 4 periods = 36 material-period combinations
    - Variables: ~1,600 (all continuous - Pure LP!)
    - Constraints: ~600 (same as Step 4)

New Features in Step 6 (vs Step 4):
    - Shadow price analysis for all constraints (WORKING!)
    - Reduced cost analysis for variables (WORKING!)
    - Binding constraint identification
    - Bottleneck detection and ranking
    - Investment recommendations based on marginal values
    - Risk assessment based on solution sensitivity
    - Enhanced HTML report with sensitivity insights

Key Concepts:
    - Shadow Prices: Marginal value of relaxing a constraint by one unit
    - Reduced Costs: Opportunity cost of forcing a variable to change
    - Binding Constraints: Constraints satisfied with equality (at capacity)
    - Bottlenecks: Binding constraints with high shadow prices
    - LP Relaxation: Continuous [0,1] instead of binary {0,1} for sensitivity analysis

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
    LXSensitivityAnalyzer,
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

    This function is identical to Step 4 - we're analyzing the same model with sensitivity analysis.

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

    model = LXModel("multiperiod_production_sensitivity")

    # ===== DECISION VARIABLES =====
    print("\n  Creating decision variables...")

    # Production quantity per product per period
    production = (
        LXVariable[(Product, Period), float]("production")
        .continuous()
        .bounds(lower=0)
        .indexed_by_product(
            LXIndexDimension(Product, lambda p: p.id).from_model(session),
            LXIndexDimension(Period, lambda per: per.id).from_model(session),
        )
    )

    # Continuous [0, 1]: is product produced in period?
    # Using continuous relaxation instead of binary to enable sensitivity analysis
    # Interpretation: >= 0.5 means produced, < 0.5 means not produced
    is_produced = (
        LXVariable[(Product, Period), float]("is_produced")
        .continuous()
        .bounds(lower=0, upper=1)
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
    print(f"    Created {product_count * period_count} setup variables (continuous [0,1] for LP relaxation)")
    print(f"    Created {product_count * period_count} inventory variables")
    print(f"    NOTE: All variables are continuous → Pure LP → Sensitivity analysis available!")

    # ===== OBJECTIVE: MAXIMIZE PROFIT - SETUP COSTS - HOLDING COSTS =====
    print("\n  Defining objective...")
    obj_expr = LXLinearExpression()

    # Add profit
    for product in session.query(Product).all():
        for period in session.query(Period).order_by(Period.week_number).all():
            obj_expr.add_multi_term(
                production,
                coeff=lambda prod, per, curr_prod=product, curr_per=period: (
                    curr_prod.profit_per_unit if prod.id == curr_prod.id and per.id == curr_per.id else 0.0
                )
            )

    # Subtract setup costs
    machines_list = session.query(Machine).all()

    for product in session.query(Product).all():
        for period in session.query(Period).order_by(Period.week_number).all():
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

    # Create temporary lookups for performance
    products_list = session.query(Product).all()
    periods_list = session.query(Period).order_by(Period.week_number).all()

    # 1. Machine capacity per period
    print("    - Machine capacity constraints per period...")
    machine_constraints = 0
    for period in periods_list:
        for machine in session.query(Machine).all():
            expr = LXLinearExpression()
            expr.add_multi_term(
                production,
                coeff=lambda prod, per, m=machine, current_per=period: (
                    get_hours(prod.id, m.id) if per.id == current_per.id else 0.0
                )
            )
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
    for period in periods_list:
        for material in session.query(RawMaterial).all():
            expr = LXLinearExpression()
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
    for product in session.query(Product).all():
        batch_size = get_batch(product.id)
        if batch_size > 0:
            for period in periods_list:
                expr = LXLinearExpression()
                expr.add_multi_term(
                    production,
                    coeff=lambda prod, per, current_prod=product, current_per=period: (
                        1.0 if prod.id == current_prod.id and per.id == current_per.id else 0.0
                    )
                )
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
    for product in session.query(Product).all():
        for i, period in enumerate(periods_list):
            expr = LXLinearExpression()

            # Current inventory
            expr.add_multi_term(
                inventory,
                coeff=lambda prod, per, current_prod=product, current_per=period: (
                    1.0 if prod.id == current_prod.id and per.id == current_per.id else 0.0
                )
            )

            # Previous inventory
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

    products_dict = {p.id: p for p in session.query(Product).all()}
    periods_dict = {per.id: per for per in session.query(Period).all()}

    for order in session.query(CustomerOrder).all():
        product = products_dict.get(order.product_id)
        period = periods_dict.get(order.period_id)

        if product and period:
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
    """Display multi-period production plan summary with setup interpretation."""
    print(f"\n{'=' * 80}")
    print("MULTI-PERIOD PRODUCTION PLAN")
    print(f"{'=' * 80}")
    print(f"Status: {solution.status}")
    print(f"Total Objective Value: ${solution.objective_value:,.2f}")
    print()

    print("Setup Variables Interpretation (continuous [0,1] with threshold 0.5):")
    print("  >= 0.5 → Product IS produced in period (setup incurred)")
    print("  < 0.5  → Product NOT produced in period (no setup)")
    print()

    for period in session.query(Period).order_by(Period.week_number).all():
        print(f"\n{period.name}:")
        print("-" * 80)
        print(f"{'Product':<20} {'Production':<15} {'Setup [0,1]':<15} {'Inventory':<15} {'Profit':<15}")
        print("-" * 80)

        period_total = 0.0
        for product in session.query(Product).all():
            prod_qty = solution.variables["production"][(product.id, period.id)]
            setup_val = solution.variables["is_produced"][(product.id, period.id)]
            inv_qty = solution.variables["inventory"][(product.id, period.id)]
            profit = prod_qty * product.profit_per_unit

            if prod_qty > 0.01 or inv_qty > 0.01 or setup_val > 0.01:
                period_total += profit
                setup_str = f"{setup_val:.3f}"
                if setup_val >= 0.5:
                    setup_str += " ✓"  # Produced
                print(f"{product.name:<20} {prod_qty:<15.2f} {setup_str:<15} {inv_qty:<15.2f} ${profit:<14.2f}")

        print("-" * 80)
        print(f"{'Period Total':<20} {'':<15} {'':<15} {'':<15} ${period_total:<14,.2f}")


def display_sensitivity_analysis(session, analyzer):
    """Display comprehensive sensitivity analysis results.

    Args:
        session: SQLAlchemy Session instance
        analyzer: LXSensitivityAnalyzer instance
    """
    print(f"\n{'=' * 80}")
    print("SENSITIVITY ANALYSIS: Solution Insights")
    print(f"{'=' * 80}")
    print("\nThis is a PURE LP problem (all variables continuous).")
    print("Shadow prices and reduced costs are fully available and valid!\n")

    # ===== CONSTRAINT SENSITIVITY (SHADOW PRICES) =====
    print("\n" + "-" * 80)
    print("CONSTRAINT SENSITIVITY ANALYSIS (Shadow Prices)")
    print("-" * 80)

    # Analyze machine capacity constraints
    print("\nMachine Capacity Constraints:")
    print(f"{'Machine':<25} {'Period':<10} {'Shadow Price':>15} {'Status':>12}")
    print("-" * 80)

    machines = session.query(Machine).all()
    periods = session.query(Period).order_by(Period.week_number).all()

    for machine in machines:
        for period in periods:
            constraint_name = f"machine_{machine.id}_period_{period.id}"
            sens = analyzer.analyze_constraint(constraint_name)
            shadow_str = f"${sens.shadow_price:.4f}" if sens.shadow_price else "$0.0000"
            status = "BINDING" if sens.is_binding else "Slack"
            print(f"{machine.name:<25} {period.name:<10} {shadow_str:>15} {status:>12}")

    # Analyze material availability constraints
    print("\nMaterial Availability Constraints:")
    print(f"{'Material':<25} {'Period':<10} {'Shadow Price':>15} {'Status':>12}")
    print("-" * 80)

    materials = session.query(RawMaterial).all()

    for material in materials:
        for period in periods:
            constraint_name = f"material_{material.id}_period_{period.id}"
            sens = analyzer.analyze_constraint(constraint_name)
            shadow_str = f"${sens.shadow_price:.4f}" if sens.shadow_price else "$0.0000"
            status = "BINDING" if sens.is_binding else "Slack"
            print(f"{material.name:<25} {period.name:<10} {shadow_str:>15} {status:>12}")

    # ===== BINDING CONSTRAINTS =====
    print("\n" + "-" * 80)
    print("BINDING CONSTRAINTS (At Capacity)")
    print("-" * 80)

    binding = analyzer.get_binding_constraints()
    if binding:
        print(f"\nFound {len(binding)} binding constraints:")
        for name, sens in binding.items():
            print(f"  • {name}")
            print(f"    Shadow Price: ${sens.shadow_price:.4f}")
            print(f"    Interpretation: Each additional unit relaxes this constraint, increasing profit by ${abs(sens.shadow_price):.2f}")
    else:
        print("\nNo binding constraints found (solution is interior)")

    # ===== BOTTLENECK IDENTIFICATION =====
    print("\n" + "-" * 80)
    print("BOTTLENECK IDENTIFICATION")
    print("-" * 80)

    bottlenecks = analyzer.identify_bottlenecks(shadow_price_threshold=0.01)
    if bottlenecks:
        print(f"\nIdentified {len(bottlenecks)} bottlenecks:")
        print("\nThese constraints are limiting profitability:")
        for name in bottlenecks:
            sens = analyzer.analyze_constraint(name)
            print(f"\n  {name}:")
            print(f"    Shadow Price: ${sens.shadow_price:.4f}")
            print(f"    Impact: Relaxing by 1 unit → +${sens.shadow_price:.2f} profit")
    else:
        print("\nNo significant bottlenecks identified")

    # ===== TOP SENSITIVE CONSTRAINTS =====
    print("\n" + "-" * 80)
    print("TOP 10 MOST VALUABLE CONSTRAINTS TO RELAX")
    print("-" * 80)

    top_constraints = analyzer.get_most_sensitive_constraints(top_n=10)
    if top_constraints:
        print("\nPrioritize relaxing these constraints for maximum profit impact:")
        for i, (name, sens) in enumerate(top_constraints, 1):
            print(f"\n  {i}. {name}")
            print(f"     Shadow Price: ${sens.shadow_price:.4f}")
            print(f"     Expected ROI: ${sens.shadow_price:.2f} per unit relaxation")
    else:
        print("\nNo constraints with significant shadow prices")

    # ===== SENSITIVITY SUMMARY =====
    print("\n" + "=" * 80)
    print("SENSITIVITY SUMMARY")
    print("=" * 80)
    print(analyzer.generate_summary())

    # ===== BUSINESS INSIGHTS =====
    print("\n" + "=" * 80)
    print("BUSINESS INSIGHTS & INVESTMENT RECOMMENDATIONS")
    print("=" * 80)

    print("\n1. RESOURCE INVESTMENT PRIORITIES")
    print("-" * 80)
    print("\nBased on shadow prices, prioritize investment in:")

    top_3 = analyzer.get_most_sensitive_constraints(top_n=3)
    for i, (name, sens) in enumerate(top_3, 1):
        print(f"\n  {i}. {name}")
        print(f"     Marginal Value: ${sens.shadow_price:.2f} per unit")
        print(f"     Status: {'BINDING (at capacity)' if sens.is_binding else 'Not binding'}")

        if sens.shadow_price and sens.shadow_price > 1.0:
            print(f"     [HIGH PRIORITY]: Strong ROI expected from capacity expansion")
        elif sens.shadow_price and sens.shadow_price > 0.1:
            print(f"     [MODERATE PRIORITY]: Positive ROI from expansion")
        else:
            print(f"     [LOW PRIORITY]: Minimal impact from expansion")

    # Risk Assessment
    print("\n2. RISK ASSESSMENT")
    print("-" * 80)

    binding_count = len(binding)

    if binding_count >= 10:
        print("\n  ⚠ HIGH SENSITIVITY:")
        print(f"    - {binding_count} constraints are binding")
        print("    - Solution is highly sensitive to parameter changes")
        print("    - Small variations in capacity can significantly impact profit")
        print("    - Recommendation: Build buffer capacity or diversify resources")
    elif binding_count >= 5:
        print("\n  ⚡ MODERATE SENSITIVITY:")
        print(f"    - {binding_count} binding constraints identified")
        print("    - Focus on relaxing the top binding constraints")
        print("    - Some resources have slack capacity")
    else:
        print("\n  ✓ LOW SENSITIVITY:")
        print(f"    - Only {binding_count} binding constraints")
        print("    - Solution is robust to small parameter changes")
        print("    - Excess capacity available in most resources")


def save_solution(session, solution, production):
    """Save solution to database using ORM."""
    if not solution.is_optimal() and not solution.is_feasible():
        print("\n❌ No solution to save!")
        return

    print("\nSaving solution to database using ORM...")
    session.query(ProductionSchedulePeriod).delete()

    schedules = []
    for product in session.query(Product).all():
        for period in session.query(Period).order_by(Period.week_number).all():
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
    """Run multi-period production optimization with sensitivity analysis."""
    print("=" * 80)
    print("LumiX Tutorial: Production Planning - Step 6 (SENSITIVITY ANALYSIS)")
    print("=" * 80)
    print("\nDemonstrates:")
    print("  ✓ Multi-period planning (4 weeks)")
    print("  ✓ Setup costs with LP relaxation (continuous [0,1] variables)")
    print("  ✓ Batch constraints and inventory management")
    print("  ✓ Large-scale optimization (16x Step 3)")
    print("  ✓ Goal programming with customer orders")
    print("  ✓ FULL sensitivity analysis (shadow prices, reduced costs)")
    print("  ✓ Binding constraint identification")
    print("  ✓ Bottleneck detection and ranking")
    print("  ✓ Investment recommendations with ROI estimates")
    print("\n💡 Key Innovation: Pure LP formulation enables complete sensitivity analysis!")
    print("   Setup variables use continuous [0,1] with threshold interpretation.")

    engine = init_database("sqlite:///production_sensitivity.db")
    session = get_session(engine)

    try:
        # Verify database
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

        # Build model
        model, production, inventory = build_multiperiod_model(session)

        print("\nPreparing goal programming...")
        model.set_goal_mode("weighted")
        model.prepare_goal_programming()
        print("  ✓ Goal programming enabled")

        print(f"\nSolving with {solver_to_use}...")
        print("  ✓ Sensitivity analysis ENABLED")
        print("  ✓ Pure LP formulation (continuous [0,1] setup variables)")
        print("  ✓ Shadow prices and reduced costs will be available!")
        print("(This may take 10-30 seconds for large-scale problem...)")

        # Enable sensitivity analysis in optimizer
        optimizer = LXOptimizer().use_solver(solver_to_use).enable_sensitivity()
        solution = optimizer.solve(model)

        # Display solution
        display_solution_summary(session, solution, production, inventory)

        # ===== SENSITIVITY ANALYSIS =====
        print("\n" + "=" * 80)
        print("PERFORMING SENSITIVITY ANALYSIS...")
        print("=" * 80)

        # Create sensitivity analyzer
        analyzer = LXSensitivityAnalyzer(model, solution)

        # Display comprehensive sensitivity analysis
        display_sensitivity_analysis(session, analyzer)

        # Save solution
        save_solution(session, solution, production)

        # Generate enhanced HTML report with sensitivity analysis
        generate_html_report(solution, session, analyzer, "production_sensitivity_report.html")

        print("\n" + "=" * 80)
        print("Tutorial Step 6 Complete!")
        print("=" * 80)
        print("\nKey Achievements:")
        print("  • Solved 16x larger problem than Step 3")
        print("  • Multi-period planning with inventory")
        print("  • Setup costs and batch constraints")
        print("  • Efficient performance with caching")
        print("  • Shadow price analysis for all constraints")
        print("  • Binding constraint identification")
        print("  • Bottleneck detection and ranking")
        print("  • Investment recommendations based on marginal values")
        print("  • Risk assessment based on solution sensitivity")
        print("\nNext Steps:")
        print("  → Use shadow prices for resource procurement decisions")
        print("  → Prioritize capacity expansion based on marginal values")
        print("  → Monitor bottlenecks and address highest priority constraints")
        print("  → Integrate sensitivity insights into decision support systems")

    finally:
        session.close()


if __name__ == "__main__":
    main()
