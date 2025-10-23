Nonlinear Module API
====================

The nonlinear module provides term definitions for nonlinear optimization constructs
that can be automatically linearized.

Overview
--------

The nonlinear module defines five key term types for expressing nonlinear relationships:

.. mermaid::

   graph LR
       A[Nonlinear Terms] --> B[LXAbsoluteTerm]
       A --> C[LXMinMaxTerm]
       A --> D[LXBilinearTerm]
       A --> E[LXIndicatorTerm]
       A --> F[LXPiecewiseLinearTerm]

       style A fill:#e1f5ff
       style B fill:#fff4e1
       style C fill:#ffe1e1
       style D fill:#e1ffe1
       style E fill:#f0e1ff
       style F fill:#ffe8e1

All terms are immutable dataclasses that serve as metadata carriers for the
linearization engine.

Components
----------

Absolute Value Terms
~~~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.nonlinear.terms.LXAbsoluteTerm

The :class:`~lumix.nonlinear.terms.LXAbsoluteTerm` class represents absolute value operations |x|.

Min/Max Terms
~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.nonlinear.terms.LXMinMaxTerm

The :class:`~lumix.nonlinear.terms.LXMinMaxTerm` class represents minimum and maximum operations
over multiple variables.

Bilinear Terms
~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.nonlinear.terms.LXBilinearTerm

The :class:`~lumix.nonlinear.terms.LXBilinearTerm` class represents products of two variables (x * y),
automatically linearized based on variable types.

Indicator Terms
~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.nonlinear.terms.LXIndicatorTerm

The :class:`~lumix.nonlinear.terms.LXIndicatorTerm` class represents conditional constraints
(if-then logic).

Piecewise-Linear Terms
~~~~~~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.nonlinear.terms.LXPiecewiseLinearTerm

The :class:`~lumix.nonlinear.terms.LXPiecewiseLinearTerm` class represents piecewise-linear
approximations of arbitrary nonlinear functions.

Detailed API Reference
----------------------

Absolute Value
~~~~~~~~~~~~~~

.. automodule:: lumix.nonlinear.terms
   :members: LXAbsoluteTerm
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

Min/Max
~~~~~~~

.. automodule:: lumix.nonlinear.terms
   :members: LXMinMaxTerm
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

Bilinear Products
~~~~~~~~~~~~~~~~~

.. automodule:: lumix.nonlinear.terms
   :members: LXBilinearTerm
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

Indicator Constraints
~~~~~~~~~~~~~~~~~~~~~

.. automodule:: lumix.nonlinear.terms
   :members: LXIndicatorTerm
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

Piecewise-Linear
~~~~~~~~~~~~~~~~

.. automodule:: lumix.nonlinear.terms
   :members: LXPiecewiseLinearTerm
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

Usage Examples
--------------

Basic Usage
~~~~~~~~~~~

.. code-block:: python

   from lumix.nonlinear import (
       LXAbsoluteTerm,
       LXMinMaxTerm,
       LXBilinearTerm,
       LXIndicatorTerm,
       LXPiecewiseLinearTerm
   )

   # Absolute value
   abs_term = LXAbsoluteTerm(var=x, coefficient=1.0)

   # Min/max
   min_cost = LXMinMaxTerm(
       vars=[cost_a, cost_b, cost_c],
       operation="min",
       coefficients=[1.0, 1.0, 1.0]
   )

   # Bilinear product
   revenue = LXBilinearTerm(var1=price, var2=quantity, coefficient=1.0)

   # Indicator constraint
   min_order = LXIndicatorTerm(
       binary_var=ordered,
       condition=True,
       linear_expr=quantity_expr,
       sense='>=',
       rhs=100.0
   )

   # Piecewise-linear
   exp_cost = LXPiecewiseLinearTerm(
       var=time,
       func=lambda t: math.exp(t),
       num_segments=30
   )

See Also
--------

**User Guides:**

- :doc:`/user-guide/nonlinear/index` - Comprehensive usage guide
- :doc:`/user-guide/linearization/index` - Linearization configuration

**Development:**

- :doc:`/development/nonlinear-architecture` - Module architecture
- :doc:`/development/extending-nonlinear` - Adding custom terms

**Related Modules:**

- :doc:`/api/core/index` - Core modeling components
- :doc:`/api/linearization/index` - Linearization engine

Quick Reference
---------------

Common Operations
~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Operation
     - Term Type
     - Key Parameters
   * - |x|
     - LXAbsoluteTerm
     - var, coefficient
   * - min(x₁, x₂, ..., xₙ)
     - LXMinMaxTerm
     - vars, operation="min"
   * - max(x₁, x₂, ..., xₙ)
     - LXMinMaxTerm
     - vars, operation="max"
   * - x * y
     - LXBilinearTerm
     - var1, var2, coefficient
   * - if b then expr ≤ rhs
     - LXIndicatorTerm
     - binary_var, condition, expr
   * - f(x)
     - LXPiecewiseLinearTerm
     - var, func, num_segments

Linearization Methods
~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Term Type
     - Linearization Method
   * - LXAbsoluteTerm
     - Auxiliary variable with z ≥ x and z ≥ -x
   * - LXMinMaxTerm
     - Auxiliary variable with bounding constraints
   * - LXBilinearTerm (Bin×Bin)
     - AND logic (3 constraints)
   * - LXBilinearTerm (Bin×Cont)
     - Big-M method (4 constraints)
   * - LXBilinearTerm (Cont×Cont)
     - McCormick envelopes (4 constraints)
   * - LXIndicatorTerm
     - Big-M method (1 constraint)
   * - LXPiecewiseLinearTerm
     - SOS2, Incremental, or Logarithmic formulation

Module Information
------------------

**Module Path:** ``lumix.nonlinear``

**Dependencies:**
  - ``lumix.core.variables`` - Variable definitions
  - ``lumix.core.expressions`` - Expression definitions

**Used By:**
  - ``lumix.linearization`` - Linearization engine

**Python Version:** 3.9+

**Type Annotations:** Fully type-annotated

Next Steps
----------

**Learn More:**

1. :doc:`/user-guide/nonlinear/index` - Start with the user guide
2. :doc:`/user-guide/nonlinear/absolute-value` - Absolute value operations
3. :doc:`/user-guide/nonlinear/bilinear` - Bilinear products
4. :doc:`/development/nonlinear-architecture` - Architecture details

**Related APIs:**

- :doc:`/api/core/index` - Core module API
- :doc:`/api/linearization/index` - Linearization module API
