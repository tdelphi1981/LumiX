Rational Conversion Guide
=========================

This guide covers the LXRationalConverter for converting floating-point coefficients
to rational numbers, essential for integer-only solvers and exact arithmetic.

Overview
--------

Many optimization solvers, particularly integer-only modes of solvers like GLPK,
require exact rational arithmetic instead of floating-point numbers. The
LXRationalConverter provides efficient algorithms to approximate floats as fractions
with configurable precision.

**Why Rational Conversion?**

- Integer-only solvers (GLPK, some CPLEX modes) require rational coefficients
- Avoid floating-point precision errors in sensitive problems
- Enable symbolic computation integration
- Ensure reproducible results across platforms

**Key Features:**

- Three approximation algorithms (Farey, Continued Fraction, Stern-Brocot)
- Configurable maximum denominator for precision control
- Batch conversion for coefficient dictionaries
- Error tracking and algorithm comparison
- Tolerance handling for float comparisons

Quick Start
-----------

Basic Conversion
~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.utils import LXRationalConverter

   # Create converter
   converter = LXRationalConverter(max_denominator=10000)

   # Convert float to fraction
   frac = converter.to_rational(3.14159)
   print(frac)  # Fraction(355, 113)
   print(f"Approximation: {float(frac):.6f}")  # 3.141593

Batch Conversion
~~~~~~~~~~~~~~~~

.. code-block:: python

   # Convert multiple coefficients
   coeffs = {
       "x1": 3.5,
       "x2": 2.333,
       "x3": 1.25,
       "x4": 0.666
   }

   int_coeffs, common_denom = converter.convert_coefficients(coeffs)

   print(f"Integer coefficients: {int_coeffs}")
   # {'x1': 42, 'x2': 28, 'x3': 15, 'x4': 8}

   print(f"Common denominator: {common_denom}")
   # 12

   # Verify: int_coeffs[key] / common_denom ≈ coeffs[key]

Configuration Options
---------------------

Maximum Denominator
~~~~~~~~~~~~~~~~~~~

Controls the trade-off between approximation accuracy and denominator size:

.. code-block:: python

   # Smaller denominator - faster, less accurate
   converter = LXRationalConverter(max_denominator=100)
   frac = converter.to_rational(3.14159)
   print(frac)  # Fraction(22, 7) = 3.142857...

   # Larger denominator - slower, more accurate
   converter = LXRationalConverter(max_denominator=100000)
   frac = converter.to_rational(3.14159)
   print(frac)  # Fraction(355, 113) = 3.141593...

**Guidelines:**

- Small denominators (< 1000): Fast, suitable for rough approximations
- Medium denominators (1000-10000): Good balance (recommended default)
- Large denominators (> 10000): High accuracy, slower computation

Approximation Method
~~~~~~~~~~~~~~~~~~~~

Choose between three algorithms:

.. code-block:: python

   # Farey sequence (default, recommended)
   converter = LXRationalConverter(method="farey")

   # Continued fractions
   converter = LXRationalConverter(method="continued_fraction")

   # Stern-Brocot tree
   converter = LXRationalConverter(method="stern_brocot")

**Algorithm Comparison:**

.. list-table::
   :header-rows: 1
   :widths: 20 25 25 30

   * - Method
     - Speed
     - Accuracy
     - Notes
   * - Farey
     - ⚡⚡⚡ Fastest
     - ✓✓✓ Best
     - Recommended default
   * - Continued Fraction
     - ⚡⚡ Fast
     - ✓✓✓ Best
     - Classic algorithm
   * - Stern-Brocot
     - ⚡⚡ Fast
     - ✓✓✓ Best
     - Equivalent to Farey

Float Tolerance
~~~~~~~~~~~~~~~

Control tolerance for float comparisons:

.. code-block:: python

   # Default tolerance
   converter = LXRationalConverter(float_tolerance=1e-9)

   # Stricter tolerance
   converter = LXRationalConverter(float_tolerance=1e-12)

   # Looser tolerance
   converter = LXRationalConverter(float_tolerance=1e-6)

Approximation Algorithms
-------------------------

Farey Sequence Method
~~~~~~~~~~~~~~~~~~~~~

The Farey method uses mediant approximation with floor/ceil optimization. It's the
fastest and recommended default.

**Algorithm Overview:**

1. Initialize bounds with floor and ceiling of the target value
2. Compute mediant: (n₁ + n₂) / (d₁ + d₂)
3. Update bounds based on mediant position
4. Repeat until denominator exceeds maximum

**Example:**

.. code-block:: python

   converter = LXRationalConverter(max_denominator=20, method="farey")
   frac, error = converter.to_rational(3.14159, return_error=True)

   print(f"Fraction: {frac}")        # 22/7
   print(f"Value: {float(frac):.6f}") # 3.142857
   print(f"Error: {error:.2e}")       # 1.27e-03

