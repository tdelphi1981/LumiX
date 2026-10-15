"""
Piecewise-linear approximation for arbitrary nonlinear functions.

Implements three formulation methods, all exact for the piecewise-linear
function through the breakpoints:
1. SOS2: convex-combination weights with adjacency enforced by segment binaries
2. Incremental: Binary selection variables
3. Logarithmic: Gray code encoding with ceil(log2(segments)) binaries
"""

import math
from typing import Any, Callable, List, Literal, Optional, Sequence, Tuple

import numpy as np

from ...core.constraints import LXConstraint
from ...core.variables import LXVariable
from ...utils._warn import warn_user
from ..config import LXLinearizerConfig
from ..refs import LXAuxFactory, LXVarRef


def adaptive_breakpoints(func: Callable[[float], float], x_min: float, x_max: float,
                         num_segments: int) -> List[float]:
    """``num_segments + 1`` strictly increasing breakpoints, denser where ``|f''|``
    is large. Deterministic: the breakpoints are quantiles of a density that mixes
    the curvature with a uniform floor, so every region keeps some breakpoints."""
    if num_segments < 1:
        raise ValueError(f"num_segments must be at least 1, got {num_segments}")
    uniform = [float(b) for b in np.linspace(x_min, x_max, num_segments + 1)]
    if num_segments == 1:
        return uniform
    xs = np.linspace(x_min, x_max, 10 * num_segments + 1)
    ys = np.array([float(func(x)) for x in xs])
    density = np.concatenate([[0.0], np.abs(np.diff(ys, 2)), [0.0]])
    total = float(density.sum())
    if not math.isfinite(total) or total <= 1e-9 * (float(np.max(np.abs(ys))) + 1.0):
        return uniform
    density = 0.5 * density / total + 0.5 / len(xs)
    cdf = np.concatenate([[0.0], np.cumsum((density[1:] + density[:-1]) / 2)])
    cdf /= cdf[-1]
    inner = np.interp(np.arange(1, num_segments) / num_segments, cdf, xs)
    points = [float(x_min), *(float(v) for v in inner), float(x_max)]
    if any(b <= a for a, b in zip(points, points[1:])):
        return uniform
    return points


def piecewise_points(
    func: Callable[[float], float],
    lower: Optional[float],
    upper: Optional[float],
    config: LXLinearizerConfig,
    *,
    name: str,
    num_segments: Optional[int] = None,
    x_min: Optional[float] = None,
    x_max: Optional[float] = None,
    adaptive: Optional[bool] = None,
    breakpoints: Optional[Sequence[float]] = None,
) -> Tuple[List[float], List[float]]:
    """Breakpoints and function values of one piecewise-linear term. Settings left
    as ``None`` come from ``config`` (B9). ``lower``/``upper`` are the variable's
    bounds (``None`` when open); a domain narrower than them is warned about."""
    if breakpoints is not None:
        if x_min is not None or x_max is not None:
            raise ValueError(f"Give either breakpoints or x_min/x_max for {name}, not both")
        points = [float(b) for b in breakpoints]
        if len(points) < 2 or any(b <= a for a, b in zip(points, points[1:])):
            raise ValueError(
                f"breakpoints for {name} must contain at least two strictly "
                f"increasing values, got {points}")
        x_min, x_max = points[0], points[-1]
    else:
        num_segments = config.pwl_num_segments if num_segments is None else num_segments
        adaptive = config.adaptive_breakpoints if adaptive is None else adaptive
        x_min = lower if x_min is None else x_min
        x_max = upper if x_max is None else x_max
        if x_min is None or x_max is None:
            raise ValueError(
                f"Cannot determine domain for piecewise-linear approximation of {name}. "
                f"Detected: [{x_min}, {x_max}]. "
                f"Please specify x_min/x_max or set bounds on the variable.")
        points = (adaptive_breakpoints(func, x_min, x_max, num_segments) if adaptive
                  else [float(b) for b in np.linspace(x_min, x_max, num_segments + 1)])
    if lower is None or lower < x_min or upper is None or upper > x_max:
        warn_user(
            f"The piecewise-linear term restricts {name} to [{x_min}, {x_max}], "
            f"narrower than its bounds [{lower}, {upper}]", UserWarning)
    try:
        values = [float(func(bp)) for bp in points]
    except Exception as e:
        raise ValueError(
            f"Failed to evaluate function at breakpoints: {e}. "
            f"Ensure function is defined over domain [{x_min}, {x_max}].") from e
    return points, values


class LXPiecewiseLinearizer:
    """Piecewise-linear approximation of a function of one variable (public API;
    the linearization engine uses :func:`piecewise` per instance)."""

    def __init__(self, config: LXLinearizerConfig):
        """
        Initialize piecewise linearizer.

        Args:
            config: Linearization configuration
        """
        self.config = config
        self._aux = LXAuxFactory()
        self.auxiliary_vars: List[LXVariable] = self._aux.variables
        self.auxiliary_constraints: List[LXConstraint] = self._aux.constraints

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

        ``var`` must be a single variable (a scalar or a family with one instance);
        terms in an ``LXNonLinearExpression`` apply to every instance of a family.

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
        x = LXVarRef.single(var, "approximate_function")
        points, values = piecewise_points(
            func, None if math.isinf(x.lower) else x.lower,
            None if math.isinf(x.upper) else x.upper, self.config, name=var.name,
            num_segments=num_segments, x_min=x_min, x_max=x_max, adaptive=adaptive,
            breakpoints=breakpoints)
        tag = self._aux.tag("pwl", [var.name])
        return piecewise(self._aux, tag, None, x, points, values,
                         method or self.config.pwl_method).var


