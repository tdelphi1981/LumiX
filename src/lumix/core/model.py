"""Model builder class for LumiX optimization models."""

from typing import Generic, List, Optional, TypeVar

from typing_extensions import Self

from .constraints import LXConstraint
from .enums import LXObjectiveSense
from .expressions import LXLinearExpression, LXQuadraticExpression
from .variables import LXVariable

TModel = TypeVar("TModel")


class LXModel(Generic[TModel]):
    """
    Main model builder with full type safety and IDE support.

    Creates and manages optimization models with:
    - Variables (single or multi-indexed)
    - Constraints (linear, indexed, multi-model)
    - Objective function (linear or quadratic)

    Examples:
        # Simple model
        model = LXModel("production_plan")
        model.add_variable(production)
        model.add_constraint(capacity_constraint)
        model.maximize(
            LXLinearExpression().add_term(production, lambda p: p.selling_price)
        )

        # Type-safe model
        model = LXModel[Product]("production_plan")
            .add_variable(production)
            .add_constraint(capacity_constraint)
            .maximize(
                LXLinearExpression()
                .add_term(production, lambda p: p.selling_price - p.cost)
            )
    """

    def __init__(self, name: str):
        """
        Initialize model.

        Args:
            name: Model name
        """
        self.name = name
        # Note: List of variable families. Each LXVariable represents a family of solver variables
        # (e.g., production[product1], production[product2], ...). A model typically contains
        # multiple families (e.g., production, inventory, transportation).
        self.variables: List[LXVariable] = []
        self.constraints: List[LXConstraint] = []
        self.objective_expr: Optional[LXLinearExpression | LXQuadraticExpression] = None
        self.objective_sense: LXObjectiveSense = LXObjectiveSense.MAXIMIZE

    def add_variable(self, var: LXVariable) -> Self:
        """
        Add variable with full type checking.

        Args:
            var: Variable to add

        Returns:
            Self for chaining
        """
        self.variables.append(var)
        return self

    def add_variables(self, *variables: LXVariable) -> Self:
        """
        Add multiple variable families.

        Args:
            *variables: Variables to add

        Returns:
            Self for chaining
        """
        self.variables.extend(variables)
        return self

    def add_constraint(self, constraint: LXConstraint) -> Self:
        """
        Add constraint with full type checking.

        Args:
            constraint: Constraint to add

        Returns:
            Self for chaining
        """
        self.constraints.append(constraint)
        return self

    def add_constraints(self, *constraints: LXConstraint) -> Self:
        """
        Add multiple constraints.

        Args:
            *constraints: Constraints to add

        Returns:
            Self for chaining
        """
        self.constraints.extend(constraints)
        return self

    def minimize(self, expr: LXLinearExpression | LXQuadraticExpression) -> Self:
        """
        Set objective to minimize.

        Args:
            expr: Objective expression (linear or quadratic)

        Returns:
            Self for chaining
        """
        self.objective_sense = LXObjectiveSense.MINIMIZE
        self.objective_expr = expr
        return self

    def maximize(self, expr: LXLinearExpression | LXQuadraticExpression) -> Self:
        """
        Set objective to maximize.

        Args:
            expr: Objective expression (linear or quadratic)

        Returns:
            Self for chaining
        """
        self.objective_sense = LXObjectiveSense.MAXIMIZE
        self.objective_expr = expr
        return self

    def get_variable(self, name: str) -> Optional[LXVariable]:
        """
        Get variable family by name.

        Args:
            name: Variable name

        Returns:
            LXVariable if found, None otherwise
        """
        for var in self.variables:
            if var.name == name:
                return var
        return None

    def get_constraint(self, name: str) -> Optional[LXConstraint]:
        """
        Get constraint by name.

        Args:
            name: Constraint name

        Returns:
            LXConstraint if found, None otherwise
        """
        for const in self.constraints:
            if const.name == name:
                return const
        return None

    def summary(self) -> str:
        """
        Get model summary.

        Returns:
            String summary of model
        """
        return (
            f"LXModel: {self.name}\n"
            f"  Variables: {len(self.variables)}\n"
            f"  Constraints: {len(self.constraints)}\n"
            f"  Objective: {self.objective_sense.value}\n"
        )


__all__ = ["LXModel"]
