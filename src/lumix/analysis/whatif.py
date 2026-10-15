"""Interactive What-If analysis for LumiX models."""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Dict, Generic, List, Optional, TypeVar, Union

from typing_extensions import Self

from ..core.enums import LXConstraintSense, LXObjectiveSense
from ..core.model import LXModel
from ..solution.solution import LXSolution
from ..solvers.base import LXOptimizer
from ._factory import ModelSource
from ._rhs import set_rhs, shift_rhs

if TYPE_CHECKING:
    from .store import LXResultStore

TModel = TypeVar("TModel")


@dataclass
class LXWhatIfChange:
    """
    Represents a single what-if change to explore.

    Examples:
        Relax capacity constraint by 100 units::

            LXWhatIfChange(
                change_type="constraint_rhs",
                target_name="capacity",
                description="Relax capacity by 100",
                new_value=1100.0
            )
    """

    change_type: str  # "constraint_rhs", "variable_bound", "objective_coeff"
    target_name: str
    description: str
    original_value: Optional[float] = None
    new_value: Optional[float] = None
    delta: Optional[float] = None  # For additive changes


@dataclass
class LXWhatIfResult(Generic[TModel]):
    """
    Results of a what-if analysis.

    Attributes:
        description: Description of the change
        original_objective: Original objective value
        new_objective: New objective value
        delta_objective: Change in objective value
        delta_percentage: Percentage change in objective
        original_solution: Original solution
        new_solution: New solution with change applied
        changes_applied: List of changes applied
    """

    description: str
    original_objective: float
    new_objective: float
    delta_objective: float
    delta_percentage: float
    original_solution: LXSolution[TModel]
    new_solution: LXSolution[TModel]
    changes_applied: List[LXWhatIfChange] = field(default_factory=list)


