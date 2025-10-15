"""Nonlinear term definitions for LumiX optimization models."""

from dataclasses import dataclass
from typing import Callable, List, Literal, Optional

from ..core.expressions import LXLinearExpression
from ..core.variables import LXVariable


@dataclass
class LXAbsoluteTerm:
    """
    Absolute value term: |x|

    Linearized as:
        z >= x
        z >= -x
        minimize z (in objective) or use Big-M constraints

    Example:
        abs_deviation = LXAbsoluteTerm(actual - target)
    """

    var: LXVariable
    coefficient: float = 1.0


@dataclass
class LXMinMaxTerm:
    """
    Min/Max of multiple variables.

    Linearization:
    - Min: z <= x_i for all i, maximize z
    - Max: z >= x_i for all i, minimize z

    Example:
        min_cost = LXMinMaxTerm([cost_a, cost_b, cost_c], "min")
        max_capacity = LXMinMaxTerm([cap_1, cap_2], "max")
    """

    vars: List[LXVariable]
    operation: Literal["min", "max"]
    coefficients: List[float]


@dataclass
class LXBilinearTerm:
    """
    Product of two variables: x * y

    Automatically linearized based on variable types:
    - Binary × Binary: AND logic (z <= x, z <= y, z >= x+y-1)
    - Binary × Continuous: Big-M method
    - Continuous × Continuous: McCormick envelopes (requires bounds)

    Example:
        # Facility open × flow
        actual_flow = LXBilinearTerm(is_open, flow_amount)

        # Rectangle area
        area = LXBilinearTerm(length, width)
    """

    var1: LXVariable
    var2: LXVariable
    coefficient: float = 1.0


@dataclass
class LXIndicatorTerm:
    """
    Conditional constraint: if binary_var == condition then constraint holds

    Linearized using Big-M method:
    - If condition=True and sense='<=':  expr <= rhs + M*(1-b)
    - If condition=False and sense='<=': expr <= rhs + M*b
    - Similar for '>=' and '=='

    Example:
        # If warehouse is open, then demand >= minimum
        LXIndicatorTerm(
            binary_var=is_open,
            condition=True,
            linear_expr=demand_expr,
            sense='>=',
            rhs=minimum_demand
        )
    """

    binary_var: LXVariable
    condition: bool  # True or False
    linear_expr: LXLinearExpression
    sense: Literal["<=", ">=", "=="] = "<="
    rhs: float = 0.0


@dataclass
class LXPiecewiseLinearTerm:
    """
    Piecewise-linear approximation for arbitrary nonlinear functions.

    Supports three formulation methods:
    - SOS2: Special Ordered Set type 2 (best when solver supports)
    - Incremental: Binary selection variables
    - Logarithmic: Gray code encoding (best for many segments)

    Example:
        # Exponential growth
        exp_term = LXPiecewiseLinearTerm(
            var=time,
            func=lambda t: math.exp(t),
            num_segments=30,
            adaptive=True
        )

        # Custom discount curve
        discount = LXPiecewiseLinearTerm(
            var=quantity,
            func=lambda q: 1.0 if q < 100 else 0.9 if q < 1000 else 0.8,
            num_segments=50
        )
    """

    var: LXVariable
    func: Callable[[float], float]
    num_segments: int = 20
    x_min: Optional[float] = None
    x_max: Optional[float] = None
    adaptive: bool = True
    method: Literal["sos2", "incremental", "logarithmic"] = "sos2"


__all__ = [
    "LXAbsoluteTerm",
    "LXMinMaxTerm",
    "LXBilinearTerm",
    "LXIndicatorTerm",
    "LXPiecewiseLinearTerm",
]
