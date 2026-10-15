# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-10-15

### Added
- `LXModel.to_canonical()` and `LXCanonicalModel`: a solver-independent form of a model that every adapter builds from.
- Coefficients and filters of `add_term` may take the constraint row instance as a second argument.
- Scalar variables: an `LXVariable` without a data source is one variable whose solution value is a number (documented before, but it raised "has no data source").
- CP-SAT: `approximate_coefficients=True` (on `solve()` or `use_solver("cpsat", ...)`) accepts coefficients that cannot be represented exactly.
- `LXVariable.cost_expression()`, `LXModel.cost_objective()`, and `minimize()` / `maximize()` without an argument, which use the variables' `cost()` / `cost_multi()`.
- `indexed_by_join(...)` builds the `(first, second)` pairs returned by `join_func`, keyed by `key_func`.
- Quadratic objectives: Gurobi and CPLEX solve them natively (nonconvex included); `add_quadratic` covers every instance pair of two families with a numeric or `coeff(a, b)` coefficient, `add_squared` the diagonal; `add_quadratic_term` is an alias of `add_quadratic`. Other solvers raise a clear error, or, with `enable_linearization()`, linearize the products (see Changed).
- Expression arithmetic: `-`, unary `-`, `+=`, `*=`, `sum([...])`, right-hand `+`/`*`, and any real constant (NumPy scalars included).
- `LXSolution.relaxation`: `True` when the solved model was linearized with a relaxation (McCormick envelopes for a product of two continuous variables); the objective value is then a bound.
- `LXModel.to_canonical().objective_nonlinear` lists the nonlinear objective terms as `LXCanonicalNonlinear` items, one per variable instance (kinds `abs`, `min`, `max`, `product`, `piecewise`; piecewise items carry numeric breakpoints, values and method). `LXCanonicalNonlinear` has the new fields `term` (position of the source term in the expression) and `key` (instance key, `None` for single variables); `schema_version` stays 1.
- Quadratic expression arithmetic: `lin - quad`, `quad - lin`, `quad - 3`, `-quad`, `quad * k` and `k * quad`.
- On `indexed_by_product` and join families, `.cost(...)` and the callable coefficients of `add_quadratic` / `add_squared` may take one argument per part (`lambda d, t: ...`), like `cost_multi`.
- Nonlinear terms in constraints are linearized; the direction comes from the constraint sense, and in an indexed constraint a row that is an instance of the term's family uses only that instance.
- `adaptive_breakpoints(func, x_min, x_max, num_segments)` and `piecewise_points(...)` in `lumix.linearization.techniques.piecewise`.
- Goal programming: `LXSolution.goal_stages`, a list of `LXGoalStage(priority, objective_value, status)` (exported from `lumix`), one per solve of sequential mode; the final stage (model objective and priority-0 goals) has priority 0.
- `LXRowKeyFilter(var, row_key)` in `lumix.core.expressions`: a row-aware filter that keeps, in each row, the instance keyed by `row_key(row)`; the canonical builder looks it up by key, so such rows build in linear time.
- `LXModel.to_canonical().goal_stages`: in sequential goal mode, the stage objectives (`{position: coeff}`) in priority order; `objective` then holds the final stage (model objective and priority-0 goals). Empty in weighted mode.
- `solve_goal_programming(model, optimizer, mode=LXGoalMode.SEQUENTIAL)` (it raised `NotImplementedError`); the mode given overrides the model's mode without changing `model.goal_mode`.
- `SEQUENTIAL_TOLERANCE` in `lumix.goal_programming.solver`: relative slack of the sequential stage bounds (default `0.0`, exact).
- `final_objective(model, custom_goals)` in `lumix.goal_programming.objective_builder`: the model's objective combined with the priority-0 goals.
- Goals whose expression is an `LXNonLinearExpression` (e.g. `add_abs`); solve them with `enable_linearization()`.
- `model_factory=` on `LXScenarioAnalyzer` and `LXWhatIfAnalyzer`: a function that builds the model, called once for the base model and once per scenario or what-if run instead of copying the model (for ORM models, open a fresh session inside it). It must return a new model on every call.
- `LXResultStore` and `LXStoredRun` (`lumix.analysis.store`, needs `lumix-opt[orm]`): pass `result_store=` to either analyzer to write every solve to the `lumix_runs` / `lumix_run_values` tables (SQLAlchemy), with optional shadow prices and reduced costs; read them back with `runs()` and `values()`.
- `LXSensitivityAnalyzer.analyze_constraint_family(name)` and `analyze_variable_family(name)`: every row or instance of a family, keyed by index key.
- `lumix.enable_logging(level="INFO", stream=None, fmt=...)`: prints LumiX's log records (LumiX itself attaches only a `NullHandler`); calling it again replaces its handler.
- `CPSAT_CAPABILITIES`, `GLPK_CAPABILITIES`, `LXPiecewiseLinearizer` and `LXRowKeyFilter` are exported from `lumix`, as the documentation already showed.
- `LXNonLinearExpression.add_indicator(..., sense="<=", rhs=0.0)`: indicator rows with `>=` and `==` and a right-hand side (any other sense raises `ValueError`).
- `lumix.solution.row_activity(model, solution)` and `LXRowActivity`: the left-hand side, right-hand side, slack and binding state of every constraint row at a solution.
- A "Correctness Notes" page in the user guide: what LumiX solves exactly, what it approximates, and how it is verified.

