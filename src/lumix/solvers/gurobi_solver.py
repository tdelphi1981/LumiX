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
from ..core.expressions import LXLinearExpression
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
        """
        Build Gurobi native model from LXModel.

        Args:
            model: LumiX model to build

        Returns:
            Gurobi Model instance

        Raises:
            ValueError: If model contains unsupported features
        """
        # Create Gurobi model instance
        self._model = gp.Model(model.name)

        # Reset internal state
        self._variable_map = {}
        self._constraint_map = {}
        self._constraint_list = []

        # Build variables
        for lx_var in model.variables:
            instances = lx_var.get_instances()

            if not instances:
                # Single variable (not indexed)
                self._create_single_variable(lx_var)
            else:
                # Variable family (indexed by data)
                self._create_indexed_variables(lx_var, instances)

        # Update model to integrate new variables
        self._model.update()

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

        # Update model to integrate constraints and objective
        self._model.update()

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
        """Create single Gurobi variable (not indexed)."""
        model = self._model
        assert model is not None

        # Get bounds
        lb = lx_var.lower_bound if lx_var.lower_bound is not None else -GRB.INFINITY
        ub = lx_var.upper_bound if lx_var.upper_bound is not None else GRB.INFINITY

        # Map variable type
        if lx_var.var_type == LXVarType.CONTINUOUS:
            vtype = GRB.CONTINUOUS
        elif lx_var.var_type == LXVarType.INTEGER:
            vtype = GRB.INTEGER
        elif lx_var.var_type == LXVarType.BINARY:
            vtype = GRB.BINARY
        else:
            raise ValueError(f"Unknown variable type: {lx_var.var_type}")

        # Create variable
        var = model.addVar(
            lb=lb,
            ub=ub,
            vtype=vtype,
            name=lx_var.name
        )

        # Store in mapping
        self._variable_map[lx_var.name] = var

    def _create_indexed_variables(
        self, lx_var: LXVariable, instances: List[Any]
    ) -> None:
        """Create indexed family of Gurobi variables."""
        model = self._model
        assert model is not None

        var_dict: Dict[Any, Any] = {}

        for instance in instances:
            # Get index key (handles cartesian products)
            index_key = self._get_index_key(lx_var, instance)

            # Variable name: "varname[index]"
            var_name = f"{lx_var.name}[{index_key}]"

            # Get bounds (same for all instances for now)
            # TODO: Support per-instance bounds via bound functions
            lb = lx_var.lower_bound if lx_var.lower_bound is not None else -GRB.INFINITY
            ub = lx_var.upper_bound if lx_var.upper_bound is not None else GRB.INFINITY

            # Map variable type
            if lx_var.var_type == LXVarType.CONTINUOUS:
                vtype = GRB.CONTINUOUS
            elif lx_var.var_type == LXVarType.INTEGER:
                vtype = GRB.INTEGER
            elif lx_var.var_type == LXVarType.BINARY:
                vtype = GRB.BINARY
            else:
                raise ValueError(f"Unknown variable type: {lx_var.var_type}")

            # Create Gurobi variable
            var = model.addVar(
                lb=lb,
                ub=ub,
                vtype=vtype,
                name=var_name
            )

            var_dict[index_key] = var

        # Store dictionary in mapping
        self._variable_map[lx_var.name] = var_dict

    def _create_single_constraint(self, lx_constraint: LXConstraint) -> None:
        """Create single Gurobi constraint."""
        model = self._model
        assert model is not None

        if lx_constraint.lhs is None:
            raise ValueError(f"Constraint '{lx_constraint.name}' has no LHS expression")

        # Build linear expression
        expr = self._build_expression(lx_constraint.lhs)

        # Get RHS value
        if lx_constraint.rhs_value is not None:
            rhs = lx_constraint.rhs_value
        elif lx_constraint.rhs_func is not None:
            # For single constraint with rhs function, call with None
            rhs = lx_constraint.rhs_func(None)  # type: ignore
        else:
            raise ValueError(f"Constraint '{lx_constraint.name}' has no RHS value")

        # Create constraint with appropriate sense
        # Note: Gurobi requires using Python operators (<=, >=, ==) to form constraint
        if lx_constraint.sense == LXConstraintSense.LE:
            constr = model.addConstr(expr <= rhs, name=lx_constraint.name)
        elif lx_constraint.sense == LXConstraintSense.GE:
            constr = model.addConstr(expr >= rhs, name=lx_constraint.name)
        elif lx_constraint.sense == LXConstraintSense.EQ:
            constr = model.addConstr(expr == rhs, name=lx_constraint.name)
        else:
            raise ValueError(f"Unknown constraint sense: {lx_constraint.sense}")

        # Store in constraint map
        self._constraint_map[lx_constraint.name] = constr
        self._constraint_list.append(constr)

    def _create_indexed_constraints(
        self, lx_constraint: LXConstraint, instances: List[Any]
    ) -> None:
        """Create indexed family of Gurobi constraints."""
        model = self._model
        assert model is not None

        if lx_constraint.lhs is None:
            raise ValueError(f"Constraint '{lx_constraint.name}' has no LHS expression")

        # Dictionary to store indexed constraints
        constraint_dict: Dict[Any, Any] = {}

        for instance in instances:
            # Get index for naming
            if lx_constraint.index_func is not None:
                index_key = lx_constraint.index_func(instance)
            else:
                index_key = instance

            # Constraint name: "constraintname[index]"
            ct_name = f"{lx_constraint.name}[{index_key}]"

            # Build expression for this instance
            expr = self._build_expression(lx_constraint.lhs, constraint_instance=instance)

            # Get RHS value for this instance
            if lx_constraint.rhs_value is not None:
                rhs = lx_constraint.rhs_value
            elif lx_constraint.rhs_func is not None:
                rhs = lx_constraint.rhs_func(instance)
            else:
                raise ValueError(f"Constraint '{lx_constraint.name}' has no RHS value")

            # Create constraint with appropriate sense
            # Note: Gurobi requires using Python operators (<=, >=, ==) to form constraint
            if lx_constraint.sense == LXConstraintSense.LE:
                constr = model.addConstr(expr <= rhs, name=ct_name)
            elif lx_constraint.sense == LXConstraintSense.GE:
                constr = model.addConstr(expr >= rhs, name=ct_name)
            elif lx_constraint.sense == LXConstraintSense.EQ:
                constr = model.addConstr(expr == rhs, name=ct_name)
            else:
                raise ValueError(f"Unknown constraint sense: {lx_constraint.sense}")

            # Store in constraint dictionary
            constraint_dict[index_key] = constr
            self._constraint_list.append(constr)

        # Store dictionary in constraint map
        self._constraint_map[lx_constraint.name] = constraint_dict

    def _build_expression(
        self,
        lx_expr: LXLinearExpression,
        constraint_instance: Optional[Any] = None,
    ) -> gp.LinExpr:
        """
        Build Gurobi LinExpr from LXLinearExpression.

        Args:
            lx_expr: LumiX linear expression
            constraint_instance: Instance for indexed constraints (for multi-model coefficients)

        Returns:
            Gurobi LinExpr object
        """
        expr = gp.LinExpr()

        # Process regular terms
        for var_name, (lx_var, coeff_func, where_func) in lx_expr.terms.items():
            solver_vars = self._variable_map[var_name]

            if isinstance(solver_vars, dict):
                # Indexed variable family
                instances = lx_var.get_instances()

                # If constraint instance is provided and matches variable type,
                # filter to only include the matching instance
                if constraint_instance is not None and constraint_instance in instances:
                    # Same-type constraint: only use matching instance
                    instances = [constraint_instance]

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
                        expr.addTerms(coeff, solver_vars[index_key])
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
                    expr.addTerms(coeff, solver_vars)

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
                        expr.addTerms(coeff, solver_vars[index_key])

        # Add constant term
        expr.addConstant(lx_expr.constant)

        return expr

    def _set_objective(self, model: LXModel) -> None:
        """Set objective function in Gurobi model."""
        gurobi_model = self._model
        assert gurobi_model is not None

        if model.objective_expr is None:
            # No objective, just feasibility
            return

        # Build expression
        expr = self._build_expression(model.objective_expr)

        # Map objective sense
        if model.objective_sense == LXObjectiveSense.MAXIMIZE:
            sense = GRB.MAXIMIZE
        else:
            sense = GRB.MINIMIZE

        # Set objective
        gurobi_model.setObjective(expr, sense)

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

        # Extract objective value
        if status in [GRB.OPTIMAL, GRB.SUBOPTIMAL]:
            try:
                obj_value = gurobi_model.ObjVal
            except Exception:
                obj_value = 0.0
        else:
            obj_value = 0.0

        # Extract variable values
        variables: Dict[str, Union[float, Dict[Any, float]]] = {}
        mapped: Dict[str, Dict[Any, float]] = {}

        if status in [GRB.OPTIMAL, GRB.SUBOPTIMAL]:
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

                        var = solver_vars[index_key]
                        try:
                            value = var.X
                        except Exception:
                            value = 0.0

                        var_values[index_key] = value
                        mapped_values[index_key] = value

                    variables[lx_var.name] = var_values
                    mapped[lx_var.name] = mapped_values
                else:
                    # Single variable
                    try:
                        value = solver_vars.X
                    except Exception:
                        value = 0.0
                    variables[lx_var.name] = value

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
            if gurobi_model.IsMIP and status in [GRB.OPTIMAL, GRB.SUBOPTIMAL]:
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
