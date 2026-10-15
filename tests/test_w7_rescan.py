"""W7 re-scan gate: findings of the second bug hunt."""
from fractions import Fraction

import pytest

from lumix import LXRationalConverter


@pytest.mark.parametrize("method", ["farey", "continued_fraction", "stern_brocot"])
@pytest.mark.parametrize("value", [-0.5, -2.75, -0.1])
def test_w7_rational_error_of_a_negative_value_is_zero_when_exact(method, value):
    fraction, error = LXRationalConverter(method=method).to_rational(value, return_error=True)
    assert fraction == Fraction(value).limit_denominator(10**6)
    assert error == pytest.approx(abs(float(fraction) - value), abs=1e-15)
    assert error < 1e-12


@pytest.mark.parametrize("method", ["farey", "continued_fraction", "stern_brocot"])
def test_w7_rational_error_reports_the_rounding_of_a_near_integer(method):
    value = 1e12 + 0.5
    fraction, error = LXRationalConverter(method=method).to_rational(value, return_error=True)
    assert error == pytest.approx(abs(float(fraction) - value))
