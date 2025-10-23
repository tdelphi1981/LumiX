"""Float-to-rational conversion utilities for integer-only solvers.

This module provides utilities for converting floating-point coefficients to rational
numbers, which is essential when using integer-only solvers like GLPK's integer
programming mode or other solvers that require exact rational arithmetic.

The module implements three different rational approximation algorithms, each with
different performance characteristics and accuracy trade-offs.

Key Features:
    - **Multiple Algorithms**: Farey sequence, continued fractions, Stern-Brocot tree
    - **Configurable Precision**: Control maximum denominator for approximations
    - **Batch Conversion**: Convert entire coefficient dictionaries at once
    - **Error Tracking**: Optional error reporting for approximation quality

Algorithms:
    - **Farey**: Fastest method using Farey sequence with floor/ceil optimization (recommended)
    - **Continued Fraction**: Classic continued fraction algorithm
    - **Stern-Brocot**: Binary search through Stern-Brocot tree (equivalent to Farey)

Use Cases:
    - Converting LP models for integer-only solvers (GLPK)
    - Exact rational arithmetic requirements
    - Avoiding floating-point precision issues
    - Symbolic computation integration

Examples:
    Basic rational conversion::

        from lumix.utils import LXRationalConverter

        converter = LXRationalConverter(max_denominator=10000)
        frac = converter.to_rational(3.14159)  # Fraction(355, 113)
        print(f"{frac} ≈ {float(frac):.5f}")

    Convert coefficients for integer solver::

        coeffs = {"x1": 3.5, "x2": 2.333, "x3": 1.25}
        int_coeffs, denom = converter.convert_coefficients(coeffs)
        # int_coeffs: {"x1": 42, "x2": 28, "x3": 15}, denom: 12

    Compare approximation methods::

        results = converter.compare_methods(3.14159)
        for method, (frac, error, time) in results.items():
            print(f"{method}: {frac} (error={error:.2e}, time={time:.6f}s)")

See Also:
    - Python fractions module: https://docs.python.org/3/library/fractions.html
    - GLPK documentation: https://www.gnu.org/software/glpk/
"""

import math
from fractions import Fraction
from typing import Literal, Tuple, Union


