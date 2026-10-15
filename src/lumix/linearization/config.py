"""Configuration for linearization engine."""

import warnings
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
        big_m_value: Bound for an indicator or a binary product when the
            expression or variable has no finite bound (default: 1e6)
        pwl_num_segments: Number of segments for piecewise-linear approximations
            whose term leaves ``num_segments`` open
        pwl_method: Method for piecewise-linear ("sos2", "incremental", "logarithmic")
            when the term leaves ``method`` open
        adaptive_breakpoints: Use adaptive breakpoint generation for PWL when the
            term leaves ``adaptive`` open
        binary_expansion_bits: Largest number of bits of an integer factor in an
            exact product
        default_method: No effect (deprecated in 0.3.0)
        prefer_sos2: No effect (deprecated in 0.3.0)
        auto_detect_bounds: No effect (deprecated in 0.3.0)
        mccormick_tighten_bounds: No effect (deprecated in 0.3.0)
        tolerance: No effect (deprecated in 0.3.0)
        verbose_logging: No effect (deprecated in 0.3.0)

    Setting a field marked "no effect" to a non-default value issues a
    ``DeprecationWarning``; these fields are removed in 0.4.0.

    Example::

        config = LXLinearizerConfig(
            big_m_value=1e5,
            pwl_num_segments=30,
            adaptive_breakpoints=True,
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

    def __post_init__(self) -> None:
        for name, default in _UNUSED.items():
            if getattr(self, name) != default:
                warnings.warn(
                    f"LXLinearizerConfig.{name} has no effect and will be removed in 0.4.0",
                    DeprecationWarning, stacklevel=3)


#: Fields that no technique reads; setting them warns (B9). Removed in 0.4.0.
_UNUSED = {
    "default_method": LXLinearizationMethod.MCCORMICK,
    "tolerance": 1e-6,
    "verbose_logging": True,
    "prefer_sos2": True,
    "auto_detect_bounds": True,
    "mccormick_tighten_bounds": True,
}


__all__ = [
    "LXLinearizationMethod",
    "LXLinearizerConfig",
]
