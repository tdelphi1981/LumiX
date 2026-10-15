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
