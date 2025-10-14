"""OR-Tools solver implementation."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from ortools.linear_solver import pywraplp
except ImportError:
    pywraplp = None  # type: ignore

from ..core.constraints import LXConstraint
from ..core.enums import LXConstraintSense, LXObjectiveSense, LXVarType
from ..core.expressions import LXLinearExpression
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
        self._constraint_list: List[Any] = []

    def build_model(self, model: LXModel) -> pywraplp.Solver:
        """
        Build OR-Tools native model from LXModel.

        Args:
            model: LumiX model to build

        Returns:
            OR-Tools Solver instance

        Raises:
            ValueError: If model contains unsupported features
        """
        # Determine if we need integer solver or continuous
        has_integer = any(
            var.var_type in [LXVarType.INTEGER, LXVarType.BINARY]
            for var in model.variables
        )

        # Create solver instance
        # SCIP: Mixed-Integer Programming
        # GLOP: Linear Programming (faster for pure LP)
        solver_type = "SCIP" if has_integer else "GLOP"
        self._solver = pywraplp.Solver.CreateSolver(solver_type)

        if self._solver is None:
            raise RuntimeError(f"Failed to create OR-Tools solver ({solver_type})")

        # Reset internal state
        self._variable_map = {}
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

        return self._solver

    def solve(
        self,
        model: LXModel,
        time_limit: Optional[float] = None,
        gap_tolerance: Optional[float] = None,
        **solver_params: Any,
    ) -> LXSolution:
        """
        Solve optimization model with OR-Tools.

        Args:
            model: LumiX model to solve
            time_limit: Time limit in seconds (None = no limit)
            gap_tolerance: MIP gap tolerance (None = solver default)
            **solver_params: Additional solver-specific parameters

        Returns:
            Solution object with results

        TODO: Add support for additional parameters:
            - threads: Number of parallel threads
            - presolve: Enable/disable presolve
            - log_level: Logging verbosity
            - solution_pool_size: Number of solutions to keep (MIP)
        """
        # Build the model
        solver = self.build_model(model)

        # Set time limit (in milliseconds)
        if time_limit is not None:
            solver.SetTimeLimit(int(time_limit * 1000))

        # TODO: Set gap tolerance when OR-Tools exposes this parameter
        # Currently OR-Tools doesn't have a direct API for MIP gap tolerance

        # Set additional parameters
        # TODO: Add parameter mapping for OR-Tools specific options
        # e.g., solver.SetSolverSpecificParametersAsString(...)

        # Solve
        start_time = time.time()
        status = solver.Solve()
        solve_time = time.time() - start_time

        # Parse and return solution
        solution = self._parse_solution(model, solver, status, solve_time)

        return solution

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

    def _create_single_variable(self, lx_var: LXVariable) -> None:
        """Create single OR-Tools variable (not indexed)."""
        solver = self._solver
        assert solver is not None

        # Get bounds
        lb = lx_var.lower_bound if lx_var.lower_bound is not None else -solver.infinity()
        ub = lx_var.upper_bound if lx_var.upper_bound is not None else solver.infinity()

        # Create variable based on type
        if lx_var.var_type == LXVarType.CONTINUOUS:
            var = solver.NumVar(lb, ub, lx_var.name)
        elif lx_var.var_type == LXVarType.INTEGER:
            var = solver.IntVar(int(lb), int(ub), lx_var.name)
        elif lx_var.var_type == LXVarType.BINARY:
            var = solver.BoolVar(lx_var.name)
        else:
            raise ValueError(f"Unknown variable type: {lx_var.var_type}")

        # Store in mapping
        self._variable_map[lx_var.name] = var

    def _create_indexed_variables(
        self, lx_var: LXVariable, instances: List[Any]
    ) -> None:
        """Create indexed family of OR-Tools variables."""
        solver = self._solver
        assert solver is not None

        var_dict: Dict[Any, Any] = {}

        for instance in instances:
            # Get index for this instance
            if lx_var.index_func is not None:
                index_key = lx_var.index_func(instance)
            else:
                # For multi-model (tuple instances), use the tuple as key
                index_key = instance

            # Variable name: "varname[index]"
            var_name = f"{lx_var.name}[{index_key}]"

            # Get bounds (same for all instances for now)
            # TODO: Support per-instance bounds via bound functions
            lb = lx_var.lower_bound if lx_var.lower_bound is not None else -solver.infinity()
            ub = lx_var.upper_bound if lx_var.upper_bound is not None else solver.infinity()

            # Create OR-Tools variable
            if lx_var.var_type == LXVarType.CONTINUOUS:
                var = solver.NumVar(lb, ub, var_name)
            elif lx_var.var_type == LXVarType.INTEGER:
                var = solver.IntVar(int(lb), int(ub), var_name)
            elif lx_var.var_type == LXVarType.BINARY:
                var = solver.BoolVar(var_name)
            else:
                raise ValueError(f"Unknown variable type: {lx_var.var_type}")

            var_dict[index_key] = var

        # Store dictionary in mapping
        self._variable_map[lx_var.name] = var_dict

    def _create_single_constraint(self, lx_constraint: LXConstraint) -> None:
        """Create single OR-Tools constraint."""
        solver = self._solver
        assert solver is not None

        if lx_constraint.lhs is None:
            raise ValueError(f"Constraint '{lx_constraint.name}' has no LHS expression")

        # Build linear expression terms
        terms = self._build_expression(lx_constraint.lhs)

        # Get RHS value
        if lx_constraint.rhs_value is not None:
            rhs = lx_constraint.rhs_value
        elif lx_constraint.rhs_func is not None:
            # For single constraint with rhs function, call with None
            rhs = lx_constraint.rhs_func(None)  # type: ignore
        else:
            raise ValueError(f"Constraint '{lx_constraint.name}' has no RHS value")

        # Create constraint based on sense
        if lx_constraint.sense == LXConstraintSense.LE:
            ct = solver.Constraint(-solver.infinity(), rhs, lx_constraint.name)
        elif lx_constraint.sense == LXConstraintSense.GE:
            ct = solver.Constraint(rhs, solver.infinity(), lx_constraint.name)
        elif lx_constraint.sense == LXConstraintSense.EQ:
            ct = solver.Constraint(rhs, rhs, lx_constraint.name)
        else:
            raise ValueError(f"Unknown constraint sense: {lx_constraint.sense}")

        # Add terms to constraint
        for var, coeff in terms:
            ct.SetCoefficient(var, coeff)

        self._constraint_list.append(ct)

    def _create_indexed_constraints(
        self, lx_constraint: LXConstraint, instances: List[Any]
    ) -> None:
        """Create indexed family of OR-Tools constraints."""
        solver = self._solver
        assert solver is not None

        if lx_constraint.lhs is None:
            raise ValueError(f"Constraint '{lx_constraint.name}' has no LHS expression")

        for instance in instances:
            # Get index for naming
            if lx_constraint.index_func is not None:
                index_key = lx_constraint.index_func(instance)
            else:
                index_key = instance

            # Constraint name: "constraintname[index]"
            ct_name = f"{lx_constraint.name}[{index_key}]"

            # Build expression for this instance
            terms = self._build_expression(lx_constraint.lhs, constraint_instance=instance)

            # Get RHS value for this instance
            if lx_constraint.rhs_value is not None:
                rhs = lx_constraint.rhs_value
            elif lx_constraint.rhs_func is not None:
                rhs = lx_constraint.rhs_func(instance)
            else:
                raise ValueError(f"Constraint '{lx_constraint.name}' has no RHS value")

            # Create constraint
            if lx_constraint.sense == LXConstraintSense.LE:
                ct = solver.Constraint(-solver.infinity(), rhs, ct_name)
            elif lx_constraint.sense == LXConstraintSense.GE:
                ct = solver.Constraint(rhs, solver.infinity(), ct_name)
            elif lx_constraint.sense == LXConstraintSense.EQ:
                ct = solver.Constraint(rhs, rhs, ct_name)
            else:
                raise ValueError(f"Unknown constraint sense: {lx_constraint.sense}")

            # Add terms
            for var, coeff in terms:
                ct.SetCoefficient(var, coeff)

            self._constraint_list.append(ct)

    def _build_expression(
        self,
        lx_expr: LXLinearExpression,
        constraint_instance: Optional[Any] = None,
    ) -> List[Tuple[Any, float]]:
        """
        Build OR-Tools expression from LXLinearExpression.

        Args:
            lx_expr: LumiX linear expression
            constraint_instance: Instance for indexed constraints (for multi-model coefficients)

        Returns:
            List of (OR-Tools variable, coefficient) tuples
        """
        terms: List[Tuple[Any, float]] = []

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

                    # Get index key
                    if lx_var.index_func is not None:
                        index_key = lx_var.index_func(instance)
                    else:
                        index_key = instance

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
                        terms.append((solver_vars[index_key], coeff))
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
                    terms.append((solver_vars, coeff))

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

                    # Get index key
                    if lx_var.index_func is not None:
                        index_key = lx_var.index_func(instance)
                    else:
                        index_key = instance

                    if abs(coeff) > 1e-10:
                        terms.append((solver_vars[index_key], coeff))

        return terms

    def _set_objective(self, model: LXModel) -> None:
        """Set objective function in OR-Tools solver."""
        solver = self._solver
        assert solver is not None

        if model.objective_expr is None:
            # No objective, just feasibility
            return

        # Get objective function
        objective = solver.Objective()

        # Build expression terms
        terms = self._build_expression(model.objective_expr)

        # Set coefficients
        for var, coeff in terms:
            objective.SetCoefficient(var, coeff)

        # Set constant term
        objective.SetOffset(model.objective_expr.constant)

        # Set sense (maximize or minimize)
        if model.objective_sense == LXObjectiveSense.MAXIMIZE:
            objective.SetMaximization()
        else:
            objective.SetMinimization()

    def _parse_solution(
        self,
        model: LXModel,
        solver: pywraplp.Solver,
        status: int,
        solve_time: float,
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

        # Extract objective value
        if status in [pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE]:
            obj_value = solver.Objective().Value()
        else:
            obj_value = 0.0

        # Extract variable values
        variables: Dict[str, Union[float, Dict[Any, float]]] = {}
        mapped: Dict[str, Dict[Any, float]] = {}

        for lx_var in model.variables:
            solver_vars = self._variable_map[lx_var.name]

            if isinstance(solver_vars, dict):
                # Indexed variable family
                var_values: Dict[Any, float] = {}
                mapped_values: Dict[Any, float] = {}
                instances = lx_var.get_instances()

                for instance in instances:
                    # Get index key
                    if lx_var.index_func is not None:
                        index_key = lx_var.index_func(instance)
                    else:
                        index_key = instance

                    var = solver_vars[index_key]
                    value = var.solution_value()

                    var_values[index_key] = value
                    # Use index_key instead of instance to avoid hashability issues
                    # with non-frozen dataclasses
                    mapped_values[index_key] = value

                variables[lx_var.name] = var_values
                mapped[lx_var.name] = mapped_values
            else:
                # Single variable
                value = solver_vars.solution_value()
                variables[lx_var.name] = value

        # TODO: Extract sensitivity data (shadow prices, reduced costs)
        # OR-Tools doesn't expose dual values as easily as Gurobi/CPLEX
        # May need to use basis status: solver.ComputeConstraintActivities()
        shadow_prices: Dict[str, float] = {}
        reduced_costs: Dict[str, float] = {}

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
