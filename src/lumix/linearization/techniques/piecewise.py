"""
Piecewise-linear approximation for arbitrary nonlinear functions.

Implements three formulation methods, all exact for the piecewise-linear
function through the breakpoints:
1. SOS2: convex-combination weights with adjacency enforced by segment binaries
2. Incremental: Binary selection variables
3. Logarithmic: Gray code encoding with ceil(log2(segments)) binaries
"""

import math
import warnings
from typing import Any, Callable, List, Literal, Optional, Sequence, Tuple

import numpy as np

from ...core.constraints import LXConstraint
from ...core.expressions import LXLinearExpression
from ...core.variables import LXVariable
from ..config import LXLinearizerConfig


class LXPiecewiseLinearizer:
    """
    Piecewise-linear approximation for arbitrary nonlinear functions.

    Supports multiple formulation methods and adaptive breakpoint generation
    for improved approximation accuracy.
    """

    def __init__(self, config: LXLinearizerConfig):
        """
        Initialize piecewise linearizer.

        Args:
            config: Linearization configuration
        """
        self.config = config
        self.auxiliary_vars: List[LXVariable] = []
        self.auxiliary_constraints: List[LXConstraint] = []
        self._aux_counter = 0

    def approximate_function(
        self,
        func: Callable[[float], float],
        var: LXVariable,
        num_segments: Optional[int] = None,
        x_min: Optional[float] = None,
        x_max: Optional[float] = None,
        method: Optional[Literal["sos2", "incremental", "logarithmic"]] = None,
        adaptive: Optional[bool] = None,
        *,
        breakpoints: Optional[Sequence[float]] = None,
    ) -> LXVariable:
        """
        Create piecewise-linear approximation of arbitrary function.

        The domain (``[x_min, x_max]``, or the first and last breakpoint)
        constrains ``var``; a ``UserWarning`` is issued when it is narrower than
        the variable's bounds.

        Args:
            func: Function to approximate (e.g., lambda x: math.exp(x))
            var: Input variable
            num_segments: Number of linear segments (default: from config)
            x_min: Minimum domain value (default: var.lower_bound)
            x_max: Maximum domain value (default: var.upper_bound)
            method: Linearization method (default: from config)
            adaptive: Use adaptive breakpoints (default: from config)
            breakpoints: Explicit, strictly increasing breakpoints; replaces
                ``num_segments``, ``adaptive``, ``x_min`` and ``x_max``

        Returns:
            Output variable representing f(var)

        Raises:
            ValueError: If domain bounds cannot be determined, or breakpoints
                are invalid or combined with x_min/x_max

        Example::

            # Exponential growth
            exp_y = linearizer.approximate_function(
                lambda x: math.exp(x),
                input_var,
                num_segments=50
            )
        """
        # Use config defaults if not specified
        method = method or self.config.pwl_method

        if breakpoints is not None:
            if x_min is not None or x_max is not None:
                raise ValueError(
                    f"Give either breakpoints or x_min/x_max for {var.name}, not both"
                )
            breakpoints = [float(b) for b in breakpoints]
            if len(breakpoints) < 2 or any(
                b <= a for a, b in zip(breakpoints, breakpoints[1:])
            ):
                raise ValueError(
                    f"breakpoints for {var.name} must contain at least two strictly "
                    f"increasing values, got {breakpoints}"
                )
            x_min, x_max = breakpoints[0], breakpoints[-1]
        else:
            num_segments = num_segments or self.config.pwl_num_segments
            adaptive = adaptive if adaptive is not None else self.config.adaptive_breakpoints

            # Determine domain (0 is a valid bound, so test for None)
            x_min = var.lower_bound if x_min is None else x_min
            x_max = var.upper_bound if x_max is None else x_max

            if x_min is None or x_max is None:
                raise ValueError(
                    f"Cannot determine domain for piecewise-linear approximation of {var.name}. "
                    f"Detected: [{x_min}, {x_max}]. "
                    f"Please specify x_min/x_max or set bounds on the variable."
                )

            # Generate breakpoints
            if adaptive:
                breakpoints = self._generate_adaptive_breakpoints(
                    func, x_min, x_max, num_segments
                )
            else:
                breakpoints = list(np.linspace(x_min, x_max, num_segments + 1))

        lower, upper = var.lower_bound, var.upper_bound
        if lower is None or lower < x_min or upper is None or upper > x_max:
            warnings.warn(
                f"The piecewise-linear term restricts {var.name} to [{x_min}, {x_max}], "
                f"narrower than its bounds [{lower}, {upper}]",
                UserWarning,
                stacklevel=2,
            )

        # Evaluate function at breakpoints
        try:
            values = [func(bp) for bp in breakpoints]
        except Exception as e:
            raise ValueError(
                f"Failed to evaluate function at breakpoints: {e}. "
                f"Ensure function is defined over domain [{x_min}, {x_max}]."
            )

        # One tag per term keeps auxiliary names unique when a variable has
        # several piecewise terms.
        tag = f"{var.name}_{self._aux_counter}"
        self._aux_counter += 1

        # Apply appropriate formulation
        if method == "sos2":
            return self._sos2_formulation(var, breakpoints, values, tag)
        elif method == "incremental":
            return self._incremental_formulation(var, breakpoints, values, tag)
        elif method == "logarithmic":
            return self._logarithmic_formulation(var, breakpoints, values, tag)
        else:
            raise ValueError(f"Unknown piecewise-linear method: {method}")

    def _generate_adaptive_breakpoints(
        self, func: Callable[[float], float], x_min: float, x_max: float, num_points: int
    ) -> List[float]:
        """
        Generate adaptive breakpoints based on function curvature.

        Uses second derivative as a measure of curvature to place
        more breakpoints where the function changes rapidly.

        Args:
            func: Function to approximate
            x_min: Minimum domain value
            x_max: Maximum domain value
            num_points: Number of breakpoints to generate

        Returns:
            List of breakpoints (including endpoints)
        """
        # Sample function at many points
        n_sample = num_points * 10
        x_sample = np.linspace(x_min, x_max, n_sample)

        try:
            # Compute approximate second derivative
            y_sample = np.array([func(x) for x in x_sample])
            second_deriv = np.abs(np.diff(np.diff(y_sample)))

            # Normalize to probability distribution
            # Add small constant to avoid division by zero
            weights = second_deriv / (np.sum(second_deriv) + 1e-10)
            weights = np.concatenate([[0], weights, [0]])  # Add endpoints with zero weight

            # Ensure weights sum to 1
            weights = weights / np.sum(weights)

            # Sample breakpoints according to curvature
            indices = np.random.choice(
                len(x_sample), size=num_points - 2, replace=False, p=weights
            )

            # Include endpoints and sort
            breakpoints = [x_min] + sorted([x_sample[i] for i in indices]) + [x_max]
            return breakpoints

        except Exception:
            # Fallback to uniform if adaptive fails
            return list(np.linspace(x_min, x_max, num_points))

    def _scalar(self, name: str, kind: str, lower: Optional[float] = None,
                upper: Optional[float] = None) -> LXVariable:
        """Create and register a single-instance auxiliary variable."""
        var = LXVariable[str, float](name)
        var = var.binary() if kind == "binary" else var.continuous().bounds(lower=lower, upper=upper)
        var = var.indexed_by(lambda x: x).from_data([name])
        self.auxiliary_vars.append(var)
        return var

    def _add(self, name: str, expr: LXLinearExpression, sense: str, rhs: float) -> None:
        constraint = LXConstraint(name).expression(expr)
        constraint = {"<=": constraint.le, ">=": constraint.ge, "==": constraint.eq}[sense]()
        self.auxiliary_constraints.append(constraint.rhs(rhs))

    def _lambda_model(
        self, var: LXVariable, breakpoints: List[float], values: List[float], tag: str
    ) -> Tuple[List[LXVariable], LXVariable]:
        """
        Convex-combination core shared by the SOS2 and logarithmic formulations.

        Creates λ[i] ∈ [0, 1] per breakpoint and the output y with
        sum(λ) = 1, x = sum(λ[i] * breakpoint[i]) and y = sum(λ[i] * value[i]).
        On its own this is only the convex hull of the function; the caller
        adds the constraints that keep at most two adjacent λ positive.
        """
        output_name = f"pwl_out_{tag}"
        lambdas = [
            self._scalar(f"lambda_{tag}_{i}", "continuous", 0, 1)
            for i in range(len(breakpoints))
        ]
        output = self._scalar(output_name, "continuous", min(values), max(values))

        convex_expr = LXLinearExpression()
        for lv in lambdas:
            convex_expr.add_term(lv, 1.0)
        self._add(f"pwl_convex_{output_name}", convex_expr, "==", 1.0)

        x_expr = LXLinearExpression().add_term(var, 1.0)
        for i, lv in enumerate(lambdas):
            x_expr.add_term(lv, -breakpoints[i])
        self._add(f"pwl_x_{output_name}", x_expr, "==", 0)

        y_expr = LXLinearExpression().add_term(output, 1.0)
        for i, lv in enumerate(lambdas):
            y_expr.add_term(lv, -values[i])
        self._add(f"pwl_y_{output_name}", y_expr, "==", 0)
        return lambdas, output

    def _sos2_formulation(
        self, var: LXVariable, breakpoints: List[float], values: List[float], tag: str
    ) -> LXVariable:
        """
        SOS2 (Special Ordered Set type 2) formulation.

        Creates λ[i] per breakpoint (see :meth:`_lambda_model`) and enforces the
        SOS2 condition (at most two adjacent λ positive) with one binary z[s]
        per segment: sum(z) = 1, λ[0] <= z[0], λ[i] <= z[i-1] + z[i],
        λ[n] <= z[n-1]. No solver adapter passes SOS2 sets to the solver yet,
        and without the condition the model is only a convex relaxation.

        Args:
            var: Input variable
            breakpoints: Breakpoint x-coordinates
            values: Function values at breakpoints
            tag: Unique name fragment for the auxiliary variables

        Returns:
            Output variable representing f(var)
        """
        lambdas, output = self._lambda_model(var, breakpoints, values, tag)
        segments = len(breakpoints) - 1
        if segments == 1:
            return output

        z = [self._scalar(f"sos2_{tag}_{s}", "binary") for s in range(segments)]
        one_expr = LXLinearExpression()
        for zv in z:
            one_expr.add_term(zv, 1.0)
        self._add(f"sos2_one_{tag}", one_expr, "==", 1)
        for i, lv in enumerate(lambdas):
            expr = LXLinearExpression().add_term(lv, 1.0)
            for s in (i - 1, i):
                if 0 <= s < segments:
                    expr.add_term(z[s], -1.0)
            self._add(f"sos2_adj_{tag}_{i}", expr, "<=", 0)
        return output

    def _incremental_formulation(
        self, var: LXVariable, breakpoints: List[float], values: List[float], tag: str
    ) -> LXVariable:
        """
        Incremental (multiple choice) formulation.

        Uses binary variables to select which segment is active.
        More variables but can be faster for some solvers.

        Args:
            var: Input variable
            breakpoints: Breakpoint x-coordinates
            values: Function values at breakpoints
            tag: Unique name fragment for the auxiliary variables

        Returns:
            Output variable representing f(var)
        """
        n = len(breakpoints) - 1  # Number of segments

        # Binary variables for segment selection
        segment_vars = [self._scalar(f"segment_{tag}_{i}", "binary") for i in range(n)]
        # Delta variables (how far into each segment, normalized to [0,1])
        delta_vars = [self._scalar(f"delta_{tag}_{i}", "continuous", 0, 1) for i in range(n)]
        output_name = f"pwl_out_{tag}"
        output = self._scalar(output_name, "continuous", min(values), max(values))

        # Constraint: exactly one segment active
        segment_expr = LXLinearExpression()
        for sv in segment_vars:
            segment_expr.add_term(sv, 1.0)
        self._add(f"one_segment_{output_name}", segment_expr, "==", 1)

        # Constraint: delta only positive if segment selected
        for i, (sv, dv) in enumerate(zip(segment_vars, delta_vars)):
            self._add(
                f"delta_active_{output_name}_{i}",
                LXLinearExpression().add_term(dv, 1.0).add_term(sv, -1.0),
                "<=",
                0,
            )

        # Constraint: x = sum(bp[i] * s[i] + delta[i] * width[i])
        x_expr = LXLinearExpression().add_term(var, 1.0)
        for i in range(n):
            width = breakpoints[i + 1] - breakpoints[i]
            x_expr.add_term(segment_vars[i], -breakpoints[i])
            x_expr.add_term(delta_vars[i], -width)
        self._add(f"pwl_x_{output_name}", x_expr, "==", 0)

        # Constraint: y = sum(value[i] * s[i] + delta[i] * (val[i+1] - val[i]))
        y_expr = LXLinearExpression().add_term(output, 1.0)
        for i in range(n):
            slope = values[i + 1] - values[i]
            y_expr.add_term(segment_vars[i], -values[i])
            y_expr.add_term(delta_vars[i], -slope)
        self._add(f"pwl_y_{output_name}", y_expr, "==", 0)

        return output

    def _logarithmic_formulation(
        self, var: LXVariable, breakpoints: List[float], values: List[float], tag: str
    ) -> LXVariable:
        """
        Logarithmic formulation using Gray code (Vielma and Nemhauser, 2011).

        Uses ceil(log2(segments)) binaries y[l] instead of one per segment.
        Segment s gets the Gray code g(s) = s XOR (s >> 1); for every bit l,
        the λ of breakpoints whose adjacent segments all have bit l set sum to
        at most y[l], and those whose adjacent segments all have it clear sum
        to at most 1 - y[l]. The segment count is padded to a power of two
        with zero-width segments at the last breakpoint.

        Args:
            var: Input variable
            breakpoints: Breakpoint x-coordinates
            values: Function values at breakpoints
            tag: Unique name fragment for the auxiliary variables

        Returns:
            Output variable representing f(var)
        """
        segments = len(breakpoints) - 1
        bits = math.ceil(math.log2(segments)) if segments > 1 else 0
        padded = 2 ** bits
        breakpoints = list(breakpoints) + [breakpoints[-1]] * (padded - segments)
        values = list(values) + [values[-1]] * (padded - segments)
        lambdas, output = self._lambda_model(var, breakpoints, values, tag)

        codes = [s ^ (s >> 1) for s in range(padded)]
        for l in range(bits):
            y = self._scalar(f"gray_{tag}_{l}", "binary")
            ones = LXLinearExpression().add_term(y, -1.0)
            zeros = LXLinearExpression().add_term(y, 1.0)
            for j, lv in enumerate(lambdas):
                adjacent = [codes[s] >> l & 1 for s in (j - 1, j) if 0 <= s < padded]
                if all(adjacent):
                    ones.add_term(lv, 1.0)
                elif not any(adjacent):
                    zeros.add_term(lv, 1.0)
            self._add(f"gray_one_{tag}_{l}", ones, "<=", 0)
            self._add(f"gray_zero_{tag}_{l}", zeros, "<=", 1)
        return output


__all__ = ["LXPiecewiseLinearizer"]
