"""OR-Tools solver implementation."""

from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from ortools.linear_solver import pywraplp
except ImportError:
    pywraplp = None  # type: ignore

from ..core.constraints import LXConstraint
from ..core.enums import LXConstraintSense, LXObjectiveSense, LXVarType
from ..core.model import LXModel
from ..core.variables import LXVariable
from ..solution.solution import LXSolution
from .base import LXSolverInterface
from .capabilities import ORTOOLS_CAPABILITIES


class LXORToolsSolver(LXSolverInterface):
    """
    OR-Tools solver implementation for LumiX.

    Supports:
    - Linear Programming (LP)
    - Mixed-Integer Programming (MIP)
    - Binary variables
    - Single and indexed variable families
    - Single and indexed constraint families
    - Multi-model expressions

    TODO: Future improvements:
    - Quadratic objective support (if OR-Tools adds support)
    - SOS1/SOS2 constraints (native OR-Tools support available)
    - Indicator constraints (native OR-Tools support available)
    - Warm start from previous solution
    - Sensitivity analysis (dual values, reduced costs)
    - Parallel solving with threads parameter
    - Advanced solver parameters passthrough
    - Solution pool for MIP problems
    - Custom branching priorities
    - Lazy constraint callbacks (if OR-Tools adds support)
    """

    def __init__(self) -> None:
        """Initialize OR-Tools solver."""
        super().__init__(ORTOOLS_CAPABILITIES)

        if pywraplp is None:
            raise ImportError(
                "OR-Tools is not installed. "
                "Install it with: pip install ortools"
            )

        # Internal state
        self._solver: Optional[pywraplp.Solver] = None
        self._variable_map: Dict[str, Union[Any, Dict[Any, Any]]] = {}
        self._constraint_map: Dict[str, Union[Any, Dict[Any, Any]]] = {}
        self._constraint_list: List[Any] = []

    def build_model(self, model: LXModel) -> pywraplp.Solver:
        """Build an OR-Tools model from the canonical form of ``model``."""
        canon = self._canonicalize(model)
        has_integer = any(v.var_type != LXVarType.CONTINUOUS for v in canon.variables)
        solver_type = "SCIP" if has_integer else "GLOP"
        self._is_mip = has_integer
        self._solver = pywraplp.Solver.CreateSolver(solver_type)
        if self._solver is None:
            raise RuntimeError(f"Failed to create OR-Tools solver ({solver_type})")
        solver = self._solver
        inf = solver.infinity()

        def bound(value: float) -> float:
            return value if math.isfinite(value) else (inf if value > 0 else -inf)

        handles = []
        for v in canon.variables:
            lb, ub = bound(v.lower), bound(v.upper)
            if v.var_type == LXVarType.CONTINUOUS:
                handles.append(solver.NumVar(lb, ub, v.name))
            else:
                handles.append(solver.IntVar(lb, ub, v.name))
        self._variable_map = self._family_map(canon, handles)

        for row in canon.rows:
            lo, hi = {
                LXConstraintSense.LE: (-inf, row.rhs),
                LXConstraintSense.GE: (row.rhs, inf),
                LXConstraintSense.EQ: (row.rhs, row.rhs),
            }[row.sense]
            ct = solver.Constraint(lo, hi, row.name)
            for pos, coeff in row.coeffs.items():
                ct.SetCoefficient(handles[pos], coeff)
            self._register_row(row, ct)

        if canon.sense is not None:
            objective = solver.Objective()
            for pos, coeff in canon.objective.items():
                objective.SetCoefficient(handles[pos], coeff)
            objective.SetOffset(canon.objective_constant)
            if canon.sense == LXObjectiveSense.MAXIMIZE:
                objective.SetMaximization()
            else:
                objective.SetMinimization()
        self._handles = handles
        return solver

    def solve(
        self,
        model: LXModel,
        time_limit: Optional[float] = None,
        gap_tolerance: Optional[float] = None,
        enable_sensitivity: bool = False,
        **solver_params: Any,
    ) -> LXSolution:
        """
        Solve optimization model with OR-Tools.

        Args:
            model: LumiX model to solve
            time_limit: Time limit in seconds (None = no limit)
            gap_tolerance: MIP gap tolerance (None = solver default)
            **solver_params: ``threads`` (number of threads); other names are
                logged and ignored

        Returns:
            Solution object with results
        """
        # Build the model
        solver = self.build_model(model)

        if time_limit is not None:
            solver.SetTimeLimit(int(time_limit * 1000))
        threads = solver_params.pop("threads", None)
        if threads is not None:
            solver.SetNumThreads(int(threads))
        for name in solver_params:
            self.logger.logger.warning(f"Unknown OR-Tools parameter '{name}' ignored")

        start_time = time.time()
        params = self._solver_parameters(gap_tolerance)
        status = solver.Solve(params)
        if status == pywraplp.Solver.INFEASIBLE and not self._is_mip:
            # GLOP's presolve reports some unbounded LPs as infeasible; ask once more.
            params.SetIntegerParam(pywraplp.MPSolverParameters.PRESOLVE,
                                   pywraplp.MPSolverParameters.PRESOLVE_OFF)
            status = solver.Solve(params)
        elif status == pywraplp.Solver.INFEASIBLE and self._is_mip:
            # SCIP reports "infeasible or unbounded" as INFEASIBLE. A model with a
            # feasible point is therefore unbounded.
            if self._has_feasible_point(solver, params):
                status = pywraplp.Solver.UNBOUNDED
        solve_time = time.time() - start_time
        self._stopped_by_time_limit = (status == pywraplp.Solver.NOT_SOLVED
                                       and time_limit is not None)

        # Parse and return solution
        solution = self._parse_solution(model, solver, status, solve_time, enable_sensitivity)

        return solution

    @staticmethod
    def _has_feasible_point(solver: pywraplp.Solver, params: pywraplp.MPSolverParameters) -> bool:
        objective = solver.Objective()
        handles = solver.variables()
        coeffs = [objective.GetCoefficient(v) for v in handles]
        offset, maximize = objective.offset(), objective.maximization()
        objective.Clear()
        try:
            return solver.Solve(params) in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE)
        finally:
            for v, c in zip(handles, coeffs):
                objective.SetCoefficient(v, c)
            objective.SetOffset(offset)
            objective.SetOptimizationDirection(maximize)

    @staticmethod
    def _solver_parameters(gap_tolerance: Optional[float]) -> pywraplp.MPSolverParameters:
        params = pywraplp.MPSolverParameters()
        if gap_tolerance is not None:
            params.SetDoubleParam(pywraplp.MPSolverParameters.RELATIVE_MIP_GAP, gap_tolerance)
        return params

    def get_solver_model(self) -> pywraplp.Solver:
        """
        Get underlying OR-Tools solver for advanced usage.

        Returns:
            OR-Tools Solver instance

        Raises:
            RuntimeError: If model hasn't been built yet

        Examples:
            # Access OR-Tools solver for advanced features
            solver = ortools_solver.get_solver_model()
            solver.EnableOutput()  # Enable solver output
            solver.SetNumThreads(4)  # Set thread count
        """
        if self._solver is None:
            raise RuntimeError(
                "Solver model not built yet. Call build_model() first."
            )
        return self._solver

    # ==================== PRIVATE HELPER METHODS ====================

    def _get_index_key(self, lx_var: LXVariable, instance: Any) -> Any:
        """
        Get index key for a variable instance, handling cartesian products.

        Args:
            lx_var: Variable definition
            instance: Variable instance (data element or tuple for cartesian products)

        Returns:
            Hashable index key
        """
        return lx_var.index_key(instance)

    def _extract_sensitivity_data(
        self,
        model: LXModel,
        solver: pywraplp.Solver,
        status: int,
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Extract sensitivity data (shadow prices and reduced costs) from OR-Tools solution.

        Args:
            model: Original LumiX model
            solver: OR-Tools solver with solution
            status: OR-Tools status code

        Returns:
            Tuple of (shadow_prices, reduced_costs) dictionaries
        """
        shadow_prices: Dict[str, float] = {}
        reduced_costs: Dict[str, float] = {}

        # Sensitivity analysis only available for LP problems with optimal solutions
        # Status 0 = OPTIMAL
        if status != pywraplp.Solver.OPTIMAL:
            return shadow_prices, reduced_costs

        try:
            # OR-Tools provides dual values for linear solvers (GLOP)
            # SCIP (MIP solver) does not provide dual values

            # Extract dual values (shadow prices) for constraints
            try:
                # Map dual values to constraint names
                for lx_constraint in model.constraints:
                    solver_constraints = self._constraint_map.get(lx_constraint.name)

                    if solver_constraints is None:
                        continue

                    if isinstance(solver_constraints, dict):
                        # Indexed constraint family
                        for index_key, constr in solver_constraints.items():
                            ct_name = f"{lx_constraint.name}[{index_key}]"
                            try:
                                shadow_price = constr.dual_value()
                                shadow_prices[ct_name] = shadow_price
                            except Exception:
                                pass
                    else:
                        # Single constraint
                        try:
                            shadow_price = solver_constraints.dual_value()
                            shadow_prices[lx_constraint.name] = shadow_price
                        except Exception:
                            pass

            except Exception as e:
                self.logger.logger.debug(f"Failed to extract dual values: {e}")

            # Extract reduced costs for variables
            try:
                # Map reduced costs to variable names
                for lx_var in model.variables:
                    solver_vars = self._variable_map.get(lx_var.name)

                    if solver_vars is None:
                        continue

                    if isinstance(solver_vars, dict):
                        # Indexed variable family
                        for index_key, var in solver_vars.items():
                            var_name = f"{lx_var.name}[{index_key}]"
                            try:
                                reduced_cost = var.reduced_cost()
                                reduced_costs[var_name] = reduced_cost
                            except Exception:
                                pass
                    else:
                        # Single variable
                        try:
                            reduced_cost = solver_vars.reduced_cost()
                            reduced_costs[lx_var.name] = reduced_cost
                        except Exception:
                            pass

            except Exception as e:
                self.logger.logger.debug(f"Failed to extract reduced costs: {e}")

        except Exception as e:
            self.logger.logger.debug(f"Failed to extract sensitivity data: {e}")

        return shadow_prices, reduced_costs

    def _parse_solution(
        self,
        model: LXModel,
        solver: pywraplp.Solver,
        status: int,
        solve_time: float,
        enable_sensitivity: bool = False,
    ) -> LXSolution:
        """
        Parse OR-Tools solution to LXSolution.

        Args:
            model: Original LumiX model
            solver: OR-Tools solver with solution
            status: Solver status code
            solve_time: Time taken to solve

        Returns:
            LXSolution object
        """
        # Map status codes
        status_map = {
            pywraplp.Solver.OPTIMAL: "optimal",
            pywraplp.Solver.FEASIBLE: "feasible",
            pywraplp.Solver.INFEASIBLE: "infeasible",
            pywraplp.Solver.UNBOUNDED: "unbounded",
            pywraplp.Solver.ABNORMAL: "abnormal",
            pywraplp.Solver.NOT_SOLVED: "not_solved",
        }

        lx_status = status_map.get(status, "unknown")
        if getattr(self, "_stopped_by_time_limit", False):
            lx_status = "time_limit"

        # Extract objective value
        if status in [pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE]:
            obj_value = solver.Objective().Value()
        else:
            obj_value = 0.0

        # Extract variable values
        has_solution = status in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE)
        handles = self._handles
        variables, mapped = self._solution_values(
            lambda pos: handles[pos].solution_value()) if has_solution else ({}, {})

        # Extract sensitivity data if enabled
        shadow_prices: Dict[str, float] = {}
        reduced_costs: Dict[str, float] = {}
        if enable_sensitivity and not self._is_mip:   # SCIP has no duals
            shadow_prices, reduced_costs = self._extract_sensitivity_data(
                model, solver, status
            )

        # Extract solver statistics
        iterations: Optional[int] = None
        nodes: Optional[int] = None

        # TODO: Get iteration count if available
        # OR-Tools doesn't expose iteration count in pywraplp API

        # Create and return solution
        return LXSolution(
            objective_value=obj_value,
            status=lx_status,
            solve_time=solve_time,
            variables=variables,
            mapped=mapped,
            shadow_prices=shadow_prices,
            reduced_costs=reduced_costs,
            gap=None,  # TODO: Extract MIP gap if available
            iterations=iterations,
            nodes=nodes,
        )


__all__ = ["LXORToolsSolver"]
