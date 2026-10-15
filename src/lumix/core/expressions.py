"""Expression classes for LumiX optimization models."""

from __future__ import annotations

import functools
import inspect
import math
import numbers
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, Iterable, List, Literal, Optional, Sequence, Tuple, TypeVar

from typing_extensions import Self

from .variables import LXVariable

TModel = TypeVar("TModel")


class LXKeyFilter:
    """
    Term filter that keeps the variable instances whose index key is in ``keys``.

    Created by ``keys=`` in :meth:`LXLinearExpression.add_term`,
    :meth:`LXLinearExpression.add_multi_term` and
    :meth:`LXLinearExpression.sum_over`. It is callable like a ``where``
    function, so every component that reads expression terms keeps working.
    Solver adapters recognise it and look matching instances up by key
    instead of scanning the whole variable family (see
    *Performance Considerations* in the user guide).

    Args:
        var: Variable family the keys belong to
        keys: Index keys in the form returned by :meth:`LXVariable.index_key`
    """

    __slots__ = ("var", "keys")

    def __init__(self, var: "LXVariable", keys: Iterable[Any]):
        if isinstance(keys, (str, bytes)):
            raise TypeError(
                "keys must be an iterable of index keys, not a single string; "
                "wrap a single key in a list: keys=[key]"
            )
        try:
            key_set = frozenset(keys)
        except TypeError as err:
            raise TypeError(
                "keys must be hashable; write indexed_by_product keys as tuples, "
                "not lists, e.g. keys=[(plant.id, customer.id)]"
            ) from err
        if var.index_func is None and var._cartesian is not None:
            width = len(var._cartesian.dimensions)
            if any(not isinstance(k, tuple) or len(k) != width for k in key_set):
                raise TypeError(
                    f"keys for the indexed_by_product variable {var.name!r} must be a "
                    f"list of tuples with {width} dimension keys each, "
                    "e.g. keys=[(plant.id, customer.id)]"
                )
        self.var = var
        self.keys = key_set

    def __call__(self, *instance: Any) -> bool:
        item = instance[0] if len(instance) == 1 else instance
        return self.var.index_key(item) in self.keys

    def __repr__(self) -> str:
        return f"LXKeyFilter({self.var.name!r}, {len(self.keys)} keys)"


_NO_ROW = object()


class LXRowKeyFilter:
    """
    Row-aware term filter for indexed constraints: in the row ``r`` it keeps the
    instance whose index key is ``row_key(r)``. The canonical builder looks that
    instance up by key instead of testing every instance, so an indexed constraint
    whose rows each use one instance of another family builds in linear time.

    Called with an instance only (no row), it keeps every instance; a coefficient
    that takes ``(instance, row)`` must then select the row's instance.

    .. versionadded:: 0.3.0
    """

    __slots__ = ("var", "row_key")
    _lumix_arity = 2

    def __init__(self, var: "LXVariable", row_key: Callable[[Any], Any]):
        self.var = var
        self.row_key = row_key

    def __call__(self, instance: Any, row: Any = _NO_ROW) -> bool:
        if row is _NO_ROW:
            return True
        return self.var.index_key(instance) == self.row_key(row)

    def __repr__(self) -> str:
        return f"LXRowKeyFilter({self.var.name!r})"


def _key_or_where(var: "LXVariable", where: Optional[Callable[..., bool]],
                  keys: Optional[Iterable[Any]]) -> Optional[Callable[..., bool]]:
    if keys is None:
        return where
    if where is not None:
        raise ValueError("Pass either where= or keys=, not both")
    return LXKeyFilter(var, keys)


