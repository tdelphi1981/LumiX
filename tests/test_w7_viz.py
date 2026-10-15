"""W7: visualization fixes (B14 and the catalog C items)."""

import warnings

import pytest

pytest.importorskip("plotly")

from dataclasses import dataclass

from lumix import (
    LXConstraint, LXLinearExpression, LXModel, LXOptimizer, LXScenario,
    LXScenarioAnalyzer, LXSensitivityAnalyzer, LXVariable,
)
from lumix.visualization import LXDashboard, LXScenarioCompare, LXSolutionVisualizer


@dataclass
class P:
    id: str
    profit: float
    use: float


PS = [P("a", 3, 1), P("b", 2, 2)]


def _lp(integer=False):
    x = LXVariable[P, float]("x")
    x = (x.integer() if integer else x.continuous()).bounds(lower=0).indexed_by(lambda p: p.id).from_data(PS)
    m = LXModel("m").add_variable(x).maximize(LXLinearExpression().add_term(x, lambda p: p.profit))
    m.add_constraint(LXConstraint("cap").expression(LXLinearExpression().add_term(x, lambda p: 1)).le().rhs(10))
    m.add_constraint(LXConstraint("cap2").expression(LXLinearExpression().add_term(x, lambda p: p.use)).le().rhs(100))
    return m


def _solve(m, sens=True):
    opt = LXOptimizer().use_solver("ortools")
    return (opt.enable_sensitivity() if sens else opt).solve(m)


def test_b14_dashboard_without_extras():
    m = _lp()
    fig = LXDashboard(m, _solve(m)).plot()
    assert len(fig.data) == 2


def test_b14_dashboard_with_sensitivity():
    m = _lp()
    sol = _solve(m)
    fig = LXDashboard(m, sol).add_sensitivity(LXSensitivityAnalyzer(m, sol)).plot()
    assert len(fig.data) == 4


def test_b14_dashboard_with_goals_and_scenarios():
    m = _lp()
    m.add_constraint(
        LXConstraint("b_goal").expression(
            LXLinearExpression().add_term(m.variables[0], lambda p: 1 if p.id == "b" else 0)
        ).ge().rhs(3).as_goal(priority=1, weight=1.0)
    )
    sol = _solve(m, sens=False)
    sa = LXScenarioAnalyzer(m, LXOptimizer().use_solver("ortools"))
    sa.add_scenario(LXScenario("tight").modify_constraint_rhs("cap", set_value=5))
    sa.run_all_scenarios()
    fig = LXDashboard(m, sol).add_scenarios(sa).plot()
    assert len(fig.data) == 6
    util = _utilization(LXSolutionVisualizer(sol, m).plot_constraint_utilization())
    assert util["cap"] == pytest.approx(100.0)


def _utilization(fig):
    return {name: x for trace in fig.data for name, x in zip(trace.y, trace.x)}


def test_c_utilization_uses_row_activity():
    m = _lp()
    util = _utilization(LXSolutionVisualizer(_solve(m), m).plot_constraint_utilization())
    # optimum x = (10, 0): cap uses 10/10, cap2 uses 10/100
    assert util["cap"] == pytest.approx(100.0)
    assert util["cap2"] == pytest.approx(10.0)


def test_c_utilization_works_without_duals():
    m = _lp(integer=True)
    util = _utilization(LXSolutionVisualizer(_solve(m, sens=False), m).plot_constraint_utilization())
    assert util["cap"] == pytest.approx(100.0)


def test_c_utilization_needs_the_model():
    m = _lp()
    with pytest.raises(ValueError, match="model"):
        LXSolutionVisualizer(_solve(m)).plot_constraint_utilization()


def _scenarios():
    m = _lp()
    sa = LXScenarioAnalyzer(m, LXOptimizer().use_solver("ortools"))
    sa.add_scenario(LXScenario("more").modify_constraint_rhs("cap", set_value=15))
    sa.add_scenario(LXScenario("less").modify_constraint_rhs("cap", set_value=5))
    sa.add_scenario(LXScenario("broken").modify_constraint_rhs("cap", set_value=-1))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sa.run_all_scenarios()
    return sa


def test_c_waterfall_bars_are_absolute_against_the_baseline():
    fig = LXScenarioCompare(_scenarios()).plot_scenario_waterfall()
    tops = {}
    for trace in fig.data:
        bases = trace.base if trace.base is not None else [0] * len(trace.x)
        if not isinstance(bases, (list, tuple)):
            bases = [bases] * len(trace.x)
        for name, base, y in zip(trace.x, bases, trace.y):
            tops[name] = base + y
    assert tops == pytest.approx({"Baseline": 30.0, "more": 45.0, "less": 15.0})


def test_c_scenario_ranking_skips_infeasible_and_follows_sense():
    from lumix.visualization.scenario import _ranked_feasible

    assert [name for name, _ in _ranked_feasible(_scenarios())] == ["more", "baseline", "less"]


def test_w7_row_activity_slack_and_binding():
    from lumix.solution.activity import row_activity

    m = _lp()
    act = row_activity(m, _solve(m))
    assert act["cap"].lhs == pytest.approx(10.0) and act["cap"].binding
    assert act["cap2"].slack == pytest.approx(90.0) and not act["cap2"].binding
