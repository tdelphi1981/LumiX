"""GLPK solver implementation for LumiX."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import swiglpk as glpk
except ImportError:
    glpk = None  # type: ignore

from ..core.constraints import LXConstraint
from ..core.enums import LXConstraintSense, LXObjectiveSense, LXVarType
from ..core.expressions import LXLinearExpression
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
        self._variable_counter: int = 0
        self._constraint_counter: int = 0

    def build_model(self, model: LXModel) -> Any:
        """
        Build GLPK native model from LXModel.

        Args:
            model: LumiX model to build

        Returns:
            GLPK problem pointer

        Raises:
            ValueError: If model contains unsupported features
        """
        # Create GLPK problem instance
        self._model = glpk.glp_create_prob()
        glpk.glp_set_prob_name(self._model, model.name)

        # Reset internal state
        self._variable_map = {}
        self._constraint_map = {}
        self._constraint_list = []
        self._variable_counter = 0
        self._constraint_counter = 0

        # Count total variables and constraints
        total_vars = sum(
            len(var.get_instances()) if var.get_instances() else 1
            for var in model.variables
        )
        total_constraints = sum(
            len(ct.get_instances()) if ct.get_instances() else 1
            for ct in model.constraints
        )

        # Pre-allocate columns (variables) and rows (constraints)
        if total_vars > 0:
            glpk.glp_add_cols(self._model, total_vars)
        if total_constraints > 0:
            glpk.glp_add_rows(self._model, total_constraints)

        # Build variables
        for lx_var in model.variables:
            instances = lx_var.get_instances()

            if not instances:
                # Single variable (not indexed)
                self._create_single_variable(lx_var)
            else:
                # Variable family (indexed by data)
                self._create_indexed_variables(lx_var, instances)

        # Build constraints
        for lx_constraint in model.constraints:
            instances = lx_constraint.get_instances()

            if not instances:
                # Single constraint
                self._create_single_constraint(lx_constraint)
            else:
                # Constraint family (indexed by data)
                self._create_indexed_constraints(lx_constraint, instances)

        # Set objective
        self._set_objective(model)

        return self._model

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

        # Determine if this is a MIP problem
        has_integer = any(
            var.var_type in [LXVarType.INTEGER, LXVarType.BINARY]
            for var in model.variables
        )

        # Configure solver parameters
        if has_integer:
            # MIP parameters
            iocp = glpk.glp_iocp()
            glpk.glp_init_iocp(iocp)
            iocp.presolve = glpk.GLP_ON
            iocp.msg_lev = solver_params.get("msg_lev", glpk.GLP_MSG_OFF)

            # Set time limit (in milliseconds)
            if time_limit is not None:
                iocp.tm_lim = int(time_limit * 1000)

            # Set MIP gap tolerance
            if gap_tolerance is not None:
                iocp.mip_gap = gap_tolerance
        else:
            # LP parameters
            smcp = glpk.glp_smcp()
            glpk.glp_init_smcp(smcp)
            smcp.msg_lev = solver_params.get("msg_lev", glpk.GLP_MSG_OFF)

            # Set time limit (in seconds for simplex)
            if time_limit is not None:
                smcp.tm_lim = int(time_limit * 1000)

            # LP method
            if "method" in solver_params:
                smcp.meth = solver_params["method"]

            # Presolve
            if solver_params.get("presolve", True):
                smcp.presolve = glpk.GLP_ON

        # Solve
        start_time = time.time()

        if has_integer:
            # Solve LP relaxation first
            ret_lp = glpk.glp_simplex(glpk_model, smcp if 'smcp' in locals() else None)

            # Then solve MIP
            ret = glpk.glp_intopt(glpk_model, iocp)
            status = glpk.glp_mip_status(glpk_model)
        else:
            # Solve LP
            ret = glpk.glp_simplex(glpk_model, smcp)
            status = glpk.glp_get_status(glpk_model)

        solve_time = time.time() - start_time

        # Parse and return solution
        solution = self._parse_solution(
            model, glpk_model, status, solve_time, has_integer, enable_sensitivity
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
        if lx_var.index_func is not None:
            return lx_var.index_func(instance)
        elif lx_var._cartesian is not None and isinstance(instance, tuple):
            # For cartesian products, apply each dimension's key function
            return tuple(
                dim.key_func(inst)
                for dim, inst in zip(lx_var._cartesian.dimensions, instance)
            )
        else:
            return instance

    def _create_single_variable(self, lx_var: LXVariable) -> None:
        """Create single GLPK variable (not indexed)."""
        model = self._model
        assert model is not None

        # Get column index (1-based in GLPK)
        self._variable_counter += 1
        col_idx = self._variable_counter

        # Set variable name
        glpk.glp_set_col_name(model, col_idx, lx_var.name)

        # Get bounds
        lb = lx_var.lower_bound if lx_var.lower_bound is not None else None
        ub = lx_var.upper_bound if lx_var.upper_bound is not None else None

        # Set bounds using GLPK bound types
        if lb is not None and ub is not None:
            if lb == ub:
                glpk.glp_set_col_bnds(model, col_idx, glpk.GLP_FX, lb, ub)
            else:
                glpk.glp_set_col_bnds(model, col_idx, glpk.GLP_DB, lb, ub)
        elif lb is not None:
            glpk.glp_set_col_bnds(model, col_idx, glpk.GLP_LO, lb, 0.0)
        elif ub is not None:
            glpk.glp_set_col_bnds(model, col_idx, glpk.GLP_UP, 0.0, ub)
        else:
            glpk.glp_set_col_bnds(model, col_idx, glpk.GLP_FR, 0.0, 0.0)

        # Set variable type
        if lx_var.var_type == LXVarType.CONTINUOUS:
            glpk.glp_set_col_kind(model, col_idx, glpk.GLP_CV)
        elif lx_var.var_type == LXVarType.INTEGER:
            glpk.glp_set_col_kind(model, col_idx, glpk.GLP_IV)
        elif lx_var.var_type == LXVarType.BINARY:
            glpk.glp_set_col_kind(model, col_idx, glpk.GLP_BV)
        else:
            raise ValueError(f"Unknown variable type: {lx_var.var_type}")

        # Store in mapping
        self._variable_map[lx_var.name] = col_idx

    def _create_indexed_variables(
        self, lx_var: LXVariable, instances: List[Any]
    ) -> None:
        """Create indexed family of GLPK variables."""
        model = self._model
        assert model is not None

        var_dict: Dict[Any, int] = {}

        for instance in instances:
            # Get index key (handles cartesian products)
            index_key = self._get_index_key(lx_var, instance)

            # Variable name: "varname[index]"
            var_name = f"{lx_var.name}[{index_key}]"

            # Get column index (1-based in GLPK)
            self._variable_counter += 1
            col_idx = self._variable_counter

            # Set variable name
            glpk.glp_set_col_name(model, col_idx, var_name)

            # Get bounds (same for all instances for now)
            lb = lx_var.lower_bound if lx_var.lower_bound is not None else None
            ub = lx_var.upper_bound if lx_var.upper_bound is not None else None

            # Set bounds
            if lb is not None and ub is not None:
                if lb == ub:
                    glpk.glp_set_col_bnds(model, col_idx, glpk.GLP_FX, lb, ub)
                else:
                    glpk.glp_set_col_bnds(model, col_idx, glpk.GLP_DB, lb, ub)
            elif lb is not None:
                glpk.glp_set_col_bnds(model, col_idx, glpk.GLP_LO, lb, 0.0)
            elif ub is not None:
                glpk.glp_set_col_bnds(model, col_idx, glpk.GLP_UP, 0.0, ub)
            else:
                glpk.glp_set_col_bnds(model, col_idx, glpk.GLP_FR, 0.0, 0.0)

            # Set variable type
            if lx_var.var_type == LXVarType.CONTINUOUS:
                glpk.glp_set_col_kind(model, col_idx, glpk.GLP_CV)
            elif lx_var.var_type == LXVarType.INTEGER:
                glpk.glp_set_col_kind(model, col_idx, glpk.GLP_IV)
            elif lx_var.var_type == LXVarType.BINARY:
                glpk.glp_set_col_kind(model, col_idx, glpk.GLP_BV)
            else:
                raise ValueError(f"Unknown variable type: {lx_var.var_type}")

            var_dict[index_key] = col_idx

        # Store dictionary in mapping
        self._variable_map[lx_var.name] = var_dict

    def _create_single_constraint(self, lx_constraint: LXConstraint) -> None:
        """Create single GLPK constraint."""
        model = self._model
        assert model is not None

        if lx_constraint.lhs is None:
            raise ValueError(f"Constraint '{lx_constraint.name}' has no LHS expression")

        # Get row index (1-based in GLPK)
        self._constraint_counter += 1
        row_idx = self._constraint_counter

        # Set constraint name
        glpk.glp_set_row_name(model, row_idx, lx_constraint.name)

        # Build linear expression
        var_indices, coeffs = self._build_expression(lx_constraint.lhs)

        # Get RHS value
        if lx_constraint.rhs_value is not None:
            rhs = lx_constraint.rhs_value
        elif lx_constraint.rhs_func is not None:
            rhs = lx_constraint.rhs_func(None)  # type: ignore
        else:
            raise ValueError(f"Constraint '{lx_constraint.name}' has no RHS value")

        # Set constraint bounds based on sense
        if lx_constraint.sense == LXConstraintSense.LE:
            glpk.glp_set_row_bnds(model, row_idx, glpk.GLP_UP, 0.0, rhs)
        elif lx_constraint.sense == LXConstraintSense.GE:
            glpk.glp_set_row_bnds(model, row_idx, glpk.GLP_LO, rhs, 0.0)
        elif lx_constraint.sense == LXConstraintSense.EQ:
            glpk.glp_set_row_bnds(model, row_idx, glpk.GLP_FX, rhs, rhs)
        else:
            raise ValueError(f"Unknown constraint sense: {lx_constraint.sense}")

        # Set constraint coefficients using sparse format
        # GLPK uses 1-based indexing for arrays
        if var_indices:
            ia = glpk.intArray(len(var_indices) + 1)
            ar = glpk.doubleArray(len(var_indices) + 1)
            for i, (var_idx, coeff) in enumerate(zip(var_indices, coeffs), start=1):
                ia[i] = var_idx
                ar[i] = coeff
            glpk.glp_set_mat_row(model, row_idx, len(var_indices), ia, ar)

        # Store in constraint map
        self._constraint_map[lx_constraint.name] = row_idx
        self._constraint_list.append(row_idx)

    def _create_indexed_constraints(
        self, lx_constraint: LXConstraint, instances: List[Any]
    ) -> None:
        """Create indexed family of GLPK constraints."""
        model = self._model
        assert model is not None

        if lx_constraint.lhs is None:
            raise ValueError(f"Constraint '{lx_constraint.name}' has no LHS expression")

        constraint_dict: Dict[Any, int] = {}

        for instance in instances:
            # Get index for naming
            if lx_constraint.index_func is not None:
                index_key = lx_constraint.index_func(instance)
            else:
                index_key = instance

            # Constraint name: "constraintname[index]"
            ct_name = f"{lx_constraint.name}[{index_key}]"

            # Get row index (1-based in GLPK)
            self._constraint_counter += 1
            row_idx = self._constraint_counter

            # Set constraint name
            glpk.glp_set_row_name(model, row_idx, ct_name)

            # Build expression for this instance
            var_indices, coeffs = self._build_expression(
                lx_constraint.lhs, constraint_instance=instance
            )

            # Get RHS value for this instance
            if lx_constraint.rhs_value is not None:
                rhs = lx_constraint.rhs_value
            elif lx_constraint.rhs_func is not None:
                rhs = lx_constraint.rhs_func(instance)
            else:
                raise ValueError(f"Constraint '{lx_constraint.name}' has no RHS value")

            # Set constraint bounds based on sense
            if lx_constraint.sense == LXConstraintSense.LE:
                glpk.glp_set_row_bnds(model, row_idx, glpk.GLP_UP, 0.0, rhs)
            elif lx_constraint.sense == LXConstraintSense.GE:
                glpk.glp_set_row_bnds(model, row_idx, glpk.GLP_LO, rhs, 0.0)
            elif lx_constraint.sense == LXConstraintSense.EQ:
                glpk.glp_set_row_bnds(model, row_idx, glpk.GLP_FX, rhs, rhs)
            else:
                raise ValueError(f"Unknown constraint sense: {lx_constraint.sense}")

            # Set constraint coefficients
            if var_indices:
                ia = glpk.intArray(len(var_indices) + 1)
                ar = glpk.doubleArray(len(var_indices) + 1)
                for i, (var_idx, coeff) in enumerate(zip(var_indices, coeffs), start=1):
                    ia[i] = var_idx
                    ar[i] = coeff
                glpk.glp_set_mat_row(model, row_idx, len(var_indices), ia, ar)

            constraint_dict[index_key] = row_idx
            self._constraint_list.append(row_idx)

        # Store dictionary in constraint map
        self._constraint_map[lx_constraint.name] = constraint_dict

    def _build_expression(
        self,
        lx_expr: LXLinearExpression,
        constraint_instance: Optional[Any] = None,
    ) -> Tuple[List[int], List[float]]:
        """
        Build GLPK expression from LXLinearExpression.

        Args:
            lx_expr: LumiX linear expression
            constraint_instance: Instance for indexed constraints

        Returns:
            Tuple of (variable_indices, coefficients)
        """
        var_indices: List[int] = []
        coefficients: List[float] = []

        # Process regular terms
        for var_name, (lx_var, coeff_func, where_func) in lx_expr.terms.items():
            solver_vars = self._variable_map[var_name]

            if isinstance(solver_vars, dict):
                # Indexed variable family
                instances = lx_var.get_instances()

                # If constraint instance is provided and matches variable type,
                # filter to only include the matching instance
                if constraint_instance is not None and constraint_instance in instances:
                    instances = [constraint_instance]

                for instance in instances:
                    # Check where clause
                    if not where_func(instance):
                        continue

                    # Get index key (handles cartesian products)
                    index_key = self._get_index_key(lx_var, instance)

                    # Get coefficient
                    if constraint_instance is not None:
                        try:
                            coeff = coeff_func(instance, constraint_instance)
                        except TypeError:
                            coeff = coeff_func(instance)
                    else:
                        coeff = coeff_func(instance)

                    if abs(coeff) > 1e-10:  # Skip near-zero coefficients
                        var_indices.append(solver_vars[index_key])
                        coefficients.append(coeff)
            else:
                # Single variable
                if constraint_instance is not None:
                    try:
                        coeff = coeff_func(constraint_instance)
                    except TypeError:
                        coeff = coeff_func(None)  # type: ignore
                else:
                    coeff = coeff_func(None)  # type: ignore

                if abs(coeff) > 1e-10:
                    var_indices.append(solver_vars)
                    coefficients.append(coeff)

        # Process multi-model terms
        for lx_var, coeff_func, where_func in lx_expr._multi_terms:
            solver_vars = self._variable_map[lx_var.name]

            if isinstance(solver_vars, dict):
                instances = lx_var.get_instances()

                for instance in instances:
                    # Check where clause
                    if where_func is not None:
                        if isinstance(instance, tuple):
                            if not where_func(*instance):
                                continue
                        else:
                            if not where_func(instance):
                                continue

                    # Get coefficient
                    if isinstance(instance, tuple):
                        coeff = coeff_func(*instance)
                    else:
                        coeff = coeff_func(instance)

                    # Get index key (handles cartesian products)
                    index_key = self._get_index_key(lx_var, instance)

                    if abs(coeff) > 1e-10:
                        var_indices.append(solver_vars[index_key])
                        coefficients.append(coeff)

        return var_indices, coefficients

    def _set_objective(self, model: LXModel) -> None:
        """Set objective function in GLPK model."""
        glpk_model = self._model
        assert glpk_model is not None

        if model.objective_expr is None:
            # No objective, just feasibility
            return

        # Build expression
        var_indices, coeffs = self._build_expression(model.objective_expr)

        # Set objective coefficients
        for var_idx, coeff in zip(var_indices, coeffs):
            glpk.glp_set_obj_coef(glpk_model, var_idx, coeff)

        # Set constant term
        if model.objective_expr.constant != 0:
            glpk.glp_set_obj_coef(glpk_model, 0, model.objective_expr.constant)

        # Set objective sense
        if model.objective_sense == LXObjectiveSense.MAXIMIZE:
            glpk.glp_set_obj_dir(glpk_model, glpk.GLP_MAX)
        else:
            glpk.glp_set_obj_dir(glpk_model, glpk.GLP_MIN)

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

        lx_status = status_map.get(status, "unknown")

        # Extract objective value
        obj_value = 0.0
        if status in [glpk.GLP_OPT, glpk.GLP_FEAS]:
            if is_mip:
                obj_value = glpk.glp_mip_obj_val(glpk_model)
            else:
                obj_value = glpk.glp_get_obj_val(glpk_model)

        # Extract variable values
        variables: Dict[str, Union[float, Dict[Any, float]]] = {}
        mapped: Dict[str, Dict[Any, float]] = {}

        if status in [glpk.GLP_OPT, glpk.GLP_FEAS]:
            for lx_var in model.variables:
                solver_vars = self._variable_map[lx_var.name]

                if isinstance(solver_vars, dict):
                    # Indexed variable family
                    var_values: Dict[Any, float] = {}
                    mapped_values: Dict[Any, float] = {}
                    instances = lx_var.get_instances()

                    for instance in instances:
                        # Get index key (handles cartesian products)
                        index_key = self._get_index_key(lx_var, instance)

                        col_idx = solver_vars[index_key]
                        if is_mip:
                            value = glpk.glp_mip_col_val(glpk_model, col_idx)
                        else:
                            value = glpk.glp_get_col_prim(glpk_model, col_idx)

                        var_values[index_key] = value
                        mapped_values[index_key] = value

                    variables[lx_var.name] = var_values
                    mapped[lx_var.name] = mapped_values
                else:
                    # Single variable
                    if is_mip:
                        value = glpk.glp_mip_col_val(glpk_model, solver_vars)
                    else:
                        value = glpk.glp_get_col_prim(glpk_model, solver_vars)
                    variables[lx_var.name] = value

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
