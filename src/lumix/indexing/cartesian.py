"""Cartesian product for multi-model indexing."""

from typing import Callable, Generic, Optional, TypeVar

from typing_extensions import Self

from .dimensions import LXIndexDimension

TModel1 = TypeVar("TModel1")
TModel2 = TypeVar("TModel2")


class LXCartesianProduct(Generic[TModel1, TModel2]):
    """
    Type-safe cartesian product for multi-model indexing.

    Enables variables indexed by multiple models:
    - LXVariable indexed by (Driver, Date)
    - LXVariable indexed by (Warehouse, Customer)
    - LXVariable indexed by (Driver, Date, Shift) - 3D+

    Example:
        product = LXCartesianProduct(
            LXIndexDimension(Driver, lambda d: d.id),
            LXIndexDimension(Date, lambda dt: dt.date)
        ).where(lambda driver, date: driver.available_dates.contains(date))
    """

    def __init__(self, dim1: LXIndexDimension[TModel1], dim2: LXIndexDimension[TModel2]):
        """
        Initialize cartesian product with two dimensions.

        Args:
            dim1: First dimension
            dim2: Second dimension
        """
        self.dimensions: list[LXIndexDimension] = [dim1, dim2]
        self._cross_filter: Optional[Callable] = None

    def add_dimension(self, dim: LXIndexDimension) -> Self:
        """
        Add another dimension for 3D+ indexing.

        Args:
            dim: Additional dimension

        Returns:
            Self for chaining

        Example:
            product.add_dimension(LXIndexDimension(Shift, lambda s: s.id))
        """
        self.dimensions.append(dim)
        return self

    def where(self, predicate: Callable[[TModel1, TModel2], bool]) -> Self:
        """
        Filter the cartesian product with cross-model constraints.

        Args:
            predicate: Filter function taking all dimension models

        Returns:
            Self for chaining

        Example:
            product.where(lambda driver, date: driver.available_dates.contains(date))
        """
        self._cross_filter = predicate
        return self


__all__ = ["LXCartesianProduct"]
