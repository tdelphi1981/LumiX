"""CPLEX solver implementation for LumiX."""

from __future__ import annotations

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
from ..core.expressions import LXLinearExpression
from ..core.model import LXModel
from ..core.variables import LXVariable
from ..solution.solution import LXSolution
from .base import LXSolverInterface
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
        self._constraint_list: List[int] = []
        self._variable_counter: int = 0

    def build_model(self, model: LXModel) -> Cplex:
        """
        Build CPLEX native model from LXModel.

        Args:
            model: LumiX model to build

        Returns:
            CPLEX Cplex instance

        Raises:
            ValueError: If model contains unsupported features
        """
        # Create CPLEX model instance
        self._model = Cplex()
        self._model.set_problem_name(model.name)

        # Reset internal state
        self._variable_map = {}
        self._constraint_list = []
        self._variable_counter = 0

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
                - output_clonelog: Show solver output (0=off, 1=on)

        Returns:
            Solution object with results

        TODO: Add support for additional features:
            - Warm start from previous solution
            - Solution pool for MIP
            - Callback functions
        """
        # Build the model
        cplex_model = self.build_model(model)

        # Suppress output by default
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
                elif param_name == "output_clonelog":
                    if param_value:
                        cplex_model.set_log_stream(None)
                else:
                    self.logger.logger.warning(
                        f"Unknown CPLEX parameter '{param_name}', skipping"
                    )
            except Exception as e:
                self.logger.logger.warning(
                    f"Failed to set CPLEX parameter '{param_name}': {e}"
                )

        # Solve
        start_time = time.time()
        try:
            cplex_model.solve()
        except CplexError as e:
            self.logger.logger.error(f"CPLEX solve error: {e}")
            # Continue to parse solution even if error (may have partial solution)
        solve_time = time.time() - start_time

        # Parse and return solution
        solution = self._parse_solution(model, cplex_model, solve_time)

        return solution

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
        """Create single CPLEX variable (not indexed)."""
        model = self._model
        assert model is not None

        # Get bounds
        lb = lx_var.lower_bound if lx_var.lower_bound is not None else -cplex.infinity
        ub = lx_var.upper_bound if lx_var.upper_bound is not None else cplex.infinity

        # Map variable type
        if lx_var.var_type == LXVarType.CONTINUOUS:
            vtype = model.variables.type.continuous
        elif lx_var.var_type == LXVarType.INTEGER:
            vtype = model.variables.type.integer
        elif lx_var.var_type == LXVarType.BINARY:
            vtype = model.variables.type.binary
        else:
            raise ValueError(f"Unknown variable type: {lx_var.var_type}")

        # Create variable using CPLEX list-based API
        var_idx = self._variable_counter
        model.variables.add(
            lb=[lb],
            ub=[ub],
            types=[vtype],
            names=[lx_var.name]
        )
        self._variable_counter += 1

        # Store in mapping
        self._variable_map[lx_var.name] = var_idx

    def _create_indexed_variables(
        self, lx_var: LXVariable, instances: List[Any]
    ) -> None:
        """Create indexed family of CPLEX variables."""
        model = self._model
        assert model is not None

        var_dict: Dict[Any, int] = {}

        # Prepare lists for batch creation
        lbs: List[float] = []
        ubs: List[float] = []
        types: List[str] = []
        names: List[str] = []
        index_keys: List[Any] = []

        for instance in instances:
            # Get index key (handles cartesian products)
            index_key = self._get_index_key(lx_var, instance)

            # Variable name: "varname[index]"
            var_name = f"{lx_var.name}[{index_key}]"

            # Get bounds (same for all instances for now)
            # TODO: Support per-instance bounds via bound functions
            lb = lx_var.lower_bound if lx_var.lower_bound is not None else -cplex.infinity
            ub = lx_var.upper_bound if lx_var.upper_bound is not None else cplex.infinity

            # Map variable type
            if lx_var.var_type == LXVarType.CONTINUOUS:
                vtype = model.variables.type.continuous
            elif lx_var.var_type == LXVarType.INTEGER:
                vtype = model.variables.type.integer
            elif lx_var.var_type == LXVarType.BINARY:
                vtype = model.variables.type.binary
            else:
                raise ValueError(f"Unknown variable type: {lx_var.var_type}")

            # Add to lists
            lbs.append(lb)
            ubs.append(ub)
            types.append(vtype)
            names.append(var_name)
            index_keys.append(index_key)

        # Create all variables in batch
        start_idx = self._variable_counter
        model.variables.add(
            lb=lbs,
            ub=ubs,
            types=types,
            names=names
        )

        # Map index keys to variable indices
        for i, index_key in enumerate(index_keys):
            var_dict[index_key] = start_idx + i

        self._variable_counter += len(instances)

        # Store dictionary in mapping
        self._variable_map[lx_var.name] = var_dict

    def _create_single_constraint(self, lx_constraint: LXConstraint) -> None:
        """Create single CPLEX constraint."""
        model = self._model
        assert model is not None

        if lx_constraint.lhs is None:
            raise ValueError(f"Constraint '{lx_constraint.name}' has no LHS expression")

        # Build linear expression
        var_indices, coeffs = self._build_expression(lx_constraint.lhs)

        # Get RHS value
        if lx_constraint.rhs_value is not None:
            rhs = lx_constraint.rhs_value
        elif lx_constraint.rhs_func is not None:
            # For single constraint with rhs function, call with None
            rhs = lx_constraint.rhs_func(None)  # type: ignore
        else:
            raise ValueError(f"Constraint '{lx_constraint.name}' has no RHS value")

        # Map constraint sense
        if lx_constraint.sense == LXConstraintSense.LE:
            sense = 'L'
        elif lx_constraint.sense == LXConstraintSense.GE:
            sense = 'G'
        elif lx_constraint.sense == LXConstraintSense.EQ:
            sense = 'E'
        else:
            raise ValueError(f"Unknown constraint sense: {lx_constraint.sense}")

        # Create constraint using CPLEX SparsePair format
        linear_expr = cplex.SparsePair(ind=var_indices, val=coeffs)
        model.linear_constraints.add(
            lin_expr=[linear_expr],
            senses=[sense],
            rhs=[rhs],
            names=[lx_constraint.name]
        )

        self._constraint_list.append(len(self._constraint_list))

    def _create_indexed_constraints(
        self, lx_constraint: LXConstraint, instances: List[Any]
    ) -> None:
        """Create indexed family of CPLEX constraints."""
        model = self._model
        assert model is not None

        if lx_constraint.lhs is None:
            raise ValueError(f"Constraint '{lx_constraint.name}' has no LHS expression")

        # Prepare lists for batch creation
        lin_exprs: List[cplex.SparsePair] = []
        senses: List[str] = []
        rhs_values: List[float] = []
        names: List[str] = []

        for instance in instances:
            # Get index for naming
            if lx_constraint.index_func is not None:
                index_key = lx_constraint.index_func(instance)
            else:
                index_key = instance

            # Constraint name: "constraintname[index]"
            ct_name = f"{lx_constraint.name}[{index_key}]"

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

            # Map constraint sense
            if lx_constraint.sense == LXConstraintSense.LE:
                sense = 'L'
            elif lx_constraint.sense == LXConstraintSense.GE:
                sense = 'G'
            elif lx_constraint.sense == LXConstraintSense.EQ:
                sense = 'E'
            else:
                raise ValueError(f"Unknown constraint sense: {lx_constraint.sense}")

            # Add to lists
            linear_expr = cplex.SparsePair(ind=var_indices, val=coeffs)
            lin_exprs.append(linear_expr)
            senses.append(sense)
            rhs_values.append(rhs)
            names.append(ct_name)

        # Create all constraints in batch
        model.linear_constraints.add(
            lin_expr=lin_exprs,
            senses=senses,
            rhs=rhs_values,
            names=names
        )

        self._constraint_list.extend(range(len(self._constraint_list), len(self._constraint_list) + len(instances)))

    def _build_expression(
        self,
        lx_expr: LXLinearExpression,
        constraint_instance: Optional[Any] = None,
    ) -> Tuple[List[int], List[float]]:
        """
        Build CPLEX expression from LXLinearExpression.

        Args:
            lx_expr: LumiX linear expression
            constraint_instance: Instance for indexed constraints (for multi-model coefficients)

        Returns:
            Tuple of (variable_indices, coefficients) for CPLEX SparsePair
        """
        var_indices: List[int] = []
        coefficients: List[float] = []

        # Process regular terms
        for var_name, (lx_var, coeff_func, where_func) in lx_expr.terms.items():
            solver_vars = self._variable_map[var_name]

            if isinstance(solver_vars, dict):
                # Indexed variable family
                instances = lx_var.get_instances()

                for instance in instances:
                    # Check where clause
                    if not where_func(instance):
                        continue

                    # Get index key (handles cartesian products)
                    index_key = self._get_index_key(lx_var, instance)

                    # Get coefficient
                    # For multi-model constraints, coefficient function may need both instances
                    if constraint_instance is not None:
                        # Try to call with both arguments (multi-model case)
                        try:
                            coeff = coeff_func(instance, constraint_instance)
                        except TypeError:
                            # Fall back to single argument
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
                        # Multi-model instances are tuples
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

        # Note: CPLEX handles constant terms differently in constraints
        # Constant is implicitly moved to RHS, so we don't include it here

        return var_indices, coefficients

    def _set_objective(self, model: LXModel) -> None:
        """Set objective function in CPLEX model."""
        cplex_model = self._model
        assert cplex_model is not None

        if model.objective_expr is None:
            # No objective, just feasibility
            return

        # Build expression
        var_indices, coeffs = self._build_expression(model.objective_expr)

        # Set linear objective coefficients
        for var_idx, coeff in zip(var_indices, coeffs):
            cplex_model.objective.set_linear(var_idx, coeff)

        # Handle constant term in objective
        if model.objective_expr.constant != 0:
            # CPLEX doesn't directly support constant in objective,
            # but it doesn't affect optimization (only the objective value)
            # We'll track it for solution reporting
            pass

        # Map objective sense
        if model.objective_sense == LXObjectiveSense.MAXIMIZE:
            cplex_model.objective.set_sense(cplex_model.objective.sense.maximize)
        else:
            cplex_model.objective.set_sense(cplex_model.objective.sense.minimize)

    def _parse_solution(
        self,
        model: LXModel,
        cplex_model: Cplex,
        solve_time: float,
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

        # CPLEX status codes (some common ones)
        # 1 = optimal, 2 = unbounded, 3 = infeasible, 4 = inf_or_unbd
        # 10 = node_limit, 11 = time_limit, 12 = dettime_limit
        # 13 = iteration_limit, etc.
        status_map = {
            1: "optimal",  # CPX_STAT_OPTIMAL
            2: "unbounded",  # CPX_STAT_UNBOUNDED
            3: "infeasible",  # CPX_STAT_INFEASIBLE
            4: "inf_or_unbounded",  # CPX_STAT_INForUNBD
            5: "optimal_infeasible",  # CPX_STAT_OPTIMAL_INFEAS
            6: "optimal",  # CPX_STAT_NUM_BEST - numerical best, treat as optimal
            10: "abort_obj_lim",  # CPX_STAT_ABORT_OBJ_LIM
            11: "time_limit",  # CPX_STAT_ABORT_TIME_LIM
            12: "abort_dettime_lim",  # CPX_STAT_ABORT_DETTIME_LIM
            13: "iteration_limit",  # CPX_STAT_ABORT_IT_LIM
            101: "optimal",  # CPXMIP_OPTIMAL_TOL - optimal within tolerance
            102: "solution_lim",  # CPXMIP_SOL_LIM
            103: "feasible",  # CPXMIP_NODE_LIM_FEAS
            104: "node_lim_infeas",  # CPXMIP_NODE_LIM_INFEAS
            105: "feasible",  # CPXMIP_TIME_LIM_FEAS
            106: "time_lim_infeas",  # CPXMIP_TIME_LIM_INFEAS
            107: "feasible",  # CPXMIP_FAIL_FEAS
            108: "fail_infeas",  # CPXMIP_FAIL_INFEAS
            109: "feasible",  # CPXMIP_MEM_LIM_FEAS
            110: "mem_lim_infeas",  # CPXMIP_MEM_LIM_INFEAS
            111: "feasible",  # CPXMIP_ABORT_FEAS
            112: "abort_infeas",  # CPXMIP_ABORT_INFEAS
            113: "optimal_infeas",  # CPXMIP_OPTIMAL_INFEAS
        }

        lx_status = status_map.get(status, f"unknown_{status}")

        # Extract objective value
        obj_value = 0.0
        if status in [1, 5, 6, 101, 103, 105, 107, 109, 111, 113]:  # Solution available
            try:
                obj_value = cplex_model.solution.get_objective_value()
                # Add constant term if present
                if model.objective_expr is not None and model.objective_expr.constant != 0:
                    obj_value += model.objective_expr.constant
            except CplexError:
                pass

        # Extract variable values
        variables: Dict[str, Union[float, Dict[Any, float]]] = {}
        mapped: Dict[str, Dict[Any, float]] = {}

        if status in [1, 5, 6, 101, 103, 105, 107, 109, 111, 113]:  # Solution available
            try:
                # Get all variable values at once
                all_values = cplex_model.solution.get_values()

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

                            var_idx = solver_vars[index_key]
                            value = all_values[var_idx]

                            var_values[index_key] = value
                            mapped_values[index_key] = value

                        variables[lx_var.name] = var_values
                        mapped[lx_var.name] = mapped_values
                    else:
                        # Single variable
                        value = all_values[solver_vars]
                        variables[lx_var.name] = value

            except CplexError as e:
                self.logger.logger.warning(f"Failed to extract variable values: {e}")

        # TODO: Extract sensitivity data (shadow prices, reduced costs)
        # Requires checking if model is LP (not MIP) and solution is optimal
        # Access via solution.get_dual_values() and solution.get_reduced_costs()
        shadow_prices: Dict[str, float] = {}
        reduced_costs: Dict[str, float] = {}

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
