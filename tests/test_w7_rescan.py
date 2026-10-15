"""W7 re-scan gate: findings of the second bug hunt."""
from fractions import Fraction

import pytest

from lumix import LXRationalConverter


@pytest.mark.parametrize("method", ["farey", "continued_fraction", "stern_brocot"])
@pytest.mark.parametrize("value", [-0.5, -2.75, -0.1])
def test_w7_rational_error_of_a_negative_value_is_zero_when_exact(method, value):
    fraction, error = LXRationalConverter(method=method).to_rational(value, return_error=True)
    assert fraction == Fraction(value).limit_denominator(10**6)
    assert error == pytest.approx(abs(float(fraction) - value), abs=1e-15)
    assert error < 1e-12


@pytest.mark.parametrize("method", ["farey", "continued_fraction", "stern_brocot"])
def test_w7_rational_error_reports_the_rounding_of_a_near_integer(method):
    value = 1e12 + 0.5
    fraction, error = LXRationalConverter(method=method).to_rational(value, return_error=True)
    assert error == pytest.approx(abs(float(fraction) - value))


# ---------------------------------------------------------------- solver adapters
import logging
import subprocess
import sys
import textwrap

from lumix import LXConstraint, LXLinearExpression, LXModel, LXOptimizer, LXVariable
from tests.solver_matrix import AVAILABLE


def _var(name, kind="continuous", lower=0.0, upper=None, keys=None):
    v = getattr(LXVariable[str, float](name), kind)().bounds(lower=lower, upper=upper)
    return v if keys is None else v.indexed_by(lambda k: k).from_data(list(keys))


def _row(name, expr, sense, rhs):
    return getattr(LXConstraint(name).expression(expr), sense)().rhs(rhs)


def _solve(solver, model, **kw):
    return LXOptimizer().use_solver(solver).solve(model, **kw)


def _infeasible_with_a_ray(kind):
    """x + y >= 2 and x + y <= 1 (infeasible); max z has an unbounded ray."""
    x, y, z = _var("x", kind), _var("y", kind), _var("z", kind)
    m = LXModel("m").add_variables(x, y, z)
    s = LXLinearExpression().add_term(x, 1).add_term(y, 1)
    m.add_constraint(_row("a", s, "ge", 2))
    m.add_constraint(_row("b", LXLinearExpression().add_term(x, 1).add_term(y, 1), "le", 1))
    m.maximize(LXLinearExpression().add_term(z, 1))
    return m


@pytest.mark.parametrize("solver", [s for s in ("ortools", "gurobi", "cplex", "glpk") if s in AVAILABLE])
@pytest.mark.parametrize("kind", ["continuous", "integer"])
def test_rescan_solvers_infeasible_model_with_a_ray_is_infeasible(solver, kind):
    status = _solve(solver, _infeasible_with_a_ray(kind)).status
    if solver == "cplex" and kind == "integer":
        assert status in ("infeasible", "inf_or_unbounded")   # documented for CPLEX MIPs
    else:
        assert status == "infeasible"


@pytest.mark.parametrize("solver", [s for s in ("ortools", "gurobi", "cplex", "glpk") if s in AVAILABLE])
def test_rescan_solvers_feasible_unbounded_mip_is_unbounded(solver):
    x, y = _var("x", "integer"), _var("y")
    m = LXModel("m").add_variables(x, y)
    m.add_constraint(_row("c", LXLinearExpression().add_term(x, 1).add_term(y, -1), "eq", 0.5))
    m.maximize(LXLinearExpression().add_term(y, 1))
    assert _solve(solver, m).status == "unbounded"


@pytest.mark.skipif("cplex" not in AVAILABLE, reason="cplex")
def test_rescan_commercial_cplex_stopped_lp_reports_no_infeasible_point():
    import random
    r = random.Random(1)
    n = 40
    c = [[r.randint(1, 20) for _ in range(n)] for _ in range(n)]
    x = _var("x", keys=range(n))
    m = LXModel("lp").add_variable(x)
    for i in range(n):
        m.add_constraint(_row(f"r{i}", LXLinearExpression().add_multi_term(x, coeff=lambda k, i=i: c[i][k]),
                              "ge", 100 + i))
    m.minimize(LXLinearExpression().add_multi_term(x, coeff=lambda k: 1 + k % 7))
    s = _solve("cplex", m, lpmethod=2, preprocessing_presolve=0, simplex_limits_iterations=1)
    assert s.status != "optimal"
    if s.variables:
        xs = s.variables["x"]
        assert all(sum(c[i][k] * xs[k] for k in range(n)) >= 100 + i - 1e-6 for i in range(n))
    else:
        assert not s.is_feasible()