### Behavior changes

Models that were solved wrongly before now give different (correct) results; every entry below that changes a result or raises where 0.2.x did not is listed here. lumix-ir's API surface is unchanged.

- Same-type constraint narrowing applies only to one-argument coefficients and filters, decided for each `add_term` separately (also after `e1 + e2` or `expr * 2`). Parameters with a default value do not count, so `lambda item, g=g: ...` is a one-argument filter.
- A variable or constraint family whose instances repeat an index key raises `ValueError`.
- Sums that cancel to floating-point noise (`0.1 + 0.2 - 0.3`) are treated as 0 in rows and right-hand sides.
- A variable family with empty data has no variables and logs a warning (it used to become one unindexed variable).
- Gurobi returns `feasible` with the incumbent when a limit stops the search.
- CP-SAT: open variable bounds become at most ±2^40 (smaller when large coefficients would overflow a row), and a solution that reaches such a bound is `feasible`, not `optimal`; equalities on scaled continuous variables that have no exact grid solution are solved again as bands of half a grid step per variable (then a whole step), and the largest deviation is logged — a feasible continuous model is no longer reported infeasible; coefficients that `max_denom` cannot represent within 1e-9 relative error, or rows whose common denominator exceeds 64 bits, raise `ValueError` unless `approximate_coefficients=True`; `scale_objective` has no effect.
- A solve without a solution (infeasible, unbounded) returns `variables == {}` on every adapter (OR-Tools returned zeros, CPLEX returned values for unbounded MIPs).
- Gurobi no longer prints its log; pass `verbose=True` to `solve()` or `use_solver("gurobi", ...)` to see it.
- OR-Tools (GLOP) and CPLEX re-solve once without presolve when presolve cannot tell an infeasible LP from an unbounded one; GLPK settles a MIP with an unbounded relaxation by a feasibility check (at most 2 s) and reports `inf_or_unbounded` when that does not finish.
- OR-Tools returns no duals or reduced costs for MIPs (SCIP has none; they were reported as 0).
- `+` and `*` on expressions return a new expression and no longer modify the left operand; use `+=` / `*=` for in-place changes.
- Adding a second variable family with an existing name raises `ValueError` (it crashed with `KeyError` at solve).
- A constraint with data but no `indexed_by(...)` raises `ValueError` (it built one combined row).
- A quadratic expression in a constraint raises `ValueError`.
- `where_multi()` on a variable with a single index raises `ValueError` (it was ignored); use `where()`.
- Assigning `model.objective_expr` replaces an objective set by `minimize()` / `maximize()` without an argument.
- `LXNonLinearExpression` terms (`add_abs`, `add_min`, `add_max`, `add_product`, `add_piecewise`) on variable families apply to every instance and the results are summed (`add_abs(x)` is the sum of `|x[i]|`). The families of one term must have the same index keys (else `ValueError`); a single variable is broadcast to every instance. `LXQuadraticExpression.add_quadratic` still multiplies all pairs.
- Absolute values, min and max that the plain epigraph form cannot represent exactly (a maximized `|x|` or `max`, a minimized `min`, `|x|` with a negative weight, rows such as `|x| >= c`, `max(...) >= c` or `min(...) <= c`, and every use in an `==` row) get binary variables and are exact; they need finite bounds on their variables (else `ValueError`).
- Products: binary × bounded variable and integer × (integer or continuous) are exact (the integer factor is expanded in binary digits, limited by `LXLinearizerConfig.binary_expansion_bits`); binary × unbounded uses `big_m_value` with a `UserWarning`; continuous × continuous uses McCormick envelopes with a `UserWarning` and sets `solution.relaxation`.
- With `enable_linearization()`, quadratic objectives on OR-Tools, GLPK and CP-SAT are linearized with the same product rules (families, integer and continuous factors included); on Gurobi and CPLEX they stay native. Auxiliary variables of `abs`, `min`, `max` and products of integer variables (whole coefficients) are integer, so CP-SAT accepts them; piecewise terms and McCormick envelopes use continuous auxiliaries and need a MIP solver.
- `linearize_model()` never modifies the user's model and starts afresh on every call. Auxiliary variables are families `aux_<kind>_<vars>_<n>_<role>` indexed by the instance keys of their term; their values appear per instance in `solution.variables`.
- Indicator Big-M constants are computed from the bounds of the expression; `big_m_value` is used (with a `UserWarning`) only when the expression is unbounded. An indicator's binary must be a single variable.
- Adaptive piecewise breakpoints are deterministic (quantiles of the curvature mixed with a uniform density) and exactly `num_segments + 1`; a linear function gets uniform breakpoints.
- `num_segments`, `adaptive` and `method` of `add_piecewise`, `LXPiecewiseLinearTerm` and `LXPiecewiseLinearizer.approximate_function` default to `None` and are taken from `LXLinearizerConfig` (`pwl_num_segments`, `adaptive_breakpoints`, `pwl_method`); values given on the term win.
- `LXBilinearLinearizer.linearize_bilinear` and `LXPiecewiseLinearizer.approximate_function` take single variables (a scalar or a one-instance family).
- `LXOptimizer.solve(model)` and `model.to_canonical()` relax goals automatically on a shallow copy; the user's model is not changed and `prepare_goal_programming()` is no longer needed (calling it still relaxes the goals in place). The goal mode can change between solves.
- Priority-0 goals are objective terms, not relaxed rows: a `.ge()` goal's expression is maximized and a `.le()` goal's minimized, times its weight; `get_goal_deviations()` returns `None` for them. Priority-0 `.eq()`, indexed or nonlinear goals, and negative or non-integer priorities raise `ValueError` (integer-valued numbers such as `numpy.int64(1)` or `2.0` are accepted; `True` is not).
- The model's own objective (`minimize` / `maximize`, also the cost-based form) is the lowest priority of a model with goals: in weighted mode it is added in minimization form with weight 1, so `objective_value` is the combined value; in sequential mode it is the final stage. A nonlinear objective with goals raises `ValueError`.
- Sequential goal programming is lexicographic: each solved priority is bounded by its optimum (`Σ weight·undesired deviation ≤ optimum + SEQUENTIAL_TOLERANCE·max(1, |optimum|)`) in the later stages, and the model objective is solved last. A stage that is not optimal stops the sequence and its solution is returned. `LXOptimizer.solve()` runs sequential mode itself; `solve_sequential()`'s `relaxed_constraints` is optional; `LXGoalProgrammingSolver.solve_sequential()` / `solve_weighted()` solve in their own mode whatever the model's goal mode (a model prepared for the other mode raises `ValueError`).
- `build_weighted_objective` skips priority-0 goals.
- Solving a model prepared with `prepare_goal_programming()` after `set_goal_mode` changed its mode raises `ValueError` (sequential → weighted ignored the goals).
- `LXSolution.is_goal_satisfied` (and the "Goals Satisfied" line of `summary()`) checks only the undesired deviations: exceeding a `>=` goal or staying below a `<=` goal is satisfied.
- A sequential stage that is not solved to optimality is reported with a warning on the `lumix.goal_programming.solver` logger instead of `print`.
- Model copies (`copy.deepcopy(model)`, used by what-if and scenario analysis) share data instances and callables with the original instead of deep-copying them; ORM objects are no longer detached by `deepcopy` (an ORM-backed family is queried once at copy time). Detaching is used only when a model is pickled.
- `LXSensitivityAnalyzer.analyze_variable` / `analyze_constraint` take an instance or row name (`"production[widget]"`, `"capacity[3]"`) or a scalar name, and raise `ValueError` for an indexed family name; `analyze_all_variables()` / `analyze_all_constraints()` and the methods built on them (binding constraints, bottlenecks, reports) are keyed per instance and per row.
- `LXWhatIfAnalyzer.find_bottlenecks` returns the improvement per unit in the objective's own direction (positive is better, also for minimization), ranks an unbounded relaxation as `inf`, skips other relaxations that are not feasible with a warning, and raises `ValueError` without a feasible baseline.
- `LXScenarioAnalyzer.get_best_scenario()` considers only feasible results and, by default (`maximize=None`), follows the base model's objective sense; it used to maximize unless told otherwise.
- Unknown scenario modification types and target types (e.g. `"objective"`) raise `ValueError` instead of being ignored.
- What-if `to=` on a constraint whose right-hand side is a function sets every row to that value; the change record's `original_value` / `new_value` / `delta` are `None` for such a constraint. `modify_variable_bound` fills `changes_applied`.
- `LXScenarioAnalyzer` and `LXWhatIfAnalyzer` accept the model and optimizer as keyword arguments (`base_model=` / `model=`, `optimizer=`).
- LumiX prints no log lines by default; call `lumix.enable_logging()` or configure `logging`. `LXModelLogger(name, level=None)` sets a level only when `level` is given and never adds a handler.
- `LXSolution.get_total_deviation(name)` sums only the undesired deviations (an over-achieved `>=` goal no longer reports a deviation); goal charts and the dashboard use it.
- `LXGoalStage.objective_value` is `None` for a stage without a feasible solution (it was 0).
- `LXSolutionVisualizer.plot_constraint_utilization()` needs the model (`LXSolutionVisualizer(solution, model)`) and no longer needs duals.
- Dashboard and scenario charts no longer prefix objective values with `$`.
- `LXConstraintSensitivity.is_binding` follows the row's slack (zero slack is binding), not a nonzero shadow price; degenerate binding rows are now reported as binding.
- `find_bottlenecks` tries equality rows in both directions and reports the better one.
- `model_factory` must return new constraint and variable objects on every call.
- `LXResultStore` tables: `lumix_runs.scenario` and `lumix_run_values.name` are `TEXT`.
- `LXSolution._undesired_deviations` moved to the end of the dataclass fields and is excluded from comparisons.
- OR-Tools and CP-SAT report `time_limit` (it was `not_solved` / `unknown`) when the time limit stops the search before any solution, as Gurobi and GLPK do.
- `LXModel.add_constraint` raises `ValueError` for a second constraint with the same name (it hid the first one from duals, activity and analysis).
- `by_percent` in what-if changes moves the right-hand side by a share of its absolute value (`-10` relaxed by 20 % for a `>=` row is `-12`); `tighten_constraint` on an equality lowers the right-hand side (it raised it, like `relax_constraint`).
- A goal solve without a solution has no goal deviations: `get_goal_deviations` and `is_goal_satisfied` return `None`, and `summary()` has no goal lines.
- `LXVariable.bounds()` raises `TypeError` for a function (per-instance bounds were documented but crashed at solve time); use an indexed constraint for per-instance limits.
- What-if `delta_objective` / `delta_percentage` are `nan` when the baseline or the changed model has no solution, and `sensitivity_range` reports `nan` for such points (an infeasible run used to count as a change to an objective of 0).
- `compare_scenarios()` lists scenarios best first in the model's sense with runs without a solution last, shown as `-`.

