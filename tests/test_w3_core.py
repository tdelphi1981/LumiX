"""W3 core API regressions (catalog A9-A13, B5, B6, C)."""
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from solver_matrix import AVAILABLE, solve_with  # noqa: E402
from test_canonical import fam, row_map  # noqa: E402

from lumix import LXConstraint, LXLinearExpression, LXModel, LXOptimizer, LXVariable


@dataclass(frozen=True)
class R:
    id: str
    cap: float


def test_a9_last_rhs_call_wins():
    c = LXConstraint("c").rhs(5).rhs(lambda r: r.cap)
    assert c.rhs_value is None and c.rhs_func is not None
    c.rhs(7)
    assert c.rhs_value == 7 and c.rhs_func is None


def test_a10_goal_sense_is_read_at_solve_time():
    x = fam("x", ["k"], lower=0, upper=10)
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint("g").expression(LXLinearExpression().add_term(x, 1.0))
                     .as_goal(priority=1).ge().rhs(8))
    m.set_goal_mode("weighted")
    m.prepare_goal_programming()
    s = solve_with("ortools", m)
    assert s.variables["x"]["k"] >= 8 - 1e-6


def test_a11_constraint_data_without_index_raises():
    x = fam("x", ["k"], upper=5)
    c = LXConstraint[R]("cap").expression(LXLinearExpression().add_term(x, 1.0)).le().rhs(3).from_data([R("a", 1)])
    with pytest.raises(ValueError, match="indexed_by"):
        LXModel("m").add_variable(x).add_constraint(c).to_canonical()