@pytest.mark.skipif("cplex" not in AVAILABLE, reason="cplex")
def test_rescan_commercial_cplex_documented_parameter_paths_are_applied():
    import lumix.solvers.cplex_solver as cs
    seen = {}
    real = cs.LXCPLEXSolver._parse_solution

    def spy(self, model, cplex_model, *a, **k):
        seen["cutsfactor"] = cplex_model.parameters.mip.limits.cutsfactor.get()
        return real(self, model, cplex_model, *a, **k)

    x = _var("x", "integer", 0, 3)
    m = LXModel("m").add_variable(x)
    m.maximize(LXLinearExpression().add_term(x, 1))
    cs.LXCPLEXSolver._parse_solution = spy
    try:
        assert _solve("cplex", m, mip_limits_cutsfactor=0).objective_value == 3
    finally:
        cs.LXCPLEXSolver._parse_solution = real
    assert seen["cutsfactor"] == 0


@pytest.mark.skipif("cplex" not in AVAILABLE, reason="cplex")
def test_rescan_commercial_cplex_verbose_prints_the_log(capfd):
    x = _var("x", "integer", 0, 3)
    m = LXModel("m").add_variable(x)
    m.maximize(LXLinearExpression().add_term(x, 1))
    _solve("cplex", m, verbose=True)
    assert "Version identifier" in capfd.readouterr().out


@pytest.mark.skipif("gurobi" not in AVAILABLE, reason="gurobi")
def test_rescan_commercial_gurobi_logtoconsole_prints_the_log(capfd):
    x = _var("x", "integer", 0, 3)
    m = LXModel("m").add_variable(x)
    m.maximize(LXLinearExpression().add_term(x, 1))
    _solve("gurobi", m, LogToConsole=1)
    assert "Gurobi" in capfd.readouterr().out


@pytest.mark.skipif("cplex" not in AVAILABLE, reason="cplex")
def test_rescan_commercial_cplex_unbounded_nonconvex_qp_warns():
    from lumix import LXQuadraticExpression
    x, y = _var("x"), _var("y")
    m = LXModel("m").add_variables(x, y)
    m.maximize(LXQuadraticExpression().add_quadratic(x, y, 1.0))
    with pytest.warns(UserWarning, match="unbounded"):
        s = _solve("cplex", m)
    assert s.status != "optimal"


@pytest.mark.parametrize("solver", [s for s in ("gurobi", "glpk", "ortools", "cplex") if s in AVAILABLE])
@pytest.mark.parametrize("key", ["k" * 300, "north\tsouth"])
def test_rescan_solvers_long_or_odd_names_solve(solver, key):
    # GLPK aborts the process on such names, so run in a subprocess
    code = textwrap.dedent(f"""
        import logging; logging.disable(logging.CRITICAL)
        from lumix import LXModel, LXVariable, LXLinearExpression, LXConstraint, LXOptimizer
        x = LXVariable[str, float]("x").continuous().bounds(lower=0, upper=10).indexed_by(lambda k: k).from_data([{key!r}])
        m = LXModel("m").add_variable(x)
        m.add_constraint(LXConstraint({key!r}).expression(LXLinearExpression().add_term(x, 1)).le().rhs(3))
        m.maximize(LXLinearExpression().add_term(x, 1))
        s = LXOptimizer().use_solver({solver!r}).solve(m)
        print(s.status, s.objective_value, s.variables["x"])
    """)
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr[-500:]
    assert out.stdout.split()[0:2] == ["optimal", "3.0"], out.stdout
    assert repr(key) in out.stdout


@pytest.mark.skipif("glpk" not in AVAILABLE, reason="glpk")
def test_rescan_lp_solvers_glpk_infeasible_mip_is_infeasible():
    assert _solve("glpk", _infeasible_with_a_ray("integer")).status == "infeasible"


