"""Index dimension definitions for multi-dimensional model indexing.

This module provides the LXIndexDimension class, which represents a single dimension
in multi-dimensional indexing. Index dimensions can be combined via cartesian products
to create multi-model indexed variables and constraints.

Classes:
    LXIndexDimension: A single dimension of a multi-dimensional index with filtering
                      and data source configuration

Example:
    Creating a dimension with filtering::

        from lumix import LXIndexDimension

        driver_dim = (
            LXIndexDimension(Driver, lambda d: d.id)
            .from_data(drivers)
            .where(lambda d: d.is_active and d.years_experience >= 2)
        )

    Using with ORM::

        driver_dim = (
            LXIndexDimension(Driver, lambda d: d.id)
            .from_model(session)
            .where(lambda d: d.is_active)
        )

See Also:
    - :class:`~lumix.indexing.cartesian.LXCartesianProduct`: Combines dimensions
    - :class:`~lumix.core.variables.LXVariable`: Uses dimensions for indexing
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Generic, List, Optional, Type, TypeVar

TModel = TypeVar("TModel")


@dataclass
class LXIndexDimension(Generic[TModel]):
    """Represents a single dimension in multi-dimensional model indexing.

    An LXIndexDimension defines one dimension of a potentially multi-dimensional index space.
    It encapsulates the model type, indexing function, optional filters, and data source for
    that dimension. Dimensions can be combined via LXCartesianProduct to create multi-model
    indexed variables and constraints.

    This class is central to LumiX's data-driven modeling approach, enabling automatic
    expansion of variables and constraints across data instances with type safety and
    IDE support.

    Type Parameters:
        TModel: The data model type for this dimension (e.g., Driver, Product, Date)

    Attributes:
        model_type: The Python class representing the data model for this dimension
        key_func: Function to extract the index key from a model instance
        filter_func: Optional predicate to filter which instances to include
        label: Optional human-readable label for this dimension
        _data: Direct data instances (mutually exclusive with _session)
        _session: ORM session for querying instances (mutually exclusive with _data)

    Examples:
        Basic dimension with direct data::

            driver_dim = (
                LXIndexDimension(Driver, lambda d: d.id)
                .from_data(drivers)
            )

        Dimension with filtering::

            active_driver_dim = (
                LXIndexDimension(Driver, lambda d: d.id)
                .from_data(drivers)
                .where(lambda d: d.is_active and d.years_experience >= 2)
            )

        Dimension with ORM::

            product_dim = (
                LXIndexDimension(Product, lambda p: p.sku)
                .from_model(db_session)
                .where(lambda p: p.in_stock)
            )

        Compound key extraction::

            route_dim = (
                LXIndexDimension(Route, lambda r: (r.origin, r.destination))
                .from_data(routes)
            )

    See Also:
        - :class:`~lumix.indexing.cartesian.LXCartesianProduct`: Combines dimensions
        - :class:`~lumix.core.variables.LXVariable.indexed_by_product`: Uses dimensions
        - Driver Scheduling Example (examples/02_driver_scheduling): Real-world usage

    Note:
        Index dimensions follow the "late binding" pattern - data instances are not
        retrieved until the dimension is actually used during model solving. This allows
        dimensions to be defined before data is available and supports dynamic data sources.
    """

    model_type: Type[TModel]
    key_func: Callable[[TModel], Any]
    filter_func: Optional[Callable[[TModel], bool]] = None
    label: Optional[str] = None
    _data: Optional[List[TModel]] = None
    _session: Optional[Any] = None

    def from_data(self, data: List[TModel]) -> LXIndexDimension[TModel]:
        """Provide data instances directly for this dimension.

        This method configures the dimension to use a pre-existing list of model instances.
        Use this when you have data already loaded in memory or when not using an ORM.

        Args:
            data: List of model instances for this dimension

        Returns:
            Self for method chaining

        Examples:
            Basic usage::

                drivers = [Driver("D1", "Alice"), Driver("D2", "Bob")]
                dim = LXIndexDimension(Driver, lambda d: d.id).from_data(drivers)

            With filtering::

                dim = (
                    LXIndexDimension(Driver, lambda d: d.id)
                    .from_data(drivers)
                    .where(lambda d: d.is_active)
                )

        Note:
            This method is mutually exclusive with from_model(). If both are called,
            the last call takes precedence.
        """
        self._data = data
        return self

    def from_model(self, session: Any) -> LXIndexDimension[TModel]:
        """Configure dimension to query data from an ORM session.

        This method configures the dimension to query instances from a database using
        an ORM session (e.g., SQLAlchemy, Django ORM). The actual query is executed
        lazily when get_instances() is called.

        Args:
            session: ORM session object (SQLAlchemy Session, Django ORM manager, etc.)

        Returns:
            Self for method chaining

        Examples:
            SQLAlchemy session::

                from sqlalchemy.orm import Session

                dim = (
                    LXIndexDimension(Driver, lambda d: d.id)
                    .from_model(db_session)
                    .where(lambda d: d.is_active)
                )

            With additional filtering::

                dim = (
                    LXIndexDimension(Product, lambda p: p.sku)
                    .from_model(session)
                    .where(lambda p: p.stock_quantity > 0)
                )

        Note:
            - This method is mutually exclusive with from_data()
            - The actual database query happens during model solving, not at definition time
            - Filters applied via where() are evaluated in Python after the query

        See Also:
            - :mod:`lumix.utils.orm`: ORM integration utilities
        """
        self._session = session
        return self

    def get_instances(self) -> List[TModel]:
        """Retrieve and filter data instances for this dimension.

        This method retrieves instances from the configured data source (either direct data
        or ORM query) and applies any filters specified via where(). This is typically called
        internally during model solving, not by user code.

        Returns:
            List of model instances after filtering

        Raises:
            ValueError: If no data source is configured (neither from_data() nor from_model()
                       has been called)

        Examples:
            The method is typically called internally, but can be used for inspection::

                dim = (
                    LXIndexDimension(Driver, lambda d: d.id)
                    .from_data(all_drivers)
                    .where(lambda d: d.is_active)
                )

                # Get filtered instances
                active_drivers = dim.get_instances()
                print(f"Found {len(active_drivers)} active drivers")

        Note:
            - For ORM-based dimensions, this triggers the database query
            - Filters are applied in Python after data retrieval
            - Results are not cached; each call may return different results if data changes

        Implementation Details:
            The method follows this logic:
            1. If _data is set, use it as the data source
            2. Otherwise, if _session is set, query via ORM using LXTypedQuery
            3. Otherwise, raise ValueError
            4. Apply filter_func if present
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
        """Apply a filter predicate to this dimension.

        This method adds a filter that determines which model instances from this dimension
        should be included. Only instances where the predicate returns True will be included
        in the dimension's expansion.

        The filter is applied within the dimension itself, before any cross-dimension filters
        (where_multi) are applied when using cartesian products.

        Args:
            predicate: A function that takes a model instance and returns True if it
                      should be included, False otherwise

        Returns:
            Self for method chaining

        Examples:
            Simple filter::

                dim = (
                    LXIndexDimension(Driver, lambda d: d.id)
                    .from_data(drivers)
                    .where(lambda d: d.is_active)
                )

            Complex filter with multiple conditions::

                dim = (
                    LXIndexDimension(Product, lambda p: p.sku)
                    .from_data(products)
                    .where(lambda p: p.in_stock and p.price > 0 and not p.discontinued)
                )

            Filter with attribute check::

                dim = (
                    LXIndexDimension(Route, lambda r: (r.origin, r.dest))
                    .from_data(routes)
                    .where(lambda r: r.distance < 1000 and r.is_operational)
                )

        Note:
            - Filters are evaluated in Python after data retrieval
            - Multiple where() calls will override previous filters (not combine them)
            - For multi-dimensional filtering across dimensions, use where_multi() on the variable

        See Also:
            - :meth:`lumix.core.variables.LXVariable.where_multi`: Cross-dimension filtering
            - :meth:`get_instances`: Where filtering is applied
        """
        self.filter_func = predicate
        return self


__all__ = ["LXIndexDimension"]