### Deprecated
- `LXLinearizerConfig` fields `default_method`, `tolerance`, `verbose_logging`, `prefer_sos2`, `auto_detect_bounds` and `mccormick_tighten_bounds` have no effect and issue a `DeprecationWarning` when set to a non-default value; so do the `prefer_sos2` and `mccormick_tighten_bounds` arguments of `enable_linearization()`. They will be removed in 0.4.0.
- `extract_custom_objectives` always returns an empty list (priority 0 goals are objective terms, not relaxed rows) and issues a `DeprecationWarning`; use `final_objective(model, custom_goals)`. It will be removed in 0.4.0.

### Fixed
- A1: a constant in a constraint's left-hand side was ignored by OR-Tools, CP-SAT, CPLEX and GLPK.
- A2: repeated terms on one variable overwrote each other (OR-Tools rows/objective, CPLEX/GLPK objective; GLPK aborted the process).
- A3: binary bounds were ignored and fractional integer bounds truncated (OR-Tools, CP-SAT).
- A4: an empty data family became one phantom variable or one constraint row.
- A5: same-type constraint rows dropped other instances even when the coefficient referenced the row; CP-SAT did not narrow at all.
- A6: CP-SAT scaled coefficients without scaling the right-hand side, rounded the objective constant, corrupted rows mixing integer and scaled continuous variables, kept scaling state between solves, capped open bounds at INT32 and rounded tiny coefficients to 0.
- A7: Gurobi discarded the incumbent on time, node and solution limits.
- A8: CPLEX status codes were mapped from wrong literals (infeasible MIPs reported as feasible).
- B1: OR-Tools crashed on integer variables with an open bound.
- B2: OR-Tools ignored `gap_tolerance` and `threads`; `use_solver(**kwargs)` and later `use_solver()` / `enable_*()` calls after a solve were ignored.
- B3: CP-SAT gap used an unscaled bound; CP-SAT warned about `enable_sensitivity` on every solve.
- B4: NamedTuple data was unpacked into several arguments in `sum_over`.
- B10: GLPK reported infeasible/unbounded problems as "undefined" and printed solver output for MIPs.
- Gurobi INF_OR_UNBD is resolved to infeasible or unbounded; CPLEX `output_clonelog` works.
- A9: `.rhs(value).rhs(func)` kept the value; the last call now wins.
- A10: `as_goal()` captured the constraint sense at call time (`.as_goal(1).ge()` was relaxed as `<=`).
- A11: a constraint with data but no `indexed_by` silently built one combined row.
- A12: `cost()` / `cost_multi()` were never used.
- A13: `where_multi` before `indexed_by_product`, and `.where()` on product variables, were ignored.
- B5: `indexed_by_join` did nothing.
- B6: quadratic objectives crashed every adapter; `LXQuadraticExpression.__add__` dropped the other expression.
- A14: binary × continuous products had wrong signs in two of their four constraints, and the product's bounds excluded 0 when the continuous variable's lower bound was positive.
- A15: linearization modified the user's objective expression, so repeated solves drifted and a second `linearize_model()` call added duplicate auxiliary variables.
- A16: nonlinear terms on variable families acted on the sum of the family instead of each instance.
- A17: a maximized `|x|`, a minimized `min` or a maximized `max` returned wrong optima; two terms on the same variables created auxiliary variables with the same name.
- A18: McCormick relaxations were reported as optimal without a warning; integer × integer products were relaxed instead of exact.
- A19: indicator Big-M rows had a wrong sign, `>=` and `==` indicators crashed, and the constant of the expression was dropped.
- A20: `LXNonLinearFunctions.power` returned 0 for negative inputs; a fractional exponent on a domain with negative values raises `ValueError`.
- B7: nonlinear terms in constraints crashed.
- B8: adaptive piecewise breakpoints were random and one short of `num_segments + 1`.
- B9: `LXLinearizerConfig` settings were never applied to piecewise terms.
- The constant of an `LXNonLinearExpression` objective was dropped.
- A21: sequential goal programming was not lexicographic: earlier priorities were not bounded, so the result was that of the last priority alone.
- A22: every row of an indexed goal contained the deviations of all rows; each row now has its own pair, named `<name>_<key>`.
- A25: priority-0 goals optimized nothing, and the model's own objective was silently replaced by the goal objective.
- A26: goals were solved as hard constraints unless `prepare_goal_programming()` was called first.
- Goals with an `LXNonLinearExpression` crashed during relaxation.
- A23: what-if and scenario copies deep-copied data instances while lambdas kept the originals, so identity checks and instance-keyed dicts in closures gave wrong results or `KeyError`.
- A24: scenario `add=` / `multiply=` did nothing on a constraint whose right-hand side is a function; they now apply row by row and compose in order.
- B11: sensitivity analysis reported no shadow prices for indexed constraints and only the first instance (without a reduced cost) for a variable family.
- B12: `find_bottlenecks` ranked minimization models backwards and failed on constraints whose right-hand side is a function.
- B15: a copy of a model built from SQLAlchemy objects with unloaded relationships failed; `detach_orm_object` now loads them while a session is available.
- `get_best_scenario` could return an infeasible scenario.
- B13: `LXRationalConverter(method="continued_fraction")` raised `ZeroDivisionError` for every non-integer.
- B14: `LXDashboard.plot()` crashed unless both sensitivity and goal data were present.
- B16: every `LXOptimizer` reset the `lumix.optimizer` logger to INFO and added a console handler, so applications could not silence LumiX and saw each line twice under a configured root logger.
- B17: README snippets (`LXBilinearTerm(..., bounds_x=...)`, `LXPiecewiseLinearTerm(variable=..., slopes=...)`, `add_scenario("base", {})`, `solve_all()`) and documented imports (`from lumix import CPSAT_CAPABILITIES, GLPK_CAPABILITIES, LXPiecewiseLinearizer`) failed.
- The constraint-utilization chart drew every non-binding row at a fixed 50 %; it now shows LHS / RHS of each row.
- The scenario waterfall accumulated the scenario differences; each scenario is now a bar from the baseline to its own objective, and infeasible scenarios (reported objective 0) are left out of every scenario chart and ranking.
- The goal deviation waterfall's "Total" bar left out the last goal.
- Linearization warnings (McCormick, big-M, indicator, piecewise domain, deprecated settings) pointed at LumiX internals instead of the user's line; the deprecated-setting warning of `enable_linearization(...)` was therefore hidden by Python's default filters.
- A zero-weight `add_abs(x, 0)` or `add_product(x, y, 0)` raised "needs finite bounds".
- In an indexed constraint, a nonlinear term over two families of different data types was narrowed (or not) depending on argument order.
- Auxiliary variables of a term on a single variable were reported as `{None: value}`.
- Sequential goal programming rebuilt the stage list for every stage solve.
- Index keys of an indexed goal that differ but print the same (`1` and `"1"`) raised an internal "duplicate index key" error; the error now names the goal.
- `find_bottlenecks` moved equality rows only upwards, so it could miss or misreport an improvement.
- A `model_factory` that reused a constraint or variable object of the base model let what-if and scenario changes modify the base model; it now raises `ValueError`.
- `LXWhatIfAnalyzer(baseline_solution=...)` never recorded the given baseline in the result store.
- `LXSensitivityAnalyzer` did not see constraints added after its first lookup, and a lookup of a scalar constraint enumerated every indexed family.
- `LXConstraintSensitivity.slack` was never filled.
- Documentation pages called API that does not exist (`identify_binding_constraints`, `set_variable_bound`, `apply_change`, `get_non_binding_constraints`, `LXCustomLinearizer`, `lower_bound_func`), used goals with data but no `indexed_by`, treated a goal's deviations as a number, and described a linearization engine LumiX no longer has; code includes in the examples pages had drifted into docstrings.
- `LXRationalConverter` reported an error of `2|x|` for exact negative values with `method="continued_fraction"`, and an error of 0 for any value it rounded to an integer.
- The README's "Advanced Analysis" snippet used constraint names that the Simple Example does not define.
- CPLEX reported an LP stopped by a limit as `feasible` with a point that violates the constraints; such a stop is now `time_limit` without values.
- CPLEX reported some infeasible LPs as `unbounded`, GLPK reported infeasible LPs as `unbounded` and infeasible MIPs as `inf_or_unbounded`, and OR-Tools (SCIP) reported a feasible unbounded MIP as `infeasible`.
- GLPK aborted the Python process, and Gurobi raised, on a variable or constraint name longer than 255 characters or with a control character; names given to the solvers are now shortened (with a hash) and cleaned.
- GLPK never freed its problems, so memory grew with every solve.
- CP-SAT widened equalities that have an exact solution on its grid when another equality had none (`x + y == 1` gave 1.001), and failed with a raw `TypeError` on a very large finite bound (it is now capped like an open bound).
- Gurobi's documented `LogToConsole=1` printed nothing; documented CPLEX parameters such as `mip_limits_cutsfactor` were skipped as unknown, and the CPLEX log could not be shown (`verbose=True` now shows it; any CPLEX parameter can be given by its path, `_` for `.`).
- CPLEX warns when it cannot bound a nonconvex objective (status 133) instead of reporting the point it stopped at as an ordinary feasible solution.
- A sequential goal model without its own objective that was prepared with `prepare_goal_programming()` was analysed as a maximization: `find_bottlenecks` reported improvements with the wrong sign and `get_best_scenario` picked the scenario with the largest deviation.
- A goal model whose solve found no solution (infeasible, unbounded) reported every goal as satisfied with zero deviation.
- `row_activity` and sensitivity `slack` / `is_binding` reported a goal's relaxed row (deviations included, always binding) instead of the goal itself.
- `LXLinearizer(...).linearize_model()` returned a model without the goal mode and the `prepare_goal_programming()` state, so a sequential goal model was solved in weighted mode (or with no objective at all).
- What-if `relax_constraint` / `tighten_constraint` / `increase_constraint_rhs` / `decrease_constraint_rhs` with `by_percent` moved a negative right-hand side the wrong way, and relaxing a prepared `>=` goal raised its target.
- `add_abs`, `add_min`, `add_max`, `add_product`, `add_piecewise` and `add_indicator` accepted an expression where a variable is needed and failed at solve time with `AttributeError`; they now raise `TypeError` at once.
- A variable with data but no `indexed_by` over unhashable instances (a plain `@dataclass`) failed with an internal `TypeError`; the error now says to add `indexed_by`.
- Scenario charts: the comparison bar marked the largest objective as "Best" (the worst scenario when minimizing, or an infeasible one); the percentage, decision-variable and radar charts still drew infeasible scenarios, the radar ignored the objective sense, and `LXScenarioCompare.plot()` divided by zero on a zero baseline.
- The dashboard's "Variable Values" panel looked only at the first five instances of each family and could stay empty for a solution with nonzero values.
- The "Constraint Status" panel of `LXSolutionVisualizer.plot()` counted binding rows by nonzero dual; with the model it now uses the slack, as `is_binding` does.
- `LXRationalConverter(method="stern_brocot")` never considered the upper starting bound and could be far less accurate than Farey (2.99999999 gave 29999/10000).
- CPLEX's documented `mip_emphasis` parameter pointed at a parameter path that does not exist and was skipped.
- Documentation: loop examples whose lambdas read the loop variable after the loop (every row used the last item), `from_data(LXCartesianProduct(...))`, per-instance bounds, constraints with data but no `indexed_by`, `add_piecewise(slopes=)`, nonlinear-function examples that did not run or left out the auxiliary rows, solver pages that used API that does not exist (`solution.mip_gap`, `solution.variable_values`, `model.copy()`, ...), and logger names that `lumix.enable_logging()` does not reach.
- Building rows of a constraint family over the variable's own data type took quadratic time (8,000 rows: 4.9 s); it is linear again (0.13 s).
- The scenario waterfall used an infeasible baseline as its base, and the comparison bar and sensitivity curve drew infeasible results at 0; `compare_scenarios()` sorted largest-first whatever the objective sense and printed infeasible runs as 0.00 / -100 %.
- `row_activity`, `LXSolutionVisualizer.plot()` and `plot_constraint_utilization()` raised on a model with a nonlinear term in a constraint (rows with nonlinear terms are now left out).
- The golden LP files of the model tests were ignored by `.gitignore`, so the test failed on a fresh clone.

