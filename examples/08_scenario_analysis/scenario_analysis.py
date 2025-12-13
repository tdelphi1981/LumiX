"""Scenario Analysis Example: Business Planning with What-If Scenarios.

This example demonstrates LumiX's scenario analysis capabilities for exploring
different business conditions and strategic decisions through systematic
comparison of multiple optimization scenarios.

Problem Description:
    A manufacturing company has an existing production optimization model
    and wants to understand how their optimal production plan and profitability
    would change under different business scenarios:

    - **Market Expansion**: Increased demand and higher capacity
    - **Resource Constraint**: Reduced capacity due to supply chain issues
    - **Cost Changes**: Different raw material and labor costs
    - **New Product Introduction**: Adding new product lines

    The goal is to compare these scenarios side-by-side to inform strategic
    planning and resource allocation decisions.

Mathematical Formulation:
    Base Model:
        Maximize: sum(profit[p] * production[p])
        Subject to: sum(usage[p,r] * production[p]) <= capacity[r] for all r

    Scenarios modify:
        - Constraint RHS values (capacity[r])
        - Variable bounds (production[p])
        - Objective coefficients (profit[p])

Key Features Demonstrated:
    - **LXScenario**: Creating named scenarios with modifications
    - **LXScenarioModification**: Constraint RHS and variable bound changes
    - **LXScenarioAnalyzer**: Running and comparing multiple scenarios
    - **Comparative Analysis**: Side-by-side scenario comparison
    - **Best Scenario Identification**: Ranking scenarios by objective value
    - **Business Insights**: Translating technical results to decisions

Use Cases:
    This pattern is essential for:
        - Strategic planning and forecasting (3-5 year plans)
        - Resource allocation decisions (capital budgeting)
        - Investment prioritization (which projects to fund)
        - Risk assessment (sensitivity to external factors)
        - Business continuity planning (supply chain disruptions)
        - Market analysis (expansion vs consolidation)

Learning Objectives:
    1. How to create and configure business scenarios
    2. How to modify constraints and variable bounds
    3. How to run scenario analysis systematically
    4. How to compare and interpret scenario results
    5. How to identify the optimal strategy under uncertainty

Prerequisites:
    Before this example, complete:
        - Example 01 (production_planning): Base optimization model
        - Example 04 (basic_lp): Understanding variable bounds

See Also:
    - Example 09 (sensitivity_analysis): Shadow prices and reduced costs
    - Example 10 (whatif_analysis): Quick tactical parameter changes
    - User Guide: Scenario Analysis section

Notes:
    Scenario analysis differs from sensitivity analysis:
        - Scenario: Tests discrete business cases (e.g., "market expansion")
        - Sensitivity: Continuous parameter variation (e.g., capacity +/- 10%)

    Both are valuable and complementary analysis techniques.
"""

from lumix import (
    LXConstraint,
    LXLinearExpression,
    LXModel,
    LXOptimizer,
    LXScenario,
    LXScenarioAnalyzer,
    LXSolution,
    LXVariable,
)

from sample_data import PRODUCTS, RESOURCES, Product, Resource, get_resource_usage


solver_to_use = "ortools"

# ==================== MODEL BUILDING ====================


def build_production_model() -> LXModel:
    """Build the base production planning optimization model for scenario analysis.

    Creates a standard production planning model that will serve as the base
    for scenario modifications. The model maximizes profit while respecting
    resource capacity constraints and minimum production requirements.

    Returns:
        An LXModel instance with:
            - Variables: production[p] for each product p
            - Objective: Maximize total profit
            - Constraints: Resource capacities and minimum production levels

    Example:
        >>> model = build_production_model()
        >>> print(model.summary())
        Model: production_planning
        Variables: 5
        Constraints: 8

    Notes:
        This base model will be reused across all scenarios. Each scenario
        will create modifications (constraint RHS changes, bound changes)
        without altering the base model structure.

        The model is intentionally generic to demonstrate how scenario
        analysis can be applied to any optimization model.
    """

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


# ==================== SCENARIO ANALYSIS ====================


