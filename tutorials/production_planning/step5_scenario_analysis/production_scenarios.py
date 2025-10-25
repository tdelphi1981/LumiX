"""Multi-Scenario Production Planning with LumiX.

This example demonstrates scenario analysis for production planning, allowing
comparison of different what-if scenarios to support strategic decision-making.

Features:
    - 5 scenarios with different parameter configurations
    - Baseline, High Demand, Supply Crisis, Expansion, Economic Downturn
    - Parameter overrides (demand, costs, capacity)
    - Multi-scenario comparison and sensitivity analysis
    - Comprehensive HTML report with scenario selector

Scenarios:
    1. Baseline: Standard operating conditions (reference)
    2. High Demand: 30% increase in orders (optimistic)
    3. Supply Chain Crisis: 40% less materials, 50% higher costs
    4. Expansion: 50% more capacity, 20% less setup costs, 20% more demand
    5. Economic Downturn: 30% less demand, higher costs, lower margins

Prerequisites:
    python sample_data.py  # Run first to populate database and scenarios
"""

import time
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
    CustomerOrder,
    Scenario,
    ScenarioParameter,
    ScenarioSolution,
    ProductionSchedulePeriod,
    create_cached_machine_hours_checker,
    create_cached_material_requirement_checker,
    create_cached_batch_size_checker,
    create_cached_setup_cost_checker,
    get_scenario_parameters,
)
from report_generator import generate_multi_scenario_html_report

solver_to_use = "ortools"


def apply_scenario_overrides(session, scenario_id: int):
    """Apply scenario parameter overrides to database entities.

    Args:
        session: SQLAlchemy Session
        scenario_id: Scenario ID

    Returns:
        Dictionary with modified data copies
    """
    scenario_params = get_scenario_parameters(session, scenario_id)

    # Get base data
    products = session.query(Product).all()
    machines = session.query(Machine).all()
    materials = session.query(RawMaterial).all()
    orders = session.query(CustomerOrder).all()

    # Apply multipliers to create modified copies
    modified_data = {}

    # Product profit margins
    profit_mult = scenario_params.get("profit_margin_multiplier", 1.0)
    modified_data["product_profits"] = {p.id: p.profit_per_unit * profit_mult for p in products}

    # Holding costs
    holding_mult = scenario_params.get("holding_cost_multiplier", 1.0)
    modified_data["holding_costs"] = {p.id: p.holding_cost_per_unit * holding_mult for p in products}

    # Machine capacity
    machine_mult = scenario_params.get("machine_capacity_multiplier", 1.0)
    modified_data["machine_hours"] = {m.id: m.available_hours * machine_mult for m in machines}

    # Material availability
    material_mult = scenario_params.get("material_availability_multiplier", 1.0)
    modified_data["material_quantities"] = {
        mat.id: mat.available_quantity_per_period * material_mult for mat in materials
    }

    # Setup costs
    setup_mult = scenario_params.get("setup_cost_multiplier", 1.0)
    modified_data["setup_cost_multiplier"] = setup_mult

    # Customer orders (demand)
    demand_mult = scenario_params.get("demand_multiplier", 1.0)
    modified_data["order_quantities"] = {o.id: o.target_quantity * demand_mult for o in orders}

    return modified_data


