"""
Piecewise-linear approximation for arbitrary nonlinear functions.

Implements three formulation methods:
1. SOS2: Special Ordered Set type 2 (most efficient when supported)
2. Incremental: Binary selection variables
3. Logarithmic: Gray code encoding (best for many segments)

Reference: sample_impl/opt_wrapper_design.py:335-578
"""

from typing import Any, Callable, List, Literal, Optional

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
    ) -> LXVariable:
        """
        Create piecewise-linear approximation of arbitrary function.

        Reference: sample_impl/opt_wrapper_design.py:346-397

        Args:
            func: Function to approximate (e.g., lambda x: math.exp(x))
            var: Input variable
            num_segments: Number of linear segments (default: from config)
            x_min: Minimum domain value (default: var.lower_bound)
            x_max: Maximum domain value (default: var.upper_bound)
            method: Linearization method (default: from config)
            adaptive: Use adaptive breakpoints (default: from config)

        Returns:
            Output variable representing f(var)

        Raises:
            ValueError: If domain bounds cannot be determined

        Example::

            # Exponential growth
            exp_y = linearizer.approximate_function(
                lambda x: math.exp(x),
                input_var,
                num_segments=50
            )
        """
        # Use config defaults if not specified
        num_segments = num_segments or self.config.pwl_num_segments
        method = method or self.config.pwl_method
        adaptive = adaptive if adaptive is not None else self.config.adaptive_breakpoints

        # Determine domain
        x_min = x_min or var.lower_bound
        x_max = x_max or var.upper_bound

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

        # Evaluate function at breakpoints
        try:
            values = [func(bp) for bp in breakpoints]
        except Exception as e:
            raise ValueError(
                f"Failed to evaluate function at breakpoints: {e}. "
                f"Ensure function is defined over domain [{x_min}, {x_max}]."
            )

        # Apply appropriate formulation
        if method == "sos2":
            return self._sos2_formulation(var, breakpoints, values)
        elif method == "incremental":
            return self._incremental_formulation(var, breakpoints, values)
        elif method == "logarithmic":
            return self._logarithmic_formulation(var, breakpoints, values)
        else:
            raise ValueError(f"Unknown piecewise-linear method: {method}")

    def _generate_adaptive_breakpoints(
        self, func: Callable[[float], float], x_min: float, x_max: float, num_points: int
    ) -> List[float]:
        """
        Generate adaptive breakpoints based on function curvature.

        Reference: sample_impl/opt_wrapper_design.py:399-434

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

    def _sos2_formulation(
        self, var: LXVariable, breakpoints: List[float], values: List[float]
    ) -> LXVariable:
        """
        SOS2 (Special Ordered Set type 2) formulation.

        Reference: sample_impl/opt_wrapper_design.py:436-507

        Most efficient when solver has native SOS2 support.

        Creates:
        - Lambda variables λ[i] for each breakpoint
        - Constraints: sum(λ) = 1
        - x = sum(λ[i] * breakpoint[i])
        - y = sum(λ[i] * value[i])
        - SOS2: at most 2 adjacent λ can be positive

        Args:
            var: Input variable
            breakpoints: Breakpoint x-coordinates
            values: Function values at breakpoints

        Returns:
            Output variable representing f(var)
        """
        n = len(breakpoints)

        # Lambda variables (convex combination weights)
        lambda_vars = []
        for i in range(n):
            lambda_name = f"lambda_{var.name}_{i}"
            lambda_var = (
                LXVariable[str, float](lambda_name)
                .continuous()
                .bounds(lower=0, upper=1)
                .indexed_by(lambda x: x)
                .from_data([lambda_name])  # Use variable name as unique index
            )
            lambda_vars.append(lambda_var)
        self.auxiliary_vars.extend(lambda_vars)

        # Output variable
        output_name = f"pwl_out_{var.name}_{self._aux_counter}"
        self._aux_counter += 1
        output = (
            LXVariable[str, float](output_name)
            .continuous()
            .bounds(lower=min(values), upper=max(values))
            .indexed_by(lambda x: x)
            .from_data([output_name])  # Use variable name as unique index
        )
        self.auxiliary_vars.append(output)

        # Constraint: sum(λ) = 1 (convexity)
        convex_expr = LXLinearExpression()
        for lv in lambda_vars:
            convex_expr.add_term(lv, 1.0)
        self.auxiliary_constraints.append(
            LXConstraint(f"pwl_convex_{output_name}").expression(convex_expr).eq().rhs(1.0)
        )

        # Constraint: x = sum(λ[i] * breakpoint[i])
        x_expr = LXLinearExpression().add_term(var, 1.0)
        for i, lv in enumerate(lambda_vars):
            x_expr.add_term(lv, -breakpoints[i])
        self.auxiliary_constraints.append(
            LXConstraint(f"pwl_x_{output_name}").expression(x_expr).eq().rhs(0)
        )

        # Constraint: y = sum(λ[i] * value[i])
        y_expr = LXLinearExpression().add_term(output, 1.0)
        for i, lv in enumerate(lambda_vars):
            y_expr.add_term(lv, -values[i])
        self.auxiliary_constraints.append(
            LXConstraint(f"pwl_y_{output_name}").expression(y_expr).eq().rhs(0)
        )

        # TODO: Add SOS2 constraint marking to solver
        # This would require solver-specific implementation
        # Most modern solvers (Gurobi, CPLEX, OR-Tools) support SOS2 natively

        return output

    def _incremental_formulation(
        self, var: LXVariable, breakpoints: List[float], values: List[float]
    ) -> LXVariable:
        """
        Incremental (multiple choice) formulation.

        Reference: sample_impl/opt_wrapper_design.py:509-567

        Uses binary variables to select which segment is active.
        More variables but can be faster for some solvers.

        Args:
            var: Input variable
            breakpoints: Breakpoint x-coordinates
            values: Function values at breakpoints

        Returns:
            Output variable representing f(var)
        """
        n = len(breakpoints) - 1  # Number of segments

        # Binary variables for segment selection
        segment_vars = []
        for i in range(n):
            seg_name = f"segment_{var.name}_{i}"
            seg_var = (
                LXVariable[str, int](seg_name)
                .binary()
                .indexed_by(lambda x: x)
                .from_data([seg_name])  # Use variable name as unique index
            )
            segment_vars.append(seg_var)
        self.auxiliary_vars.extend(segment_vars)

        # Delta variables (how far into each segment, normalized to [0,1])
        delta_vars = []
        for i in range(n):
            delta_name = f"delta_{var.name}_{i}"
            delta_var = (
                LXVariable[str, float](delta_name)
                .continuous()
                .bounds(lower=0, upper=1)
                .indexed_by(lambda x: x)
                .from_data([delta_name])  # Use variable name as unique index
            )
            delta_vars.append(delta_var)
        self.auxiliary_vars.extend(delta_vars)

        # Output variable
        output_name = f"pwl_out_{var.name}_{self._aux_counter}"
        self._aux_counter += 1
        output = (
            LXVariable[str, float](output_name)
            .continuous()
            .bounds(lower=min(values), upper=max(values))
            .indexed_by(lambda x: x)
            .from_data([output_name])  # Use variable name as unique index
        )
        self.auxiliary_vars.append(output)

        # Constraint: exactly one segment active
        segment_expr = LXLinearExpression()
        for sv in segment_vars:
            segment_expr.add_term(sv, 1.0)
        self.auxiliary_constraints.append(
            LXConstraint(f"one_segment_{output_name}")
            .expression(segment_expr)
            .eq()
            .rhs(1)
        )

        # Constraint: delta only positive if segment selected
        for i, (sv, dv) in enumerate(zip(segment_vars, delta_vars)):
            self.auxiliary_constraints.append(
                LXConstraint(f"delta_active_{output_name}_{i}")
                .expression(LXLinearExpression().add_term(dv, 1.0).add_term(sv, -1.0))
                .le()
                .rhs(0)
            )

        # Constraint: x = sum(breakpoint[i] * segment[i] + delta[i] * (bp[i+1] - bp[i]) * segment[i])
        # Simplified: x = sum(bp[i] * s[i] + delta[i] * width[i])
        x_expr = LXLinearExpression().add_term(var, 1.0)
        for i in range(n):
            width = breakpoints[i + 1] - breakpoints[i]
            x_expr.add_term(segment_vars[i], -breakpoints[i])
            x_expr.add_term(delta_vars[i], -width)
        self.auxiliary_constraints.append(
            LXConstraint(f"pwl_x_{output_name}").expression(x_expr).eq().rhs(0)
        )

        # Constraint: y = sum(value[i] * segment[i] + delta[i] * (val[i+1] - val[i]) * segment[i])
        y_expr = LXLinearExpression().add_term(output, 1.0)
        for i in range(n):
            slope = values[i + 1] - values[i]
            y_expr.add_term(segment_vars[i], -values[i])
            y_expr.add_term(delta_vars[i], -slope)
        self.auxiliary_constraints.append(
            LXConstraint(f"pwl_y_{output_name}").expression(y_expr).eq().rhs(0)
        )

        return output

    def _logarithmic_formulation(
        self, var: LXVariable, breakpoints: List[float], values: List[float]
    ) -> LXVariable:
        """
        Logarithmic formulation using Gray code.

        Reference: sample_impl/opt_wrapper_design.py:569-577

        Uses log2(n) binary variables instead of n.
        Best for many segments but more complex to implement.

        Note: This is a placeholder for future implementation.

        Args:
            var: Input variable
            breakpoints: Breakpoint x-coordinates
            values: Function values at breakpoints

        Returns:
            Output variable representing f(var)

        Raises:
            NotImplementedError: Gray code formulation not yet implemented
        """
        raise NotImplementedError(
            "Logarithmic (Gray code) formulation not yet implemented. "
            "Please use 'sos2' or 'incremental' method instead."
        )


__all__ = ["LXPiecewiseLinearizer"]
