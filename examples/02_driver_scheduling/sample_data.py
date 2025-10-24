"""Sample data classes for driver scheduling example.

This module provides data models and sample data for the driver scheduling
optimization example, which demonstrates LumiX's multi-model indexing capabilities.

The driver scheduling problem involves:
    - Multiple drivers with different availability and cost rates
    - Multiple dates with varying coverage requirements and overtime rates
    - Binary decisions: assign driver to date or not
    - Variables indexed by (Driver × Date) cartesian product

This is one of the most powerful features of LumiX, allowing natural expression
of multi-dimensional decision variables without manual index management.

Example:
    Create a multi-indexed variable family::

        duty = LXVariable[Tuple[Driver, Date], int]("duty")
            .binary()
            .indexed_by_product(
                LXIndexDimension(Driver, lambda d: d.id).from_data(DRIVERS),
                LXIndexDimension(Date, lambda dt: dt.date).from_data(DATES)
            )

Notes:
    The cartesian product indexing means that each (driver, date) combination
    gets its own binary variable, making the model naturally express the
    assignment problem structure.
"""

import datetime
from dataclasses import dataclass
from typing import List


@dataclass
class Driver:
    """Represents a delivery driver with availability and cost information.

    This class models a driver who can be assigned to work on specific dates,
    with constraints on maximum working days and scheduled days off.

    Attributes:
        id: Unique identifier for the driver.
        name: Human-readable driver name.
        daily_rate: Base cost per day in dollars (before overtime multipliers).
        max_days_per_week: Maximum number of days the driver can work per week.
        is_active: Whether the driver is currently available for scheduling.
        days_off: List of unavailable weekday numbers (0=Monday, 1=Tuesday, ..., 6=Sunday).

    Example:
        >>> driver = Driver(
        ...     id=1, name="Alice", daily_rate=150.0,
        ...     max_days_per_week=5, is_active=True, days_off=[6]
        ... )
        >>> print(f"{driver.name} costs ${driver.daily_rate}/day")
        Alice costs $150.0/day

    Notes:
        The max_days_per_week constraint is enforced in the optimization model
        by summing assignments across all dates for each driver.
    """

    id: int
    name: str
    daily_rate: float  # Base $ per day
    max_days_per_week: int  # Maximum days they can work
    is_active: bool  # Whether they're currently available
    days_off: List[int]  # List of weekday numbers (0=Monday, 6=Sunday)


@dataclass
class Date:
    """Represents a date in the scheduling period with coverage requirements.

    This class models a specific date with its coverage requirements and
    cost characteristics (e.g., overtime rates for weekends).

    Attributes:
        date: The calendar date being scheduled.
        overtime_multiplier: Cost multiplier applied to driver rates (e.g., 1.5 for weekends).
        min_drivers_required: Minimum number of drivers needed on this date.
        is_weekend: Whether this date falls on a weekend (Saturday or Sunday).

    Example:
        >>> weekend_date = Date(
        ...     date=datetime.date(2025, 1, 11),
        ...     overtime_multiplier=1.5,
        ...     min_drivers_required=2,
        ...     is_weekend=True
        ... )
        >>> print(f"Weekend cost multiplier: {weekend_date.overtime_multiplier}x")
        Weekend cost multiplier: 1.5x

    Notes:
        The min_drivers_required constraint is enforced in the optimization model
        by summing assignments across all drivers for each date.
    """

    date: datetime.date
    overtime_multiplier: float  # Cost multiplier (e.g., 1.5x for weekends)
    min_drivers_required: int  # Minimum drivers needed this day
    is_weekend: bool


