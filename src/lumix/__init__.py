"""
LumiX: A Type-Safe, Data-Driven Optimization Library
========================================================

LumiX is a modern wrapper for optimization solvers (OR-Tools, Gurobi, CPLEX)
that centralizes data-driven modeling with:

- Type-safe, IDE-friendly API with full autocomplete
- Multi-model indexing (Driver x Date x Shift)
- Automatic solution mapping to ORM models
- Automatic linearization of non-linear constraints
- Comprehensive scenario and sensitivity analysis
- What-if analysis for decision support
- Solver capability detection
- Float-to-rational conversion for integer solvers

Quick Start
-----------

    from lumix import LXModel, LXVariable, LXConstraint, LXOptimizer
    from lumix.core import LXLinearExpression

    # Define variables
    production = LXVariable[Product, float]("production")
        .continuous()
        .bounds(lower=0)
        .indexed_by(lambda p: p.id)
        .cost(lambda p: p.unit_cost)
        .from_model(Product)

    # Define constraints
    capacity = LXConstraint[Resource]("capacity")
        .expression(
            LXLinearExpression().sum_over(production)
        )
        .le()
        .rhs(lambda r: r.capacity)
        .from_model(Resource)
        .indexed_by(lambda r: r.id)

    # Build model
    model = LXModel("production_plan")
        .add_variable(production)
        .add_constraint(capacity)
        .maximize(
            LXLinearExpression().add_term(production, lambda p: p.selling_price)
        )

    # Solve
    optimizer = LXOptimizer().use_solver("gurobi")
    solution = optimizer.solve(model)

    print(f"Objective: {solution.objective_value}")
    for product, value in solution.get_mapped(production).items():
        print(f"Produce {value} units of {product.name}")

    # Analysis
    from lumix import LXSensitivityAnalyzer, LXWhatIfAnalyzer

    # Sensitivity analysis
    sens = LXSensitivityAnalyzer(model, solution)
    print(sens.generate_report())

    # What-if analysis
    whatif = LXWhatIfAnalyzer(model, optimizer)
    result = whatif.increase_constraint_rhs("capacity", by=100)
    print(f"Impact: ${result.delta_objective:,.2f}")
"""

__version__ = "0.1.0"

# Core classes
from .core import (
    LXConstraint,
    LXConstraintSense,
    LXLinearExpression,
    LXModel,
    LXNonLinearExpression,
    LXObjectiveSense,
    LXQuadraticExpression,
    LXQuadraticTerm,
    LXVariable,
    LXVarType,
)

# Indexing
from .indexing import LXCartesianProduct, LXIndexDimension

# Linearization
from .linearization import (
    LXLinearizer,
    LXLinearizerConfig,
    LXLinearizationMethod,
    LXNonLinearFunctions,
)

# Nonlinear terms
from .nonlinear import (
    LXAbsoluteTerm,
    LXBilinearTerm,
    LXIndicatorTerm,
    LXMinMaxTerm,
    LXPiecewiseLinearTerm,
)

# Solution
from .solution import LXSolution, LXSolutionMapper

# Solvers
from .solvers import (
    CPLEX_CAPABILITIES,
    GUROBI_CAPABILITIES,
    ORTOOLS_CAPABILITIES,
    LXOptimizer,
    LXSolverCapability,
    LXSolverFeature,
    LXSolverInterface,
)

# Analysis
from .analysis import (
    LXConstraintSensitivity,
    LXScenario,
    LXScenarioAnalyzer,
    LXScenarioModification,
    LXSensitivityAnalyzer,
    LXVariableSensitivity,
    LXWhatIfAnalyzer,
    LXWhatIfChange,
    LXWhatIfResult,
)

# Utils
from .utils import LXModelLogger, LXORMContext, LXORMModel, LXRationalConverter, LXTypedQuery

# Goal Programming
from .goal_programming import (
    LXGoal,
    LXGoalMetadata,
    LXGoalMode,
    LXGoalProgrammingSolver,
    RelaxedConstraint,
    build_sequential_objectives,
    build_weighted_objective,
    combine_objectives,
    extract_custom_objectives,
    get_deviation_var_name,
    priority_to_weight,
    relax_constraint,
    relax_constraints,
    solve_goal_programming,
)

__all__ = [
    # Version
    "__version__",
    # Core
    "LXModel",
    "LXVariable",
    "LXConstraint",
    "LXLinearExpression",
    "LXQuadraticExpression",
    "LXQuadraticTerm",
    "LXNonLinearExpression",
    "LXVarType",
    "LXConstraintSense",
    "LXObjectiveSense",
    # Indexing
    "LXIndexDimension",
    "LXCartesianProduct",
    # Linearization
    "LXLinearizer",
    "LXLinearizerConfig",
    "LXLinearizationMethod",
    "LXNonLinearFunctions",
    # Nonlinear terms
    "LXAbsoluteTerm",
    "LXBilinearTerm",
    "LXIndicatorTerm",
    "LXMinMaxTerm",
    "LXPiecewiseLinearTerm",
    # Solution
    "LXSolution",
    "LXSolutionMapper",
    # Solvers
    "LXOptimizer",
    "LXSolverInterface",
    "LXSolverFeature",
    "LXSolverCapability",
    "ORTOOLS_CAPABILITIES",
    "GUROBI_CAPABILITIES",
    "CPLEX_CAPABILITIES",
    # Analysis
    "LXScenario",
    "LXScenarioAnalyzer",
    "LXScenarioModification",
    "LXSensitivityAnalyzer",
    "LXVariableSensitivity",
    "LXConstraintSensitivity",
    "LXWhatIfAnalyzer",
    "LXWhatIfResult",
    "LXWhatIfChange",
    # Utils
    "LXORMModel",
    "LXORMContext",
    "LXTypedQuery",
    "LXRationalConverter",
    "LXModelLogger",
    # Goal Programming
    "LXGoal",
    "LXGoalMetadata",
    "LXGoalMode",
    "LXGoalProgrammingSolver",
    "RelaxedConstraint",
    "build_sequential_objectives",
    "build_weighted_objective",
    "combine_objectives",
    "extract_custom_objectives",
    "get_deviation_var_name",
    "priority_to_weight",
    "relax_constraint",
    "relax_constraints",
    "solve_goal_programming",
]
