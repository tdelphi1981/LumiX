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

import numbers

from typing import TYPE_CHECKING, Generic, List, Optional, TypeVar

from typing_extensions import Self

from .constraints import LXConstraint
from .enums import LXObjectiveSense
from .expressions import LXLinearExpression, LXQuadraticExpression
from .variables import LXVariable

if TYPE_CHECKING:
    from .canonical import LXCanonicalModel
    from ..goal_programming.goal import LXGoalMode
    from ..goal_programming.relaxation import RelaxedConstraint
    from ..solution.solution import LXSolution

TModel = TypeVar("TModel")


class LXModel(Generic[TModel]):
    """
    Main model builder with full type safety and IDE support.

    Creates and manages optimization models with:

    - Variables (single or multi-indexed)
    - Constraints (linear, indexed, multi-model)
    - Objective function (linear or quadratic)

    Examples::

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
        self._objective_expr: Optional[LXLinearExpression | LXQuadraticExpression] = None
        self.objective_sense: LXObjectiveSense = LXObjectiveSense.MAXIMIZE
        self._objective_from_costs = False

        # Goal programming support
        self.goal_mode: Optional[str] = None  # "weighted" or "sequential"
        self._relaxed_constraints: List["RelaxedConstraint"] = []
        self._goal_programming_prepared: bool = False

    def __deepcopy__(self, memo):
        """Copy the model structure for what-if and scenario analysis.

        This method orchestrates copying of the entire model including:
        1. All variable families (an ORM query is materialized once)
        2. All constraint families (an ORM query is materialized once)
        3. Objective expression
        4. Goal programming metadata

        This is the central method that makes what-if analysis possible by creating
        independent copies of models that can be modified without affecting the original.

        Args:
            memo: Dictionary for tracking circular references during deepcopy

        Returns:
            Copy of this model whose families, constraints and expressions are new
            objects

        Note:
            Data instances (plain and ORM objects) and callables are shared with the
            original, so closures behave the same in the copy. ORM objects are not
            detached; pickling a model detaches them.

        .. versionchanged:: 0.3.0
           Data instances are shared instead of deep-copied/detached (catalog A23, B15).

        Example:
            >>> original_model = build_model_with_orm(session)
            >>> modified_model = deepcopy(original_model)
            >>> # modified_model can now be changed without affecting original_model
        """
        from copy import deepcopy

        # Create new instance without calling __init__
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result

        # Copy simple attributes
        result.name = self.name
        result.objective_sense = self.objective_sense
        result.goal_mode = self.goal_mode
        result._goal_programming_prepared = self._goal_programming_prepared
        result._goal_prepared_mode = getattr(self, "_goal_prepared_mode", None)

        # Deep copy all variable families
        # Each variable's __deepcopy__ shares its data instances and callables
        result.variables = [deepcopy(var, memo) for var in self.variables]

        # Deep copy all constraint families
        # Each constraint's __deepcopy__ shares its data instances and callables
        result.constraints = [deepcopy(constr, memo) for constr in self.constraints]

        # Deep copy objective expression (if present)
        result.objective_expr = (
            deepcopy(self.objective_expr, memo)
            if self.objective_expr is not None
            else None
        )
        result._objective_from_costs = self._objective_from_costs

        # Deep copy relaxed constraints (for goal programming)
        result._relaxed_constraints = [
            deepcopy(rc, memo) for rc in self._relaxed_constraints
        ]

        return result

    def __getstate__(self):
        """Support for pickle protocol - detach ORM sessions before pickling.

        Returns:
            Dictionary of instance state safe for pickling
        """
        # The default pickle behavior will work since all nested objects
        # (variables, constraints, expressions) have their own __getstate__
        # methods that handle ORM detachment
        return self.__dict__.copy()

    def __setstate__(self, state):
        """Support for pickle protocol - restore from pickled state.

        Args:
            state: Dictionary of instance state from pickling
        """
        self.__dict__.update(state)

    def add_variable(self, var: LXVariable) -> Self:
        """
        Add variable with full type checking.

        Args:
            var: Variable to add

        Returns:
            Self for chaining
        """
        if any(v.name == var.name for v in self.variables):
            raise ValueError(f"Model '{self.name}' already has a variable family named "
                             f"'{var.name}'")
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
        for var in variables:
            self.add_variable(var)
        return self

    def add_constraint(self, constraint: LXConstraint) -> Self:
        """
        Add constraint with full type checking.

        Args:
            constraint: Constraint to add

        Returns:
            Self for chaining

        Raises:
            ValueError: If the model already has a constraint with this name.

        .. versionchanged:: 0.3.0
           A second constraint with the same name raises ``ValueError``; it used to be
           accepted and then hid the first one from duals, activity and analysis.
        """
        names = self._constraint_name_set()
        if constraint.name in names and any(c.name == constraint.name for c in self.constraints):
            raise ValueError(f"Model '{self.name}' already has a constraint named "
                             f"'{constraint.name}'")
        self.constraints.append(constraint)
        names.add(constraint.name)
        return self

    def _constraint_name_set(self) -> set:
        """Names of ``self.constraints``, cached for this list object (rebuilt when the
        list is replaced or changed outside ``add_constraint``)."""
        cache = self.__dict__.get("_constraint_names")
        if (cache is None or cache[0] is not self.constraints
                or len(cache[1]) != len(self.constraints)):
            cache = (self.constraints, {c.name for c in self.constraints})
            self.__dict__["_constraint_names"] = cache
        return cache[1]

    def add_constraints(self, *constraints: LXConstraint) -> Self:
        """
        Add multiple constraints.

        Args:
            *constraints: Constraints to add

        Returns:
            Self for chaining
        """
        for constraint in constraints:
            self.add_constraint(constraint)
        return self

    def to_canonical(self) -> "LXCanonicalModel":
        """Solver-independent canonical form of this model (variable instances,
        rows with summed coefficients, objective). Solver adapters build from
        it; external engines can read it instead of LumiX internals. Goals are
        relaxed in the canonical form without changing this model.

        .. versionadded:: 0.3.0
        """
        from ..goal_programming.view import goal_form
        from .canonical import LXCanonicalBuilder

        return LXCanonicalBuilder(goal_form(self)).build()

    def minimize(self, expr: Optional[LXLinearExpression | LXQuadraticExpression] = None) -> Self:
        """
        Set objective to minimize.

        Args:
            expr: Objective expression (linear or quadratic). Without it, the
                objective is the sum of the variables' costs (``.cost()`` /
                ``.cost_multi()``), taken from the variables in the model when
                it is solved.

        Returns:
            Self for chaining

        .. versionchanged:: 0.3.0
           ``expr`` is optional.
        """
        self.objective_sense = LXObjectiveSense.MINIMIZE
        self.objective_expr = self.cost_objective() if expr is None else expr
        self._objective_from_costs = expr is None
        return self

    def maximize(self, expr: Optional[LXLinearExpression | LXQuadraticExpression] = None) -> Self:
        """
        Set objective to maximize.

        Args:
            expr: Objective expression (linear or quadratic). Without it, the
                objective is the sum of the variables' costs (``.cost()`` /
                ``.cost_multi()``), taken from the variables in the model when
                it is solved.

        Returns:
            Self for chaining

        .. versionchanged:: 0.3.0
           ``expr`` is optional.
        """
        self.objective_sense = LXObjectiveSense.MAXIMIZE
        self.objective_expr = self.cost_objective() if expr is None else expr
        self._objective_from_costs = expr is None
        return self

    @property
    def objective_expr(self) -> Optional[LXLinearExpression | LXQuadraticExpression]:
        """The objective expression. Assigning one replaces an objective taken from
        the variables' costs (``minimize()`` / ``maximize()`` without an argument)."""
        return self._objective_expr

    @objective_expr.setter
    def objective_expr(self, expr: Optional[LXLinearExpression | LXQuadraticExpression]) -> None:
        self._objective_expr = expr
        self._objective_from_costs = False

    def cost_objective(self) -> Optional[LXLinearExpression]:
        """Sum of the cost expressions of all variable families (``None`` if no
        variable defines a cost).

        .. versionadded:: 0.3.0
        """
        total: Optional[LXLinearExpression] = None
        for var in self.variables:
            part = var.cost_expression()
            if part is not None:
                total = part if total is None else total + part
        return total

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

        Priority 0 goals are not relaxed rows but objective terms: a ``.ge()``
        goal's expression is maximized and a ``.le()`` goal's expression is
        minimized, times its weight. The model's own objective
        (``minimize``/``maximize``) is kept as the lowest priority, together with
        the priority 0 goals: in weighted mode it is added in minimization form
        with weight ``priority_to_weight(0) = 1``; in sequential mode it is solved
        in the last stage.

        Solving a model with goals relaxes them on a copy automatically; call
        this method to relax them in the model itself (to inspect it, or for
        tools that read the model).

        Returns:
            Self for chaining

        Raises:
            ValueError: If a goal priority is not an integer >= 0, a priority 0
                goal is indexed, uses ``.eq()`` or has nonlinear terms, or the
                model's objective is nonlinear

        Example:
            >>> model.set_goal_mode("weighted")
            >>> model.prepare_goal_programming()
            >>> # Model now has deviation variables and goal objective

        .. versionchanged:: 0.3.0
           Priority 0 goals and the model's own objective are optimized after the
           goals instead of being dropped.
        """
        if self._goal_programming_prepared:
            return self
        from ..goal_programming.objective_builder import build_weighted_objective, final_objective
        from ..goal_programming.relaxation import relax_constraint
        from ..goal_programming.view import goal_mode_value

        goals = [c for c in self.constraints if c.is_goal()]
        if not goals:
            return self
        for c in goals:
            p = c.goal_metadata.priority
            integral = (isinstance(p, numbers.Integral) and not isinstance(p, bool)) or (
                isinstance(p, numbers.Real) and not isinstance(p, bool) and float(p).is_integer())
            if not integral or p < 0:
                raise ValueError(f"Goal '{c.name}' has priority {p!r}; priorities are integers >= 0")
            c.goal_metadata.priority = int(p)
        if self.goal_mode is None:
            self.goal_mode = "weighted"
        final = final_objective(self, [c for c in goals if c.goal_metadata.priority == 0])

        self._relaxed_constraints = []
        constraints = []
        for constraint in self.constraints:
            if not constraint.is_goal():
                constraints.append(constraint)
            elif constraint.goal_metadata.priority > 0:
                relaxed = relax_constraint(constraint, constraint.goal_metadata)
                self._relaxed_constraints.append(relaxed)
                self.add_variable(relaxed.pos_deviation)
                self.add_variable(relaxed.neg_deviation)
                constraints.append(relaxed.constraint)
            # priority 0 goals are objective terms (final_objective), not rows
        self.constraints = constraints

        if goal_mode_value(self.goal_mode) == "weighted":
            objective = build_weighted_objective(self._relaxed_constraints)
            if final is not None:
                expr, sense = final
                objective = objective + (expr if sense == LXObjectiveSense.MINIMIZE else -expr)
            self.minimize(objective)
        elif final is not None:
            expr, sense = final
            self.minimize(expr) if sense == LXObjectiveSense.MINIMIZE else self.maximize(expr)
        else:
            self.objective_expr = None      # the stages minimize the deviations
            self.objective_sense = LXObjectiveSense.MINIMIZE
        self._goal_prepared_mode = goal_mode_value(self.goal_mode)
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

        ``LXOptimizer.solve`` calls this method on the model it relaxed.

        Args:
            solution: Solution object to populate

        Returns:
            The solution object with goal_deviations populated
        """
        if not self._goal_programming_prepared or not self._relaxed_constraints:
            return solution
        if not solution.variables:
            return solution     # no solution (infeasible, unbounded, stopped): no deviations

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
            meta = relaxed.goal_metadata
            solution._undesired_deviations[constraint_name] = frozenset(
                side for side, bad in (("pos", meta.is_pos_undesired()),
                                       ("neg", meta.is_neg_undesired())) if bad)

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
