"""Variable class with multi-indexing support for LumiX."""

import itertools
from dataclasses import dataclass, field
from typing import Any, Callable, Generic, List, Optional, Tuple, Type, TypeVar

from typing_extensions import Self

from ..indexing import LXCartesianProduct, LXIndexDimension
from .enums import LXVarType

TModel = TypeVar("TModel")
TValue = TypeVar("TValue", int, float)
TIndex = TypeVar("TIndex")
TModel1 = TypeVar("TModel1")
TModel2 = TypeVar("TModel2")


@dataclass
class LXVariable(Generic[TModel, TValue]):
    """
    Variable Family - represents multiple solver variables indexed by data models.

    IMPORTANT: LXVariable is NOT a single variable, but a FAMILY/TEMPLATE that
    automatically expands to multiple solver variables based on data.

    When you write:
        production = LXVariable[Product, float]("production").from_data(products)

    This creates ONE LXVariable object that represents MANY solver variables:
        production[product1], production[product2], production[product3], ...

    The expansion happens automatically during model building - you don't loop manually.

    Supports:
    - Single-model indexing: LXVariable[Product, float]
    - Multi-model indexing: LXVariable[Tuple[Driver, Date], int]
    - Join-based sparse indexing
    - Cartesian product indexing

    Examples:
        # Single model - data-driven
        production = (
            LXVariable[Product, float]("production")
            .continuous()
            .indexed_by(lambda p: p.id)
            .bounds(lower=0)
            .cost(lambda p: p.unit_cost)
            .from_data(products)  # Provide the data directly
        )

        # Or with ORM
        production = (
            LXVariable[Product, float]("production")
            .continuous()
            .from_model(Product, session=session)  # Query from ORM
        )

        # Multi-model (cartesian product)
        duty = (
            LXVariable[Tuple[Driver, Date], int]("duty")
            .binary()
            .indexed_by_product(
                LXIndexDimension(Driver, lambda d: d.id).from_data(drivers),
                LXIndexDimension(Date, lambda dt: dt.date).from_data(dates)
            )
            .where_multi(lambda driver, date: driver.is_active)
        )
    """

    name: str
    var_type: LXVarType = LXVarType.CONTINUOUS
    lower_bound: Optional[TValue] = None
    upper_bound: Optional[TValue] = None
    model_type: Optional[Type[TModel]] = None
    index_func: Optional[Callable[[TModel], TIndex]] = None
    cost_func: Optional[Callable[[TModel], float]] = None
    _filter: Optional[Callable[[TModel], bool]] = None

    # Data sources - EITHER data or model/session for ORM
    _data: Optional[List[TModel]] = None
    _session: Optional[Any] = None

    # Multi-model indexing
    _cartesian: Optional[LXCartesianProduct] = None
    _multi_cost_func: Optional[Callable[..., float]] = None
    _join_config: Optional[dict] = None

    def continuous(self) -> Self:
        """Set as continuous variable. Returns self for chaining."""
        self.var_type = LXVarType.CONTINUOUS
        return self

    def integer(self) -> Self:
        """Set as integer variable. Returns self for chaining."""
        self.var_type = LXVarType.INTEGER
        return self

    def binary(self) -> Self:
        """Set as binary variable. Returns self for chaining."""
        self.var_type = LXVarType.BINARY
        self.lower_bound = 0  # type: ignore
        self.upper_bound = 1  # type: ignore
        return self

    def bounds(self, lower: Optional[TValue] = None, upper: Optional[TValue] = None) -> Self:
        """
        Set variable bounds with full type checking.

        Args:
            lower: Lower bound (optional)
            upper: Upper bound (optional)

        Returns:
            Self for chaining
        """
        self.lower_bound = lower
        self.upper_bound = upper
        return self

    def from_data(self, data: List[TModel]) -> Self:
        """
        Provide data instances directly (for non-ORM usage).

        Args:
            data: List of model instances

        Returns:
            Self for chaining

        Example:
            production = Variable[Product, float]("production").from_data(products)
        """
        self._data = data
        return self

    def from_model(self, model: Type[TModel], session: Optional[Any] = None) -> Self:
        """
        Bind to ORM model type for automatic querying.

        Args:
            model: Model class
            session: Optional ORM session for querying

        Returns:
            Self for chaining

        Example:
            production = Variable[Product, float]("production").from_model(Product, session)
        """
        self.model_type = model
        self._session = session
        return self

    def get_instances(self) -> List[TModel]:
        """
        Get the data instances for this variable family.

        Returns:
            List of model instances

        Raises:
            ValueError: If no data source configured
        """
        # If data provided directly, use it
        if self._data is not None:
            instances = self._data
        # If ORM model configured, query it
        elif self.model_type is not None and self._session is not None:
            from ..utils.orm import LXTypedQuery
            query = LXTypedQuery(self._session, self.model_type)
            instances = query.all()
        # If Cartesian product, get from dimensions
        elif self._cartesian is not None:
            # Get instances from each dimension
            dimension_instances = [dim.get_instances() for dim in self._cartesian.dimensions]

            # Generate cartesian product of all dimensions
            combinations = list(itertools.product(*dimension_instances))

            # Apply cross-filter if present
            if self._cartesian._cross_filter is not None:
                combinations = [combo for combo in combinations if self._cartesian._cross_filter(*combo)]

            return combinations
        else:
            raise ValueError(
                f"Variable '{self.name}' has no data source. "
                "Use .from_data(data) or .from_model(Model, session)"
            )

        # Apply filter if present
        if self._filter is not None:
            instances = [inst for inst in instances if self._filter(inst)]

        return instances

    def indexed_by(self, func: Callable[[TModel], TIndex]) -> Self:
        """
        Define indexing function with full type inference.

        Args:
            func: Function to extract index from model instance

        Returns:
            Self for chaining

        Examples:
            .indexed_by(lambda product: product.id)
            .indexed_by(lambda route: (route.origin, route.destination))
        """
        self.index_func = func
        return self

    def indexed_by_product(
        self,
        dim1: LXIndexDimension[TModel1],
        dim2: LXIndexDimension[TModel2],
        *extra_dims: LXIndexDimension,
    ) -> Self:
        """
        Index by cartesian product of multiple models.
        Creates variables for every valid combination.

        Args:
            dim1: First dimension
            dim2: Second dimension
            *extra_dims: Additional dimensions for 3D+ indexing

        Returns:
            Self for chaining

        Example:
            duty = LXVariable[Tuple[Driver, Date], int]("duty")
                .indexed_by_product(
                    LXIndexDimension(Driver, lambda d: d.id)
                        .where(lambda d: d.is_active),
                    LXIndexDimension(Date, lambda dt: dt.date)
                        .where(lambda dt: dt >= today)
                )
        """
        self._cartesian = LXCartesianProduct(dim1, dim2)
        for dim in extra_dims:
            self._cartesian.add_dimension(dim)
        return self

    def indexed_by_join(
        self,
        primary: Type[TModel1],
        related: Type[TModel2],
        join_func: Callable[[TModel1], List[TModel2]],
        key_func: Optional[Callable[[TModel1, TModel2], Tuple]] = None,
    ) -> Self:
        """
        Index by a relationship/join between models.
        Only creates variables where relationship exists (sparse).

        Args:
            primary: Primary model type
            related: Related model type
            join_func: Function to get related models from primary
            key_func: Optional function to create compound key

        Returns:
            Self for chaining

        Example:
            # Only create variables for valid driver-route assignments
            assignment = LXVariable[Tuple[Driver, Route], int]("assign")
                .indexed_by_join(
                    Driver,
                    Route,
                    join_func=lambda d: d.qualified_routes,  # ORM relationship
                    key_func=lambda d, r: (d.id, r.id)
                )
        """
        self._join_config = {
            "primary": primary,
            "related": related,
            "join_func": join_func,
            "key_func": key_func or (lambda m1, m2: (m1, m2)),
        }
        return self

    def cost(self, func: Callable[[TModel], float]) -> Self:
        """
        Define objective coefficient from model.

        Args:
            func: Function to calculate cost from model

        Returns:
            Self for chaining

        Example:
            .cost(lambda product: product.unit_cost)
        """
        self.cost_func = func
        return self

    def cost_multi(self, func: Callable[..., float]) -> Self:
        """
        Define cost function for multi-indexed variables.
        Function receives all index models as arguments.

        Args:
            func: Function receiving all dimension models

        Returns:
            Self for chaining

        Example:
            .cost_multi(lambda driver, date: driver.daily_rate * date.overtime_multiplier)
        """
        self._multi_cost_func = func
        return self

    def where(self, predicate: Callable[[TModel], bool]) -> Self:
        """
        Filter which model instances to include.

        Args:
            predicate: Filter function

        Returns:
            Self for chaining

        Example:
            .where(lambda p: p.is_active and p.stock > 0)
        """
        self._filter = predicate
        return self

    def where_multi(self, predicate: Callable[..., bool]) -> Self:
        """
        Filter multi-indexed variable combinations.

        Args:
            predicate: Filter function receiving all dimension models

        Returns:
            Self for chaining

        Example:
            .where_multi(lambda driver, date, shift:
                driver.can_work_shift(shift) and
                date.weekday() not in driver.days_off
            )
        """
        if self._cartesian:
            self._cartesian.where(predicate)
        return self


__all__ = ["LXVariable"]
