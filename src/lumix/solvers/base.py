"""Base solver interface for LumiX."""

import hashlib
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Generic, List, Literal, Optional, Tuple, TypeVar

from typing_extensions import Self

from ..core.canonical import LXCanonicalBuilder, LXCanonicalModel, LXInstanceCache
from ..core.expressions import LXQuadraticExpression
from ..core.model import LXModel
from ..linearization.config import LXLinearizerConfig
from ..solution.solution import LXSolution
from ..utils.logger import LXModelLogger
from ..utils.orm import LXORMContext
from ..utils.rational import LXRationalConverter
from .capabilities import LXSolverCapability

TModel = TypeVar("TModel")


def native_name(name: Any, limit: int = 255) -> str:
    """A name every solver accepts for ``name``.

    Control characters become ``_`` and a name longer than ``limit`` bytes is cut and
    ends in a hash of the full name, so distinct names stay distinct. GLPK aborts the
    process on such names and Gurobi raises; the names are only labels, LumiX never
    reads them back.
    """
    text = "".join(ch if ch.isprintable() else "_" for ch in str(name))
    if len(text.encode("utf-8")) <= limit:
        return text
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]
    head = text.encode("utf-8")[: limit - len(digest) - 1].decode("utf-8", "ignore")
    return f"{head}~{digest}"


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
        self._instance_cache = LXInstanceCache()

    # ---- canonical build helpers (0.3.0) ----------------------------------
    def _canonicalize(self, model: LXModel) -> LXCanonicalModel:
        """Canonical form of ``model`` for this build; resets per-build state."""
        self._reset_instance_cache()
        self._constraint_map = {}
        self._constraint_list = []
        self._canonical = LXCanonicalBuilder(model, self._instance_cache).build()
        if self._canonical.objective_nonlinear:
            raise ValueError(
                "The objective has nonlinear terms; call LXOptimizer().enable_linearization() "
                "or LXLinearizer(...).linearize_model() before solving")
        if self._canonical.objective_quadratic and not self.capability.can_solve_quadratic():
            raise ValueError(
                f"{self.capability.name} has no quadratic objective; call "
                "enable_linearization() to turn the products into linear constraints, or "
                "use 'gurobi' or 'cplex'")
        return self._canonical

    @staticmethod
    def _family_map(canon: LXCanonicalModel, handles: List[Any]) -> Dict[str, Dict[Any, Any]]:
        """``{family: {index_key: solver handle}}``; empty families map to ``{}``
        and a scalar variable maps directly to its handle (0.2 shape)."""
        return {family: (handles[keys[None]] if family in canon.scalar_families
                         else {key: handles[pos] for key, pos in keys.items()})
                for family, keys in canon.families.items()}

    def _register_row(self, row: Any, handle: Any) -> None:
        """Store a row handle in ``_constraint_map`` with the 0.2 shapes:
        ``{name: handle}`` for a single constraint, ``{family: {key: handle}}``
        for an indexed family."""
        if row.indexed:
            self._constraint_map.setdefault(row.family, {})[row.key] = handle
        else:
            self._constraint_map[row.family] = handle
        self._constraint_list.append(handle)

    def _solution_values(self, read: Callable[[int], float]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """``(variables, mapped)`` for LXSolution from a reader of canonical positions."""
        canon = self._canonical
        variables: Dict[str, Any] = {family: {} for family in canon.families}
        for pos, var in enumerate(canon.variables):
            if var.family in canon.scalar_families:
                variables[var.family] = read(pos)
            else:
                variables[var.family][var.key] = read(pos)
        mapped = {family: dict(values) for family, values in variables.items()
                  if family not in canon.scalar_families}
        return variables, mapped

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
        self._solver_params: Dict[str, Any] = {}

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
        self._solver = None
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
        self._solver = None
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
            prefer_sos2: No effect (deprecated in 0.3.0, removed in 0.4.0)
            adaptive_breakpoints: Use adaptive breakpoint generation for PWL (default: True)
            mccormick_tighten_bounds: No effect (deprecated in 0.3.0, removed in 0.4.0)
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
        self._solver = None
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
        self._solver = None
        return self

    def solve(self, model: LXModel[TModel], **solver_params: Any) -> LXSolution[TModel]:
        """
        Solve with full type safety.

        Models with goals are relaxed automatically, without changing ``model``.

        Args:
            model: LXModel to solve
            **solver_params: Solver-specific parameters

        Returns:
            Type-safe solution

        Raises:
            ImportError: If solver not installed
            ValueError: If model is invalid
        """
        from ..goal_programming.view import goal_form, goal_mode_value

        view = goal_form(model)
        if view._goal_programming_prepared and goal_mode_value(view.goal_mode) == "sequential":
            from ..goal_programming.solver import LXGoalProgrammingSolver
            return LXGoalProgrammingSolver(self).solve_sequential(view, **solver_params)
        solution = self._solve_once(view, **solver_params)
        if view._goal_programming_prepared:
            view.populate_goal_deviations(solution)
        return solution

    def _solve_once(self, model: LXModel[TModel], **solver_params: Any) -> LXSolution[TModel]:
        """Solve ``model`` as it is (goals already relaxed), with linearization if enabled."""
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

            linearizer = LXLinearizer(solve_model, self._solver.capability, self.linearizer_config)
            if linearizer.needs_linearization():
                solve_model = linearizer.linearize_model()

        # Solve
        self.logger.log_solve_start(self.solver_name)
        params = {**self._solver_params, **solver_params}
        solution = self._solver.solve(
            solve_model, enable_sensitivity=self.enable_sens, **params
        )
        solution.relaxation = bool(getattr(solve_model, "relaxation_terms", None))
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
        elif self.solver_name == "glpk":
            from .glpk_solver import LXGLPKSolver

            return LXGLPKSolver()
        else:
            raise ValueError(f"Unknown solver: {self.solver_name}")


__all__ = ["LXSolverInterface", "LXOptimizer"]
