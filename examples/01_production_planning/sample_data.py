"""Sample data classes for production planning example.

This module provides data models and sample data for the production planning
optimization example. The classes are designed to simulate ORM models that
would typically come from database frameworks like SQLAlchemy or Django ORM.

The production planning problem involves:
    - Multiple products with different profitability and resource requirements
    - Limited resources (labor, machines, materials) with capacity constraints
    - Minimum production requirements to meet customer orders

In a real-world application, these dataclasses would be replaced with your
actual database models, and LumiX would work directly with ORM query results.

Example:
    Use these models to create optimization variables indexed by Product::

        production = (
            LXVariable[Product, float]("production")
            .continuous()
            .indexed_by(lambda p: p.id)
            .from_data(PRODUCTS)
        )

Notes:
    The data structure follows standard relational database design patterns,
    making it easy to adapt this example to work with real database models.
"""

from dataclasses import dataclass


@dataclass
class Product:
    """Represents a product that can be manufactured.

    This class models a product with its economic and resource consumption
    characteristics. Each product has a profit margin (selling_price - unit_cost)
    and requires various resources for production.

    Attributes:
        id: Unique identifier for the product.
        name: Human-readable product name.
        selling_price: Revenue per unit sold, in dollars.
        unit_cost: Total production cost per unit (materials + labor), in dollars.
        labor_hours: Labor time required per unit, in hours.
        machine_hours: Machine time required per unit, in hours.
        material_units: Raw material quantity required per unit.
        min_production: Minimum production quantity to meet customer orders.

    Example:
        >>> widget = Product(
        ...     id=1, name="Widget A", selling_price=100.0,
        ...     unit_cost=50.0, labor_hours=5.0, machine_hours=3.0,
        ...     material_units=2.0, min_production=10
        ... )
        >>> profit_margin = widget.selling_price - widget.unit_cost
        >>> print(f"Profit: ${profit_margin}")
        Profit: $50.0
    """

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
    """Represents a limited resource used in production.

    This class models a constrained resource such as labor hours, machine time,
    or raw materials. Each resource has a maximum capacity that constrains
    total production.

    Attributes:
        id: Unique identifier for the resource.
        name: Human-readable resource name (e.g., "Labor Hours", "Machine Hours").
        capacity: Maximum available quantity per planning period (e.g., per week).

    Example:
        >>> labor = Resource(id=1, name="Labor Hours", capacity=1000.0)
        >>> print(f"{labor.name}: {labor.capacity} hours available")
        Labor Hours: 1000.0 hours available

    Notes:
        Capacity constraints are modeled as inequality constraints in the
        optimization problem: sum(resource_usage) <= capacity.
    """

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
    """Get the amount of a specific resource required to produce one unit of a product.

    This function demonstrates how to query relationships between products and
    resources in optimization models. In a real application with an ORM, this
    might be a database relationship or join query.

    Args:
        product: The product for which to retrieve resource usage.
        resource: The resource whose usage amount is being queried.

    Returns:
        The quantity of the specified resource required to produce one unit
        of the product. Returns 0.0 if the resource is not used by the product.

    Example:
        >>> widget = Product(id=1, name="Widget", selling_price=100, unit_cost=50,
        ...                  labor_hours=5.0, machine_hours=3.0, material_units=2.0,
        ...                  min_production=10)
        >>> labor = Resource(id=1, name="Labor Hours", capacity=1000)
        >>> usage = get_resource_usage(widget, labor)
        >>> print(f"Usage: {usage} hours")
        Usage: 5.0 hours

    Notes:
        This mapping approach allows for flexible resource-product relationships
        and can be easily extended to support additional resource types or
        database-backed lookups.
    """
    if resource.name == "Labor Hours":
        return product.labor_hours
    elif resource.name == "Machine Hours":
        return product.machine_hours
    elif resource.name == "Raw Materials":
        return product.material_units
    else:
        return 0.0
