"""Cartesian product support for multi-dimensional model indexing.

This module provides the LXCartesianProduct class, which combines multiple index
dimensions to create multi-dimensional index spaces. This enables variables and
constraints indexed by tuples of data models (e.g., (Driver, Date, Shift)).

Classes:
    LXCartesianProduct: Type-safe cartesian product of multiple index dimensions

Example:
    Two-dimensional product::

        from lumix import LXCartesianProduct, LXIndexDimension

        product = LXCartesianProduct(
            LXIndexDimension(Driver, lambda d: d.id).from_data(drivers),
            LXIndexDimension(Date, lambda dt: dt.date).from_data(dates)
        ).where(lambda driver, date: driver.is_available(date))

    Three-dimensional product::

        product = (
            LXCartesianProduct(
                LXIndexDimension(Driver, lambda d: d.id).from_data(drivers),
                LXIndexDimension(Date, lambda dt: dt.date).from_data(dates)
            )
            .add_dimension(LXIndexDimension(Shift, lambda s: s.id).from_data(shifts))
            .where(lambda driver, date, shift: driver.can_work_shift(shift))
        )

See Also:
    - :class:`~lumix.indexing.dimensions.LXIndexDimension`: Individual dimensions
    - :class:`~lumix.core.variables.LXVariable.indexed_by_product`: Uses cartesian products
    - Driver Scheduling Example (examples/02_driver_scheduling): Real-world usage
"""

from typing import Callable, Generic, Optional, TypeVar

from typing_extensions import Self

from .dimensions import LXIndexDimension

TModel1 = TypeVar("TModel1")
TModel2 = TypeVar("TModel2")


