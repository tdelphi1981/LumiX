"""
Pre-built piecewise-linear approximations for common nonlinear functions.

"""

import math
from typing import Callable, Optional

from ..core.variables import LXVariable
from .techniques.piecewise import LXPiecewiseLinearizer


class LXNonLinearFunctions:
    """
    Pre-built approximations for common nonlinear functions.

    All functions use piecewise-linear approximation; the number of segments and
    adaptive breakpoints come from the linearizer's config unless ``segments`` is
    given.

    .. versionchanged:: 0.3.2
       Segments and adaptive breakpoints follow the linearizer's config (they were
       fixed per function). ``log``, ``sqrt`` and ``tan`` raise ``ValueError`` on a
       domain where they are undefined instead of using sentinel values.

    Example:
        # Create linearizer
        linearizer = LXPiecewiseLinearizer(config)

        # Approximate exponential growth
        growth = LXNonLinearFunctions.exp(time, linearizer)

        # Logarithmic decay
        decay = LXNonLinearFunctions.log(age, linearizer, base=10)
    """

    @staticmethod
    def exp(
        var: LXVariable, linearizer: LXPiecewiseLinearizer, segments: Optional[int] = None
    ) -> LXVariable:
        """
        Exponential function: e^x

        Args:
            var: Input variable
            linearizer: Piecewise linearizer instance
            segments: Number of segments (default: the config's ``pwl_num_segments``)

        Returns:
            Output variable representing exp(var)

        Example:
            # Population growth model
            population = LXNonLinearFunctions.exp(time, linearizer)
        """
        return linearizer.approximate_function(
            lambda x: math.exp(x), var, num_segments=segments, adaptive=None,
        )

    @staticmethod
    def log(
        var: LXVariable,
        linearizer: LXPiecewiseLinearizer,
        base: float = math.e,
        segments: Optional[int] = None,
    ) -> LXVariable:
        """
        Logarithm: log_base(x)

        Args:
            var: Input variable (must be positive)
            linearizer: Piecewise linearizer instance
            base: Logarithm base (default: e for natural log)
            segments: Number of segments (default: the config's ``pwl_num_segments``)

        Returns:
            Output variable representing log(var)

        Example:
            # Natural logarithm
            ln_demand = LXNonLinearFunctions.log(demand, linearizer)

            # Base-10 logarithm
            log10_quantity = LXNonLinearFunctions.log(quantity, linearizer, base=10)
        """

        def log_func(x: float) -> float:
            if x <= 0:
                raise ValueError(f"log is undefined at x = {x}; restrict the variable to x > 0")
            return math.log(x, base)

        return linearizer.approximate_function(
            log_func, var, num_segments=segments, adaptive=None,
        )

    @staticmethod
    def sqrt(
        var: LXVariable, linearizer: LXPiecewiseLinearizer, segments: Optional[int] = None
    ) -> LXVariable:
        """
        Square root: √x

        Args:
            var: Input variable (must be non-negative)
            linearizer: Piecewise linearizer instance
            segments: Number of segments (default: the config's ``pwl_num_segments``)

        Returns:
            Output variable representing sqrt(var)

        Example:
            # Standard deviation
            std_dev = LXNonLinearFunctions.sqrt(variance, linearizer)

            # Flow velocity in pipes
            velocity = LXNonLinearFunctions.sqrt(pressure_drop, linearizer)
        """

        def sqrt_func(x: float) -> float:
            if x < 0:
                raise ValueError(f"sqrt is undefined at x = {x}; restrict the variable to x >= 0")
            return math.sqrt(x)

        return linearizer.approximate_function(
            sqrt_func,
            var,
            num_segments=segments,
            adaptive=None,
        )

    @staticmethod
    def power(
        var: LXVariable,
        exponent: float,
        linearizer: LXPiecewiseLinearizer,
        segments: Optional[int] = None,
    ) -> LXVariable:
        """
        Power function: x^n

        Args:
            var: Input variable
            exponent: Power to raise variable to
            linearizer: Piecewise linearizer instance
            segments: Number of segments (default: the config's ``pwl_num_segments``)

        Returns:
            Output variable representing var^exponent

        Example:
            # Cubic cost function
            cubic_cost = LXNonLinearFunctions.power(production, 3, linearizer)

            # Quadratic relationship
            area = LXNonLinearFunctions.power(radius, 2, linearizer)

            # Fractional power (e.g., Cobb-Douglas)
            output = LXNonLinearFunctions.power(capital, 0.3, linearizer)
        """

        def power_func(x: float) -> float:
            if x < 0 and not float(exponent).is_integer():
                raise ValueError(
                    f"x**{exponent} is not real for x = {x} < 0; restrict the variable "
                    "to x >= 0")
            return x ** exponent

        return linearizer.approximate_function(
            power_func,
            var,
            num_segments=segments,
            adaptive=None,
        )

    @staticmethod
    def sigmoid(
        var: LXVariable, linearizer: LXPiecewiseLinearizer, segments: Optional[int] = None
    ) -> LXVariable:
        """
        Sigmoid function: 1 / (1 + e^(-x))

        Useful for modeling probabilities, S-curves, saturation effects.

        Args:
            var: Input variable
            linearizer: Piecewise linearizer instance
            segments: Number of segments (default: the config's ``pwl_num_segments``)

        Returns:
            Output variable representing sigmoid(var) ∈ [0, 1]

        Example:
            # Probability of success
            probability = LXNonLinearFunctions.sigmoid(score, linearizer)

            # Learning curve
            efficiency = LXNonLinearFunctions.sigmoid(experience, linearizer)
        """

        def sigmoid_func(x: float) -> float:
            try:
                return 1.0 / (1.0 + math.exp(-x))
            except OverflowError:
                # Handle very negative x (exp overflow)
                return 0.0 if x < 0 else 1.0

        return linearizer.approximate_function(
            sigmoid_func, var, num_segments=segments, adaptive=None,
        )

    @staticmethod
    def sin(
        var: LXVariable, linearizer: LXPiecewiseLinearizer, segments: Optional[int] = None
    ) -> LXVariable:
        """
        Sine function: sin(x)

        Useful for seasonal patterns, cyclical behavior.

        Args:
            var: Input variable (typically in radians)
            linearizer: Piecewise linearizer instance
            segments: Number of segments (default: the config's ``pwl_num_segments``)

        Returns:
            Output variable representing sin(var) ∈ [-1, 1]

        Example:
            # Seasonal factor; day_angle is a variable holding the angle in radians
            # (constrain it to day_of_year * 2 * pi / 365 with a linear row)
            seasonal_factor = LXNonLinearFunctions.sin(day_angle, linearizer)
        """
        return linearizer.approximate_function(
            math.sin, var, num_segments=segments, adaptive=None,
        )

    @staticmethod
    def cos(
        var: LXVariable, linearizer: LXPiecewiseLinearizer, segments: Optional[int] = None
    ) -> LXVariable:
        """
        Cosine function: cos(x)

        Similar to sine but phase-shifted by π/2.

        Args:
            var: Input variable (typically in radians)
            linearizer: Piecewise linearizer instance
            segments: Number of segments (default: the config's ``pwl_num_segments``)

        Returns:
            Output variable representing cos(var) ∈ [-1, 1]

        Example:
            # Phase-shifted seasonal factor; day_angle is a variable in radians
            seasonal_factor = LXNonLinearFunctions.cos(day_angle, linearizer)
        """
        return linearizer.approximate_function(
            math.cos, var, num_segments=segments, adaptive=None,
        )

    @staticmethod
    def tan(
        var: LXVariable, linearizer: LXPiecewiseLinearizer, segments: Optional[int] = None
    ) -> LXVariable:
        """
        Tangent function: tan(x)

        Warning: Has discontinuities at x = π/2 + nπ. Ensure domain avoids these.

        Args:
            var: Input variable (in radians, avoid discontinuities)
            linearizer: Piecewise linearizer instance
            segments: Number of segments (default: the config's ``pwl_num_segments``)

        Returns:
            Output variable representing tan(var)

        Example:
            # Slope calculation
            slope = LXNonLinearFunctions.tan(angle, linearizer)
        """

        lo, hi = var.lower_bound, var.upper_bound
        if lo is not None and hi is not None:
            k_lo = math.ceil((float(lo) - math.pi / 2) / math.pi)
            if math.pi / 2 + k_lo * math.pi <= float(hi):
                raise ValueError(
                    f"tan has a pole at {math.pi / 2 + k_lo * math.pi:.6g} inside "
                    f"[{lo}, {hi}]; restrict the variable to avoid pi/2 + k*pi")

        return linearizer.approximate_function(
            math.tan, var, num_segments=segments, adaptive=None,
        )

    @staticmethod
    def custom(
        var: LXVariable,
        func: Callable[[float], float],
        linearizer: LXPiecewiseLinearizer,
        segments: Optional[int] = None,
        adaptive: Optional[bool] = None,
    ) -> LXVariable:
        """
        Custom user-defined function.

        Allows approximation of any arbitrary function.

        Args:
            var: Input variable
            func: Custom function to approximate
            linearizer: Piecewise linearizer instance
            segments: Number of segments (default: the config's ``pwl_num_segments``)
            adaptive: Use adaptive breakpoints (default: the config's ``adaptive_breakpoints``)

        Returns:
            Output variable representing func(var)

        Example::

            # Custom discount curve
            def discount_curve(q):
                if q < 100:
                    return 1.0  # No discount
                elif q < 1000:
                    return 0.9  # 10% discount
                else:
                    return 0.8  # 20% discount

            discount = LXNonLinearFunctions.custom(
                quantity, discount_curve, linearizer, segments=50
            )

            # Piecewise quadratic
            def piecewise_quad(x):
                return x**2 if x < 10 else 100 + 20*(x-10)

            cost = LXNonLinearFunctions.custom(
                production, piecewise_quad, linearizer
            )
        """
        return linearizer.approximate_function(
            func, var, num_segments=segments, adaptive=adaptive,
        )


__all__ = ["LXNonLinearFunctions"]