def call_arity(func: Callable[..., Any]) -> int:
    """How many positional arguments a coefficient or filter takes: 1 (the
    variable instance) or 2 (the instance and the constraint row instance).

    Wrappers built by LumiX (merged and scaled terms) carry ``_lumix_arity``;
    other ``*args`` callables count as 2. Parameters with a default value do not
    count, so ``lambda item, g=g: ...`` (loop-variable capture) takes one argument."""
    explicit = getattr(func, "_lumix_arity", None)
    if explicit is not None:
        return explicit
    if isinstance(func, LXKeyFilter):
        return 1
    try:
        params = inspect.signature(func).parameters.values()
    except (TypeError, ValueError):
        return 1
    positional = 0
    for p in params:
        if p.kind == p.VAR_POSITIONAL:
            return 2
        if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD) and p.default is p.empty:
            positional += 1
    return 2 if positional >= 2 else 1


def call_with_row(func: Callable[..., Any], instance: Any, row: Any) -> Any:
    """Call ``func`` with the constraint row instance when it takes two arguments."""
    if row is not None and call_arity(func) > 1:
        return func(instance, row)
    return func(instance)


def _call_coeff(coeff_func: Callable[..., float], args: tuple) -> float:
    """Call a coefficient with (instance, constraint_instance) when it accepts two
    arguments, else with the instance only."""
    return call_with_row(coeff_func, args[0], args[1] if len(args) > 1 else None)


def positional_count(func: Callable[..., Any]) -> float:
    """Number of required positional parameters (``math.inf`` with ``*args``)."""
    try:
        params = inspect.signature(func).parameters.values()
    except (TypeError, ValueError):
        return 1
    count = 0
    for p in params:
        if p.kind == p.VAR_POSITIONAL:
            return math.inf
        if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD) and p.default is p.empty:
            count += 1
    return count


def _scale_quadratic(coeff: Any, scalar: float) -> Any:
    if not callable(coeff):
        return float(coeff) * scalar

    @functools.wraps(coeff)
    def scaled(*args: Any) -> float:
        return scalar * coeff(*args)
    return scaled


def term_parts(coeff: Callable[..., Any], where: Callable[..., Any]) -> List[Tuple[Any, Any]]:
    """The ``(coeff, where)`` terms a term was combined from (itself when it was not
    combined). The canonical builder applies the row-narrowing rule to each part,
    so ``add_term(x, 1.0)`` merged with a two-argument term on ``x`` still narrows."""
    return list(getattr(coeff, "_lumix_parts", None) or [(coeff, where)])


def _merge_terms(first: tuple, second: tuple) -> tuple:
    """Combine two terms on the same variable into one equivalent term.

    An instance is included when either term includes it, and its coefficient
    is the sum of the coefficients of the terms that include it.
    """
    var, coeff1, where1 = first
    _, coeff2, where2 = second
    row_aware = max(call_arity(coeff1), call_arity(where1),
                    call_arity(coeff2), call_arity(where2))

    def merged_coeff(*args: Any) -> float:
        row = args[1] if len(args) > 1 else None
        total = 0.0
        if call_with_row(where1, args[0], row):
            total += call_with_row(coeff1, args[0], row)
        if call_with_row(where2, args[0], row):
            total += call_with_row(coeff2, args[0], row)
        return total

    def merged_where(*args: Any) -> bool:
        row = args[1] if len(args) > 1 else None
        return bool(call_with_row(where1, args[0], row) or call_with_row(where2, args[0], row))

    merged_coeff._lumix_arity = row_aware  # type: ignore[attr-defined]
    merged_coeff._lumix_parts = term_parts(coeff1, where1) + term_parts(coeff2, where2)  # type: ignore[attr-defined]
    merged_where._lumix_arity = max(call_arity(where1), call_arity(where2))  # type: ignore[attr-defined]
    return (var, merged_coeff, merged_where)


def _scaled(coeff_func: Callable[..., float], scalar: float) -> Callable[..., float]:
    def scaled(*args: Any) -> float:
        return coeff_func(*args) * scalar
    scaled._lumix_arity = call_arity(coeff_func)  # type: ignore[attr-defined]
    parts = getattr(coeff_func, "_lumix_parts", None)
    if parts:
        scaled._lumix_parts = [(_scaled(c, scalar), w) for c, w in parts]  # type: ignore[attr-defined]
    return scaled