def run_scenario_analysis():
    """Run comprehensive scenario analysis across multiple business conditions.

    This function orchestrates a complete scenario analysis workflow by:
        1. Building the base production optimization model
        2. Creating 6 distinct business scenarios with different resource conditions
        3. Solving all scenarios systematically
        4. Comparing results to identify the optimal strategy
        5. Performing sensitivity analysis on labor capacity
        6. Providing actionable business insights

    The scenarios tested include market expansion, resource constraints, moderate
    growth, labor investment, automation, and material procurement strategies.
    Each scenario modifies constraint RHS values to reflect different business
    conditions.

    Returns:
        None. Results are printed to console including:
            - Scenario comparison table
            - Best scenario identification
            - Labor capacity sensitivity analysis
            - Strategic recommendations and risk assessment

    Example:
        >>> run_scenario_analysis()
        ============================================================
        SCENARIO ANALYSIS: Production Planning Under Different Conditions
        ============================================================
        Creating 6 business scenarios...
        Best Scenario: market_expansion
        Objective Value: 12345.67
        ...

    Notes:
        This function demonstrates the complete LXScenarioAnalyzer workflow:
            - Creating scenarios with .modify_constraint_rhs()
            - Running batch analysis with .run_all_scenarios()
            - Comparing scenarios with .compare_scenarios()
            - Parameter sensitivity with .sensitivity_to_parameter()

        The function includes a baseline scenario automatically for comparison.
        Labor capacity sensitivity tests multipliers from 0.7x to 1.5x to
        understand the profit-capacity relationship.
    """

    print("=" * 80)
    print("SCENARIO ANALYSIS: Production Planning Under Different Conditions")
    print("=" * 80)

    # Build base model
    print("\nBuilding base optimization model...")
    model = build_production_model()
    optimizer = LXOptimizer().use_solver(solver_to_use).enable_rational_conversion()

    # Create scenario analyzer
    analyzer = LXScenarioAnalyzer(model, optimizer, include_baseline=True)

    print("\n" + "-" * 80)
    print("CREATING BUSINESS SCENARIOS")
    print("-" * 80)

    # Scenario 1: Optimistic - Market Expansion
    print("\n1. OPTIMISTIC SCENARIO: Market Expansion")
    print("   - Hire more workers (+30% labor capacity)")
    print("   - Purchase new machines (+20% machine capacity)")
    print("   - Increase material procurement (+25% materials)")

    optimistic = (
        LXScenario[Product]("market_expansion")
        .modify_constraint_rhs("capacity_Labor Hours", multiply=1.30)
        .modify_constraint_rhs("capacity_Machine Hours", multiply=1.20)
        .modify_constraint_rhs("capacity_Raw Materials", multiply=1.25)
        .describe("Market expansion: increase all resource capacities")
    )
    analyzer.add_scenario(optimistic)

    # Scenario 2: Pessimistic - Resource Constraints
    print("\n2. PESSIMISTIC SCENARIO: Resource Constraints")
    print("   - Labor shortage (-20% labor capacity)")
    print("   - Supply chain issues (-15% material availability)")

    pessimistic = (
        LXScenario[Product]("resource_constraints")
        .modify_constraint_rhs("capacity_Labor Hours", multiply=0.80)
        .modify_constraint_rhs("capacity_Raw Materials", multiply=0.85)
        .describe("Resource constraints due to market conditions")
    )
    analyzer.add_scenario(pessimistic)

    # Scenario 3: Realistic - Moderate Growth
    print("\n3. REALISTIC SCENARIO: Moderate Growth")
    print("   - Modest capacity increase (+10% across all resources)")

    realistic = (
        LXScenario[Product]("moderate_growth")
        .modify_constraint_rhs("capacity_Labor Hours", multiply=1.10)
        .modify_constraint_rhs("capacity_Machine Hours", multiply=1.10)
        .modify_constraint_rhs("capacity_Raw Materials", multiply=1.10)
        .describe("Moderate growth scenario with balanced expansion")
    )
    analyzer.add_scenario(realistic)

    # Scenario 4: Labor Investment
    print("\n4. LABOR INVESTMENT SCENARIO: Focus on Workforce")
    print("   - Significant labor investment (+50% labor capacity)")
    print("   - Machines unchanged")

    labor_focus = (
        LXScenario[Product]("labor_investment")
        .modify_constraint_rhs("capacity_Labor Hours", multiply=1.50)
        .describe("Focus on expanding labor force")
    )
    analyzer.add_scenario(labor_focus)

    # Scenario 5: Automation
    print("\n5. AUTOMATION SCENARIO: Invest in Machinery")
    print("   - Purchase additional machines (+40% machine capacity)")
    print("   - Reduce labor dependency (-10% labor capacity)")

    automation = (
        LXScenario[Product]("automation")
        .modify_constraint_rhs("capacity_Machine Hours", multiply=1.40)
        .modify_constraint_rhs("capacity_Labor Hours", multiply=0.90)
        .describe("Automation: invest in machines, reduce labor")
    )
    analyzer.add_scenario(automation)

    # Scenario 6: Material Procurement
    print("\n6. MATERIAL PROCUREMENT SCENARIO: Secure More Materials")
    print("   - Negotiate better supplier contracts (+30% materials)")
    print("   - Enable higher production volumes")

    material_procurement = (
        LXScenario[Product]("material_procurement")
        .modify_constraint_rhs("capacity_Raw Materials", multiply=1.30)
        .describe("Increase material supply through better procurement")
    )
    analyzer.add_scenario(material_procurement)

    # Run all scenarios
    print("\n" + "-" * 80)
    print("SOLVING ALL SCENARIOS...")
    print("-" * 80)

    results = analyzer.run_all_scenarios()

    # Display results
    print("\n" + "=" * 80)
    print("SCENARIO COMPARISON RESULTS")
    print("=" * 80)
    print(analyzer.compare_scenarios())

    # Identify best scenario
    best = analyzer.get_best_scenario(maximize=True)
    print("\n" + "-" * 80)
    print(f"BEST SCENARIO: {best}")
    print("-" * 80)

    if best:
        best_solution = analyzer.get_result(best)
        if best_solution:
            baseline = analyzer.get_result("baseline")
            if baseline:
                improvement = best_solution.objective_value - baseline.objective_value
                improvement_pct = (improvement / baseline.objective_value) * 100
                print(f"Objective Value: ${best_solution.objective_value:,.2f}")
                print(f"Improvement over baseline: ${improvement:,.2f} ({improvement_pct:.1f}%)")

    # Sensitivity analysis - varying labor capacity
    print("\n" + "=" * 80)
    print("SENSITIVITY ANALYSIS: Labor Capacity Impact")
    print("=" * 80)
    print("\nTesting different labor capacity multipliers...")

    labor_multipliers = [0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5]
    labor_sensitivity = analyzer.sensitivity_to_parameter(
        "capacity_Labor Hours",
        values=labor_multipliers,
        modification_type="rhs_multiply",
    )

    print(f"\n{'Multiplier':<12s} {'Labor Hours':<15s} {'Objective Value':<20s} {'vs Baseline':<15s}")
    print("-" * 80)

    baseline_obj = results["baseline"].objective_value
    for multiplier, solution in labor_sensitivity.items():
        labor_hours = 1000.0 * multiplier
        obj_value = solution.objective_value
        delta = obj_value - baseline_obj
        delta_pct = (delta / baseline_obj) * 100

        print(
            f"{multiplier:<12.1f} {labor_hours:<15.0f} ${obj_value:<18,.2f} "
            f"{delta_pct:+.1f}%"
        )

    # Visualize scenarios
    visualize_scenarios(analyzer)

    # Business insights
    print("\n" + "=" * 80)
    print("BUSINESS INSIGHTS")
    print("=" * 80)

    print("\n1. Resource Capacity Impact:")
    print("   - Labor capacity has the highest impact on profitability")
    print("   - Each 10% increase in labor yields significant profit gains")
    print("   - Machine capacity is the second most constraining resource")

    print("\n2. Strategic Recommendations:")
    print("   - Prioritize labor expansion for maximum ROI")
    print("   - Consider automation for long-term efficiency")
    print("   - Market expansion scenario shows highest profit potential")

    print("\n3. Risk Considerations:")
    print("   - Resource constraint scenario shows significant downside risk")
    print("   - Diversifying production capacity mitigates single-resource dependency")
    print("   - Material procurement strategy reduces supply chain risks")

    print("\n" + "=" * 80)


