"""Multi-Period Production Planning with What-If Analysis using LumiX.

This example extends Step 4 by demonstrating LumiX's what-if analysis capabilities
for quick, interactive exploration of parameter changes and their impact on the
optimal solution. This is ideal for tactical decision-making and investment planning.

Key Difference from Step 4:
    Step 4 focuses on solving the optimization problem and reporting results.
    Step 7 extends this with comprehensive what-if analysis to answer questions like:
    - What if we add 100 hours of machine capacity?
    - Which resource is the biggest bottleneck?
    - What's the ROI of investing in more materials vs machines?
    - How sensitive is profit to capacity changes?
    - What's the risk if we lose machine capacity?

Problem Scale:
    - 9 products × 4 periods = 36 product-period combinations
    - 6 machines × 4 periods = 24 machine-period combinations
    - 9 materials × 4 periods = 36 material-period combinations
    - Variables: ~1,600 (same as Step 4)
    - Constraints: ~600 (same as Step 4)

New Features in Step 7 (vs Step 4):
    - What-if analysis for capacity changes
    - Bottleneck identification with ROI ranking
    - Sensitivity range analysis (profit curves)
    - Multi-option investment comparison
    - Risk assessment (downside scenarios)
    - Enhanced HTML report with what-if visualizations
    - Concrete investment recommendations

Key Concepts:
    - What-If Analysis: Quick exploration of parameter changes
    - Marginal Value: Profit impact per unit of resource
    - Bottleneck Identification: Finding most valuable capacity expansions
    - Sensitivity Ranges: How profit varies across parameter values
    - ROI Analysis: Comparing investment options

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
    LXWhatIfAnalyzer,
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
    """Build multi-period production model (identical to Step 4).

    This function builds the same model as Step 4 - we're adding what-if analysis
    on top of the existing optimization model.

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

    model = LXModel("multiperiod_production_whatif")

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
    """Display multi-period production plan summary."""
    print(f"\n{'=' * 80}")
    print("MULTI-PERIOD PRODUCTION PLAN (BASELINE)")
    print(f"{'=' * 80}")
    print(f"Status: {solution.status}")
    print(f"Total Objective Value: ${solution.objective_value:,.2f}")
    print()

    # Production by period
    for period in session.query(Period).order_by(Period.week_number).all():
        print(f"\n{period.name}:")
        print("-" * 80)
        print(f"{'Product':<20} {'Production':<15} {'Inventory':<15} {'Profit Contrib':<15}")
        print("-" * 80)

        period_total = 0.0
        for product in session.query(Product).all():
            prod_qty = solution.variables["production"][(product.id, period.id)]
            inv_qty = solution.variables["inventory"][(product.id, period.id)]
            profit = prod_qty * product.profit_per_unit

            if prod_qty > 0.01 or inv_qty > 0.01:
                period_total += profit
                print(f"{product.name:<20} {prod_qty:<15.2f} {inv_qty:<15.2f} ${profit:<14.2f}")

        print("-" * 80)
        print(f"{'Period Total':<20} {'':<15} {'':<15} ${period_total:<14,.2f}")


