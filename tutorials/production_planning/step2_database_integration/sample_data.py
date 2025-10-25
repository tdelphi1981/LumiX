"""Populate database with sample production planning data using SQLAlchemy ORM.

This module demonstrates how to populate a SQLAlchemy database using ORM
session operations instead of raw SQL INSERT statements. This approach provides:
    - Type safety: IDE autocomplete for model attributes
    - Automatic foreign key handling
    - Transaction management
    - Cleaner, more maintainable code

Usage:
    Run this script to populate the database:

    >>> python sample_data.py

    Or import and call populate_database():

    >>> from sample_data import populate_database
    >>> populate_database()
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
)


def populate_database(database_url: str = "sqlite:///production.db"):
    """Populate database with sample production planning data using SQLAlchemy ORM.

    Creates and populates all tables with sample data:
        - 3 products (Chair, Table, Desk)
        - 2 machines (Cutting Machine, Assembly Station)
        - 3 raw materials (Wood, Metal, Fabric)
        - 6 production recipes
        - 8 material requirements

    Args:
        database_url: SQLAlchemy database URL

    Example:
        >>> populate_database("sqlite:///production.db")
        >>> print("Database populated successfully!")
    """
    print("=" * 80)
    print("PRODUCTION PLANNING DATABASE SETUP - STEP 2 (ORM)")
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
            Product(
                id=1,
                name="Chair",
                profit_per_unit=45.0,
                min_demand=10.0,
                max_demand=100.0
            ),
            Product(
                id=2,
                name="Table",
                profit_per_unit=120.0,
                min_demand=5.0,
                max_demand=50.0
            ),
            Product(
                id=3,
                name="Desk",
                profit_per_unit=200.0,
                min_demand=3.0,
                max_demand=30.0
            ),
        ]
        session.add_all(products)
        session.commit()

        for product in products:
            print(f"  {product.name}: Profit ${product.profit_per_unit}/unit, "
                  f"Demand {product.min_demand}-{product.max_demand} units")
        print()

        # ==================== INSERT MACHINES ====================
        print("Inserting machines...")
        machines = [
            Machine(
                id=1,
                name="Cutting Machine",
                available_hours=80.0
            ),
            Machine(
                id=2,
                name="Assembly Station",
                available_hours=100.0
            ),
        ]
        session.add_all(machines)
        session.commit()

        for machine in machines:
            print(f"  {machine.name}: {machine.available_hours} hours/week")
        print()

        # ==================== INSERT RAW MATERIALS ====================
        print("Inserting raw materials...")
        materials = [
            RawMaterial(
                id=1,
                name="Wood (board feet)",
                available_quantity=500.0,
                cost_per_unit=5.0
            ),
            RawMaterial(
                id=2,
                name="Metal (pounds)",
                available_quantity=200.0,
                cost_per_unit=8.0
            ),
            RawMaterial(
                id=3,
                name="Fabric (yards)",
                available_quantity=150.0,
                cost_per_unit=12.0
            ),
        ]
        session.add_all(materials)
        session.commit()

        for material in materials:
            print(f"  {material.name}: {material.available_quantity} units @ ${material.cost_per_unit}/unit")
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

        # Display recipes with ORM queries for names
        for recipe in recipes:
            product = session.query(Product).filter_by(id=recipe.product_id).first()
            machine = session.query(Machine).filter_by(id=recipe.machine_id).first()
            print(f"  {product.name} on {machine.name}: {recipe.hours_required} hours/unit")
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

        # Display requirements with ORM queries for names
        for req in requirements:
            product = session.query(Product).filter_by(id=req.product_id).first()
            material = session.query(RawMaterial).filter_by(id=req.material_id).first()
            print(f"  {product.name} requires {req.quantity_required} {material.name}")
        print()

        # ==================== SUMMARY ====================
        print("=" * 80)
        print("Database populated successfully!")
        print("=" * 80)
        print(f"  Products:              {len(products)}")
        print(f"  Machines:              {len(machines)}")
        print(f"  Raw Materials:         {len(materials)}")
        print(f"  Production Recipes:    {len(recipes)}")
        print(f"  Material Requirements: {len(requirements)}")
        print("=" * 80)
        print()
        print("Next step: Run 'python production_db.py' to solve the optimization")
        print()

    finally:
        session.close()


if __name__ == "__main__":
    populate_database()