class LXCartesianProduct(Generic[TModel1, TModel2]):
    """Type-safe cartesian product of multiple index dimensions.

    LXCartesianProduct combines two or more index dimensions to create a multi-dimensional
    index space. This enables variables and constraints indexed by tuples of data models,
    such as (Driver, Date) or (Warehouse, Product, TimePeriod).

    The cartesian product generates all combinations of instances across dimensions, with
    optional cross-dimension filtering to create sparse index spaces (only valid combinations).

    This class is the foundation of LumiX's multi-model indexing capability, which is one
    of the library's most powerful features for complex scheduling, routing, and allocation
    problems.

    Type Parameters:
        TModel1: The data model type for the first dimension
        TModel2: The data model type for the second dimension

    Attributes:
        dimensions: List of LXIndexDimension objects defining each dimension
        _cross_filter: Optional predicate for filtering combinations across dimensions

    Examples:
        Basic two-dimensional product::

            product = LXCartesianProduct(
                LXIndexDimension(Driver, lambda d: d.id).from_data(drivers),
                LXIndexDimension(Date, lambda dt: dt.date).from_data(dates)
            )

        With cross-dimension filtering::

            product = LXCartesianProduct(
                LXIndexDimension(Driver, lambda d: d.id).from_data(drivers),
                LXIndexDimension(Date, lambda dt: dt.date).from_data(dates)
            ).where(lambda driver, date: date not in driver.days_off)

        Three-dimensional product::

            product = (
                LXCartesianProduct(
                    LXIndexDimension(Warehouse, lambda w: w.id).from_data(warehouses),
                    LXIndexDimension(Product, lambda p: p.sku).from_data(products)
                )
                .add_dimension(LXIndexDimension(Month, lambda m: m.id).from_data(months))
                .where(lambda w, p, m: w.stocks_product(p) and m.is_active)
            )

        Used in variable definition::

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

    See Also:
        - :class:`~lumix.indexing.dimensions.LXIndexDimension`: Individual dimensions
        - :meth:`lumix.core.variables.LXVariable.indexed_by_product`: Uses this class
        - Driver Scheduling Example (examples/02_driver_scheduling): Complete example

    Note:
        - The cartesian product follows lazy evaluation - combinations are generated
          only when needed during model solving
        - Cross-dimension filters (where()) are applied after per-dimension filters
        - For N dimensions, the product generates O(n1 × n2 × ... × nN) combinations
          before filtering
    """

    def __init__(self, dim1: LXIndexDimension[TModel1], dim2: LXIndexDimension[TModel2]):
        """Initialize a cartesian product with two dimensions.

        Creates a two-dimensional cartesian product. Additional dimensions can be added
        via add_dimension() for 3D, 4D, or higher-dimensional index spaces.

        Args:
            dim1: First index dimension
            dim2: Second index dimension

        Examples:
            Basic initialization::

                product = LXCartesianProduct(
                    LXIndexDimension(Driver, lambda d: d.id).from_data(drivers),
                    LXIndexDimension(Date, lambda dt: dt.date).from_data(dates)
                )

            With per-dimension filters::

                product = LXCartesianProduct(
                    LXIndexDimension(Driver, lambda d: d.id)
                        .from_data(drivers)
                        .where(lambda d: d.is_active),
                    LXIndexDimension(Date, lambda dt: dt.date)
                        .from_data(dates)
                        .where(lambda dt: dt.is_weekday)
                )
        """
        self.dimensions: list[LXIndexDimension] = [dim1, dim2]
        self._cross_filter: Optional[Callable] = None

    def __deepcopy__(self, memo):
        """Custom deepcopy that handles dimensions and cross-filter functions.

        This method enables what-if analysis on cartesian products by:
        1. Deep copying all index dimensions (with ORM data materialization)
        2. Safely copying the cross-filter lambda function

        Args:
            memo: Dictionary for tracking circular references during deepcopy

        Returns:
            Deep copy of this cartesian product with all dependencies resolved
        """
        from copy import deepcopy
        from ..utils.copy_utils import copy_function_detaching_closure

        # Create new instance without calling __init__
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result

        # Deep copy all dimensions
        # Each dimension's __deepcopy__ will materialize and detach ORM data
        result.dimensions = [deepcopy(dim, memo) for dim in self.dimensions]

        # Copy cross-filter function (may have closures capturing ORM objects)
        result._cross_filter = (
            copy_function_detaching_closure(self._cross_filter, memo)
            if self._cross_filter is not None
            else None
        )

        return result

    def add_dimension(self, dim: LXIndexDimension) -> Self:
        """Add another dimension to create 3D or higher-dimensional indexing.

        This method extends a two-dimensional product to three or more dimensions.
        Each additional dimension multiplies the number of combinations (before filtering).

        Args:
            dim: Additional index dimension to add

        Returns:
            Self for method chaining

        Examples:
            Three-dimensional indexing::

                product = (
                    LXCartesianProduct(
                        LXIndexDimension(Driver, lambda d: d.id).from_data(drivers),
                        LXIndexDimension(Date, lambda dt: dt.date).from_data(dates)
                    )
                    .add_dimension(LXIndexDimension(Shift, lambda s: s.id).from_data(shifts))
                )

            Four-dimensional indexing::

                product = (
                    LXCartesianProduct(
                        LXIndexDimension(Warehouse, lambda w: w.id).from_data(warehouses),
                        LXIndexDimension(Product, lambda p: p.sku).from_data(products)
                    )
                    .add_dimension(LXIndexDimension(Customer, lambda c: c.id).from_data(customers))
                    .add_dimension(LXIndexDimension(Month, lambda m: m.id).from_data(months))
                )

        Note:
            - Dimensions can be added in any order
            - The cross-filter predicate (if set via where()) must match the number of dimensions
            - Each added dimension increases the computational complexity exponentially
        """
        self.dimensions.append(dim)
        return self

    def where(self, predicate: Callable[[TModel1, TModel2], bool]) -> Self:
        """Apply cross-dimension filtering to the cartesian product.

        This method adds a filter that operates across all dimensions simultaneously,
        allowing you to exclude invalid combinations based on relationships between
        the dimension models. This is essential for creating sparse index spaces.

        The predicate function receives one instance from each dimension as arguments
        (in the order dimensions were added) and should return True for valid combinations.

        This is different from per-dimension filters (applied via LXIndexDimension.where()),
        which filter within a single dimension before the cartesian product is formed.

        Args:
            predicate: A function that takes one model instance from each dimension
                      and returns True if the combination is valid, False otherwise

        Returns:
            Self for method chaining

        Examples:
            Two-dimensional filtering::

                product = LXCartesianProduct(
                    LXIndexDimension(Driver, lambda d: d.id).from_data(drivers),
                    LXIndexDimension(Date, lambda dt: dt.date).from_data(dates)
                ).where(lambda driver, date: date not in driver.days_off)

            Three-dimensional filtering::

                product = (
                    LXCartesianProduct(
                        LXIndexDimension(Driver, lambda d: d.id).from_data(drivers),
                        LXIndexDimension(Date, lambda dt: dt.date).from_data(dates)
                    )
                    .add_dimension(LXIndexDimension(Shift, lambda s: s.id).from_data(shifts))
                    .where(lambda driver, date, shift:
                        driver.can_work_shift(shift) and
                        date not in driver.days_off and
                        shift.requires_certification <= driver.certifications
                    )
                )

            Complex business logic::

                product = LXCartesianProduct(
                    LXIndexDimension(Warehouse, lambda w: w.id).from_data(warehouses),
                    LXIndexDimension(Customer, lambda c: c.id).from_data(customers)
                ).where(lambda warehouse, customer:
                    warehouse.region == customer.region and
                    warehouse.can_ship_to(customer.zip_code) and
                    customer.preferred_warehouses is None or
                    warehouse.id in customer.preferred_warehouses
                )

        Note:
            - The predicate is called for every combination after per-dimension filters
            - Multiple where() calls override previous filters (not combine them)
            - For best performance, use per-dimension filters first, then cross-dimension filters
            - The function signature must match the number of dimensions

        Performance Tip:
            Apply filters that reduce data size at the dimension level (via
            LXIndexDimension.where()) before applying cross-dimension filters here.
            This reduces the number of combinations that need to be evaluated.

        See Also:
            - :meth:`lumix.indexing.dimensions.LXIndexDimension.where`: Per-dimension filtering
            - :meth:`lumix.core.variables.LXVariable.where_multi`: Alternative syntax
        """
        self._cross_filter = predicate
        return self


__all__ = ["LXCartesianProduct"]