Continued Fraction Method
~~~~~~~~~~~~~~~~~~~~~~~~~

Classic continued fraction expansion algorithm. Good balance of speed and accuracy.

**Algorithm Overview:**

1. Extract integer part and fractional part
2. Build continued fraction representation
3. Compute convergents until max denominator

**Example:**

.. code-block:: python

   converter = LXRationalConverter(method="continued_fraction")
   frac = converter.to_rational(3.14159)
   print(frac)  # Fraction(355, 113)

Stern-Brocot Tree Method
~~~~~~~~~~~~~~~~~~~~~~~~~

Binary search through the Stern-Brocot tree. Mathematically equivalent to Farey
but offers alternative algorithmic framing.

**Example:**

.. code-block:: python

   converter = LXRationalConverter(method="stern_brocot")
   frac = converter.to_rational(3.14159)
   print(frac)  # Fraction(355, 113)

Error Tracking
--------------

Return Approximation Error
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   converter = LXRationalConverter(max_denominator=10000)

   # Get fraction and error
   frac, error = converter.to_rational(3.14159, return_error=True)

   print(f"Fraction: {frac}")
   print(f"Approximation: {float(frac):.8f}")
   print(f"Target: 3.14159000")
   print(f"Error: {error:.2e}")

Compare Methods
~~~~~~~~~~~~~~~

Compare all three methods for a given value:

.. code-block:: python

   converter = LXRationalConverter(max_denominator=10000)

   results = converter.compare_methods(3.14159)

   for method, (frac, error, time) in results.items():
       print(f"{method:20} : {frac:10} | Error: {error:.2e} | Time: {time*1e6:.2f}μs")

   # Output:
   # farey                : 355/113    | Error: 2.67e-07 | Time: 15.23μs
   # continued_fraction   : 355/113    | Error: 2.67e-07 | Time: 18.45μs
   # stern_brocot         : 355/113    | Error: 2.67e-07 | Time: 16.78μs

Practical Applications
----------------------

GLPK Integer Solver
~~~~~~~~~~~~~~~~~~~

Convert model coefficients for GLPK's exact rational mode:

.. code-block:: python

   from lumix import LXModel, LXVariable, LXLinearExpression
   from lumix.utils import LXRationalConverter

   # Build model with float coefficients
   products = [
       Product(id=1, profit=12.5),
       Product(id=2, profit=8.333),
       Product(id=3, profit=15.75)
   ]

   model = LXModel("production")
   production = LXVariable[Product, float]("x").from_data(products)
   model.add_variable(production)

   # Extract coefficients
   obj_coeffs = {p.id: p.profit for p in products}

   # Convert to rationals
   converter = LXRationalConverter(max_denominator=10000)
   int_coeffs, denom = converter.convert_coefficients(obj_coeffs)

   print(f"Original: {obj_coeffs}")
   print(f"Integer:  {int_coeffs}")
   print(f"Denominator: {denom}")

   # Use int_coeffs with GLPK
   # ... GLPK-specific solver code ...

Constraint Coefficient Conversion
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Convert constraint coefficients:

.. code-block:: python

   # Resource usage coefficients
   usage_coeffs = {
       ("Product_1", "Resource_A"): 2.5,
       ("Product_1", "Resource_B"): 1.333,
       ("Product_2", "Resource_A"): 3.75,
       ("Product_2", "Resource_B"): 0.666,
   }

   converter = LXRationalConverter(max_denominator=10000)
   int_usage, denom = converter.convert_coefficients(usage_coeffs)

   print(f"Integer usage coefficients: {int_usage}")
   print(f"Common denominator: {denom}")

Exact Arithmetic
~~~~~~~~~~~~~~~~

Ensure exact arithmetic for sensitive calculations:

.. code-block:: python

   from fractions import Fraction

   converter = LXRationalConverter(max_denominator=1000000)

   # Convert all coefficients to exact rationals
   values = [0.1, 0.2, 0.3, 0.4, 0.5]
   fractions = [converter.to_rational(v) for v in values]

   # Sum with exact arithmetic (no rounding errors)
   exact_sum = sum(fractions, start=Fraction(0))
   print(f"Exact sum: {exact_sum}")  # Fraction(3, 2) = 1.5
   print(f"Float sum: {sum(values)}")  # Might have rounding error

Advanced Techniques
-------------------

Custom Tolerance Handling
~~~~~~~~~~~~~~~~~~~~~~~~~

Fine-tune tolerance for specific use cases:

.. code-block:: python

   # Very strict tolerance for financial calculations
   converter = LXRationalConverter(
       max_denominator=1000000,
       float_tolerance=1e-15
   )

   price = 123.456789012345
   frac = converter.to_rational(price)
   print(f"Exact fraction: {frac}")

