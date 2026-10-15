# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

### Changed
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
- Absolute values, min and max that the plain epigraph form cannot represent exactly (a maximized `|x|`, a negative weight, a minimized `min`, a maximized `max`, `>=` and `==` rows) get binary variables and are exact; they need finite bounds on their variables (else `ValueError`).
- Products: binary × bounded variable and integer × (integer or continuous) are exact (the integer factor is expanded in binary digits, limited by `LXLinearizerConfig.binary_expansion_bits`); binary × unbounded uses `big_m_value` with a `UserWarning`; continuous × continuous uses McCormick envelopes with a `UserWarning` and sets `solution.relaxation`.
- With `enable_linearization()`, quadratic objectives on OR-Tools, GLPK and CP-SAT are linearized with the same product rules (families, integer and continuous factors included); on Gurobi and CPLEX they stay native.
- `linearize_model()` never modifies the user's model and starts afresh on every call. Auxiliary variables are families `aux_<kind>_<vars>_<n>_<role>` indexed by the instance keys of their term; their values appear per instance in `solution.variables`.
- Indicator Big-M constants are computed from the bounds of the expression; `big_m_value` is used (with a `UserWarning`) only when the expression is unbounded. An indicator's binary must be a single variable.
- Adaptive piecewise breakpoints are deterministic (quantiles of the curvature mixed with a uniform density) and exactly `num_segments + 1`; a linear function gets uniform breakpoints.
- `num_segments`, `adaptive` and `method` of `add_piecewise`, `LXPiecewiseLinearTerm` and `LXPiecewiseLinearizer.approximate_function` default to `None` and are taken from `LXLinearizerConfig` (`pwl_num_segments`, `adaptive_breakpoints`, `pwl_method`); values given on the term win.
- `LXBilinearLinearizer.linearize_bilinear` and `LXPiecewiseLinearizer.approximate_function` take single variables (a scalar or a one-instance family).

### Deprecated
- `LXLinearizerConfig` fields `default_method`, `tolerance`, `verbose_logging`, `prefer_sos2`, `auto_detect_bounds` and `mccormick_tighten_bounds` have no effect and issue a `DeprecationWarning` when set to a non-default value; so do the `prefer_sos2` and `mccormick_tighten_bounds` arguments of `enable_linearization()`. They will be removed in 0.4.0.

### Removed

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

### Security

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