## [0.2.1] - 2026-10-14

### Added
- `breakpoints=[...]` on `add_piecewise` / `LXPiecewiseLinearTerm`: use explicit,
  strictly increasing breakpoints instead of generated ones. With a function that is
  piecewise linear through them the term is exact.
- The logarithmic (Gray code) piecewise formulation; it raised `NotImplementedError`.
- A `UserWarning` when a piecewise term's domain is narrower than its variable's bounds.

### Fixed
- **Nonlinear terms vanished with Gurobi and CPLEX.** The linearizer skipped every term
  the solver declares native support for (products, abs, min/max, piecewise, indicator),
  but no adapter translates nonlinear terms, so they were missing from the model
  (Gurobi: `min 3|x| + x` returned -10 instead of 8). Every term is now linearized.
- **SOS2 piecewise formulation was a relaxation.** No SOS2 condition was added, so the
  model was the convex hull of the function; nonconvex objectives could exceed the
  function (25 instead of 20.67 in a three-point example). Adjacency is now enforced
  with segment binaries.
- `x_min=0` / `x_max=0` on piecewise terms were ignored and replaced by the variable's
  bounds.
- Two piecewise terms on the same variable created auxiliary variables with the same
  names.

### Behavior changes
- Models with nonlinear terms solved with Gurobi or CPLEX now contain those terms;
  results change (they were wrong before). Products of continuous variables use the
  McCormick relaxation on these solvers too.
