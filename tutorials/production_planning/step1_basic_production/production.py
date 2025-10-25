"""Basic Production Planning Optimization.

This example demonstrates how to build a production planning optimization model
using LumiX with **continuous variables**. The problem determines optimal production
quantities to maximize profit while respecting machine capacity, material availability,
and demand constraints.

Problem Description:
    A furniture factory produces chairs, tables, and desks. Each product:
        - Generates a specific profit per unit
        - Requires machine time on cutting and assembly equipment
        - Consumes raw materials (wood, metal, fabric)
        - Has minimum and maximum demand constraints

    Goal: Determine how many units of each product to manufacture to maximize
    total weekly profit while staying within resource limits.

Mathematical Formulation:
    Decision Variables:
        production[p] ≥ 0  (continuous, units of product p to produce)

    Objective:
        Maximize: Σ (profit[p] × production[p])  for all products p

    Subject to:
        - Machine capacity: Σ (hours_per_unit[p,m] × production[p]) ≤ available_hours[m]
        - Material availability: Σ (material_per_unit[p,mat] × production[p]) ≤ available[mat]
        - Demand bounds: min_demand[p] ≤ production[p] ≤ max_demand[p]

Key Features Demonstrated:
    - **Continuous variables** (not binary): Represent quantities, not assignments
    - **Single-dimensional indexing**: Variables indexed by Product only
    - **Resource consumption constraints**: Linear aggregation of resource usage
    - **Profit maximization**: Optimization objective (not just feasibility)
    - **Bounds on variables**: Lower and upper limits on production quantities

Use Cases:
    This pattern applies to:
        - Manufacturing production planning
        - Diet optimization (minimize cost, meet nutrition requirements)
        - Portfolio allocation (maximize return, limit risk)
        - Blending problems (mix ingredients to meet specifications)
        - Resource allocation (maximize value, respect capacity limits)

Learning Objectives:
    1. How to create continuous variables with bounds
    2. How to model resource consumption constraints
    3. How to formulate profit maximization objectives
    4. How to interpret continuous solution values
    5. Difference between binary (assignment) and continuous (quantity) problems

Next Steps:
    - Step 2: Add SQLite database for persistent data storage
    - Step 3: Add goal programming with customer order priorities
    - Step 4: Multi-period planning with setup costs and inventory
"""

from typing import Dict, List
from lumix import (
    LXModel,
    LXVariable,
    LXLinearExpression,
    LXConstraint,
    LXOptimizer,
)
from sample_data import (
    Product,
    Machine,
    RawMaterial,
    ProductionRecipe,
    MaterialRequirement,
    PRODUCTS,
    MACHINES,
    RAW_MATERIALS,
    PRODUCTION_RECIPES,
    MATERIAL_REQUIREMENTS,
    get_product_by_id,
    get_machine_by_id,
    get_material_by_id,
    get_machine_hours_required,
    get_material_required,
)


