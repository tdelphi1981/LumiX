"""
What-If Analysis Example: Interactive Decision Support
=======================================================

This example demonstrates LumiX's what-if analysis capabilities for
quick, interactive exploration of parameter changes and their impact
on the optimal solution.

Problem: A manufacturing company wants to quickly assess the impact of
various operational changes without running full scenario analysis:
- What if we get more labor hours?
- What if machine capacity is reduced?
- What if we relax minimum production requirements?
- Which resources are most valuable to expand?

Key Features Demonstrated:
- Increasing/decreasing constraint RHS
- Relaxing/tightening constraints
- Modifying variable bounds
- Finding bottlenecks through testing
- Sensitivity range analysis
- Comparing multiple changes
- Quick ROI assessment

Use Cases:
- Quick operational decisions
- Resource allocation
- Capacity planning
- Trade-off analysis
- Investment prioritization
- Tactical adjustments
"""

from lumix import (
    LXConstraint,
    LXLinearExpression,
    LXModel,
    LXOptimizer,
    LXVariable,
    LXWhatIfAnalyzer,
)

from sample_data import PRODUCTS, RESOURCES, Product, Resource, get_resource_usage


solver_to_use = "cplex"

# ==================== MODEL BUILDING ====================


def build_production_model() -> LXModel:
    """Build the production planning optimization model."""

    # Decision Variable: Production quantity for each product
    production = (
        LXVariable[Product, float]("production")
        .continuous()
        .bounds(lower=0)
        .indexed_by(lambda p: p.id)
        .from_data(PRODUCTS)
    )

    # Create model
    model = LXModel[Product]("production_planning").add_variable(production)

    # Objective: Maximize total profit
    profit_expr = LXLinearExpression[Product]().add_term(
        production, coeff=lambda p: p.selling_price - p.unit_cost
    )
    model.maximize(profit_expr)

    # Constraints: Resource capacity limits
    for resource in RESOURCES:
        usage_expr = LXLinearExpression().add_term(
            production, coeff=lambda p, r=resource: get_resource_usage(p, r)
        )

        model.add_constraint(
            LXConstraint(f"capacity_{resource.name}")
            .expression(usage_expr)
            .le()
            .rhs(resource.capacity)
        )

    # Constraints: Minimum production requirements
    model.add_constraint(
        LXConstraint[Product]("min_production")
        .expression(LXLinearExpression[Product]().add_term(production, 1.0))
        .ge()
        .rhs(lambda p: float(p.min_production))
        .from_data(PRODUCTS)
        .indexed_by(lambda p: p.name)
    )

    return model


# ==================== WHAT-IF ANALYSIS ====================