- The SOS2 piecewise formulation adds one binary per segment; nonconvex piecewise
  objectives now return the true optimum.

## [0.2.0] - 2026-10-14

### Added
- `keys=` on `LXLinearExpression.add_term`, `add_multi_term` and `sum_over`: select the
  instances of a term by index key instead of a `where` filter. Builds the same model,
  much faster for large variable families.
- `LXKeyFilter`, the callable that stores `keys=` (it works anywhere a `where` works).
- `LXVariable.index_key(instance)`: the key adapters use for an instance.
- User guide: *Performance Considerations*.

### Changed
- Solver adapters fetch each variable family's instances once per build instead of once
  per constraint row. ORM-backed families are queried once per build. The cache is cleared
  on every build.
- Solver adapters no longer re-check terms whose instances were already selected by key.

### Performance
- Transportation model with 600 rows and 90,000 variables (OR-Tools): build time 4.78 s in
  0.1.2; 2.88 s with `where` and 0.43 s with `keys=` in 0.2.0.

## [0.1.2] - 2026-10-14

### Added
- CONTRIBUTING.md with comprehensive development guidelines
- CODE_OF_CONDUCT.md with academic-focused community standards
- SECURITY.md with vulnerability reporting policy
- This CHANGELOG.md to track project changes
- Regression tests for the linearizer (both objective senses), the CP-SAT adapter and expression arithmetic