@pytest.mark.skipif("glpk" not in AVAILABLE, reason="glpk")
def test_rescan_lp_solvers_glpk_deletes_its_problem(monkeypatch):
    import swiglpk
    created, deleted = [], []
    real_create, real_delete = swiglpk.glp_create_prob, swiglpk.glp_delete_prob
    monkeypatch.setattr(swiglpk, "glp_create_prob", lambda: created.append(1) or real_create())
    monkeypatch.setattr(swiglpk, "glp_delete_prob", lambda p: deleted.append(1) or real_delete(p))
    x = _var("x", upper=1, keys=range(3))
    m = LXModel("m").add_variable(x)
    m.maximize(LXLinearExpression().add_term(x, 1))
    opt = LXOptimizer().use_solver("glpk")
    for _ in range(3):
        assert opt.solve(m).objective_value == 3
    assert len(created) >= 3 and len(deleted) >= len(created) - 1


def _hard_equality_knapsack(n=70, seed=3):
    import random
    r = random.Random(seed)
    w = [r.randint(10**6, 10**7) for _ in range(n)]
    x = _var("x", "binary", keys=range(n))
    m = LXModel("hard").add_variable(x)
    for i in range(2):
        wi = [r.randint(10**6, 10**7) for _ in range(n)]
        target = sum(wi[j] for j in range(0, n, 2)) + 1
        m.add_constraint(_row(f"eq{i}", LXLinearExpression().add_multi_term(x, coeff=lambda j, wi=wi: wi[j]),
                              "eq", target))
    m.maximize(LXLinearExpression().add_multi_term(x, coeff=lambda j: w[j]))
    return m


@pytest.mark.parametrize("solver", [s for s in ("ortools", "cpsat") if s in AVAILABLE or s == "cpsat"])
def test_rescan_lp_solvers_time_limit_without_solution_is_time_limit(solver):
    s = _solve(solver, _hard_equality_knapsack(), time_limit=0.3)
    if not s.variables:
        assert s.status == "time_limit"


def test_rescan_lp_solvers_cpsat_keeps_exact_equalities_exact():
    x, y, z = _var("x"), _var("y"), _var("z")
    m = LXModel("m").add_variables(x, y, z)
    m.add_constraint(_row("exact", LXLinearExpression().add_term(x, 1).add_term(y, 1), "eq", 1))
    m.add_constraint(_row("offgrid", LXLinearExpression().add_term(z, 3), "eq", 1))
    m.maximize(LXLinearExpression().add_term(x, 1))
    s = LXOptimizer().use_solver("cpsat").enable_rational_conversion().solve(m)
    assert s.variables["x"] + s.variables["y"] == pytest.approx(1.0, abs=1e-9)


def test_rescan_lp_solvers_cpsat_huge_finite_bound_is_treated_as_open():
    x = _var("x", "integer", 0, 1e20)
    m = LXModel("m").add_variable(x)
    m.add_constraint(_row("c", LXLinearExpression().add_term(x, 1), "le", 10))
    m.maximize(LXLinearExpression().add_term(x, 1))
    assert _solve("cpsat", m).objective_value == 10


# ---------------------------------------------------------------- goal programming
def _goal_model(mode="sequential"):
    x = LXVariable("x").continuous().bounds(lower=0)
    m = LXModel("m").add_variable(x)
    m.add_constraint(_row("cap", LXLinearExpression().add_term(x, 1), "le", 8))
    m.add_constraint(_row("tgt", LXLinearExpression().add_term(x, 1), "ge", 10).as_goal(1))
    m.set_goal_mode(mode)
    return m


@pytest.mark.parametrize("prepare", [False, True])
def test_rescan_goals_prepared_model_without_objective_is_minimized(prepare):
    from lumix import LXObjectiveSense, LXScenario, LXScenarioAnalyzer, LXWhatIfAnalyzer
    from lumix.analysis._sense import solved_sense
    m = _goal_model()
    if prepare:
        m.prepare_goal_programming()
    assert solved_sense(m) == LXObjectiveSense.MINIMIZE
    opt = LXOptimizer().use_solver("ortools")
    assert dict(LXWhatIfAnalyzer(m, opt).find_bottlenecks())["cap"] == pytest.approx(1.0)
    a = LXScenarioAnalyzer(m, opt)
    a.add_scenario(LXScenario("more_cap").modify_constraint_rhs("cap", set_value=10))
    a.add_scenario(LXScenario("less_cap").modify_constraint_rhs("cap", set_value=5))
    a.run_all_scenarios()
    assert a.get_best_scenario() == "more_cap"


