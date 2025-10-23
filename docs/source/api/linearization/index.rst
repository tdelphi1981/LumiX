Linearization Module API
========================

The linearization module provides automatic conversion of nonlinear optimization terms
into linear or mixed-integer linear programming (MILP) formulations.

Overview
--------

The linearization module implements a comprehensive framework for handling nonlinear
terms in optimization models:

.. mermaid::

   graph TD
       A[LXLinearizer] --> B[LXBilinearLinearizer]
       A --> C[LXPiecewiseLinearizer]
       D[LXLinearizerConfig] --> A
       E[LXLinearizationMethod] --> D
       F[LXNonLinearFunctions] --> C

       style A fill:#e1f5ff
       style B fill:#fff4e1
       style C fill:#ffe1e1
       style D fill:#e1ffe1
       style E fill:#f0e1ff
       style F fill:#f0e1ff

Components
----------

Main Engine
~~~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.linearization.engine.LXLinearizer

The :class:`~lumix.linearization.engine.LXLinearizer` class is the main engine that
orchestrates the linearization process by detecting nonlinear terms, checking solver
capabilities, and applying appropriate techniques.

Configuration
~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.linearization.config.LXLinearizerConfig
   lumix.linearization.config.LXLinearizationMethod

Configuration classes for controlling linearization behavior, method selection,
and accuracy requirements.

Pre-built Functions
~~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.linearization.functions.LXNonLinearFunctions

Pre-built piecewise-linear approximations for common nonlinear functions
(exp, log, sqrt, power, sigmoid, trigonometric functions).

Linearization Techniques
~~~~~~~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.linearization.techniques.LXBilinearLinearizer
   lumix.linearization.techniques.LXPiecewiseLinearizer

Specialized linearization techniques for bilinear products and piecewise-linear
function approximations.

Detailed API Reference
----------------------

Main Engine
~~~~~~~~~~~

.. automodule:: lumix.linearization.engine
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

Configuration
~~~~~~~~~~~~~

.. automodule:: lumix.linearization.config
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

Pre-built Functions
~~~~~~~~~~~~~~~~~~~

.. automodule:: lumix.linearization.functions
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

Bilinear Linearization
~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: lumix.linearization.techniques.bilinear
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

Piecewise-Linear Approximation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: lumix.linearization.techniques.piecewise
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

Usage Examples
--------------

Basic Linearization
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.linearization import LXLinearizer, LXLinearizerConfig
   from lumix.solvers.capabilities import LXSolverCapability

   # Configure linearization
   config = LXLinearizerConfig(
       default_method=LXLinearizationMethod.MCCORMICK,
       big_m_value=1e5,
       pwl_num_segments=30,
       adaptive_breakpoints=True
   )

   # Create linearizer
   solver_capability = LXSolverCapability.for_solver("glpk")
   linearizer = LXLinearizer(model, solver_capability, config)

   # Linearize if needed
   if linearizer.needs_linearization():
       linearized_model = linearizer.linearize_model()

       # Get statistics
       stats = linearizer.get_statistics()
       print(f"Added {stats['auxiliary_variables']} auxiliary variables")
       print(f"Added {stats['auxiliary_constraints']} auxiliary constraints")

Using Pre-built Functions
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.linearization import LXNonLinearFunctions
   from lumix.linearization.techniques import LXPiecewiseLinearizer

   # Create linearizer
   config = LXLinearizerConfig(pwl_num_segments=40)
   linearizer = LXPiecewiseLinearizer(config)

   # Exponential growth
   exp_output = LXNonLinearFunctions.exp(time_var, linearizer, segments=50)

   # Logarithmic decay
   log_output = LXNonLinearFunctions.log(quantity_var, linearizer, base=10)

   # Sigmoid function for probabilities
   probability = LXNonLinearFunctions.sigmoid(score_var, linearizer)

   # Custom function
   def custom_cost(x):
       return x**3 - 2*x**2 + x + 5

   cost_output = LXNonLinearFunctions.custom(
       production_var,
       custom_cost,
       linearizer,
       segments=30,
       adaptive=True
   )

Direct Technique Usage
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.linearization.techniques import LXBilinearLinearizer
   from lumix.nonlinear.terms import LXBilinearTerm

   # Create bilinear linearizer
   config = LXLinearizerConfig(big_m_value=1e6)
   linearizer = LXBilinearLinearizer(config)

   # Linearize bilinear term
   bilinear_term = LXBilinearTerm(
       var1=binary_var,
       var2=continuous_var,
       coefficient=1.0
   )

   aux_var = linearizer.linearize_bilinear(bilinear_term)

   # Add auxiliary elements to model
   for var in linearizer.auxiliary_vars:
       model.add_variable(var)
   for constraint in linearizer.auxiliary_constraints:
       model.add_constraint(constraint)

See Also
--------

- :doc:`/user-guide/linearization/index` - Complete user guide
- :doc:`/development/linearization-architecture` - Architecture details
- :doc:`/development/extending-linearization` - Extending linearization