def build_scenario_model(session, scenario_id: int, scenario_name: str) -> tuple:
    """Build multi-period production model with scenario-specific parameters.

    Args:
        session: SQLAlchemy Session instance
        scenario_id: Scenario ID for parameter overrides
        scenario_name: Scenario name for display

    Returns:
        Tuple of (model, production, inventory, modified_data)
    """
    print(f"\nBuilding model for scenario: {scenario_name}...")

    # Apply scenario overrides
    modified_data = apply_scenario_overrides(session, scenario_id)

    # Create cached helpers (use base data, overrides applied in constraints)
    get_hours = create_cached_machine_hours_checker(session)
    get_material = create_cached_material_requirement_checker(session)
    get_batch = create_cached_batch_size_checker(session)
    get_setup = create_cached_setup_cost_checker(session)

    model = LXModel(f"scenario_{scenario_id}_{scenario_name.replace(' ', '_').lower()}")

    # ===== DECISION VARIABLES =====
    print("  Creating decision variables...")

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

    # ===== OBJECTIVE: MAXIMIZE PROFIT - SETUP COSTS - HOLDING COSTS =====
    print("  Defining objective...")
    obj_expr = LXLinearExpression()

    # Add profit (with scenario override)
    for product in session.query(Product).all():
        profit = modified_data["product_profits"][product.id]
        for period in session.query(Period).order_by(Period.week_number).all():
            obj_expr.add_multi_term(
                production,
                coeff=lambda prod, per, curr_prod=product, curr_per=period, p=profit: (
                    p if prod.id == curr_prod.id and per.id == curr_per.id else 0.0
                )
            )

    # Subtract setup costs (with scenario override)
    machines_list = session.query(Machine).all()
    setup_mult = modified_data["setup_cost_multiplier"]

    for product in session.query(Product).all():
        for period in session.query(Period).order_by(Period.week_number).all():
            total_setup = sum(get_setup(product.id, m.id)[0] for m in machines_list)
            avg_setup = (total_setup / len(machines_list) if machines_list else 0) * setup_mult
            obj_expr.add_multi_term(
                is_produced,
                coeff=lambda prod, per, curr_prod=product, curr_per=period, setup=avg_setup: (
                    -setup if prod.id == curr_prod.id and per.id == curr_per.id else 0.0
                )
            )

    # Subtract inventory holding costs (with scenario override)
    for product in session.query(Product).all():
        holding = modified_data["holding_costs"][product.id]
        for period in session.query(Period).order_by(Period.week_number).all():
            obj_expr.add_multi_term(
                inventory,
                coeff=lambda prod, per, curr_prod=product, curr_per=period, h=holding: (
                    -h if prod.id == curr_prod.id and per.id == curr_per.id else 0.0
                )
            )

    model.add_variable(production)
    model.add_variable(is_produced)
    model.add_variable(inventory)
    model.maximize(obj_expr)

    # ===== CONSTRAINTS =====
    print("  Adding constraints...")

    products_list = session.query(Product).all()
    periods_list = session.query(Period).order_by(Period.week_number).all()

    # 1. Machine capacity per period (with scenario override)
    print("    - Machine capacity constraints...")
    for period in periods_list:
        for machine in session.query(Machine).all():
            machine_capacity = modified_data["machine_hours"][machine.id]
            expr = LXLinearExpression()

            # Production hours
            expr.add_multi_term(
                production,
                coeff=lambda prod, per, m=machine, current_per=period: (
                    get_hours(prod.id, m.id) if per.id == current_per.id else 0.0
                )
            )
            # Setup hours (multiplier already applied to costs, hours unchanged)
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
                .rhs(machine_capacity)
            )

    # 2. Material availability per period (with scenario override)
    print("    - Material availability constraints...")
    for period in periods_list:
        for material in session.query(RawMaterial).all():
            material_available = modified_data["material_quantities"][material.id]
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
                .rhs(material_available)
            )

    # 3. Batch size constraints
    print("    - Batch size constraints...")
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

    # 4. Inventory balance constraints
    print("    - Inventory balance constraints...")
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

    # 5. Customer orders as soft goals (with scenario override)
    print("    - Customer order goal constraints...")
    products_dict = {p.id: p for p in session.query(Product).all()}
    periods_dict = {per.id: per for per in session.query(Period).all()}

    for order in session.query(CustomerOrder).all():
        order_quantity = modified_data["order_quantities"][order.id]
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
                .rhs(order_quantity)
                .as_goal(priority=order.priority, weight=1.0)
            )

    print("  ✓ Model built successfully")

    return model, production, inventory, modified_data


def save_scenario_solution(session, scenario_id: int, solution, production, solve_time: float):
    """Save solution to database with scenario_id.

    Args:
        session: SQLAlchemy Session
        scenario_id: Scenario ID
        solution: LXSolution object
        production: Production variable
        solve_time: Time taken to solve
    """
    if not solution.is_optimal() and not solution.is_feasible():
        print(f"  ⚠️ No feasible solution for scenario {scenario_id}")
        return

    print(f"  Saving solution for scenario {scenario_id}...")

    # Delete existing solution for this scenario
    session.query(ProductionSchedulePeriod).filter_by(scenario_id=scenario_id).delete()

    # Save production schedule
    schedules = []
    for product in session.query(Product).all():
        for period in session.query(Period).order_by(Period.week_number).all():
            qty = solution.variables["production"][(product.id, period.id)]
            if qty > 0.01:
                schedule = ProductionSchedulePeriod(
                    scenario_id=scenario_id,
                    product_id=product.id,
                    period_id=period.id,
                    quantity=qty,
                    profit_contribution=qty * product.profit_per_unit
                )
                schedules.append(schedule)

    session.add_all(schedules)

    # Calculate and save high-level metrics
    products = session.query(Product).all()
    orders = session.query(CustomerOrder).all()

    production_runs = len([s for s in schedules])
    unique_products = len(set(s.product_id for s in schedules))

    # Order fulfillment
    orders_fulfilled = 0
    for order in orders:
        actual = solution.variables["production"].get((order.product_id, order.period_id), 0.0)
        if actual >= order.target_quantity - 0.01:
            orders_fulfilled += 1

    # Save scenario solution metrics
    session.query(ScenarioSolution).filter_by(scenario_id=scenario_id).delete()
    scenario_solution = ScenarioSolution(
        scenario_id=scenario_id,
        solution_status=solution.status,
        objective_value=solution.objective_value,
        solve_time_seconds=solve_time,
        total_production_runs=production_runs,
        unique_products_made=unique_products,
        machine_utilization_pct=0.0,  # Calculated in report generator
        material_utilization_pct=0.0,  # Calculated in report generator
        orders_fulfilled=orders_fulfilled,
        orders_total=len(orders)
    )
    session.add(scenario_solution)

    session.commit()
    print(f"  ✓ Saved {len(schedules)} production schedule entries")