@pytest.mark.parametrize("mode", ["weighted", "sequential"])
def test_rescan_goals_infeasible_solve_reports_no_goal_as_satisfied(mode):
    x = LXVariable("x").continuous().bounds(lower=0, upper=10)
    m = LXModel("m").add_variable(x)
    m.add_constraint(_row("hard", LXLinearExpression().add_term(x, 1), "ge", 20))
    m.add_constraint(_row("g", LXLinearExpression().add_term(x, 1), "ge", 5).as_goal(1))
    m.set_goal_mode(mode)
    s = _solve("ortools", m)
    assert s.status == "infeasible"
    assert s.is_goal_satisfied("g") is not True
    assert s.get_total_deviation("g") is None
    assert "Goals Satisfied" not in s.summary()


def _nonlinear_goal_model():
    from lumix import LXNonLinearExpression
    x = LXVariable("x").integer().bounds(lower=0, upper=10)
    y = LXVariable("y").integer().bounds(lower=0, upper=10)
    m = LXModel("orig").add_variables(x, y)
    m.add_constraint(_row("cap", LXLinearExpression().add_term(x, 1).add_term(y, 1), "le", 10))
    m.add_constraint(_row("g1", LXLinearExpression().add_term(x, 1), "ge", 8).as_goal(1, 1.0))
    m.add_constraint(_row("g2", LXLinearExpression().add_term(y, 1), "ge", 6).as_goal(2, 100.0))
    m.add_constraint(_row("nl", LXNonLinearExpression().add_abs(x), "le", 10))
    m.set_goal_mode("sequential")
    return m


@pytest.mark.parametrize("prepare", [False, True])
def test_rescan_linearization_manual_linearize_model_keeps_the_goals(prepare):
    from lumix.linearization import LXLinearizer, LXLinearizerConfig
    from lumix.solvers import ORTOOLS_CAPABILITIES
    m = _nonlinear_goal_model()
    if prepare:
        m.prepare_goal_programming()
    lm = LXLinearizer(m, ORTOOLS_CAPABILITIES, LXLinearizerConfig()).linearize_model()
    s = _solve("ortools", lm)
    assert (s.variables["x"], s.variables["y"]) == (8, 2)        # lexicographic
    assert s.get_total_deviation("g2") == pytest.approx(4)


@pytest.mark.parametrize("prepare", [False, True])
def test_rescan_goals_row_activity_reports_the_goal_row_itself(prepare):
    from lumix import LXConstraintSense
    from lumix.solution import row_activity
    x = LXVariable("x").continuous().bounds(lower=0)
    m = LXModel("m").add_variable(x)
    m.add_constraint(_row("hard", LXLinearExpression().add_term(x, 1), "le", 3))
    m.add_constraint(_row("short", LXLinearExpression().add_term(x, 1), "ge", 5).as_goal(1))
    m.maximize(LXLinearExpression().add_term(x, 1))
    if prepare:
        m.prepare_goal_programming()
    s = _solve("ortools", m)
    row = row_activity(m, s)["short"]
    assert (row.lhs, row.rhs, row.sense) == (pytest.approx(3), 5, LXConstraintSense.GE)
    assert row.slack == pytest.approx(-2) and not row.binding


@pytest.mark.parametrize("method, sense, expected", [
    ("relax_constraint", "ge", -12.0), ("tighten_constraint", "ge", -8.0),
    ("relax_constraint", "le", -8.0), ("tighten_constraint", "le", -12.0),
    ("increase_constraint_rhs", "ge", -8.0), ("decrease_constraint_rhs", "ge", -12.0),
])
def test_rescan_analysis_percent_change_of_a_negative_rhs_moves_the_right_way(method, sense, expected):
    from lumix import LXWhatIfAnalyzer
    x = LXVariable("x").continuous().bounds(lower=-100, upper=100)
    m = LXModel("m").add_variable(x)
    m.add_constraint(_row("c", LXLinearExpression().add_term(x, 1), sense, -10))
    (m.minimize if sense == "ge" else m.maximize)(LXLinearExpression().add_term(x, 1))
    result = getattr(LXWhatIfAnalyzer(m, LXOptimizer().use_solver("ortools")), method)("c", by_percent=0.2)
    assert result.new_objective == pytest.approx(expected)


