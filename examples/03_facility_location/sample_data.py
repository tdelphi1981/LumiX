"""Sample data classes for facility location example.

This module provides data models and sample data for the facility location
optimization example, which demonstrates mixed-integer programming with
binary decision variables and Big-M constraints.

The facility location problem involves:
    - Binary decisions: which warehouses to open (fixed costs)
    - Continuous decisions: how much to ship from each warehouse to each customer
    - Conditional constraints: can only ship from open warehouses
    - Geographic considerations: shipping costs based on distance

In a real-world application, these dataclasses would be replaced with your
actual database models (e.g., SQLAlchemy, Django ORM), and LumiX would work
directly with ORM query results.

Example:
    Use these models to create optimization variables::

        open_warehouse = (
            LXVariable[Warehouse, int]("open_warehouse")
            .binary()
            .indexed_by(lambda w: w.id)
            .from_data(WAREHOUSES)
        )

        ship = (
            LXVariable[Tuple[Warehouse, Customer], float]("ship")
            .continuous()
            .indexed_by_product(
                LXIndexDimension(Warehouse, lambda w: w.id).from_data(WAREHOUSES),
                LXIndexDimension(Customer, lambda c: c.id).from_data(CUSTOMERS)
            )
        )

Notes:
    The geographic location data uses actual latitude/longitude coordinates,
    and the haversine formula calculates great-circle distances. This makes
    the example realistic for real-world logistics planning.
"""

import math
from dataclasses import dataclass
from typing import Tuple


@dataclass
class Warehouse:
    """Represents a potential warehouse location with costs and capacity.

    This class models a facility location decision: whether to open a warehouse
    and, if opened, how much to ship from it. Each warehouse has both fixed
    costs (one-time opening cost) and variable costs (shipping).

    Attributes:
        id: Unique identifier for the warehouse.
        name: Human-readable warehouse name with location (e.g., "Warehouse A (New York)").
        location: Geographic coordinates as (latitude, longitude) tuple.
        fixed_cost: One-time cost to open the warehouse, in dollars.
        capacity: Maximum shipping capacity per period (e.g., units per week).

    Example:
        >>> warehouse = Warehouse(
        ...     id=1, name="Warehouse A (New York)",
        ...     location=(40.7128, -74.0060),
        ...     fixed_cost=5000.0, capacity=500.0
        ... )
        >>> print(f"Opening cost: ${warehouse.fixed_cost:,.0f}")
        Opening cost: $5,000

    Notes:
        The fixed_cost creates a binary decision variable in the optimization:
        either pay the fixed cost and open (binary=1) or don't open (binary=0).
        This is a classic facility location formulation.
    """

    id: int
    name: str
    location: Tuple[float, float]  # (latitude, longitude)
    fixed_cost: float  # $ to open
    capacity: float  # maximum units


@dataclass
class Customer:
    """Represents a customer with demand and geographic location.

    This class models customer demand that must be satisfied by shipments
    from warehouses. Each customer has a specific demand quantity and
    location used for calculating shipping costs.

    Attributes:
        id: Unique identifier for the customer.
        name: Human-readable customer name.
        location: Geographic coordinates as (latitude, longitude) tuple.
        demand: Required quantity of goods, in units.

    Example:
        >>> customer = Customer(
        ...     id=1, name="Customer 1",
        ...     location=(40.0, -75.0),
        ...     demand=150.0
        ... )
        >>> print(f"{customer.name} needs {customer.demand} units")
        Customer 1 needs 150.0 units

    Notes:
        In the optimization model, the demand becomes a constraint:
        sum(shipments to customer) >= demand.
    """

    id: int
    name: str
    location: Tuple[float, float]  # (latitude, longitude)
    demand: float  # units needed


