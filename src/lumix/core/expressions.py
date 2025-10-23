"""Expression classes for LumiX optimization models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, List, Literal, Optional, Tuple, TypeVar

from typing_extensions import Self

from .variables import LXVariable

TModel = TypeVar("TModel")


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

    def add_term(
            self, var: LXVariable[TModel, Any],
            coeff: float | Callable[[TModel], float] = 1.0,
            where: Callable[[TModel], bool] | None = None,
    ) -> Self:
        """
        Add term with coefficient (constant or function).

        Args:
            var: Variable Family to add
            coeff: Coefficient (constant or function)
            where: Optional filter function

        Returns:
            Self for chaining
        """
        coeff_func = coeff if callable(coeff) else lambda _: coeff
        if where is None:
            where = lambda _: True
        self.terms[var.name] = (var, coeff_func, where)
        return self

    def add_multi_term(
            self,
            var: LXVariable,
            coeff: Callable[..., float] = lambda *args: 1.0,
            where: Optional[Callable[..., bool]] = None,
    ) -> Self:
        """
        Add multi-indexed variable to expression.

        Args:
            var: Multi-indexed variable family
            coeff: Coefficient function receiving all dimension models
            where: Optional filter function

        Returns:
            Self for chaining

        Example::

            expr.add_multi_term(
                duty,
                coeff=lambda driver, date: driver.cost * date.multiplier,
                where=lambda driver, date: date.is_weekend
            )
        """
        self._multi_terms.append((var, coeff, where))
        return self

    def sum_over(
            self,
            var: LXVariable,
            where: Optional[Callable[..., bool]] = None,
    ) -> Self:
        """
        Syntactic sugar for summing over all dimensions of a variable.

        Args:
            var: Variable to sum over all its dimensions
            where: Optional filter function to selectively include terms

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
        return self.add_multi_term(var, where=where)

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
                # Combine coefficients when same variable appears in both expressions
                var1, coeff_func1, where1 = self.terms[var_name]
                var2, coeff_func2, where2 = term

                # Create combined coefficient function that sums both
                def combined_coeff(m, cf1=coeff_func1, cf2=coeff_func2):
                    return cf1(m) + cf2(m)

                # Combine where clauses with AND logic
                def combined_where(m, w1=where1, w2=where2):
                    return w1(m) and w2(m)

                self.terms[var_name] = (var1, combined_coeff, combined_where)
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
        for var_name in self.terms:
            var, old_coeff = self.terms[var_name]
            self.terms[var_name] = (var, lambda m, c=old_coeff, s=scalar: c(m) * s)
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
