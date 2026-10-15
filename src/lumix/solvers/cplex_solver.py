"""CPLEX solver implementation for LumiX."""

from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import cplex
    from cplex import Cplex
    from cplex.exceptions import CplexError
except ImportError:
    cplex = None  # type: ignore
    Cplex = None  # type: ignore
    CplexError = Exception  # type: ignore

from ..core.constraints import LXConstraint
from ..core.enums import LXConstraintSense, LXObjectiveSense, LXVarType
from ..core.model import LXModel
from ..core.variables import LXVariable
from ..solution.solution import LXSolution
from ..utils._warn import warn_user
from .base import LXSolverInterface, native_name
from .capabilities import CPLEX_CAPABILITIES


class LXCPLEXSolver(LXSolverInterface):
    """
    CPLEX solver implementation for LumiX.

    Supports:
    - Linear Programming (LP)
    - Mixed-Integer Programming (MIP)
    - Binary variables
    - Single and indexed variable families
    - Single and indexed constraint families
    - Multi-model expressions

    TODO: Future improvements:
    - Quadratic objective support (when library adds support)
    - SOCP support (when library adds support)
    - Warm start from previous solution
    - Sensitivity analysis (dual values, reduced costs)
    - Solution pool for MIP problems
    - Lazy constraint callbacks
    - User cut callbacks
    - IIS computation for infeasible models
    - Conflict refinement
    - SOS1/SOS2 constraints
    - Indicator constraints
    - Piecewise linear functions
    """

    def __init__(self) -> None:
        """Initialize CPLEX solver."""
        super().__init__(CPLEX_CAPABILITIES)

        if cplex is None or Cplex is None:
            raise ImportError(
                "CPLEX is not installed. "
                "Install it with: pip install cplex\n"
                "Note: CPLEX requires a license (free academic licenses available)"
            )

        # Internal state
        self._model: Optional[Cplex] = None
        self._variable_map: Dict[str, Union[int, Dict[Any, int]]] = {}
        self._constraint_map: Dict[str, Union[int, Dict[Any, int]]] = {}
        self._constraint_list: List[int] = []
        self._variable_counter: int = 0
        self._constraint_counter: int = 0

    def build_model(self, model: LXModel) -> Cplex:
        """Build a CPLEX model from the canonical form of ``model``."""
        canon = self._canonicalize(model)
        self._model = Cplex()
        cm = self._model
        cm.set_problem_name(model.name)
        n = len(canon.variables)
        if n:
            kinds = {LXVarType.CONTINUOUS: cm.variables.type.continuous,
                     LXVarType.INTEGER: cm.variables.type.integer,
                     LXVarType.BINARY: cm.variables.type.binary}
            is_mip = any(v.var_type != LXVarType.CONTINUOUS for v in canon.variables)
            args = dict(lb=[v.lower if math.isfinite(v.lower) else -cplex.infinity for v in canon.variables],
                        ub=[v.upper if math.isfinite(v.upper) else cplex.infinity for v in canon.variables],
                        names=[native_name(v.name) for v in canon.variables])
            if is_mip:   # types turn the problem into a MIP; keep pure LPs as LPs
                args["types"] = [kinds[v.var_type] for v in canon.variables]
            cm.variables.add(**args)
        handles = list(range(n))
        self._handles = handles
        self._variable_map = self._family_map(canon, handles)
        senses = {LXConstraintSense.LE: "L", LXConstraintSense.GE: "G", LXConstraintSense.EQ: "E"}
        for row in canon.rows:
            idx = cm.linear_constraints.add(
                lin_expr=[cplex.SparsePair(ind=list(row.coeffs), val=list(row.coeffs.values()))],
                senses=[senses[row.sense]], rhs=[row.rhs], names=[native_name(row.name)])[0]
            self._register_row(row, idx)
        if canon.sense is not None:
            if canon.objective:
                cm.objective.set_linear(list(canon.objective.items()))
            cm.objective.set_offset(canon.objective_constant)
            if canon.objective_quadratic:
                # CPLEX minimizes c'x + 1/2 x'Qx: Q_ii = 2c for c*x_i^2, Q_ij = c for c*x_i*x_j.
                cm.objective.set_quadratic_coefficients(
                    [(i, j, 2 * c if i == j else c) for (i, j), c in canon.objective_quadratic.items()])
                cm.parameters.optimalitytarget.set(3)   # global optimum, also when nonconvex
            cm.objective.set_sense(cm.objective.sense.maximize
                                   if canon.sense == LXObjectiveSense.MAXIMIZE
                                   else cm.objective.sense.minimize)
        return cm

    def solve(
        self,
        model: LXModel,
        time_limit: Optional[float] = None,
        gap_tolerance: Optional[float] = None,
        enable_sensitivity: bool = False,
        **solver_params: Any,
    ) -> LXSolution:
        """
        Solve optimization model with CPLEX.

        Args:
            model: LumiX model to solve
            time_limit: Time limit in seconds (None = no limit)
            gap_tolerance: MIP gap tolerance (None = solver default, typically 0.0001)
            **solver_params: Additional CPLEX-specific parameters
                Examples:
                - threads: Number of parallel threads (int)
                - mip_emphasis: MIP emphasis (0=balanced, 1=feasibility, 2=optimality, 3=bound, 4=hidden)
                - preprocessing_presolve: Presolve level (0=off, 1=on)
                - lpmethod: Algorithm for LP (0=auto, 1=primal, 2=dual, 3=network, 4=barrier)
                - verbose: print the CPLEX log (True/False)
                - any other CPLEX parameter by its path with ``_`` for ``.``,
                  e.g. ``mip_limits_cutsfactor`` for ``parameters.mip.limits.cutsfactor``

        Returns:
            Solution object with results

        TODO: Add support for additional features:
            - Warm start from previous solution
            - Solution pool for MIP
            - Callback functions
        """
        # Build the model
        cplex_model = self.build_model(model)

        # Suppress output unless verbose=True
        if not solver_params.pop("verbose", False):
            cplex_model.set_log_stream(None)
            cplex_model.set_error_stream(None)
            cplex_model.set_warning_stream(None)
            cplex_model.set_results_stream(None)

        # Set time limit
        if time_limit is not None:
            cplex_model.parameters.timelimit.set(time_limit)

        # Set MIP gap tolerance
        if gap_tolerance is not None:
            cplex_model.parameters.mip.tolerances.mipgap.set(gap_tolerance)

        # Set additional solver parameters
        for param_name, param_value in solver_params.items():
            try:
                # Convert snake_case to parameter path
                # e.g., "mip_emphasis" -> parameters.mip.strategy.emphasis
                if param_name == "threads":
                    cplex_model.parameters.threads.set(param_value)
                elif param_name == "mip_emphasis":
                    cplex_model.parameters.mip.strategy.emphasis.set(param_value)
                elif param_name == "preprocessing_presolve":
                    cplex_model.parameters.preprocessing.presolve.set(param_value)
                elif param_name == "lpmethod":
                    cplex_model.parameters.lpmethod.set(param_value)
                elif param_name == "solution_limit":
                    cplex_model.parameters.mip.limits.solutions.set(int(param_value))
                elif param_name == "output_clonelog":
                    cplex_model.parameters.output.clonelog.set(int(param_value))
                else:
                    parameter = self._parameter(cplex_model.parameters, param_name)
                    if parameter is None:
                        self.logger.logger.warning(
                            f"Unknown CPLEX parameter '{param_name}', skipping"
                        )
                    else:
                        parameter.set(param_value)
            except Exception as e:
                self.logger.logger.warning(
                    f"Failed to set CPLEX parameter '{param_name}': {e}"
                )

        # Solve
        start_time = time.time()
        try:
            cplex_model.solve()
            st = cplex_model.solution.status
            code = cplex_model.solution.get_status()
            if code in (st.infeasible_or_unbounded, st.MIP_infeasible_or_unbounded, st.unbounded):
                # Presolve could not tell infeasible from unbounded, or the dual simplex
                # found a ray without a feasible point; ask once more without presolve,
                # with the primal simplex for an LP (its phase 1 proves feasibility).
                cplex_model.parameters.preprocessing.presolve.set(0)
                if code != st.MIP_infeasible_or_unbounded:
                    cplex_model.parameters.lpmethod.set(
                        cplex_model.parameters.lpmethod.values.primal)
                cplex_model.solve()
        except CplexError as e:
            self.logger.logger.error(f"CPLEX solve error: {e}")
            # Continue to parse solution even if error (may have partial solution)
        solve_time = time.time() - start_time

        # Parse and return solution
        solution = self._parse_solution(model, cplex_model, solve_time, enable_sensitivity)

        return solution

    @staticmethod
    def _parameter(parameters: Any, name: str) -> Any:
        """The CPLEX parameter at ``name`` read as a path (``mip_limits_cutsfactor``)."""
        def walk(node: Any, parts: List[str]) -> Any:
            if not parts:
                return node if hasattr(node, "set") else None
            for i in range(len(parts), 0, -1):    # names may contain "_" themselves
                child = getattr(node, "_".join(parts[:i]), None)
                if child is not None:
                    found = walk(child, parts[i:])
                    if found is not None:
                        return found
            return None
        return walk(parameters, name.split("_"))

    @staticmethod
    def _status_name(st: Any, code: int, has_solution: bool) -> str:
        """LumiX status for a CPLEX status code, using CPLEX's named constants."""
        if code in (st.optimal, st.MIP_optimal, st.optimal_tolerance):
            return "optimal"
        if code in (st.infeasible, st.MIP_infeasible):
            return "infeasible"
        if code in (st.unbounded, st.MIP_unbounded):
            return "unbounded"
        if code in (st.infeasible_or_unbounded, st.MIP_infeasible_or_unbounded):
            return "inf_or_unbounded"
        if has_solution:
            return "feasible"
        if code in (st.abort_time_limit, st.MIP_time_limit_infeasible):
            return "time_limit"
        return f"unknown_{code}"

    def get_solver_model(self) -> Cplex:
        """
        Get underlying CPLEX model for advanced usage.

        Returns:
            CPLEX Cplex instance

        Raises:
            RuntimeError: If model hasn't been built yet

        Examples:
            # Access CPLEX model for advanced features
            cplex_model = solver.get_solver_model()
            cplex_model.parameters.threads.set(4)  # Set thread count
            cplex_model.parameters.timelimit.set(300)  # Set time limit
        """
        if self._model is None:
            raise RuntimeError(
                "Solver model not built yet. Call build_model() first."
            )
        return self._model

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
        cplex_model: Cplex,
        status: int,
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Extract sensitivity data (shadow prices and reduced costs) from CPLEX solution.

        Args:
            model: Original LumiX model
            cplex_model: CPLEX model with solution
            status: CPLEX status code

        Returns:
            Tuple of (shadow_prices, reduced_costs) dictionaries
        """
        shadow_prices: Dict[str, float] = {}
        reduced_costs: Dict[str, float] = {}

        # Sensitivity analysis only available for LP problems with optimal solutions
        # Status 1 = optimal, 6 = optimal (numerical best)
        if status not in [1, 6]:
            return shadow_prices, reduced_costs

        try:
            # Extract dual values (shadow prices) for constraints
            # Note: We don't check variable types here because if sensitivity was enabled,
            # the solve() method already verified all vars are continuous and set LP mode
            try:
                dual_values = cplex_model.solution.get_dual_values()

                # Map dual values to constraint names
                for lx_constraint in model.constraints:
                    solver_constraints = self._constraint_map.get(lx_constraint.name)

                    if solver_constraints is None:
                        continue

                    if isinstance(solver_constraints, dict):
                        # Indexed constraint family
                        for index_key, constraint_idx in solver_constraints.items():
                            ct_name = f"{lx_constraint.name}[{index_key}]"
                            if constraint_idx < len(dual_values):
                                shadow_prices[ct_name] = dual_values[constraint_idx]
                    else:
                        # Single constraint
                        if solver_constraints < len(dual_values):
                            shadow_prices[lx_constraint.name] = dual_values[solver_constraints]

            except CplexError as e:
                self.logger.logger.debug(f"Failed to extract dual values: {e}")

            # Extract reduced costs for variables
            try:
                reduced_cost_values = cplex_model.solution.get_reduced_costs()

                # Map reduced costs to variable names
                for lx_var in model.variables:
                    solver_vars = self._variable_map.get(lx_var.name)

                    if solver_vars is None:
                        continue

                    if isinstance(solver_vars, dict):
                        # Indexed variable family
                        for index_key, var_idx in solver_vars.items():
                            var_name = f"{lx_var.name}[{index_key}]"
                            if var_idx < len(reduced_cost_values):
                                reduced_costs[var_name] = reduced_cost_values[var_idx]
                    else:
                        # Single variable
                        if solver_vars < len(reduced_cost_values):
                            reduced_costs[lx_var.name] = reduced_cost_values[solver_vars]

            except CplexError as e:
                self.logger.logger.debug(f"Failed to extract reduced costs: {e}")

        except CplexError as e:
            self.logger.logger.debug(f"Failed to check problem type: {e}")

        return shadow_prices, reduced_costs

    def _parse_solution(
        self,
        model: LXModel,
        cplex_model: Cplex,
        solve_time: float,
        enable_sensitivity: bool = False,
    ) -> LXSolution:
        """
        Parse CPLEX solution to LXSolution.

        Args:
            model: Original LumiX model
            cplex_model: CPLEX model with solution
            solve_time: Time taken to solve

        Returns:
            LXSolution object
        """
        # Map status codes
        try:
            status = cplex_model.solution.get_status()
        except CplexError:
            return LXSolution(
                objective_value=0.0,
                status="error",
                solve_time=solve_time,
                variables={},
                mapped={},
            )

        sol = cplex_model.solution
        code = sol.get_status()
        st = sol.status
        has_solution = sol.get_solution_type() != sol.type.none and code not in (
            st.unbounded, st.MIP_unbounded, st.infeasible_or_unbounded,
            st.MIP_infeasible_or_unbounded, st.infeasible, st.MIP_infeasible)
        if has_solution and not sol.is_primal_feasible():
            has_solution = False    # an LP stopped by a limit keeps an infeasible point
        if code == st.relaxation_unbounded:
            warn_user(
                "CPLEX could not bound the objective (its relaxation is unbounded); the "
                "model may be unbounded, and any point returned is only feasible",
                UserWarning)
        lx_status = self._status_name(sol.status, code, has_solution)
        obj_value = sol.get_objective_value() if has_solution else 0.0
        if has_solution:
            values = sol.get_values()
            variables, mapped = self._solution_values(lambda pos: values[pos])
        else:
            variables, mapped = {}, {}

        # Extract sensitivity data if enabled
        shadow_prices: Dict[str, float] = {}
        reduced_costs: Dict[str, float] = {}
        if enable_sensitivity:
            shadow_prices, reduced_costs = self._extract_sensitivity_data(
                model, cplex_model, status
            )

        # Extract solver statistics
        gap: Optional[float] = None
        iterations: Optional[int] = None
        nodes: Optional[int] = None

        try:
            # MIP gap (only for MIP problems)
            if cplex_model.get_problem_type() in [
                cplex_model.problem_type.MILP,
                cplex_model.problem_type.MIQP,
                cplex_model.problem_type.MIQCP,
            ]:
                try:
                    gap = cplex_model.solution.MIP.get_mip_relative_gap()
                except CplexError:
                    pass
        except CplexError:
            pass

        try:
            # Iteration count
            iterations = cplex_model.solution.progress.get_num_iterations()
        except CplexError:
            pass

        try:
            # Node count (for MIP)
            if cplex_model.get_problem_type() in [
                cplex_model.problem_type.MILP,
                cplex_model.problem_type.MIQP,
                cplex_model.problem_type.MIQCP,
            ]:
                nodes = cplex_model.solution.progress.get_num_nodes_processed()
        except CplexError:
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


__all__ = ["LXCPLEXSolver"]
