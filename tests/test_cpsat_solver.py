"""
Tests for the CP-SAT solver adapter.

Constraint naming used to write through ``ct.Proto().name``; with OR-Tools
9.13+ that proxy is temporary and the process aborts (segfault or
"Check failed: LoadConstraint"). The test runs in a subprocess so a crash is
reported as a failure instead of killing the test session.
"""

import subprocess
import sys
import textwrap

import pytest

pytest.importorskip("ortools")

SCRIPT = textwrap.dedent(
    """
    from lumix import LXConstraint, LXLinearExpression, LXModel, LXOptimizer, LXVariable

    items = ["a", "b", "c"]
    x = (
        LXVariable[str, int]("x").integer().bounds(lower=0, upper=10)
        .indexed_by(lambda k: k).from_data(items)
    )
    model = LXModel("cpsat_names")
    model.add_variable(x)
    model.add_constraint(
        LXConstraint("total")
        .expression(LXLinearExpression().add_term(x, 1))
        .le()
        .rhs(12)
    )
    for item in items:
        model.add_constraint(
            LXConstraint(f"cap_{item}")
            .expression(LXLinearExpression().add_term(x, 1, where=lambda k, i=item: k == i))
            .le()
            .rhs(5)
        )
    model.maximize(LXLinearExpression().add_term(x, 1))
    solution = LXOptimizer().use_solver("cpsat").solve(model)
    print(solution.status, solution.objective_value)
    """
)


def test_cpsat_solves_named_constraints_without_crashing():
    result = subprocess.run([sys.executable, "-c", SCRIPT], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr[-2000:]
    status, objective = result.stdout.split()[-2:]
    assert status == "optimal"
    assert float(objective) == pytest.approx(12)