@dataclass
class LXLinearExpression(Generic[TModel]):
    """
    Type-safe linear expression builder with multi-model support.

    Represents: sum(coeff[i] * var[i]) + constant

    Examples::

        expr = LXLinearExpression()
        expr.add_term(production, 1.0)
        expr.add_term(inventory, -1.0)
        expr.add_constant(100)

        # Multi-model
        expr = LXLinearExpression()
        expr.sum_over(duty, where=lambda driver, date: date.is_weekend)
    """

    terms: Dict[str, Tuple[LXVariable, Callable[[TModel], float]], Tuple[Callable[[TModel], bool]]] = field(default_factory=dict)
    constant: float = 0.0

    # Multi-model terms
    _multi_terms: List[Tuple[LXVariable, Callable[..., float], Optional[Callable[..., bool]]]] = field(
        default_factory=list)

    def __deepcopy__(self, memo):
        """Copy the expression structure; share data instances and callables.

        Data instances (plain objects and ORM objects alike) and callables are shared
        with the original, so closures and identity checks behave the same in the copy.
        An ORM-backed source is materialized once (its query runs at copy time).

        Args:
            memo: Dictionary for tracking circular references during deepcopy

        .. versionchanged:: 0.3.0
           Instances are shared instead of deep-copied/detached (catalog A23, B15).
        """
        from copy import deepcopy

        # Create new instance
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result

        # Copy simple attributes
        result.constant = self.constant

        # Deep copy terms dictionary
        # Each term: (LXVariable, coeff_func, where_func)
        result.terms = {}
        for var_name, (var, coeff_func, where_func) in self.terms.items():
            result.terms[var_name] = (deepcopy(var, memo), coeff_func, where_func)

        # Deep copy multi-terms list
        # Each multi-term: (LXVariable, coeff_func, where_func)
        result._multi_terms = []
        for var, coeff_func, where_func in self._multi_terms:
            result._multi_terms.append((deepcopy(var, memo), coeff_func, where_func))

        return result

    def add_term(
            self, var: LXVariable[TModel, Any],
            coeff: float | Callable[[TModel], float] = 1.0,
            where: Callable[[TModel], bool] | None = None,
            keys: Iterable[Any] | None = None,
    ) -> Self:
        """
        Add term with coefficient (constant or function).

        Args:
            var: Variable Family to add
            coeff: Coefficient (constant or function)
            where: Optional filter function
            keys: Optional index keys of the instances to include, in the form
                returned by :meth:`LXVariable.index_key`. Equivalent to a
                ``where`` that tests key membership, but solver adapters look
                the instances up directly, so large models build much faster.
                Cannot be combined with ``where``.

        Returns:
            Self for chaining
        """
        coeff_func = coeff if callable(coeff) else lambda _: coeff
        where = _key_or_where(var, where, keys)
        if where is None:
            where = lambda _: True
        term = (var, coeff_func, where)
        if var.name in self.terms:
            term = _merge_terms(self.terms[var.name], term)
        self.terms[var.name] = term
        return self

    def add_multi_term(
            self,
            var: LXVariable,
            coeff: Callable[..., float] = lambda *args: 1.0,
            where: Optional[Callable[..., bool]] = None,
            keys: Optional[Iterable[Any]] = None,
    ) -> Self:
        """
        Add multi-indexed variable to expression.

        Args:
            var: Multi-indexed variable family
            coeff: Coefficient function receiving all dimension models
            where: Optional filter function
            keys: Optional index keys of the instances to include; for
                ``indexed_by_product`` families each key is the tuple of the
                dimension keys, e.g. ``(plant.id, customer.id)``. Cannot be
                combined with ``where``.

        Returns:
            Self for chaining

        Example::

            expr.add_multi_term(
                duty,
                coeff=lambda driver, date: driver.cost * date.multiplier,
                where=lambda driver, date: date.is_weekend
            )

            # Same terms, looked up by key (fast for large families)
            weekend = [(d.id, dt.id) for d in drivers for dt in dates if dt.is_weekend]
            expr.add_multi_term(
                duty,
                coeff=lambda driver, date: driver.cost * date.multiplier,
                keys=weekend
            )
        """
        self._multi_terms.append((var, coeff, _key_or_where(var, where, keys)))
        return self

    def sum_over(
            self,
            var: LXVariable,
            where: Optional[Callable[..., bool]] = None,
            keys: Optional[Iterable[Any]] = None,
    ) -> Self:
        """
        Syntactic sugar for summing over all dimensions of a variable.

        Args:
            var: Variable to sum over all its dimensions
            where: Optional filter function to selectively include terms
            keys: Optional index keys of the instances to include (see add_multi_term)

        Returns:
            Self for chaining

        Example::

            # Sum all driver duties (over all drivers and dates)
            expr.sum_over(duty)

            # Sum duties for all drivers on a specific date
            expr.sum_over(duty, where=lambda d, dt: dt == specific_date)

        Note:
            Currently sums over all dimensions. Future enhancement could add
            selective dimension summing (e.g., sum only over drivers, not dates).
        """
        return self.add_multi_term(var, where=where, keys=keys)

    def add_constant(self, value: float) -> Self:
        """
        Add constant to expression.

        Args:
            value: Constant value

        Returns:
            Self for chaining
        """
        self.constant += value
        return self

    def __iadd__(self, other: "numbers.Real | LXLinearExpression") -> Self:
        """``expr += other``: add terms (or a constant) to this expression in place.

        Terms on the same variable are merged: an instance is included when
        either expression includes it, with the sum of the coefficients that
        apply to it.
        """
        if isinstance(other, numbers.Real):
            self.constant += float(other)
            return self
        if not isinstance(other, LXLinearExpression):
            return NotImplemented
        for var_name, term in other.terms.items():
            if var_name in self.terms:
                self.terms[var_name] = _merge_terms(self.terms[var_name], term)
            else:
                self.terms[var_name] = term
        self.constant += other.constant
        self._multi_terms.extend(other._multi_terms)
        return self

    def __add__(self, other: Any) -> Any:
        """``expr1 + expr2`` or ``expr + constant``: a new expression; the operands
        are not changed.

        .. versionchanged:: 0.3.0
           Returns a new expression (``+`` used to change ``expr1``); use ``+=``
           to add in place.
        """
        if isinstance(other, LXQuadraticExpression):
            return other + self
        if not isinstance(other, (numbers.Real, LXLinearExpression)):
            return NotImplemented
        result = self.copy()
        result += other
        return result

    def __radd__(self, other: Any) -> Any:
        """``constant + expr``; makes ``sum([e1, e2, ...])`` work."""
        return self + other

    def __sub__(self, other: Any) -> Any:
        """``expr1 - expr2`` or ``expr - constant`` (a new expression)."""
        if isinstance(other, LXQuadraticExpression):
            return (-other) + self
        if isinstance(other, numbers.Real):
            return self + (-float(other))
        if isinstance(other, LXLinearExpression):
            return self + other * -1
        return NotImplemented

    def __rsub__(self, other: Any) -> Any:
        """``constant - expr``."""
        return self * -1 + other

    def __neg__(self) -> Self:
        """``-expr`` (a new expression)."""
        return self * -1

    def __imul__(self, scalar: "numbers.Real") -> Self:
        """``expr *= scalar`` in place."""
        if not isinstance(scalar, numbers.Real):
            return NotImplemented
        scalar = float(scalar)
        for var_name, (var, coeff_func, where) in list(self.terms.items()):
            self.terms[var_name] = (var, _scaled(coeff_func, scalar), where)
        self._multi_terms = [
            (var, _scaled(coeff_func, scalar), where)
            for var, coeff_func, where in self._multi_terms
        ]
        self.constant *= scalar
        return self

    def __mul__(self, scalar: "numbers.Real") -> Self:
        """``expr * scalar`` or ``scalar * expr`` (a new expression).

        .. versionchanged:: 0.3.0
           Returns a new expression; use ``*=`` to scale in place.
        """
        if not isinstance(scalar, numbers.Real):
            return NotImplemented
        result = self.copy()
        result *= scalar
        return result

    __rmul__ = __mul__

    def copy(self) -> Self:
        """
        Create a deep copy of this expression.

        Returns:
            New expression with same terms and constant
        """
        new_expr = LXLinearExpression[TModel]()
        new_expr.terms = self.terms.copy()
        new_expr.constant = self.constant
        new_expr._multi_terms = self._multi_terms.copy()
        return new_expr


