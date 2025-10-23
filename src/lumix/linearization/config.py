"""Configuration for linearization engine."""

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class LXLinearizationMethod(Enum):
    """
    Available linearization techniques.

    Methods:
        MCCORMICK: McCormick envelopes for continuous × continuous products
        BIG_M: Big-M method for conditional constraints
        BINARY_EXPANSION: Binary expansion for integer × integer products
        SOS2: Special Ordered Set type 2 for piecewise-linear
        LOGARITHMIC: Logarithmic (Gray code) encoding for large integer products
    """

    MCCORMICK = "mccormick"
    BIG_M = "big_m"
    BINARY_EXPANSION = "binary_expansion"
    SOS2 = "sos2"
    LOGARITHMIC = "logarithmic"


@dataclass
class LXLinearizerConfig:
    """
    Configuration for automatic linearization engine.

    Attributes:
        default_method: Default linearization technique
        big_m_value: Big-M constant for conditional constraints (default: 1e6)
        pwl_num_segments: Number of segments for piecewise-linear approximations
        pwl_method: Method for piecewise-linear ("sos2", "incremental", "logarithmic")
        prefer_sos2: Use SOS2 formulation when solver supports it
        adaptive_breakpoints: Use adaptive breakpoint generation for PWL
        auto_detect_bounds: Automatically detect variable bounds for McCormick
        mccormick_tighten_bounds: Apply bound tightening for McCormick envelopes
        binary_expansion_bits: Number of bits for binary expansion method
        tolerance: Numerical tolerance for comparisons
        verbose_logging: Enable detailed linearization logging

    Example::

        config = LXLinearizerConfig(
            big_m_value=1e5,
            pwl_num_segments=30,
            adaptive_breakpoints=True,
            mccormick_tighten_bounds=True
        )
    """

    # General settings
    default_method: LXLinearizationMethod = LXLinearizationMethod.MCCORMICK
    tolerance: float = 1e-6
    verbose_logging: bool = True

    # Big-M settings
    big_m_value: float = 1e6

    # Piecewise-linear settings
    pwl_num_segments: int = 20
    pwl_method: Literal["sos2", "incremental", "logarithmic"] = "sos2"
    prefer_sos2: bool = True
    adaptive_breakpoints: bool = True

    # McCormick envelope settings
    auto_detect_bounds: bool = True
    mccormick_tighten_bounds: bool = True

    # Binary expansion settings
    binary_expansion_bits: int = 10  # For integers up to 2^10 = 1024


__all__ = [
    "LXLinearizationMethod",
    "LXLinearizerConfig",
]
