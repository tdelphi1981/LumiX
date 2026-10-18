"""One definition of "percent change from the baseline" for analysis and charts."""
import math


def pct_change(new: float, base: float) -> float:
    """Signed change of ``new`` from ``base`` in percent of ``|base|``: positive when the
    objective rises, whatever its sign. ``nan`` for a zero or non-finite base."""
    if not base or not math.isfinite(base) or not math.isfinite(new):
        return math.nan
    return (new - base) / abs(base) * 100.0