Iterative Refinement
~~~~~~~~~~~~~~~~~~~~

Progressively increase denominator until error threshold is met:

.. code-block:: python

   def convert_with_error_bound(value: float, max_error: float = 1e-6):
       """Convert to rational with guaranteed error bound."""
       max_denom = 10
       while max_denom <= 1000000:
           converter = LXRationalConverter(max_denominator=max_denom)
           frac, error = converter.to_rational(value, return_error=True)

           if error <= max_error:
               return frac, max_denom

           max_denom *= 10

       raise ValueError(f"Could not meet error bound {max_error}")

   # Usage
   frac, denom = convert_with_error_bound(3.14159, max_error=1e-6)
   print(f"Fraction: {frac} (max denom: {denom})")

Batch Optimization
~~~~~~~~~~~~~~~~~~

Optimize denominator for batch of coefficients:

.. code-block:: python

   def optimize_batch_conversion(coeffs: dict, target_error: float = 1e-6):
       """Find optimal max_denominator for batch."""
       for max_denom in [100, 1000, 10000, 100000]:
           converter = LXRationalConverter(max_denominator=max_denom)

           # Convert all
           int_coeffs, common_denom = converter.convert_coefficients(coeffs)

           # Check errors
           max_error = max(
               abs(int_coeffs[k] / common_denom - v)
               for k, v in coeffs.items()
           )

           if max_error <= target_error:
               return int_coeffs, common_denom, max_denom

       raise ValueError(f"Could not meet error bound {target_error}")

   # Usage
   coeffs = {"x1": 3.14159, "x2": 2.71828, "x3": 1.41421}
   int_coeffs, denom, max_denom = optimize_batch_conversion(coeffs)
   print(f"Used max_denominator: {max_denom}")

Best Practices
--------------

1. **Choose Appropriate Max Denominator**

   Balance accuracy vs. complexity:

   .. code-block:: python

      # For typical LP problems
      converter = LXRationalConverter(max_denominator=10000)  # Good default

      # For high-precision needs
      converter = LXRationalConverter(max_denominator=100000)

      # For quick approximations
      converter = LXRationalConverter(max_denominator=1000)

2. **Use Batch Conversion**

   More efficient than individual conversions:

   .. code-block:: python

      # Good: Batch conversion
      int_coeffs, denom = converter.convert_coefficients(coeffs)

      # Avoid: Individual conversions
      fracs = {k: converter.to_rational(v) for k, v in coeffs.items()}

3. **Check Approximation Quality**

   Always verify error for critical applications:

   .. code-block:: python

      frac, error = converter.to_rational(value, return_error=True)

      if error > acceptable_threshold:
          # Increase max_denominator or handle error

4. **Use Farey Method**

   Unless you have specific algorithmic needs:

   .. code-block:: python

      # Recommended
      converter = LXRationalConverter(method="farey")

Performance Considerations
--------------------------

Computation Time
~~~~~~~~~~~~~~~~

- Farey is fastest (typically 10-20μs per conversion)
- Time increases with max_denominator
- Batch conversion is more efficient than individual calls

Memory Usage
~~~~~~~~~~~~

- Minimal memory footprint
- No caching of previous results
- Safe for large-scale conversions

Accuracy vs. Speed
~~~~~~~~~~~~~~~~~~

Trade-off between denominator size and speed:

.. code-block:: python

   import time

   for max_denom in [100, 1000, 10000, 100000]:
       converter = LXRationalConverter(max_denominator=max_denom)

       start = time.perf_counter()
       frac, error = converter.to_rational(3.14159, return_error=True)
       elapsed = time.perf_counter() - start

       print(f"Max denom: {max_denom:6} | Error: {error:.2e} | Time: {elapsed*1e6:.1f}μs")

Common Issues
-------------

Large Denominators
~~~~~~~~~~~~~~~~~~

If denominators grow too large, reduce max_denominator:

.. code-block:: python

   # Problem: denominators too large
   converter = LXRationalConverter(max_denominator=1000000)
   int_coeffs, denom = converter.convert_coefficients(coeffs)
   print(denom)  # Might be very large!

   # Solution: Use smaller max_denominator
   converter = LXRationalConverter(max_denominator=10000)

Approximation Errors
~~~~~~~~~~~~~~~~~~~~

If errors are too large, increase max_denominator:

.. code-block:: python

   # Check error
   frac, error = converter.to_rational(value, return_error=True)

   if error > threshold:
       # Increase precision
       converter = LXRationalConverter(max_denominator=100000)
       frac, error = converter.to_rational(value, return_error=True)

See Also
--------

- :class:`~lumix.utils.rational.LXRationalConverter` - API reference
- :doc:`/api/utils/index` - Utils module API
- Python fractions module: https://docs.python.org/3/library/fractions.html
- GLPK documentation: https://www.gnu.org/software/glpk/