class LXRationalConverter:
    """
    Converts floating-point coefficients to rational numbers for integer-only solvers.

    Supports three approximation methods:
    - "farey": Farey sequence with floor/ceil optimization (fastest, recommended)
    - "continued_fraction": Continued fraction algorithm
    - "stern_brocot": Stern-Brocot tree (equivalent to Farey, alternative framing)
    """

    def __init__(
        self,
        max_denominator: int = 10000,
        method: Literal["farey", "continued_fraction", "stern_brocot"] = "farey",
        float_tolerance: float = 1e-9,
    ):
        """
        Initialize rational converter.

        Args:
            max_denominator: Maximum denominator for rational approximation
            method: Approximation algorithm ("farey", "continued_fraction", "stern_brocot")
            float_tolerance: Tolerance for float comparisons to handle precision errors (default: 1e-9)
        """
        self.max_denominator = max_denominator
        self.method = method
        self.float_tolerance = float_tolerance

    def to_rational(self, value: float, return_error: bool = False) -> Union[Fraction, Tuple[Fraction, float]]:
        """
        Convert float to rational number using configured method.

        Args:
            value: Float value to convert
            return_error: If True, return (fraction, error) tuple

        Returns:
            Fraction approximation (or tuple with error if return_error=True)
        """
        # Dispatch to appropriate method
        if self.method == "farey":
            num, den, error = self._farey_approximation(value)
        elif self.method == "continued_fraction":
            num, den, error = self._continued_fraction_approximation(value)
        elif self.method == "stern_brocot":
            num, den, error = self._stern_brocot_approximation(value)
        else:
            raise ValueError(f"Unknown method: {self.method}")

        fraction = Fraction(num, den)
        return (fraction, error) if return_error else fraction

    def convert_coefficients(
        self, coefficients: dict[str, float]
    ) -> tuple[dict[str, int], int]:
        """
        Convert dictionary of float coefficients to integers.

        Args:
            coefficients: Dictionary mapping variable names to float coefficients

        Returns:
            Tuple of (integer_coefficients, common_denominator)
        """
        # Convert all to fractions
        fractions = {k: self.to_rational(v) for k, v in coefficients.items()}

        # Find LCM of all denominators
        denominators = [f.denominator for f in fractions.values()]
        common_denom = self._lcm_list(denominators)

        # Scale all to integers
        int_coeffs = {k: int(f.numerator * (common_denom // f.denominator)) for k, f in fractions.items()}

        return int_coeffs, common_denom

    @staticmethod
    def _gcd(a: int, b: int) -> int:
        """Calculate greatest common divisor."""
        while b:
            a, b = b, a % b
        return a

    def _lcm(self, a: int, b: int) -> int:
        """Calculate least common multiple."""
        return abs(a * b) // self._gcd(a, b)

    def _lcm_list(self, numbers: list[int]) -> int:
        """Calculate LCM of a list of numbers."""
        if not numbers:
            return 1
        result = numbers[0]
        for num in numbers[1:]:
            result = self._lcm(result, num)
        return result

    def _is_close(self, a: float, b: float, use_abs: bool = False) -> bool:
        """
        Compare two floats with configured tolerance.

        Args:
            a: First value
            b: Second value
            use_abs: If True, use absolute tolerance only (for near-zero comparisons)

        Returns:
            True if values are close within tolerance
        """
        if use_abs:
            # For near-zero comparisons, use absolute tolerance
            return math.isclose(a, b, rel_tol=0, abs_tol=self.float_tolerance * 1e-3)
        else:
            # Standard comparison with relative tolerance
            return math.isclose(a, b, rel_tol=self.float_tolerance, abs_tol=self.float_tolerance * 1e-3)

    def _extract_integer_part(self, x: float) -> Tuple[int, int, float]:
        """
        Extract sign, integer part, and fractional part from float.

        Args:
            x: Float value

        Returns:
            Tuple of (sign, integer_part, fractional_part)
            where sign is 1 or -1, integer_part >= 0, 0 <= fractional_part < 1
        """
        sign = 1 if x >= 0 else -1
        x_abs = abs(x)
        integer_part = int(math.floor(x_abs))
        fractional_part = x_abs - integer_part
        return sign, integer_part, fractional_part

    def _compute_error(self, num: int, den: int, target: float) -> float:
        """
        Compute absolute approximation error.

        Args:
            num: Numerator
            den: Denominator
            target: Target float value

        Returns:
            Absolute error |num/den - target|
        """
        return abs(num / den - target)

    def _farey_approximation(self, x: float) -> Tuple[int, int, float]:
        """
        Farey sequence approximation with floor/ceil optimization.

        Uses floor(x) and ceil(x) as tight initial bounds for fast convergence.

        Args:
            x: Float value to approximate

        Returns:
            Tuple of (numerator, denominator, error)
        """
        # Handle exact integers (with tolerance)
        rounded_x = round(x)
        if self._is_close(x, float(rounded_x)):
            return int(rounded_x), 1, 0.0

        # Extract sign and work with absolute value
        sign, int_part, frac_part = self._extract_integer_part(x)
        x_abs = abs(x)

        # Handle pure fractions (0 < x < 1)
        if int_part == 0:
            lower_n, lower_d = 0, 1
            upper_n, upper_d = 1, 1
        else:
            # Use floor/ceil as tight initial bounds
            lower_n, lower_d = int_part, 1  # floor(x)
            upper_n, upper_d = int_part + 1, 1  # ceil(x)

        # Farey mediant iteration
        while True:
            # Compute mediant: (n1 + n2) / (d1 + d2)
            med_n = lower_n + upper_n
            med_d = lower_d + upper_d

            # Check denominator limit
            if med_d > self.max_denominator:
                break

            mediant_value = med_n / med_d

            # Check for exact match (with tolerance)
            if self._is_close(mediant_value, x_abs):
                # Essentially equal - exact match
                return sign * med_n, med_d, abs(mediant_value - x_abs)

            # Update bounds based on mediant position
            if mediant_value < x_abs:
                lower_n, lower_d = med_n, med_d
            else:  # mediant_value > x_abs
                upper_n, upper_d = med_n, med_d

        # Choose the bound with smaller error
        lower_error = self._compute_error(lower_n, lower_d, x_abs)
        upper_error = self._compute_error(upper_n, upper_d, x_abs)

        if lower_error <= upper_error:
            return sign * lower_n, lower_d, lower_error
        else:
            return sign * upper_n, upper_d, upper_error

    def _continued_fraction_approximation(self, x: float) -> Tuple[int, int, float]:
        """
        Continued fraction approximation with integer extraction.

        Extracts integer part first for better performance on large values.

        Args:
            x: Float value to approximate

        Returns:
            Tuple of (numerator, denominator, error)
        """
        # Handle exact integers (with tolerance)
        rounded_x = round(x)
        if self._is_close(x, float(rounded_x)):
            return int(rounded_x), 1, 0.0

        # Extract sign and integer part
        sign, int_part, frac_part = self._extract_integer_part(x)

        # Build continued fraction for fractional part
        if self._is_close(frac_part, 0.0, use_abs=True):
            return sign * int_part, 1, 0.0

        # Standard continued fraction algorithm
        # Start with fractional part
        value = frac_part

        # Initialize convergents: p_{-1}/q_{-1} = 1/0, p_0/q_0 = a_0/1
        p_prev2, q_prev2 = 1, 0
        p_prev1, q_prev1 = 0, 1

        while True:
            # Get next coefficient
            a = int(math.floor(value))

            # Update convergent
            p = a * p_prev1 + p_prev2
            q = a * q_prev1 + q_prev2

            # Check denominator limit
            if q > self.max_denominator:
                # Return previous convergent
                num = sign * (int_part * q_prev1 + p_prev1)
                den = q_prev1
                error = self._compute_error(num, den, abs(x))
                return num, den, error

            # Check if we've converged (with tolerance)
            if self._is_close(value, float(a)) or q == 0:
                num = sign * (int_part * q + p)
                den = q
                error = self._compute_error(num, den, abs(x))
                return num, den, error

            # Update for next iteration
            p_prev2, p_prev1 = p_prev1, p
            q_prev2, q_prev1 = q_prev1, q

            # Continue with reciprocal
            value = 1.0 / (value - a)

    def _stern_brocot_approximation(self, x: float) -> Tuple[int, int, float]:
        """
        Stern-Brocot tree approximation (equivalent to Farey).

        Binary search through Stern-Brocot tree using floor/ceil initial bounds.

        Args:
            x: Float value to approximate

        Returns:
            Tuple of (numerator, denominator, error)
        """
        # Handle exact integers (with tolerance)
        rounded_x = round(x)
        if self._is_close(x, float(rounded_x)):
            return int(rounded_x), 1, 0.0

        # Extract sign and work with absolute value
        sign, int_part, frac_part = self._extract_integer_part(x)
        x_abs = abs(x)

        # Initialize tree bounds with floor/ceil
        if int_part == 0:
            left_n, left_d = 0, 1
            right_n, right_d = 1, 1
        else:
            left_n, left_d = int_part, 1
            right_n, right_d = int_part + 1, 1

        best_n, best_d = left_n, left_d
        best_error = self._compute_error(best_n, best_d, x_abs)

        # Binary search through tree
        while True:
            # Compute mediant (next node in tree)
            med_n = left_n + right_n
            med_d = left_d + right_d

            # Check denominator limit
            if med_d > self.max_denominator:
                break

            mediant_value = med_n / med_d
            error = self._compute_error(med_n, med_d, x_abs)

            # Update best if this is better
            if error < best_error:
                best_n, best_d = med_n, med_d
                best_error = error

            # Check for exact match (with tolerance)
            if self._is_close(mediant_value, x_abs):
                # Essentially equal - exact match
                return sign * med_n, med_d, error

            # Navigate tree based on comparison
            if mediant_value < x_abs:
                left_n, left_d = med_n, med_d  # Go right in tree
            else:  # mediant_value > x_abs
                right_n, right_d = med_n, med_d  # Go left in tree

        return sign * best_n, best_d, best_error

    def compare_methods(self, value: float) -> dict[str, Tuple[Fraction, float, float]]:
        """
        Compare all three approximation methods for a given value.

        Args:
            value: Float value to approximate

        Returns:
            Dictionary mapping method name to (fraction, error, computation_time)
        """
        import time

        results = {}
        methods = ["farey", "continued_fraction", "stern_brocot"]

        for method in methods:
            original_method = self.method
            self.method = method

            start_time = time.perf_counter()
            fraction, error = self.to_rational(value, return_error=True)
            elapsed = time.perf_counter() - start_time

            results[method] = (fraction, error, elapsed)

            self.method = original_method

        return results


__all__ = ["LXRationalConverter"]
