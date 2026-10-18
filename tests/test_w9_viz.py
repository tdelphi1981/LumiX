"""W9c (0.3.2): visualization."""
import pytest

pytest.importorskip("plotly")

from lumix import LXConstraint, LXLinearExpression, LXModel, LXOptimizer, LXVariable
from lumix.visualization import LXVisualizationConfig
from lumix.visualization.themes import get_color_sequence


def _solved(feasible=True):
    x = LXVariable[None, float]("x").continuous().bounds(0, 10)
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint("cap").expression(
        LXLinearExpression().add_term(x, 1.0)).le().rhs(4 if feasible else -1))
    m.add_constraint(LXConstraint("neg").expression(
        LXLinearExpression().add_term(x, -1.0)).le().rhs(-1))
    m.maximize(LXLinearExpression().add_term(x, 1.0))
    return m, LXOptimizer().use_solver("ortools").solve(m)


def test_w9_config_keeps_the_user_template_and_theme_colours():
    cfg = LXVisualizationConfig(template="plotly_dark", theme="pastel")
    assert cfg.template == "plotly_dark"
    assert cfg.color_sequence == get_color_sequence("pastel")


def test_w9_utilization_only_for_positive_le_rows():
    from lumix.visualization import LXSolutionVisualizer
    m, s = _solved()
    fig = LXSolutionVisualizer(s, m).plot_constraint_utilization()
    util = {y: x for tr in fig.data for y, x in zip(tr.y, tr.x)}
    assert util["cap"] == pytest.approx(100.0) and util["neg"] is None


def test_w9_infeasible_solution_title_says_no_solution():
    from lumix.visualization import LXSolutionVisualizer
    m, s = _solved(feasible=False)
    fig = LXSolutionVisualizer(s, m).plot()
    assert "no solution" in fig.layout.title.text.lower()
    assert "0.00" not in fig.layout.title.text


def test_w9_hint_annotation_sits_on_the_constraint_panel():
    from lumix.visualization import LXSolutionVisualizer
    _, s = _solved()
    fig = LXSolutionVisualizer(s).plot()
    hint = [a for a in fig.layout.annotations if "sensitivity" in (a.text or "")]
    status_axis = [tr.xaxis for tr in fig.data if tr.name == "Constraint Status"
                   or getattr(tr, "x", None) == ("No Data",)][0]
    assert hint and hint[0].xref.split()[0] == status_axis


def test_w9_dashboard_height_is_per_panel_row():
    from lumix.visualization import LXDashboard
    m, s = _solved()
    assert LXDashboard(m, s).plot_summary_only().layout.height == 300


def test_w9_satisfaction_tolerance_zero_is_honoured():
    from lumix.solution.solution import LXSolution
    from lumix.visualization import LXGoalProgressChart
    sol = LXSolution(objective_value=0.0, status="optimal", solve_time=0.0,
                     variables={}, mapped={})
    sol.goal_deviations = {"g": {"pos": {None: 5e-7}, "neg": {None: 0.0}}}
    fig = LXGoalProgressChart(sol).plot_satisfaction_status(tolerance=0.0)
    labels = [str(t) for tr in fig.data for t in (tr.text or ())]
    assert labels and "Satisfied" not in labels


def test_w9_waterfall_colours_follow_the_sense():
    from lumix.analysis.scenario import LXScenario, LXScenarioAnalyzer
    from lumix.visualization import LXScenarioCompare
    x = LXVariable[None, float]("x").continuous().bounds(0, 100)
    m = LXModel("m").add_variable(x)
    m.add_constraint(LXConstraint("need").expression(
        LXLinearExpression().add_term(x, 1.0)).ge().rhs(5))
    m.minimize(LXLinearExpression().add_term(x, 1.0))
    a = LXScenarioAnalyzer(m, LXOptimizer().use_solver("ortools"))
    a.add_scenario(LXScenario("more").modify_constraint_rhs("need", set_value=8))
    a.run_all_scenarios()
    viz = LXScenarioCompare(a)
    fig = viz.plot_scenario_waterfall()
    colours = list(fig.data[0].marker.color)
    assert colours[-1] == viz._get_colors()[3]          # cost went up: worse