# ==================== VISUALIZATION ====================


def visualize_scenarios(analyzer: LXScenarioAnalyzer) -> None:
    """Visualize scenario comparison results interactively.

    Creates interactive charts showing scenario objective values
    and comparison with baseline.

    Args:
        analyzer: The scenario analyzer with solved scenarios

    Requires:
        pip install lumix-opt[viz]
    """
    try:
        from lumix.visualization import LXScenarioCompare

        print("\n" + "=" * 80)
        print("INTERACTIVE VISUALIZATION")
        print("=" * 80)

        viz = LXScenarioCompare(analyzer)
        viz.show()

    except ImportError:
        print("\nVisualization skipped (install with: pip install lumix-opt[viz])")


# ==================== ADVANCED: SCENARIO COMPARISON ====================


def compare_investment_scenarios():
    """Compare different capital investment scenarios."""

    print("\n" + "=" * 80)
    print("INVESTMENT SCENARIO COMPARISON")
    print("=" * 80)

    model = build_production_model()
    optimizer = LXOptimizer().use_solver(solver_to_use)
    analyzer = LXScenarioAnalyzer(model, optimizer)

    # Investment options with different cost/capacity trade-offs
    scenarios = [
        ("Small Labor Investment", "capacity_Labor Hours", 1.15),
        ("Medium Labor Investment", "capacity_Labor Hours", 1.30),
        ("Large Labor Investment", "capacity_Labor Hours", 1.50),
        ("Small Machine Investment", "capacity_Machine Hours", 1.20),
        ("Medium Machine Investment", "capacity_Machine Hours", 1.40),
        ("Large Machine Investment", "capacity_Machine Hours", 1.60),
    ]

    for name, constraint, multiplier in scenarios:
        scenario = LXScenario[Product](name).modify_constraint_rhs(
            constraint, multiply=multiplier
        )
        analyzer.add_scenario(scenario)

    results = analyzer.run_all_scenarios(include_baseline=True)

    print("\nInvestment Options Comparison:")
    print(analyzer.compare_scenarios())


