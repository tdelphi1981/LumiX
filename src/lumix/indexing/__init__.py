"""Multi-dimensional indexing support for LumiX optimization models.

This module provides powerful indexing capabilities for creating variables and constraints
indexed by one or more data models. It enables natural, type-safe multi-dimensional
indexing that preserves relationships between data models.

Key Components:
    - LXIndexDimension: Represents a single dimension of indexing with filtering support
    - LXCartesianProduct: Creates cartesian products of multiple dimensions for multi-model indexing

Features:
    - **Type-Safe**: Full generic type support with IDE autocomplete
    - **Data-Driven**: Automatic expansion based on data instances
    - **Filtering**: Both per-dimension and cross-dimension filtering
    - **Sparse Indexing**: Only create variables/constraints for valid combinations
    - **ORM Integration**: Works with direct data or ORM queries

Examples:
    Single-dimension indexing::

        from lumix import LXVariable, LXIndexDimension

        production = (
            LXVariable[Product, float]("production")
            .continuous()
            .indexed_by(lambda p: p.id)
            .from_data(products)
        )

    Multi-dimension indexing::

        from lumix import LXVariable, LXIndexDimension
        from typing import Tuple

        assignment = (
            LXVariable[Tuple[Driver, Date], int]("assignment")
            .binary()
            .indexed_by_product(
                LXIndexDimension(Driver, lambda d: d.id).from_data(drivers),
                LXIndexDimension(Date, lambda dt: dt.date).from_data(dates)
            )
            .where_multi(lambda driver, date: driver.is_available(date))
        )

    Three-dimensional indexing::

        from lumix import LXCartesianProduct, LXIndexDimension

        schedule = (
            LXVariable[Tuple[Driver, Date, Shift], int]("schedule")
            .binary()
            .indexed_by_product(
                LXIndexDimension(Driver, lambda d: d.id).from_data(drivers),
                LXIndexDimension(Date, lambda dt: dt.date).from_data(dates),
                LXIndexDimension(Shift, lambda s: s.id).from_data(shifts)
            )
        )

See Also:
    - :class:`~lumix.core.variables.LXVariable`: Uses indexing for variable families
    - :class:`~lumix.core.constraints.LXConstraint`: Uses indexing for constraint families
    - Driver Scheduling Example (examples/02_driver_scheduling): Comprehensive multi-model example

Module Structure:
    This module is part of LumiX's core architecture and is used extensively by the
    core module's variable and constraint systems to enable automatic expansion and
    data-driven modeling.
"""

from .cartesian import LXCartesianProduct
from .dimensions import LXIndexDimension

__all__ = ["LXIndexDimension", "LXCartesianProduct"]
