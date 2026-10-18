"""One definition of "percent change from the baseline" for analysis and charts."""
import math


def pct_change(new: float, base: float) -> float:
    """Signed change of ``new`` from ``base`` in percent of ``|base|``: positive when the
    objective rises, whatever its sign. ``nan`` for a zero or non-finite base. A change
    below 1e-9 percent is floating-point noise and reported as 0 (no "-0.0%")."""
    if not base or not math.isfinite(base) or not math.isfinite(new):
        return math.nan
    pct = (new - base) / abs(base) * 100.0
    return 0.0 if abs(pct) < 1e-9 else pct