def run_scenario_analysis():
    """Run optimization for all scenarios and generate comparison report."""
    print("=" * 80)
    print("LumiX Tutorial: Production Planning - Step 5 (SCENARIO ANALYSIS)")
    print("=" * 80)
    print("\nDemonstrates:")
    print("  ✓ 5 scenarios with parameter variations")
    print("  ✓ What-if analysis (demand, cost, capacity)")
    print("  ✓ Multi-scenario comparison and sensitivity analysis")
    print("  ✓ Comprehensive HTML report with scenario selector")

    engine = init_database("sqlite:///production_scenarios.db")
    session = get_session(engine)

    try:
        # Verify database is populated
        print("\nVerifying database...")
        scenario_count = session.query(Scenario).count()
        if scenario_count == 0:
            print("\n❌ No scenarios found! Please run sample_data.py first:")
            print("   python sample_data.py")
            return

        print(f"  Found {scenario_count} scenarios")

        # Get all scenarios
        scenarios = session.query(Scenario).order_by(Scenario.id).all()

        # Store all solutions for report generation
        all_solutions = {}
        all_production_vars = {}
        all_inventory_vars = {}
        all_modified_data = {}

        # Run each scenario
        for scenario in scenarios:
            print("\n" + "=" * 80)
            print(f"SCENARIO {scenario.id}: {scenario.name}")
            print("=" * 80)
            print(f"Description: {scenario.description}")

            # Show parameter overrides
            params = session.query(ScenarioParameter).filter_by(scenario_id=scenario.id).all()
            if params:
                print("\nParameter Overrides:")
                for param in params:
                    print(f"  • {param.parameter_description}")
            else:
                print("\nParameter Overrides: None (baseline)")

            # Build model
            model, production, inventory, modified_data = build_scenario_model(
                session, scenario.id, scenario.name
            )

            # Solve
            print("\nPreparing goal programming...")
            model.set_goal_mode("weighted")
            model.prepare_goal_programming()

            print(f"Solving with {solver_to_use}...")
            start_time = time.time()
            optimizer = LXOptimizer().use_solver(solver_to_use)
            solution = optimizer.solve(model)
            solve_time = time.time() - start_time

            print(f"Status: {solution.status}")
            print(f"Objective Value: ${solution.objective_value:,.2f}")
            print(f"Solve Time: {solve_time:.2f} seconds")

            # Save solution
            save_scenario_solution(session, scenario.id, solution, production, solve_time)

            # Store for report generation
            all_solutions[scenario.id] = solution
            all_production_vars[scenario.id] = production
            all_inventory_vars[scenario.id] = inventory
            all_modified_data[scenario.id] = modified_data

        # Generate multi-scenario HTML report
        print("\n" + "=" * 80)
        print("GENERATING MULTI-SCENARIO COMPARISON REPORT")
        print("=" * 80)

        generate_multi_scenario_html_report(
            scenarios,
            all_solutions,
            all_production_vars,
            all_inventory_vars,
            all_modified_data,
            session,
            "production_scenarios_report.html"
        )

        print("\n" + "=" * 80)
        print("Tutorial Step 5 Complete!")
        print("=" * 80)
        print("\nKey Achievements:")
        print("  • Solved 5 different scenarios successfully")
        print("  • Analyzed impact of demand, cost, and capacity variations")
        print("  • Generated comprehensive comparison report")
        print("  • Demonstrated strategic decision-making with what-if analysis")
        print("\nNext Steps:")
        print("  → Open production_scenarios_report.html to compare scenarios")
        print("  → Analyze sensitivity to parameter changes")
        print("  → Use insights for strategic planning")

    finally:
        session.close()


if __name__ == "__main__":
    run_scenario_analysis()
