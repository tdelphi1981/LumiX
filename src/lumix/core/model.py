"""Model builder class for LumiX optimization models.

This module provides the LXModel class, which is the central component for building
optimization models in LumiX. It implements the Builder pattern with fluent API for
creating type-safe, data-driven optimization models.

The model serves as a container for:
    - Variable families (decision variables indexed by data)
    - Constraint families (constraints indexed by data)
    - Objective function (linear or quadratic expression)
    - Goal programming metadata (for multi-objective optimization)

Key Features:
    - **Fluent API**: Method chaining for concise model building
    - **Type Safety**: Generic type parameter for compile-time type checking
    - **Goal Programming**: Native support for multi-objective optimization
    - **Auto-expansion**: Variable and constraint families expand automatically

Architecture:
    LXModel uses the Builder pattern where each method returns `self` to enable
    method chaining. The model doesn't create solver variables directly - instead,
    it stores variable and constraint *families* that are expanded during solving.

Examples:
    Simple production planning model::

        from lumix import LXModel, LXVariable, LXConstraint, LXLinearExpression

        # Create model
        model = LXModel("production_plan")

        # Add variables
        production = LXVariable[Product, float]("production")\\
            .continuous()\\
            .bounds(lower=0)\\
            .from_data(products)

        model.add_variable(production)

        # Add constraints
        capacity = LXConstraint("capacity")\\
            .expression(
                LXLinearExpression().add_term(production, lambda p: p.usage)
            )\\
            .le()\\
            .rhs(max_capacity)

        model.add_constraint(capacity)

        # Set objective
        model.maximize(
            LXLinearExpression().add_term(production, lambda p: p.profit)
        )

    Fluent API with method chaining::

        model = (
            LXModel[Product]("production")
            .add_variable(production)
            .add_constraint(capacity)
            .maximize(profit_expr)
        )

    Goal programming for multi-objective optimization::

        model = LXModel("multi_objective")\\
            .set_goal_mode("weighted")

        # Mark constraints as goals with priorities
        model.add_constraint(
            profit_constraint.as_goal(priority=1, weight=1.0)
        )
        model.add_constraint(
            quality_constraint.as_goal(priority=2, weight=0.8)
        )

        # Solve with goal programming solver
        solution = optimizer.solve(model)

Note:
    The model is solver-agnostic. The same model can be solved with different
    solvers (OR-Tools, Gurobi, CPLEX, GLPK) by simply changing the optimizer
    configuration.

See Also:
    - :class:`~lumix.core.variables.LXVariable`: Variable family builder
    - :class:`~lumix.core.constraints.LXConstraint`: Constraint family builder
    - :class:`~lumix.core.expressions.LXLinearExpression`: Linear expression builder
    - :class:`~lumix.solvers.base.LXOptimizer`: Solver interface
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, List, Optional, TypeVar

from typing_extensions import Self

from .constraints import LXConstraint
from .enums import LXObjectiveSense
from .expressions import LXLinearExpression, LXQuadraticExpression
from .variables import LXVariable

if TYPE_CHECKING:
    from ..goal_programming.goal import LXGoalMode
    from ..goal_programming.relaxation import RelaxedConstraint

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

        # Goal programming support
        self.goal_mode: Optional[str] = None  # "weighted" or "sequential"
        self._relaxed_constraints: List["RelaxedConstraint"] = []
        self._goal_programming_prepared: bool = False

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

    def set_goal_mode(self, mode: str) -> Self:
        """
        Set goal programming mode.

        Args:
            mode: Goal programming mode ("weighted" or "sequential")

        Returns:
            Self for chaining

        Raises:
            ValueError: If mode is not "weighted" or "sequential"

        Example:
            >>> model.set_goal_mode("weighted")
            >>> # Solve with weighted objectives (single solve)

            >>> model.set_goal_mode("sequential")
            >>> # Solve lexicographically (multiple solves)
        """
        if mode not in ("weighted", "sequential"):
            raise ValueError(
                f"Invalid goal mode: {mode}. Must be 'weighted' or 'sequential'"
            )
        self.goal_mode = mode
        return self

    def prepare_goal_programming(self) -> Self:
        """
        Prepare model for goal programming by relaxing goal constraints.

        This method:
        1. Identifies constraints marked as goals (via .as_goal())
        2. Relaxes them by adding deviation variables
        3. Builds the appropriate objective function based on mode
        4. Adds deviation variables to the model
        5. Replaces goal constraints with relaxed versions

        This is automatically called by the solver, but can be called
        manually for inspection or debugging.

        Returns:
            Self for chaining

        Example:
            >>> model.set_goal_mode("weighted")
            >>> model.prepare_goal_programming()
            >>> # Model now has deviation variables and goal objective
        """
        if self._goal_programming_prepared:
            # Already prepared, skip
            return self

        # Import here to avoid circular dependencies
        from ..goal_programming.goal import LXGoalMode
        from ..goal_programming.objective_builder import build_weighted_objective
        from ..goal_programming.relaxation import relax_constraint

        # Collect goal constraints
        goal_constraints = [c for c in self.constraints if c.is_goal()]

        if not goal_constraints:
            # No goals, nothing to do
            return self

        # Determine mode (default to weighted if not set)
        if self.goal_mode is None:
            self.goal_mode = "weighted"

        # Relax each goal constraint
        self._relaxed_constraints = []
        regular_constraints = []

        for constraint in self.constraints:
            if constraint.is_goal():
                # Relax this constraint
                relaxed = relax_constraint(constraint, constraint.goal_metadata)
                self._relaxed_constraints.append(relaxed)

                # Add deviation variables to model
                self.add_variable(relaxed.pos_deviation)
                self.add_variable(relaxed.neg_deviation)

                # Add relaxed constraint (equality with deviations)
                regular_constraints.append(relaxed.constraint)
            else:
                # Keep regular constraint as-is
                regular_constraints.append(constraint)

        # Replace constraints with relaxed versions
        self.constraints = regular_constraints

        # Build objective based on mode
        if self.goal_mode == "weighted":
            # Build weighted objective
            goal_objective = build_weighted_objective(self._relaxed_constraints)

            # Set as objective (or combine with existing if present)
            if self.objective_expr is None:
                # No existing objective, use goal objective
                self.minimize(goal_objective)
            else:
                # Combine with existing objective
                # For now, we'll just replace it (user can handle this manually)
                # Future enhancement: provide combine_objectives helper
                self.minimize(goal_objective)

        # For sequential mode, objective will be set during solving
        # (handled by LXGoalProgrammingSolver)

        self._goal_programming_prepared = True
        return self

    def has_goals(self) -> bool:
        """
        Check if model has any goal constraints.

        Returns:
            True if at least one constraint is marked as a goal
        """
        return any(c.is_goal() for c in self.constraints)

    def populate_goal_deviations(self, solution: "LXSolution") -> "LXSolution":
        """
        Populate goal deviation values in the solution.

        Extracts deviation variable values from the solution and organizes
        them by goal name for easy access via solution.get_goal_deviations().

        This method is automatically called after solving if the model has goals.

        Args:
            solution: Solution object to populate

        Returns:
            The solution object with goal_deviations populated
        """
        if not self._goal_programming_prepared or not self._relaxed_constraints:
            return solution

        # Import here to avoid circular dependency
        from ..solution.solution import LXSolution

        # Extract deviation values for each relaxed constraint
        for relaxed in self._relaxed_constraints:
            constraint_name = relaxed.constraint.name

            # Get positive and negative deviation values
            pos_dev_values = solution.get_variable(relaxed.pos_deviation)
            neg_dev_values = solution.get_variable(relaxed.neg_deviation)

            # Store in solution's goal_deviations
            solution.goal_deviations[constraint_name] = {
                "pos": pos_dev_values,
                "neg": neg_dev_values,
            }

        return solution

    def summary(self) -> str:
        """
        Get model summary.

        Returns:
            String summary of model
        """
        summary_str = (
            f"LXModel: {self.name}\n"
            f"  Variable Families: {len(self.variables)}\n"
            f"  Constraint Families: {len(self.constraints)}\n"
            f"  Objective: {self.objective_sense.value}\n"
        )

        # Add goal programming info if applicable
        if self.has_goals():
            goal_count = sum(1 for c in self.constraints if c.is_goal())
            summary_str += f"  Goal Constraints: {goal_count}\n"
            if self.goal_mode:
                summary_str += f"  Goal Mode: {self.goal_mode}\n"

        return summary_str


__all__ = ["LXModel"]