def run_basic_whatif_analysis():
    """Run basic what-if analysis with simple changes."""

    print("=" * 80)
    print("WHAT-IF ANALYSIS: Quick Impact Assessment")
    print("=" * 80)

    # Build model and create analyzer
    model = build_production_model()
    optimizer = LXOptimizer().use_solver(solver_to_use)
    whatif = LXWhatIfAnalyzer(model, optimizer)

    # Get baseline
    print("\nSolving baseline model...")
    baseline = whatif.get_baseline_solution()
    print(f"Baseline Profit: ${baseline.objective_value:,.2f}")

    # What-if #1: Increase labor hours
    print("\n" + "-" * 80)
    print("WHAT-IF #1: Increase Labor Hours by 200")
    print("-" * 80)

    result = whatif.increase_constraint_rhs("capacity_Labor Hours", by=200)
    print(f"\nOriginal Profit:  ${result.original_objective:,.2f}")
    print(f"New Profit:       ${result.new_objective:,.2f}")
    print(f"Change:           ${result.delta_objective:,.2f} ({result.delta_percentage:+.2f}%)")
    print(f"\nInterpretation: Adding 200 labor hours would increase profit by ${result.delta_objective:,.2f}")
    print(f"Marginal value:  ${result.delta_objective/200:.2f} per labor hour")

    # What-if #2: Decrease machine hours
    print("\n" + "-" * 80)
    print("WHAT-IF #2: Decrease Machine Hours by 100 (Equipment Failure)")
    print("-" * 80)

    result = whatif.decrease_constraint_rhs("capacity_Machine Hours", by=100)
    print(f"\nOriginal Profit:  ${result.original_objective:,.2f}")
    print(f"New Profit:       ${result.new_objective:,.2f}")
    print(f"Change:           ${result.delta_objective:,.2f} ({result.delta_percentage:+.2f}%)")
    print(f"\n⚠ Risk Assessment: Machine failure would cost ${abs(result.delta_objective):,.2f} in lost profit")

    # What-if #3: Increase raw materials
    print("\n" + "-" * 80)
    print("WHAT-IF #3: Increase Raw Materials by 100 Units")
    print("-" * 80)

    result = whatif.increase_constraint_rhs("capacity_Raw Materials", by=100)
    print(f"\nOriginal Profit:  ${result.original_objective:,.2f}")
    print(f"New Profit:       ${result.new_objective:,.2f}")
    print(f"Change:           ${result.delta_objective:,.2f} ({result.delta_percentage:+.2f}%)")

    if result.delta_objective > 0:
        print(f"\n✓ Benefit: Adding raw materials increases production capacity and profit")
        print(f"  Marginal value: ${result.delta_objective/100:.2f} per unit of raw material")
    else:
        print(f"\n✗ No benefit: Raw materials are not currently a bottleneck")

    # What-if #4: Set capacity to specific value
    print("\n" + "-" * 80)
    print("WHAT-IF #4: Set Labor Hours to 1500 (50% Increase)")
    print("-" * 80)

    result = whatif.increase_constraint_rhs("capacity_Labor Hours", to=1500)
    print(f"\nOriginal Profit:  ${result.original_objective:,.2f}")
    print(f"New Profit:       ${result.new_objective:,.2f}")
    print(f"Change:           ${result.delta_objective:,.2f} ({result.delta_percentage:+.2f}%)")
    print(f"\nROI Analysis: Increasing labor by 500 hours → ${result.delta_objective:,.2f} profit increase")

    # What-if #5: Tighten constraint
    print("\n" + "-" * 80)
    print("WHAT-IF #5: Tighten Raw Materials by 20% (Supply Chain Issues)")
    print("-" * 80)

    result = whatif.tighten_constraint("capacity_Raw Materials", by_percent=0.2)
    print(f"\nOriginal Profit:  ${result.original_objective:,.2f}")
    print(f"New Profit:       ${result.new_objective:,.2f}")
    print(f"Change:           ${result.delta_objective:,.2f} ({result.delta_percentage:+.2f}%)")
    print(f"\n⚠ Supply Risk: 20% material shortage would cost ${abs(result.delta_objective):,.2f}")


# ==================== BOTTLENECK IDENTIFICATION ====================


