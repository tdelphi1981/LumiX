"""ORM integration protocols and utilities for LumiX.

This module provides type-safe protocols and utilities for integrating LumiX with
Object-Relational Mapping (ORM) libraries like SQLAlchemy, Django ORM, or Peewee.

The module defines structural typing protocols that allow LumiX to work with any
ORM model that satisfies the interface, without requiring inheritance or explicit
implementation.

Key Features:
    - **Structural Typing**: Works with any ORM via Protocol (PEP 544)
    - **Type Safety**: Full type checking and IDE autocomplete for ORM queries
    - **Generic Support**: Type-safe query builders with Generic types
    - **ORM Agnostic**: Compatible with SQLAlchemy, Django ORM, Peewee, etc.

Architecture:
    The module uses Python's Protocol to define structural interfaces. Any object
    that has the required attributes automatically satisfies the protocol without
    needing explicit inheritance.

Examples:
    Using with SQLAlchemy models::

        from sqlalchemy import Column, Integer, String, Float
        from sqlalchemy.ext.declarative import declarative_base
        from lumix.utils import LXORMContext

        Base = declarative_base()

        class Product(Base):
            __tablename__ = 'products'
            id = Column(Integer, primary_key=True)
            name = Column(String)
            profit = Column(Float)

        # Use type-safe ORM context
        session = Session()
        ctx = LXORMContext(session)

        # Query with full type safety
        products = ctx.query(Product).filter(lambda p: p.profit > 100).all()

    Integration with LumiX models::

        from lumix import LXVariable

        # Create variable family from ORM data
        production = (
            LXVariable[Product, float]("production")
            .continuous()
            .bounds(lower=0)
            .from_data(products)  # products from ORM query
            .indexed_by(lambda p: p.id)
        )

See Also:
    - :class:`~lumix.core.variables.LXVariable`: Variable families with ORM data
    - :class:`~lumix.core.constraints.LXConstraint`: Constraints with ORM data
"""

from __future__ import annotations

from typing import Any, Callable, Generic, List, Optional, Protocol, Type, TypeVar, runtime_checkable

from typing_extensions import Self


TModel = TypeVar("TModel")


@runtime_checkable
class LXORMModel(Protocol):
    """Structural protocol for any ORM model.

    This protocol defines the minimal interface that an ORM model must satisfy to be
    used with LumiX. Any class with an 'id' attribute automatically satisfies this
    protocol through structural typing.

    The protocol is runtime-checkable, meaning you can use isinstance() to verify
    if an object satisfies the protocol at runtime.

    Attributes:
        id: Unique identifier for the model instance. Can be any type (int, str, UUID, etc.)

    Examples:
        SQLAlchemy model automatically satisfies the protocol::

            from sqlalchemy import Column, Integer, String
            from sqlalchemy.ext.declarative import declarative_base

            Base = declarative_base()

            class Product(Base):
                __tablename__ = 'products'
                id = Column(Integer, primary_key=True)
                name = Column(String)

            # Product automatically satisfies LXORMModel
            assert isinstance(Product(), LXORMModel)

        Plain dataclass also works::

            from dataclasses import dataclass

            @dataclass
            class Customer:
                id: int
                name: str

            # Customer satisfies the protocol
            assert isinstance(Customer(1, "Alice"), LXORMModel)

    Note:
        This is a structural Protocol (PEP 544), not a base class. You don't need
        to inherit from it - any object with an 'id' attribute satisfies it.
    """

    id: Any

    def __getattribute__(self, name: str) -> Any:
        ...


class LXNumeric(Protocol):
    """Structural protocol for numeric types with optimization operations.

    Defines the interface for types that can be used as numeric coefficients
    in optimization expressions. Supports addition, multiplication, and conversion
    to float.

    This protocol allows type-safe usage of various numeric types (int, float,
    Decimal, Fraction, etc.) in optimization expressions.

    Examples:
        Standard numeric types satisfy the protocol::

            x: LXNumeric = 5        # int satisfies protocol
            y: LXNumeric = 3.14     # float satisfies protocol

        Custom numeric types can also satisfy it::

            from decimal import Decimal

            z: LXNumeric = Decimal("10.5")  # Decimal satisfies protocol

    Note:
        This is a structural Protocol. Any type with the required methods
        automatically satisfies it without explicit inheritance.
    """

    def __add__(self, other: int | float) -> int | float:
        ...

    def __mul__(self, other: int | float) -> int | float:
        ...

    def __float__(self) -> float:
        ...


