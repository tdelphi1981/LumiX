"""Constraint class for LumiX optimization models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Generic, List, Optional, Type, TypeVar

from typing_extensions import Self

from .enums import LXConstraintSense
from .expressions import LXLinearExpression

if TYPE_CHECKING:
    from ..goal_programming.goal import LXGoalMetadata

TModel = TypeVar("TModel")
TIndex = TypeVar("TIndex")


@dataclass
class LXConstraint(Generic[TModel]):
    """
    Constraint Family - represents multiple constraints indexed by data models.

    Like LXVariable, an LXConstraint represents a FAMILY of constraints that
    automatically expands to multiple solver constraints based on data.

    Represents: LHS {<=, >=, ==} RHS

    Examples::

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

    # Goal programming metadata
    goal_metadata: Optional["LXGoalMetadata"] = None

    def __deepcopy__(self, memo):
        """Custom deepcopy that detaches ORM sessions and handles lambda closures.

        This method enables what-if analysis on constraints using ORM data sources by:
        1. Materializing lazy-loaded ORM data before copying
        2. Detaching ORM objects from database sessions
        3. Safely copying lambda functions (index_func, rhs_func, etc.)
        4. Deep copying constraint expressions and goal metadata

        Args:
            memo: Dictionary for tracking circular references during deepcopy

        Returns:
            Deep copy of this constraint with all ORM dependencies resolved

        Note:
            After copying, the new constraint will have _session=None and all data
            stored in _data as detached objects safe for pickling.
        """
        from copy import deepcopy
        from ..utils.copy_utils import (
            materialize_and_detach_list,
            copy_function_detaching_closure
        )

        # Create new instance without calling __init__
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result

        # Copy simple attributes
        result.name = self.name
        result.sense = self.sense
        result.rhs_value = self.rhs_value
        result.model_type = self.model_type

        # Copy callable attributes - may have closures capturing ORM objects
        result.index_func = (
            copy_function_detaching_closure(self.index_func, memo)
            if self.index_func is not None
            else None
        )
        result.rhs_func = (
            copy_function_detaching_closure(self.rhs_func, memo)
            if self.rhs_func is not None
            else None
        )

        # Deep copy LHS expression (may contain variables and terms)
        result.lhs = (
            deepcopy(self.lhs, memo)
            if self.lhs is not None
            else None
        )

        # Handle data sources
        if self._session is not None:
            # Materialize ORM data before copying
            try:
                instances = self.get_instances()
                result._data = materialize_and_detach_list(instances, memo)
            except Exception as e:
                import warnings
                warnings.warn(
                    f"Failed to materialize constraint data for '{self.name}': {e}. "
                    f"Constraint will have no instances in the copy.",
                    UserWarning
                )
                result._data = []
            result._session = None
        elif self._data is not None:
            # Already have data - just detach and copy
            result._data = materialize_and_detach_list(self._data, memo)
            result._session = None
        else:
            result._data = None
            result._session = None

        # Deep copy goal metadata if present
        result.goal_metadata = (
            deepcopy(self.goal_metadata, memo)
            if self.goal_metadata is not None
            else None
        )

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

    def as_goal(self, priority: int, weight: float = 1.0) -> Self:
        """
        Mark this constraint as a goal for goal programming.

        Automatically relaxes the constraint by adding deviation variables
        and includes it in the goal programming objective function.

        Constraint types are handled as follows:

        - LE (expr <= rhs): expr + neg_dev - pos_dev == rhs

          - Positive deviation (exceeding target) is undesired

        - GE (expr >= rhs): expr + neg_dev - pos_dev == rhs

          - Negative deviation (falling short) is undesired

        - EQ (expr == rhs): expr + neg_dev - pos_dev == rhs

          - Both deviations are undesired

        Args:
            priority: Priority level (1=highest, 2=second, etc.)
                      Priority 0 is reserved for custom objective terms
            weight: Relative weight within the same priority level (default: 1.0)

        Returns:
            Self for chaining

        Example::

            # High priority production goal
            .as_goal(priority=1, weight=1.0)

            # Lower priority overtime limit
            .as_goal(priority=2, weight=0.5)

            # Custom objective term (maximize profit)
            .as_goal(priority=0, weight=1.0)
        """
        from ..goal_programming.goal import LXGoalMetadata

        self.goal_metadata = LXGoalMetadata(
            priority=priority,
            weight=weight,
            constraint_sense=self.sense,
        )
        return self

    def is_goal(self) -> bool:
        """
        Check if this constraint is marked as a goal.

        Returns:
            True if this is a goal constraint, False otherwise
        """
        return self.goal_metadata is not None

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