def build_production_model(
    products: List[Product],
    machines: List[Machine],
    materials: List[RawMaterial],
    recipes: List[ProductionRecipe],
    material_reqs: List[MaterialRequirement],
) -> LXModel:
    """Build the production planning optimization model.

    Args:
        products: List of products to manufacture
        machines: List of machines with capacity limits
        materials: List of raw materials with availability limits
        recipes: Machine time requirements for each product
        material_reqs: Material consumption for each product

    Returns:
        LXModel ready to be solved
    """
    print("Building production planning model...")
    print()

    # ========================================================================
    # Decision Variables: How many units of each product to produce
    # ========================================================================

    # KEY FEATURE: Continuous variables (not binary!)
    # production[p] represents the quantity of product p to manufacture
    # Indexed by Product only (1D, not 3D like timetabling)
    print("Creating decision variables...")
    production = (
        LXVariable[Product, float]("production")
        .continuous()
        .bounds(lower=0)  # Global lower bound (non-negative production)
        .indexed_by(lambda p: p.id)
        .from_data(products)
    )

    print(f"  Created {len(products)} continuous variables (one per product)")
    print()

    # ========================================================================
    # Objective: Maximize Total Profit
    # ========================================================================

    print("Defining objective function (maximize profit)...")

    # Build profit expression: Σ (profit[p] × production[p])
    profit_expr = LXLinearExpression()
    profit_expr.add_term(
        production,
        coeff=lambda p: p.profit_per_unit
    )

    # Create model with maximization objective
    model = LXModel("production_planning")
    model.add_variable(production)
    model.maximize(profit_expr)

    print(f"  Objective: Maximize Σ (profit × production)")
    print(f"  Profit coefficients: {[f'${p.profit_per_unit}' for p in products]}")
    print()

    # ========================================================================
    # Constraints: Machine Capacity
    # ========================================================================

    print("Adding machine capacity constraints...")
    machine_constraints_added = 0

    for machine in machines:
        # For this machine, sum up hours used by all products
        # Σ (hours_per_unit[p, m] × production[p]) ≤ available_hours[m]
        machine_hours_expr = LXLinearExpression()
        machine_hours_expr.add_term(
            production,
            coeff=lambda p, m=machine: get_machine_hours_required(p.id, m.id)
        )

        # Add constraint: total hours ≤ available hours
        model.add_constraint(
            LXConstraint(f"machine_capacity_{machine.name.replace(' ', '_')}")
            .expression(machine_hours_expr)
            .le()
            .rhs(machine.available_hours)
        )
        machine_constraints_added += 1

    print(f"  Added {machine_constraints_added} machine capacity constraints")
    print()

    # ========================================================================
    # Constraints: Material Availability
    # ========================================================================

    print("Adding material availability constraints...")
    material_constraints_added = 0

    for material in materials:
        # For this material, sum up consumption by all products
        # Σ (material_per_unit[p, mat] × production[p]) ≤ available[mat]
        material_usage_expr = LXLinearExpression()
        material_usage_expr.add_term(
            production,
            coeff=lambda p, mat=material: get_material_required(p.id, mat.id)
        )

        # Add constraint: total material used ≤ available
        model.add_constraint(
            LXConstraint(f"material_availability_{material.name.replace(' ', '_').replace('(', '').replace(')', '')}")
            .expression(material_usage_expr)
            .le()
            .rhs(material.available_quantity)
        )
        material_constraints_added += 1

    print(f"  Added {material_constraints_added} material availability constraints")
    print()

    # ========================================================================
    # Constraints: Demand Bounds (Min and Max)
    # ========================================================================

    print("Adding demand bound constraints...")
    demand_constraints_added = 0

    # Minimum demand constraints
    for product in products:
        if product.min_demand > 0:
            min_demand_expr = LXLinearExpression()
            min_demand_expr.add_term(
                production,
                coeff=1.0,
                where=lambda p, current_product=product: p.id == current_product.id
            )
            model.add_constraint(
                LXConstraint(f"min_demand_{product.name}")
                .expression(min_demand_expr)
                .ge()
                .rhs(product.min_demand)
            )
            demand_constraints_added += 1

    # Maximum demand constraints
    for product in products:
        max_demand_expr = LXLinearExpression()
        max_demand_expr.add_term(
            production,
            coeff=1.0,
            where=lambda p, current_product=product: p.id == current_product.id
        )
        model.add_constraint(
            LXConstraint(f"max_demand_{product.name}")
            .expression(max_demand_expr)
            .le()
            .rhs(product.max_demand)
        )
        demand_constraints_added += 1

    print(f"  Added {demand_constraints_added} demand bound constraints")
    print()

    # ========================================================================
    # Summary
    # ========================================================================

    total_constraints = machine_constraints_added + material_constraints_added + demand_constraints_added

    print("Model built successfully!")
    print(f"  Variables: {len(products)} continuous")
    print(f"  Constraints: {total_constraints} total")
    print(f"    - Machine capacity: {machine_constraints_added}")
    print(f"    - Material availability: {material_constraints_added}")
    print(f"    - Demand bounds: {demand_constraints_added}")
    print()

    return model


