"""Shared helpers for tests that run one model on every installed solver."""
from __future__ import annotations

import importlib.util
import itertools
import logging
import math

from lumix import LXOptimizer
from lumix.core.enums import LXConstraintSense, LXObjectiveSense

_MODULES = {"ortools": "ortools", "gurobi": "gurobipy", "cplex": "cplex", "glpk": "swiglpk"}
AVAILABLE = [name for name, module in _MODULES.items()
             if importlib.util.find_spec(module) is not None]
# CP-SAT takes integer models only (continuous ones need enable_rational_conversion).
INTEGER_SOLVERS = AVAILABLE + (["cpsat"] if "ortools" in AVAILABLE else [])


def solve_with(solver, model, rational=False, **params):
    logging.disable(logging.CRITICAL)
    try:
        optimizer = LXOptimizer().use_solver(solver)
        if rational:
            optimizer.enable_rational_conversion()
        return optimizer.solve(model, **params)
    finally:
        logging.disable(logging.NOTSET)


def brute_force(model):
    """(status, objective) by enumerating every integer point of a small, bounded,
    all-integer model. Independent of every solver adapter: it evaluates the
    canonical rows directly."""
    canon = model.to_canonical()
    ranges = []
    for v in canon.variables:
        assert math.isfinite(v.lower) and math.isfinite(v.upper), v.name
        ranges.append(range(int(v.lower), int(v.upper) + 1))
    assert math.prod(len(r) for r in ranges) <= 4096, "model too large to enumerate"
    best = None
    for point in itertools.product(*ranges):
        ok = True
        for row in canon.rows:
            lhs = sum(c * point[i] for i, c in row.coeffs.items())
            if row.sense == LXConstraintSense.LE and lhs > row.rhs + 1e-9:
                ok = False
            elif row.sense == LXConstraintSense.GE and lhs < row.rhs - 1e-9:
                ok = False
            elif row.sense == LXConstraintSense.EQ and abs(lhs - row.rhs) > 1e-9:
                ok = False
            if not ok:
                break
        if not ok:
            continue
        value = canon.objective_constant + sum(c * point[i] for i, c in canon.objective.items())
        if best is None or (value > best if canon.sense == LXObjectiveSense.MAXIMIZE
                            else value < best):
            best = value
    return ("infeasible", None) if best is None else ("optimal", best)