def test_rescan_analysis_relaxing_a_prepared_ge_goal_lowers_its_target():
    from lumix import LXWhatIfAnalyzer
    m = _goal_model("weighted").prepare_goal_programming()
    w = LXWhatIfAnalyzer(m, LXOptimizer().use_solver("ortools"))
    relaxed = w.relax_constraint("tgt", by=1)
    tightened = w.tighten_constraint("tgt", by=1)
    assert relaxed.new_solution.get_total_deviation("tgt") == pytest.approx(1.0)
    assert tightened.new_solution.get_total_deviation("tgt") == pytest.approx(3.0)


def test_rescan_goals_duplicate_constraint_names_raise():
    x = _var("x")
    m = LXModel("m").add_variable(x)
    m.add_constraint(_row("lim", LXLinearExpression().add_term(x, 1), "le", 2))
    with pytest.raises(ValueError, match="already has a constraint named 'lim'"):
        m.add_constraint(_row("lim", LXLinearExpression().add_term(x, 1), "le", 5))
    with pytest.raises(ValueError, match="already has a constraint named 'lim'"):
        m.add_constraints(_row("lim", LXLinearExpression().add_term(x, 1), "le", 5))


# ---------------------------------------------------------------- core
@pytest.mark.parametrize("call", [
    lambda e, x, y: e.add_abs(LXLinearExpression().add_term(x, 1)),
    lambda e, x, y: e.add_min(x, LXLinearExpression().add_term(y, 1)),
    lambda e, x, y: e.add_max(LXLinearExpression().add_term(y, 1), x),
    lambda e, x, y: e.add_product(x, LXLinearExpression().add_term(y, 1)),
    lambda e, x, y: e.add_piecewise(LXLinearExpression().add_term(y, 1), abs),
    lambda e, x, y: e.add_indicator(LXLinearExpression().add_term(y, 1), True, LXLinearExpression()),
])
def test_rescan_linearization_terms_reject_an_expression_where_a_variable_is_needed(call):
    from lumix import LXNonLinearExpression
    x, y = _var("x", upper=5), _var("y", "binary")
    with pytest.raises(TypeError, match="LXVariable"):
        call(LXNonLinearExpression(), x, y)


@pytest.mark.parametrize("bound", ["lower", "upper"])
def test_rescan_core_callable_bounds_are_rejected_with_a_clear_message(bound):
    with pytest.raises(TypeError, match="per-instance"):
        LXVariable("x").continuous().bounds(**{bound: lambda p: 3})


def test_rescan_core_unhashable_instances_without_indexed_by_get_a_clear_error():
    from dataclasses import dataclass

    @dataclass
    class Product:
        name: str

    x = LXVariable[Product, float]("x").continuous().bounds(lower=0, upper=1).from_data(
        [Product("a"), Product("b")])
    m = LXModel("m").add_variable(x)
    m.maximize(LXLinearExpression().add_term(x, 1))
    with pytest.raises(ValueError, match="indexed_by"):
        m.to_canonical()


# ---------------------------------------------------------------- visualization
def _min_scenarios(baseline_demand=10):
    """minimize 2x, x >= demand, x <= cap: baseline 20, low 10, high 100, impossible infeasible."""
    from lumix import LXScenario, LXScenarioAnalyzer
    x = _var("x")
    m = LXModel("m").add_variable(x)
    m.add_constraint(_row("demand", LXLinearExpression().add_term(x, 1), "ge", baseline_demand))
    m.add_constraint(_row("cap", LXLinearExpression().add_term(x, 1), "le", 60))
    m.minimize(LXLinearExpression().add_term(x, 2))
    sa = LXScenarioAnalyzer(m, LXOptimizer().use_solver("ortools"))
    sa.add_scenario(LXScenario("low").modify_constraint_rhs("demand", set_value=5))
    sa.add_scenario(LXScenario("high").modify_constraint_rhs("demand", set_value=50))
    sa.add_scenario(LXScenario("impossible").modify_constraint_rhs("cap", set_value=-1))
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sa.run_all_scenarios()
    return sa


def test_rescan_viz_comparison_bar_marks_the_best_feasible_scenario_in_the_model_sense():
    pytest.importorskip("plotly")
    from lumix.visualization import LXScenarioCompare
    fig = LXScenarioCompare(_min_scenarios()).plot_comparison_bar()
    assert [a.text for a in fig.layout.annotations if a.text == "Best"] == ["Best"]
    assert [a.x for a in fig.layout.annotations if a.text == "Best"] == ["low"]


