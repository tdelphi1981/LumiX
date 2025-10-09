"""CPLEX solver implementation (stub)."""

from typing import Any, Optional

from ..core.model import LXModel
from ..solution.solution import LXSolution
from .base import LXSolverInterface
from .capabilities import CPLEX_CAPABILITIES


class LXCPLEXSolver(LXSolverInterface):
    """CPLEX solver implementation."""

    def __init__(self) -> None:
        """Initialize CPLEX solver."""
        super().__init__(CPLEX_CAPABILITIES)

    def build_model(self, model: LXModel) -> Any:
        """Build CPLEX model (stub)."""
        raise NotImplementedError("CPLEX solver not yet implemented")

    def solve(
        self,
        model: LXModel,
        time_limit: Optional[float] = None,
        gap_tolerance: Optional[float] = None,
        **solver_params: Any,
    ) -> LXSolution:
        """Solve with CPLEX (stub)."""
        raise NotImplementedError("CPLEX solver not yet implemented")

    def get_solver_model(self) -> Any:
        """Get CPLEX model (stub)."""
        raise NotImplementedError("CPLEX solver not yet implemented")


__all__ = ["LXCPLEXSolver"]
