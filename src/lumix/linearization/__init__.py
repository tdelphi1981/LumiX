"""
Linearization engine for automatic nonlinear term conversion.

This module provides automatic linearization of nonlinear optimization terms
to convert them into linear or mixed-integer linear programming (MILP) formulations
that can be solved by standard solvers.

The linearization engine automatically detects nonlinear terms in your model and
applies appropriate linearization techniques based on:
- Variable types (continuous, integer, binary)
- Solver capabilities (native quadratic support, SOS2 support, etc.)
- User configuration (method preferences, accuracy requirements)

Main Components:
    - :class:`~lumix.linearization.engine.LXLinearizer`: Main linearization engine
    - :class:`~lumix.linearization.config.LXLinearizerConfig`: Configuration settings
    - :class:`~lumix.linearization.config.LXLinearizationMethod`: Available methods
    - :class:`~lumix.linearization.functions.LXNonLinearFunctions`: Pre-built function approximations
    - :class:`~lumix.linearization.techniques.LXBilinearLinearizer`: Bilinear product linearization
    - :class:`~lumix.linearization.techniques.LXPiecewiseLinearizer`: Piecewise-linear approximation

Supported Linearization Techniques:
    - **Bilinear Products** (x * y): McCormick envelopes, Big-M, Binary AND
    - **Absolute Values** (|x|): Linear reformulation with auxiliary variables
    - **Min/Max Functions**: Linear reformulation with auxiliary constraints
    - **Piecewise-Linear**: SOS2, incremental, and logarithmic formulations
    - **Indicator Constraints**: Big-M method for conditional constraints

Example:
    Basic usage with automatic linearization::

        from lumix.linearization import LXLinearizer, LXLinearizerConfig
        from lumix.solvers.capabilities import LXSolverCapability

        # Configure linearization
        config = LXLinearizerConfig(
            default_method=LXLinearizationMethod.MCCORMICK,
            pwl_num_segments=30,
            adaptive_breakpoints=True
        )

        # Create linearizer
        linearizer = LXLinearizer(model, solver_capability, config)

        # Check if linearization needed
        if linearizer.needs_linearization():
            linearized_model = linearizer.linearize_model()
            solution = solver.solve(linearized_model)
        else:
            solution = solver.solve(model)

See Also:
    - :doc:`/user-guide/linearization/index` - User guide for linearization
    - :doc:`/api/linearization/index` - Complete API reference
    - :doc:`/development/linearization-architecture` - Architecture details
"""

from .config import LXLinearizerConfig, LXLinearizationMethod
from .engine import LXLinearizer
from .functions import LXNonLinearFunctions
from .techniques import LXBilinearLinearizer, LXPiecewiseLinearizer

__all__ = [
    "LXLinearizerConfig",
    "LXLinearizationMethod",
    "LXLinearizer",
    "LXNonLinearFunctions",
    "LXBilinearLinearizer",
    "LXPiecewiseLinearizer",
]