@dataclass
class LXQuadraticTerm:
    """
    Quadratic term: coeff * var1 * var2

    Used in portfolio optimization, risk modeling, etc.
    """

    var1: LXVariable
    var2: LXVariable
    #: A number, or ``callable(instance1, instance2)`` (``callable(instance)`` for a
    #: diagonal term).
    coefficient: Any = 1.0
    #: ``add_squared``: one product per instance (``x_i * x_i``) instead of every pair.
    diagonal: bool = False

    def __deepcopy__(self, memo):
        """Custom deepcopy that handles variables.

        Args:
            memo: Dictionary for tracking circular references during deepcopy

        Returns:
            Deep copy of this quadratic term
        """
        from copy import deepcopy

        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result

        result.var1 = deepcopy(self.var1, memo)
        result.var2 = deepcopy(self.var2, memo)
        result.coefficient = self.coefficient
        result.diagonal = self.diagonal

        return result

    def is_squared_term(self) -> bool:
        """Check if this is x^2 (same variable twice)."""
        return self.var1.name == self.var2.name


@dataclass
class LXQuadraticExpression:
    """
    Quadratic expression: linear_terms + quadratic_terms + constant

    Represents: sum(coeff * x[i] * x[j]) + c^T x + constant

    Example::

        # Portfolio variance sum(cov[i][j] * w[i] * w[j]) minus expected return
        quad_expr = LXQuadraticExpression()
        quad_expr.add_quadratic(weight, weight, lambda a, b: cov[a.id][b.id])
        quad_expr.linear_terms.add_term(weight, lambda a: -a.expected_return)
    """

    linear_terms: LXLinearExpression = field(default_factory=LXLinearExpression)
    quadratic_terms: List[LXQuadraticTerm] = field(default_factory=list)
    constant: float = 0.0

    def __deepcopy__(self, memo):
        """Custom deepcopy that handles linear and quadratic terms.

        This method enables what-if analysis on quadratic expressions by:
        1. Deep copying the linear expression component
        2. Deep copying all quadratic terms
        3. Preserving the expression structure

        Args:
            memo: Dictionary for tracking circular references during deepcopy

        Returns:
            Deep copy of this quadratic expression with all dependencies resolved
        """
        from copy import deepcopy

        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result

        # Deep copy linear terms
        result.linear_terms = deepcopy(self.linear_terms, memo)

        # Deep copy quadratic terms
        result.quadratic_terms = [deepcopy(term, memo) for term in self.quadratic_terms]

        # Copy constant
        result.constant = self.constant

        return result

    def add_quadratic(self, var1: LXVariable, var2: LXVariable, coeff: Any = 1.0) -> Self:
        """
        Add ``sum(coeff(i, j) * var1[i] * var2[j])`` over every instance ``i`` of
        ``var1`` and ``j`` of ``var2``. For single variables this is
        ``coeff * var1 * var2``; a numeric ``coeff`` on families gives
        ``coeff * sum(var1) * sum(var2)``.

        Args:
            var1: First variable family
            var2: Second variable family (may be ``var1``)
            coeff: Number, or ``callable(instance1, instance2)``, e.g.
                ``lambda a, b: 0.5 * cov[a.id][b.id]``

        Returns:
            Self for chaining
        """
        self.quadratic_terms.append(LXQuadraticTerm(var1, var2, coeff))
        return self

    def add_squared(self, var: LXVariable, coeff: Any = 1.0) -> Self:
        """
        Add ``sum(coeff(i) * var[i] ** 2)`` (one square per instance).

        Args:
            var: Variable to square
            coeff: Coefficient

        Returns:
            Self for chaining
        """
        self.quadratic_terms.append(LXQuadraticTerm(var, var, coeff, diagonal=True))
        return self

    def add_quadratic_term(self, var1: Any, var2: Optional[LXVariable] = None,
                           coefficient: Any = 1.0) -> Self:
        """Add ``coefficient * var1 * var2``, or an :class:`LXQuadraticTerm`.

        .. versionadded:: 0.3.0
        """
        if isinstance(var1, LXQuadraticTerm):
            self.quadratic_terms.append(var1)
            return self
        if var2 is None:
            raise ValueError("add_quadratic_term needs two variables or an LXQuadraticTerm")
        return self.add_quadratic(var1, var2, coefficient)

    def __add__(self, other: Any) -> "LXQuadraticExpression":
        """``quad + quad``, ``quad + linear`` or ``quad + constant``: a new expression
        holding the terms and constants of both operands.

        .. versionchanged:: 0.3.0
           Returns a new expression and keeps the quadratic terms of both sides.
        """
        result = LXQuadraticExpression(self.linear_terms.copy(), list(self.quadratic_terms),
                                       self.constant)
        if isinstance(other, LXQuadraticExpression):
            result.linear_terms += other.linear_terms
            result.quadratic_terms.extend(other.quadratic_terms)
            result.constant += other.constant
        elif isinstance(other, LXLinearExpression):
            result.linear_terms += other
        elif isinstance(other, numbers.Real):
            result.constant += float(other)
        else:
            return NotImplemented
        return result

    __radd__ = __add__

    def __mul__(self, scalar: Any) -> "LXQuadraticExpression":
        """``quad * scalar`` or ``scalar * quad`` (a new expression)."""
        if not isinstance(scalar, numbers.Real):
            return NotImplemented
        s = float(scalar)
        terms = [LXQuadraticTerm(t.var1, t.var2, _scale_quadratic(t.coefficient, s), t.diagonal)
                 for t in self.quadratic_terms]
        return LXQuadraticExpression(self.linear_terms * s, terms, self.constant * s)

    __rmul__ = __mul__

    def __neg__(self) -> "LXQuadraticExpression":
        return self * -1

    def __sub__(self, other: Any) -> Any:
        if isinstance(other, (numbers.Real, LXLinearExpression, LXQuadraticExpression)):
            return self + (-other)
        return NotImplemented

    def __rsub__(self, other: Any) -> Any:
        return (-self) + other


