"""ORM integration protocols and utilities for LumiX."""

from __future__ import annotations

from typing import Any, Callable, Generic, List, Optional, Protocol, Type, TypeVar, runtime_checkable

from typing_extensions import Self


TModel = TypeVar("TModel")


@runtime_checkable
class LXORMModel(Protocol):
    """Structural type for any ORM model."""

    id: Any

    def __getattribute__(self, name: str) -> Any:
        ...


class LXNumeric(Protocol):
    """Type-safe numeric types."""

    def __add__(self, other: int | float) -> int | float:
        ...

    def __mul__(self, other: int | float) -> int | float:
        ...

    def __float__(self) -> float:
        ...


class LXORMContext(Generic[TModel]):
    """Type-safe ORM query interface."""

    def __init__(self, session: Any):
        self.session = session

    def query(self, model: Type[TModel]) -> "LXTypedQuery[TModel]":
        """Start typed query with full IDE support."""
        return LXTypedQuery(self.session, model)


class LXTypedQuery(Generic[TModel]):
    """Type-safe query builder."""

    def __init__(self, session: Any, model: Type[TModel]):
        self.session = session
        self.model = model
        self._filters: List[Callable[[TModel], bool]] = []

    def filter(self, predicate: Callable[[TModel], bool]) -> Self:
        """Filter with type-safe predicate. IDE knows model structure!"""
        self._filters.append(predicate)
        return self

    def all(self) -> List[TModel]:
        """Execute and return typed results."""
        # Query execution with ORM
        results = self.session.query(self.model).all()
        # Apply filters
        for predicate in self._filters:
            results = [r for r in results if predicate(r)]
        return results

    def first(self) -> Optional[TModel]:
        """Get first result."""
        all_results = self.all()
        return all_results[0] if all_results else None


__all__ = ["LXORMModel", "LXNumeric", "LXORMContext", "LXTypedQuery"]
