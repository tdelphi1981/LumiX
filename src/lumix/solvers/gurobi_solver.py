"""Gurobi solver implementation for LumiX."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import gurobipy as gp
    from gurobipy import GRB
except ImportError:
    gp = None  # type: ignore
    GRB = None  # type: ignore

from ..core.constraints import LXConstraint
from ..core.enums import LXConstraintSense, LXObjectiveSense, LXVarType
from ..core.model import LXModel
from ..core.variables import LXVariable
from ..solution.solution import LXSolution
from .base import LXSolverInterface
from .capabilities import GUROBI_CAPABILITIES


class LXGurobiSolver(LXSolverInterface):
    """
    Gurobi solver implementation for LumiX.

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
    """

    def __init__(self) -> None:
        """Initialize Gurobi solver."""
        super().__init__(GUROBI_CAPABILITIES)

        if gp is None or GRB is None:
            raise ImportError(
                "Gurobi is not installed. "
                "Install it with: pip install gurobipy\n"
                "Note: Gurobi requires a license (free academic licenses available)"
            )

        # Internal state
        self._model: Optional[gp.Model] = None
        self._variable_map: Dict[str, Union[Any, Dict[Any, Any]]] = {}
        self._constraint_map: Dict[str, Union[Any, Dict[Any, Any]]] = {}
        self._constraint_list: List[Any] = []

    def build_model(self, model: LXModel) -> gp.Model:
        """Build a Gurobi model from the canonical form of ``model``."""
        canon = self._canonicalize(model)
        self._model = gp.Model(model.name)
        gm = self._model
        vtype = {LXVarType.CONTINUOUS: GRB.CONTINUOUS, LXVarType.INTEGER: GRB.INTEGER,
                 LXVarType.BINARY: GRB.BINARY}
        handles = [gm.addVar(lb=v.lower, ub=v.upper, vtype=vtype[v.var_type], name=v.name)
                   for v in canon.variables]
        self._handles = handles
        self._variable_map = self._family_map(canon, handles)
        gm.update()
        sense = {LXConstraintSense.LE: GRB.LESS_EQUAL, LXConstraintSense.GE: GRB.GREATER_EQUAL,
                 LXConstraintSense.EQ: GRB.EQUAL}
        for row in canon.rows:
            expr = gp.LinExpr([c for c in row.coeffs.values()], [handles[p] for p in row.coeffs])
            self._register_row(row, gm.addLConstr(expr, sense[row.sense], row.rhs, name=row.name))
        if canon.sense is not None:
            expr = gp.LinExpr([c for c in canon.objective.values()],
                              [handles[p] for p in canon.objective])
            expr.addConstant(canon.objective_constant)
            gm.setObjective(expr, GRB.MAXIMIZE if canon.sense == LXObjectiveSense.MAXIMIZE
                            else GRB.MINIMIZE)
        gm.update()
        return gm

    def solve(
        self,
        model: LXModel,
        time_limit: Optional[float] = None,
        gap_tolerance: Optional[float] = None,
        enable_sensitivity: bool = False,
        **solver_params: Any,
    ) -> LXSolution:
        """
        Solve optimization model with Gurobi.

        Args:
            model: LumiX model to solve
            time_limit: Time limit in seconds (None = no limit)
            gap_tolerance: MIP gap tolerance (None = solver default, typically 0.0001)
            **solver_params: Additional Gurobi-specific parameters
                Examples:
                - Threads: Number of parallel threads (int)
                - MIPFocus: MIP focus (1=feasibility, 2=optimality, 3=bound)
                - Presolve: Presolve level (-1=auto, 0=off, 1=conservative, 2=aggressive)
                - Method: Algorithm for continuous models (-1=auto, 0=primal, 1=dual, 2=barrier)
                - LogToConsole: Show solver output (0=off, 1=on)

        Returns:
            Solution object with results

        TODO: Add support for additional features:
            - Warm start from previous solution
            - Solution pool for MIP
            - Callback functions
        """
        # Build the model
        gurobi_model = self.build_model(model)

        # Set time limit
        if time_limit is not None:
            gurobi_model.setParam(GRB.Param.TimeLimit, time_limit)

        # Set MIP gap tolerance
        if gap_tolerance is not None:
            gurobi_model.setParam(GRB.Param.MIPGap, gap_tolerance)

        # Set additional solver parameters
        for param_name, param_value in solver_params.items():
            try:
                gurobi_model.setParam(param_name, param_value)
            except Exception as e:
                self.logger.logger.warning(
                    f"Failed to set Gurobi parameter '{param_name}': {e}"
                )

        # Solve
        start_time = time.time()
        gurobi_model.optimize()
        if gurobi_model.Status == GRB.INF_OR_UNBD:
            # Presolve could not tell infeasible from unbounded; ask once more.
            gurobi_model.setParam(GRB.Param.DualReductions, 0)
            gurobi_model.optimize()
        solve_time = time.time() - start_time

        # Parse and return solution
        solution = self._parse_solution(model, gurobi_model, solve_time, enable_sensitivity)

        return solution

    def get_solver_model(self) -> gp.Model:
        """
        Get underlying Gurobi model for advanced usage.

        Returns:
            Gurobi Model instance

        Raises:
            RuntimeError: If model hasn't been built yet

        Examples:
            # Access Gurobi model for advanced features
            gurobi_model = solver.get_solver_model()
            gurobi_model.setParam(GRB.Param.OutputFlag, 1)  # Enable output
            gurobi_model.setParam(GRB.Param.Threads, 4)  # Set thread count
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
        gurobi_model: gp.Model,
        status: int,
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Extract sensitivity data (shadow prices and reduced costs) from Gurobi solution.

        Args:
            model: Original LumiX model
            gurobi_model: Gurobi model with solution
            status: Gurobi status code

        Returns:
            Tuple of (shadow_prices, reduced_costs) dictionaries
        """
        shadow_prices: Dict[str, float] = {}
        reduced_costs: Dict[str, float] = {}

        # Sensitivity analysis only available for LP problems with optimal solutions
        # Status 2 = OPTIMAL
        if status != GRB.OPTIMAL:
            return shadow_prices, reduced_costs

        try:
            # Check if problem is LP (not MIP)
            if gurobi_model.getAttr('IsMIP') == 1:
                # MIP problems don't have dual values
                return shadow_prices, reduced_costs

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
                                shadow_price = constr.getAttr('Pi')
                                shadow_prices[ct_name] = shadow_price
                            except Exception:
                                pass
                    else:
                        # Single constraint
                        try:
                            shadow_price = solver_constraints.getAttr('Pi')
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
                                reduced_cost = var.getAttr('RC')
                                reduced_costs[var_name] = reduced_cost
                            except Exception:
                                pass
                    else:
                        # Single variable
                        try:
                            reduced_cost = solver_vars.getAttr('RC')
                            reduced_costs[lx_var.name] = reduced_cost
                        except Exception:
                            pass

            except Exception as e:
                self.logger.logger.debug(f"Failed to extract reduced costs: {e}")

        except Exception as e:
            self.logger.logger.debug(f"Failed to check problem type: {e}")

        return shadow_prices, reduced_costs

    def _parse_solution(
        self,
        model: LXModel,
        gurobi_model: gp.Model,
        solve_time: float,
        enable_sensitivity: bool = False,
    ) -> LXSolution:
        """
        Parse Gurobi solution to LXSolution.

        Args:
            model: Original LumiX model
            gurobi_model: Gurobi model with solution
            solve_time: Time taken to solve

        Returns:
            LXSolution object
        """
        # Map status codes
        status = gurobi_model.Status

        status_map = {
            GRB.OPTIMAL: "optimal",
            GRB.SUBOPTIMAL: "feasible",
            GRB.INFEASIBLE: "infeasible",
            GRB.UNBOUNDED: "unbounded",
            GRB.INF_OR_UNBD: "inf_or_unbounded",
            GRB.CUTOFF: "cutoff",
            GRB.ITERATION_LIMIT: "iteration_limit",
            GRB.NODE_LIMIT: "node_limit",
            GRB.TIME_LIMIT: "time_limit",
            GRB.SOLUTION_LIMIT: "solution_limit",
            GRB.INTERRUPTED: "interrupted",
            GRB.NUMERIC: "numeric",
        }

        lx_status = status_map.get(status, "unknown")
        has_solution = gurobi_model.SolCount > 0 and status not in (
            GRB.INFEASIBLE, GRB.INF_OR_UNBD, GRB.UNBOUNDED)
        if has_solution and status != GRB.OPTIMAL:
            lx_status = "feasible"      # a limit stopped the search with an incumbent
        obj_value = gurobi_model.ObjVal if has_solution else 0.0
        if has_solution:
            variables, mapped = self._solution_values(lambda pos: self._handles[pos].X)
        else:
            variables, mapped = {}, {}

        # Extract sensitivity data if enabled
        shadow_prices: Dict[str, float] = {}
        reduced_costs: Dict[str, float] = {}
        if enable_sensitivity:
            shadow_prices, reduced_costs = self._extract_sensitivity_data(
                model, gurobi_model, status
            )

        # Extract solver statistics
        gap: Optional[float] = None
        iterations: Optional[int] = None
        nodes: Optional[int] = None

        try:
            # MIP gap (only for MIP problems)
            if gurobi_model.IsMIP and has_solution:
                gap = gurobi_model.MIPGap
        except Exception:
            pass

        try:
            # Iteration count
            iterations = int(gurobi_model.IterCount)
        except Exception:
            pass

        try:
            # Node count (for MIP)
            if gurobi_model.IsMIP:
                nodes = int(gurobi_model.NodeCount)
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


__all__ = ["LXGurobiSolver"]
