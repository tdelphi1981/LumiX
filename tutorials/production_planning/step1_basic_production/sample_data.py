"""Sample data for basic production planning.

This module defines the data structures and sample data for a simple manufacturing
production planning problem. A small factory produces furniture (chairs, tables, desks)
using shared machines and raw materials.

Data Models:
    - Product: Items manufactured with profit margins and demand constraints
    - Machine: Production equipment with limited capacity (hours per week)
    - RawMaterial: Materials consumed during production with limited availability
    - ProductionRecipe: How many machine hours each product requires
    - MaterialRequirement: How much material each product consumes

Problem Scale:
    - 3 Products (Chair, Table, Desk)
    - 2 Machines (Cutting Machine, Assembly Station)
    - 3 Raw Materials (Wood, Metal, Fabric)
    - Weekly planning horizon
"""

from dataclasses import dataclass
from typing import List


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class Product:
    """A product that can be manufactured.

    Attributes:
        id: Unique identifier
        name: Product name
        profit_per_unit: Profit earned per unit sold ($)
        min_demand: Minimum units to produce (customer commitments)
        max_demand: Maximum units that can be sold (market limit)
    """
    id: int
    name: str
    profit_per_unit: float
    min_demand: float
    max_demand: float


@dataclass
class Machine:
    """A production machine with limited capacity.

    Attributes:
        id: Unique identifier
        name: Machine name
        available_hours: Maximum hours available per week
    """
    id: int
    name: str
    available_hours: float


@dataclass
class RawMaterial:
    """A raw material consumed during production.

    Attributes:
        id: Unique identifier
        name: Material name
        available_quantity: Maximum units available per week
        cost_per_unit: Cost per unit ($) - for reference, not used in basic model
    """
    id: int
    name: str
    available_quantity: float
    cost_per_unit: float


@dataclass
class ProductionRecipe:
    """Defines how much machine time a product requires.

    Attributes:
        product_id: Which product
        machine_id: Which machine
        hours_required: Hours of machine time per unit of product
    """
    product_id: int
    machine_id: int
    hours_required: float


@dataclass
class MaterialRequirement:
    """Defines how much raw material a product consumes.

    Attributes:
        product_id: Which product
        material_id: Which material
        quantity_required: Units of material per unit of product
    """
    product_id: int
    material_id: int
    quantity_required: float


# ============================================================================
# Sample Data
# ============================================================================

# Products: Furniture items with profit margins and demand
PRODUCTS = [
    Product(
        id=1,
        name="Chair",
        profit_per_unit=45.0,
        min_demand=10.0,   # Must produce at least 10 chairs
        max_demand=100.0   # Market can absorb up to 100 chairs
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

# Machines: Production equipment with weekly capacity
MACHINES = [
    Machine(
        id=1,
        name="Cutting Machine",
        available_hours=80.0  # 2 workers × 40 hours/week
    ),
    Machine(
        id=2,
        name="Assembly Station",
        available_hours=100.0  # 2.5 workers × 40 hours/week
    ),
]

# Raw Materials: Limited supplies
RAW_MATERIALS = [
    RawMaterial(
        id=1,
        name="Wood (board feet)",
        available_quantity=500.0,  # 500 board feet available
        cost_per_unit=5.0
    ),
    RawMaterial(
        id=2,
        name="Metal (pounds)",
        available_quantity=200.0,  # 200 pounds available
        cost_per_unit=8.0
    ),
    RawMaterial(
        id=3,
        name="Fabric (yards)",
        available_quantity=150.0,  # 150 yards available
        cost_per_unit=12.0
    ),
]

# Production Recipes: Machine time requirements
# Format: (product_id, machine_id, hours_required_per_unit)
PRODUCTION_RECIPES = [
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

# Material Requirements: Material consumption per unit
# Format: (product_id, material_id, quantity_required_per_unit)
MATERIAL_REQUIREMENTS = [
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


# ============================================================================
# Helper Functions
# ============================================================================

def get_product_by_id(product_id: int) -> Product:
    """Retrieve a product by ID."""
    for product in PRODUCTS:
        if product.id == product_id:
            return product
    raise ValueError(f"Product with id {product_id} not found")


def get_machine_by_id(machine_id: int) -> Machine:
    """Retrieve a machine by ID."""
    for machine in MACHINES:
        if machine.id == machine_id:
            return machine
    raise ValueError(f"Machine with id {machine_id} not found")


def get_material_by_id(material_id: int) -> RawMaterial:
    """Retrieve a material by ID."""
    for material in RAW_MATERIALS:
        if material.id == material_id:
            return material
    raise ValueError(f"Material with id {material_id} not found")


def get_recipes_for_product(product_id: int) -> List[ProductionRecipe]:
    """Get all machine recipes for a product."""
    return [r for r in PRODUCTION_RECIPES if r.product_id == product_id]


def get_material_reqs_for_product(product_id: int) -> List[MaterialRequirement]:
    """Get all material requirements for a product."""
    return [m for m in MATERIAL_REQUIREMENTS if m.product_id == product_id]


def get_machine_hours_required(product_id: int, machine_id: int) -> float:
    """Get hours required for a product on a specific machine."""
    for recipe in PRODUCTION_RECIPES:
        if recipe.product_id == product_id and recipe.machine_id == machine_id:
            return recipe.hours_required
    return 0.0  # Product doesn't use this machine


def get_material_required(product_id: int, material_id: int) -> float:
    """Get material quantity required for a product."""
    for req in MATERIAL_REQUIREMENTS:
        if req.product_id == product_id and req.material_id == material_id:
            return req.quantity_required
    return 0.0  # Product doesn't use this material


if __name__ == "__main__":
    """Display sample data when run directly."""
    print("=" * 80)
    print("PRODUCTION PLANNING SAMPLE DATA")
    print("=" * 80)
    print()

    print("PRODUCTS:")
    print("-" * 80)
    for product in PRODUCTS:
        print(f"  {product.name}:")
        print(f"    Profit: ${product.profit_per_unit}/unit")
        print(f"    Demand: {product.min_demand}-{product.max_demand} units/week")
    print()

    print("MACHINES:")
    print("-" * 80)
    for machine in MACHINES:
        print(f"  {machine.name}: {machine.available_hours} hours/week")
    print()

    print("RAW MATERIALS:")
    print("-" * 80)
    for material in RAW_MATERIALS:
        print(f"  {material.name}: {material.available_quantity} units available")
        print(f"    Cost: ${material.cost_per_unit}/unit")
    print()

    print("PRODUCTION RECIPES (Machine Hours per Unit):")
    print("-" * 80)
    for product in PRODUCTS:
        print(f"  {product.name}:")
        for recipe in get_recipes_for_product(product.id):
            machine = get_machine_by_id(recipe.machine_id)
            print(f"    {machine.name}: {recipe.hours_required} hours/unit")
    print()

    print("MATERIAL REQUIREMENTS (per Unit):")
    print("-" * 80)
    for product in PRODUCTS:
        print(f"  {product.name}:")
        for req in get_material_reqs_for_product(product.id):
            material = get_material_by_id(req.material_id)
            print(f"    {material.name}: {req.quantity_required} units/unit")
    print()

    print("=" * 80)
    print("Total Products: ", len(PRODUCTS))
    print("Total Machines: ", len(MACHINES))
    print("Total Materials:", len(RAW_MATERIALS))
    print("=" * 80)