class LXWhatIfAnalyzer(Generic[TModel]):
    """
    Interactive what-if analysis for optimization models.

    Allows quick exploration of parameter changes and their impact on
    the optimal solution. Useful for understanding trade-offs and
    identifying opportunities for improvement.

    Examples:
        Create analyzer and explore changes::

            analyzer = LXWhatIfAnalyzer(model, optimizer)

            # Get baseline solution
            baseline = analyzer.get_baseline_solution()

            # What if we increase capacity?
            result = analyzer.increase_constraint_rhs("capacity", by=200.0)
            print(f"Increasing capacity by 200 would improve profit by ${result.delta_objective:,.2f}")

            # What if we relax minimum production?
            result = analyzer.relax_constraint("min_production", by_percent=0.5)
            print(f"Relaxing min production by 50% would change objective by {result.delta_percentage:.1f}%")

            # Compare multiple changes
            results = analyzer.compare_changes([
                ("capacity", "increase", 100),
                ("capacity", "increase", 200),
                ("capacity", "increase", 300),
            ])

            # Find bottlenecks
            bottlenecks = analyzer.find_bottlenecks(top_n=5)
            for name, improvement in bottlenecks:
                print(f"{name}: relaxing by 1 unit would improve objective by ${improvement:.2f}")
    """

    def __init__(
        self,
        model: Optional[LXModel[TModel]] = None,
        optimizer: Optional[LXOptimizer[TModel]] = None,
        baseline_solution: Optional[LXSolution[TModel]] = None,
        *,
        model_factory: Optional[Callable[[], LXModel[TModel]]] = None,
        result_store: Optional["LXResultStore"] = None,
    ):
        """
        Initialize what-if analyzer.

        Args:
            model: Optimization model (copied for every what-if run)
            optimizer: Optimizer to use for solving
            baseline_solution: Pre-computed baseline solution (optional)
            model_factory: Instead of ``model``: a function that builds the model. It is
                called once for the baseline and once per what-if run, so nothing is
                copied (recommended for ORM-backed models: open a session inside it).
                It must return a new model on every call; the analyzer keeps the
                models it built until it is discarded.
            result_store: Optional :class:`~lumix.analysis.store.LXResultStore` that
                records every solve.

        .. versionchanged:: 0.3.0
           ``model_factory`` and ``result_store`` added; ``model`` and ``optimizer``
           may be passed by keyword.
        """
        self._source = ModelSource(model, model_factory, optimizer, "LXWhatIfAnalyzer")
        self.model = self._source.base
        self.optimizer = optimizer
        self.result_store = result_store
        self._baseline_solution = baseline_solution
        self._result_cache: Dict[str, LXWhatIfResult[TModel]] = {}

    def get_baseline_solution(self, recompute: bool = False) -> LXSolution[TModel]:
        """
        Get baseline solution (caches result).

        Args:
            recompute: Force recomputation of baseline

        Returns:
            Baseline solution
        """
        if self._baseline_solution is None or recompute:
            self._baseline_solution = self.optimizer.solve(self.model)
        return self._baseline_solution

    def increase_constraint_rhs(
        self,
        constraint_name: str,
        by: Optional[float] = None,
        by_percent: Optional[float] = None,
        to: Optional[float] = None,
    ) -> LXWhatIfResult[TModel]:
        """
        Analyze impact of increasing constraint RHS.

        Args:
            constraint_name: Name of constraint
            by: Increase by this amount
            by_percent: Increase by this percentage (0.1 = 10%)
            to: Set to this value

        Returns:
            What-if analysis result

        Examples:
            # Increase capacity by 100 units
            result = analyzer.increase_constraint_rhs("capacity", by=100)

            # Increase capacity by 20%
            result = analyzer.increase_constraint_rhs("capacity", by_percent=0.2)

            # Set capacity to 1500
            result = analyzer.increase_constraint_rhs("capacity", to=1500)
        """
        return self._modify_constraint_rhs(
            constraint_name,
            by=by,
            by_percent=by_percent,
            to=to,
            description_prefix="Increase",
        )

    def decrease_constraint_rhs(
        self,
        constraint_name: str,
        by: Optional[float] = None,
        by_percent: Optional[float] = None,
        to: Optional[float] = None,
    ) -> LXWhatIfResult[TModel]:
        """
        Analyze impact of decreasing constraint RHS.

        Args:
            constraint_name: Name of constraint
            by: Decrease by this amount
            by_percent: Decrease by this percentage (0.1 = 10%)
            to: Set to this value

        Returns:
            What-if analysis result
        """
        if by is not None:
            by = -by  # Convert to negative
        return self._modify_constraint_rhs(
            constraint_name,
            by=by,
            by_percent=-by_percent if by_percent else None,
            to=to,
            description_prefix="Decrease",
        )

    def relax_constraint(
        self,
        constraint_name: str,
        by: Optional[float] = None,
        by_percent: Optional[float] = None,
    ) -> LXWhatIfResult[TModel]:
        """
        Relax a constraint (increase RHS for LE, decrease for GE).

        This is a convenience method that automatically determines the
        direction based on constraint type.

        Args:
            constraint_name: Name of constraint
            by: Relax by this amount
            by_percent: Relax by this percentage

        Returns:
            What-if analysis result

        Examples:
            # Relax capacity constraint by 100 units
            result = analyzer.relax_constraint("capacity", by=100)

            # Relax minimum production by 20%
            result = analyzer.relax_constraint("min_production", by_percent=0.2)
        """
        # Get constraint to determine sense
        constraint = self.model.get_constraint(constraint_name)
        if constraint is None:
            raise ValueError(f"Constraint '{constraint_name}' not found")

        # For LE constraints, relaxing means increasing RHS
        # For GE constraints, relaxing means decreasing RHS
        # For EQ constraints, we increase (arbitrary choice)
        if constraint.sense == LXConstraintSense.GE:
            # For >= constraints, relaxing means decreasing RHS
            if by is not None:
                by = -by
            if by_percent is not None:
                by_percent = -by_percent

        return self._modify_constraint_rhs(
            constraint_name,
            by=by,
            by_percent=by_percent,
            description_prefix="Relax",
        )

    def tighten_constraint(
        self,
        constraint_name: str,
        by: Optional[float] = None,
        by_percent: Optional[float] = None,
    ) -> LXWhatIfResult[TModel]:
        """
        Tighten a constraint (decrease RHS for LE, increase for GE).

        Args:
            constraint_name: Name of constraint
            by: Tighten by this amount
            by_percent: Tighten by this percentage

        Returns:
            What-if analysis result
        """
        # Get constraint to determine sense
        constraint = self.model.get_constraint(constraint_name)
        if constraint is None:
            raise ValueError(f"Constraint '{constraint_name}' not found")

        # Tightening is opposite of relaxing
        if constraint.sense == LXConstraintSense.LE:
            # For <= constraints, tightening means decreasing RHS
            if by is not None:
                by = -by
            if by_percent is not None:
                by_percent = -by_percent

        return self._modify_constraint_rhs(
            constraint_name,
            by=by,
            by_percent=by_percent,
            description_prefix="Tighten",
        )

    def modify_variable_bound(
        self,
        variable_name: str,
        lower: Optional[float] = None,
        upper: Optional[float] = None,
    ) -> LXWhatIfResult[TModel]:
        """
        Analyze impact of changing variable bounds.

        Args:
            variable_name: Name of variable
            lower: New lower bound
            upper: New upper bound

        Returns:
            What-if analysis result

        Examples:
            # Increase minimum production to 100
            result = analyzer.modify_variable_bound("production", lower=100)

            # Set production range to [50, 500]
            result = analyzer.modify_variable_bound("production", lower=50, upper=500)
        """
        baseline = self.get_baseline_solution()

        # Clone model and modify
        modified_model = self._new_model()
        variable = modified_model.get_variable(variable_name)
        if variable is None:
            raise ValueError(f"Variable '{variable_name}' not found")

        original_lower = variable.lower_bound
        original_upper = variable.upper_bound

        if lower is not None:
            variable.lower_bound = lower
        if upper is not None:
            variable.upper_bound = upper

        # Solve modified model
        new_solution = self.optimizer.solve(modified_model)

        # Build description
        desc_parts = []
        if lower is not None:
            desc_parts.append(f"lower bound: {original_lower} → {lower}")
        if upper is not None:
            desc_parts.append(f"upper bound: {original_upper} → {upper}")
        description = f"Modify {variable_name} bounds ({', '.join(desc_parts)})"

        return self._build_result(
            description=description,
            baseline=baseline,
            new_solution=new_solution,
            changes_applied=[],
        )

    def compare_changes(
        self,
        changes: List[tuple],  # List of (constraint_name, change_type, value)
        constraint_type: str = "rhs",
    ) -> List[LXWhatIfResult[TModel]]:
        """
        Compare multiple what-if changes.

        Args:
            changes: List of (name, change_type, value) tuples
            constraint_type: Type of change ("rhs", "bound")

        Returns:
            List of what-if results

        Examples:
            Compare different capacity increases::

                results = analyzer.compare_changes([
                    ("capacity", "increase", 100),
                    ("capacity", "increase", 200),
                    ("capacity", "increase", 300),
                ])

                for result in results:
                    print(f"{result.description}: Δ = ${result.delta_objective:,.2f}")
        """
        results = []

        for change in changes:
            name, change_type, value = change

            if change_type == "increase":
                result = self.increase_constraint_rhs(name, by=value)
            elif change_type == "decrease":
                result = self.decrease_constraint_rhs(name, by=value)
            elif change_type == "relax":
                result = self.relax_constraint(name, by=value)
            elif change_type == "tighten":
                result = self.tighten_constraint(name, by=value)
            else:
                raise ValueError(f"Unknown change type: {change_type}")

            results.append(result)

        return results

    def find_bottlenecks(
        self,
        test_amount: float = 1.0,
        top_n: int = 10,
    ) -> List[tuple[str, float]]:
        """
        Find bottleneck constraints by testing small relaxations.

        Tests relaxing each constraint by a small amount and measures
        the impact on the objective function.

        Args:
            test_amount: Amount to relax each constraint
            top_n: Number of top bottlenecks to return

        Returns:
            List of (constraint_name, improvement per unit) sorted best first; improvement
            is positive when relaxing the constraint makes the objective better (larger for
            maximization, smaller for minimization). For an indexed constraint family every
            row is relaxed by ``test_amount``.

        Examples:
            Find top bottlenecks::

                bottlenecks = analyzer.find_bottlenecks(test_amount=1.0, top_n=5)
                print("Top 5 bottlenecks:")
                for name, improvement in bottlenecks:
                    print(f"  {name}: +${improvement:.2f} per unit relaxation")

        .. versionchanged:: 0.3.0
           Values are improvements in the objective's own direction (minimization used to
           rank backwards) and constraints with a per-row RHS are supported (catalog B12).
        """
        baseline = self.get_baseline_solution()
        if not baseline.is_feasible():
            raise ValueError(
                f"find_bottlenecks needs a feasible baseline (status '{baseline.status}')")
        sign = -1.0 if self.model.objective_sense == LXObjectiveSense.MINIMIZE else 1.0

        improvements = []
        for constraint in self.model.constraints:
            result = self.relax_constraint(constraint.name, by=test_amount)
            solution = result.new_solution
            if solution.is_feasible():
                improvement = sign * result.delta_objective / test_amount
            elif solution.status.lower() == "unbounded":
                improvement = math.inf
            else:
                warnings.warn(
                    f"find_bottlenecks: relaxing '{constraint.name}' gave status "
                    f"'{solution.status}'; it is left out of the ranking",
                    UserWarning, stacklevel=2)
                continue
            improvements.append((constraint.name, improvement))

        improvements.sort(key=lambda item: item[1], reverse=True)
        return improvements[:top_n]

    def sensitivity_range(
        self,
        constraint_name: str,
        min_value: float,
        max_value: float,
        num_points: int = 10,
    ) -> List[tuple[float, float]]:
        """
        Analyze objective sensitivity across a range of constraint RHS values.

        Args:
            constraint_name: Name of constraint
            min_value: Minimum RHS value to test
            max_value: Maximum RHS value to test
            num_points: Number of points to sample

        Returns:
            List of (rhs_value, objective_value) tuples

        Examples:
            # Analyze sensitivity to capacity from 800 to 1200
            sensitivity = analyzer.sensitivity_range("capacity", 800, 1200, num_points=20)

            for rhs, obj in sensitivity:
                print(f"Capacity = {rhs:6.1f} → Objective = ${obj:,.2f}")
        """
        import numpy as np

        rhs_values = np.linspace(min_value, max_value, num_points)
        results = []

        for rhs_value in rhs_values:
            result = self.increase_constraint_rhs(constraint_name, to=rhs_value)
            results.append((rhs_value, result.new_objective))

        return results

    def _modify_constraint_rhs(
        self,
        constraint_name: str,
        by: Optional[float] = None,
        by_percent: Optional[float] = None,
        to: Optional[float] = None,
        description_prefix: str = "Modify",
    ) -> LXWhatIfResult[TModel]:
        """
        Internal method to modify constraint RHS.

        Args:
            constraint_name: Name of constraint
            by: Change by this amount
            by_percent: Change by this percentage
            to: Set to this value
            description_prefix: Prefix for description

        Returns:
            What-if analysis result
        """
        baseline = self.get_baseline_solution()

        constraint = self.model.get_constraint(constraint_name)
        if constraint is None:
            raise ValueError(f"Constraint '{constraint_name}' not found")
        if constraint.rhs_value is None and constraint.rhs_func is None:
            raise ValueError(f"Constraint '{constraint_name}' has no RHS value")
        original_rhs = constraint.rhs_value      # None: the RHS is a per-row function

        if to is not None:
            new_rhs: Optional[float] = to
            description = f"{description_prefix} {constraint_name} RHS to {to}"
        elif by is not None:
            new_rhs = None if original_rhs is None else original_rhs + by
            description = f"{description_prefix} {constraint_name} RHS by {by}"
        elif by_percent is not None:
            new_rhs = None if original_rhs is None else original_rhs * (1 + by_percent)
            description = f"{description_prefix} {constraint_name} RHS by {by_percent*100:.1f}%"
        else:
            raise ValueError("Must specify one of: by, by_percent, or to")

        modified_model = self._new_model()
        modified = modified_model.get_constraint(constraint_name)
        if to is not None:
            set_rhs(modified, to)
        elif by is not None:
            shift_rhs(modified, add=by)
        else:
            shift_rhs(modified, multiply=1 + by_percent)

        new_solution = self.optimizer.solve(modified_model)

        change = LXWhatIfChange(
            change_type="constraint_rhs",
            target_name=constraint_name,
            description=description,
            original_value=original_rhs,
            new_value=new_rhs,
            delta=(None if original_rhs is None or new_rhs is None
                   else new_rhs - original_rhs),
        )

        return self._build_result(
            description=description,
            baseline=baseline,
            new_solution=new_solution,
            changes_applied=[change],
        )

    def _new_model(self) -> LXModel[TModel]:
        """A fresh, independent model to modify for one what-if run."""
        return self._source.new()

    def _build_result(
        self,
        description: str,
        baseline: LXSolution[TModel],
        new_solution: LXSolution[TModel],
        changes_applied: List[LXWhatIfChange],
    ) -> LXWhatIfResult[TModel]:
        """
        Build what-if result from baseline and new solution.

        Args:
            description: Description of change
            baseline: Baseline solution
            new_solution: New solution
            changes_applied: List of changes applied

        Returns:
            What-if result
        """
        delta_obj = new_solution.objective_value - baseline.objective_value

        if baseline.objective_value != 0:
            delta_pct = (delta_obj / baseline.objective_value) * 100
        else:
            delta_pct = 0.0

        return LXWhatIfResult(
            description=description,
            original_objective=baseline.objective_value,
            new_objective=new_solution.objective_value,
            delta_objective=delta_obj,
            delta_percentage=delta_pct,
            original_solution=baseline,
            new_solution=new_solution,
            changes_applied=changes_applied,
        )


__all__ = [
    "LXWhatIfAnalyzer",
    "LXWhatIfResult",
    "LXWhatIfChange",
]
