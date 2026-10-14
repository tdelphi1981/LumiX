"""Expression classes for LumiX optimization models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, Iterable, List, Literal, Optional, Tuple, TypeVar

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
        self.var = var
        self.keys = frozenset(keys)

    def __call__(self, *instance: Any) -> bool:
        item = instance[0] if len(instance) == 1 else instance
        return self.var.index_key(item) in self.keys

    def __repr__(self) -> str:
        return f"LXKeyFilter({self.var.name!r}, {len(self.keys)} keys)"


def _key_or_where(var: "LXVariable", where: Optional[Callable[..., bool]],
                  keys: Optional[Iterable[Any]]) -> Optional[Callable[..., bool]]:
    if keys is None:
        return where
    if where is not None:
        raise ValueError("Pass either where= or keys=, not both")
    return LXKeyFilter(var, keys)


def _call_coeff(coeff_func: Callable[..., float], args: tuple) -> float:
    """Call a coefficient with (instance, constraint_instance) when it accepts two
    arguments, else with the instance only -- the same fallback adapters use."""
    if len(args) > 1:
        try:
            return coeff_func(*args)
        except TypeError:
            return coeff_func(args[0])
    return coeff_func(*args)


def _merge_terms(first: tuple, second: tuple) -> tuple:
    """Combine two terms on the same variable into one equivalent term.

    An instance is included when either term includes it, and its coefficient
    is the sum of the coefficients of the terms that include it.
    """
    var, coeff1, where1 = first
    _, coeff2, where2 = second

    def merged_coeff(*args: Any) -> float:
        total = 0.0
        if where1(args[0]):
            total += _call_coeff(coeff1, args)
        if where2(args[0]):
            total += _call_coeff(coeff2, args)
        return total

    def merged_where(instance: Any) -> bool:
        return bool(where1(instance) or where2(instance))

    return (var, merged_coeff, merged_where)


def _scaled(coeff_func: Callable[..., float], scalar: float) -> Callable[..., float]:
    def scaled(*args: Any) -> float:
        return coeff_func(*args) * scalar
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
        expr.constant(100)

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
        """Custom deepcopy that handles variables and lambda functions.

        This method enables what-if analysis on expressions by:
        1. Deep copying all variables in the expression
        2. Safely copying coefficient and filter lambda functions
        3. Preserving the expression structure

        Args:
            memo: Dictionary for tracking circular references during deepcopy

        Returns:
            Deep copy of this expression with all dependencies resolved
        """
        from copy import deepcopy
        from ..utils.copy_utils import copy_function_detaching_closure

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
            copied_var = deepcopy(var, memo)
            copied_coeff = copy_function_detaching_closure(coeff_func, memo)
            copied_where = copy_function_detaching_closure(where_func, memo)
            result.terms[var_name] = (copied_var, copied_coeff, copied_where)

        # Deep copy multi-terms list
        # Each multi-term: (LXVariable, coeff_func, where_func)
        result._multi_terms = []
        for var, coeff_func, where_func in self._multi_terms:
            copied_var = deepcopy(var, memo)
            copied_coeff = copy_function_detaching_closure(coeff_func, memo)
            copied_where = (
                copy_function_detaching_closure(where_func, memo)
                if where_func is not None
                else None
            )
            result._multi_terms.append((copied_var, copied_coeff, copied_where))

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

    def __add__(self, other: float | Self) -> Self:
        """
        Enable expr1 + expr2 or expr + constant.

        Terms on the same variable are merged: an instance is included when
        either expression includes it, with the sum of the coefficients that
        apply to it.

        Args:
            other: Expression or constant to add

        Returns:
            Self for chaining
        """
        if isinstance(other, (int, float)):
            self.constant += other
            return self
        # Merge expressions
        for var_name, term in other.terms.items():
            if var_name in self.terms:
                self.terms[var_name] = _merge_terms(self.terms[var_name], term)
            else:
                self.terms[var_name] = term
        self.constant += other.constant
        # Also merge multi-terms
        self._multi_terms.extend(other._multi_terms)
        return self

    def __mul__(self, scalar: float) -> Self:
        """
        Enable scalar * expression.

        Args:
            scalar: Scalar multiplier

        Returns:
            Self for chaining
        """
        for var_name, (var, coeff_func, where) in list(self.terms.items()):
            self.terms[var_name] = (var, _scaled(coeff_func, scalar), where)
        self._multi_terms = [
            (var, _scaled(coeff_func, scalar), where)
            for var, coeff_func, where in self._multi_terms
        ]
        self.constant *= scalar
        return self

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
    coefficient: float = 1.0

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

        return result

    def is_squared_term(self) -> bool:
        """Check if this is x^2 (same variable twice)."""
        return self.var1.name == self.var2.name


@dataclass
class LXQuadraticExpression:
    """
    Quadratic expression: linear_terms + quadratic_terms + constant

    Represents: 0.5 * x^T Q x + c^T x + constant

    Example:
        # Portfolio variance: sum(w[i] * w[j] * cov[i,j])
        # Plus linear returns: sum(return[i] * w[i])
        quad_expr = LXQuadraticExpression()
        quad_expr.add_quadratic(w[0], w[1], cov[0,1])
        quad_expr.linear_terms.add_term(w[0], returns[0])
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

    def add_quadratic(self, var1: LXVariable, var2: LXVariable, coeff: float = 1.0) -> Self:
        """
        Add quadratic term.

        Args:
            var1: First variable
            var2: Second variable
            coeff: Coefficient

        Returns:
            Self for chaining
        """
        self.quadratic_terms.append(LXQuadraticTerm(var1, var2, coeff))
        return self

    def add_squared(self, var: LXVariable, coeff: float = 1.0) -> Self:
        """
        Add x^2 term.

        Args:
            var: Variable to square
            coeff: Coefficient

        Returns:
            Self for chaining
        """
        self.quadratic_terms.append(LXQuadraticTerm(var, var, coeff))
        return self

    def __add__(self, other: LXLinearExpression | float) -> Self:
        """
        Enable: quad_expr + linear_expr or quad_expr + constant.

        Args:
            other: Linear expression or constant

        Returns:
            Self for chaining
        """
        if isinstance(other, LXLinearExpression):
            self.linear_terms = self.linear_terms + other
        elif isinstance(other, (int, float)):
            self.constant += other
        return self


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
            # Minimize absolute deviation
            expr.add_abs(actual - target)
        """
        from ..nonlinear.terms import LXAbsoluteTerm

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

        self.nonlinear_terms.append(LXBilinearTerm(var1, var2, coeff))
        return self

    def add_indicator(
        self, binary_var: LXVariable, condition: bool, linear_expr: LXLinearExpression
    ) -> Self:
        """
        Add conditional constraint: if binary_var == condition then linear_expr

        Args:
            binary_var: Binary variable
            condition: Condition value (True or False)
            linear_expr: Expression to apply when condition is met

        Returns:
            Self for chaining

        Example::

            # If warehouse is open, then demand must be met
            expr.add_indicator(
                is_open,
                True,
                LXLinearExpression().add_term(supply, 1.0)
            )
        """
        from ..nonlinear.terms import LXIndicatorTerm

        self.nonlinear_terms.append(LXIndicatorTerm(binary_var, condition, linear_expr))
        return self

    def add_piecewise(
        self,
        var: LXVariable,
        func: Callable[[float], float],
        num_segments: int = 20,
        x_min: Optional[float] = None,
        x_max: Optional[float] = None,
        adaptive: bool = True,
        method: Literal["sos2", "incremental", "logarithmic"] = "sos2",
    ) -> Self:
        """
        Add piecewise-linear approximation of arbitrary function.

        Args:
            var: Input variable
            func: Function to approximate (e.g., lambda x: math.exp(x))
            num_segments: Number of linear segments
            x_min: Minimum domain value (default: var.lower_bound)
            x_max: Maximum domain value (default: var.upper_bound)
            adaptive: Use adaptive breakpoint generation
            method: Linearization method ("sos2", "incremental", "logarithmic")

        Returns:
            Self for chaining

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

        self.nonlinear_terms.append(
            LXPiecewiseLinearTerm(var, func, num_segments, x_min, x_max, adaptive, method)
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
    "LXLinearExpression",
    "LXQuadraticTerm",
    "LXQuadraticExpression",
    "LXNonLinearExpression",
]
