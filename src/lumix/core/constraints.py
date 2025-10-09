"""Constraint class for LumiX optimization models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Generic, List, Optional, Type, TypeVar

from typing_extensions import Self

from .enums import LXConstraintSense
from .expressions import LXLinearExpression

TModel = TypeVar("TModel")
TIndex = TypeVar("TIndex")


@dataclass
class LXConstraint(Generic[TModel]):
    """
    Constraint Family - represents multiple constraints indexed by data models.

    Like LXVariable, an LXConstraint represents a FAMILY of constraints that
    automatically expands to multiple solver constraints based on data.

    Represents: LHS {<=, >=, ==} RHS

    Examples:
        # Simple single constraint
        LXConstraint("total_capacity")
            .expression(LXLinearExpression().add_term(production, 1.0))
            .le()
            .rhs(100)

        # Constraint family - one per resource
        # Note: In multi-model constraints, the coefficient lambda receives instances from:
        #   - p: Product (from the production variable's indexing)
        #   - r: Resource (from this constraint's indexing)
        # This allows expressing relationships between different data models.
        LXConstraint[Resource]("capacity")
            .expression(LXLinearExpression().add_term(production, lambda p, r: p.usage[r.id]))
            .le()
            .rhs(lambda r: r.capacity)
            .from_data(resources)
            .indexed_by(lambda r: r.id)
    """

    name: str
    lhs: Optional[LXLinearExpression[TModel]] = None
    sense: LXConstraintSense = LXConstraintSense.LE
    rhs_value: Optional[float] = None
    rhs_func: Optional[Callable[[TModel], float]] = None
    model_type: Optional[Type[TModel]] = None
    index_func: Optional[Callable[[TModel], TIndex]] = None

    # Data sources
    _data: Optional[List[TModel]] = None
    _session: Optional[Any] = None

    def expression(self, expr: LXLinearExpression[TModel]) -> Self:
        """
        Set LHS expression.

        Args:
            expr: Linear expression for left-hand side

        Returns:
            Self for chaining
        """
        self.lhs = expr
        return self

    def le(self) -> Self:
        """
        Set as <= constraint.

        Returns:
            Self for chaining
        """
        self.sense = LXConstraintSense.LE
        return self

    def ge(self) -> Self:
        """
        Set as >= constraint.

        Returns:
            Self for chaining
        """
        self.sense = LXConstraintSense.GE
        return self

    def eq(self) -> Self:
        """
        Set as == constraint.

        Returns:
            Self for chaining
        """
        self.sense = LXConstraintSense.EQ
        return self

    def rhs(self, value: float | Callable[[TModel], float]) -> Self:
        """
        Set RHS (constant or function).

        Args:
            value: Right-hand side value (constant or function)

        Returns:
            Self for chaining

        Examples:
            .rhs(100)  # constant
            .rhs(lambda resource: resource.capacity)  # from model
        """
        if callable(value):
            self.rhs_func = value
        else:
            self.rhs_value = value
        return self

    def from_data(self, data: List[TModel]) -> Self:
        """
        Provide data instances directly.

        Args:
            data: List of model instances

        Returns:
            Self for chaining
        """
        self._data = data
        return self

    def from_model(self, model: Type[TModel], session: Optional[Any] = None) -> Self:
        """
        Bind to model for indexed constraints.

        Args:
            model: Model class
            session: Optional ORM session

        Returns:
            Self for chaining
        """
        self.model_type = model
        self._session = session
        return self

    def indexed_by(self, func: Callable[[TModel], TIndex]) -> Self:
        """
        Create constraint for each model instance.

        Args:
            func: Function to extract index from model

        Returns:
            Self for chaining

        Example:
            .indexed_by(lambda r: r.id)
        """
        self.index_func = func
        return self

    def get_instances(self) -> List[TModel]:
        """
        Get the data instances for this constraint family.

        Returns:
            List of model instances, or empty list if single constraint

        Raises:
            ValueError: If indexed but no data source configured
        """
        # If not indexed, return empty list (single constraint)
        if self.index_func is None:
            return []

        # If data provided directly, use it
        if self._data is not None:
            return self._data

        # If ORM model configured, query it
        if self.model_type is not None and self._session is not None:
            from ..utils.orm import LXTypedQuery
            query = LXTypedQuery(self._session, self.model_type)
            return query.all()

        # If indexed but no data source
        raise ValueError(
            f"LXConstraint '{self.name}' is indexed but has no data source. "
            "Use .from_data(data) or .from_model(Model, session)"
        )


__all__ = ["LXConstraint"]
