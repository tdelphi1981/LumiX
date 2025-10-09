"""
Sample data classes for production planning example.

These classes simulate ORM models (like SQLAlchemy, Django ORM, etc.)
In a real application, these would be your actual database models.
"""

from dataclasses import dataclass


@dataclass
class Product:
    """Represents a product that can be manufactured."""

    id: int
    name: str
    selling_price: float  # $ per unit
    unit_cost: float  # $ per unit (materials + labor)
    labor_hours: float  # hours per unit
    machine_hours: float  # hours per unit
    material_units: float  # units of raw material per product unit
    min_production: int  # minimum units to produce (customer orders)


@dataclass
class Resource:
    """Represents a limited resource (labor, machine, materials)."""

    id: int
    name: str
    capacity: float  # maximum available per week


# Sample products
PRODUCTS = [
    Product(
        id=1,
        name="Widget A",
        selling_price=100.0,
        unit_cost=50.0,
        labor_hours=5.0,
        machine_hours=3.0,
        material_units=2.0,
        min_production=10,
    ),
    Product(
        id=2,
        name="Widget B",
        selling_price=150.0,
        unit_cost=80.0,
        labor_hours=8.0,
        machine_hours=5.0,
        material_units=4.0,
        min_production=5,
    ),
    Product(
        id=3,
        name="Gadget X",
        selling_price=200.0,
        unit_cost=135.0,
        labor_hours=10.0,
        machine_hours=8.0,
        material_units=6.0,
        min_production=8,
    ),
    Product(
        id=4,
        name="Gadget Y",
        selling_price=120.0,
        unit_cost=70.0,
        labor_hours=6.0,
        machine_hours=4.0,
        material_units=3.0,
        min_production=12,
    ),
    Product(
        id=5,
        name="Premium Z",
        selling_price=300.0,
        unit_cost=200.0,
        labor_hours=15.0,
        machine_hours=12.0,
        material_units=8.0,
        min_production=3,
    ),
]

# Available resources
RESOURCES = [
    Resource(id=1, name="Labor Hours", capacity=1000.0),
    Resource(id=2, name="Machine Hours", capacity=800.0),
    Resource(id=3, name="Raw Materials", capacity=500.0),
]


def get_resource_usage(product: Product, resource: Resource) -> float:
    """
    Get how much of a resource a product uses.
    This demonstrates how you'd query relationships in a real ORM.
    """
    if resource.name == "Labor Hours":
        return product.labor_hours
    elif resource.name == "Machine Hours":
        return product.machine_hours
    elif resource.name == "Raw Materials":
        return product.material_units
    else:
        return 0.0
