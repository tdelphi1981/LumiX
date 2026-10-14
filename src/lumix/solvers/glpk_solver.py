"""GLPK solver implementation for LumiX."""

from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import swiglpk as glpk
except ImportError:
    glpk = None  # type: ignore

from ..core.constraints import LXConstraint
from ..core.enums import LXConstraintSense, LXObjectiveSense, LXVarType
from ..core.model import LXModel
from ..core.variables import LXVariable
from ..solution.solution import LXSolution
from .base import LXSolverInterface
from .capabilities import GLPK_CAPABILITIES


class LXGLPKSolver(LXSolverInterface):
    """
    GLPK (GNU Linear Programming Kit) solver implementation for LumiX.

    Supports:
    - Linear Programming (LP)
    - Mixed-Integer Linear Programming (MILP)
    - Binary and Integer variables
    - Single and indexed variable families
    - Single and indexed constraint families
    - Multi-model expressions
    - Sensitivity analysis (dual values, reduced costs)

    TODO: Future improvements:
    - Warm start from previous solution (if GLPK adds support)
    - Advanced solver parameters passthrough
    - Interior point method options
    - Branch-and-cut callback support
    """

    def __init__(self) -> None:
        """Initialize GLPK solver."""
        super().__init__(GLPK_CAPABILITIES)

        if glpk is None:
            raise ImportError(
                "GLPK is not installed. "
                "Install it with: pip install swiglpk\n"
                "Note: GLPK is free and open-source"
            )

        # Internal state
        self._model: Optional[Any] = None  # glp_prob pointer
        self._variable_map: Dict[str, Union[int, Dict[Any, int]]] = {}
        self._constraint_map: Dict[str, Union[int, Dict[Any, int]]] = {}
        self._constraint_list: List[int] = []

    def build_model(self, model: LXModel) -> Any:
        """Build a GLPK problem from the canonical form of ``model``."""
        canon = self._canonicalize(model)
        self._model = glpk.glp_create_prob()
        gm = self._model
        glpk.glp_set_prob_name(gm, model.name)
        if canon.variables:
            glpk.glp_add_cols(gm, len(canon.variables))
        if canon.rows:
            glpk.glp_add_rows(gm, len(canon.rows))
        kind = {LXVarType.CONTINUOUS: glpk.GLP_CV, LXVarType.INTEGER: glpk.GLP_IV,
                LXVarType.BINARY: glpk.GLP_BV}
        handles = []
        for col, v in enumerate(canon.variables, start=1):
            glpk.glp_set_col_name(gm, col, v.name)
            glpk.glp_set_col_kind(gm, col, kind[v.var_type])
            self._set_bounds(glpk.glp_set_col_bnds, col, v.lower, v.upper)
            handles.append(col)
        self._handles = handles
        self._variable_map = self._family_map(canon, handles)
        for r, row in enumerate(canon.rows, start=1):
            glpk.glp_set_row_name(gm, r, row.name)
            lo, hi = {LXConstraintSense.LE: (-math.inf, row.rhs),
                      LXConstraintSense.GE: (row.rhs, math.inf),
                      LXConstraintSense.EQ: (row.rhs, row.rhs)}[row.sense]
            self._set_bounds(glpk.glp_set_row_bnds, r, lo, hi)
            if row.coeffs:
                ia = glpk.intArray(len(row.coeffs) + 1)
                ar = glpk.doubleArray(len(row.coeffs) + 1)
                for i, (pos, coeff) in enumerate(row.coeffs.items(), start=1):
                    ia[i], ar[i] = handles[pos], coeff
                glpk.glp_set_mat_row(gm, r, len(row.coeffs), ia, ar)
            self._register_row(row, r)
        if canon.sense is not None:
            for pos, coeff in canon.objective.items():
                glpk.glp_set_obj_coef(gm, handles[pos], coeff)
            glpk.glp_set_obj_coef(gm, 0, canon.objective_constant)
            glpk.glp_set_obj_dir(gm, glpk.GLP_MAX if canon.sense == LXObjectiveSense.MAXIMIZE
                                 else glpk.GLP_MIN)
        return gm

    #: Time budget of the feasibility check that settles an unbounded MIP relaxation.
    FEASIBILITY_CHECK_MS = 2000

    def _has_integer_point(self, glpk_model: Any, smcp: Any) -> Optional[bool]:
        """Feasibility of the integer problem, found with a zero objective."""
        for col in range(1, glpk.glp_get_num_cols(glpk_model) + 1):
            glpk.glp_set_obj_coef(glpk_model, col, 0.0)
        if glpk.glp_simplex(glpk_model, smcp) != 0:
            return None
        if glpk.glp_get_status(glpk_model) == glpk.GLP_NOFEAS:
            return False
        iocp = glpk.glp_iocp()
        glpk.glp_init_iocp(iocp)
        iocp.msg_lev = smcp.msg_lev
        # An infeasible MIP can keep branch-and-bound busy forever (2a - 2b = 1).
        iocp.tm_lim = min(smcp.tm_lim, self.FEASIBILITY_CHECK_MS)
        if glpk.glp_intopt(glpk_model, iocp) != 0:
            return None
        status = glpk.glp_mip_status(glpk_model)
        return {glpk.GLP_OPT: True, glpk.GLP_FEAS: True, glpk.GLP_NOFEAS: False}.get(status)

    def _set_bounds(self, setter: Any, index: int, lower: float, upper: float) -> None:
        lo_open, hi_open = not math.isfinite(lower), not math.isfinite(upper)
        if lo_open and hi_open:
            setter(self._model, index, glpk.GLP_FR, 0.0, 0.0)
        elif lo_open:
            setter(self._model, index, glpk.GLP_UP, 0.0, upper)
        elif hi_open:
            setter(self._model, index, glpk.GLP_LO, lower, 0.0)
        elif lower == upper:
            setter(self._model, index, glpk.GLP_FX, lower, upper)
        else:
            setter(self._model, index, glpk.GLP_DB, lower, upper)

    def solve(
        self,
        model: LXModel,
        time_limit: Optional[float] = None,
        gap_tolerance: Optional[float] = None,
        enable_sensitivity: bool = False,
        **solver_params: Any,
    ) -> LXSolution:
        """
        Solve optimization model with GLPK.

        Args:
            model: LumiX model to solve
            time_limit: Time limit in seconds (None = no limit)
            gap_tolerance: MIP gap tolerance (None = solver default)
            enable_sensitivity: Enable sensitivity analysis
            **solver_params: Additional GLPK-specific parameters
                Examples:
                - msg_lev: Message level (glpk.GLP_MSG_OFF, GLP_MSG_ERR, GLP_MSG_ON, GLP_MSG_ALL)
                - presolve: Enable presolve (True/False)
                - method: LP method (glpk.GLP_PRIMAL, GLP_DUAL, GLP_DUALP)

        Returns:
            Solution object with results
        """
        # Build the model
        glpk_model = self.build_model(model)

        has_integer = any(v.var_type != LXVarType.CONTINUOUS for v in self._canonical.variables)

        smcp = glpk.glp_smcp()
        glpk.glp_init_smcp(smcp)
        smcp.msg_lev = solver_params.get("msg_lev", glpk.GLP_MSG_OFF)
        smcp.presolve = glpk.GLP_ON if solver_params.get("presolve", True) else glpk.GLP_OFF
        if "method" in solver_params:
            smcp.meth = solver_params["method"]
        if time_limit is not None:
            smcp.tm_lim = int(time_limit * 1000)

        start_time = time.time()
        ret = glpk.glp_simplex(glpk_model, smcp)
        is_mip = False
        if has_integer and ret == 0 and glpk.glp_get_status(glpk_model) in (glpk.GLP_OPT, glpk.GLP_FEAS):
            iocp = glpk.glp_iocp()
            glpk.glp_init_iocp(iocp)
            iocp.msg_lev = smcp.msg_lev
            if time_limit is not None:
                iocp.tm_lim = int(time_limit * 1000)
            if gap_tolerance is not None:
                iocp.mip_gap = gap_tolerance
            ret = glpk.glp_intopt(glpk_model, iocp)
            status = glpk.glp_mip_status(glpk_model)
            is_mip = True
        else:
            # an LP, or a MIP whose relaxation is infeasible/unbounded/stopped
            status = glpk.glp_get_status(glpk_model)
        solve_time = time.time() - start_time
        self._return_code = ret
        # A MIP whose LP relaxation did not solve: its relaxation status says nothing
        # definite about the integer problem except infeasibility.
        self._relaxation_only = has_integer and not is_mip
        self._mip_feasible: Optional[bool] = None
        if self._relaxation_only and (ret == glpk.GLP_ENODFS
                                      or glpk.glp_get_status(glpk_model) == glpk.GLP_UNBND):
            # The relaxation is unbounded, so the MIP is unbounded if it is feasible at all.
            self._mip_feasible = self._has_integer_point(glpk_model, smcp)

        # Parse and return solution
        solution = self._parse_solution(
            model, glpk_model, status, solve_time, is_mip, enable_sensitivity
        )

        return solution

    def get_solver_model(self) -> Any:
        """
        Get underlying GLPK model for advanced usage.

        Returns:
            GLPK problem pointer

        Raises:
            RuntimeError: If model hasn't been built yet

        Examples:
            # Access GLPK model for advanced features
            glpk_model = solver.get_solver_model()
            glpk.glp_set_obj_name(glpk_model, "MyObjective")
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
        glpk_model: Any,
        is_mip: bool,
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Extract sensitivity data (shadow prices and reduced costs) from GLPK solution.

        Args:
            model: Original LumiX model
            glpk_model: GLPK model with solution
            is_mip: Whether this is a MIP problem

        Returns:
            Tuple of (shadow_prices, reduced_costs) dictionaries
        """
        shadow_prices: Dict[str, float] = {}
        reduced_costs: Dict[str, float] = {}

        # Sensitivity analysis only available for LP problems (not MIP)
        if is_mip:
            return shadow_prices, reduced_costs

        try:
            # Extract dual values (shadow prices) for constraints
            for lx_constraint in model.constraints:
                solver_constraints = self._constraint_map.get(lx_constraint.name)

                if solver_constraints is None:
                    continue

                if isinstance(solver_constraints, dict):
                    # Indexed constraint family
                    for index_key, row_idx in solver_constraints.items():
                        ct_name = f"{lx_constraint.name}[{index_key}]"
                        try:
                            shadow_price = glpk.glp_get_row_dual(glpk_model, row_idx)
                            shadow_prices[ct_name] = shadow_price
                        except Exception:
                            pass
                else:
                    # Single constraint
                    try:
                        shadow_price = glpk.glp_get_row_dual(glpk_model, solver_constraints)
                        shadow_prices[lx_constraint.name] = shadow_price
                    except Exception:
                        pass

            # Extract reduced costs for variables
            for lx_var in model.variables:
                solver_vars = self._variable_map.get(lx_var.name)

                if solver_vars is None:
                    continue

                if isinstance(solver_vars, dict):
                    # Indexed variable family
                    for index_key, col_idx in solver_vars.items():
                        var_name = f"{lx_var.name}[{index_key}]"
                        try:
                            reduced_cost = glpk.glp_get_col_dual(glpk_model, col_idx)
                            reduced_costs[var_name] = reduced_cost
                        except Exception:
                            pass
                else:
                    # Single variable
                    try:
                        reduced_cost = glpk.glp_get_col_dual(glpk_model, solver_vars)
                        reduced_costs[lx_var.name] = reduced_cost
                    except Exception:
                        pass

        except Exception as e:
            self.logger.logger.debug(f"Failed to extract sensitivity data: {e}")

        return shadow_prices, reduced_costs

    def _parse_solution(
        self,
        model: LXModel,
        glpk_model: Any,
        status: int,
        solve_time: float,
        is_mip: bool,
        enable_sensitivity: bool = False,
    ) -> LXSolution:
        """
        Parse GLPK solution to LXSolution.

        Args:
            model: Original LumiX model
            glpk_model: GLPK model with solution
            status: GLPK status code
            solve_time: Time taken to solve
            is_mip: Whether this is a MIP problem
            enable_sensitivity: Whether to extract sensitivity data

        Returns:
            LXSolution object
        """
        # Map GLPK status codes
        if is_mip:
            status_map = {
                glpk.GLP_OPT: "optimal",
                glpk.GLP_FEAS: "feasible",
                glpk.GLP_NOFEAS: "infeasible",
                glpk.GLP_UNBND: "unbounded",
                glpk.GLP_UNDEF: "undefined",
            }
        else:
            status_map = {
                glpk.GLP_OPT: "optimal",
                glpk.GLP_FEAS: "feasible",
                glpk.GLP_INFEAS: "infeasible",
                glpk.GLP_NOFEAS: "infeasible",
                glpk.GLP_UNBND: "unbounded",
                glpk.GLP_UNDEF: "undefined",
            }

        ret = getattr(self, "_return_code", 0)
        relaxation_only = getattr(self, "_relaxation_only", False)
        if ret == glpk.GLP_ENOPFS:
            lx_status = "infeasible"
        elif relaxation_only and (ret == glpk.GLP_ENODFS or status == glpk.GLP_UNBND):
            feasible = getattr(self, "_mip_feasible", None)
            lx_status = {True: "unbounded", False: "infeasible"}.get(feasible, "inf_or_unbounded")
        elif relaxation_only and status not in (glpk.GLP_NOFEAS, glpk.GLP_INFEAS):
            lx_status = "time_limit" if ret == glpk.GLP_ETMLIM else "undefined"
        elif ret == glpk.GLP_ENODFS:
            lx_status = "unbounded"
        elif ret == glpk.GLP_ETMLIM and status not in (glpk.GLP_OPT, glpk.GLP_FEAS):
            lx_status = "time_limit"
        else:
            lx_status = status_map.get(status, "unknown")

        # Extract objective value
        obj_value = 0.0
        if status in [glpk.GLP_OPT, glpk.GLP_FEAS]:
            if is_mip:
                obj_value = glpk.glp_mip_obj_val(glpk_model)
            else:
                obj_value = glpk.glp_get_obj_val(glpk_model)

        # Extract variable values
        if status in (glpk.GLP_OPT, glpk.GLP_FEAS) and not relaxation_only:
            read = glpk.glp_mip_col_val if is_mip else glpk.glp_get_col_prim
            variables, mapped = self._solution_values(
                lambda pos: read(glpk_model, self._handles[pos]))
        else:
            variables, mapped = {}, {}

        # Extract sensitivity data if enabled
        shadow_prices: Dict[str, float] = {}
        reduced_costs: Dict[str, float] = {}
        if enable_sensitivity and status == glpk.GLP_OPT:
            shadow_prices, reduced_costs = self._extract_sensitivity_data(
                model, glpk_model, is_mip
            )

        # Extract MIP gap if available
        gap: Optional[float] = None
        if is_mip and status in [glpk.GLP_OPT, glpk.GLP_FEAS]:
            # GLPK doesn't directly expose MIP gap in swiglpk
            # We could calculate it manually if needed
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
            iterations=None,  # GLPK doesn't expose iteration count via swiglpk
            nodes=None,  # GLPK doesn't expose node count via swiglpk
        )


__all__ = ["LXGLPKSolver"]
