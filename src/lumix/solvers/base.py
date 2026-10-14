"""Base solver interface for LumiX."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Literal, Optional, Tuple, TypeVar

from typing_extensions import Self

from ..core.expressions import LXKeyFilter
from ..core.model import LXModel
from ..linearization.config import LXLinearizerConfig
from ..solution.solution import LXSolution
from ..utils.logger import LXModelLogger
from ..utils.orm import LXORMContext
from ..utils.rational import LXRationalConverter
from .capabilities import LXSolverCapability

TModel = TypeVar("TModel")


def _accept_all(*instance: Any) -> bool:
    """Filter used for terms whose instances were already selected by key."""
    return True


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

    def _reset_instance_cache(self) -> None:
        """Forget cached variable instances. Adapters call this at the start of
        every ``build_model`` so data changed between solves is picked up."""
        # Keyed by id(): two distinct LXVariable objects may share a name.
        # The model keeps every variable object alive for the whole build.
        self._instance_cache: Dict[int, List[Any]] = {}
        self._key_positions: Dict[int, Dict[Any, List[int]]] = {}

    def _candidates(
        self, lx_var: Any, where_func: Any, constraint_instance: Any = None
    ) -> Tuple[List[Any], Any]:
        """
        Instances of ``lx_var`` that a term has to examine, in instance order.

        ``get_instances()`` runs once per variable family per build instead of
        once per constraint row. When ``constraint_instance`` is one of the
        family's instances (a data-driven constraint over the variable's own
        type), the row is narrowed to that instance and ``where_func`` still
        decides whether it is included. For an
        :class:`~lumix.core.expressions.LXKeyFilter` only the instances whose
        index key is in the filter are returned, looked up through a key index,
        so the work per row is proportional to the number of keys rather than
        to the size of the family. The order is the instance order, which makes
        ``keys=`` build exactly the same model as the equivalent ``where``.

        Returns:
            ``(instances, where_func)``. For a key-filter lookup the returned
            filter accepts everything, because the instances were already
            selected by key; otherwise ``where_func`` is returned unchanged.
        """
        if not hasattr(self, "_instance_cache"):
            self._reset_instance_cache()
        slot = id(lx_var)
        instances = self._instance_cache.get(slot)
        if instances is None:
            instances = lx_var.get_instances()
            self._instance_cache[slot] = instances
        if constraint_instance is not None and constraint_instance in instances:
            return [constraint_instance], where_func
        if not isinstance(where_func, LXKeyFilter):
            return instances, where_func
        positions = self._key_positions.get(slot)
        if positions is None:
            positions = {}
            for i, instance in enumerate(instances):
                positions.setdefault(lx_var.index_key(instance), []).append(i)
            self._key_positions[slot] = positions
        hits = sorted(i for key in where_func.keys for i in positions.get(key, ()))
        return [instances[i] for i in hits], _accept_all

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
        self.use_linearization: bool = False
        self.rational_converter: Optional[LXRationalConverter] = None
        self.linearizer_config: Optional[LXLinearizerConfig] = None
        self.logger = LXModelLogger("lumix.optimizer")
        self._solver: Optional[LXSolverInterface[TModel]] = None

    def use_solver(self, name: Literal["ortools", "gurobi", "cplex", "cpsat", "glpk"], **kwargs) -> Self:
        """
        Set solver with literal type checking.

        Args:
            name: Solver name ("ortools", "gurobi", "cplex", "cpsat", "glpk")

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

    def enable_linearization(
        self,
        big_m: float = 1e6,
        pwl_segments: int = 20,
        pwl_method: Literal["sos2", "incremental", "logarithmic"] = "sos2",
        prefer_sos2: bool = True,
        adaptive_breakpoints: bool = True,
        mccormick_tighten_bounds: bool = True,
        **kwargs: Any,
    ) -> Self:
        """
        Enable automatic linearization for nonlinear terms.

        Mirrors enable_rational_conversion() API pattern for consistency.

        When enabled, the optimizer will automatically:

        - Detect nonlinear terms in the model
        - Check if solver lacks native support
        - Apply appropriate linearization techniques:

            - Binary × Binary: AND logic
            - Binary × Continuous: Big-M method
            - Continuous × Continuous: McCormick envelopes
            - Piecewise-linear approximations for exp, log, sin, cos, etc.

        Args:
            big_m: Big-M constant for conditional constraints (default: 1e6)
            pwl_segments: Number of segments for piecewise-linear approximations (default: 20)
            pwl_method: Method for PWL ("sos2", "incremental", "logarithmic")
            prefer_sos2: Use SOS2 formulation when solver supports it (default: True)
            adaptive_breakpoints: Use adaptive breakpoint generation for PWL (default: True)
            mccormick_tighten_bounds: Apply bound tightening for McCormick envelopes (default: True)
            **kwargs: Additional linearization configuration options

        Returns:
            Self for chaining

        Example::

            optimizer = (
                LXOptimizer[Product]()
                .use_solver("ortools")
                .enable_linearization(
                    big_m=1e5,
                    pwl_segments=30,
                    adaptive_breakpoints=True
                )
            )

            solution = optimizer.solve(model)
        """
        self.use_linearization = True
        self.linearizer_config = LXLinearizerConfig(
            big_m_value=big_m,
            pwl_num_segments=pwl_segments,
            pwl_method=pwl_method,
            prefer_sos2=prefer_sos2,
            adaptive_breakpoints=adaptive_breakpoints,
            mccormick_tighten_bounds=mccormick_tighten_bounds,
            **kwargs,
        )
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

        # Linearize nonlinear terms the solver cannot handle natively
        solve_model = model
        if self.use_linearization:
            from ..linearization.engine import LXLinearizer

            linearizer = LXLinearizer(model, self._solver.capability, self.linearizer_config)
            if linearizer.needs_linearization():
                solve_model = linearizer.linearize_model()

        # Solve
        self.logger.log_solve_start(self.solver_name)
        solution = self._solver.solve(
            solve_model, enable_sensitivity=self.enable_sens, **solver_params
        )
        self.logger.log_solve_end(solution.status, solution.objective_value, solution.solve_time)

        # Populate goal deviations if model has prepared goal programming
        if (hasattr(model, 'populate_goal_deviations') and
            hasattr(model, '_goal_programming_prepared') and
            model._goal_programming_prepared):
            model.populate_goal_deviations(solution)

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
        elif self.solver_name == "glpk":
            from .glpk_solver import LXGLPKSolver

            return LXGLPKSolver()
        else:
            raise ValueError(f"Unknown solver: {self.solver_name}")


__all__ = ["LXSolverInterface", "LXOptimizer"]
