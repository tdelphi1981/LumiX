"""
Bilinear product linearization techniques.

Implements three main methods:
1. Binary × Binary: AND logic
2. Binary × Continuous: Big-M method
3. Continuous × Continuous: McCormick envelopes

Reference: sample_impl/opt_wrapper_design.py:1285-1366
"""

from typing import Any, List, Optional

from ...core.constraints import LXConstraint
from ...core.enums import LXVarType
from ...core.expressions import LXLinearExpression
from ...core.variables import LXVariable
from ...nonlinear.terms import LXBilinearTerm
from ..config import LXLinearizerConfig


class LXBilinearLinearizer:
    """
    Linearization techniques for bilinear products (x * y).

    Automatically selects the appropriate technique based on variable types.
    """

    def __init__(self, config: LXLinearizerConfig):
        """
        Initialize bilinear linearizer.

        Args:
            config: Linearization configuration
        """
        self.config = config
        self.auxiliary_vars: List[LXVariable] = []
        self.auxiliary_constraints: List[LXConstraint] = []
        self._aux_counter = 0

    def linearize_bilinear(self, term: LXBilinearTerm) -> LXVariable:
        """
        Linearize bilinear product based on variable types.

        Args:
            term: Bilinear term to linearize

        Returns:
            Auxiliary variable representing the product

        Raises:
            ValueError: If variable types are not supported
        """
        x, y = term.var1, term.var2

        # Binary × Binary → AND logic
        if x.var_type == LXVarType.BINARY and y.var_type == LXVarType.BINARY:
            return self._binary_and(x, y, term.coefficient)

        # Binary × Continuous → Big-M
        elif x.var_type == LXVarType.BINARY and y.var_type in [
            LXVarType.CONTINUOUS,
            LXVarType.INTEGER,
        ]:
            return self._big_m_product(x, y, term.coefficient)
        elif y.var_type == LXVarType.BINARY and x.var_type in [
            LXVarType.CONTINUOUS,
            LXVarType.INTEGER,
        ]:
            return self._big_m_product(y, x, term.coefficient)

        # Continuous × Continuous → McCormick envelopes
        elif x.var_type in [LXVarType.CONTINUOUS, LXVarType.INTEGER] and y.var_type in [
            LXVarType.CONTINUOUS,
            LXVarType.INTEGER,
        ]:
            return self._mccormick_envelope(x, y, term.coefficient)

        else:
            raise ValueError(
                f"Unsupported variable type combination for bilinear product: "
                f"{x.name} ({x.var_type}) × {y.name} ({y.var_type})"
            )

    def _binary_and(
        self, x: LXVariable, y: LXVariable, coeff: float
    ) -> LXVariable:
        """
        Linearize Binary × Binary using AND logic.

        Creates auxiliary binary variable z with constraints:
            z <= x
            z <= y
            z >= x + y - 1

        This ensures z = 1 if and only if both x = 1 and y = 1.

        Args:
            x: First binary variable
            y: Second binary variable
            coeff: Coefficient (usually 1.0)

        Returns:
            Auxiliary binary variable z representing x AND y
        """
        z_name = self._generate_aux_name("and", x.name, y.name)
        z = (
            LXVariable[str, int](z_name)
            .binary()
            .indexed_by(lambda x: x)
            .from_data([z_name])  # Use variable name as unique index
        )
        self.auxiliary_vars.append(z)

        # Constraint: z <= x
        self.auxiliary_constraints.append(
            LXConstraint(f"{z_name}_le_x")
            .expression(LXLinearExpression().add_term(z, 1.0).add_term(x, -1.0))
            .le()
            .rhs(0)
        )

        # Constraint: z <= y
        self.auxiliary_constraints.append(
            LXConstraint(f"{z_name}_le_y")
            .expression(LXLinearExpression().add_term(z, 1.0).add_term(y, -1.0))
            .le()
            .rhs(0)
        )

        # Constraint: z >= x + y - 1
        self.auxiliary_constraints.append(
            LXConstraint(f"{z_name}_ge_sum")
            .expression(
                LXLinearExpression()
                .add_term(z, 1.0)
                .add_term(x, -1.0)
                .add_term(y, -1.0)
            )
            .ge()
            .rhs(-1)
        )

        return z

    def _big_m_product(
        self, binary_var: LXVariable, cont_var: LXVariable, coeff: float
    ) -> LXVariable:
        """
        Linearize Binary × Continuous using Big-M method.

        Creates auxiliary continuous variable z = b * x with constraints:
            z <= M * b
            z >= m * b
            z <= x - m * (1 - b)
            z >= x - M * (1 - b)

        where M = upper bound of x, m = lower bound of x.

        Args:
            binary_var: Binary variable (b)
            cont_var: Continuous/integer variable (x)
            coeff: Coefficient

        Returns:
            Auxiliary variable z representing b * x
        """
        # Determine bounds
        M = cont_var.upper_bound
        m = cont_var.lower_bound

        if M is None:
            M = self.config.big_m_value
        if m is None:
            m = -self.config.big_m_value

        # Create auxiliary variable (with scalar data source)
        z_name = self._generate_aux_name("prod", binary_var.name, cont_var.name)
        z = (
            LXVariable[str, float](z_name)
            .continuous()
            .bounds(lower=m, upper=M)
            .indexed_by(lambda x: x)
            .from_data([z_name])  # Use variable name as unique index
        )
        self.auxiliary_vars.append(z)

        # Constraint: z <= M * b
        self.auxiliary_constraints.append(
            LXConstraint(f"{z_name}_ub")
            .expression(
                LXLinearExpression().add_term(z, 1.0).add_term(binary_var, -M)
            )
            .le()
            .rhs(0)
        )

        # Constraint: z >= m * b
        self.auxiliary_constraints.append(
            LXConstraint(f"{z_name}_lb")
            .expression(
                LXLinearExpression().add_term(z, 1.0).add_term(binary_var, -m)
            )
            .ge()
            .rhs(0)
        )

        # Constraint: z <= x - m * (1 - b) → z - x + m*b <= m
        self.auxiliary_constraints.append(
            LXConstraint(f"{z_name}_ub_tight")
            .expression(
                LXLinearExpression()
                .add_term(z, 1.0)
                .add_term(cont_var, -1.0)
                .add_term(binary_var, m)
            )
            .le()
            .rhs(m)
        )

        # Constraint: z >= x - M * (1 - b) → z - x + M*b >= M
        self.auxiliary_constraints.append(
            LXConstraint(f"{z_name}_lb_tight")
            .expression(
                LXLinearExpression()
                .add_term(z, 1.0)
                .add_term(cont_var, -1.0)
                .add_term(binary_var, M)
            )
            .ge()
            .rhs(M)
        )

        return z

    def _mccormick_envelope(
        self, x: LXVariable, y: LXVariable, coeff: float
    ) -> LXVariable:
        """
        Linearize Continuous × Continuous using McCormick envelopes.

        Reference: sample_impl/opt_wrapper_design.py:1285-1366

        Creates auxiliary variable z = x * y with convex hull constraints:
            z >= xL*y + yL*x - xL*yL  (convex envelope 1)
            z >= xU*y + yU*x - xU*yU  (convex envelope 2)
            z <= xL*y + yU*x - xL*yU  (concave envelope 1)
            z <= xU*y + yL*x - xU*yL  (concave envelope 2)

        where x ∈ [xL, xU], y ∈ [yL, yU].

        These four constraints form a tight linear relaxation of the bilinear
        term z = x * y.

        Args:
            x: First continuous/integer variable
            y: Second continuous/integer variable
            coeff: Coefficient

        Returns:
            Auxiliary variable z representing x * y

        Raises:
            ValueError: If variables don't have bounds (required for McCormick)
        """
        # Extract bounds
        xL = x.lower_bound
        xU = x.upper_bound
        yL = y.lower_bound
        yU = y.upper_bound

        # Validate bounds are available
        if xL is None or xU is None or yL is None or yU is None:
            raise ValueError(
                f"McCormick envelopes require bounds on both variables. "
                f"Detected: {x.name} ∈ [{xL}, {xU}], {y.name} ∈ [{yL}, {yU}]. "
                f"Please specify bounds using .bounds(lower=..., upper=...) "
                f"or enable auto_detect_bounds in configuration."
            )

        # Create auxiliary variable z = x * y
        z_name = self._generate_aux_name("mccormick", x.name, y.name)

        # Compute bounds for z
        corner_products = [xL * yL, xL * yU, xU * yL, xU * yU]
        z_lower = min(corner_products)
        z_upper = max(corner_products)

        z = (
            LXVariable[str, float](z_name)
            .continuous()
            .bounds(lower=z_lower, upper=z_upper)
            .indexed_by(lambda x: x)
            .from_data([z_name])  # Use variable name as unique index
        )
        self.auxiliary_vars.append(z)

        # McCormick envelope constraint 1: z >= xL*y + yL*x - xL*yL
        self.auxiliary_constraints.append(
            LXConstraint(f"mccormick_{z_name}_1")
            .expression(
                LXLinearExpression()
                .add_term(z, 1.0)
                .add_term(y, -xL)
                .add_term(x, -yL)
            )
            .ge()
            .rhs(-xL * yL)
        )

        # McCormick envelope constraint 2: z >= xU*y + yU*x - xU*yU
        self.auxiliary_constraints.append(
            LXConstraint(f"mccormick_{z_name}_2")
            .expression(
                LXLinearExpression()
                .add_term(z, 1.0)
                .add_term(y, -xU)
                .add_term(x, -yU)
            )
            .ge()
            .rhs(-xU * yU)
        )

        # McCormick envelope constraint 3: z <= xL*y + yU*x - xL*yU
        self.auxiliary_constraints.append(
            LXConstraint(f"mccormick_{z_name}_3")
            .expression(
                LXLinearExpression()
                .add_term(z, 1.0)
                .add_term(y, -xL)
                .add_term(x, -yU)
            )
            .le()
            .rhs(-xL * yU)
        )

        # McCormick envelope constraint 4: z <= xU*y + yL*x - xU*yL
        self.auxiliary_constraints.append(
            LXConstraint(f"mccormick_{z_name}_4")
            .expression(
                LXLinearExpression()
                .add_term(z, 1.0)
                .add_term(y, -xU)
                .add_term(x, -yL)
            )
            .le()
            .rhs(-xU * yL)
        )

        return z

    def _generate_aux_name(self, prefix: str, name1: str, name2: str) -> str:
        """
        Generate unique name for auxiliary variable.

        Args:
            prefix: Prefix (e.g., "and", "prod", "mccormick")
            name1: First variable name
            name2: Second variable name

        Returns:
            Unique auxiliary variable name
        """
        self._aux_counter += 1
        return f"aux_{prefix}_{name1}_{name2}_{self._aux_counter}"


__all__ = ["LXBilinearLinearizer"]
