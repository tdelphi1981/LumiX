"""Populate database with customers and orders for goal programming using ORM.

This script extends Step 2 by adding customers with different tiers and
their production orders using SQLAlchemy ORM. Orders become soft constraints (goals)
in the optimization, with priorities based on customer tier.

Customer Tiers:
    - GOLD: Priority 1 (highest) - Premium customers
    - SILVER: Priority 2 (medium) - Regular customers
    - BRONZE: Priority 3 (lowest) - New/small customers

Usage:
    Run this script before running production_goals.py:

    >>> python sample_data.py
    >>> python production_goals.py
"""

from database import (
    init_database,
    get_session,
    clear_all_data,
    Product,
    Machine,
    RawMaterial,
    ProductionRecipe,
    MaterialRequirement,
    Customer,
    CustomerOrder,
    calculate_priority_from_tier,
)


def populate_database(database_url: str = "sqlite:///production.db"):
    """Populate database with customer orders for goal programming using ORM.

    Creates and populates all tables with sample data including:
        - 3 products (Chair, Table, Desk)
        - 2 machines (Cutting Machine, Assembly Station)
        - 3 raw materials (Wood, Metal, Fabric)
        - 6 production recipes
        - 7 material requirements
        - 5 customers (2 GOLD, 2 SILVER, 1 BRONZE)
        - 9 customer orders (soft constraints for goal programming)

    Args:
        database_url: SQLAlchemy database URL

    Example:
        >>> populate_database("sqlite:///production.db")
        >>> print("Database populated successfully!")
    """
    print("=" * 80)
    print("PRODUCTION PLANNING DATABASE SETUP - STEP 3 (GOAL PROGRAMMING with ORM)")
    print("=" * 80)
    print()

    # Initialize database and create tables
    print("Initializing database...")
    engine = init_database(database_url)
    session = get_session(engine)

    try:
        # Clear existing data
        print("Clearing existing data...")
        clear_all_data(session)
        print("  ✓ Data cleared")
        print()

        # ==================== INSERT PRODUCTS ====================
        print("Inserting products...")
        products = [
            Product(id=1, name="Chair", profit_per_unit=45.0, min_demand=0.0, max_demand=100.0),
            Product(id=2, name="Table", profit_per_unit=120.0, min_demand=0.0, max_demand=50.0),
            Product(id=3, name="Desk", profit_per_unit=200.0, min_demand=0.0, max_demand=30.0),
        ]
        session.add_all(products)
        session.commit()

        for product in products:
            print(f"  {product.name}: ${product.profit_per_unit}/unit")
        print()

        # ==================== INSERT MACHINES ====================
        print("Inserting machines...")
        machines = [
            Machine(id=1, name="Cutting Machine", available_hours=80.0),
            Machine(id=2, name="Assembly Station", available_hours=100.0),
        ]
        session.add_all(machines)
        session.commit()

        for machine in machines:
            print(f"  {machine.name}: {machine.available_hours} hours/week")
        print()

        # ==================== INSERT RAW MATERIALS ====================
        print("Inserting raw materials...")
        materials = [
            RawMaterial(id=1, name="Wood (board feet)", available_quantity=500.0, cost_per_unit=5.0),
            RawMaterial(id=2, name="Metal (pounds)", available_quantity=200.0, cost_per_unit=8.0),
            RawMaterial(id=3, name="Fabric (yards)", available_quantity=150.0, cost_per_unit=12.0),
        ]
        session.add_all(materials)
        session.commit()

        for material in materials:
            print(f"  {material.name}: {material.available_quantity} units")
        print()

        # ==================== INSERT PRODUCTION RECIPES ====================
        print("Inserting production recipes...")
        recipes = [
            # Chair: 0.5 hours cutting, 1.0 hours assembly
            ProductionRecipe(product_id=1, machine_id=1, hours_required=0.5),
            ProductionRecipe(product_id=1, machine_id=2, hours_required=1.0),

            # Table: 1.5 hours cutting, 2.5 hours assembly
            ProductionRecipe(product_id=2, machine_id=1, hours_required=1.5),
            ProductionRecipe(product_id=2, machine_id=2, hours_required=2.5),

            # Desk: 2.0 hours cutting, 3.5 hours assembly
            ProductionRecipe(product_id=3, machine_id=1, hours_required=2.0),
            ProductionRecipe(product_id=3, machine_id=2, hours_required=3.5),
        ]
        session.add_all(recipes)
        session.commit()

        print(f"  Added {len(recipes)} recipes")
        print()

        # ==================== INSERT MATERIAL REQUIREMENTS ====================
        print("Inserting material requirements...")
        requirements = [
            # Chair: 8 bf wood, 2 lbs metal, 2 yards fabric
            MaterialRequirement(product_id=1, material_id=1, quantity_required=8.0),
            MaterialRequirement(product_id=1, material_id=2, quantity_required=2.0),
            MaterialRequirement(product_id=1, material_id=3, quantity_required=2.0),

            # Table: 25 bf wood, 5 lbs metal, 0 fabric
            MaterialRequirement(product_id=2, material_id=1, quantity_required=25.0),
            MaterialRequirement(product_id=2, material_id=2, quantity_required=5.0),

            # Desk: 35 bf wood, 8 lbs metal, 0 fabric
            MaterialRequirement(product_id=3, material_id=1, quantity_required=35.0),
            MaterialRequirement(product_id=3, material_id=2, quantity_required=8.0),
        ]
        session.add_all(requirements)
        session.commit()

        print(f"  Added {len(requirements)} material requirements")
        print()

        # ==================== INSERT CUSTOMERS (NEW in Step 3) ====================
        print("Inserting customers with tier-based priorities...")
        customers = [
            # GOLD tier - Priority 1 (highest - standard GP convention)
            Customer(id=1, name="Premium Office Furniture Inc.", tier="GOLD",
                    priority_level=calculate_priority_from_tier("GOLD")),
            Customer(id=2, name="Global Workspace Solutions", tier="GOLD",
                    priority_level=calculate_priority_from_tier("GOLD")),

            # SILVER tier - Priority 2 (medium)
            Customer(id=3, name="Regional School District", tier="SILVER",
                    priority_level=calculate_priority_from_tier("SILVER")),
            Customer(id=4, name="Mid-Size Corp", tier="SILVER",
                    priority_level=calculate_priority_from_tier("SILVER")),

            # BRONZE tier - Priority 3 (lowest)
            Customer(id=5, name="Small Business Startup", tier="BRONZE",
                    priority_level=calculate_priority_from_tier("BRONZE")),
        ]
        session.add_all(customers)
        session.commit()

        for customer in customers:
            print(f"  [{customer.tier}] {customer.name} → Priority {customer.priority_level}")
        print()

        # ==================== INSERT CUSTOMER ORDERS (NEW in Step 3) ====================
        print("Inserting customer orders (soft constraints)...")

        orders = []

        # GOLD customers (Priority 1 = highest) - High-value orders
        orders.append(CustomerOrder(
            customer_id=1, product_id=3,  # Desk
            target_quantity=15.0, due_week=1, priority=calculate_priority_from_tier("GOLD")
        ))

        orders.append(CustomerOrder(
            customer_id=1, product_id=2,  # Table
            target_quantity=20.0, due_week=1, priority=calculate_priority_from_tier("GOLD")
        ))

        orders.append(CustomerOrder(
            customer_id=2, product_id=1,  # Chair
            target_quantity=50.0, due_week=1, priority=calculate_priority_from_tier("GOLD")
        ))

        orders.append(CustomerOrder(
            customer_id=2, product_id=3,  # Desk
            target_quantity=10.0, due_week=1, priority=calculate_priority_from_tier("GOLD")
        ))

        # SILVER customers (Priority 2 = medium) - Medium orders
        orders.append(CustomerOrder(
            customer_id=3, product_id=1,  # Chair
            target_quantity=30.0, due_week=1, priority=calculate_priority_from_tier("SILVER")
        ))

        orders.append(CustomerOrder(
            customer_id=3, product_id=2,  # Table
            target_quantity=10.0, due_week=1, priority=calculate_priority_from_tier("SILVER")
        ))

        orders.append(CustomerOrder(
            customer_id=4, product_id=3,  # Desk
            target_quantity=5.0, due_week=1, priority=calculate_priority_from_tier("SILVER")
        ))

        # BRONZE customers (Priority 3 = lowest) - Small orders
        orders.append(CustomerOrder(
            customer_id=5, product_id=1,  # Chair
            target_quantity=15.0, due_week=1, priority=calculate_priority_from_tier("BRONZE")
        ))

        orders.append(CustomerOrder(
            customer_id=5, product_id=2,  # Table
            target_quantity=8.0, due_week=1, priority=calculate_priority_from_tier("BRONZE")
        ))

        # Insert orders
        session.add_all(orders)
        session.commit()

        # Display orders with ORM queries for names
        for order in orders:
            customer = session.query(Customer).filter_by(id=order.customer_id).first()
            product = session.query(Product).filter_by(id=order.product_id).first()
            print(f"  [P{order.priority}] {customer.name}: {order.target_quantity} {product.name}s")

        print()

        # ==================== SUMMARY ====================
        priority_counts = {}
        for order in orders:
            priority_counts[order.priority] = priority_counts.get(order.priority, 0) + 1

        print("=" * 80)
        print("Database populated successfully!")
        print("=" * 80)
        print(f"  Products:              {len(products)}")
        print(f"  Machines:              {len(machines)}")
        print(f"  Raw Materials:         {len(materials)}")
        print(f"  Production Recipes:    {len(recipes)}")
        print(f"  Material Requirements: {len(requirements)}")
        print(f"  Customers:             {len(customers)}")
        print(f"  Customer Orders:       {len(orders)}")
        print()
        print("Priority Distribution (Standard GP: lower number = higher priority):")
        print(f"  Priority 1 (GOLD):   {priority_counts.get(1, 0)} orders → Highest priority")
        print(f"  Priority 2 (SILVER): {priority_counts.get(2, 0)} orders → Medium priority")
        print(f"  Priority 3 (BRONZE): {priority_counts.get(3, 0)} orders → Lowest priority")
        print("=" * 80)
        print()
        print("Next step: Run 'python production_goals.py' to solve with goal programming")
        print()

    finally:
        session.close()


if __name__ == "__main__":
    populate_database()
