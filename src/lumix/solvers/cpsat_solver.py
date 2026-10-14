"""OR-Tools CP-SAT solver implementation for LumiX."""

from __future__ import annotations

import math
import time
from fractions import Fraction
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from ortools.sat.python import cp_model
except ImportError:
    cp_model = None  # type: ignore

from ..core.constraints import LXConstraint
from ..core.enums import LXConstraintSense, LXObjectiveSense, LXVarType
from ..core.model import LXModel
from ..solution.solution import LXSolution
from ..utils.rational import LXRationalConverter
from .base import LXSolverInterface
from .capabilities import CPSAT_CAPABILITIES


class LXCPSATSolver(LXSolverInterface):
    """
    OR-Tools CP-SAT (Constraint Programming - Satisfiability) solver implementation for LumiX.

    CP-SAT is a constraint programming solver optimized for:
    - Scheduling problems
    - Routing problems (TSP, VRP)
    - Combinatorial optimization
    - Integer and boolean decision problems

    IMPORTANT: CP-SAT only supports INTEGER and BINARY variables (no continuous variables).
    Float coefficients are automatically converted to integers using rational approximation.

    Supports:
    - Integer variables (bounded or unbounded)
    - Binary (boolean) variables
    - Linear constraints (≤, ≥, ==)
    - Single and indexed variable families
    - Multi-model expressions
    - Automatic float-to-rational conversion

    TODO: Future CP-SAT-specific features:
    - AllDifferent constraints for scheduling
    - Circuit constraints for routing/TSP
    - Table constraints for allowed combinations
    - Interval variables for scheduling
    - NoOverlap constraints for resource scheduling
    - Cumulative constraints for resource capacity
    - Boolean logic constraints (OR, AND, XOR, implications)
    - Solution pool for multiple optimal solutions
    - Warm start via solution hints
    - Custom search strategies
    - Symmetry breaking
    """

    #: Bound used for an open variable bound (CP-SAT domains must stay well inside int64).
    OPEN_BOUND = 2**40

    def __init__(
        self,
        enable_rational_conversion: bool = False,
        rational_max_denom: int = 10000,
        scale_objective: bool = True,
        scaling_factor: int = 1000,
    ) -> None:
        """
        Initialize CP-SAT solver.

        Args:
            enable_rational_conversion: Enable rational conversion and auto-scaling for continuous variables
            rational_max_denom: Maximum denominator for float-to-rational conversion
            scale_objective: Whether to scale objective coefficients to integers
            scaling_factor: Scaling factor for continuous variables (default: 1000)
                Higher values = more precision but risk integer overflow
        """
        super().__init__(CPSAT_CAPABILITIES)

        if cp_model is None:
            raise ImportError(
                "OR-Tools is not installed. "
                "Install it with: pip install ortools"
            )

        # Internal state
        self._model: Optional[cp_model.CpModel] = None
        self._variable_map: Dict[str, Union[Any, Dict[Any, Any]]] = {}
        self._constraint_list: List[Any] = []
        self._rational_converter = LXRationalConverter(max_denominator=rational_max_denom)
        self._enable_rational_conversion = enable_rational_conversion
        self._scaling_factor = scaling_factor
        self._max_denom = rational_max_denom
        self._scale_objective = scale_objective   # kept for API compatibility; no effect since 0.3.0
        self._handles: List[Any] = []
        self._scales: List[int] = []
        self._open: List[int] = []
        self._objective_scale = 1
        self._objective_constant = 0.0
        self._has_objective = False
        self._approximate = False
        self._approximation_error = 0.0

    def build_model(self, model: LXModel) -> cp_model.CpModel:
        """Build a CP-SAT model from the canonical form of ``model``. Every row and
        the objective are scaled to integers exactly (see ``_integer_row``)."""
        canon = self._canonicalize(model)
        self._approximation_error = 0.0
        continuous = sorted({v.family for v in canon.variables
                             if v.var_type == LXVarType.CONTINUOUS})
        if continuous and not self._enable_rational_conversion:
            raise ValueError(
                f"CP-SAT does not support continuous variables. "
                f"Found continuous variables: {', '.join(continuous)}.\n"
                f"Options:\n"
                f"  1. Use integer/binary variables only\n"
                f"  2. Switch to 'ortools', 'gurobi', or 'cplex' solvers\n"
                f"  3. Enable rational conversion: optimizer.enable_rational_conversion()\n"
                f"     This will scale continuous variables to integers and de-scale solutions."
            )
        if continuous:
            self._log_scaling_warning(continuous)

        self._model = cp_model.CpModel()
        cm = self._model
        self._handles, self._scales, self._open = [], [], []
        for pos, v in enumerate(canon.variables):
            scale = self._scaling_factor if v.var_type == LXVarType.CONTINUOUS else 1
            lo = self._int_bound(v.lower * scale, math.ceil, pos)
            hi = self._int_bound(v.upper * scale, math.floor, pos)
            if lo > hi:
                raise ValueError(f"Variable '{v.name}' has no value on the CP-SAT grid "
                                 f"1/{scale} within [{v.lower}, {v.upper}]")
            if v.var_type == LXVarType.BINARY and (lo, hi) == (0, 1):
                handle = cm.NewBoolVar(v.name)
            else:
                handle = cm.NewIntVar(lo, hi, v.name)
            self._handles.append(handle)
            self._scales.append(scale)
        self._variable_map = self._family_map(canon, self._handles)

        for row in canon.rows:
            ints, rhs, _ = self._integer_row(row.coeffs, row.rhs, f"constraint '{row.name}'")
            expr = self._expr(ints)
            if row.sense == LXConstraintSense.LE:
                ct = cm.Add(expr <= rhs)
            elif row.sense == LXConstraintSense.GE:
                ct = cm.Add(expr >= rhs)
            else:
                ct = cm.Add(expr == rhs)
            ct.with_name(row.name)
            self._register_row(row, ct)

        self._objective_constant = canon.objective_constant
        self._has_objective = canon.sense is not None and bool(canon.objective)
        self._objective_scale = 1
        if self._has_objective:
            ints, _, self._objective_scale = self._integer_row(canon.objective, 0.0, "the objective")
            if canon.sense == LXObjectiveSense.MAXIMIZE:
                cm.Maximize(self._expr(ints))
            else:
                cm.Minimize(self._expr(ints))

        if self._approximation_error:
            self.logger.logger.warning(
                f"CP-SAT: coefficients approximated with denominators up to {self._max_denom} "
                f"(largest relative error {self._approximation_error:.2e})")
        problem = cm.Validate()
        if problem:
            raise ValueError(f"CP-SAT rejected the model: {problem}")
        return cm

    def _int_bound(self, value: float, rounding: Any, pos: int) -> int:
        if math.isfinite(value):
            return int(rounding(value - 1e-9 if rounding is math.ceil else value + 1e-9))
        self._open.append(pos)
        return self.OPEN_BOUND if value > 0 else -self.OPEN_BOUND

    def _expr(self, ints: Dict[int, int]) -> Any:
        if not ints:
            return self._model.NewConstant(0)
        return cp_model.LinearExpr.WeightedSum([self._handles[p] for p in ints], list(ints.values()))

    def _fraction(self, value: float, what: str) -> Fraction:
        frac = Fraction(value).limit_denominator(self._max_denom)
        if value == 0:
            return frac
        error = abs(float(frac) - value) / max(1.0, abs(value))
        if frac != 0 and error <= 1e-9:
            return frac
        if self._approximate and frac != 0:
            self._approximation_error = max(self._approximation_error, error)
            return frac
        raise ValueError(
            f"CP-SAT cannot represent {value!r} in {what} with denominators up to "
            f"{self._max_denom}; pass approximate_coefficients=True to solve() or "
            "use_solver('cpsat', ...) to accept an approximation, raise "
            "enable_rational_conversion(max_denom=...), or use a linear solver "
            "('ortools', 'gurobi', 'cplex', 'glpk')"
        )

    def _integer_row(self, coeffs: Dict[int, float], rhs: float,
                     what: str) -> Tuple[Dict[int, int], int, int]:
        """Exact integer form of ``sum(c * x) <sense> rhs`` on the CP-SAT variables
        (``x_cpsat = x * scale``): every value becomes a fraction and the row is
        multiplied by the LCM of the denominators, right-hand side included."""
        fracs = {pos: self._fraction(c, what) / self._scales[pos] for pos, c in coeffs.items()}
        rhs_frac = self._fraction(rhs, what)
        scale = math.lcm(rhs_frac.denominator, *(f.denominator for f in fracs.values()))
        ints = {pos: int(f * scale) for pos, f in fracs.items()}
        return ints, int(rhs_frac * scale), scale

    def solve(
        self,
        model: LXModel,
        time_limit: Optional[float] = None,
        gap_tolerance: Optional[float] = None,
        enable_sensitivity: bool = False,
        approximate_coefficients: bool = False,
        **solver_params: Any,
    ) -> LXSolution:
        """
        Solve optimization model with CP-SAT.

        Args:
            model: LumiX model to solve
            time_limit: Time limit in seconds (None = no limit)
            gap_tolerance: Relative optimality gap tolerance (None = 0.0001)
            enable_sensitivity: Accepted for API symmetry; CP-SAT has no sensitivity data
            approximate_coefficients: Accept coefficients that ``max_denom`` cannot
                represent within a relative error of 1e-9, using the nearest fraction
                (a warning reports the largest error). Default: raise ``ValueError``.
            **solver_params: Additional CP-SAT parameters
                Examples:
                - num_search_workers: Number of parallel workers (default: auto)
                - log_search_progress: Enable search logging (default: False)
                - max_time_in_seconds: Alternative to time_limit
                - cp_model_presolve: Enable presolve (default: True)
                - linearization_level: Linearization aggressiveness (0-2)
                - cp_model_probing_level: Probing level (0-2)

        Returns:
            Solution object with results

        TODO: Add support for additional features:
            - Solution hints (warm start)
            - Solution callbacks
            - Assumption-based solving
            - Multiple solutions enumeration
        """
        if enable_sensitivity:
            self.logger.logger.info("CP-SAT provides no sensitivity data")
        self._approximate = approximate_coefficients
        cpsat_model = self.build_model(model)

        # Create solver instance
        solver = cp_model.CpSolver()

        # Set time limit
        if time_limit is not None:
            solver.parameters.max_time_in_seconds = time_limit

        # Set relative gap tolerance
        if gap_tolerance is not None:
            solver.parameters.relative_gap_limit = gap_tolerance

        # Set additional solver parameters
        for param_name, param_value in solver_params.items():
            try:
                if param_name == "num_search_workers":
                    solver.parameters.num_search_workers = param_value
                elif param_name == "log_search_progress":
                    solver.parameters.log_search_progress = param_value
                elif param_name == "max_time_in_seconds":
                    solver.parameters.max_time_in_seconds = param_value
                elif param_name == "cp_model_presolve":
                    solver.parameters.cp_model_presolve = param_value
                elif param_name == "linearization_level":
                    solver.parameters.linearization_level = param_value
                elif param_name == "cp_model_probing_level":
                    solver.parameters.cp_model_probing_level = param_value
                else:
                    # Try to set as generic parameter
                    setattr(solver.parameters, param_name, param_value)
            except Exception as e:
                self.logger.logger.warning(
                    f"Failed to set CP-SAT parameter '{param_name}': {e}"
                )

        # Solve
        start_time = time.time()
        status = solver.Solve(cpsat_model)
        solve_time = time.time() - start_time

        # Parse and return solution
        solution = self._parse_solution(model, solver, status, solve_time)

        return solution

    def get_solver_model(self) -> cp_model.CpModel:
        """
        Get underlying CP-SAT model for advanced usage.

        Returns:
            CP-SAT CpModel instance

        Raises:
            RuntimeError: If model hasn't been built yet

        Examples:
            # Access CP-SAT model for advanced features
            cpsat_model = solver.get_solver_model()
            # Add custom CP-SAT constraints
            cpsat_model.AddAllDifferent([var1, var2, var3])
        """
        if self._model is None:
            raise RuntimeError(
                "Solver model not built yet. Call build_model() first."
            )
        return self._model

    # ==================== PRIVATE HELPER METHODS ====================

    def _log_scaling_warning(self, continuous_vars: List[str]) -> None:
        """Log warning about rational conversion auto-scaling."""
        self.logger.logger.warning("")
        self.logger.logger.warning("╔════════════════════════════════════════════════════════════╗")
        self.logger.logger.warning("║     CP-SAT: RATIONAL CONVERSION (AUTO-SCALING ENABLED)     ║")
        self.logger.logger.warning("╠════════════════════════════════════════════════════════════╣")
        self.logger.logger.warning(f"║  Variables scaled: {len(continuous_vars):2d}                                        ║")
        self.logger.logger.warning(f"║  Scale factor: {self._scaling_factor:5d}                                      ║")
        self.logger.logger.warning(f"║  Rational max denom: {self._rational_converter.max_denominator:5d}                             ║")
        self.logger.logger.warning("║                                                            ║")
        self.logger.logger.warning("║  Continuous variables will be converted to integers by     ║")
        self.logger.logger.warning("║  multiplying by the scale factor. Solution values will be  ║")
        self.logger.logger.warning("║  automatically de-scaled back to continuous domain.        ║")
        self.logger.logger.warning("║                                                            ║")
        self.logger.logger.warning("║  Note: Small rounding errors may occur due to integer      ║")
        self.logger.logger.warning("║  approximation. For high-precision needs, use a linear     ║")
        self.logger.logger.warning("║  solver ('ortools', 'gurobi', or 'cplex') instead.         ║")
        self.logger.logger.warning("╚════════════════════════════════════════════════════════════╝")
        self.logger.logger.warning("")

    def _parse_solution(
        self,
        model: LXModel,
        solver: cp_model.CpSolver,
        status: int,
        solve_time: float,
    ) -> LXSolution:
        """
        Parse CP-SAT solution to LXSolution.

        Args:
            model: Original LumiX model
            solver: CP-SAT solver with solution
            status: Solver status code
            solve_time: Time taken to solve

        Returns:
            LXSolution object
        """
        # Map status codes
        status_map = {
            cp_model.OPTIMAL: "optimal",
            cp_model.FEASIBLE: "feasible",
            cp_model.INFEASIBLE: "infeasible",
            cp_model.MODEL_INVALID: "model_invalid",
            cp_model.UNKNOWN: "unknown",
        }

        lx_status = status_map.get(status, "unknown")
        has_solution = status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
        variables: Dict[str, Any] = {}
        mapped: Dict[str, Any] = {}
        obj_value = 0.0
        gap: Optional[float] = None
        if has_solution:
            variables, mapped = self._solution_values(
                lambda pos: solver.Value(self._handles[pos]) / self._scales[pos])
            obj_value = self._objective_constant
            if self._has_objective:
                obj_value += solver.ObjectiveValue() / self._objective_scale
                bound = solver.BestObjectiveBound() / self._objective_scale + self._objective_constant
                gap = abs(obj_value - bound) / max(abs(obj_value), 1e-10)
            for pos in self._open:
                if abs(solver.Value(self._handles[pos])) >= self.OPEN_BOUND:
                    var = self._canonical.variables[pos]
                    self.logger.logger.warning(
                        f"Variable '{var.name}' reached the CP-SAT bound ±2^40 used for an open "
                        "bound; the true optimum may lie beyond it")

        # CP-SAT doesn't provide sensitivity analysis
        # TODO: Could compute reduced costs for feasibility/bound analysis
        shadow_prices: Dict[str, float] = {}
        reduced_costs: Dict[str, float] = {}

        # Extract solver statistics
        iterations: Optional[int] = None
        nodes: Optional[int] = None

        # CP-SAT provides branch count and conflict count
        try:
            nodes = solver.NumBranches()
        except Exception:
            pass

        # Create and return solution
        return LXSolution(
            objective_value=obj_value,
            status=lx_status,
            solve_time=solve_time,
            variables=variables,
            mapped=mapped,
            shadow_prices=shadow_prices,
            reduced_costs=reduced_costs,
            gap=gap,
            iterations=iterations,
            nodes=nodes,
        )


__all__ = ["LXCPSATSolver"]
