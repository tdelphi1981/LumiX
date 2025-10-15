"""
Core linearization engine for automatic nonlinear term conversion.

This module orchestrates the entire linearization process:
1. Scan model for nonlinear terms
2. Check solver capabilities
3. Apply appropriate linearization techniques
4. Add auxiliary variables and constraints
5. Return linearized model
"""

from typing import Any, List, Optional

from ..core.constraints import LXConstraint
from ..core.expressions import LXLinearExpression, LXNonLinearExpression
from ..core.model import LXModel
from ..core.variables import LXVariable
from ..nonlinear.terms import (
    LXAbsoluteTerm,
    LXBilinearTerm,
    LXIndicatorTerm,
    LXMinMaxTerm,
    LXPiecewiseLinearTerm,
)
from ..solvers.capabilities import LXSolverCapability
from .config import LXLinearizerConfig
from .techniques.bilinear import LXBilinearLinearizer
from .techniques.piecewise import LXPiecewiseLinearizer


class LXLinearizer:
    """
    Automatic linearization engine.

    Transforms nonlinear expressions into linear equivalents by:
    - Detecting nonlinear terms in model
    - Checking solver capabilities
    - Applying appropriate linearization techniques
    - Adding auxiliary variables and constraints

    Example:
        linearizer = LXLinearizer(model, solver_capability, config)

        if linearizer.needs_linearization():
            linearized_model = linearizer.linearize_model()
    """

    def __init__(
        self,
        model: LXModel,
        solver_capability: LXSolverCapability,
        config: Optional[LXLinearizerConfig] = None,
    ):
        """
        Initialize linearization engine.

        Args:
            model: Model to linearize
            solver_capability: Solver capability information
            config: Linearization configuration (default: LXLinearizerConfig())
        """
        self.model = model
        self.capability = solver_capability
        self.config = config or LXLinearizerConfig()

        # Auxiliary elements created during linearization
        self.auxiliary_vars: List[LXVariable] = []
        self.auxiliary_constraints: List[LXConstraint] = []

        # Linearization technique instances
        self._bilinear_linearizer = LXBilinearLinearizer(self.config)
        self._piecewise_linearizer = LXPiecewiseLinearizer(self.config)

        # Counters for statistics
        self._num_bilinear_terms = 0
        self._num_piecewise_terms = 0
        self._num_abs_terms = 0
        self._num_minmax_terms = 0
        self._num_indicator_terms = 0

    def needs_linearization(self) -> bool:
        """
        Check if model contains nonlinear terms requiring linearization.

        Returns:
            True if linearization is needed
        """
        # Scan objective
        if self.model.objective_expr is not None:
            if isinstance(self.model.objective_expr, LXNonLinearExpression):
                if len(self.model.objective_expr.nonlinear_terms) > 0:
                    return True

        # Scan constraints
        for constraint in self.model.constraints:
            if constraint.lhs is not None:
                # Check if constraint expression contains nonlinear terms
                # For now, we check if it's a nonlinear expression type
                # TODO: Add more sophisticated checking
                pass

        return False

    def linearize_model(self) -> LXModel:
        """
        Linearize the entire model.

        Creates a new model with:
        - All original variables and constraints
        - Auxiliary variables for linearized terms
        - Auxiliary constraints for linearization

        Returns:
            Linearized model

        Example:
            linearized = linearizer.linearize_model()
            solution = solver.solve(linearized)
        """
        # Create new model (copy original)
        linearized = LXModel(f"{self.model.name}_linearized")

        # Add all original variables
        for var in self.model.variables:
            linearized.add_variable(var)

        # Process objective if it contains nonlinear terms
        if self.model.objective_expr is not None:
            if isinstance(self.model.objective_expr, LXNonLinearExpression):
                linear_objective = self._linearize_expression(self.model.objective_expr)
                # Set objective with same sense
                if self.model.objective_sense.value == "maximize":
                    linearized.maximize(linear_objective)
                else:
                    linearized.minimize(linear_objective)
            else:
                # Keep original objective
                if self.model.objective_sense.value == "maximize":
                    linearized.maximize(self.model.objective_expr)
                else:
                    linearized.minimize(self.model.objective_expr)

        # Add all original constraints
        # TODO: Process constraints that contain nonlinear terms
        for constraint in self.model.constraints:
            linearized.add_constraint(constraint)

        # Add auxiliary variables
        for aux_var in self.auxiliary_vars:
            linearized.add_variable(aux_var)

        # Collect auxiliary variables from technique linearizers
        for aux_var in self._bilinear_linearizer.auxiliary_vars:
            if aux_var not in self.auxiliary_vars:
                linearized.add_variable(aux_var)
                self.auxiliary_vars.append(aux_var)

        for aux_var in self._piecewise_linearizer.auxiliary_vars:
            if aux_var not in self.auxiliary_vars:
                linearized.add_variable(aux_var)
                self.auxiliary_vars.append(aux_var)

        # Add auxiliary constraints
        for aux_constraint in self.auxiliary_constraints:
            linearized.add_constraint(aux_constraint)

        # Collect auxiliary constraints from technique linearizers
        for aux_constraint in self._bilinear_linearizer.auxiliary_constraints:
            if aux_constraint not in self.auxiliary_constraints:
                linearized.add_constraint(aux_constraint)
                self.auxiliary_constraints.append(aux_constraint)

        for aux_constraint in self._piecewise_linearizer.auxiliary_constraints:
            if aux_constraint not in self.auxiliary_constraints:
                linearized.add_constraint(aux_constraint)
                self.auxiliary_constraints.append(aux_constraint)

        return linearized

    def _linearize_expression(
        self, expr: LXNonLinearExpression
    ) -> LXLinearExpression:
        """
        Linearize a nonlinear expression.

        Args:
            expr: Nonlinear expression to linearize

        Returns:
            Equivalent linear expression with auxiliary variables

        Raises:
            ValueError: If term type is not supported
        """
        # Start with linear terms
        linear_expr = expr.linear_terms

        # Process each nonlinear term
        for term in expr.nonlinear_terms:
            if isinstance(term, LXBilinearTerm):
                # Linearize bilinear product
                if self.capability.needs_linearization_for_bilinear():
                    aux_var = self._bilinear_linearizer.linearize_bilinear(term)
                    linear_expr = linear_expr + LXLinearExpression().add_term(
                        aux_var, term.coefficient
                    )
                    self._num_bilinear_terms += 1
                else:
                    # Solver has native support, keep as-is
                    # TODO: Convert to solver-specific quadratic form
                    pass

            elif isinstance(term, LXPiecewiseLinearTerm):
                # Linearize piecewise function
                if self.capability.needs_linearization_for_nonlinear():
                    aux_var = self._piecewise_linearizer.approximate_function(
                        term.func,
                        term.var,
                        term.num_segments,
                        term.x_min,
                        term.x_max,
                        term.method,
                        term.adaptive,
                    )
                    linear_expr = linear_expr + LXLinearExpression().add_term(
                        aux_var, 1.0
                    )
                    self._num_piecewise_terms += 1
                else:
                    # Solver has native support
                    pass

            elif isinstance(term, LXAbsoluteTerm):
                # Linearize absolute value
                if self.capability.needs_linearization_for_abs():
                    aux_var = self._linearize_absolute(term)
                    linear_expr = linear_expr + LXLinearExpression().add_term(
                        aux_var, term.coefficient
                    )
                    self._num_abs_terms += 1
                else:
                    # Solver has native support
                    pass

            elif isinstance(term, LXMinMaxTerm):
                # Linearize min/max
                if self.capability.needs_linearization_for_minmax():
                    aux_var = self._linearize_minmax(term)
                    linear_expr = linear_expr + LXLinearExpression().add_term(
                        aux_var, 1.0
                    )
                    self._num_minmax_terms += 1
                else:
                    # Solver has native support
                    pass

            elif isinstance(term, LXIndicatorTerm):
                # Linearize indicator constraint
                if not self.capability.can_use_indicator():
                    self._linearize_indicator(term)
                    self._num_indicator_terms += 1
                else:
                    # Solver has native support
                    pass

            else:
                raise ValueError(f"Unsupported nonlinear term type: {type(term)}")

        # Add constant
        linear_expr = linear_expr + expr.constant

        return linear_expr

    def _linearize_absolute(self, term: LXAbsoluteTerm) -> LXVariable:
        """
        Linearize absolute value: z = |x|

        Creates:
        - Auxiliary variable z
        - Constraints: z >= x, z >= -x

        Note: z is minimized in objective or bounded appropriately

        Args:
            term: Absolute value term

        Returns:
            Auxiliary variable z representing |x|
        """
        var = term.var
        var_name = var.name

        # Create auxiliary variable z
        z_name = f"aux_abs_{var_name}"

        # Determine bounds for z
        z_lower = 0  # |x| is always non-negative
        z_upper = None
        if var.lower_bound is not None and var.upper_bound is not None:
            z_upper = max(abs(var.lower_bound), abs(var.upper_bound))

        z = (
            LXVariable[str, float](z_name)
            .continuous()
            .bounds(lower=z_lower, upper=z_upper)
            .indexed_by(lambda x: x)
            .from_data([z_name])  # Use variable name as unique index
        )
        self.auxiliary_vars.append(z)

        # Constraint: z >= x
        self.auxiliary_constraints.append(
            LXConstraint(f"{z_name}_ge_pos")
            .expression(LXLinearExpression().add_term(z, 1.0).add_term(var, -1.0))
            .ge()
            .rhs(0)
        )

        # Constraint: z >= -x
        self.auxiliary_constraints.append(
            LXConstraint(f"{z_name}_ge_neg")
            .expression(LXLinearExpression().add_term(z, 1.0).add_term(var, 1.0))
            .ge()
            .rhs(0)
        )

        return z

    def _linearize_minmax(self, term: LXMinMaxTerm) -> LXVariable:
        """
        Linearize min/max functions.

        For min: z <= x_i for all i (z minimized in objective)
        For max: z >= x_i for all i (z maximized in objective)

        Args:
            term: Min/max term

        Returns:
            Auxiliary variable z representing min/max
        """
        vars_list = term.vars
        coeffs = term.coefficients
        operation = term.operation

        # Create auxiliary variable z
        z_name = f"aux_{operation}_{'_'.join(v.name for v in vars_list)}"
        z = (
            LXVariable[str, float](z_name)
            .continuous()
            .indexed_by(lambda x: x)
            .from_data([z_name])  # Use variable name as unique index
        )
        self.auxiliary_vars.append(z)

        # Add constraints based on operation
        if operation == "min":
            # z <= x_i for all i
            for i, (var, coeff) in enumerate(zip(vars_list, coeffs)):
                self.auxiliary_constraints.append(
                    LXConstraint(f"{z_name}_le_{i}")
                    .expression(
                        LXLinearExpression().add_term(z, 1.0).add_term(var, -coeff)
                    )
                    .le()
                    .rhs(0)
                )
        else:  # max
            # z >= x_i for all i
            for i, (var, coeff) in enumerate(zip(vars_list, coeffs)):
                self.auxiliary_constraints.append(
                    LXConstraint(f"{z_name}_ge_{i}")
                    .expression(
                        LXLinearExpression().add_term(z, 1.0).add_term(var, -coeff)
                    )
                    .ge()
                    .rhs(0)
                )

        return z

    def _linearize_indicator(self, term: LXIndicatorTerm) -> None:
        """
        Linearize indicator constraint: if b == condition then (expr sense rhs)

        Uses Big-M method to convert conditional constraint to linear form:
        - If condition=True and sense='<=':  expr - rhs <= M*(1-b)
        - If condition=True and sense='>=':  rhs - expr <= M*(1-b)
        - If condition=False and sense='<=': expr - rhs <= M*b
        - If condition=False and sense='>=': rhs - expr <= M*b
        - For '==': use both <= and >= constraints

        Args:
            term: Indicator term with binary variable, condition, expression, sense, and RHS

        Example:
            If is_open == 1 then flow >= 10:
            - Linearizes to: 10 - flow <= M*(1 - is_open)
            - When is_open=1: 10 - flow <= 0 → flow >= 10 (enforced)
            - When is_open=0: 10 - flow <= M (relaxed)
        """
        binary_var = term.binary_var
        condition = term.condition
        expr = term.linear_expr
        sense = term.sense
        rhs = term.rhs
        M = self.config.big_m_value

        # Create constraint name
        constraint_prefix = (
            f"indicator_{binary_var.name}_{int(condition)}_{sense.replace('=', 'eq')}"
        )

        if sense == "<=":
            # expr <= rhs when condition matches
            # Linearize: expr - rhs <= M * (1-b) if condition=True
            #            expr - rhs <= M * b     if condition=False
            if condition:
                # expr <= rhs + M*(1-b)
                # Rewrite as: expr - M*b <= rhs - M
                indicator_expr = expr.copy()
                indicator_expr = indicator_expr.add_term(binary_var, -M)

                self.auxiliary_constraints.append(
                    LXConstraint(f"{constraint_prefix}_le")
                    .expression(indicator_expr)
                    .le()
                    .rhs(rhs - M)
                )
            else:
                # expr <= rhs + M*b
                # Rewrite as: expr - M*b <= rhs
                indicator_expr = expr.copy()
                indicator_expr = indicator_expr.add_term(binary_var, -M)

                self.auxiliary_constraints.append(
                    LXConstraint(f"{constraint_prefix}_le")
                    .expression(indicator_expr)
                    .le()
                    .rhs(rhs)
                )

        elif sense == ">=":
            # expr >= rhs when condition matches
            # Linearize: rhs - expr <= M * (1-b) if condition=True
            #            rhs - expr <= M * b     if condition=False
            if condition:
                # expr >= rhs - M*(1-b)
                # Rewrite as: rhs - expr <= M*(1-b)
                # Rewrite as: -expr + M*b <= M - rhs
                indicator_expr = LXLinearExpression()
                # Negate all terms in expr
                for var, coeff in expr.terms.items():
                    indicator_expr = indicator_expr.add_term(var, -coeff)
                indicator_expr = indicator_expr.add_term(binary_var, M)

                self.auxiliary_constraints.append(
                    LXConstraint(f"{constraint_prefix}_ge")
                    .expression(indicator_expr)
                    .le()
                    .rhs(M - rhs)
                )
            else:
                # expr >= rhs - M*b
                # Rewrite as: rhs - expr <= M*b
                # Rewrite as: -expr - M*b <= -rhs
                indicator_expr = LXLinearExpression()
                # Negate all terms in expr
                for var, coeff in expr.terms.items():
                    indicator_expr = indicator_expr.add_term(var, -coeff)
                indicator_expr = indicator_expr.add_term(binary_var, -M)

                self.auxiliary_constraints.append(
                    LXConstraint(f"{constraint_prefix}_ge")
                    .expression(indicator_expr)
                    .le()
                    .rhs(-rhs)
                )

        elif sense == "==":
            # expr == rhs when condition matches
            # Need both <= and >= constraints
            # Create two indicator terms and recursively linearize
            le_term = LXIndicatorTerm(
                binary_var=binary_var,
                condition=condition,
                linear_expr=expr,
                sense="<=",
                rhs=rhs,
            )
            ge_term = LXIndicatorTerm(
                binary_var=binary_var,
                condition=condition,
                linear_expr=expr,
                sense=">=",
                rhs=rhs,
            )

            self._linearize_indicator(le_term)
            self._linearize_indicator(ge_term)

    def get_statistics(self) -> dict:
        """
        Get linearization statistics.

        Returns:
            Dictionary with counts of linearized terms
        """
        return {
            "bilinear_terms": self._num_bilinear_terms,
            "piecewise_terms": self._num_piecewise_terms,
            "absolute_terms": self._num_abs_terms,
            "minmax_terms": self._num_minmax_terms,
            "indicator_terms": self._num_indicator_terms,
            "auxiliary_variables": len(self.auxiliary_vars),
            "auxiliary_constraints": len(self.auxiliary_constraints),
        }


__all__ = ["LXLinearizer"]
