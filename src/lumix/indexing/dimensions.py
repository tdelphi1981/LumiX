"""Index dimensions for multi-model indexing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Generic, List, Optional, Type, TypeVar

TModel = TypeVar("TModel")


@dataclass
class LXIndexDimension(Generic[TModel]):
    """
    Single dimension of a multi-dimensional index.

    Enables variables indexed by multiple data models like:
    - LXVariable indexed by (Driver, Date)
    - LXVariable indexed by (Warehouse, Customer)
    - LXVariable indexed by (Product, Location, TimePeriod)

    Example:
        driver_dim = (
            LXIndexDimension(Driver, lambda d: d.id)
            .from_data(drivers)
            .where(lambda d: d.is_active)
        )
    """

    model_type: Type[TModel]
    key_func: Callable[[TModel], Any]
    filter_func: Optional[Callable[[TModel], bool]] = None
    label: Optional[str] = None
    _data: Optional[List[TModel]] = None
    _session: Optional[Any] = None

    def from_data(self, data: List[TModel]) -> LXIndexDimension[TModel]:
        """
        Provide data instances directly.

        Args:
            data: List of model instances

        Returns:
            Self for chaining
        """
        self._data = data
        return self

    def from_model(self, session: Any) -> LXIndexDimension[TModel]:
        """
        Use ORM session for querying.

        Args:
            session: ORM session

        Returns:
            Self for chaining
        """
        self._session = session
        return self

    def get_instances(self) -> List[TModel]:
        """
        Get the data instances for this dimension.

        Returns:
            List of model instances

        Raises:
            ValueError: If no data source configured
        """
        if self._data is not None:
            instances = self._data
        elif self._session is not None:
            from ..utils.orm import LXTypedQuery
            query = LXTypedQuery(self._session, self.model_type)
            instances = query.all()
        else:
            raise ValueError(
                f"LXIndexDimension for {self.model_type.__name__} has no data source. "
                "Use .from_data(data) or .from_model(session)"
            )

        # Apply filter if present
        if self.filter_func is not None:
            instances = [inst for inst in instances if self.filter_func(inst)]

        return instances

    def where(self, predicate: Callable[[TModel], bool]) -> LXIndexDimension[TModel]:
        """
        Add filter to dimension.

        Args:
            predicate: Filter function

        Returns:
            Self for chaining

        Example:
            LXIndexDimension(Driver, lambda d: d.id).where(lambda d: d.is_active)
        """
        self.filter_func = predicate
        return self


__all__ = ["LXIndexDimension"]