### Fixed
- **Linearizer kept every objective as a minimization.** `LXLinearizer.linearize_model()`
  compared the objective sense to `"maximize"` while `LXObjectiveSense` values are
  `"min"`/`"max"`. Maximized product, min and piecewise objectives returned wrong optima
  (example 06 reported an area of 16 instead of 100).
- **`LXOptimizer.enable_linearization()` had no effect.** `solve()` now linearizes the model
  with the solver's capabilities when linearization is enabled and the model needs it.
- **CP-SAT crashed the process with OR-Tools ≥ 9.13.** Constraints are now named with
  `with_name()` instead of writing through `Proto()`.
- **`priority_to_weight(1)` returned `1e5` instead of the documented `1e6`.**
- **Adding two expressions that share a variable silently dropped terms.** `e1 + e2` combined
  the two `where` filters with AND, so instances selected by only one of them were lost.
  Calling `add_term` twice for the same variable overwrote the first term. Both now keep every
  term: an instance is included when either term includes it, with the sum of the
  coefficients that apply to it.
- **`expr * scalar` always raised `ValueError`.** It now scales every term (including
  multi-indexed terms) and the constant.
- Version strings in `lumix.__version__` and the documentation now match the package version.
- `pytest` coverage now measures `lumix` (was the old `optixng` name).

