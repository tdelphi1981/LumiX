# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- CONTRIBUTING.md with comprehensive development guidelines
- CODE_OF_CONDUCT.md with academic-focused community standards
- SECURITY.md with vulnerability reporting policy
- This CHANGELOG.md to track project changes

### Changed

### Deprecated

### Removed

### Fixed

### Security

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
