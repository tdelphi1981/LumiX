Core Module API
===============

The core module provides the fundamental building blocks for creating optimization models in LumiX.

Overview
--------

The core module implements a type-safe, data-driven approach to optimization modeling through five main components:

.. mermaid::

   graph TD
       A[LXModel] --> B[LXVariable]
       A --> C[LXConstraint]
       A --> D[LXExpression]
       B --> D
       C --> D
       E[LXEnums] --> B
       E --> C
       E --> A

       style A fill:#e1f5ff
       style B fill:#fff4e1
       style C fill:#ffe1e1
       style D fill:#e1ffe1
       style E fill:#f0e1ff

Components
----------

Model Builder
~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.core.model.LXModel

The :class:`~lumix.core.model.LXModel` class is the central component for building optimization models.
It uses the Builder pattern with a fluent API.

Variables
~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.core.variables.LXVariable

The :class:`~lumix.core.variables.LXVariable` class represents variable families that automatically
expand to multiple solver variables based on data.

Constraints
~~~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.core.constraints.LXConstraint

The :class:`~lumix.core.constraints.LXConstraint` class represents constraint families that automatically
expand to multiple solver constraints based on data.

Expressions
~~~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.core.expressions.LXLinearExpression
   lumix.core.expressions.LXQuadraticExpression
   lumix.core.expressions.LXNonLinearExpression
   lumix.core.expressions.LXQuadraticTerm

Expression classes for building objective functions and constraint left-hand sides.

Enumerations
~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.core.enums.LXVarType
   lumix.core.enums.LXConstraintSense
   lumix.core.enums.LXObjectiveSense

Type-safe enumerations for variable types, constraint senses, and objective directions.

Detailed API Reference
----------------------

Model
~~~~~

.. automodule:: lumix.core.model
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

Variables
~~~~~~~~~

.. automodule:: lumix.core.variables
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

Constraints
~~~~~~~~~~~

.. automodule:: lumix.core.constraints
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

Expressions
~~~~~~~~~~~

.. automodule:: lumix.core.expressions
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

Enumerations
~~~~~~~~~~~~

.. automodule:: lumix.core.enums
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:
