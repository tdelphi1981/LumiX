"""Solver capability detection and management."""

from dataclasses import dataclass
from enum import Enum, Flag, auto


class LXSolverFeature(Flag):
    """
    Solver features/capabilities (bit flags for combinations).

    Basic:
        LINEAR: Linear programming
        INTEGER: Integer variables
        BINARY: Binary variables
        MIXED_INTEGER: Mixed-integer programming (LP + INTEGER)

    Advanced:
        QUADRATIC_CONVEX: Convex quadratic programming
        QUADRATIC_NONCONVEX: Non-convex quadratic programming
        SOCP: Second-order cone programming
        SDP: Semidefinite programming

    Special:
        SOS1: Special Ordered Set type 1
        SOS2: Special Ordered Set type 2
        INDICATOR: Indicator constraints
        CARDINALITY: Cardinality constraints

    Non-linear:
        PWL: Piecewise-linear functions
        EXPONENTIAL_CONE: Exponential cone constraints
        LOG: Logarithmic constraints

    Features:
        LAZY_CONSTRAINTS: Lazy constraint callbacks
        USER_CUTS: User cut callbacks
        HEURISTICS: Custom heuristics
        IIS: Irreducible Inconsistent Subsystem
        CONFLICT_REFINEMENT: Conflict refinement
    """

    # Basic
    LINEAR = auto()
    INTEGER = auto()
    BINARY = auto()
    MIXED_INTEGER = LINEAR | INTEGER

    # Advanced
    QUADRATIC_CONVEX = auto()
    QUADRATIC_NONCONVEX = auto()
    SOCP = auto()
    SDP = auto()

    # Special
    SOS1 = auto()
    SOS2 = auto()
    INDICATOR = auto()
    CARDINALITY = auto()

    # Non-linear
    PWL = auto()
    EXPONENTIAL_CONE = auto()
    LOG = auto()

    # Features
    LAZY_CONSTRAINTS = auto()
    USER_CUTS = auto()
    HEURISTICS = auto()
    IIS = auto()
    CONFLICT_REFINEMENT = auto()
    SENSITIVITY_ANALYSIS = auto()


@dataclass
class LXSolverCapability:
    """
    Describes a solver's capabilities.

    Used to:
    - Query what features a solver supports
    - Automatically select appropriate linearization methods
    - Provide meaningful errors when features are unavailable
    """

    name: str
    features: LXSolverFeature
    max_variables: int = 2**31 - 1
    max_constraints: int = 2**31 - 1
    supports_warmstart: bool = False
    supports_parallel: bool = False
    supports_callbacks: bool = False

    def has_feature(self, feature: LXSolverFeature) -> bool:
        """
        Check if solver has a specific feature.

        Args:
            feature: Feature to check

        Returns:
            True if solver supports the feature
        """
        return bool(self.features & feature)

    def can_solve_quadratic(self) -> bool:
        """Check if solver can handle quadratic objectives."""
        return self.has_feature(LXSolverFeature.QUADRATIC_CONVEX) or self.has_feature(
            LXSolverFeature.QUADRATIC_NONCONVEX
        )

    def can_solve_integer(self) -> bool:
        """Check if solver can handle integer variables."""
        return self.has_feature(LXSolverFeature.INTEGER) or self.has_feature(LXSolverFeature.BINARY)

    def can_use_sos2(self) -> bool:
        """Check if solver has native SOS2 support."""
        return self.has_feature(LXSolverFeature.SOS2)

    def can_use_indicator(self) -> bool:
        """Check if solver has native indicator constraint support."""
        return self.has_feature(LXSolverFeature.INDICATOR)

    def description(self) -> str:
        """Get human-readable capability description."""
        capabilities = []

        if self.has_feature(LXSolverFeature.LINEAR):
            capabilities.append("Linear Programming")
        if self.has_feature(LXSolverFeature.MIXED_INTEGER):
            capabilities.append("Mixed-Integer Programming")
        if self.can_solve_quadratic():
            capabilities.append("Quadratic Programming")
        if self.has_feature(LXSolverFeature.SOCP):
            capabilities.append("Second-Order Cone Programming")
        if self.has_feature(LXSolverFeature.SDP):
            capabilities.append("Semidefinite Programming")

        return f"{self.name}: {', '.join(capabilities)}"


# Pre-defined capabilities for common solvers
ORTOOLS_CAPABILITIES = LXSolverCapability(
    name="OR-Tools",
    features=(
        LXSolverFeature.LINEAR
        | LXSolverFeature.INTEGER
        | LXSolverFeature.BINARY
        | LXSolverFeature.SOS1
        | LXSolverFeature.SOS2
        | LXSolverFeature.INDICATOR
    ),
    supports_warmstart=True,
    supports_parallel=True,
)

GUROBI_CAPABILITIES = LXSolverCapability(
    name="Gurobi",
    features=(
        LXSolverFeature.LINEAR
        | LXSolverFeature.INTEGER
        | LXSolverFeature.BINARY
        | LXSolverFeature.QUADRATIC_CONVEX
        | LXSolverFeature.QUADRATIC_NONCONVEX
        | LXSolverFeature.SOCP
        | LXSolverFeature.SOS1
        | LXSolverFeature.SOS2
        | LXSolverFeature.INDICATOR
        | LXSolverFeature.PWL
        | LXSolverFeature.LAZY_CONSTRAINTS
        | LXSolverFeature.USER_CUTS
        | LXSolverFeature.IIS
        | LXSolverFeature.CONFLICT_REFINEMENT
        | LXSolverFeature.SENSITIVITY_ANALYSIS
    ),
    supports_warmstart=True,
    supports_parallel=True,
    supports_callbacks=True,
)

CPLEX_CAPABILITIES = LXSolverCapability(
    name="CPLEX",
    features=(
        LXSolverFeature.LINEAR
        | LXSolverFeature.INTEGER
        | LXSolverFeature.BINARY
        | LXSolverFeature.QUADRATIC_CONVEX
        | LXSolverFeature.QUADRATIC_NONCONVEX
        | LXSolverFeature.SOCP
        | LXSolverFeature.SOS1
        | LXSolverFeature.SOS2
        | LXSolverFeature.INDICATOR
        | LXSolverFeature.PWL
        | LXSolverFeature.LAZY_CONSTRAINTS
        | LXSolverFeature.USER_CUTS
        | LXSolverFeature.IIS
        | LXSolverFeature.CONFLICT_REFINEMENT
        | LXSolverFeature.SENSITIVITY_ANALYSIS
    ),
    supports_warmstart=True,
    supports_parallel=True,
    supports_callbacks=True,
)


__all__ = [
    "LXSolverFeature",
    "LXSolverCapability",
    "ORTOOLS_CAPABILITIES",
    "GUROBI_CAPABILITIES",
    "CPLEX_CAPABILITIES",
]
