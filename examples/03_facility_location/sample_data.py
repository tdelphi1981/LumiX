"""Sample data for facility location example."""

import math
from dataclasses import dataclass
from typing import Tuple


@dataclass
class Warehouse:
    """Potential warehouse location."""

    id: int
    name: str
    location: Tuple[float, float]  # (latitude, longitude)
    fixed_cost: float  # $ to open
    capacity: float  # maximum units


@dataclass
class Customer:
    """Customer with demand."""

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
    """
    Calculate distance between two lat/long coordinates in miles.
    Uses Haversine formula.
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
    """
    Calculate shipping cost from warehouse to customer.
    Cost = $0.10 per unit per 100 miles.
    """
    distance = haversine_distance(warehouse.location, customer.location)
    cost_per_unit_per_mile = 0.001  # $0.10 per 100 miles = $0.001 per mile
    return distance * cost_per_unit_per_mile


# Big-M constant (large number for big-M formulation)
BIG_M = sum(c.demand for c in CUSTOMERS)  # Total demand is a good upper bound