def _require_variable(value: Any, method: str) -> None:
    """Nonlinear terms act on variables; an expression must be named by a variable first."""
    if not isinstance(value, LXVariable):
        raise TypeError(
            f"{method}() takes an LXVariable, got {type(value).__name__}. To apply it to an "
            "expression, add a variable equal to the expression (a constraint "
            "'d - expression == 0') and pass that variable")


@dataclass
class LXNonLinearExpression:
    """
    Non-linear expression containing arbitrary non-linear terms.

    Supports:
    - Bilinear terms (x * y)
    - Absolute value (|x|)
    - Min/max functions
    - Piecewise-linear approximations
    - Conditional expressions
    - Custom non-linear functions

    These will be automatically linearized by the Linearizer engine.

    Example:
        # Create nonlinear expression
        expr = LXNonLinearExpression()

        # Add bilinear product
        expr.add_product(length, width)

        # Add absolute value
        expr.add_abs(deviation)

        # Add piecewise function
        expr.add_piecewise(time, lambda t: math.exp(t), num_segments=30)
    """

    linear_terms: LXLinearExpression = field(default_factory=LXLinearExpression)
    nonlinear_terms: List[Any] = field(default_factory=list)
    constant: float = 0.0

    def add_linear(self, expr: LXLinearExpression) -> Self:
        """
        Add linear terms.

        Args:
            expr: Linear expression to add

        Returns:
            Self for chaining
        """
        self.linear_terms = self.linear_terms + expr
        return self

    def add_abs(self, var: LXVariable, coeff: float = 1.0) -> Self:
        """
        Add absolute value term: coeff * |var|

        Args:
            var: Variable to take absolute value of
            coeff: Coefficient (default: 1.0)

        Returns:
            Self for chaining

        Example:
            # Minimize the absolute value of a deviation variable
            expr.add_abs(deviation)
        """
        from ..nonlinear.terms import LXAbsoluteTerm

        _require_variable(var, "add_abs")

        self.nonlinear_terms.append(LXAbsoluteTerm(var, coeff))
        return self

    def add_min(self, *vars: LXVariable, coefficients: Optional[List[float]] = None) -> Self:
        """
        Add minimum function: min(vars)

        Args:
            *vars: Variables to take minimum of
            coefficients: Optional coefficients for each variable

        Returns:
            Self for chaining

        Example:
            # Minimum of three costs
            expr.add_min(cost_a, cost_b, cost_c)
        """
        from ..nonlinear.terms import LXMinMaxTerm

        for v in vars:
            _require_variable(v, "add_min")
        coeffs = coefficients or [1.0] * len(vars)
        self.nonlinear_terms.append(LXMinMaxTerm(list(vars), "min", coeffs))
        return self

    def add_max(self, *vars: LXVariable, coefficients: Optional[List[float]] = None) -> Self:
        """
        Add maximum function: max(vars)

        Args:
            *vars: Variables to take maximum of
            coefficients: Optional coefficients for each variable

        Returns:
            Self for chaining

        Example:
            # Maximum capacity
            expr.add_max(capacity_1, capacity_2, capacity_3)
        """
        from ..nonlinear.terms import LXMinMaxTerm

        for v in vars:
            _require_variable(v, "add_max")
        coeffs = coefficients or [1.0] * len(vars)
        self.nonlinear_terms.append(LXMinMaxTerm(list(vars), "max", coeffs))
        return self

    def add_product(self, var1: LXVariable, var2: LXVariable, coeff: float = 1.0) -> Self:
        """
        Add bilinear product: coeff * var1 * var2

        Automatically linearized based on variable types:
        - Binary × Binary: AND logic
        - Binary × Continuous: Big-M method
        - Continuous × Continuous: McCormick envelopes

        Args:
            var1: First variable
            var2: Second variable
            coeff: Coefficient (default: 1.0)

        Returns:
            Self for chaining

        Example:
            # Rectangle area
            expr.add_product(length, width)

            # Facility open × flow amount
            expr.add_product(is_open, flow_amount)
        """
        from ..nonlinear.terms import LXBilinearTerm

        _require_variable(var1, "add_product")
        _require_variable(var2, "add_product")
        self.nonlinear_terms.append(LXBilinearTerm(var1, var2, coeff))
        return self

    def add_indicator(
        self,
        binary_var: LXVariable,
        condition: bool,
        linear_expr: LXLinearExpression,
        sense: Literal["<=", ">=", "=="] = "<=",
        rhs: float = 0.0,
    ) -> Self:
        """
        Add a conditional row: if ``binary_var == condition`` then
        ``linear_expr <sense> rhs``.

        The term adds rows to the model and nothing to the expression's value, so it is
        usually placed in the objective expression next to the linear part.

        Args:
            binary_var: Binary variable (a single variable)
            condition: Condition value (True or False)
            linear_expr: Left-hand side of the conditional row
            sense: ``"<="`` (default), ``">="`` or ``"=="``
            rhs: Right-hand side (default 0)

        Returns:
            Self for chaining

        Raises:
            ValueError: If ``sense`` is not one of the three senses.

        Example::

            # If the warehouse is open, it ships at least 10 units
            expr.add_indicator(
                is_open,
                True,
                LXLinearExpression().add_term(supply, 1.0),
                sense=">=",
                rhs=10,
            )

        .. versionchanged:: 0.3.0
           ``sense`` and ``rhs`` (the row was always ``<= 0`` before).
        """
        from ..nonlinear.terms import LXIndicatorTerm

        _require_variable(binary_var, "add_indicator")
        if sense not in ("<=", ">=", "=="):
            raise ValueError(f"add_indicator: sense must be '<=', '>=' or '==', not {sense!r}")
        self.nonlinear_terms.append(
            LXIndicatorTerm(binary_var, condition, linear_expr, sense, float(rhs)))
        return self

    def add_piecewise(
        self,
        var: LXVariable,
        func: Callable[[float], float],
        num_segments: Optional[int] = None,
        x_min: Optional[float] = None,
        x_max: Optional[float] = None,
        adaptive: Optional[bool] = None,
        method: Optional[Literal["sos2", "incremental", "logarithmic"]] = None,
        breakpoints: Optional[Sequence[float]] = None,
    ) -> Self:
        """
        Add piecewise-linear approximation of arbitrary function.

        The approximation domain ``[x_min, x_max]`` (or the first and last
        breakpoint) constrains ``var``: the variable cannot take values outside
        it. A ``UserWarning`` is issued when the domain is narrower than the
        variable's bounds.

        Args:
            var: Input variable
            func: Function to approximate (e.g., lambda x: math.exp(x))
            num_segments: Number of linear segments (default: ``None`` — taken from
                ``LXLinearizerConfig.pwl_num_segments``, 20)
            x_min: Minimum domain value (default: var.lower_bound)
            x_max: Maximum domain value (default: var.upper_bound)
            adaptive: Use adaptive breakpoint generation (default: ``None`` — taken
                from ``LXLinearizerConfig.adaptive_breakpoints``, True)
            method: Linearization method ("sos2", "incremental", "logarithmic");
                all three are exact for the piecewise-linear function through
                the breakpoints (default: ``None`` — taken from
                ``LXLinearizerConfig.pwl_method``, "sos2")
            breakpoints: Strictly increasing x-coordinates to use instead of
                generated ones (``num_segments``, ``adaptive``, ``x_min`` and
                ``x_max`` are then not used). With a ``func`` that is itself
                piecewise linear through these points, the term is exact.

        Returns:
            Self for chaining

        .. versionchanged:: 0.3.0
           ``num_segments``, ``adaptive`` and ``method`` default to ``None`` so that
           the linearizer configuration applies when they are left open.

        Example::

            # Exponential growth
            expr.add_piecewise(time, lambda t: math.exp(t), num_segments=30)

            # Custom discount curve
            expr.add_piecewise(
                quantity,
                lambda q: 1.0 if q < 100 else 0.9 if q < 1000 else 0.8,
                num_segments=50
            )
        """
        from ..nonlinear.terms import LXPiecewiseLinearTerm

        _require_variable(var, "add_piecewise")
        self.nonlinear_terms.append(
            LXPiecewiseLinearTerm(var, func, num_segments, x_min, x_max, adaptive, method,
                                  None if breakpoints is None else list(breakpoints))
        )
        return self

    def add_nonlinear_term(self, term: Any) -> Self:
        """
        Add pre-constructed non-linear term.

        Args:
            term: Non-linear term object

        Returns:
            Self for chaining
        """
        self.nonlinear_terms.append(term)
        return self

    def add_nonlinear_terms(self, terms: List[Any]) -> Self:
        """
        Add multiple non-linear terms.

        Args:
            terms: List of non-linear terms

        Returns:
            Self for chaining
        """
        self.nonlinear_terms.extend(terms)
        return self


__all__ = [
    "LXRowKeyFilter",
    "LXLinearExpression",
    "LXQuadraticTerm",
    "LXQuadraticExpression",
    "LXNonLinearExpression",
]
