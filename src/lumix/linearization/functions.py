"""
Pre-built piecewise-linear approximations for common nonlinear functions.

"""

import math
from typing import Callable

from ..core.variables import LXVariable
from .techniques.piecewise import LXPiecewiseLinearizer


class LXNonLinearFunctions:
    """
    Pre-built approximations for common nonlinear functions.

    All functions use piecewise-linear approximation with adaptive
    breakpoint generation for improved accuracy.

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
        var: LXVariable, linearizer: LXPiecewiseLinearizer, segments: int = 30
    ) -> LXVariable:
        """
        Exponential function: e^x

        Args:
            var: Input variable
            linearizer: Piecewise linearizer instance
            segments: Number of segments (default: 30 for good accuracy)

        Returns:
            Output variable representing exp(var)

        Example:
            # Population growth model
            population = LXNonLinearFunctions.exp(time, linearizer)

            # Compound interest
            future_value = principal * LXNonLinearFunctions.exp(rate * time, linearizer)
        """
        return linearizer.approximate_function(
            lambda x: math.exp(x), var, num_segments=segments, adaptive=True  # Exponential curves sharply
        )

    @staticmethod
    def log(
        var: LXVariable,
        linearizer: LXPiecewiseLinearizer,
        base: float = math.e,
        segments: int = 30,
    ) -> LXVariable:
        """
        Logarithm: log_base(x)

        Args:
            var: Input variable (must be positive)
            linearizer: Piecewise linearizer instance
            base: Logarithm base (default: e for natural log)
            segments: Number of segments

        Returns:
            Output variable representing log(var)

        Example:
            # Natural logarithm
            ln_demand = LXNonLinearFunctions.log(demand, linearizer)

            # Base-10 logarithm
            log10_quantity = LXNonLinearFunctions.log(quantity, linearizer, base=10)

            # Information entropy
            entropy = -probability * LXNonLinearFunctions.log(probability, linearizer, base=2)
        """

        def log_func(x: float) -> float:
            if x > 0:
                return math.log(x, base)
            else:
                return -1e10  # Very large negative value for x <= 0

        return linearizer.approximate_function(
            log_func, var, num_segments=segments, adaptive=True  # Log curves sharply near 0
        )

    @staticmethod
    def sqrt(
        var: LXVariable, linearizer: LXPiecewiseLinearizer, segments: int = 20
    ) -> LXVariable:
        """
        Square root: √x

        Args:
            var: Input variable (must be non-negative)
            linearizer: Piecewise linearizer instance
            segments: Number of segments

        Returns:
            Output variable representing sqrt(var)

        Example:
            # Standard deviation
            std_dev = LXNonLinearFunctions.sqrt(variance, linearizer)

            # Euclidean distance (after squaring)
            distance = LXNonLinearFunctions.sqrt(x_squared + y_squared, linearizer)

            # Flow velocity in pipes
            velocity = LXNonLinearFunctions.sqrt(pressure_drop, linearizer)
        """

        def sqrt_func(x: float) -> float:
            return math.sqrt(x) if x >= 0 else 0

        return linearizer.approximate_function(
            sqrt_func,
            var,
            num_segments=segments,
            adaptive=False,  # Square root is smooth, uniform breakpoints OK
        )

    @staticmethod
    def power(
        var: LXVariable,
        exponent: float,
        linearizer: LXPiecewiseLinearizer,
        segments: int = 25,
    ) -> LXVariable:
        """
        Power function: x^n

        Args:
            var: Input variable
            exponent: Power to raise variable to
            linearizer: Piecewise linearizer instance
            segments: Number of segments

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
            return x**exponent if x >= 0 else 0

        return linearizer.approximate_function(
            power_func,
            var,
            num_segments=segments,
            adaptive=abs(exponent) > 2,  # More adaptive for higher powers
        )

    @staticmethod
    def sigmoid(
        var: LXVariable, linearizer: LXPiecewiseLinearizer, segments: int = 40
    ) -> LXVariable:
        """
        Sigmoid function: 1 / (1 + e^(-x))

        Useful for modeling probabilities, S-curves, saturation effects.

        Args:
            var: Input variable
            linearizer: Piecewise linearizer instance
            segments: Number of segments (higher for sharper transition)

        Returns:
            Output variable representing sigmoid(var) ∈ [0, 1]

        Example:
            # Probability of success
            probability = LXNonLinearFunctions.sigmoid(score, linearizer)

            # Market saturation
            market_share = capacity * LXNonLinearFunctions.sigmoid(time, linearizer)

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
            sigmoid_func, var, num_segments=segments, adaptive=True  # Sigmoid curves sharply around x=0
        )

    @staticmethod
    def sin(
        var: LXVariable, linearizer: LXPiecewiseLinearizer, segments: int = 50
    ) -> LXVariable:
        """
        Sine function: sin(x)

        Useful for seasonal patterns, cyclical behavior.

        Args:
            var: Input variable (typically in radians)
            linearizer: Piecewise linearizer instance
            segments: Number of segments

        Returns:
            Output variable representing sin(var) ∈ [-1, 1]

        Example:
            # Seasonal demand pattern (annual cycle)
            import math
            day_angle = day_of_year * 2 * math.pi / 365
            seasonal_factor = LXNonLinearFunctions.sin(day_angle, linearizer)

            # Daily temperature variation
            hour_angle = hour * 2 * math.pi / 24
            temp_variation = LXNonLinearFunctions.sin(hour_angle, linearizer)
        """
        return linearizer.approximate_function(
            math.sin, var, num_segments=segments, adaptive=False  # Sine is smooth
        )

    @staticmethod
    def cos(
        var: LXVariable, linearizer: LXPiecewiseLinearizer, segments: int = 50
    ) -> LXVariable:
        """
        Cosine function: cos(x)

        Similar to sine but phase-shifted by π/2.

        Args:
            var: Input variable (typically in radians)
            linearizer: Piecewise linearizer instance
            segments: Number of segments

        Returns:
            Output variable representing cos(var) ∈ [-1, 1]

        Example:
            # Phase-shifted seasonal pattern
            import math
            day_angle = day_of_year * 2 * math.pi / 365
            seasonal_factor = LXNonLinearFunctions.cos(day_angle, linearizer)

            # Circular motion x-coordinate
            x_pos = radius * LXNonLinearFunctions.cos(angle, linearizer)
        """
        return linearizer.approximate_function(
            math.cos, var, num_segments=segments, adaptive=False  # Cosine is smooth
        )

    @staticmethod
    def tan(
        var: LXVariable, linearizer: LXPiecewiseLinearizer, segments: int = 40
    ) -> LXVariable:
        """
        Tangent function: tan(x)

        Warning: Has discontinuities at x = π/2 + nπ. Ensure domain avoids these.

        Args:
            var: Input variable (in radians, avoid discontinuities)
            linearizer: Piecewise linearizer instance
            segments: Number of segments

        Returns:
            Output variable representing tan(var)

        Example:
            # Slope calculation
            slope = LXNonLinearFunctions.tan(angle, linearizer)
        """

        def tan_func(x: float) -> float:
            try:
                return math.tan(x)
            except (ValueError, OverflowError):
                # Handle discontinuities
                return 1e10 if math.cos(x) > 0 else -1e10

        return linearizer.approximate_function(
            tan_func, var, num_segments=segments, adaptive=True  # Tan has sharp curves
        )

    @staticmethod
    def custom(
        var: LXVariable,
        func: Callable[[float], float],
        linearizer: LXPiecewiseLinearizer,
        segments: int = 30,
        adaptive: bool = True,
    ) -> LXVariable:
        """
        Custom user-defined function.

        Allows approximation of any arbitrary function.

        Args:
            var: Input variable
            func: Custom function to approximate
            linearizer: Piecewise linearizer instance
            segments: Number of segments
            adaptive: Use adaptive breakpoints

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
            func, var, num_segments=segments, adaptive=adaptive
        )


__all__ = ["LXNonLinearFunctions"]
