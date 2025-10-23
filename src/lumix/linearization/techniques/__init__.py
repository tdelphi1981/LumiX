"""
Linearization techniques for various nonlinear terms.

This module provides specialized linearization techniques for different types
of nonlinear terms commonly found in optimization models.

Techniques:
    - :class:`~lumix.linearization.techniques.bilinear.LXBilinearLinearizer`:
      Linearizes bilinear products (x * y) using McCormick envelopes, Big-M method,
      or Binary AND logic depending on variable types.

    - :class:`~lumix.linearization.techniques.piecewise.LXPiecewiseLinearizer`:
      Approximates arbitrary nonlinear functions using piecewise-linear segments
      with SOS2, incremental, or logarithmic formulations.

Mathematical Background:
    **Bilinear Linearization:**

    - Binary × Binary: Uses AND logic with 3 constraints
    - Binary × Continuous: Big-M method with 4 constraints
    - Continuous × Continuous: McCormick envelopes with 4 constraints

    **Piecewise-Linear Approximation:**

    - SOS2: Uses Special Ordered Set type 2 (most efficient with solver support)
    - Incremental: Uses binary variables for segment selection
    - Logarithmic: Uses Gray code encoding for many segments

Example:
    Using bilinear linearizer directly::

        from lumix.linearization.techniques import LXBilinearLinearizer
        from lumix.linearization.config import LXLinearizerConfig

        config = LXLinearizerConfig()
        linearizer = LXBilinearLinearizer(config)

        # Linearize bilinear term
        aux_var = linearizer.linearize_bilinear(bilinear_term)

        # Access auxiliary variables and constraints
        for var in linearizer.auxiliary_vars:
            model.add_variable(var)
        for const in linearizer.auxiliary_constraints:
            model.add_constraint(const)

    Using piecewise linearizer::

        from lumix.linearization.techniques import LXPiecewiseLinearizer
        import math

        linearizer = LXPiecewiseLinearizer(config)

        # Approximate exponential function
        output_var = linearizer.approximate_function(
            func=lambda x: math.exp(x),
            var=input_var,
            num_segments=30,
            x_min=0,
            x_max=10,
            method="sos2",
            adaptive=True
        )

See Also:
    - :doc:`/user-guide/linearization/bilinear` - Bilinear linearization guide
    - :doc:`/user-guide/linearization/piecewise` - Piecewise approximation guide
    - :doc:`/development/extending-linearization` - Add custom techniques
"""

from .bilinear import LXBilinearLinearizer
from .piecewise import LXPiecewiseLinearizer

__all__ = ["LXBilinearLinearizer", "LXPiecewiseLinearizer"]
