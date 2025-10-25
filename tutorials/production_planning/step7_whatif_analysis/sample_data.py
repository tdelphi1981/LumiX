"""Populate database with large-scale multi-period production planning data using ORM.

This script creates realistic large-scale data for Step 4:
- 9 products (3x Step 3)
- 6 machines (3x Step 3)
- 9 materials (3x Step 3)
- 4 periods (weeks)
- Production batches with minimum sizes
- Setup costs for production runs
- Customers with tier-based priorities
- Customer orders distributed across periods

Scale: ~1,600 decision variables (vs ~10 in Step 3)

Usage:
    python sample_data.py
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
    Period,
    ProductionBatch,
    SetupCost,
)


def populate_database(database_url: str = "sqlite:///production_whatif.db"):
    """Populate database with large-scale multi-period planning data using ORM."""
    print("=" * 80)
    print("PRODUCTION PLANNING DATABASE SETUP - STEP 7 (WHAT-IF ANALYSIS)")
    print("=" * 80)
    print("\nScale: 9 products × 6 machines × 9 materials × 4 periods")
    print("Expected variables: ~1,600 (16x Step 3)")
    print()

    engine = init_database(database_url)
    session = get_session(engine)

    try:
        print("Clearing existing data...")
        clear_all_data(session)
        print("  ✓ Data cleared\n")

        # ===== PERIODS =====
        print("Inserting planning periods...")
        periods = [
            Period(id=1, week_number=1, name="Week 1"),
            Period(id=2, week_number=2, name="Week 2"),
            Period(id=3, week_number=3, name="Week 3"),
            Period(id=4, week_number=4, name="Week 4"),
        ]
        session.add_all(periods)
        session.commit()
        print(f"  Added {len(periods)} planning periods\n")

        # ===== PRODUCTS (9 total - 3x scale) =====
        print("Inserting products...")
        products = [
            Product(id=1, name="Chair", profit_per_unit=45.0, min_demand=0.0, max_demand=100.0, holding_cost_per_unit=1.0),
            Product(id=2, name="Table", profit_per_unit=120.0, min_demand=0.0, max_demand=50.0, holding_cost_per_unit=3.0),
            Product(id=3, name="Desk", profit_per_unit=200.0, min_demand=0.0, max_demand=30.0, holding_cost_per_unit=5.0),
            Product(id=4, name="Sofa", profit_per_unit=350.0, min_demand=0.0, max_demand=20.0, holding_cost_per_unit=10.0),
            Product(id=5, name="Bookcase", profit_per_unit=150.0, min_demand=0.0, max_demand=40.0, holding_cost_per_unit=4.0),
            Product(id=6, name="Cabinet", profit_per_unit=180.0, min_demand=0.0, max_demand=35.0, holding_cost_per_unit=4.5),
            Product(id=7, name="Bed", profit_per_unit=400.0, min_demand=0.0, max_demand=15.0, holding_cost_per_unit=12.0),
            Product(id=8, name="Wardrobe", profit_per_unit=280.0, min_demand=0.0, max_demand=25.0, holding_cost_per_unit=8.0),
            Product(id=9, name="Nightstand", profit_per_unit=80.0, min_demand=0.0, max_demand=60.0, holding_cost_per_unit=2.0),
        ]
        session.add_all(products)
        session.commit()
        print(f"  Added {len(products)} products\n")

        # ===== MACHINES (6 total - 3x scale) =====
        # Increased capacity by 50% to enable higher order fulfillment
        print("Inserting machines...")
        machines = [
            Machine(id=1, name="Cutting Machine", available_hours=160.0, hourly_cost=50.0),
            Machine(id=2, name="Assembly Station", available_hours=200.0, hourly_cost=40.0),
            Machine(id=3, name="Finishing Station", available_hours=180.0, hourly_cost=45.0),
            Machine(id=4, name="Painting Booth", available_hours=140.0, hourly_cost=55.0),
            Machine(id=5, name="Upholstery Station", available_hours=100.0, hourly_cost=60.0),
            Machine(id=6, name="Packaging Line", available_hours=240.0, hourly_cost=30.0),
        ]
        session.add_all(machines)
        session.commit()
        print(f"  Added {len(machines)} machines\n")

        # ===== RAW MATERIALS (9 total - 3x scale) =====
        # Increased availability by 50% to enable higher order fulfillment
        print("Inserting raw materials...")
        materials = [
            RawMaterial(id=1, name="Wood (board feet)", available_quantity_per_period=1600.0, cost_per_unit=5.0),
            RawMaterial(id=2, name="Metal (pounds)", available_quantity_per_period=600.0, cost_per_unit=8.0),
            RawMaterial(id=3, name="Fabric (yards)", available_quantity_per_period=500.0, cost_per_unit=12.0),
            RawMaterial(id=4, name="Leather (sq ft)", available_quantity_per_period=300.0, cost_per_unit=25.0),
            RawMaterial(id=5, name="Glass (panels)", available_quantity_per_period=200.0, cost_per_unit=15.0),
            RawMaterial(id=6, name="Plastic (pounds)", available_quantity_per_period=400.0, cost_per_unit=4.0),
            RawMaterial(id=7, name="Foam (cu ft)", available_quantity_per_period=360.0, cost_per_unit=6.0),
            RawMaterial(id=8, name="Hardware (sets)", available_quantity_per_period=1000.0, cost_per_unit=3.0),
            RawMaterial(id=9, name="Paint (gallons)", available_quantity_per_period=240.0, cost_per_unit=20.0),
        ]
        session.add_all(materials)
        session.commit()
        print(f"  Added {len(materials)} raw materials\n")

        # ===== PRODUCTION RECIPES =====
        print("Inserting production recipes...")
        recipes = [
            # Chair: cutting, assembly, finishing, painting, packaging
            ProductionRecipe(product_id=1, machine_id=1, hours_required=0.5),
            ProductionRecipe(product_id=1, machine_id=2, hours_required=1.0),
            ProductionRecipe(product_id=1, machine_id=3, hours_required=0.5),
            ProductionRecipe(product_id=1, machine_id=4, hours_required=0.3),
            ProductionRecipe(product_id=1, machine_id=6, hours_required=0.2),

            # Table: cutting, assembly, finishing, painting, packaging
            ProductionRecipe(product_id=2, machine_id=1, hours_required=1.5),
            ProductionRecipe(product_id=2, machine_id=2, hours_required=2.5),
            ProductionRecipe(product_id=2, machine_id=3, hours_required=1.0),
            ProductionRecipe(product_id=2, machine_id=4, hours_required=0.8),
            ProductionRecipe(product_id=2, machine_id=6, hours_required=0.5),

            # Desk: cutting, assembly, finishing, packaging
            ProductionRecipe(product_id=3, machine_id=1, hours_required=2.0),
            ProductionRecipe(product_id=3, machine_id=2, hours_required=3.5),
            ProductionRecipe(product_id=3, machine_id=3, hours_required=1.5),
            ProductionRecipe(product_id=3, machine_id=6, hours_required=0.7),

            # Sofa: cutting, assembly, upholstery, packaging
            ProductionRecipe(product_id=4, machine_id=1, hours_required=3.0),
            ProductionRecipe(product_id=4, machine_id=2, hours_required=4.0),
            ProductionRecipe(product_id=4, machine_id=5, hours_required=5.0),
            ProductionRecipe(product_id=4, machine_id=6, hours_required=1.0),

            # Bookcase: cutting, assembly, finishing, painting, packaging
            ProductionRecipe(product_id=5, machine_id=1, hours_required=1.8),
            ProductionRecipe(product_id=5, machine_id=2, hours_required=2.0),
            ProductionRecipe(product_id=5, machine_id=3, hours_required=0.8),
            ProductionRecipe(product_id=5, machine_id=4, hours_required=0.6),
            ProductionRecipe(product_id=5, machine_id=6, hours_required=0.4),

            # Cabinet: cutting, assembly, finishing, packaging
            ProductionRecipe(product_id=6, machine_id=1, hours_required=2.2),
            ProductionRecipe(product_id=6, machine_id=2, hours_required=2.8),
            ProductionRecipe(product_id=6, machine_id=3, hours_required=1.2),
            ProductionRecipe(product_id=6, machine_id=6, hours_required=0.5),

            # Bed: cutting, assembly, upholstery, packaging
            ProductionRecipe(product_id=7, machine_id=1, hours_required=3.5),
            ProductionRecipe(product_id=7, machine_id=2, hours_required=5.0),
            ProductionRecipe(product_id=7, machine_id=5, hours_required=3.0),
            ProductionRecipe(product_id=7, machine_id=6, hours_required=1.2),

            # Wardrobe: cutting, assembly, finishing, painting, packaging
            ProductionRecipe(product_id=8, machine_id=1, hours_required=4.0),
            ProductionRecipe(product_id=8, machine_id=2, hours_required=5.5),
            ProductionRecipe(product_id=8, machine_id=3, hours_required=2.0),
            ProductionRecipe(product_id=8, machine_id=4, hours_required=1.5),
            ProductionRecipe(product_id=8, machine_id=6, hours_required=0.8),

            # Nightstand: cutting, assembly, finishing, painting, packaging
            ProductionRecipe(product_id=9, machine_id=1, hours_required=0.8),
            ProductionRecipe(product_id=9, machine_id=2, hours_required=1.2),
            ProductionRecipe(product_id=9, machine_id=3, hours_required=0.6),
            ProductionRecipe(product_id=9, machine_id=4, hours_required=0.4),
            ProductionRecipe(product_id=9, machine_id=6, hours_required=0.3),
        ]
        session.add_all(recipes)
        session.commit()
        print(f"  Added {len(recipes)} production recipes\n")

        # ===== MATERIAL REQUIREMENTS =====
        print("Inserting material requirements...")
        requirements = [
            # Chair: wood, metal, fabric, hardware, paint
            MaterialRequirement(product_id=1, material_id=1, quantity_required=8.0),
            MaterialRequirement(product_id=1, material_id=2, quantity_required=2.0),
            MaterialRequirement(product_id=1, material_id=3, quantity_required=2.0),
            MaterialRequirement(product_id=1, material_id=8, quantity_required=1.0),
            MaterialRequirement(product_id=1, material_id=9, quantity_required=0.5),

            # Table: wood, metal, hardware, paint
            MaterialRequirement(product_id=2, material_id=1, quantity_required=25.0),
            MaterialRequirement(product_id=2, material_id=2, quantity_required=5.0),
            MaterialRequirement(product_id=2, material_id=8, quantity_required=2.0),
            MaterialRequirement(product_id=2, material_id=9, quantity_required=1.0),

            # Desk: wood, metal, glass, hardware
            MaterialRequirement(product_id=3, material_id=1, quantity_required=35.0),
            MaterialRequirement(product_id=3, material_id=2, quantity_required=8.0),
            MaterialRequirement(product_id=3, material_id=5, quantity_required=2.0),
            MaterialRequirement(product_id=3, material_id=8, quantity_required=3.0),

            # Sofa: wood, fabric, leather, foam, hardware
            MaterialRequirement(product_id=4, material_id=1, quantity_required=30.0),
            MaterialRequirement(product_id=4, material_id=3, quantity_required=20.0),
            MaterialRequirement(product_id=4, material_id=4, quantity_required=15.0),
            MaterialRequirement(product_id=4, material_id=7, quantity_required=12.0),
            MaterialRequirement(product_id=4, material_id=8, quantity_required=2.0),

            # Bookcase: wood, glass, hardware, paint
            MaterialRequirement(product_id=5, material_id=1, quantity_required=40.0),
            MaterialRequirement(product_id=5, material_id=5, quantity_required=4.0),
            MaterialRequirement(product_id=5, material_id=8, quantity_required=3.0),
            MaterialRequirement(product_id=5, material_id=9, quantity_required=1.2),

            # Cabinet: wood, metal, hardware
            MaterialRequirement(product_id=6, material_id=1, quantity_required=45.0),
            MaterialRequirement(product_id=6, material_id=2, quantity_required=10.0),
            MaterialRequirement(product_id=6, material_id=8, quantity_required=4.0),

            # Bed: wood, metal, fabric, foam, hardware
            MaterialRequirement(product_id=7, material_id=1, quantity_required=50.0),
            MaterialRequirement(product_id=7, material_id=2, quantity_required=12.0),
            MaterialRequirement(product_id=7, material_id=3, quantity_required=15.0),
            MaterialRequirement(product_id=7, material_id=7, quantity_required=18.0),
            MaterialRequirement(product_id=7, material_id=8, quantity_required=5.0),

            # Wardrobe: wood, metal, glass, hardware, paint
            MaterialRequirement(product_id=8, material_id=1, quantity_required=80.0),
            MaterialRequirement(product_id=8, material_id=2, quantity_required=15.0),
            MaterialRequirement(product_id=8, material_id=5, quantity_required=3.0),
            MaterialRequirement(product_id=8, material_id=8, quantity_required=6.0),
            MaterialRequirement(product_id=8, material_id=9, quantity_required=2.0),

            # Nightstand: wood, hardware, paint
            MaterialRequirement(product_id=9, material_id=1, quantity_required=12.0),
            MaterialRequirement(product_id=9, material_id=8, quantity_required=1.0),
            MaterialRequirement(product_id=9, material_id=9, quantity_required=0.6),
        ]
        session.add_all(requirements)
        session.commit()
        print(f"  Added {len(requirements)} material requirements\n")

        # ===== PRODUCTION BATCHES =====
        print("Inserting production batches...")
        batches = [
            ProductionBatch(product_id=1, min_batch_size=10.0),
            ProductionBatch(product_id=2, min_batch_size=5.0),
            ProductionBatch(product_id=3, min_batch_size=5.0),
            ProductionBatch(product_id=4, min_batch_size=3.0),
            ProductionBatch(product_id=5, min_batch_size=8.0),
            ProductionBatch(product_id=6, min_batch_size=6.0),
            ProductionBatch(product_id=7, min_batch_size=3.0),
            ProductionBatch(product_id=8, min_batch_size=4.0),
            ProductionBatch(product_id=9, min_batch_size=12.0),
        ]
        session.add_all(batches)
        session.commit()
        print(f"  Added {len(batches)} production batch constraints\n")

        # ===== SETUP COSTS =====
        print("Inserting setup costs...")
        setup_costs = []
        # Generate setup costs for major production steps
        for product_id in range(1, 10):
            # Cutting machine setup
            setup_costs.append(SetupCost(product_id=product_id, machine_id=1, cost=100.0, setup_hours=2.0))
            # Assembly station setup
            setup_costs.append(SetupCost(product_id=product_id, machine_id=2, cost=150.0, setup_hours=3.0))

        session.add_all(setup_costs)
        session.commit()
        print(f"  Added {len(setup_costs)} setup cost entries\n")

        # ===== CUSTOMERS =====
        print("Inserting customers...")
        customers = [
            Customer(id=1, name="Premium Furniture Co.", tier="GOLD", priority_level=1),
            Customer(id=2, name="Global Office Supplies", tier="GOLD", priority_level=1),
            Customer(id=3, name="Corporate Furnishings Ltd.", tier="GOLD", priority_level=1),
            Customer(id=4, name="Regional Retail Chain", tier="SILVER", priority_level=2),
            Customer(id=5, name="Educational Institutions", tier="SILVER", priority_level=2),
            Customer(id=6, name="Hotel Group", tier="SILVER", priority_level=2),
            Customer(id=7, name="Small Business Network", tier="BRONZE", priority_level=3),
            Customer(id=8, name="Startup Collective", tier="BRONZE", priority_level=3),
        ]
        session.add_all(customers)
        session.commit()
        print(f"  Added {len(customers)} customers\n")

        # ===== CUSTOMER ORDERS =====
        print("Inserting customer orders across periods...")
        orders = [
            # Week 1 orders
            CustomerOrder(customer_id=1, product_id=3, period_id=1, target_quantity=20.0, priority=1),
            CustomerOrder(customer_id=1, product_id=2, period_id=1, target_quantity=30.0, priority=1),
            CustomerOrder(customer_id=2, product_id=1, period_id=1, target_quantity=80.0, priority=1),
            CustomerOrder(customer_id=4, product_id=5, period_id=1, target_quantity=25.0, priority=2),
            CustomerOrder(customer_id=7, product_id=9, period_id=1, target_quantity=40.0, priority=3),

            # Week 2 orders
            CustomerOrder(customer_id=3, product_id=4, period_id=2, target_quantity=15.0, priority=1),
            CustomerOrder(customer_id=5, product_id=1, period_id=2, target_quantity=60.0, priority=2),
            CustomerOrder(customer_id=5, product_id=3, period_id=2, target_quantity=15.0, priority=2),
            CustomerOrder(customer_id=8, product_id=6, period_id=2, target_quantity=20.0, priority=3),

            # Week 3 orders
            CustomerOrder(customer_id=2, product_id=7, period_id=3, target_quantity=10.0, priority=1),
            CustomerOrder(customer_id=6, product_id=4, period_id=3, target_quantity=12.0, priority=2),
            CustomerOrder(customer_id=7, product_id=2, period_id=3, target_quantity=18.0, priority=3),

            # Week 4 orders
            CustomerOrder(customer_id=1, product_id=8, period_id=4, target_quantity=20.0, priority=1),
            CustomerOrder(customer_id=4, product_id=9, period_id=4, target_quantity=50.0, priority=2),
            CustomerOrder(customer_id=8, product_id=1, period_id=4, target_quantity=35.0, priority=3),
        ]
        session.add_all(orders)
        session.commit()
        print(f"  Added {len(orders)} customer orders across 4 periods\n")

        # ===== SUMMARY =====
        print("=" * 80)
        print("Database populated successfully!")
        print("=" * 80)
        print(f"  Periods:               {len(periods)}")
        print(f"  Products:              {len(products)} (3x Step 3)")
        print(f"  Machines:              {len(machines)} (3x Step 3)")
        print(f"  Raw Materials:         {len(materials)} (3x Step 3)")
        print(f"  Production Recipes:    {len(recipes)}")
        print(f"  Material Requirements: {len(requirements)}")
        print(f"  Production Batches:    {len(batches)}")
        print(f"  Setup Costs:           {len(setup_costs)}")
        print(f"  Customers:             {len(customers)}")
        print(f"  Customer Orders:       {len(orders)}")
        print()
        print("Problem Scale:")
        print(f"  Variables:    ~{len(products) * len(periods) * 100:.0f} (estimated)")
        print(f"  Constraints:  ~{(len(machines) + len(materials)) * len(periods) * 10:.0f} (estimated)")
        print("=" * 80)
        print("\nNext step: Run 'python production_whatif.py' to solve with what-if analysis")
        print()

    finally:
        session.close()


if __name__ == "__main__":
    populate_database()