### Behavior changes
These fixes intentionally change results of code that relied on the old behavior:
- Maximized nonlinear objectives solved through the linearizer now return the correct
  (different) optimum.
- Goal-programming objective values are 10× larger with the default weights because
  priority 1 now weighs `1e6`. The ranking of priorities is unchanged; the optimal plan is
  usually the same.
- `enable_linearization()` now linearizes. Models that were linearized by hand are not
  linearized twice: `needs_linearization()` is false for them.
- Expressions built by adding expressions (or repeated `add_term` calls) on the same variable
  now contain all of their terms; models that silently lost terms will change.

## [0.1.1] - 2025-01-XX

### Added
- Production planning tutorial with comprehensive documentation
- What-if analysis support for production planning scenarios
- Large-scale timetabling with room type constraints (Step 4)
- Comprehensive documentation for goal_programming module
- Comprehensive documentation for analysis module
- AUTHORS file with core team members
- CITATION.cff for academic citation support

### Changed
- Enhanced documentation structure and content
- Updated README.md with improved examples and project information

### Fixed
- Various documentation improvements and corrections

## [0.1.0] - Initial Release

### Added
- Core model building functionality with type-safe API
- Support for multiple solver backends:
  - OR-Tools (CP-SAT, SCIP)
  - Gurobi
  - CPLEX
  - GLPK
  - CBC