class LXORMContext(Generic[TModel]):
    """Type-safe ORM query interface with generic support.

    Provides a type-safe wrapper around ORM sessions that enables IDE autocomplete
    and type checking for database queries. The generic type parameter ensures
    that query results have proper type information.

    Attributes:
        session: The underlying ORM session (SQLAlchemy, Django, etc.)

    Type Parameters:
        TModel: The ORM model type being queried

    Examples:
        Create context from SQLAlchemy session::

            from sqlalchemy.orm import Session
            from lumix.utils import LXORMContext

            session = Session()
            ctx = LXORMContext(session)

            # Query with full type safety
            products = ctx.query(Product).all()  # Type: List[Product]

        Chain query operations::

            expensive_products = (
                ctx.query(Product)
                .filter(lambda p: p.price > 100)
                .filter(lambda p: p.in_stock)
                .all()
            )

    See Also:
        :class:`LXTypedQuery`: The query builder returned by query()
    """

    def __init__(self, session: Any):
        """Initialize ORM context with a session.

        Args:
            session: ORM session object (e.g., SQLAlchemy Session, Django QuerySet)

        Examples:
            Initialize with SQLAlchemy session::

                from sqlalchemy.orm import Session
                session = Session()
                ctx = LXORMContext(session)
        """
        self.session = session

    def query(self, model: Type[TModel]) -> "LXTypedQuery[TModel]":
        """Start a type-safe query for the specified model.

        Args:
            model: The ORM model class to query

        Returns:
            A type-safe query builder for the model

        Examples:
            Basic query::

                products = ctx.query(Product).all()

            With filtering::

                active_products = ctx.query(Product).filter(lambda p: p.active).all()
        """
        return LXTypedQuery(self.session, model)


class LXTypedQuery(Generic[TModel]):
    """Type-safe query builder with fluent API.

    Provides a chainable query interface with full type safety and IDE autocomplete.
    The generic type parameter ensures that filter predicates and results have proper
    type information.

    The query builder supports filtering via lambda predicates, where the IDE knows
    the structure of the model being queried.

    Attributes:
        session: The underlying ORM session
        model: The ORM model class being queried
        _filters: Internal list of filter predicates to apply

    Type Parameters:
        TModel: The ORM model type being queried

    Examples:
        Basic querying with type safety::

            query = LXTypedQuery(session, Product)
            products = query.all()  # Type: List[Product]

        Filtering with lambda predicates::

            expensive = (
                LXTypedQuery(session, Product)
                .filter(lambda p: p.price > 100)
                .filter(lambda p: p.in_stock)
                .all()
            )

        Using with LXORMContext::

            ctx = LXORMContext(session)
            active_products = ctx.query(Product).filter(lambda p: p.active).all()

    Note:
        The filter predicates are applied in Python after retrieving results from
        the ORM. For large datasets, consider using ORM-specific filtering before
        wrapping in LXTypedQuery.
    """

    def __init__(self, session: Any, model: Type[TModel]):
        """Initialize typed query builder.

        Args:
            session: ORM session object
            model: ORM model class to query

        Examples:
            Create query builder directly::

                query = LXTypedQuery(session, Product)
        """
        self.session = session
        self.model = model
        self._filters: List[Callable[[TModel], bool]] = []

    def filter(self, predicate: Callable[[TModel], bool]) -> Self:
        """Add a type-safe filter predicate to the query.

        The predicate receives model instances with full type information, enabling
        IDE autocomplete for all model attributes.

        Args:
            predicate: A callable that takes a model instance and returns True/False.
                The IDE will autocomplete model attributes in the lambda.

        Returns:
            Self for method chaining

        Examples:
            Filter by single condition::

                query.filter(lambda p: p.price > 100)

            Chain multiple filters::

                query.filter(lambda p: p.active).filter(lambda p: p.in_stock)

            Complex filtering::

                query.filter(lambda p: p.price > 50 and p.category == "Electronics")
        """
        self._filters.append(predicate)
        return self

    def all(self) -> List[TModel]:
        """Execute query and return all matching results.

        Retrieves all records from the ORM, then applies the filter predicates
        in order.

        Returns:
            List of model instances matching all filter conditions

        Examples:
            Get all filtered results::

                products = query.filter(lambda p: p.active).all()

            Use in LumiX variable::

                production = (
                    LXVariable[Product, float]("production")
                    .from_data(query.filter(lambda p: p.available).all())
                    .indexed_by(lambda p: p.id)
                )
        """
        # Query execution with ORM
        results = self.session.query(self.model).all()
        # Apply filters
        for predicate in self._filters:
            results = [r for r in results if predicate(r)]
        return results

    def first(self) -> Optional[TModel]:
        """Execute query and return the first matching result.

        Returns:
            The first model instance matching all filters, or None if no matches

        Examples:
            Get single result::

                product = query.filter(lambda p: p.id == 5).first()

            Check for existence::

                if query.filter(lambda p: p.name == "Widget").first():
                    print("Widget exists")
        """
        all_results = self.all()
        return all_results[0] if all_results else None


__all__ = ["LXORMModel", "LXNumeric", "LXORMContext", "LXTypedQuery"]