def identify_bottlenecks():
    """Identify bottlenecks by testing small capacity changes."""

    print("\n" + "=" * 80)
    print("BOTTLENECK IDENTIFICATION: Testing Resource Constraints")
    print("=" * 80)

    model = build_production_model()
    optimizer = LXOptimizer().use_solver(solver_to_use)
    whatif = LXWhatIfAnalyzer(model, optimizer)

    # Find bottlenecks by testing 10 unit increases
    # Note: Only testing resource capacity constraints (with constant RHS)
    print("\nTesting impact of adding 10 units to each resource...")

    test_amount = 10.0
    improvements = []

    # Manually test each resource capacity constraint
    for resource in RESOURCES:
        constraint_name = f"capacity_{resource.name}"
        result = whatif.relax_constraint(constraint_name, by=test_amount)
        improvement_per_unit = result.delta_objective / test_amount
        improvements.append((constraint_name, improvement_per_unit))

    # Sort by improvement (descending)
    bottlenecks = sorted(improvements, key=lambda x: x[1], reverse=True)

    print(f"\n{'Resource':<30s} {'Improvement':<20s} {'Per Unit':<15s} {'Priority':<10s}")
    print("-" * 80)

    for name, improvement_per_unit in bottlenecks:
        resource_name = name.replace("capacity_", "")
        improvement_total = improvement_per_unit * test_amount
        priority = "HIGH" if improvement_per_unit > 1.0 else "MEDIUM" if improvement_per_unit > 0.1 else "LOW"

        print(f"{resource_name:<30s} ${improvement_total:<18,.2f} ${improvement_per_unit:<13,.2f} {priority:<10s}")

    # Detailed analysis
    print("\n" + "-" * 80)
    print("BOTTLENECK ANALYSIS")
    print("-" * 80)

    if bottlenecks:
        top_bottleneck, top_value = bottlenecks[0]
        resource_name = top_bottleneck.replace("capacity_", "")

        print(f"\n► Primary Bottleneck: {resource_name}")
        print(f"  Marginal Value: ${top_value:.2f} per unit")
        print(f"  Recommendation: Prioritize expanding this resource")

        if top_value > 1.0:
            print(f"  ✓ HIGH PRIORITY: Strong ROI from capacity expansion")
            print(f"    - Each unit of capacity adds ${top_value:.2f} to profit")
            print(f"    - Consider immediate investment if cost < ${top_value:.2f}/unit")
        elif top_value > 0.1:
            print(f"  → MODERATE PRIORITY: Positive ROI from expansion")
        else:
            print(f"  ✗ LOW PRIORITY: Minimal profit impact")


# ==================== SENSITIVITY RANGE ANALYSIS ====================


def analyze_sensitivity_ranges():
    """Analyze how objective changes across range of parameter values."""

    print("\n" + "=" * 80)
    print("SENSITIVITY RANGE ANALYSIS: Parameter Impact Curves")
    print("=" * 80)

    model = build_production_model()
    optimizer = LXOptimizer().use_solver(solver_to_use)
    whatif = LXWhatIfAnalyzer(model, optimizer)

    # Analyze labor capacity sensitivity
    print("\n1. LABOR CAPACITY SENSITIVITY (700 - 1300 hours)")
    print("-" * 80)

    labor_range = whatif.sensitivity_range(
        "capacity_Labor Hours", min_value=700, max_value=1300, num_points=13
    )

    print(f"\n{'Labor Hours':<15s} {'Profit':<20s} {'Marginal Value':<20s}")
    print("-" * 80)

    prev_labor, prev_profit = labor_range[0]
    print(f"{prev_labor:<15.0f} ${prev_profit:<18,.2f} {'(baseline)':>20s}")

    for labor, profit in labor_range[1:]:
        delta_labor = labor - prev_labor
        delta_profit = profit - prev_profit
        marginal = delta_profit / delta_labor if delta_labor != 0 else 0

        print(f"{labor:<15.0f} ${profit:<18,.2f} ${marginal:>18.2f}/hour")
        prev_labor, prev_profit = labor, profit

    # Analyze machine capacity sensitivity
    print("\n\n2. MACHINE CAPACITY SENSITIVITY (600 - 1000 hours)")
    print("-" * 80)

    machine_range = whatif.sensitivity_range(
        "capacity_Machine Hours", min_value=600, max_value=1000, num_points=9
    )

    print(f"\n{'Machine Hours':<15s} {'Profit':<20s} {'vs Baseline':<20s}")
    print("-" * 80)

    baseline_profit = machine_range[4][1]  # Middle value (800) is baseline

    for machine, profit in machine_range:
        delta = profit - baseline_profit
        delta_pct = (delta / baseline_profit) * 100 if baseline_profit != 0 else 0

        marker = " (baseline)" if abs(delta) < 0.01 else ""
        print(f"{machine:<15.0f} ${profit:<18,.2f} {delta_pct:+6.2f}%{marker}")


# ==================== COMPARING MULTIPLE CHANGES ====================


