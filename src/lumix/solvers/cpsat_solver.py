"""OR-Tools CP-SAT solver implementation for LumiX."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from ortools.sat.python import cp_model
except ImportError:
    cp_model = None  # type: ignore

from ..core.constraints import LXConstraint
from ..core.enums import LXConstraintSense, LXObjectiveSense, LXVarType
from ..core.expressions import LXLinearExpression
from ..core.model import LXModel
from ..core.variables import LXVariable
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

    def __init__(
        self,
        rational_max_denom: int = 10000,
        scale_objective: bool = True,
        auto_scale_continuous: bool = False,
        scaling_factor: int = 1000,
    ) -> None:
        """
        Initialize CP-SAT solver.

        Args:
            rational_max_denom: Maximum denominator for float-to-rational conversion
            scale_objective: Whether to scale objective coefficients to integers
            auto_scale_continuous: Automatically scale continuous variables to integers
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
        self._scale_objective = scale_objective
        self._objective_scale: int = 1

        # Auto-scaling for continuous variables
        self.auto_scale_continuous = auto_scale_continuous
        self._scaling_factor = scaling_factor
        self._scaled_variables: set = set()  # Names of variables that were scaled
        self._variable_scales: Dict[str, int] = {}  # Variable name -> scale factor
        self._objective_has_scaled_vars: bool = False  # Track if objective needs de-scaling
        self._objective_coeff_scale: int = 1  # Coefficient scale from rational conversion

    def build_model(self, model: LXModel) -> cp_model.CpModel:
        """
        Build CP-SAT native model from LXModel.

        Args:
            model: LumiX model to build

        Returns:
            CP-SAT CpModel instance

        Raises:
            ValueError: If model contains continuous variables or unsupported features
        """
        # Check for continuous variables (not supported by CP-SAT)
        continuous_vars = [
            var.name for var in model.variables
            if var.var_type == LXVarType.CONTINUOUS
        ]
        if continuous_vars:
            if not self.auto_scale_continuous:
                raise ValueError(
                    f"CP-SAT does not support continuous variables. "
                    f"Found continuous variables: {', '.join(continuous_vars)}.\n"
                    f"Options:\n"
                    f"  1. Use integer/binary variables only\n"
                    f"  2. Switch to 'ortools', 'gurobi', or 'cplex' solvers\n"
                    f"  3. Enable auto-scaling: LXCPSATSolver(auto_scale_continuous=True)\n"
                    f"     This will scale continuous variables to integers and de-scale solutions."
                )
            else:
                # Auto-scaling enabled: warn and proceed
                self._log_scaling_warning(continuous_vars)
                # Track which variables will be scaled
                self._scaled_variables = set(continuous_vars)
                for var_name in continuous_vars:
                    self._variable_scales[var_name] = self._scaling_factor

        # Create CP-SAT model instance
        self._model = cp_model.CpModel()

        # Reset internal state
        self._variable_map = {}
        self._constraint_list = []
        self._objective_scale = 1

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
        Solve optimization model with CP-SAT.

        Args:
            model: LumiX model to solve
            time_limit: Time limit in seconds (None = no limit)
            gap_tolerance: Relative optimality gap tolerance (None = 0.0001)
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
        # Build the model
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
        """Log warning about automatic continuous variable scaling."""
        self.logger.logger.warning("")
        self.logger.logger.warning("╔════════════════════════════════════════════════════════════╗")
        self.logger.logger.warning("║     CP-SAT: AUTO-SCALING CONTINUOUS VARIABLES              ║")
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

    def _create_single_variable(self, lx_var: LXVariable) -> None:
        """Create single CP-SAT variable (not indexed)."""
        model = self._model
        assert model is not None

        # Get bounds (CP-SAT requires integer bounds)
        lb = lx_var.lower_bound if lx_var.lower_bound is not None else cp_model.INT32_MIN
        ub = lx_var.upper_bound if lx_var.upper_bound is not None else cp_model.INT32_MAX

        # Create variable based on type
        if lx_var.var_type == LXVarType.BINARY:
            var = model.NewBoolVar(lx_var.name)
        elif lx_var.var_type == LXVarType.INTEGER:
            # Ensure integer bounds
            lb = int(lb)
            ub = int(ub)
            var = model.NewIntVar(lb, ub, lx_var.name)
        elif lx_var.var_type == LXVarType.CONTINUOUS:
            if not self.auto_scale_continuous:
                raise ValueError(
                    f"CP-SAT does not support continuous variables. "
                    f"Variable '{lx_var.name}' is continuous."
                )
            # Auto-scale: convert continuous to integer
            scale = self._variable_scales.get(lx_var.name, self._scaling_factor)
            lb_scaled = int(lb * scale) if lb != cp_model.INT32_MIN else cp_model.INT32_MIN
            ub_scaled = int(ub * scale) if ub != cp_model.INT32_MAX else cp_model.INT32_MAX
            var = model.NewIntVar(lb_scaled, ub_scaled, lx_var.name)
        else:
            raise ValueError(f"Unknown variable type: {lx_var.var_type}")

        # Store in mapping
        self._variable_map[lx_var.name] = var

    def _create_indexed_variables(
        self, lx_var: LXVariable, instances: List[Any]
    ) -> None:
        """Create indexed family of CP-SAT variables."""
        model = self._model
        assert model is not None

        var_dict: Dict[Any, Any] = {}

        for instance in instances:
            # Get index for this instance
            if lx_var.index_func is not None:
                index_key = lx_var.index_func(instance)
            elif lx_var._cartesian is not None:
                # For cartesian products, build key from dimension key functions
                if isinstance(instance, tuple):
                    # Apply each dimension's key function to its corresponding element
                    index_key = tuple(
                        dim.key_func(inst)
                        for dim, inst in zip(lx_var._cartesian.dimensions, instance)
                    )
                else:
                    index_key = instance
            else:
                # For multi-model (tuple instances), use the tuple as key
                # This may fail if instances are not hashable
                index_key = instance

            # Variable name: "varname[index]"
            var_name = f"{lx_var.name}[{index_key}]"

            # Get bounds (same for all instances for now)
            # TODO: Support per-instance bounds via bound functions
            lb = lx_var.lower_bound if lx_var.lower_bound is not None else cp_model.INT32_MIN
            ub = lx_var.upper_bound if lx_var.upper_bound is not None else cp_model.INT32_MAX

            # Create CP-SAT variable based on type
            if lx_var.var_type == LXVarType.BINARY:
                var = model.NewBoolVar(var_name)
            elif lx_var.var_type == LXVarType.INTEGER:
                # Ensure integer bounds
                lb = int(lb)
                ub = int(ub)
                var = model.NewIntVar(lb, ub, var_name)
            elif lx_var.var_type == LXVarType.CONTINUOUS:
                if not self.auto_scale_continuous:
                    raise ValueError(
                        f"CP-SAT does not support continuous variables. "
                        f"Variable '{lx_var.name}' is continuous."
                    )
                # Auto-scale: convert continuous to integer
                scale = self._variable_scales.get(lx_var.name, self._scaling_factor)
                lb_scaled = int(lb * scale) if lb != cp_model.INT32_MIN else cp_model.INT32_MIN
                ub_scaled = int(ub * scale) if ub != cp_model.INT32_MAX else cp_model.INT32_MAX
                var = model.NewIntVar(lb_scaled, ub_scaled, var_name)
            else:
                raise ValueError(f"Unknown variable type: {lx_var.var_type}")

            var_dict[index_key] = var

        # Store dictionary in mapping
        self._variable_map[lx_var.name] = var_dict

    def _create_single_constraint(self, lx_constraint: LXConstraint) -> None:
        """Create single CP-SAT constraint."""
        model = self._model
        assert model is not None

        if lx_constraint.lhs is None:
            raise ValueError(f"Constraint '{lx_constraint.name}' has no LHS expression")

        # Build linear expression with integer coefficients
        terms, int_coeffs = self._build_expression(lx_constraint.lhs)

        # Get RHS value
        if lx_constraint.rhs_value is not None:
            rhs = lx_constraint.rhs_value
        elif lx_constraint.rhs_func is not None:
            # For single constraint with rhs function, call with None
            rhs = lx_constraint.rhs_func(None)  # type: ignore
        else:
            raise ValueError(f"Constraint '{lx_constraint.name}' has no RHS value")

        # Scale RHS if constraint involves scaled variables
        # Original: sum(coeff * var_cont) <= RHS
        # Scaled: sum(coeff * var_int / scale) <= RHS
        # Multiply both sides by scale: sum(coeff * var_int) <= RHS * scale
        rhs_scaled = self._scale_rhs_if_needed(lx_constraint.lhs, rhs)

        # Convert RHS to integer
        if not isinstance(rhs_scaled, int):
            rhs_scaled = int(round(rhs_scaled))

        # Build linear expression
        if not terms:
            # Empty constraint (0 sense rhs)
            linear_expr = 0
        else:
            linear_expr = sum(var * coeff for var, coeff in zip(terms, int_coeffs))

        # Create constraint based on sense
        if lx_constraint.sense == LXConstraintSense.LE:
            ct = model.Add(linear_expr <= rhs_scaled)
        elif lx_constraint.sense == LXConstraintSense.GE:
            ct = model.Add(linear_expr >= rhs_scaled)
        elif lx_constraint.sense == LXConstraintSense.EQ:
            ct = model.Add(linear_expr == rhs_scaled)
        else:
            raise ValueError(f"Unknown constraint sense: {lx_constraint.sense}")

        # Set constraint name (for debugging)
        ct.Proto().name = lx_constraint.name

        self._constraint_list.append(ct)

    def _create_indexed_constraints(
        self, lx_constraint: LXConstraint, instances: List[Any]
    ) -> None:
        """Create indexed family of CP-SAT constraints."""
        model = self._model
        assert model is not None

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
            terms, int_coeffs = self._build_expression(
                lx_constraint.lhs, constraint_instance=instance
            )

            # Get RHS value for this instance
            if lx_constraint.rhs_value is not None:
                rhs = lx_constraint.rhs_value
            elif lx_constraint.rhs_func is not None:
                rhs = lx_constraint.rhs_func(instance)
            else:
                raise ValueError(f"Constraint '{lx_constraint.name}' has no RHS value")

            # Scale RHS if constraint involves scaled variables
            rhs_scaled = self._scale_rhs_if_needed(lx_constraint.lhs, rhs)

            # Convert RHS to integer
            if not isinstance(rhs_scaled, int):
                rhs_scaled = int(round(rhs_scaled))

            # Build linear expression
            if not terms:
                # Empty constraint
                linear_expr = 0
            else:
                linear_expr = sum(var * coeff for var, coeff in zip(terms, int_coeffs))

            # Create constraint
            if lx_constraint.sense == LXConstraintSense.LE:
                ct = model.Add(linear_expr <= rhs_scaled)
            elif lx_constraint.sense == LXConstraintSense.GE:
                ct = model.Add(linear_expr >= rhs_scaled)
            elif lx_constraint.sense == LXConstraintSense.EQ:
                ct = model.Add(linear_expr == rhs_scaled)
            else:
                raise ValueError(f"Unknown constraint sense: {lx_constraint.sense}")

            # Set constraint name
            ct.Proto().name = ct_name

            self._constraint_list.append(ct)

    def _scale_rhs_if_needed(self, lx_expr: LXLinearExpression, rhs: float) -> float:
        """
        Scale RHS if expression contains scaled variables.

        When variables are scaled (var_int = var_cont * scale), constraints must be adjusted:
        Original: sum(coeff * var_cont) <= RHS
        Scaled: sum(coeff * var_int / scale) <= RHS
        Multiply both sides by scale: sum(coeff * var_int) <= RHS * scale

        Args:
            lx_expr: Expression to check
            rhs: Original RHS value

        Returns:
            Scaled RHS if any variables are scaled, otherwise original RHS
        """
        # Check if any variables in the expression are scaled
        has_scaled_vars = False

        # Check regular terms
        for var_name in lx_expr.terms.keys():
            if var_name in self._scaled_variables:
                has_scaled_vars = True
                break

        # Check multi-model terms
        if not has_scaled_vars:
            for lx_var, _, _ in lx_expr._multi_terms:
                if lx_var.name in self._scaled_variables:
                    has_scaled_vars = True
                    break

        # If any scaled variables, multiply RHS by the scale factor
        if has_scaled_vars:
            # Assume uniform scaling for now (all variables have same scale)
            scale = self._scaling_factor
            return rhs * scale

        return rhs

    def _build_expression(
        self,
        lx_expr: LXLinearExpression,
        constraint_instance: Optional[Any] = None,
    ) -> Tuple[List[Any], List[int]]:
        """
        Build CP-SAT expression from LXLinearExpression.

        Converts float coefficients to integers using rational approximation.

        Args:
            lx_expr: LumiX linear expression
            constraint_instance: Instance for indexed constraints (for multi-model coefficients)

        Returns:
            Tuple of (CP-SAT variables, integer coefficients)
        """
        terms: List[Any] = []
        float_coeffs: List[float] = []

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
                    elif lx_var._cartesian is not None and isinstance(instance, tuple):
                        # For cartesian products, build key from dimension key functions
                        index_key = tuple(
                            dim.key_func(inst)
                            for dim, inst in zip(lx_var._cartesian.dimensions, instance)
                        )
                    else:
                        index_key = instance

                    # Get coefficient
                    if constraint_instance is not None:
                        try:
                            coeff = coeff_func(instance, constraint_instance)
                        except TypeError:
                            coeff = coeff_func(instance)
                    else:
                        coeff = coeff_func(instance)

                    # Note: For scaled variables, coefficients stay the same
                    # but RHS will be scaled instead (see _create_single_constraint)

                    if abs(coeff) > 1e-10:  # Skip near-zero coefficients
                        terms.append(solver_vars[index_key])
                        float_coeffs.append(coeff)
            else:
                # Single variable
                if constraint_instance is not None:
                    try:
                        coeff = coeff_func(constraint_instance)
                    except TypeError:
                        coeff = coeff_func(None)  # type: ignore
                else:
                    coeff = coeff_func(None)  # type: ignore

                # Note: Coefficients stay the same for scaled variables
                # RHS will be scaled instead

                if abs(coeff) > 1e-10:
                    terms.append(solver_vars)
                    float_coeffs.append(coeff)

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

                    # Note: Coefficients stay the same for scaled variables
                    # RHS will be scaled instead

                    # Get index key
                    if lx_var.index_func is not None:
                        index_key = lx_var.index_func(instance)
                    elif lx_var._cartesian is not None and isinstance(instance, tuple):
                        # For cartesian products, build key from dimension key functions
                        index_key = tuple(
                            dim.key_func(inst)
                            for dim, inst in zip(lx_var._cartesian.dimensions, instance)
                        )
                    else:
                        index_key = instance

                    if abs(coeff) > 1e-10:
                        terms.append(solver_vars[index_key])
                        float_coeffs.append(coeff)

        # Convert float coefficients to integers
        int_coeffs, coeff_scale = self._convert_coefficients_to_integers(float_coeffs)

        return terms, int_coeffs

    def _convert_coefficients_to_integers(self, coeffs: List[float]) -> Tuple[List[int], int]:
        """
        Convert float coefficients to integers using rational approximation.

        Args:
            coeffs: List of float coefficients

        Returns:
            Tuple of (integer coefficients, common scale factor)
        """
        # Check if all coefficients are already integers
        if all(isinstance(c, int) or c.is_integer() for c in coeffs):
            return [int(c) for c in coeffs], 1

        # Use rational converter for float coefficients
        coeff_dict = {i: c for i, c in enumerate(coeffs)}
        int_coeff_dict, scale = self._rational_converter.convert_coefficients(coeff_dict)

        # Return scaled integer coefficients and scale factor
        return [int_coeff_dict[i] for i in range(len(coeffs))], scale

    def _set_objective(self, model: LXModel) -> None:
        """Set objective function in CP-SAT model."""
        cpsat_model = self._model
        assert cpsat_model is not None

        if model.objective_expr is None:
            # No objective, just feasibility
            return

        # Check if objective involves scaled variables (for later de-scaling)
        self._objective_has_scaled_vars = False
        if model.objective_expr:
            # Check regular terms
            for var_name in model.objective_expr.terms.keys():
                if var_name in self._scaled_variables:
                    self._objective_has_scaled_vars = True
                    break
            # Check multi-model terms
            if not self._objective_has_scaled_vars:
                for lx_var, _, _ in model.objective_expr._multi_terms:
                    if lx_var.name in self._scaled_variables:
                        self._objective_has_scaled_vars = True
                        break

        # Build expression - need to handle scaling manually for objective
        terms: List[Any] = []
        float_coeffs: List[float] = []

        # Collect terms and coefficients from objective expression
        for var_name, (lx_var, coeff_func, where_func) in model.objective_expr.terms.items():
            solver_vars = self._variable_map[var_name]
            if isinstance(solver_vars, dict):
                instances = lx_var.get_instances()
                for instance in instances:
                    if not where_func(instance):
                        continue
                    if lx_var.index_func is not None:
                        index_key = lx_var.index_func(instance)
                    elif lx_var._cartesian is not None and isinstance(instance, tuple):
                        index_key = tuple(
                            dim.key_func(inst)
                            for dim, inst in zip(lx_var._cartesian.dimensions, instance)
                        )
                    else:
                        index_key = instance
                    coeff = coeff_func(instance)
                    if abs(coeff) > 1e-10:
                        terms.append(solver_vars[index_key])
                        float_coeffs.append(coeff)
            else:
                coeff = coeff_func(None)  # type: ignore
                if abs(coeff) > 1e-10:
                    terms.append(solver_vars)
                    float_coeffs.append(coeff)

        # Handle multi-model terms
        for lx_var, coeff_func, where_func in model.objective_expr._multi_terms:
            solver_vars = self._variable_map[lx_var.name]
            if isinstance(solver_vars, dict):
                instances = lx_var.get_instances()
                for instance in instances:
                    if where_func is not None:
                        if isinstance(instance, tuple):
                            if not where_func(*instance):
                                continue
                        else:
                            if not where_func(instance):
                                continue
                    if isinstance(instance, tuple):
                        coeff = coeff_func(*instance)
                    else:
                        coeff = coeff_func(instance)
                    if lx_var.index_func is not None:
                        index_key = lx_var.index_func(instance)
                    elif lx_var._cartesian is not None and isinstance(instance, tuple):
                        index_key = tuple(
                            dim.key_func(inst)
                            for dim, inst in zip(lx_var._cartesian.dimensions, instance)
                        )
                    else:
                        index_key = instance
                    if abs(coeff) > 1e-10:
                        terms.append(solver_vars[index_key])
                        float_coeffs.append(coeff)

        # Convert coefficients to integers and track the scale factor
        int_coeffs, self._objective_coeff_scale = self._convert_coefficients_to_integers(float_coeffs)

        # Handle constant term (convert to integer)
        constant = model.objective_expr.constant
        int_constant = int(round(constant)) if constant != 0 else 0

        # Build objective expression
        if not terms:
            # Constant objective only
            obj_expr = int_constant
        else:
            obj_expr = sum(var * coeff for var, coeff in zip(terms, int_coeffs))
            if int_constant != 0:
                obj_expr += int_constant

        # Set sense (maximize or minimize)
        if model.objective_sense == LXObjectiveSense.MAXIMIZE:
            cpsat_model.Maximize(obj_expr)
        else:
            cpsat_model.Minimize(obj_expr)

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

        # Extract objective value
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            obj_value = float(solver.ObjectiveValue())
            # De-scale objective
            # The objective is scaled by:
            # 1. Variable scaling (if continuous variables): var_int = var_cont * var_scale
            # 2. Coefficient rational conversion: coefficients multiplied by coeff_scale
            #
            # So: CP-SAT minimizes sum((coeff * coeff_scale) * (var_cont * var_scale))
            #                      = coeff_scale * var_scale * sum(coeff * var_cont)
            #
            # To get original objective: divide by both scales
            if self._objective_has_scaled_vars:
                obj_value = obj_value / self._scaling_factor
            obj_value = obj_value / self._objective_coeff_scale
        else:
            obj_value = 0.0

        # Extract variable values
        variables: Dict[str, Union[float, Dict[Any, float]]] = {}
        mapped: Dict[str, Dict[Any, float]] = {}

        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
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
                        elif lx_var._cartesian is not None and isinstance(instance, tuple):
                            # For cartesian products, build key from dimension key functions
                            index_key = tuple(
                                dim.key_func(inst)
                                for dim, inst in zip(lx_var._cartesian.dimensions, instance)
                            )
                        else:
                            index_key = instance

                        var = solver_vars[index_key]
                        value = float(solver.Value(var))

                        # De-scale if variable was scaled
                        if lx_var.name in self._scaled_variables:
                            scale = self._variable_scales[lx_var.name]
                            value = value / scale

                        var_values[index_key] = value
                        mapped_values[index_key] = value

                    variables[lx_var.name] = var_values
                    mapped[lx_var.name] = mapped_values
                else:
                    # Single variable
                    value = float(solver.Value(solver_vars))

                    # De-scale if variable was scaled
                    if lx_var.name in self._scaled_variables:
                        scale = self._variable_scales[lx_var.name]
                        value = value / scale

                    variables[lx_var.name] = value

        # CP-SAT doesn't provide sensitivity analysis
        # TODO: Could compute reduced costs for feasibility/bound analysis
        shadow_prices: Dict[str, float] = {}
        reduced_costs: Dict[str, float] = {}

        # Extract solver statistics
        gap: Optional[float] = None
        iterations: Optional[int] = None
        nodes: Optional[int] = None

        # Get best objective bound for gap calculation
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            try:
                best_bound = solver.BestObjectiveBound()
                if obj_value != 0 and abs(obj_value - best_bound) > 1e-10:
                    gap = abs(obj_value - best_bound) / abs(obj_value)
            except Exception:
                pass

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