- Automatic data-driven modeling capabilities
- Multi-dimensional indexing support
- Goal programming functionality
- Solution analysis tools
- Automatic linearization of non-linear expressions
- Comprehensive type hints for IDE support
- Basic documentation and examples
- Test suite with pytest
- Code quality tools (black, ruff, mypy)

---

## Guidelines for Maintaining This Changelog

### Types of Changes

- **Added** for new features
- **Changed** for changes in existing functionality
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** for vulnerability fixes

### Version Numbers

- **Major version** (X.0.0): Incompatible API changes
- **Minor version** (0.X.0): New functionality in a backward compatible manner
- **Patch version** (0.0.X): Backward compatible bug fixes

### How to Update

When making changes:

1. Add entries under the **[Unreleased]** section
2. When releasing a new version:
   - Change **[Unreleased]** to the version number and date
   - Create a new **[Unreleased]** section at the top
   - Update the links at the bottom of the file
3. Keep entries concise but descriptive
4. Group related changes together
5. Credit contributors when appropriate

### Example Entry Format

```markdown
## [0.2.0] - 2025-02-15

### Added
- New constraint type for special ordered sets (SOS) (#42)
- Support for warm start solutions (@contributor-name)

### Changed
- Improved solver interface performance by 30% (#38)
- Updated dependency versions

### Fixed
- Fixed memory leak in solution extraction (#45)
- Corrected type hints for Variable bounds (#47)

### Security
- Updated dependency X to address CVE-2025-1234
```

### Links

For more information:
- [Keep a Changelog](https://keepachangelog.com/)
- [Semantic Versioning](https://semver.org/)

[Unreleased]: https://github.com/tdelphi1981/LumiX/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/tdelphi1981/LumiX/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/tdelphi1981/LumiX/releases/tag/v0.1.0