def compare_multiple_changes():
    """Compare multiple what-if changes side by side."""

    print("\n" + "=" * 80)
    print("COMPARING MULTIPLE CHANGES: Investment Options")
    print("=" * 80)

    model = build_production_model()
    optimizer = LXOptimizer().use_solver(solver_to_use)
    whatif = LXWhatIfAnalyzer(model, optimizer)

    # Define investment scenarios
    investment_options = [
        ("capacity_Labor Hours", "increase", 100),
        ("capacity_Labor Hours", "increase", 200),
        ("capacity_Labor Hours", "increase", 300),
        ("capacity_Machine Hours", "increase", 100),
        ("capacity_Machine Hours", "increase", 200),
        ("capacity_Raw Materials", "increase", 100),
    ]

    print("\nComparing different capacity expansion options:")
    results = whatif.compare_changes(investment_options)

    print(f"\n{'Investment Option':<40s} {'Profit Increase':<20s} {'ROI per Unit':<15s}")
    print("-" * 80)

    for (resource, _, amount), result in zip(investment_options, results):
        resource_name = resource.replace("capacity_", "")
        roi_per_unit = result.delta_objective / amount if amount != 0 else 0

        print(
            f"{resource_name} +{amount:<3.0f} units"
            f"{'':<23s} ${result.delta_objective:<18,.2f} ${roi_per_unit:>13.2f}"
        )

    # Best investment
    print("\n" + "-" * 80)
    print("INVESTMENT RECOMMENDATION")
    print("-" * 80)

    best_idx = max(range(len(results)), key=lambda i: results[i].delta_objective)
    best_resource, _, best_amount = investment_options[best_idx]
    best_result = results[best_idx]

    print(f"\nBest Investment:")
    print(f"  Resource: {best_resource.replace('capacity_', '')}")
    print(f"  Amount: +{best_amount} units")
    print(f"  Profit Impact: ${best_result.delta_objective:,.2f}")
    print(f"  ROI: ${best_result.delta_objective/best_amount:.2f} per unit")


# ==================== VARIABLE BOUND MODIFICATIONS ====================


def analyze_variable_bounds():
    """Analyze impact of variable bound changes."""

    print("\n" + "=" * 80)
    print("VARIABLE BOUND ANALYSIS: Production Constraints")
    print("=" * 80)

    model = build_production_model()
    optimizer = LXOptimizer().use_solver(solver_to_use)
    whatif = LXWhatIfAnalyzer(model, optimizer)

    baseline = whatif.get_baseline_solution()

    # What if we limit premium production?
    print("\n1. LIMITING PREMIUM Z PRODUCTION")
    print("-" * 80)
    print("\nWhat if market demand limits Premium Z to max 10 units?")

    # Note: This would require modifying the variable bounds in the model
    # For this example, we'll demonstrate the concept
    print("\nCurrent Production:")
    for product in PRODUCTS:
        qty = baseline.variables["production"][product.id]
        if product.name == "Premium Z":
            print(f"  {product.name}: {qty:.1f} units")

    print("\n(Bound modification example - would require model variable access)")


# ==================== MAIN ====================


def main():
    """Run what-if analysis examples."""

    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 22 + "LumiX What-If Analysis Example" + " " * 24 + "║")
    print("╚" + "═" * 78 + "╝")

    # Basic what-if analysis
    run_basic_whatif_analysis()

    # Bottleneck identification
    identify_bottlenecks()

    # Sensitivity ranges
    analyze_sensitivity_ranges()

    # Compare multiple changes
    compare_multiple_changes()

    # Variable bounds
    analyze_variable_bounds()

    # Summary
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print("\nKey Takeaways:")
    print("  ✓ What-if analysis enables quick impact assessment")
    print("  ✓ Bottleneck identification reveals most valuable improvements")
    print("  ✓ Sensitivity ranges show how objective varies with parameters")
    print("  ✓ Comparing changes helps prioritize investments")
    print("  ✓ Interactive analysis supports agile decision making")
    print()


if __name__ == "__main__":
    main()
