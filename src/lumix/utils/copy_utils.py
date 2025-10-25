"""Utilities for safe copying of models with ORM integration.

This module provides utilities for safely copying LumiX models that use ORM
(Object-Relational Mapping) frameworks like SQLAlchemy or Django. ORM objects
and database sessions cannot be pickled/deep copied directly, so this module
provides specialized functions to handle:

- Detaching ORM objects from database sessions
- Materializing lazy-loaded data before copying
- Safely copying lambda functions that capture ORM objects

The main use case is enabling what-if analysis on models built with ORM data sources.

Functions:
    detach_orm_object: Detach single ORM object from session
    copy_function_detaching_closure: Copy function with ORM-safe closures
    materialize_and_detach_list: Materialize and detach list of items

Examples:
    Detach SQLAlchemy object::

        from sqlalchemy.orm import Session

        product = session.query(Product).first()
        detached = detach_orm_object(product)
        # detached can now be pickled/copied

    Copy lambda with captured ORM object::

        profit_func = lambda p: product.profit * p.quantity
        safe_func = copy_function_detaching_closure(profit_func, {})

See Also:
    - :class:`lumix.analysis.whatif.LXWhatIfAnalyzer`: Uses these utilities
    - Tutorial Step 7: Production Planning with What-If Analysis
"""

from typing import Any, TypeVar, Callable, List, Optional
import warnings

T = TypeVar('T')


def detach_orm_object(obj: Any) -> Any:
    """
    Detach an ORM object from its database session, making it safe to copy.

    This function handles objects from multiple ORM frameworks:

    - **SQLAlchemy**: Detaches via make_transient or attribute copying
    - **Django ORM**: Copies field values to new instance
    - **Plain objects**: Returned as-is (no modification needed)

    Args:
        obj: Object to detach (may be ORM object or plain object)

    Returns:
        Detached copy of the object safe for pickling/copying.
        For plain Python objects, returns the original object unchanged.

    Examples:
        SQLAlchemy usage::

            from sqlalchemy import create_engine, Column, Integer, String
            from sqlalchemy.orm import sessionmaker, declarative_base

            Base = declarative_base()

            class Product(Base):
                __tablename__ = 'products'
                id = Column(Integer, primary_key=True)
                name = Column(String)

            engine = create_engine('sqlite:///db.sqlite')
            Session = sessionmaker(bind=engine)
            session = Session()

            product = session.query(Product).first()
            detached = detach_orm_object(product)
            # detached is no longer bound to session

        Plain object (no-op)::

            from dataclasses import dataclass

            @dataclass
            class Product:
                id: int
                name: str

            product = Product(1, "Widget")
            result = detach_orm_object(product)
            # result is product (same object)

    Note:
        - For SQLAlchemy, relationship attributes may not be fully loaded
        - For Django, only direct field values are copied (no relations)
        - If detachment fails, returns original object with a warning
    """
    # Handle None
    if obj is None:
        return None

    # SQLAlchemy object detection
    if hasattr(obj, '_sa_instance_state'):
        return _detach_sqlalchemy_object(obj)

    # Django ORM object detection
    if hasattr(obj, '_state') and hasattr(obj, '_meta'):
        return _detach_django_object(obj)

    # Plain object - return as is
    return obj


def _detach_sqlalchemy_object(obj: Any) -> Any:
    """
    Detach SQLAlchemy object from session.

    Strategy:
    1. Create new instance of same class (plain object, not ORM-instrumented)
    2. Copy all column attribute values as regular Python attributes
    3. Optionally copy relationship attributes if they're already loaded

    Args:
        obj: SQLAlchemy model instance

    Returns:
        Detached copy of the object (plain Python object with same attributes)
    """
    try:
        from sqlalchemy import inspect

        # Get mapper/state information
        state = inspect(obj)

        # Create new instance
        cls = obj.__class__
        new_obj = cls.__new__(cls)

        # Initialize __dict__ to make it a plain Python object
        new_obj.__dict__ = {}

        # Copy all column attributes (simple values) as plain attributes
        for attr in state.mapper.column_attrs:
            try:
                value = getattr(obj, attr.key)
                # Set directly in __dict__ to avoid SQLAlchemy instrumentation
                new_obj.__dict__[attr.key] = value
            except Exception:
                # Skip attributes that can't be accessed
                pass

        # Also copy relationship attributes if they're loaded (not lazy)
        # This preserves any eagerly-loaded relationships
        for rel_attr in state.mapper.relationships:
            try:
                # Check if the relationship is already loaded
                if rel_attr.key in state.dict:
                    value = getattr(obj, rel_attr.key)
                    # For relationships, just copy the reference (don't deep copy here)
                    # The caller will handle deep copying if needed
                    new_obj.__dict__[rel_attr.key] = value
            except Exception:
                # Skip relationships that aren't loaded or can't be accessed
                pass

        return new_obj

    except ImportError:
        warnings.warn(
            "SQLAlchemy not installed, cannot detach ORM object. "
            "Returning original object (may cause pickling errors).",
            UserWarning
        )
        return obj
    except Exception as e:
        warnings.warn(
            f"Failed to detach SQLAlchemy object: {e}. "
            f"Returning original object (may cause pickling errors).",
            UserWarning
        )
        return obj


