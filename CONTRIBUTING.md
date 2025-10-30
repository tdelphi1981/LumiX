# Contributing to LumiX

Thank you for your interest in contributing to LumiX! This document provides guidelines for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Academic Contributions](#academic-contributions)
- [Submitting Changes](#submitting-changes)

## Code of Conduct

This project adheres to a Code of Conduct that all contributors are expected to follow. Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before contributing.

## Getting Started

LumiX is a modern, type-safe Python library for mathematical optimization. Before contributing, please:

1. Read the [README.md](README.md) to understand the project's goals and features
2. Browse existing [issues](https://github.com/tdelphi1981/LumiX/issues) to see what needs help
3. Check the [documentation](https://lumix.readthedocs.io) to understand the API

## Development Setup

### Prerequisites

- Python 3.10 or higher
- pip or uv for package management
- Git for version control

### Setting Up Your Development Environment

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/YOUR-USERNAME/LumiX.git
   cd LumiX
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install development dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Install optional solver backends (as needed):**
   ```bash
   # For OR-Tools support
   pip install -e ".[ortools]"

   # For Gurobi support (requires license)
   pip install -e ".[gurobi]"

   # For CPLEX support (requires license)
   pip install -e ".[cplex]"

   # For all solvers
   pip install -e ".[all]"
   ```

5. **Verify your installation:**
   ```bash
   pytest tests/
   ```

## How to Contribute

### Reporting Bugs

Before submitting a bug report:
- Check if the issue already exists
- Ensure you're using the latest version
- Verify the issue is reproducible

When reporting bugs, include:
- Python version and operating system
- LumiX version
- Solver backend(s) being used
- Minimal reproducible example
- Full error traceback

### Suggesting Features

We welcome feature suggestions! Please:
- Check if the feature has already been requested
- Clearly describe the use case and benefits
- Consider academic/research applications
- Provide examples of how the feature would be used

### Contributing Code

1. **Choose or create an issue** to work on
2. **Comment on the issue** to let others know you're working on it
3. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **Make your changes** following our coding standards
5. **Write or update tests** for your changes
6. **Update documentation** as needed
7. **Submit a pull request**

## Coding Standards

LumiX uses modern Python best practices with strict type checking.

### Code Style

- **Formatter:** [Black](https://black.readthedocs.io/) (line length: 88)
  ```bash
  black src/ tests/
  ```

- **Linter:** [Ruff](https://github.com/astral-sh/ruff)
  ```bash
  ruff check src/ tests/
  ```

- **Type Checker:** [mypy](http://mypy-lang.org/) (strict mode)
  ```bash
  mypy src/
  ```

### Type Hints

- All public functions and methods must have complete type hints
- Use modern Python 3.10+ syntax (`list[int]` instead of `List[int]`)
- Generic types should be properly parameterized
- Avoid using `Any` unless absolutely necessary

Example:
```python
def solve_model(
    model: Model,
    solver: SolverType = SolverType.CBC,
    time_limit: float | None = None,
) -> Solution:
    """Solve the optimization model.

    Args:
        model: The optimization model to solve
        solver: The solver backend to use
        time_limit: Maximum solving time in seconds

    Returns:
        The solution object containing results
    """
    ...
```

### Code Organization

- Keep modules focused and cohesive
- Follow the existing directory structure in `src/lumix/`
- Avoid circular dependencies
- Use appropriate access modifiers (leading underscore for private)

## Testing Guidelines

### Writing Tests

- Place tests in the `tests/` directory mirroring `src/lumix/` structure
- Use pytest for all tests
- Aim for high code coverage (target: 80%+)
- Test both success cases and error handling
- Include edge cases and boundary conditions

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/lumix --cov-report=html

# Run specific test file
pytest tests/test_core/test_model.py

# Run tests for specific solver
pytest -m "solver_ortools"
```

### Test Organization

```python
import pytest
from lumix import Model, Variable

def test_variable_creation():
    """Test basic variable creation."""
    model = Model("test")
    x = model.add_var("x", lb=0, ub=10)
    assert x.name == "x"
    assert x.lb == 0
    assert x.ub == 10

def test_invalid_bounds():
    """Test that invalid bounds raise an error."""
    model = Model("test")
    with pytest.raises(ValueError):
        model.add_var("x", lb=10, ub=0)
```

## Documentation

### Docstrings

- Use Google-style docstrings
- Document all public classes, functions, and methods
- Include type information (even though types are in hints)
- Provide examples for complex functionality

### Updating Documentation

- Documentation source is in `docs/source/`
- Built with Sphinx and hosted on ReadTheDocs
- Update relevant `.rst` files when adding features
- Run `make html` in `docs/` to preview changes

## Academic Contributions

### Citation and Attribution

- If your contribution is based on published research, include citations
- Add relevant papers to the documentation bibliography
- Update CITATION.cff if contribution significantly changes the project

### Research Use Cases

- We especially welcome contributions that:
  - Add new solver backends
  - Implement advanced optimization techniques
  - Improve performance for large-scale problems
  - Add domain-specific modeling capabilities
  - Enhance analysis and visualization features

### Examples and Tutorials

- Consider adding examples in `examples/` for new features
- Tutorial contributions to `tutorials/` are highly valued
- Include clear explanations of the mathematical formulation

## Submitting Changes

### Pull Request Process

1. **Ensure all tests pass** and code quality checks succeed:
   ```bash
   black src/ tests/
   ruff check src/ tests/
   mypy src/
   pytest
   ```

2. **Update documentation** as needed

3. **Update CHANGELOG.md** under the "Unreleased" section

4. **Write a clear commit message** following these guidelines:
   - Use the present tense ("Add feature" not "Added feature")
   - Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
   - Limit the first line to 72 characters
   - Reference issues and pull requests

5. **Create a pull request** with:
   - Clear title describing the change
   - Description of what changed and why
   - Reference to related issues (e.g., "Closes #123")
   - Screenshots or examples if applicable

6. **Respond to review feedback** promptly

### Review Criteria

Pull requests will be reviewed for:
- Code quality and adherence to standards
- Test coverage and passing tests
- Documentation completeness
- Backward compatibility (or clear migration path)
- Performance implications
- Alignment with project goals

## Questions?

If you have questions about contributing:

- Open a [discussion](https://github.com/tdelphi1981/LumiX/discussions)
- Email the maintainers:
  - Tolga BERBER (tolga.berber@fen.ktu.edu.tr)
  - Beyzanur SİYAH (beyzanursiyah@ktu.edu.tr)

## License

By contributing to LumiX, you agree that your contributions will be licensed under the [Academic Free License v3.0](LICENSE).

Thank you for contributing to LumiX! Your efforts help make mathematical optimization more accessible to researchers and developers worldwide.