def test_rescan_viz_scenario_charts_leave_out_infeasible_scenarios():
    pytest.importorskip("plotly")
    from lumix.visualization import LXScenarioCompare
    compare = LXScenarioCompare(_min_scenarios())
    names = set()
    for trace in list(compare.plot().data) + list(compare.plot_radar_comparison().data):
        names |= set(getattr(trace, "x", None) or []) | ({trace.name} if trace.name else set())
    assert "impossible" not in names


def test_rescan_viz_scenario_plot_with_a_zero_baseline():
    pytest.importorskip("plotly")
    from lumix.visualization import LXScenarioCompare
    assert LXScenarioCompare(_min_scenarios(baseline_demand=0)).plot() is not None


def test_rescan_viz_dashboard_variable_panel_shows_nonzero_instances():
    pytest.importorskip("plotly")
    from lumix.visualization import LXDashboard
    x = _var("x", upper=10, keys=range(8))
    m = LXModel("m").add_variable(x)
    m.add_constraint(_row("c", LXLinearExpression().add_term(x, 1), "le", 30))
    m.maximize(LXLinearExpression().add_term(x, lambda k: k))
    fig = LXDashboard(m, _solve("ortools", m)).plot()
    bars = [t for t in fig.data if t.type == "bar" and t.x and any(str(v).startswith("x[") for v in t.x)]
    assert bars and set(bars[0].x) == {"x[5]", "x[6]", "x[7]"}


def test_rescan_viz_constraint_status_panel_counts_binding_rows_by_slack():
    pytest.importorskip("plotly")
    from lumix.visualization import LXSolutionVisualizer
    x = _var("x")
    m = LXModel("m").add_variable(x)
    m.add_constraint(_row("a", LXLinearExpression().add_term(x, 1), "le", 4))
    m.add_constraint(_row("b", LXLinearExpression().add_term(x, 1), "le", 4))   # degenerate: binding, dual 0
    m.add_constraint(_row("c", LXLinearExpression().add_term(x, 1), "le", 9))
    m.maximize(LXLinearExpression().add_term(x, 1))
    s = LXOptimizer().use_solver("ortools").enable_sensitivity().solve(m)
    fig = LXSolutionVisualizer(s, m).plot()
    status = [t for t in fig.data if t.type == "bar" and list(t.x or []) == ["Binding", "Non-binding"]]
    assert status and list(status[0].y) == [2, 1]


@pytest.mark.parametrize("value, max_den", [(2.99999999, 10000), (0.99999999, 10000), (2.9, 2), (0.9, 1)])
def test_rescan_utils_stern_brocot_matches_the_best_approximation(value, max_den):
    got = LXRationalConverter(max_denominator=max_den, method="stern_brocot").to_rational(value)
    best = Fraction(value).limit_denominator(max_den)
    assert abs(float(got) - value) <= abs(float(best) - value) + 1e-15


def test_rescan_goals_constraint_name_check_follows_direct_list_changes():
    x = _var("x")
    m = LXModel("m").add_variable(x)
    first = _row("a", LXLinearExpression().add_term(x, 1), "le", 2)
    m.add_constraint(first)
    m.constraints.remove(first)
    m.constraints.append(_row("b", LXLinearExpression().add_term(x, 1), "le", 3))
    m.add_constraint(_row("a", LXLinearExpression().add_term(x, 1), "le", 4))   # no false duplicate
    assert [c.name for c in m.constraints] == ["b", "a"]


@pytest.mark.skipif("cplex" not in AVAILABLE, reason="cplex")
def test_rescan_commercial_cplex_mip_emphasis_is_applied():
    import lumix.solvers.cplex_solver as cs
    seen = {}
    real = cs.LXCPLEXSolver._parse_solution

    def spy(self, model, cplex_model, *a, **k):
        seen["emphasis"] = cplex_model.parameters.emphasis.mip.get()
        return real(self, model, cplex_model, *a, **k)

    x = _var("x", "integer", 0, 3)
    m = LXModel("m").add_variable(x)
    m.maximize(LXLinearExpression().add_term(x, 1))
    cs.LXCPLEXSolver._parse_solution = spy
    try:
        _solve("cplex", m, mip_emphasis=1)
    finally:
        cs.LXCPLEXSolver._parse_solution = real
    assert seen["emphasis"] == 1