def _detach_django_object(obj: Any) -> Any:
    """
    Detach Django ORM object by copying field values.

    Args:
        obj: Django model instance

    Returns:
        New instance with copied field values (plain Python object)
    """
    try:
        cls = obj.__class__
        new_obj = cls.__new__(cls)

        # Initialize __dict__ to make it a plain Python object
        new_obj.__dict__ = {}

        # Copy all field values as plain attributes
        for field in obj._meta.fields:
            try:
                value = getattr(obj, field.name)
                # Set directly in __dict__ to avoid Django ORM instrumentation
                new_obj.__dict__[field.name] = value
            except Exception:
                # Skip fields that can't be accessed
                pass

        return new_obj

    except Exception as e:
        warnings.warn(
            f"Failed to detach Django object: {e}. "
            f"Returning original object (may cause pickling errors).",
            UserWarning
        )
        return obj


def copy_function_detaching_closure(func: Callable, memo: dict) -> Callable:
    """
    Copy a function while detaching any ORM objects in its closure.

    This is needed for lambda functions that capture ORM objects in their closures.
    Python function closures are immutable, but we can create new functions with
    modified closures.

    Args:
        func: Function to copy (may have closure with ORM objects)
        memo: deepcopy memo dict for circular reference tracking

    Returns:
        New function with ORM objects in closure detached from sessions.
        If the function has no closure or no ORM objects in closure, returns
        the original function.

    Examples:
        Lambda capturing ORM object::

            # Original lambda captures 'product' from ORM
            profit_func = lambda p: product.profit_per_unit * p.quantity

            # Create safe copy
            safe_func = copy_function_detaching_closure(profit_func, {})
            # safe_func uses detached copy of 'product'

        Lambda with no ORM objects::

            simple_func = lambda x: x * 2
            result = copy_function_detaching_closure(simple_func, {})
            # result is simple_func (same object, no modification needed)

    Note:
        This function uses advanced Python features (types.FunctionType, cell_contents).
        If creating the new function fails, the original function is returned with a warning.
    """
    if not callable(func):
        return func

    # No closure - simple case, return as-is
    if not hasattr(func, '__closure__') or func.__closure__ is None:
        return func

    # Has closure - check for ORM objects
    try:
        import types

        # Extract closure variables
        closure_vars = []
        needs_detachment = False

        for cell in func.__closure__:
            var = cell.cell_contents

            # Check if ORM object (SQLAlchemy or Django)
            is_orm = (
                hasattr(var, '_sa_instance_state') or
                (hasattr(var, '_state') and hasattr(var, '_meta'))
            )

            if is_orm:
                detached = detach_orm_object(var)
                closure_vars.append(detached)
                needs_detachment = True
            else:
                closure_vars.append(var)

        # If no ORM objects found, return original
        if not needs_detachment:
            return func

        # Create new function with detached closure
        new_func = types.FunctionType(
            func.__code__,
            func.__globals__,
            func.__name__,
            func.__defaults__,
            tuple(types.CellType(var) for var in closure_vars)
        )

        return new_func

    except Exception as e:
        warnings.warn(
            f"Failed to detach function closure: {e}. "
            f"Returning original function (may cause pickling errors).",
            UserWarning
        )
        return func


def materialize_and_detach_list(items: Optional[List[Any]], memo: dict) -> Optional[List[Any]]:
    """
    Materialize and detach a list of items that may contain ORM objects.

    This function:
    1. Detaches each ORM object from its session
    2. Deep copies the detached objects for complete independence

    Args:
        items: List of items (may contain ORM objects), or None
        memo: deepcopy memo dict for circular reference tracking

    Returns:
        New list with detached and deep-copied objects, or None if input is None

    Examples:
        List of SQLAlchemy objects::

            products = session.query(Product).all()  # List of ORM objects
            detached = materialize_and_detach_list(products, {})
            # detached contains copies independent of session

        Mixed list::

            items = [orm_object, plain_dict, orm_object2]
            detached = materialize_and_detach_list(items, {})
            # Each item processed appropriately

    Note:
        - Uses deepcopy after detachment for complete object independence
        - Handles None input gracefully
        - Safe to use on lists of plain Python objects (no modification)
    """
    from copy import deepcopy

    if items is None:
        return None

    result = []
    for item in items:
        # Detach ORM objects first
        detached = detach_orm_object(item)

        # Then deep copy for complete independence
        # This ensures no shared references between original and copy
        result.append(deepcopy(detached, memo))

    return result


__all__ = [
    'detach_orm_object',
    'copy_function_detaching_closure',
    'materialize_and_detach_list',
]