def piecewise(aux: LXAuxFactory, tag: str, key: Any, x: LXVarRef, breakpoints: Sequence[float],
              values: Sequence[float], method: str) -> LXVarRef:
    """``y = f(x)``, exact for the piecewise-linear function through the breakpoints."""
    if method == "sos2":
        return _sos2(aux, tag, key, x, list(breakpoints), list(values))
    if method == "incremental":
        return _incremental(aux, tag, key, x, list(breakpoints), list(values))
    if method == "logarithmic":
        return _logarithmic(aux, tag, key, x, list(breakpoints), list(values))
    raise ValueError(f"Unknown piecewise-linear method: {method}")


def _lambdas(aux, tag, key, x, bps, values):
    """Convex-combination weights ``lam`` with ``x = sum(lam*b)``, ``y = sum(lam*v)``."""
    lam = [aux.var(tag, f"lam{i}", key, "continuous", 0.0, 1.0) for i in range(len(bps))]
    y = aux.var(tag, "out", key, "continuous", min(values), max(values))
    aux.row(tag, "convex", key, [(l, 1.0) for l in lam], "==", 1.0)
    aux.row(tag, "x", key, [(x, 1.0)] + [(l, -b) for l, b in zip(lam, bps)], "==", 0.0)
    aux.row(tag, "y", key, [(y, 1.0)] + [(l, -v) for l, v in zip(lam, values)], "==", 0.0)
    return lam, y


def _sos2(aux, tag, key, x, bps, values):
    """SOS2 by segment binaries: only the two weights of the chosen segment can be
    nonzero."""
    lam, y = _lambdas(aux, tag, key, x, bps, values)
    segments = len(bps) - 1
    if segments == 1:
        return y
    z = [aux.var(tag, f"sos{s}", key, "binary") for s in range(segments)]
    aux.row(tag, "sos_one", key, [(v, 1.0) for v in z], "==", 1.0)
    for i, l in enumerate(lam):
        aux.row(tag, f"adj{i}", key,
                [(l, 1.0)] + [(z[s], -1.0) for s in (i - 1, i) if 0 <= s < segments], "<=", 0.0)
    return y


def _incremental(aux, tag, key, x, bps, values):
    """One binary per segment selects it; ``delta`` is the position inside it."""
    n = len(bps) - 1
    seg = [aux.var(tag, f"seg{i}", key, "binary") for i in range(n)]
    delta = [aux.var(tag, f"delta{i}", key, "continuous", 0.0, 1.0) for i in range(n)]
    y = aux.var(tag, "out", key, "continuous", min(values), max(values))
    aux.row(tag, "one", key, [(s, 1.0) for s in seg], "==", 1.0)
    for i in range(n):
        aux.row(tag, f"active{i}", key, [(delta[i], 1.0), (seg[i], -1.0)], "<=", 0.0)
    aux.row(tag, "x", key, [(x, 1.0)] + [(seg[i], -bps[i]) for i in range(n)]
            + [(delta[i], -(bps[i + 1] - bps[i])) for i in range(n)], "==", 0.0)
    aux.row(tag, "y", key, [(y, 1.0)] + [(seg[i], -values[i]) for i in range(n)]
            + [(delta[i], -(values[i + 1] - values[i])) for i in range(n)], "==", 0.0)
    return y


def _logarithmic(aux, tag, key, x, bps, values):
    """Gray-code encoding with ``ceil(log2(segments))`` binaries; segments are padded
    to a power of two with zero-width copies of the last breakpoint."""
    segments = len(bps) - 1
    bits = math.ceil(math.log2(segments)) if segments > 1 else 0
    padded = 2 ** bits
    bps = bps + [bps[-1]] * (padded - segments)
    values = values + [values[-1]] * (padded - segments)
    lam, y = _lambdas(aux, tag, key, x, bps, values)
    codes = [s ^ (s >> 1) for s in range(padded)]
    for l in range(bits):
        g = aux.var(tag, f"gray{l}", key, "binary")
        ones, zeros = [(g, -1.0)], [(g, 1.0)]
        for j, lv in enumerate(lam):
            adjacent = [codes[s] >> l & 1 for s in (j - 1, j) if 0 <= s < padded]
            if all(adjacent):
                ones.append((lv, 1.0))
            elif not any(adjacent):
                zeros.append((lv, 1.0))
        aux.row(tag, f"gray_one{l}", key, ones, "<=", 0.0)
        aux.row(tag, f"gray_zero{l}", key, zeros, "<=", 1.0)
    return y


__all__ = ["LXPiecewiseLinearizer", "adaptive_breakpoints", "piecewise", "piecewise_points"]
