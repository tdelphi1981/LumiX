"""Base solver interface for LumiX."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Literal, Optional, TypeVar

from typing_extensions import Self

from ..core.model import LXModel
from ..solution.solution import LXSolution
from ..utils.logger import LXModelLogger
from ..utils.orm import LXORMContext
from ..utils.rational import LXRationalConverter
from .capabilities import LXSolverCapability

TModel = TypeVar("TModel")


class LXSolverInterface(ABC, Generic[TModel]):
    """
    Abstract base class for all solver interfaces.

    Provides:
    - Unified API across solvers (OR-Tools, Gurobi, CPLEX)
    - Capability detection
    - Automatic linearization when needed
    - Type-safe solution mapping
    """

    def __init__(self, capability: LXSolverCapability):
        """
        Initialize solver interface.

        Args:
            capability: Solver capability description
        """
        self.capability = capability
        self.logger = LXModelLogger(f"lumix.{capability.name}")

    @abstractmethod
    def build_model(self, model: LXModel[TModel]) -> Any:
        """
        Build solver-specific model from LumiX model.

        Args:
            model: OPtiXNG model

        Returns:
            Solver-specific model object
        """
        pass

    @abstractmethod
    def solve(
        self,
        model: LXModel[TModel],
        time_limit: Optional[float] = None,
        gap_tolerance: Optional[float] = None,
        **solver_params: Any,
    ) -> LXSolution[TModel]:
        """
        Solve the optimization model.

        Args:
            model: LumiX model
            time_limit: Time limit in seconds
            gap_tolerance: MIP gap tolerance
            **solver_params: Additional solver-specific parameters

        Returns:
            Solution object
        """
        pass

    @abstractmethod
    def get_solver_model(self) -> Any:
        """
        Get underlying solver model for advanced usage.

        Returns:
            Solver-specific model object
        """
        pass


class LXOptimizer(Generic[TModel]):
    """
    Main optimizer with full generic support.

    Provides high-level interface to:
    - Select solver
    - Configure rational conversion
    - Enable sensitivity analysis
    - Solve models

    Examples:
        optimizer = LXOptimizer[Product](orm_context)
            .use_solver("gurobi")
            .enable_sensitivity()
            .enable_rational_conversion()

        solution = optimizer.solve(model)
    """

    def __init__(self, orm: Optional[LXORMContext[TModel]] = None):
        """
        Initialize optimizer.

        Args:
            orm: Optional ORM context for data access
        """
        self.orm = orm
        self.solver_name: str = "ortools"
        self.use_rationals: bool = False
        self.enable_sens: bool = False
        self.rational_converter: Optional[LXRationalConverter] = None
        self.logger = LXModelLogger("lumix.optimizer")
        self._solver: Optional[LXSolverInterface[TModel]] = None

    def use_solver(self, name: Literal["ortools", "gurobi", "cplex", "cpsat"], **kwargs) -> Self:
        """
        Set solver with literal type checking.

        Args:
            name: Solver name ("ortools", "gurobi", "cplex", "cpsat")

        Returns:
            Self for chaining
        """
        self.solver_name = name
        self._solver_params = kwargs
        return self

    def enable_rational_conversion(self, max_denom: int = 10000) -> Self:
        """
        Enable float-to-rational conversion.

        Args:
            max_denom: Maximum denominator for rational approximation

        Returns:
            Self for chaining
        """
        self.use_rationals = True
        self.rational_converter = LXRationalConverter(max_denom)
        return self

    def enable_sensitivity(self) -> Self:
        """
        Enable sensitivity analysis.

        Returns:
            Self for chaining
        """
        self.enable_sens = True
        return self

    def solve(self, model: LXModel[TModel], **solver_params: Any) -> LXSolution[TModel]:
        """
        Solve with full type safety.

        Args:
            model: LXModel to solve
            **solver_params: Solver-specific parameters

        Returns:
            Type-safe solution

        Raises:
            ImportError: If solver not installed
            ValueError: If model is invalid
        """
        # Create solver instance (or reuse existing one if already set)
        if self._solver is None:
            self._solver = self._create_solver()

        # Log model info
        self.logger.log_model_creation(
            model.name, len(model.variables), len(model.constraints)
        )

        # Solve
        self.logger.log_solve_start(self.solver_name)
        solution = self._solver.solve(model, **solver_params)
        self.logger.log_solve_end(solution.status, solution.objective_value, solution.solve_time)

        return solution

    def _create_solver(self) -> LXSolverInterface[TModel]:
        """
        Create solver instance based on configured solver name.

        Returns:
            Solver interface instance

        Raises:
            ImportError: If solver not available
        """
        if self.solver_name == "ortools":
            from .ortools_solver import LXORToolsSolver

            return LXORToolsSolver()
        elif self.solver_name == "gurobi":
            from .gurobi_solver import LXGurobiSolver

            return LXGurobiSolver()
        elif self.solver_name == "cplex":
            from .cplex_solver import LXCPLEXSolver

            return LXCPLEXSolver()
        elif self.solver_name == "cpsat":
            from .cpsat_solver import LXCPSATSolver

            # Pass rational conversion settings to CP-SAT
            rational_max_denom = 10000  # default
            if self.rational_converter is not None:
                rational_max_denom = self.rational_converter.max_denominator

            return LXCPSATSolver(
                enable_rational_conversion=self.use_rationals,
                rational_max_denom=rational_max_denom
            )
        else:
            raise ValueError(f"Unknown solver: {self.solver_name}")


__all__ = ["LXSolverInterface", "LXOptimizer"]
