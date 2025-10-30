<p align="center">
  <img src="docs/source/_static/Lumix_Logo_1024.png" alt="LumiX Logo" width="200"/>
</p>

# LumiX

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-AFL--3.0-green.svg)](https://opensource.org/licenses/AFL-3.0)
[![Documentation](https://img.shields.io/badge/docs-latest-brightgreen.svg)](https://lumix.readthedocs.io)

**A modern, type-safe wrapper for optimization solvers with automatic data-driven modeling**

LumiX makes mathematical programming accessible, maintainable, and enjoyable by providing a unified, type-safe interface to multiple optimization solvers.

## ✨ Key Features

- 🎯 **Type-Safe & IDE-Friendly** — Full type hints and autocomplete support for a superior development experience
- 🔌 **Multi-Solver Support** — Seamlessly switch between OR-Tools, Gurobi, CPLEX, GLPK, and CP-SAT
- 📊 **Data-Driven Modeling** — Build models directly from your data with automatic indexing and mapping
- 🔄 **Automatic Linearization** — Automatically linearize non-linear constraints (bilinear, absolute value, piecewise)
- 📈 **Advanced Analysis** — Built-in sensitivity analysis, scenario analysis, and what-if analysis tools
- 🎯 **Goal Programming** — Native support for multi-objective optimization with priorities and weights
- ⚡ **ORM Integration** — Map solutions directly to your ORM models for seamless data flow

## 🚀 Quick Start

### Installation

```bash
# Install core library
pip install lumix-opt

# Install with a solver (e.g., OR-Tools - free and open-source)
pip install "lumix-opt[ortools]"

# Or install with multiple solvers
pip install "lumix-opt[ortools,gurobi,cplex]"
```

### Simple Example

```python
from dataclasses import dataclass
from lumix import (
    LXModel,
    LXVariable,
    LXConstraint,
    LXLinearExpression,
    LXOptimizer,
)

# Define your data
@dataclass
class Product:
    id: str
    name: str
    profit: float
    resource_usage: float

products = [
    Product("A", "Product A", profit=30, resource_usage=2),
    Product("B", "Product B", profit=40, resource_usage=3),
]

# Define decision variables
production = (
    LXVariable[Product, float]("production")
    .continuous()
    .bounds(lower=0)
    .indexed_by(lambda p: p.id)
    .from_data(products)
)

# Build the model
model = (
    LXModel("production_plan")
    .add_variable(production)
    .maximize(
        LXLinearExpression()
        .add_term(production, lambda p: p.profit)
    )
)

# Add constraints
model.add_constraint(
    LXConstraint("resource_limit")
    .expression(
        LXLinearExpression()
        .add_term(production, lambda p: p.resource_usage)
    )
    .le()
    .rhs(100)  # Resource capacity
)

# Solve
optimizer = LXOptimizer().use_solver("ortools")
solution = optimizer.solve(model)

# Access results
if solution.is_optimal():
    print(f"Optimal profit: ${solution.objective_value:,.2f}")
    for product in products:
        qty = solution.variables["production"][product.id]
        print(f"Produce {qty:.2f} units of {product.name}")
```

## 🔧 Supported Solvers

LumiX provides a unified interface to multiple solvers:

| Solver | Linear | Integer | Quadratic | Advanced Features | License | Best For |
|--------|--------|---------|-----------|-------------------|---------|----------|
| **OR-Tools** | ✓ | ✓ | ✗ | SOS, Indicator | Apache 2.0 (Free) | General LP/MIP, Learning |
| **Gurobi** | ✓ | ✓ | ✓ | SOCP, PWL, Callbacks | Commercial/Academic | Large-scale, Production |
| **CPLEX** | ✓ | ✓ | ✓ | SOCP, PWL, Callbacks | Commercial/Academic | Large-scale, Production |
| **GLPK** | ✓ | ✓ | ✗ | Basic | GPL (Free) | Small problems, Teaching |
| **CP-SAT** | ✗ | ✓ | ✗ | Constraint Programming | Apache 2.0 (Free) | Scheduling, Assignment |

### Switching Solvers

```python
# Just change one line to switch solvers
optimizer = LXOptimizer().use_solver("ortools")   # Free
optimizer = LXOptimizer().use_solver("gurobi")    # Requires license
optimizer = LXOptimizer().use_solver("cplex")     # Requires license
optimizer = LXOptimizer().use_solver("glpk")      # Free
optimizer = LXOptimizer().use_solver("cpsat")     # Free
```

## 📚 Core Capabilities

### Variables with Automatic Indexing

```python
# Single-dimension indexing
production = (
    LXVariable[Product, float]("production")
    .continuous()
    .indexed_by(lambda p: p.id)
    .from_data(products)
)

# Multi-dimension indexing
from lumix import LXCartesianProduct

assignment = (
    LXVariable[tuple[Driver, Date, Shift], int]("assignment")
    .binary()
    .indexed_by(lambda t: (t[0].id, t[1].id, t[2].id))
    .from_data(LXCartesianProduct(drivers, dates, shifts))
)
```

### Type-Safe Expressions

```python
# Linear expressions with automatic coefficient extraction
profit_expr = (
    LXLinearExpression()
    .add_term(production, lambda p: p.profit)
)

# Quadratic expressions
quadratic_expr = (
    LXQuadraticExpression()
    .add_quadratic_term(x, y, coefficient=0.5)
)
```

### Automatic Linearization

LumiX can automatically linearize non-linear terms:

```python
from lumix import LXBilinearTerm, LXAbsoluteTerm, LXPiecewiseLinearTerm

# Bilinear products (x * y)
bilinear = LXBilinearTerm(x, y, bounds_x=(0, 10), bounds_y=(0, 5))

# Absolute values |x|
absolute = LXAbsoluteTerm(x)

# Piecewise-linear functions
piecewise = LXPiecewiseLinearTerm(
    variable=x,
    breakpoints=[0, 10, 20, 30],
    slopes=[1.0, 0.5, 0.2]
)
```

### Advanced Analysis

```python
from lumix import (
    LXSensitivityAnalyzer,
    LXScenarioAnalyzer,
    LXWhatIfAnalyzer,
)

# Sensitivity analysis
sens = LXSensitivityAnalyzer(model, solution)
report = sens.generate_report()
print(report)

# Scenario analysis
scenario_analyzer = LXScenarioAnalyzer(model, optimizer)
scenario_analyzer.add_scenario("base", {})
scenario_analyzer.add_scenario("high_demand", {"demand": 150})
results = scenario_analyzer.solve_all()

# What-if analysis
whatif = LXWhatIfAnalyzer(model, optimizer)
result = whatif.increase_constraint_rhs("capacity", by=10)
print(f"Impact: ${result.delta_objective:,.2f}")
```

### Goal Programming

```python
from lumix import (
    LXGoal,
    LXGoalMode,
    solve_goal_programming,
)

# Define multiple goals with priorities
goals = [
    LXGoal(
        name="profit",
        target=1000,
        priority=1,
        weight=1.0,
        is_minimization=False,
    ),
    LXGoal(
        name="quality",
        target=95,
        priority=2,
        weight=0.8,
    ),
]

# Solve with goal programming
solution = solve_goal_programming(
    model,
    goals,
    mode=LXGoalMode.SEQUENTIAL,
    solver="gurobi",
)
```

## 📖 Documentation

- **[Installation Guide](docs/source/getting-started/installation.rst)** — Install LumiX and solvers
- **[Quick Start](docs/source/getting-started/quickstart.rst)** — Build your first model
- **[Solver Guide](docs/source/getting-started/solvers.rst)** — Choose the right solver
- **[Examples](examples/)** — 11 comprehensive examples

### Examples

The repository includes 11 examples demonstrating various features:

1. **Production Planning** — Single-model indexing, data-driven modeling
2. **Driver Scheduling** — Multi-dimensional indexing, scheduling
3. **Facility Location** — Binary variables, fixed costs
4. **Basic LP** — Simple linear programming
5. **CP-SAT Assignment** — Constraint programming solver
6. **McCormick Bilinear** — Bilinear term linearization
7. **Piecewise Functions** — Piecewise-linear approximations
8. **Scenario Analysis** — Multiple scenario comparison
9. **Sensitivity Analysis** — Parameter sensitivity
10. **What-If Analysis** — Decision support
11. **Goal Programming** — Multi-objective optimization

## 🎯 Why LumiX?

### Before (Traditional Approach)

```python
# Manual indexing, no type safety
x = {}
for i in range(len(products)):
    x[i] = model.addVar(name=f"x_{i}")

# String-based error-prone expressions
model.addConstr(
    sum(x[i] * data[i] for i in range(len(products))) <= capacity
)
```

### After (LumiX)

```python
# Type-safe, data-driven, IDE-friendly
production = (
    LXVariable[Product, float]("production")
    .continuous()
    .indexed_by(lambda p: p.id)
    .from_data(products)
)

model.add_constraint(
    LXConstraint("capacity")
    .expression(
        LXLinearExpression()
        .add_term(production, lambda p: p.usage)
    )
    .le()
    .rhs(capacity)
)
```

**Benefits:**
- ✓ Full IDE autocomplete
- ✓ Type checking catches errors early
- ✓ No manual indexing
- ✓ Data-driven coefficients
- ✓ Readable, maintainable code
- ✓ Easy to refactor

## 🛠️ Development

### Setup Development Environment

```bash
git clone https://github.com/tdelphi1981/LumiX.git
cd LumiX
pip install -e .[dev]
```

### Run Tests

```bash
pytest
```

### Type Checking

```bash
mypy src/lumix
```

### Code Formatting

```bash
black src/lumix
ruff check src/lumix
```

## 📦 Project Structure

```
lumix/
├── src/lumix/
│   ├── core/              # Core model building (variables, constraints, expressions)
│   ├── solvers/           # Solver interfaces (OR-Tools, Gurobi, CPLEX, GLPK, CP-SAT)
│   ├── analysis/          # Analysis tools (sensitivity, scenario, what-if)
│   ├── linearization/     # Automatic linearization engine
│   ├── goal_programming/  # Goal programming support
│   ├── indexing/          # Multi-dimensional indexing
│   ├── nonlinear/         # Non-linear terms
│   ├── solution/          # Solution handling and mapping
│   └── utils/             # Utilities (logger, ORM, rational converter)
├── examples/              # 11 comprehensive examples
├── tests/                 # Test suite
└── docs/                  # Sphinx documentation
```

## 🤝 Contributing

Contributions are welcome! Please:

1. Open an issue to discuss your idea
2. Fork the repository
3. Create a feature branch
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

LumiX is licensed under the [Academic Free License v3.0](LICENSE).

This is a permissive open-source license that:
- ✓ Allows commercial use
- ✓ Allows modification and distribution
- ✓ Provides patent protection
- ✓ Is OSI-approved

## 🙏 Acknowledgments

LumiX builds upon the excellent work of:

- [OR-Tools](https://developers.google.com/optimization) by Google
- [Gurobi](https://www.gurobi.com/) Optimization
- [CPLEX](https://www.ibm.com/products/ilog-cplex-optimization-studio) by IBM
- [GLPK](https://www.gnu.org/software/glpk/) by GNU

## 📞 Support

- **Documentation**: https://lumix.readthedocs.io
- **Issues**: https://github.com/tdelphi1981/LumiX/issues
- **Discussions**: https://github.com/tdelphi1981/LumiX/discussions

## 🗺️ Roadmap

- [ ] Additional solver support (HiGHS, SCIP)
- [ ] Jupyter notebook integration
- [ ] Interactive visualization tools
- [ ] Cloud solver integration
- [ ] Extended ORM support (SQLAlchemy, Django)
- [ ] Advanced constraint programming features
- [ ] Parallel scenario evaluation
- [ ] Model versioning and serialization

## Authors

This project is maintained by:

- **Tolga BERBER** - tolga.berber@fen.ktu.edu.tr
- **Beyzanur SİYAH** - beyzanursiyah@ktu.edu.tr

For a complete list of contributors, see [AUTHORS](AUTHORS).

---

**Made with ❤️ by the LumiX Contributors**