# ==================== MAIN ====================


def main():
    """Run the complete scenario analysis example workflow.

    This function executes a comprehensive demonstration of LumiX's scenario
    analysis capabilities by running two related examples:
        1. Main scenario analysis with 6 business scenarios
        2. Investment scenario comparison for capital allocation decisions

    The workflow demonstrates how scenario analysis supports strategic
    decision-making by comparing multiple what-if cases systematically.
    Results include scenario rankings, sensitivity analysis, and actionable
    business recommendations.

    Example:
        Run this example from the command line::

            $ python scenario_analysis.py

        Or import and run programmatically::

            >>> from scenario_analysis import main
            >>> main()

        Expected output includes:
            - Scenario comparison tables
            - Best scenario identification
            - Labor capacity sensitivity curves
            - Investment option rankings
            - Business insights and recommendations

    Notes:
        This is a comprehensive example that demonstrates:
            - LXScenario creation and configuration
            - LXScenarioModification for constraint RHS changes
            - LXScenarioAnalyzer for batch scenario execution
            - Comparative analysis and ranking
            - Parameter sensitivity analysis

        The example uses OR-Tools as the solver and demonstrates how to
        systematically explore different business strategies through
        optimization modeling.
    """

    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "LumiX Scenario Analysis Example" + " " * 26 + "║")
    print("╚" + "═" * 78 + "╝")

    # Main scenario analysis
    run_scenario_analysis()

    # Investment comparison
    compare_investment_scenarios()

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print("\nKey Takeaways:")
    print("  * Scenario analysis helps explore different business conditions")
    print("  * Sensitivity analysis identifies most impactful parameters")
    print("  * Comparing scenarios enables data-driven decision making")
    print("  * What-if analysis supports strategic planning and risk assessment")
    print()


if __name__ == "__main__":
    main()
