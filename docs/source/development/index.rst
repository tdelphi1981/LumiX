Development Guide
=================

This guide is for contributors and advanced users who want to understand LumiX's architecture
and extend its functionality.

.. toctree::
   :maxdepth: 2
   :caption: Development Topics

   core-architecture
   extending-core
   solvers-architecture
   extending-solvers
   indexing-architecture
   extending-indexing
   nonlinear-architecture
   extending-nonlinear
   linearization-architecture
   extending-linearization
   utils-architecture
   extending-utils
   solution-architecture
   extending-solution
   design-decisions

Overview
--------

LumiX is built with several key principles:

1. **Type Safety**: Extensive use of Python's type system
2. **Data-Driven**: Models built from data, not loops
3. **Solver Agnostic**: Unified interface to multiple solvers
4. **Fluent API**: Method chaining for readability
5. **Automatic Expansion**: Variable/constraint families expand during solving

Target Audience
---------------

This guide is for:

- Contributors to LumiX
- Advanced users building extensions
- Researchers customizing the library
- Anyone curious about the internals

Getting Started
---------------

Clone and Install
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   git clone https://github.com/lumix/lumix.git
   cd lumix
   pip install -e .[dev]

Run Tests
~~~~~~~~~

.. code-block:: bash

   pytest

Type Check
~~~~~~~~~~

.. code-block:: bash

   mypy src/lumix

Code Style
~~~~~~~~~~

.. code-block:: bash

   black src/lumix
   ruff check src/lumix

Module Overview
---------------

.. mermaid::

   graph TD
       A[core] --> B[solvers]
       A --> C[analysis]
       A --> D[linearization]
       A --> E[goal_programming]
       F[indexing] --> A
       G[nonlinear] --> D
       H[solution] --> B
       I[utils] --> A

       style A fill:#e1f5ff
       style B fill:#fff4e1
       style C fill:#ffe1e1
       style D fill:#e1ffe1
       style E fill:#f0e1ff

**Core Modules:**

- ``core``: Model building (variables, constraints, expressions, models) (documented)
- ``solvers``: Solver interfaces (OR-Tools, Gurobi, CPLEX, GLPK, CP-SAT) (documented)
- ``indexing``: Multi-dimensional indexing utilities (documented)
- ``nonlinear``: Non-linear term definitions (documented)
- ``linearization``: Automatic linearization engine (documented)
- ``utils``: Logging, ORM, rational conversion (documented)
- ``solution``: Solution handling and mapping (documented)
- ``analysis``: Sensitivity, scenario, what-if analysis
- ``goal_programming``: Multi-objective optimization

Core Module Documentation
-------------------------

Deep dive into the core module's architecture and extensibility:

- :doc:`core-architecture` - Core module design patterns and architecture
- :doc:`extending-core` - How to extend core components
- :doc:`design-decisions` - Design decisions and trade-offs

Solvers Module Documentation
-----------------------------

Understand solvers architecture and how to add new solver implementations:

- :doc:`solvers-architecture` - Solvers module design patterns and architecture
- :doc:`extending-solvers` - How to implement custom solvers

Indexing Module Documentation
------------------------------

Understand indexing architecture and customization:

- :doc:`indexing-architecture` - Indexing module design patterns and architecture
- :doc:`extending-indexing` - How to create custom dimensions and products

Nonlinear Module Documentation
-------------------------------

Learn about nonlinear term definitions and how to extend them:

- :doc:`nonlinear-architecture` - Nonlinear module design patterns and architecture
- :doc:`extending-nonlinear` - How to create custom nonlinear term types

Utils Module Documentation
---------------------------

Learn about utils module architecture and how to extend it:

- :doc:`utils-architecture` - Utils module design patterns and architecture
- :doc:`extending-utils` - How to extend and customize utils components

Linearization Module Documentation
-----------------------------------

Understand linearization architecture and customization:

- :doc:`linearization-architecture` - Linearization module design patterns and architecture
- :doc:`extending-linearization` - How to create custom linearization techniques

Solution Module Documentation
------------------------------

Learn about solution handling architecture and customization:

- :doc:`solution-architecture` - Solution module design patterns and architecture
- :doc:`extending-solution` - How to create custom solution classes and mappers

Next Steps
----------

**For Core Module Development:**

- :doc:`core-architecture` - Deep dive into core module design
- :doc:`extending-core` - How to extend core components
- :doc:`design-decisions` - Why things work the way they do

**For Solvers Module Development:**

- :doc:`solvers-architecture` - Solvers module architecture and patterns
- :doc:`extending-solvers` - How to implement custom solver interfaces

**For Indexing Module Development:**

- :doc:`indexing-architecture` - Indexing module architecture and patterns
- :doc:`extending-indexing` - Custom dimensions, products, and filters

**For Nonlinear Module Development:**

- :doc:`nonlinear-architecture` - Nonlinear module architecture and patterns
- :doc:`extending-nonlinear` - Custom nonlinear term types and linearization

**For Utils Module Development:**

- :doc:`utils-architecture` - Utils module architecture details
- :doc:`extending-utils` - Custom loggers, protocols, and converters

**For Linearization Module Development:**

- :doc:`linearization-architecture` - Linearization module architecture and patterns
- :doc:`extending-linearization` - Custom linearization techniques and formulations

**For Solution Module Development:**

- :doc:`solution-architecture` - Solution module architecture and patterns
- :doc:`extending-solution` - Custom solution classes, mappers, and validators
