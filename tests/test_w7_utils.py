"""W7: utilities (rational conversion, exports, logging)."""

from fractions import Fraction

import pytest

from lumix.utils import LXRationalConverter


@pytest.mark.parametrize(
    "value, expected",
    [
        (0.5, Fraction(1, 2)),
        (-0.5, Fraction(-1, 2)),
        (2.333, Fraction(2333, 1000)),
        (-2.75, Fraction(-11, 4)),
        (3.14159, Fraction(9563, 3044)),
        (0.1, Fraction(1, 10)),
        (-0.1, Fraction(-1, 10)),
        (0.9999, Fraction(9999, 10000)),
        (1e-7, Fraction(0)),
        (-1e-7, Fraction(0)),
        (7.0, Fraction(7)),
    ],
)
def test_b13_continued_fraction_converges(value, expected):
    conv = LXRationalConverter(max_denominator=10000, method="continued_fraction")
    assert conv.to_rational(value) == expected


def test_b13_continued_fraction_respects_max_denominator():
    conv = LXRationalConverter(max_denominator=100, method="continued_fraction")
    frac = conv.to_rational(3.14159265)
    assert frac == Fraction(311, 99) or frac == Fraction(22, 7)
    assert frac.denominator <= 100


def test_b17_documented_top_level_imports():
    import lumix
    from lumix import CPSAT_CAPABILITIES, GLPK_CAPABILITIES, LXPiecewiseLinearizer, LXRowKeyFilter

    assert CPSAT_CAPABILITIES.name and GLPK_CAPABILITIES.name
    assert LXPiecewiseLinearizer.__name__ == "LXPiecewiseLinearizer"
    assert LXRowKeyFilter.__name__ == "LXRowKeyFilter"
    for name in ("CPSAT_CAPABILITIES", "GLPK_CAPABILITIES", "LXPiecewiseLinearizer", "LXRowKeyFilter"):
        assert name in lumix.__all__
