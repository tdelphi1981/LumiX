"""W7: goal programming carry-overs from the W5 final review."""
import sys
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from solver_matrix import AVAILABLE, solve_with  # noqa: E402
from test_canonical import fam  # noqa: E402
from test_w5_goals import _lex_model, goal, hard, lin  # noqa: E402

from lumix import LXConstraint, LXModel, LXNonLinearExpression, LXOptimizer, LXVariable
from lumix.core.canonical import LXCanonicalBuilder


def test_w5_stage_models_do_not_rebuild_goal_stages(monkeypatch):
    calls = []
    original = LXCanonicalBuilder._goal_stages

    def spy(self):
        result = original(self)
        calls.append(result)
        return result

    monkeypatch.setattr(LXCanonicalBuilder, "_goal_stages", spy)
    s = solve_with("ortools", _lex_model())
    assert [st.objective_value for st in s.goal_stages] == pytest.approx([0, 6])
    assert calls and all(result == () for result in calls)


def _abs_goal_model(objective):
    x = fam("x", ["k"], lower=-5, upper=5)
    m = LXModel("m").add_variable(x)
    m.add_constraint(hard("lo", lin((x, 1.0)), "<=", 1))
    m.add_constraint(goal("absgoal", LXNonLinearExpression().add_abs(x), ">=", 4, priority=1))
    m.add_constraint(goal("pos", lin((x, 1.0)), ">=", 0, priority=2))
    if objective == "min":
        m.minimize(lin((x, 1.0)))
    elif objective == "max":
        m.maximize(lin((x, 1.0)))
    return m.set_goal_mode("sequential")


@pytest.mark.parametrize("solver", AVAILABLE)
@pytest.mark.parametrize("objective", [None, "min", "max"])
def test_w5_sequential_with_linearization(solver, objective):
    s = LXOptimizer().use_solver(solver).enable_linearization().solve(_abs_goal_model(objective))
    assert s.status == "optimal"
    assert s.variables["x"]["k"] == pytest.approx(-4.0)
    expected = [(1, 0.0), (2, 4.0)] + ([(0, -4.0)] if objective else [])
    assert [st.priority for st in s.goal_stages] == [p for p, _ in expected]
    assert [st.objective_value for st in s.goal_stages] == pytest.approx([v for _, v in expected])
    assert s.get_goal_deviations("pos")["neg"] == pytest.approx({"pos": 4.0})


@pytest.mark.parametrize("solver", AVAILABLE)
def test_w5_sequential_relinearizes_after_stage_bounds(solver):
    x = fam("x", ["k"], lower=-5, upper=5)
    m = LXModel("m").add_variable(x).minimize(lin((x, 1.0)))
    m.add_constraint(hard("lo", lin((x, 1.0)), "<=", 1))
    m.add_constraint(goal("floor", lin((x, 1.0)), ">=", -2, priority=1))
    m.add_constraint(goal("absgoal", LXNonLinearExpression().add_abs(x), ">=", 4, priority=2))
    m.set_goal_mode("sequential")
    s = LXOptimizer().use_solver(solver).enable_linearization().solve(m)
    assert s.variables["x"]["k"] == pytest.approx(-2.0)
    assert [st.priority for st in s.goal_stages] == [1, 2, 0]
    assert [st.objective_value for st in s.goal_stages] == pytest.approx([0.0, 2.0, -2.0])


def test_w5_extract_custom_objectives_is_deprecated():
    from lumix import extract_custom_objectives

    with pytest.warns(DeprecationWarning, match="final_objective"):
        assert extract_custom_objectives([]) == []


def test_w5_colliding_goal_keys_name_the_goal():
    x = fam("x", ["k"], lower=0, upper=10)
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint[object]("tgt").expression(lin((x, 1.0))).ge().rhs(1)
                     .indexed_by(lambda k: k).from_data([1, "1"]).as_goal(priority=1))
    with pytest.raises(ValueError, match=r"Goal 'tgt' has index keys 1 and '1'"):
        m.prepare_goal_programming()


def test_w5_infeasible_stage_has_no_objective_value():
    x = fam("x", ["k"], lower=0, upper=1)
    m = LXModel("m").add_variable(x)
    m.add_constraint(hard("bad", lin((x, 1.0)), ">=", 5))
    m.add_constraint(goal("g", lin((x, 1.0)), ">=", 1, priority=1))
    m.set_goal_mode("sequential")
    s = solve_with("ortools", m)
    assert s.goal_stages[0].status == "infeasible"
    assert s.goal_stages[0].objective_value is None


def test_w5_private_solution_field_is_last():
    from dataclasses import fields

    from lumix import LXSolution

    names = [f.name for f in fields(LXSolution)]
    assert names[-1] == "_undesired_deviations"


def test_w5_total_deviation_counts_only_the_undesired_side():
    x = fam("x", ["k"], lower=0, upper=10)
    m = LXModel("m").add_variable(x).maximize(lin((x, 1.0)))
    m.add_constraint(goal("atleast2", lin((x, 1.0)), ">=", 2, priority=1))
    m.add_constraint(goal("atmost3", lin((x, 1.0)), "<=", 3, priority=2))
    s = solve_with("ortools", m)
    assert s.get_goal_deviations("atleast2")["pos"] == pytest.approx({"atleast2": 1.0})
    assert s.get_total_deviation("atleast2") == pytest.approx(0.0)
    assert s.get_total_deviation("atmost3") == pytest.approx(0.0)


def test_w5_goal_waterfall_total_includes_every_goal():
    pytest.importorskip("plotly")
    from lumix.visualization import LXGoalProgressChart

    x = fam("x", ["k"], lower=0, upper=10)
    m = LXModel("m").add_variable(x)
    m.add_constraint(hard("cap", lin((x, 1.0)), "<=", 4))
    m.add_constraint(goal("g1", lin((x, 1.0)), ">=", 6, priority=1))
    m.add_constraint(goal("g2", lin((x, 1.0)), ">=", 7, priority=2))
    s = solve_with("ortools", m)
    fig = LXGoalProgressChart(s).plot_deviation_waterfall()
    trace = fig.data[0]
    values = dict(zip(trace.x, trace.y))
    assert values["Total"] == pytest.approx(values["g1"] + values["g2"])
