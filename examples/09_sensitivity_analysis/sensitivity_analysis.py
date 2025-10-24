"""
Sensitivity Analysis Example: Understanding Optimal Solutions
==============================================================

This example demonstrates LumiX's sensitivity analysis capabilities for
understanding how changes in parameters affect the optimal solution.

Problem: A manufacturing company has solved their production optimization
problem and wants to understand:
- Which resources are most valuable (shadow prices)
- Which products are worth increasing (reduced costs)
- What are the critical bottlenecks
- How sensitive is the solution to parameter changes

Key Features Demonstrated:
- Computing shadow prices (dual values) for constraints
- Computing reduced costs for variables
- Identifying binding (tight) constraints
- Finding bottlenecks
- Generating comprehensive sensitivity reports
- Top N most sensitive parameters
- Practical business decision support

Use Cases:
- Resource valuation and prioritization
- Investment decision support
- Capacity planning
- Bottleneck identification
- Marginal value analysis
"""

from lumix import (
    LXConstraint,
    LXLinearExpression,
    LXModel,
    LXOptimizer,
    LXSensitivityAnalyzer,
    LXVariable,
)

from sample_data import PRODUCTS, RESOURCES, Product, Resource, get_resource_usage

solver_to_use = "ortools"

# ==================== MODEL BUILDING ====================


