"""Nonlinear term definitions for LumiX optimization models.

This module provides dataclasses for representing nonlinear terms in optimization models.
These terms are designed to be automatically linearized by the linearization engine.

The module includes:
    - Absolute value terms (|x|)
    - Min/max operations
    - Bilinear products (x * y)
    - Indicator (conditional) constraints
    - Piecewise-linear function approximations

Each term type includes metadata about how it should be linearized and integrated
into the optimization model.
"""

from dataclasses import dataclass
from typing import Callable, List, Literal, Optional

from ..core.expressions import LXLinearExpression
from ..core.variables import LXVariable


@dataclass
class LXAbsoluteTerm:
    """Absolute value term: |x|.

    Represents the absolute value of a variable, which can be linearized using
    auxiliary variables and linear constraints. The linearization introduces a
    new variable z and constraints: z >= x and z >= -x.

    Attributes:
        var: The variable to take the absolute value of.
        coefficient: Coefficient to multiply the absolute value by (default: 1.0).

    Example:
        Basic absolute value term::

            from lumix.nonlinear import LXAbsoluteTerm
            from lumix.core import LXVariable

            # Minimize absolute deviation from target
            actual = LXVariable[Product, float]("actual").from_data(products)
            abs_deviation = LXAbsoluteTerm(var=actual, coefficient=1.0)

        With coefficient::

            # Weighted absolute penalty
            penalty = LXAbsoluteTerm(var=deviation, coefficient=10.0)

    Note:
        The linearization creates auxiliary variables and adds constraints automatically
        during the model building phase. The auxiliary variable z will appear in the
        objective function or constraints where the absolute value is used.
    """

    var: LXVariable
    coefficient: float = 1.0


@dataclass
class LXMinMaxTerm:
    """Min/Max of multiple variables.

    Represents the minimum or maximum value among a set of variables. This is
    linearized by introducing an auxiliary variable z and adding constraints
    that ensure z equals the min or max of the input variables.

    Attributes:
        vars: List of variables to take min/max over.
        operation: Either "min" or "max" to specify the operation.
        coefficients: Coefficients for each variable in the min/max operation.

    Example:
        Minimum cost selection::

            from lumix.nonlinear import LXMinMaxTerm
            from lumix.core import LXVariable

            # Select minimum cost among alternatives
            cost_a = LXVariable[Option, float]("cost_a").from_data(options_a)
            cost_b = LXVariable[Option, float]("cost_b").from_data(options_b)
            cost_c = LXVariable[Option, float]("cost_c").from_data(options_c)

            min_cost = LXMinMaxTerm(
                vars=[cost_a, cost_b, cost_c],
                operation="min",
                coefficients=[1.0, 1.0, 1.0]
            )

        Maximum capacity::

            # Find maximum capacity among resources
            max_capacity = LXMinMaxTerm(
                vars=[cap_1, cap_2],
                operation="max",
                coefficients=[1.0, 1.0]
            )

    Note:
        Linearization for min: Introduces auxiliary variable z with constraints
        z <= x_i for all i. For max: z >= x_i for all i.

        The auxiliary variable z represents the result of the min/max operation
        and can be used in subsequent constraints or the objective function.
    """

    vars: List[LXVariable]
    operation: Literal["min", "max"]
    coefficients: List[float]


@dataclass
class LXBilinearTerm:
    """Product of two variables: x * y.

    Represents the product of two decision variables, which is nonlinear but can
    be linearized using different techniques depending on the variable types.

    The linearization method is automatically selected based on variable types:
        - Binary × Binary: AND logic (z <= x, z <= y, z >= x+y-1)
        - Binary × Continuous: Big-M method
        - Continuous × Continuous: McCormick envelopes (requires bounds)

    Attributes:
        var1: First variable in the product.
        var2: Second variable in the product.
        coefficient: Coefficient to multiply the product by (default: 1.0).

    Example:
        Facility activation times flow::

            from lumix.nonlinear import LXBilinearTerm
            from lumix.core import LXVariable

            # Flow is only active if facility is open
            is_open = LXVariable[Facility, int]("is_open").binary()
            flow_amount = LXVariable[Facility, float]("flow").continuous()

            # actual_flow = is_open * flow_amount
            actual_flow = LXBilinearTerm(
                var1=is_open,
                var2=flow_amount,
                coefficient=1.0
            )

        Rectangle area calculation::

            # Area = length * width (both continuous)
            length = LXVariable[Shape, float]("length").continuous().bounds(1, 10)
            width = LXVariable[Shape, float]("width").continuous().bounds(1, 10)

            area = LXBilinearTerm(var1=length, var2=width)

        Weighted product::

            # Price * quantity with discount factor
            revenue = LXBilinearTerm(
                var1=price,
                var2=quantity,
                coefficient=0.9  # 10% discount
            )

    Note:
        For Continuous × Continuous products, both variables MUST have finite
        bounds defined. McCormick envelopes require knowing the variable bounds
        to construct the linearization.

        The linearization introduces auxiliary variables and constraints that
        ensure the auxiliary variable equals the product of the two input variables.
    """

    var1: LXVariable
    var2: LXVariable
    coefficient: float = 1.0


