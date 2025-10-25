"""Comparison of Weighted vs Sequential Goal Programming Modes.

This script demonstrates the behavioral differences between LumiX's two goal programming
modes by solving the SAME production planning model with both approaches and comparing results.

Goal Programming Modes:
    1. WEIGHTED MODE (current default in production_goals.py):
       - Single optimization solve
       - All priorities combined into one objective with exponential weights
       - Allows trade-offs between priority levels
       - Example: May sacrifice 2 GOLD orders to satisfy 5 SILVER orders if weights allow it

    2. SEQUENTIAL MODE (preemptive/lexicographic):
       - Multiple optimization solves (one per priority level)
       - Solves Priority 1 first, fixes its optimal value
       - Then solves Priority 2 while maintaining Priority 1 optimality
       - Then solves Priority 3 while maintaining Priority 1 and 2 optimality
       - NEVER compromises higher priorities for lower priorities
       - True preemptive goal programming

Expected Results:
    - Sequential mode should show HIGHER satisfaction for GOLD (Priority 1) customers
    - Sequential mode may show LOWER satisfaction for BRONZE (Priority 3) customers
    - Weighted mode makes trade-offs across all priorities based on exponential scaling
    - Sequential mode enforces strict priority hierarchy

Prerequisites:
    Run sample_data.py first to populate the database:
    >>> python sample_data.py

Usage:
    >>> python production_goals_comparison.py
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
    create_cached_machine_hours_checker,
    create_cached_material_requirement_checker,
)

solver_to_use = "ortools"


def calculate_actual_profit(session, solution):
    """Calculate actual profit from production quantities.

    IMPORTANT: In weighted goal programming mode, solution.objective_value returns
    the TRANSFORMED objective which includes exponentially weighted goal deviation
    terms (e.g., 10^6 × deviations). This is NOT the actual profit!

    This function calculates the TRUE profit by summing:
        profit = Σ (production[p] × profit_per_unit[p])

    Args:
        session: SQLAlchemy Session instance
        solution: LXSolution object

    Returns:
        float: Actual profit in dollars

    Example:
        If production = {Chair: 50, Desk: 2.86}:
        actual_profit = 50 × $45 + 2.86 × $200 = $2,822
    """
    total_profit = 0.0

    for product in session.query(Product).all():
        quantity = solution.variables["production"][product.id]
        profit_contribution = quantity * product.profit_per_unit
        total_profit += profit_contribution

    return total_profit


def build_production_model_with_goals(session) -> LXModel:
    """Build production model with goal programming for customer orders using ORM.

    This is the SAME model used in production_goals.py. We reuse it to ensure
    fair comparison between weighted and sequential modes.

    Args:
        session: SQLAlchemy Session instance

    Returns:
        LXModel with hard constraints and soft goals
    """
    # Create cached checkers for efficient lookups
    get_hours = create_cached_machine_hours_checker(session)
    get_material_qty = create_cached_material_requirement_checker(session)

    # ========================================================================
    # Decision Variables
    # ========================================================================

    # Decision variable: production[product]
    production = (
        LXVariable[Product, float]("production")
        .continuous()
        .bounds(lower=0)
        .indexed_by(lambda p: p.id)
        .from_model(Product, session)
    )

    # ========================================================================
    # Objective: Maximize Profit
    # ========================================================================

    profit_expr = LXLinearExpression().add_multi_term(
        production,
        coeff=lambda p: p.profit_per_unit
    )

    model = LXModel("production_planning_comparison")
    model.add_variable(production)
    model.maximize(profit_expr)

    # ========================================================================
    # Hard Constraints
    # ========================================================================

    # Max Demand Constraints
    for product in session.query(Product).all():
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

    # Machine Capacity Constraints
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

    # Material Availability Constraints
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

    # ========================================================================
    # Soft Goals: Customer Orders
    # ========================================================================

    # Create lookups for efficient access
    products_dict = {p.id: p for p in session.query(Product).all()}
    customers_dict = {c.id: c for c in session.query(Customer).all()}

    # Query customer orders directly from database
    for order in session.query(CustomerOrder).all():
        product = products_dict.get(order.product_id)
        if not product:
            continue

        customer = customers_dict.get(order.customer_id)
        if not customer:
            continue

        # Goal: production[product] >= target_quantity
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
            .as_goal(priority=order.priority, weight=1.0)
        )

    return model


def solve_with_weighted_mode(session):
    """Solve model using weighted goal programming (current default).

    Returns:
        LXSolution object
    """
    print("\n" + "=" * 80)
    print("SOLVING WITH WEIGHTED GOAL PROGRAMMING")
    print("=" * 80)
    print("Mode: Single solve with exponentially weighted priorities")
    print("Behavior: Allows trade-offs between all priority levels")
    print()

    model = build_production_model_with_goals(session)

    # Enable weighted goal programming
    model.set_goal_mode("weighted")
    model.prepare_goal_programming()

    # Solve
    optimizer = LXOptimizer().use_solver(solver_to_use)
    solution = optimizer.solve(model)

    # Calculate actual profit (transformed objective is not the real profit!)
    actual_profit = calculate_actual_profit(session, solution)

    print(f"Status: {solution.status}")
    print(f"Transformed Objective Value: ${solution.objective_value:,.2f}")
    print(f"  ⚠️  NOTE: This includes weighted goal deviation terms (10^6, 10^4, 10^2)")
    print(f"  ⚠️  NOT the actual profit - use manual calculation instead")
    print(f"Actual Profit (calculated): ${actual_profit:,.2f}")

    return solution


def solve_with_sequential_mode(session):
    """Solve model using sequential (preemptive) goal programming.

    Returns:
        LXSolution object
    """
    print("\n" + "=" * 80)
    print("SOLVING WITH SEQUENTIAL GOAL PROGRAMMING (Preemptive/Lexicographic)")
    print("=" * 80)
    print("Mode: Multiple solves - one per priority level")
    print("Behavior: Priority 1 optimized first, then P2 (maintaining P1), then P3 (maintaining P1+P2)")
    print("Note: Higher priorities are NEVER sacrificed for lower priorities")
    print()

    model = build_production_model_with_goals(session)

    # Enable sequential goal programming
    model.set_goal_mode("sequential")
    model.prepare_goal_programming()

    # Solve
    optimizer = LXOptimizer().use_solver(solver_to_use)
    solution = optimizer.solve(model)

    # Calculate actual profit for consistency
    actual_profit = calculate_actual_profit(session, solution)

    print(f"Status: {solution.status}")
    print(f"Objective Value: ${solution.objective_value:,.2f}")
    print(f"  ✓ In sequential mode, this IS the actual profit (final solve iteration)")
    print(f"Actual Profit (verified): ${actual_profit:,.2f}")

    return solution


def analyze_goal_satisfaction(session, solution, mode_name):
    """Analyze which customer orders were satisfied.

    Args:
        session: SQLAlchemy Session instance
        solution: Solved LXSolution object
        mode_name: String name of the mode (for display)

    Returns:
        Dictionary with satisfaction statistics
    """
    products_dict = {p.id: p for p in session.query(Product).all()}
    customers_dict = {c.id: c for c in session.query(Customer).all()}

    # Group orders by priority
    orders_by_priority = {}
    for order in session.query(CustomerOrder).all():
        if order.priority not in orders_by_priority:
            orders_by_priority[order.priority] = []
        orders_by_priority[order.priority].append(order)

    stats = {}

    # Analyze each priority level
    for priority in sorted(orders_by_priority.keys()):
        tier_name = "GOLD" if priority == 1 else "SILVER" if priority == 2 else "BRONZE"
        orders = orders_by_priority[priority]
        satisfied_count = 0
        total_shortfall = 0.0

        for order in orders:
            product = products_dict.get(order.product_id)
            if not product:
                continue

            actual_production = solution.variables["production"][product.id]
            satisfied = actual_production >= order.target_quantity - 0.01
            shortfall = max(0, order.target_quantity - actual_production)

            if satisfied:
                satisfied_count += 1
            total_shortfall += shortfall

        stats[priority] = {
            'tier': tier_name,
            'satisfied': satisfied_count,
            'total': len(orders),
            'percentage': (satisfied_count / len(orders) * 100) if len(orders) > 0 else 0,
            'shortfall': total_shortfall
        }

    return stats


def display_comparison(session, weighted_solution, sequential_solution):
    """Display side-by-side comparison of both solutions.

    Args:
        session: SQLAlchemy Session instance
        weighted_solution: Solution from weighted mode
        sequential_solution: Solution from sequential mode
    """
    print("\n" + "=" * 80)
    print("COMPARISON: WEIGHTED vs SEQUENTIAL GOAL PROGRAMMING")
    print("=" * 80)
    print()

    # Analyze goal satisfaction for both
    weighted_stats = analyze_goal_satisfaction(session, weighted_solution, "Weighted")
    sequential_stats = analyze_goal_satisfaction(session, sequential_solution, "Sequential")

    # Display comparison table
    print(f"{'Priority':<12} {'Tier':<8} {'Weighted Mode':<25} {'Sequential Mode':<25} {'Difference':<20}")
    print("-" * 90)

    for priority in sorted(weighted_stats.keys()):
        w_stat = weighted_stats[priority]
        s_stat = sequential_stats[priority]
        tier = w_stat['tier']

        w_text = f"{w_stat['satisfied']}/{w_stat['total']} ({w_stat['percentage']:.1f}%)"
        s_text = f"{s_stat['satisfied']}/{s_stat['total']} ({s_stat['percentage']:.1f}%)"

        diff_count = s_stat['satisfied'] - w_stat['satisfied']
        diff_pct = s_stat['percentage'] - w_stat['percentage']

        if diff_count > 0:
            diff_text = f"+{diff_count} orders ({diff_pct:+.1f}%)"
        elif diff_count < 0:
            diff_text = f"{diff_count} orders ({diff_pct:+.1f}%)"
        else:
            diff_text = "No change"

        print(f"Priority {priority:<3} {tier:<8} {w_text:<25} {s_text:<25} {diff_text:<20}")

    print()
    print("-" * 90)

    # Calculate actual profit for both solutions (important for weighted mode!)
    weighted_actual_profit = calculate_actual_profit(session, weighted_solution)
    sequential_actual_profit = calculate_actual_profit(session, sequential_solution)

    print(f"{'Actual Profit:':<20} ${weighted_actual_profit:>15,.2f} ${sequential_actual_profit:>18,.2f}")

    profit_diff = sequential_actual_profit - weighted_actual_profit
    profit_diff_pct = (profit_diff / weighted_actual_profit * 100) if weighted_actual_profit > 0 else 0
    print(f"{'Profit Difference:':<20} {'':<15} ${profit_diff:>18,.2f} ({profit_diff_pct:+.1f}%)")
    print()
    print("⚠️  NOTE: Actual profit calculated manually from production quantities")
    print("   Weighted mode's objective_value includes goal deviation terms (not comparable)")
    print()

    # Production quantities comparison
    print("\nPRODUCTION QUANTITIES COMPARISON:")
    print("-" * 80)
    print(f"{'Product':<20} {'Weighted':<20} {'Sequential':<20} {'Difference':<15}")
    print("-" * 80)

    for product in session.query(Product).all():
        w_qty = weighted_solution.variables["production"][product.id]
        s_qty = sequential_solution.variables["production"][product.id]
        diff = s_qty - w_qty

        print(f"{product.name:<20} {w_qty:<20.2f} {s_qty:<20.2f} {diff:+.2f}")

    print()


def explain_results():
    """Display explanation of the observed differences."""
    print("\n" + "=" * 80)
    print("EXPLANATION OF RESULTS")
    print("=" * 80)
    print()
    print("CRITICAL: WHY OBJECTIVE VALUES DIFFER BETWEEN MODES")
    print("-" * 80)
    print()
    print("⚠️  IMPORTANT: solution.objective_value means DIFFERENT THINGS in each mode!")
    print()
    print("WEIGHTED MODE - Transformed Objective:")
    print("  • LumiX transforms the objective into:")
    print("    Combined = Profit + (10^6 × P1_deviations) + (10^4 × P2_deviations) + (10^2 × P3_deviations)")
    print("  • solution.objective_value returns this TRANSFORMED value (includes huge weights)")
    print("  • Example: If actual profit = $2,822 but P1 has 2 violations:")
    print("    Transformed objective ≈ $2,822 + (10^6 × 2) = $2,000,822")
    print("  • This is why you see values like $4,058,000 instead of the real $2,822")
    print()
    print("SEQUENTIAL MODE - Actual Profit:")
    print("  • Solves multiple times, final iteration optimizes profit directly")
    print("  • solution.objective_value from the LAST solve = actual profit")
    print("  • Example: $2,857.14 IS the real profit (no transformation)")
    print()
    print("SOLUTION: Always Calculate Actual Profit Manually")
    print("  • For fair comparison, calculate: profit = Σ(production[p] × profit_per_unit[p])")
    print("  • This script uses calculate_actual_profit() to ensure correct comparison")
    print("  • NEVER compare solution.objective_value directly between modes!")
    print()
    print("=" * 80)
    print()
    print("WHY THE DIFFERENCES IN PRODUCTION STRATEGY?")
    print("-" * 80)
    print()
    print("WEIGHTED MODE:")
    print("  • Combines all priorities into a single objective function")
    print("  • Uses exponential weights to differentiate priorities (e.g., 10^6, 10^4, 10^2)")
    print("  • Allows trade-offs: May sacrifice higher-priority goals if it significantly")
    print("    improves lower-priority goals weighted by the scaling factor")
    print("  • Single optimization solve - computationally efficient")
    print("  • Best when: Priorities are preferences rather than strict requirements")
    print()
    print("SEQUENTIAL MODE (Preemptive):")
    print("  • Solves multiple times, one per priority level")
    print("  • Priority 1 optimized first → solution value fixed as constraint")
    print("  • Priority 2 optimized next (subject to maintaining P1 optimality)")
    print("  • Priority 3 optimized last (subject to maintaining P1 and P2 optimality)")
    print("  • NEVER compromises higher priorities for lower priorities")
    print("  • Multiple optimization solves - more computationally expensive")
    print("  • Best when: Priorities are strict requirements (must satisfy P1 before considering P2)")
    print()
    print("TYPICAL PATTERN IN RESOURCE-CONSTRAINED PROBLEMS:")
    print("  • Sequential mode: Higher Priority 1 satisfaction, lower Priority 3 satisfaction")
    print("  • Weighted mode: More balanced satisfaction across all priorities")
    print("  • If Priority 1 demands exceed capacity: Even sequential mode cannot satisfy all P1 goals")
    print()
    print("WHEN TO USE EACH MODE:")
    print("  • Use WEIGHTED when priorities represent relative importance (soft preferences)")
    print("  • Use SEQUENTIAL when priorities are hierarchical requirements (hard hierarchy)")
    print("  • Use WEIGHTED for faster solve times on large models")
    print("  • Use SEQUENTIAL when higher-priority customers/orders are non-negotiable")
    print()
    print("=" * 80)
    print()


def main():
    """Run comparison between weighted and sequential goal programming."""
    print("=" * 80)
    print("LumiX Tutorial: Goal Programming Mode Comparison")
    print("=" * 80)
    print()
    print("This script compares two goal programming approaches:")
    print("  1. WEIGHTED: Single solve with exponentially weighted priorities")
    print("  2. SEQUENTIAL: Multiple solves in strict priority order (preemptive)")
    print()

    # Initialize database and create session
    engine = init_database("sqlite:///production.db")
    session = get_session(engine)

    try:
        # Verify database is populated
        if session.query(Product).count() == 0 or session.query(CustomerOrder).count() == 0:
            print("\n❌ Database is empty! Please run sample_data.py first:")
            print("   python sample_data.py")
            return

        print(f"Database verified: {session.query(CustomerOrder).count()} customer orders loaded")

        # Solve with both modes
        weighted_solution = solve_with_weighted_mode(session)
        sequential_solution = solve_with_sequential_mode(session)

        # Display comparison
        display_comparison(session, weighted_solution, sequential_solution)

        # Explain results
        explain_results()

        print("\nComparison complete! Review the differences above to understand each mode's behavior.")

    finally:
        session.close()


if __name__ == "__main__":
    main()
