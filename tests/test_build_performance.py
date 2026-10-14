"""Build-time benchmark for keyed terms (Performance Considerations, user guide)."""

import time

import pytest

pytest.importorskip("ortools")

from lumix.solvers.ortools_solver import LXORToolsSolver

from .test_instance_cache import transport


def _build_seconds(keyed: bool, n: int, repeats: int = 2) -> float:
    """Best of ``repeats`` builds, to keep the comparison stable on a busy machine."""
    times = []
    for _ in range(repeats):
        model = transport(n, keyed=keyed)[0]
        start = time.perf_counter()
        LXORToolsSolver().build_model(model)
        times.append(time.perf_counter() - start)
    return min(times)


@pytest.mark.slow
def test_keys_build_at_least_five_times_faster_than_where():
    n = 300  # 600 rows, 90,000 variables
    keyed = _build_seconds(True, n)
    scanned = _build_seconds(False, n)
    print(f"\nn={n}: where {scanned:.2f}s, keys {keyed:.2f}s, ratio {scanned / keyed:.1f}x")
    assert scanned / keyed >= 5