# Sample warehouses
WAREHOUSES = [
    Warehouse(1, "Warehouse A (New York)", (40.7128, -74.0060), 5000, 500),
    Warehouse(2, "Warehouse B (Los Angeles)", (34.0522, -118.2437), 6000, 600),
    Warehouse(3, "Warehouse C (Dallas)", (32.7767, -96.7970), 4500, 450),
    Warehouse(4, "Warehouse D (Miami)", (25.7617, -80.1918), 4000, 400),
    Warehouse(5, "Warehouse E (Seattle)", (47.6062, -122.3321), 5500, 550),
]

# Sample customers
CUSTOMERS = [
    Customer(1, "Customer 1", (40.0, -75.0), 150),
    Customer(2, "Customer 2", (34.5, -119.0), 120),
    Customer(3, "Customer 3", (41.0, -74.5), 200),
    Customer(4, "Customer 4", (33.0, -117.0), 80),
    Customer(5, "Customer 5", (32.5, -97.0), 160),
    Customer(6, "Customer 6", (48.0, -122.5), 140),
    Customer(7, "Customer 7", (26.0, -80.5), 100),
    Customer(8, "Customer 8", (47.5, -121.0), 90),
    Customer(9, "Customer 9", (33.5, -96.5), 110),
    Customer(10, "Customer 10", (40.5, -73.5), 130),
]


def haversine_distance(loc1: Tuple[float, float], loc2: Tuple[float, float]) -> float:
    """Calculate great-circle distance between two geographic coordinates.

    Uses the haversine formula to compute the shortest distance between two
    points on the surface of a sphere (Earth), given their latitude and
    longitude coordinates.

    Args:
        loc1: First location as (latitude, longitude) in decimal degrees.
        loc2: Second location as (latitude, longitude) in decimal degrees.

    Returns:
        The great-circle distance between the two locations, in miles.

    Example:
        >>> ny = (40.7128, -74.0060)  # New York
        >>> la = (34.0522, -118.2437)  # Los Angeles
        >>> distance = haversine_distance(ny, la)
        >>> print(f"Distance: {distance:.1f} miles")
        Distance: 2445.6 miles

    Notes:
        The formula is:
            a = sin²(Δlat/2) + cos(lat1) × cos(lat2) × sin²(Δlon/2)
            c = 2 × atan2(√a, √(1-a))
            d = R × c

        where R is Earth's radius (3959 miles), and Δlat, Δlon are the
        differences in latitude and longitude.

        This produces irrational numbers, which can be problematic for some
        solvers (like CP-SAT). Use rational arithmetic solvers (CPLEX, Gurobi,
        OR-Tools LP) for best results.
    """
    lat1, lon1 = loc1
    lat2, lon2 = loc2

    R = 3959  # Earth radius in miles

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.asin(math.sqrt(a))
    return R * c


def shipping_cost(warehouse: Warehouse, customer: Customer) -> float:
    """Calculate the shipping cost from a warehouse to a customer.

    Computes the variable cost of shipping one unit from the warehouse to
    the customer based on geographic distance. The cost model is:
    $0.10 per unit per 100 miles.

    Args:
        warehouse: The source warehouse location.
        customer: The destination customer location.

    Returns:
        The shipping cost per unit, in dollars.

    Example:
        >>> warehouse = Warehouse(1, "NY Warehouse", (40.7128, -74.0060), 5000, 500)
        >>> customer = Customer(1, "Customer", (40.0, -75.0), 150)
        >>> cost = shipping_cost(warehouse, customer)
        >>> print(f"Shipping cost: ${cost:.4f} per unit")
        Shipping cost: $0.0651 per unit

    Notes:
        The total shipping cost in the optimization is:
            shipping_cost(w, c) × quantity_shipped[w, c]

        This cost is part of the objective function, combined with the
        fixed costs of opening warehouses.
    """
    distance = haversine_distance(warehouse.location, customer.location)
    cost_per_unit_per_mile = 0.001  # $0.10 per 100 miles = $0.001 per mile
    return distance * cost_per_unit_per_mile


# Big-M constant (large number for big-M formulation)
BIG_M = sum(c.demand for c in CUSTOMERS)  # Total demand is a good upper bound
