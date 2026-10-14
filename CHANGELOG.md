# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Deprecated

### Removed

### Fixed

### Security

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
