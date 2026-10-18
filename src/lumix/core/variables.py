"""Variable class with multi-indexing support for LumiX."""

import itertools
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Generic, List, Optional, Tuple, Type, TypeVar

from typing_extensions import Self

from ..indexing import LXCartesianProduct, LXIndexDimension
from .enums import LXVarType

if TYPE_CHECKING:
    from .expressions import LXLinearExpression

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

    When you write::

        production = LXVariable[Product, float]("production").from_data(products)

    This creates ONE LXVariable object that represents MANY solver variables::

        production[product1], production[product2], production[product3], ...

    The expansion happens automatically during model building - you don't loop manually.

    Supports:

    - Single-model indexing: LXVariable[Product, float]
    - Multi-model indexing: LXVariable[Tuple[Driver, Date], int]
    - Join-based sparse indexing
    - Cartesian product indexing

    Examples::

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
    _multi_filter: Optional[Callable[..., bool]] = None

    def __deepcopy__(self, memo):
        """Copy the family structure; share data instances and callables.

        Data instances (plain objects and ORM objects alike) and callables are shared
        with the original, so closures and identity checks behave the same in the copy.
        An ORM-backed source is materialized once (its query runs at copy time).

        Args:
            memo: Dictionary for tracking circular references during deepcopy

        .. versionchanged:: 0.3.0
           Instances are shared instead of deep-copied/detached (catalog A23, B15).
        """
        from copy import deepcopy

        # Create new instance without calling __init__
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result

        # Copy simple attributes
        result.name = self.name
        result.var_type = self.var_type
        result.lower_bound = self.lower_bound
        result.upper_bound = self.upper_bound
        result.model_type = self.model_type

        # Callables are shared, not copied: closures keep seeing the user's own objects.
        result.index_func = self.index_func
        result.cost_func = self.cost_func
        result._filter = self._filter
        result._multi_filter = self._multi_filter
        result._multi_cost_func = self._multi_cost_func

        # Handle data sources
        if self._session is not None:
            # Materialize the ORM query once; the instances themselves are shared
            try:
                instances = self.get_instances()
                result._data = list(instances)
            except Exception as e:
                import warnings
                warnings.warn(
                    f"Failed to materialize variable data for '{self.name}': {e}. "
                    f"Variable will be empty in the copy.",
                    UserWarning
                )
                result._data = []
            result._session = None
        elif self._data is not None:
            # Data instances are shared (never copied or detached)
            result._data = list(self._data)
            result._session = None
        else:
            result._data = None
            result._session = None

        # Deep copy cartesian product (if present)
        result._cartesian = (
            deepcopy(self._cartesian, memo)
            if self._cartesian is not None
            else None
        )

        # Handle join configuration
        if self._join_config is not None:
            result._join_config = {}
            result._join_config['primary'] = self._join_config['primary']
            result._join_config['related'] = self._join_config['related']
            result._join_config['join_func'] = self._join_config['join_func']
            result._join_config['key_func'] = self._join_config['key_func']
        else:
            result._join_config = None

        return result

    def __getstate__(self):
        """Support for pickle protocol - detach ORM sessions before pickling.

        Returns:
            Dictionary of instance state safe for pickling
        """
        state = self.__dict__.copy()

        # If using ORM session, materialize data before pickling
        if state.get('_session') is not None:
            try:
                instances = self.get_instances()
                from ..utils.copy_utils import detach_orm_object
                state['_data'] = [detach_orm_object(inst) for inst in instances]
            except Exception:
                state['_data'] = []
            state['_session'] = None

        return state

    def __setstate__(self, state):
        """Support for pickle protocol - restore from pickled state.

        Args:
            state: Dictionary of instance state from pickling
        """
        self.__dict__.update(state)

    def continuous(self) -> Self:
        """Set as continuous variable. Returns self for chaining."""
        self.var_type = LXVarType.CONTINUOUS
        return self

    def integer(self) -> Self:
        """Set as integer variable. Returns self for chaining."""
        self.var_type = LXVarType.INTEGER
        return self

    def binary(self) -> Self:
        """Set as binary variable. Returns self for chaining.

        Bounds set before or after are kept; the model intersects them with [0, 1].

        .. versionchanged:: 0.3.2
           Bounds set before ``binary()`` are no longer reset to [0, 1].
        """
        self.var_type = LXVarType.BINARY
        return self

    def bounds(self, lower: Optional[TValue] = None, upper: Optional[TValue] = None) -> Self:
        """
        Set variable bounds with full type checking.

        Args:
            lower: Lower bound (optional)
            upper: Upper bound (optional)

        Returns:
            Self for chaining

        Raises:
            TypeError: If a bound is a function. Bounds apply to the whole family; for
                per-instance bounds add an indexed constraint
                (``LXConstraint("cap").expression(...).le().rhs(lambda p: p.capacity)``).
        """
        for value in (lower, upper):
            if callable(value):
                raise TypeError(
                    f"Variable '{self.name}': bounds are numbers for the whole family; "
                    "per-instance bounds are not supported. Add an indexed constraint "
                    "instead, e.g. LXConstraint(...).expression(LXLinearExpression()"
                    ".add_term(var, 1)).le().rhs(lambda item: item.capacity)")
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

        ``where()`` filters every instance (for ``indexed_by_product`` the tuple of
        dimension instances; for ``indexed_by_join`` the primary record) and
        ``where_multi()`` filters product and join combinations with one argument
        per part, whatever the order of the calls.

        Returns:
            List of model instances

        Raises:
            ValueError: If no data source configured
        """
        if self._cartesian is not None:
            dimension_instances = [dim.get_instances() for dim in self._cartesian.dimensions]
            instances = list(itertools.product(*dimension_instances))
            if self._cartesian._cross_filter is not None:
                instances = [c for c in instances if self._cartesian._cross_filter(*c)]
        else:
            if self._data is not None:
                instances = list(self._data)
            elif self.model_type is not None and self._session is not None:
                from ..utils.orm import LXTypedQuery
                instances = LXTypedQuery(self._session, self.model_type).all()
            else:
                raise ValueError(
                    f"Variable '{self.name}' has no data source. "
                    "Use .from_data(data) or .from_model(Model, session)"
                )
            if self._join_config is not None:
                if self._filter is not None:            # where() filters primary records
                    instances = [p for p in instances if self._filter(p)]
                join = self._join_config["join_func"]
                instances = [(p, r) for p in instances for r in join(p)]
        if self._multi_filter is not None:
            if not self.is_multi_indexed:
                raise ValueError(
                    f"Variable '{self.name}': where_multi() filters the parts of a "
                    "multi-index (indexed_by_product / indexed_by_join); use where() "
                    "on a single index")
            instances = [i for i in instances if self._multi_filter(*i)]
        if self._filter is not None and self._join_config is None:
            instances = [i for i in instances if self._filter(i)]
        return instances

    @property
    def is_scalar(self) -> bool:
        """True for a single variable without a data source (no ``from_data``,
        ``from_model``, ``indexed_by``, ``indexed_by_product`` or join); it has one
        instance, ``None``, and its solution value is a number, not a dict."""
        return (self._data is None and self._session is None and self.model_type is None
                and self._cartesian is None and self._join_config is None
                and self.index_func is None)

    @property
    def is_multi_indexed(self) -> bool:
        """True when instances are tuples of one model per dimension
        (``indexed_by_product``); coefficients and filters then receive one
        argument per dimension."""
        return self.index_func is None and (self._cartesian is not None
                                            or self._join_config is not None)

    def index_key(self, instance: Any) -> Any:
        """
        Return the index key of one instance of this variable family.

        Solver adapters key their variable maps with this value, and
        ``keys=`` in :meth:`LXLinearExpression.add_term` /
        :meth:`LXLinearExpression.add_multi_term` must use the same form.

        Args:
            instance: A data instance (for ``indexed_by_product`` families,
                the tuple of one instance per dimension)

        Returns:
            ``index_func(instance)`` when an index function is set; for
            ``indexed_by_product`` families the tuple of each dimension's key;
            otherwise the instance itself.
        """
        if self.index_func is not None:
            return self.index_func(instance)
        if self._join_config is not None:
            return self._join_config["key_func"](*instance)
        if self._cartesian is not None and isinstance(instance, tuple):
            return tuple(
                dim.key_func(part)
                for dim, part in zip(self._cartesian.dimensions, instance)
            )
        return instance

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

        Example::

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

        The primary records come from ``from_data(...)`` or ``from_model(...)``;
        instances are ``(primary, related)`` pairs for every ``related`` in
        ``join_func(primary)``, keyed by ``key_func(primary, related)``. Coefficients
        and ``where_multi`` filters receive the two records as two arguments;
        ``where()`` filters the primary records.

        Args:
            primary: Primary model type
            related: Related model type
            join_func: Function to get related models from primary
            key_func: Optional function to create compound key

        Returns:
            Self for chaining

        Example::

            # Only create variables for valid driver-route assignments
            assignment = LXVariable[Tuple[Driver, Route], int]("assign")
                .indexed_by_join(
                    Driver,
                    Route,
                    join_func=lambda d: d.qualified_routes,  # ORM relationship
                    key_func=lambda d, r: (d.id, r.id)
                )
                .from_data(drivers)
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

        On an ``indexed_by_product`` / join family the function may take one
        argument per part, like :meth:`cost_multi`.

        Example:
            .cost(lambda product: product.unit_cost)

        .. versionchanged:: 0.3.0
           Accepts one argument per part on multi-index families.
        """
        self.cost_func = func
        return self

    def cost_expression(self) -> Optional["LXLinearExpression"]:
        """The objective contribution defined by ``cost()`` / ``cost_multi()``:
        ``sum(cost(instance) * self[instance])``, or ``None`` without a cost.

        .. versionadded:: 0.3.0
        """
        from .expressions import LXLinearExpression, call_arity
        if self._multi_cost_func is not None:
            return LXLinearExpression().add_multi_term(self, coeff=self._multi_cost_func)
        if self.cost_func is not None:
            if self.is_multi_indexed and call_arity(self.cost_func) > 1:
                return LXLinearExpression().add_multi_term(self, coeff=self.cost_func)
            return LXLinearExpression().add_term(self, self.cost_func)
        return None

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

        Example::

            .where_multi(lambda driver, date, shift:
                driver.can_work_shift(shift) and
                date.weekday() not in driver.days_off
            )
        """
        self._multi_filter = predicate
        return self


__all__ = ["LXVariable"]