@dataclass
class LXIndicatorTerm:
    """Conditional constraint: if binary_var == condition then constraint holds.

    Represents a constraint that is only enforced when a binary variable takes
    a specific value. This is also known as an indicator constraint or conditional
    constraint.

    The linearization uses the Big-M method:
        - If condition=True and sense='<=':  expr <= rhs + M*(1-b)
        - If condition=False and sense='<=': expr <= rhs + M*b
        - Similar formulations for '>=' and '=='

    Attributes:
        binary_var: The binary variable that controls the constraint activation.
        condition: Value of binary_var that activates the constraint (True or False).
        linear_expr: The linear expression on the left-hand side of the constraint.
        sense: Constraint sense - '<=', '>=', or '==' (default: '<=').
        rhs: Right-hand side value of the constraint (default: 0.0).

    Example:
        Minimum demand when warehouse is open::

            from lumix.nonlinear import LXIndicatorTerm
            from lumix.core import LXVariable, LXLinearExpression

            # If warehouse is open, then demand must be >= minimum
            is_open = LXVariable[Warehouse, int]("is_open").binary()
            demand = LXVariable[Warehouse, float]("demand").continuous()

            demand_expr = LXLinearExpression().add_term(demand, 1.0)

            min_demand_constraint = LXIndicatorTerm(
                binary_var=is_open,
                condition=True,  # When is_open == 1
                linear_expr=demand_expr,
                sense='>=',
                rhs=100.0  # minimum_demand
            )

        Maximum capacity when machine is active::

            # If machine is active, production <= capacity
            is_active = LXVariable[Machine, int]("is_active").binary()
            production = LXVariable[Machine, float]("production").continuous()

            prod_expr = LXLinearExpression().add_term(production, 1.0)

            capacity_constraint = LXIndicatorTerm(
                binary_var=is_active,
                condition=True,
                linear_expr=prod_expr,
                sense='<=',
                rhs=500.0  # capacity
            )

        Route selection constraint::

            # If route NOT selected, flow must be zero
            route_selected = LXVariable[Route, int]("selected").binary()
            flow = LXVariable[Route, float]("flow").continuous()

            flow_expr = LXLinearExpression().add_term(flow, 1.0)

            no_flow_constraint = LXIndicatorTerm(
                binary_var=route_selected,
                condition=False,  # When selected == 0
                linear_expr=flow_expr,
                sense='==',
                rhs=0.0
            )

    Note:
        The Big-M method requires selecting an appropriate value of M (big-M constant).
        The linearization engine typically computes M based on variable bounds.

        If M is too small, the constraint may not be properly enforced.
        If M is too large, it can cause numerical issues in the solver.
    """

    binary_var: LXVariable
    condition: bool  # True or False
    linear_expr: LXLinearExpression
    sense: Literal["<=", ">=", "=="] = "<="
    rhs: float = 0.0


@dataclass
class LXPiecewiseLinearTerm:
    """Piecewise-linear approximation for arbitrary nonlinear functions.

    Approximates any univariate nonlinear function using a piecewise-linear function.
    The domain is divided into segments, and the function is approximated by linear
    interpolation between breakpoints.

    Three formulation methods are supported:
        - SOS2: Special Ordered Set type 2 (best when solver supports SOS2)
        - Incremental: Binary selection variables for each segment
        - Logarithmic: Gray code encoding (best for many segments, uses fewer binaries)

    Attributes:
        var: The input variable to the nonlinear function.
        func: The nonlinear function to approximate, taking a float and returning a float.
        num_segments: Number of linear segments to use (default: 20).
        x_min: Minimum value of the input domain (default: use variable lower bound).
        x_max: Maximum value of the input domain (default: use variable upper bound).
        adaptive: If True, use adaptive segmentation based on function curvature (default: True).
        method: Formulation method - "sos2", "incremental", or "logarithmic" (default: "sos2").

    Example:
        Exponential growth function::

            import math
            from lumix.nonlinear import LXPiecewiseLinearTerm
            from lumix.core import LXVariable

            # Approximate exp(t) for t in [0, 5]
            time = LXVariable[Task, float]("time").continuous().bounds(0, 5)

            exp_term = LXPiecewiseLinearTerm(
                var=time,
                func=lambda t: math.exp(t),
                num_segments=30,
                x_min=0.0,
                x_max=5.0,
                adaptive=True,
                method="sos2"
            )

        Custom discount curve::

            # Tiered discount: 100% up to 100 units, 90% up to 1000, then 80%
            quantity = LXVariable[Order, float]("qty").continuous().bounds(0, 2000)

            def discount_func(q):
                if q < 100:
                    return 1.0
                elif q < 1000:
                    return 0.9
                else:
                    return 0.8

            discount = LXPiecewiseLinearTerm(
                var=quantity,
                func=discount_func,
                num_segments=50,
                adaptive=False,  # Uniform segments for step function
                method="incremental"
            )

        Logarithmic cost function::

            # Cost grows logarithmically with size
            size = LXVariable[Component, float]("size").continuous().bounds(1, 1000)

            log_cost = LXPiecewiseLinearTerm(
                var=size,
                func=lambda s: 10 * math.log(s),
                num_segments=25,
                method="logarithmic"  # Efficient for many segments
            )

        Sigmoid activation::

            # Approximate sigmoid function
            def sigmoid(x):
                return 1.0 / (1.0 + math.exp(-x))

            activation = LXVariable[Node, float]("activation").continuous()

            sigmoid_approx = LXPiecewiseLinearTerm(
                var=activation,
                func=sigmoid,
                num_segments=40,
                x_min=-6.0,
                x_max=6.0,
                adaptive=True
            )

    Note:
        **Adaptive Segmentation**: When adaptive=True, the algorithm places more
        breakpoints in regions where the function has higher curvature, improving
        approximation accuracy with fewer segments.

        **Method Selection**:
            - Use "sos2" if your solver has native SOS2 support (most efficient)
            - Use "incremental" for better solver performance with few segments
            - Use "logarithmic" when you need many segments (uses O(log n) binaries)

        **Domain Bounds**: If x_min and x_max are not specified, they default to
        the variable's lower and upper bounds. The variable MUST have finite bounds
        for piecewise-linear approximation.

        **Approximation Error**: More segments generally provide better approximation
        but increase model complexity. The num_segments parameter allows you to
        trade off accuracy for solving speed.
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
