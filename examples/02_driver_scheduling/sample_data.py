"""
Sample data classes for driver scheduling example.

This demonstrates multi-model indexing with Driver × Date.
"""

import datetime
from dataclasses import dataclass
from typing import List


@dataclass
class Driver:
    """Represents a delivery driver."""

    id: int
    name: str
    daily_rate: float  # Base $ per day
    max_days_per_week: int  # Maximum days they can work
    is_active: bool  # Whether they're currently available
    days_off: List[int]  # List of weekday numbers (0=Monday, 6=Sunday)


@dataclass
class Date:
    """Represents a date in the scheduling period."""

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
        days_off=[0, 6],  # Mon, Sun off
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
    """Generate a week of dates starting from Monday."""
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
    """Check if a driver is available on a specific date."""
    if not driver.is_active:
        return False
    if date.date.weekday() in driver.days_off:
        return False
    return True


def calculate_cost(driver: Driver, date: Date) -> float:
    """Calculate cost for assigning a driver to a date."""
    return driver.daily_rate * date.overtime_multiplier
