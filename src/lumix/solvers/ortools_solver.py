"""OR-Tools solver implementation (stub)."""

from typing import Any, Optional

from ..core.model import LXModel
from ..solution.solution import LXSolution
from .base import LXSolverInterface
from .capabilities import ORTOOLS_CAPABILITIES


class LXORToolsSolver(LXSolverInterface):
    """OR-Tools solver implementation."""

    def __init__(self) -> None:
        """Initialize OR-Tools solver."""
        super().__init__(ORTOOLS_CAPABILITIES)

    def build_model(self, model: LXModel) -> Any:
        """Build OR-Tools model (stub)."""
        raise NotImplementedError("OR-Tools solver not yet implemented")

    def solve(
        self,
        model: LXModel,
        time_limit: Optional[float] = None,
        gap_tolerance: Optional[float] = None,
        **solver_params: Any,
    ) -> LXSolution:
        """Solve with OR-Tools (stub)."""
        raise NotImplementedError("OR-Tools solver not yet implemented")

    def get_solver_model(self) -> Any:
        """Get OR-Tools model (stub)."""
        raise NotImplementedError("OR-Tools solver not yet implemented")


__all__ = ["LXORToolsSolver"]