# Sample drivers
DRIVERS = [
    Driver(
        id=1,
        name="Alice",
        daily_rate=150.0,
        max_days_per_week=5,
        is_active=True,
        days_off=[6],  # Sunday off
    ),
    Driver(
        id=2,
        name="Bob",
        daily_rate=120.0,
        max_days_per_week=6,
        is_active=True,
        days_off=[],  # Can work any day
    ),
    Driver(
        id=3,
        name="Charlie",
        daily_rate=100.0,
        max_days_per_week=4,
        is_active=True,
        days_off=[5, 6],  # Sat, Sun off
    ),
    Driver(
        id=4,
        name="Diana",
        daily_rate=140.0,
        max_days_per_week=5,
        is_active=True,
        days_off=[0],  # Mon off
    ),
    Driver(
        id=5,
        name="Eve",
        daily_rate=110.0,
        max_days_per_week=3,
        is_active=True,
        days_off=[1, 2, 5, 6],  # Only works Wed, Thu, Fri
    ),
    Driver(
        id=6,
        name="Frank",
        daily_rate=95.0,
        max_days_per_week=7,
        is_active=False,  # Not currently active
        days_off=[],
    ),
]


# Generate a week of dates (Monday through Sunday)
def generate_week_dates(start_date: datetime.date) -> List[Date]:
    """Generate a week of scheduling dates starting from a given Monday.

    Creates Date objects for a 7-day week (Monday through Sunday) with
    appropriate overtime multipliers and coverage requirements.

    Args:
        start_date: The starting date (should be a Monday).

    Returns:
        A list of 7 Date objects representing Monday through Sunday,
        with weekend dates having higher overtime multipliers (1.5x)
        and lower coverage requirements (2 vs 3 drivers).

    Example:
        >>> start = datetime.date(2025, 1, 6)  # Monday
        >>> week = generate_week_dates(start)
        >>> print(f"Generated {len(week)} dates")
        Generated 7 dates

    Notes:
        Weekend dates (Saturday, Sunday) automatically get:
            - overtime_multiplier = 1.5
            - min_drivers_required = 2 (vs 3 for weekdays)
    """
    dates = []
    for i in range(7):
        current_date = start_date + datetime.timedelta(days=i)
        is_weekend = current_date.weekday() >= 5  # Saturday, Sunday
        dates.append(
            Date(
                date=current_date,
                overtime_multiplier=1.5 if is_weekend else 1.0,
                min_drivers_required=2 if is_weekend else 3,  # Less on weekends
                is_weekend=is_weekend,
            )
        )
    return dates


# Week starting Monday, January 6, 2025
START_DATE = datetime.date(2025, 1, 6)  # Monday
DATES = generate_week_dates(START_DATE)


def is_driver_available(driver: Driver, date: Date) -> bool:
    """Check if a driver is available to work on a specific date.

    Determines whether a driver can be assigned to a date based on their
    active status and scheduled days off.

    Args:
        driver: The driver whose availability is being checked.
        date: The date for which availability is being checked.

    Returns:
        True if the driver is active and the date's weekday is not in
        their days_off list. False otherwise.

    Example:
        >>> driver = Driver(id=1, name="Alice", daily_rate=150,
        ...                 max_days_per_week=5, is_active=True, days_off=[6])
        >>> sunday = Date(date=datetime.date(2025, 1, 12), overtime_multiplier=1.5,
        ...               min_drivers_required=2, is_weekend=True)
        >>> is_driver_available(driver, sunday)
        False  # Sunday is in days_off

    Notes:
        This function is used in the where_multi() filter when defining
        the multi-indexed variable to exclude infeasible assignments.
    """
    if not driver.is_active:
        return False
    if date.date.weekday() in driver.days_off:
        return False
    return True


def calculate_cost(driver: Driver, date: Date) -> float:
    """Calculate the cost of assigning a driver to a specific date.

    Computes the total cost by applying the date's overtime multiplier
    to the driver's base daily rate.

    Args:
        driver: The driver being assigned.
        date: The date of assignment.

    Returns:
        The total cost in dollars: driver.daily_rate * date.overtime_multiplier.

    Example:
        >>> driver = Driver(id=1, name="Alice", daily_rate=100,
        ...                 max_days_per_week=5, is_active=True, days_off=[])
        >>> weekend = Date(date=datetime.date(2025, 1, 11), overtime_multiplier=1.5,
        ...                min_drivers_required=2, is_weekend=True)
        >>> cost = calculate_cost(driver, weekend)
        >>> print(f"Cost: ${cost}")
        Cost: $150.0

    Notes:
        This cost function is used in:
            - cost_multi() when defining the variable
            - The objective function expression
            - Solution display for reporting costs
    """
    return driver.daily_rate * date.overtime_multiplier
