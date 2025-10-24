"""Sample data classes for sensitivity analysis example.

This module provides data models and sample data for the sensitivity analysis
optimization example. The classes are designed to simulate ORM models from
database frameworks like SQLAlchemy or Django ORM.

Problem Context:
    A manufacturing company wants to understand how changes in parameters
    (resource capacities, minimum requirements) affect the optimal solution.
    Sensitivity analysis helps identify which resources are most valuable
    (shadow prices) and which constraints are binding (at capacity).

Data Structure:
    - Products: Items manufactured with profit margins and resource consumption
    - Resources: Limited capacity constraints (labor, machines, materials)
    - Resource Usage: Many-to-many relationship between products and resources

Key Features:
    - Simple dataclass structure for easy understanding
    - Realistic production planning parameters
    - Multiple products with varying profitability
    - Three constrained resources (labor, machines, materials)
    - Minimum production requirements for customer orders

Use Cases:
    This data structure supports:
        - Production planning and optimization
        - Sensitivity analysis on constraints and variables
        - Shadow price calculation
        - Bottleneck identification
        - Marginal value analysis

Example:
    Use these models in sensitivity analysis::

        from sample_data import PRODUCTS, RESOURCES, get_resource_usage
        from lumix import LXSensitivityAnalyzer

        # Solve model and analyze
        solution = optimizer.solve(model)
        analyzer = LXSensitivityAnalyzer(model, solution)

        # Get shadow prices for resources
        labor_sens = analyzer.analyze_constraint("capacity_Labor Hours")
        print(f"Shadow price: ${labor_sens.shadow_price:.2f}")

Notes:
    In a real application, these dataclasses would be replaced with actual
    ORM models, and LumiX would work directly with database query results.
    The data follows standard relational database design patterns.

See Also:
    - sensitivity_analysis.py: Main sensitivity analysis using this data
    - Example 01 (production_planning): Similar data structure
    - Example 08 (scenario_analysis): Alternative analysis approach
"""

from dataclasses import dataclass


@dataclass
class Product:
    """Represents a product that can be manufactured.

    This class models a product with its economic characteristics and
    resource consumption requirements. Each product has a profit margin
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
        ...     id=1, name="Widget A", selling_price=100.0, unit_cost=50.0,
        ...     labor_hours=5.0, machine_hours=3.0, material_units=2.0,
        ...     min_production=10
        ... )
        >>> profit_margin = widget.selling_price - widget.unit_cost
        >>> print(f"Profit per unit: ${profit_margin}")
        Profit per unit: $50.0

    Notes:
        Profit margin = selling_price - unit_cost
        This is used as the coefficient in the objective function.
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
    or raw materials. Each resource has a maximum capacity that limits total
    production.

    Attributes:
        id: Unique identifier for the resource.
        name: Human-readable resource name (e.g., "Labor Hours", "Machine Hours").
        capacity: Maximum available quantity per planning period (e.g., per week).

    Example:
        >>> labor = Resource(id=1, name="Labor Hours", capacity=1000.0)
        >>> print(f"{labor.name}: {labor.capacity} hours available per week")
        Labor Hours: 1000.0 hours available per week

    Notes:
        Capacity constraints are modeled as inequality constraints:
        sum(resource_usage[p,r] * production[p]) <= capacity[r]

        In sensitivity analysis, shadow prices reveal the marginal value
        of relaxing these capacity constraints.
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
    resources in optimization models. In a real ORM application, this might be
    a database relationship or join query.

    Args:
        product: The product for which to retrieve resource usage.
        resource: The resource whose usage amount is being queried.

    Returns:
        The quantity of the specified resource required to produce one unit
        of the product. Returns 0.0 if the resource is not used by the product.

    Example:
        >>> widget = Product(id=1, name="Widget A", selling_price=100, unit_cost=50,
        ...                  labor_hours=5.0, machine_hours=3.0, material_units=2.0,
        ...                  min_production=10)
        >>> labor = Resource(id=1, name="Labor Hours", capacity=1000)
        >>> usage = get_resource_usage(widget, labor)
        >>> print(f"{widget.name} requires {usage} hours of {labor.name}")
        Widget A requires 5.0 hours of Labor Hours

    Notes:
        This mapping approach allows for flexible resource-product relationships
        and can be easily extended to support additional resource types or
        database-backed lookups.

        In a real application with an ORM, this would typically be a database
        join query or relationship attribute (e.g., product.resources).
    """
    if resource.name == "Labor Hours":
        return product.labor_hours
    elif resource.name == "Machine Hours":
        return product.machine_hours
    elif resource.name == "Raw Materials":
        return product.material_units
    else:
        return 0.0