def display_solution(
    solution,
    products: List[Product],
    machines: List[Machine],
    materials: List[RawMaterial],
):
    """Display the optimization solution in a readable format.

    Args:
        solution: Solved LXSolution object
        products: List of products
        machines: List of machines
        materials: List of materials
    """
    print("=" * 80)
    print("PRODUCTION PLAN")
    print("=" * 80)
    print(f"Status: {solution.status}")
    print(f"Total Profit: ${solution.objective_value:,.2f}")
    print()

    # ========================================================================
    # Production Quantities
    # ========================================================================

    print("PRODUCTION QUANTITIES:")
    print("-" * 80)
    print(f"{'Product':<20} {'Quantity':<15} {'Profit/Unit':<15} {'Total Profit':<15}")
    print("-" * 80)

    production_values = {}
    for product in products:
        quantity = solution.variables["production"][product.id]
        production_values[product.id] = quantity
        total_profit = quantity * product.profit_per_unit

        print(f"{product.name:<20} {quantity:<15.2f} ${product.profit_per_unit:<14.2f} ${total_profit:<14.2f}")

    print("-" * 80)
    print(f"{'TOTAL':<20} {'':<15} {'':<15} ${solution.objective_value:<14,.2f}")
    print()

    # ========================================================================
    # Machine Utilization
    # ========================================================================

    print("MACHINE UTILIZATION:")
    print("-" * 80)
    print(f"{'Machine':<25} {'Hours Used':<15} {'Available':<15} {'Utilization':<15}")
    print("-" * 80)

    for machine in machines:
        hours_used = 0.0
        for product in products:
            quantity = production_values[product.id]
            hours_required = get_machine_hours_required(product.id, machine.id)
            hours_used += quantity * hours_required

        utilization = (hours_used / machine.available_hours) * 100 if machine.available_hours > 0 else 0

        print(f"{machine.name:<25} {hours_used:<15.2f} {machine.available_hours:<15.2f} {utilization:<14.1f}%")

    print()

    # ========================================================================
    # Material Consumption
    # ========================================================================

    print("MATERIAL CONSUMPTION:")
    print("-" * 80)
    print(f"{'Material':<30} {'Used':<15} {'Available':<15} {'Remaining':<15}")
    print("-" * 80)

    for material in materials:
        used = 0.0
        for product in products:
            quantity = production_values[product.id]
            material_required = get_material_required(product.id, material.id)
            used += quantity * material_required

        remaining = material.available_quantity - used

        print(f"{material.name:<30} {used:<15.2f} {material.available_quantity:<15.2f} {remaining:<15.2f}")

    print()

    # ========================================================================
    # Demand Analysis
    # ========================================================================

    print("DEMAND ANALYSIS:")
    print("-" * 80)
    print(f"{'Product':<20} {'Produced':<15} {'Min Demand':<15} {'Max Demand':<15} {'Status':<15}")
    print("-" * 80)

    for product in products:
        quantity = production_values[product.id]
        if quantity < product.min_demand + 0.01:
            status = "At Minimum"
        elif quantity > product.max_demand - 0.01:
            status = "At Maximum"
        else:
            status = "Within Range"

        print(f"{product.name:<20} {quantity:<15.2f} {product.min_demand:<15.2f} {product.max_demand:<15.2f} {status:<15}")

    print()


def main():
    """Main execution function."""
    print("=" * 80)
    print("LumiX Tutorial: Manufacturing Production Planning - Step 1")
    print("=" * 80)
    print()
    print("This example demonstrates:")
    print("  ✓ Continuous variables (production quantities)")
    print("  ✓ Resource consumption constraints")
    print("  ✓ Profit maximization objective")
    print("  ✓ Single-dimensional indexing (by Product)")
    print()

    # Build the model
    model = build_production_model(
        PRODUCTS,
        MACHINES,
        RAW_MATERIALS,
        PRODUCTION_RECIPES,
        MATERIAL_REQUIREMENTS,
    )

    # Solve the model
    print("Solving...")
    print()
    solver_to_use = "ortools"  # or "cpsat", "gurobi", etc.
    optimizer = LXOptimizer().use_solver(solver_to_use)
    solution = optimizer.solve(model)

    # Display results
    display_solution(solution, PRODUCTS, MACHINES, RAW_MATERIALS)

    print("=" * 80)
    print("Tutorial Step 1 Complete!")
    print("=" * 80)
    print()
    print("Key Learnings:")
    print("  → Continuous variables represent quantities (not binary assignments)")
    print("  → Resource constraints aggregate consumption across products")
    print("  → Profit maximization drives optimal production mix")
    print("  → Solution shows exact production quantities (e.g., 42.5 units)")
    print()
    print("Next Steps:")
    print("  → Step 2: Add SQLite database for persistent storage")
    print("  → Step 3: Add customer orders with goal programming")
    print("  → Step 4: Multi-period planning with setup costs")
    print()


if __name__ == "__main__":
    main()