def run_whatif_analysis(session, model, optimizer, baseline_solution):
    """Run comprehensive what-if analysis on the production model.

    Args:
        session: SQLAlchemy Session
        model: LXModel instance
        optimizer: LXOptimizer instance
        baseline_solution: Baseline solution

    Returns:
        Dictionary containing all what-if analysis results
    """
    print("\n" + "=" * 80)
    print("WHAT-IF ANALYSIS: Interactive Decision Support")
    print("=" * 80)

    # Create what-if analyzer
    whatif = LXWhatIfAnalyzer(model, optimizer, baseline_solution=baseline_solution)

    # Store all results for report generation
    whatif_results = {
        "baseline_profit": baseline_solution.objective_value,
        "capacity_changes": [],
        "bottlenecks": [],
        "sensitivity_ranges": {},
        "investment_comparison": [],
        "risk_scenarios": []
    }

    # ===== 1. MACHINE CAPACITY CHANGES =====
    print("\n" + "-" * 80)
    print("1. MACHINE CAPACITY WHAT-IF SCENARIOS")
    print("-" * 80)

    machines = session.query(Machine).all()
    periods = session.query(Period).order_by(Period.week_number).all()

    # Test adding 50 hours to first machine in first period
    test_machine = machines[0]
    test_period = periods[0]
    constraint_name = f"machine_{test_machine.id}_period_{test_period.id}"

    print(f"\nWhat if we add 50 hours to {test_machine.name} in {test_period.name}?")
    result = whatif.increase_constraint_rhs(constraint_name, by=50)

    print(f"  Original Profit:  ${result.original_objective:,.2f}")
    print(f"  New Profit:       ${result.new_objective:,.2f}")
    print(f"  Change:           ${result.delta_objective:,.2f} ({result.delta_percentage:+.2f}%)")
    print(f"  Marginal Value:   ${result.delta_objective/50:.2f} per hour")

    whatif_results["capacity_changes"].append({
        "description": f"Add 50 hours to {test_machine.name} ({test_period.name})",
        "resource": test_machine.name,
        "period": test_period.name,
        "change": +50,
        "original_profit": result.original_objective,
        "new_profit": result.new_objective,
        "delta": result.delta_objective,
        "delta_pct": result.delta_percentage,
        "marginal_value": result.delta_objective/50
    })

    # ===== 2. MATERIAL AVAILABILITY CHANGES =====
    print("\n" + "-" * 80)
    print("2. MATERIAL AVAILABILITY WHAT-IF SCENARIOS")
    print("-" * 80)

    materials = session.query(RawMaterial).all()
    test_material = materials[0]
    test_period = periods[0]
    constraint_name = f"material_{test_material.id}_period_{test_period.id}"

    print(f"\nWhat if {test_material.name} supply increases by 100 units in {test_period.name}?")
    result = whatif.increase_constraint_rhs(constraint_name, by=100)

    print(f"  Original Profit:  ${result.original_objective:,.2f}")
    print(f"  New Profit:       ${result.new_objective:,.2f}")
    print(f"  Change:           ${result.delta_objective:,.2f} ({result.delta_percentage:+.2f}%)")

    if result.delta_objective > 0:
        print(f"  Marginal Value:   ${result.delta_objective/100:.2f} per unit")
        print(f"  ✓ Material is a bottleneck - expansion would be beneficial")
    else:
        print(f"  ✗ Material is not a bottleneck - no benefit from expansion")

    whatif_results["capacity_changes"].append({
        "description": f"Add 100 units of {test_material.name} ({test_period.name})",
        "resource": test_material.name,
        "period": test_period.name,
        "change": +100,
        "original_profit": result.original_objective,
        "new_profit": result.new_objective,
        "delta": result.delta_objective,
        "delta_pct": result.delta_percentage,
        "marginal_value": result.delta_objective/100
    })

    # ===== 3. BOTTLENECK IDENTIFICATION =====
    print("\n" + "-" * 80)
    print("3. BOTTLENECK IDENTIFICATION")
    print("-" * 80)

    print("\nTesting impact of adding 10 units to each resource constraint...")

    test_amount = 10.0
    improvements = []

    # Test machine constraints
    for machine in machines:
        for period in periods:
            constraint_name = f"machine_{machine.id}_period_{period.id}"
            result = whatif.increase_constraint_rhs(constraint_name, by=test_amount)
            improvement_per_unit = result.delta_objective / test_amount
            improvements.append({
                "name": f"{machine.name} ({period.name})",
                "type": "machine",
                "resource": machine.name,
                "period": period.name,
                "improvement": improvement_per_unit
            })

    # Test material constraints
    for material in materials:
        for period in periods:
            constraint_name = f"material_{material.id}_period_{period.id}"
            result = whatif.increase_constraint_rhs(constraint_name, by=test_amount)
            improvement_per_unit = result.delta_objective / test_amount
            improvements.append({
                "name": f"{material.name} ({period.name})",
                "type": "material",
                "resource": material.name,
                "period": period.name,
                "improvement": improvement_per_unit
            })

    # Sort by improvement (descending)
    bottlenecks = sorted(improvements, key=lambda x: x["improvement"], reverse=True)
    top_bottlenecks = bottlenecks[:10]

    print(f"\n{'Resource':<40s} {'Marginal Value':<20s} {'Priority':<10s}")
    print("-" * 80)

    for item in top_bottlenecks:
        priority = "HIGH" if item["improvement"] > 1.0 else ("MEDIUM" if item["improvement"] > 0.1 else "LOW")
        print(f"{item['name']:<40s} ${item['improvement']:<18.2f} {priority:<10s}")

        whatif_results["bottlenecks"].append({
            "name": item["name"],
            "resource": item["resource"],
            "period": item["period"],
            "type": item["type"],
            "marginal_value": item["improvement"],
            "priority": priority
        })

    # ===== 4. SENSITIVITY RANGE ANALYSIS =====
    print("\n" + "-" * 80)
    print("4. SENSITIVITY RANGE ANALYSIS")
    print("-" * 80)

    # Analyze first machine capacity sensitivity
    test_machine = machines[0]
    test_period = periods[0]
    constraint_name = f"machine_{test_machine.id}_period_{test_period.id}"

    print(f"\nAnalyzing sensitivity: {test_machine.name} capacity in {test_period.name}")
    print(f"Range: 100 - 250 hours (baseline: {test_machine.available_hours})")

    # Get current RHS value
    # For this, we'll test multiple values
    capacity_values = [100, 120, 140, 160, 180, 200, 220, 240]
    sensitivity_data = []

    print(f"\n{'Capacity (hrs)':<20s} {'Profit':<20s} {'vs Baseline':<15s}")
    print("-" * 80)

    for capacity in capacity_values:
        result = whatif.increase_constraint_rhs(constraint_name, to=capacity)
        delta = result.new_objective - baseline_solution.objective_value
        delta_pct = (delta / baseline_solution.objective_value) * 100 if baseline_solution.objective_value != 0 else 0

        marker = " (baseline)" if abs(delta) < 0.01 else ""
        print(f"{capacity:<20.0f} ${result.new_objective:<18,.2f} {delta_pct:+6.2f}%{marker}")

        sensitivity_data.append({
            "capacity": capacity,
            "profit": result.new_objective,
            "delta": delta,
            "delta_pct": delta_pct
        })

    whatif_results["sensitivity_ranges"][f"{test_machine.name}_{test_period.name}"] = sensitivity_data

    # ===== 5. INVESTMENT COMPARISON =====
    print("\n" + "-" * 80)
    print("5. INVESTMENT COMPARISON")
    print("-" * 80)

    print("\nComparing different capacity expansion options:")

    investment_options = [
        (f"machine_{machines[0].id}_period_{periods[0].id}", "increase", 50, f"{machines[0].name} +50hrs ({periods[0].name})"),
        (f"machine_{machines[0].id}_period_{periods[0].id}", "increase", 100, f"{machines[0].name} +100hrs ({periods[0].name})"),
        (f"machine_{machines[1].id}_period_{periods[0].id}", "increase", 50, f"{machines[1].name} +50hrs ({periods[0].name})"),
        (f"material_{materials[0].id}_period_{periods[0].id}", "increase", 100, f"{materials[0].name} +100 units ({periods[0].name})"),
        (f"material_{materials[0].id}_period_{periods[0].id}", "increase", 200, f"{materials[0].name} +200 units ({periods[0].name})"),
    ]

    print(f"\n{'Investment Option':<50s} {'Profit Increase':<20s} {'ROI/Unit':<15s}")
    print("-" * 80)

    for constraint_name, action, amount, description in investment_options:
        result = whatif.increase_constraint_rhs(constraint_name, by=amount)
        roi_per_unit = result.delta_objective / amount if amount != 0 else 0

        print(f"{description:<50s} ${result.delta_objective:<18,.2f} ${roi_per_unit:>13.2f}")

        whatif_results["investment_comparison"].append({
            "description": description,
            "constraint": constraint_name,
            "amount": amount,
            "delta_profit": result.delta_objective,
            "roi_per_unit": roi_per_unit
        })

    # Best investment
    best_idx = max(range(len(investment_options)),
                   key=lambda i: whatif.increase_constraint_rhs(investment_options[i][0],
                                                               by=investment_options[i][2]).delta_objective)
    best_option = investment_options[best_idx]
    best_result = whatif.increase_constraint_rhs(best_option[0], by=best_option[2])

    print("\n" + "-" * 80)
    print("INVESTMENT RECOMMENDATION")
    print("-" * 80)
    print(f"\nBest Investment Option:")
    print(f"  {best_option[3]}")
    print(f"  Profit Impact: ${best_result.delta_objective:,.2f}")
    print(f"  ROI: ${best_result.delta_objective/best_option[2]:.2f} per unit")

    # ===== 6. RISK ASSESSMENT =====
    print("\n" + "-" * 80)
    print("6. RISK ASSESSMENT (Downside Scenarios)")
    print("-" * 80)

    # Equipment failure scenario
    test_machine = machines[0]
    test_period = periods[0]
    constraint_name = f"machine_{test_machine.id}_period_{test_period.id}"

    print(f"\nWhat if {test_machine.name} loses 50 hours in {test_period.name} (equipment failure)?")
    result = whatif.decrease_constraint_rhs(constraint_name, by=50)

    print(f"  Original Profit:  ${result.original_objective:,.2f}")
    print(f"  New Profit:       ${result.new_objective:,.2f}")
    print(f"  Loss:             ${result.delta_objective:,.2f} ({result.delta_percentage:+.2f}%)")
    print(f"  ⚠ Risk: Equipment failure would cost ${abs(result.delta_objective):,.2f}")

    whatif_results["risk_scenarios"].append({
        "description": f"{test_machine.name} loses 50 hours ({test_period.name})",
        "resource": test_machine.name,
        "period": test_period.name,
        "change": -50,
        "profit_loss": result.delta_objective,
        "loss_pct": result.delta_percentage
    })

    # Supply chain disruption
    test_material = materials[0]
    print(f"\nWhat if {test_material.name} supply decreases by 20% in {test_period.name}?")
    constraint_name = f"material_{test_material.id}_period_{test_period.id}"
    result = whatif.tighten_constraint(constraint_name, by_percent=0.2)

    print(f"  Original Profit:  ${result.original_objective:,.2f}")
    print(f"  New Profit:       ${result.new_objective:,.2f}")
    print(f"  Loss:             ${result.delta_objective:,.2f} ({result.delta_percentage:+.2f}%)")
    print(f"  ⚠ Supply Risk: 20% shortage would cost ${abs(result.delta_objective):,.2f}")

    whatif_results["risk_scenarios"].append({
        "description": f"{test_material.name} decreases 20% ({test_period.name})",
        "resource": test_material.name,
        "period": test_period.name,
        "change": -20,  # percentage
        "profit_loss": result.delta_objective,
        "loss_pct": result.delta_percentage
    })

    return whatif_results


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
    """Run multi-period production optimization with what-if analysis."""
    print("=" * 80)
    print("LumiX Tutorial: Production Planning - Step 7 (WHAT-IF ANALYSIS)")
    print("=" * 80)
    print("\nDemonstrates:")
    print("  ✓ Multi-period planning (4 weeks)")
    print("  ✓ Setup costs and batch constraints")
    print("  ✓ Inventory management")
    print("  ✓ Large-scale optimization (16x Step 3)")
    print("  ✓ Goal programming with customer orders")
    print("  ✓ COMPREHENSIVE what-if analysis")
    print("  ✓ Bottleneck identification and ranking")
    print("  ✓ Sensitivity range analysis")
    print("  ✓ Investment ROI comparison")
    print("  ✓ Risk assessment scenarios")
    print("\n💡 Key Innovation: Interactive decision support for tactical planning!")
    print("   Answer 'what-if' questions quickly without full scenario setup.")

    engine = init_database("sqlite:///production_whatif.db")
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

        print(f"\nSolving baseline model with {solver_to_use}...")
        print("(This may take 10-30 seconds for large-scale problem...)")

        optimizer = LXOptimizer().use_solver(solver_to_use)
        baseline_solution = optimizer.solve(model)

        # Display baseline solution
        display_solution_summary(session, baseline_solution, production, inventory)

        # Run comprehensive what-if analysis
        whatif_results = run_whatif_analysis(session, model, optimizer, baseline_solution)

        # Save baseline solution
        save_solution(session, baseline_solution, production)

        # Generate enhanced HTML report with what-if analysis
        generate_html_report(baseline_solution, session, whatif_results, "production_whatif_report.html")

        print("\n" + "=" * 80)
        print("Tutorial Step 7 Complete!")
        print("=" * 80)
        print("\nKey Achievements:")
        print("  • Solved 16x larger problem than Step 3")
        print("  • Multi-period planning with inventory")
        print("  • Setup costs and batch constraints")
        print("  • Efficient performance with caching")
        print("  • Comprehensive what-if analysis")
        print("  • Bottleneck identification and ranking")
        print("  • Sensitivity range analysis with profit curves")
        print("  • Investment ROI comparison")
        print("  • Risk assessment for downside scenarios")
        print("  • Interactive HTML report with what-if visualizations")
        print("\nNext Steps:")
        print("  → Use what-if analysis for tactical capacity decisions")
        print("  → Prioritize investments based on marginal value rankings")
        print("  → Build interactive decision support dashboards")
        print("  → Integrate what-if analysis into operational planning systems")

    finally:
        session.close()


if __name__ == "__main__":
    main()
