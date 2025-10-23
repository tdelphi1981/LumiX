"""Nonlinear modeling components for LumiX.

This module provides term definitions for nonlinear optimization constructs that can be
automatically linearized and integrated into linear or mixed-integer programming models.

Overview
--------
The nonlinear module defines five key term types that represent common nonlinear operations
in optimization models:

1. **LXAbsoluteTerm**: Absolute value operations |x|
2. **LXMinMaxTerm**: Minimum and maximum operations over multiple variables
3. **LXBilinearTerm**: Products of two variables x * y
4. **LXIndicatorTerm**: Conditional constraints (if-then logic)
5. **LXPiecewiseLinearTerm**: Approximations of arbitrary nonlinear functions

Design Philosophy
-----------------
Unlike some optimization frameworks that require manual linearization, LumiX allows you to
express nonlinear terms naturally. The linearization engine automatically converts these
terms into equivalent linear formulations suitable for MIP solvers.

Key benefits:

- **Declarative**: Express what you want, not how to linearize it
- **Type-safe**: Full type checking and IDE support
- **Automatic**: Linearization happens transparently during model building
- **Flexible**: Multiple linearization methods available (Big-M, McCormick, SOS2, etc.)

Usage Pattern
-------------
All nonlinear terms are dataclasses that capture the structure of the nonlinear operation.
They are designed to be used with the linearization module, which handles the conversion
to linear constraints.

Example:
    Basic usage with automatic linearization::

        from lumix.core import LXModel, LXVariable
        from lumix.nonlinear import LXBilinearTerm, LXAbsoluteTerm
        from lumix.linearization import LXLinearizer

        # Define variables
        is_open = LXVariable[Facility, int]("is_open").binary()
        flow = LXVariable[Facility, float]("flow").continuous()

        # Define nonlinear terms
        actual_flow = LXBilinearTerm(var1=is_open, var2=flow)
        abs_deviation = LXAbsoluteTerm(var=flow, coefficient=1.0)

        # Build model (linearization happens automatically)
        model = LXModel("facility_planning")
        # ... add constraints using nonlinear terms ...

Integration with Linearization Module
--------------------------------------
These term definitions work seamlessly with the ``lumix.linearization`` module, which
provides the automatic linearization engine. See :mod:`lumix.linearization` for details
on how to configure and use the linearization process.

Module Contents
---------------
.. autosummary::
   :nosignatures:

   LXAbsoluteTerm
   LXMinMaxTerm
   LXBilinearTerm
   LXIndicatorTerm
   LXPiecewiseLinearTerm

See Also
--------
lumix.linearization : Automatic linearization engine
lumix.core : Core modeling components (variables, constraints, expressions)

Notes
-----
The nonlinear terms in this module are **declarations**, not implementations. They describe
the structure of nonlinear operations, which are then converted to linear constraints by
the linearization engine based on:

- Variable types (binary, integer, continuous)
- Variable bounds
- Solver capabilities
- User-specified configuration

This separation of concerns allows the same nonlinear term definition to be linearized
in different ways depending on the context.
"""

from .terms import (
    LXAbsoluteTerm,
    LXBilinearTerm,
    LXIndicatorTerm,
    LXMinMaxTerm,
    LXPiecewiseLinearTerm,
)

__all__ = [
    "LXAbsoluteTerm",
    "LXBilinearTerm",
    "LXIndicatorTerm",
    "LXMinMaxTerm",
    "LXPiecewiseLinearTerm",
]