def build_production_model() -> LXModel:
    """Build the base production planning optimization model for sensitivity analysis.

    Creates a standard production planning model that will be solved and then
    analyzed for sensitivity insights including shadow prices, reduced costs,
    and binding constraints. The model maximizes profit while respecting
    resource capacity limits and minimum production requirements.

    Returns:
        An LXModel instance containing:
            - Variables: production[p] for each product p
            - Objective: Maximize total profit
            - Constraints: Resource capacity limits and minimum production

    Example:
        >>> model = build_production_model()
        >>> print(model.summary())
        Model: production_planning
        Variables: 5
        Constraints: 8
        >>> optimizer = LXOptimizer().use_solver("ortools").enable_sensitivity()
        >>> solution = optimizer.solve(model)

    Notes:
        This model is identical to the base production model but will be
        solved with sensitivity analysis enabled (.enable_sensitivity()).
        The solver must support sensitivity analysis (dual values) to
        extract shadow prices and reduced costs.

        The model structure remains unchanged from Example 01, but the
        focus here is on post-solution analysis rather than just finding
        the optimal solution.
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


# ==================== SENSITIVITY ANALYSIS ====================


def run_sensitivity_analysis():
    """Run comprehensive sensitivity analysis on the optimal solution.

    This function performs a complete sensitivity analysis workflow that reveals
    the economic insights hidden in the optimal solution:
        1. Build and solve the production model with sensitivity enabled
        2. Analyze shadow prices (dual values) for all constraints
        3. Identify binding constraints that limit profitability
        4. Find bottlenecks with high marginal values
        5. Compute reduced costs for decision variables
        6. Rank constraints by sensitivity impact
        7. Generate comprehensive sensitivity reports

    The analysis provides actionable insights for resource investment decisions,
    capacity planning, and understanding solution robustness.

    Returns:
        None. Results are printed to console including:
            - Solution summary with optimal objective value
            - Comprehensive sensitivity report
            - Constraint-by-constraint shadow price analysis
            - Binding constraint identification
            - Bottleneck ranking and recommendations
            - Variable reduced cost analysis
            - Sensitivity summary with key insights

    Example:
        >>> run_sensitivity_analysis()
        ============================================================
        SENSITIVITY ANALYSIS: Production Planning Solution Insights
        ============================================================

        CONSTRAINT SENSITIVITY ANALYSIS
        Shadow Price: 2.50 per unit (Labor Hours)
        Interpretation: Each additional labor hour increases profit by 2.50
        ...

    Notes:
        Sensitivity analysis requires:
            - The optimizer must support dual values (.enable_sensitivity())
            - The optimal solution must be available (not infeasible/unbounded)
            - Only works with LP models (not MIP)

        Key concepts demonstrated:
            - Shadow prices: marginal value of relaxing a constraint by one unit
            - Reduced costs: opportunity cost of forcing a variable into solution
            - Binding constraints: constraints satisfied with equality at optimum
            - Bottlenecks: binding constraints with high shadow prices

        Shadow prices are only valid within the allowable increase/decrease
        range. Beyond that range, the basis changes and shadow prices become
        invalid (though this example doesn't compute ranges).
    """

    print("=" * 80)
    print("SENSITIVITY ANALYSIS: Production Planning Solution Insights")
    print("=" * 80)

    # Build and solve model
    print("\nBuilding and solving base model...")
    model = build_production_model()
    optimizer = LXOptimizer().use_solver(solver_to_use).enable_sensitivity()
    solution = optimizer.solve(model)

    # Create sensitivity analyzer
    analyzer = LXSensitivityAnalyzer(model, solution)

    # Display solution summary
    print("\n" + "-" * 80)
    print("OPTIMAL SOLUTION SUMMARY")
    print("-" * 80)
    print(solution.summary())

    # Generate full sensitivity report
    print("\n" + "=" * 80)
    print("COMPREHENSIVE SENSITIVITY REPORT")
    print("=" * 80)
    print(analyzer.generate_report(include_variables=True, include_constraints=True))

    # Analyze constraint sensitivity
    print("\n" + "=" * 80)
    print("CONSTRAINT SENSITIVITY ANALYSIS")
    print("=" * 80)

    print("\nAnalyzing individual constraints:")
    for constraint in model.constraints:
        if constraint.name.startswith("capacity_"):
            sens = analyzer.analyze_constraint(constraint.name)
            print(f"\n  {constraint.name}:")
            print(f"    Shadow Price: ${sens.shadow_price:.4f}" if sens.shadow_price else "    Shadow Price: $0.0000")
            print(f"    Binding: {'YES' if sens.is_binding else 'NO'}")

            if sens.shadow_price and sens.shadow_price > 0.01:
                print(
                    f"    => Interpretation: Each additional unit of this resource "
                    f"increases profit by ${sens.shadow_price:.2f}"
                )

    # Find binding constraints
    print("\n" + "-" * 80)
    print("BINDING CONSTRAINTS (At Capacity)")
    print("-" * 80)

    binding = analyzer.get_binding_constraints()
    if binding:
        print(f"\nFound {len(binding)} binding constraints:")
        for name, sens in binding.items():
            print(f"  • {name}")
            print(f"    Shadow Price: ${sens.shadow_price:.4f}")
    else:
        print("\nNo binding constraints found (solution is interior)")

    # Identify bottlenecks
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

    # Top sensitive constraints
    print("\n" + "-" * 80)
    print("TOP 5 MOST VALUABLE CONSTRAINTS TO RELAX")
    print("-" * 80)

    top_constraints = analyzer.get_most_sensitive_constraints(top_n=5)
    if top_constraints:
        print("\nPrioritize relaxing these constraints for maximum profit impact:")
        for i, (name, sens) in enumerate(top_constraints, 1):
            print(f"\n  {i}. {name}")
            print(f"     Shadow Price: ${sens.shadow_price:.4f}")
            print(f"     Expected ROI: ${sens.shadow_price:.2f} per unit relaxation")
    else:
        print("\nNo constraints with significant shadow prices")

    # Variable sensitivity
    print("\n" + "=" * 80)
    print("VARIABLE SENSITIVITY ANALYSIS")
    print("=" * 80)

    print("\nAnalyzing production variables:")
    for var in model.variables:
        if var.name == "production":
            sens = analyzer.analyze_variable(var.name)
            print(f"\n  Variable: {var.name}")
            print(f"    Reduced Cost: ${sens.reduced_cost:.6f}" if sens.reduced_cost else "    Reduced Cost: $0.000000")
            print(f"    In Basis: {'YES' if sens.is_basic else 'NO'}")
            print(f"    At Bound: {'YES' if sens.is_at_bound else 'NO'}")

    # Non-basic variables
    print("\n" + "-" * 80)
    print("NON-BASIC VARIABLES (Not in Optimal Basis)")
    print("-" * 80)

    non_basic = analyzer.get_non_basic_variables()
    if non_basic:
        print(f"\nFound {len(non_basic)} non-basic variables:")
        for name, sens in non_basic.items():
            print(f"  • {name}")
            print(f"    Reduced Cost: ${sens.reduced_cost:.6f}")
            print(
                f"    Interpretation: Increasing this variable would "
                f"decrease profit by ${abs(sens.reduced_cost):.2f} per unit"
            )
    else:
        print("\nAll variables are basic (in optimal solution)")

    # Summary insights
    print("\n" + "=" * 80)
    print("SENSITIVITY SUMMARY")
    print("=" * 80)
    print(analyzer.generate_summary())


# ==================== BUSINESS INSIGHTS ====================


def extract_business_insights():
    """Extract actionable business insights from sensitivity analysis."""

    print("\n" + "=" * 80)
    print("BUSINESS INSIGHTS & RECOMMENDATIONS")
    print("=" * 80)

    # Build and solve
    model = build_production_model()
    optimizer = LXOptimizer().use_solver(solver_to_use).enable_sensitivity()
    solution = optimizer.solve(model)
    analyzer = LXSensitivityAnalyzer(model, solution)

    # Get top sensitive constraints
    top_constraints = analyzer.get_most_sensitive_constraints(top_n=3)

    print("\n1. RESOURCE INVESTMENT PRIORITIES")
    print("-" * 80)
    print("\nBased on shadow prices, prioritize investment in:")

    for i, (name, sens) in enumerate(top_constraints, 1):
        resource_name = name.replace("capacity_", "")
        print(f"\n  {i}. {resource_name}")
        print(f"     Marginal Value: ${sens.shadow_price:.2f} per unit")
        print(f"     Status: {'BINDING (at capacity)' if sens.is_binding else 'Not binding'}")

        # Investment recommendation
        if sens.shadow_price and sens.shadow_price > 1.0:
            print(f"     [HIGH PRIORITY]: Strong ROI expected from capacity expansion")
        elif sens.shadow_price and sens.shadow_price > 0.1:
            print(f"     [MODERATE PRIORITY]: Positive ROI from expansion")
        else:
            print(f"     [LOW PRIORITY]: Minimal impact from expansion")

    # Bottleneck analysis
    bottlenecks = analyzer.identify_bottlenecks()

    print("\n2. BOTTLENECK MITIGATION")
    print("-" * 80)

    if bottlenecks:
        print(f"\nIdentified {len(bottlenecks)} critical bottlenecks:")
        for name in bottlenecks:
            sens = analyzer.analyze_constraint(name)
            resource_name = name.replace("capacity_", "")
            print(f"\n  • {resource_name}")
            print(f"    Current Status: Operating at capacity")
            print(f"    Cost of Constraint: ${sens.shadow_price:.2f} per unit shortage")
            print(f"    Recommendation: Expand capacity or optimize usage")
    else:
        print("\n  * No critical bottlenecks identified")
        print("  * Current capacity is well-balanced")

    # Production efficiency
    print("\n3. PRODUCTION EFFICIENCY")
    print("-" * 80)

    print("\nOptimal production quantities:")
    for product in PRODUCTS:
        qty = solution.variables["production"][product.id]
        profit = (product.selling_price - product.unit_cost) * qty
        print(f"  • {product.name:15s}: {qty:6.1f} units  (profit: ${profit:,.2f})")

    # Strategic recommendations
    print("\n4. STRATEGIC RECOMMENDATIONS")
    print("-" * 80)

    print("\nBased on sensitivity analysis:")

    # Check if labor is binding
    labor_sens = analyzer.analyze_constraint("capacity_Labor Hours")
    if labor_sens.is_binding:
        print("\n  ► HIRING RECOMMENDATION:")
        print(f"    - Labor capacity is constraining profit")
        print(f"    - Each additional labor hour adds ${labor_sens.shadow_price:.2f} profit")
        print(f"    - Consider hiring if cost per hour < ${labor_sens.shadow_price:.2f}")

    # Check if machines are binding
    machine_sens = analyzer.analyze_constraint("capacity_Machine Hours")
    if machine_sens.is_binding:
        print("\n  ► EQUIPMENT INVESTMENT:")
        print(f"    - Machine capacity is constraining profit")
        print(f"    - Each additional machine hour adds ${machine_sens.shadow_price:.2f} profit")
        print(f"    - Evaluate ROI of new equipment based on this marginal value")

    # Check if materials are binding
    material_sens = analyzer.analyze_constraint("capacity_Raw Materials")
    if material_sens.is_binding:
        print("\n  ► SUPPLY CHAIN OPTIMIZATION:")
        print(f"    - Material availability is constraining profit")
        print(f"    - Each additional material unit adds ${material_sens.shadow_price:.2f} profit")
        print(f"    - Negotiate better supplier contracts or find alternative sources")

    print("\n5. RISK ASSESSMENT")
    print("-" * 80)

    binding = analyzer.get_binding_constraints()
    binding_count = len(binding)

    if binding_count >= 2:
        print("\n  ⚠ HIGH SENSITIVITY:")
        print(f"    - {binding_count} constraints are binding")
        print("    - Solution is highly sensitive to parameter changes")
        print("    - Small variations in capacity can significantly impact profit")
        print("    - Recommendation: Build buffer capacity or diversify resources")
    elif binding_count == 1:
        print("\n  ⚡ MODERATE SENSITIVITY:")
        print("    - One primary bottleneck identified")
        print("    - Focus on relaxing the binding constraint")
        print("    - Other resources have slack capacity")
    else:
        print("\n  * LOW SENSITIVITY:")
        print("    - No binding constraints")
        print("    - Solution is robust to small parameter changes")
        print("    - Excess capacity available")


# ==================== MAIN ====================


def main():
    """Run the complete sensitivity analysis example workflow.

    This function orchestrates a comprehensive demonstration of LumiX's
    sensitivity analysis capabilities by executing two related examples:
        1. Main sensitivity analysis with shadow prices and reduced costs
        2. Business insights extraction with investment recommendations

    The workflow demonstrates how to extract actionable business intelligence
    from optimization solutions by understanding the marginal value of
    resources and the economic structure of the optimal solution.

    Example:
        Run this example from the command line::

            $ python sensitivity_analysis.py

        Or import and run programmatically::

            >>> from sensitivity_analysis import main
            >>> main()

        Expected output includes:
            - Comprehensive sensitivity reports
            - Shadow prices for all constraints
            - Binding constraint identification
            - Bottleneck analysis and rankings
            - Variable reduced cost analysis
            - Investment recommendations based on marginal values
            - Risk assessment based on solution sensitivity

    Notes:
        This example demonstrates the complete LXSensitivityAnalyzer workflow:
            - Solving with sensitivity enabled
            - Analyzing individual constraints and variables
            - Identifying bottlenecks and binding constraints
            - Ranking resources by marginal value
            - Extracting business insights from dual values

        Sensitivity analysis is a powerful tool for:
            - Resource investment prioritization
            - Understanding capacity bottlenecks
            - Evaluating "what-if" questions
            - Assessing solution robustness
            - Making data-driven operational decisions

        The example uses OR-Tools which provides full sensitivity support
        for linear programming models.
    """

    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 18 + "LumiX Sensitivity Analysis Example" + " " * 24 + "║")
    print("╚" + "═" * 78 + "╝")

    # Main sensitivity analysis
    run_sensitivity_analysis()

    # Business insights
    extract_business_insights()

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print("\nKey Takeaways:")
    print("  * Shadow prices reveal the marginal value of relaxing constraints")
    print("  * Reduced costs show opportunity costs of changing variable values")
    print("  * Binding constraints identify current bottlenecks")
    print("  * Sensitivity analysis supports investment and resource decisions")
    print("  * Understanding duality provides powerful business insights")
    print()


if __name__ == "__main__":
    main()
