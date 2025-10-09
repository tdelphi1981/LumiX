"""Gurobi solver implementation (stub)."""

from typing import Any, Optional

from ..core.model import LXModel
from ..solution.solution import LXSolution
from .base import LXSolverInterface
from .capabilities import GUROBI_CAPABILITIES


class LXGurobiSolver(LXSolverInterface):
    """Gurobi solver implementation."""

    def __init__(self) -> None:
        """Initialize Gurobi solver."""
        super().__init__(GUROBI_CAPABILITIES)

    def build_model(self, model: LXModel) -> Any:
        """Build Gurobi model (stub)."""
        raise NotImplementedError("Gurobi solver not yet implemented")

    def solve(
        self,
        model: LXModel,
        time_limit: Optional[float] = None,
        gap_tolerance: Optional[float] = None,
        **solver_params: Any,
    ) -> LXSolution:
        """Solve with Gurobi (stub)."""
        raise NotImplementedError("Gurobi solver not yet implemented")

    def get_solver_model(self) -> Any:
        """Get Gurobi model (stub)."""
        raise NotImplementedError("Gurobi solver not yet implemented")


__all__ = ["LXGurobiSolver"]
