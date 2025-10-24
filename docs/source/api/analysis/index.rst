Analysis Module API
===================

The analysis module provides comprehensive tools for post-optimization analysis and decision support.

Overview
--------

The analysis module implements three complementary analysis approaches:

.. mermaid::

   graph TD
       A[LXSolution] --> B[Sensitivity Analysis]
       A --> C[Scenario Analysis]
       A --> D[What-If Analysis]
       E[LXModel] --> C
       E --> D
       F[LXOptimizer] --> C
       F --> D

       style A fill:#e1f5ff
       style B fill:#fff4e1
       style C fill:#ffe1e1
       style D fill:#e1ffe1
       style E fill:#f0e1ff
       style F fill:#e8f4f8

Components
----------

Scenario Analysis
~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.analysis.scenario.LXScenario
   lumix.analysis.scenario.LXScenarioAnalyzer
   lumix.analysis.scenario.LXScenarioModification

The :class:`~lumix.analysis.scenario.LXScenarioAnalyzer` class enables systematic comparison of
multiple what-if scenarios. Define scenarios with :class:`~lumix.analysis.scenario.LXScenario`,
run them in parallel, and compare results side-by-side.

Sensitivity Analysis
~~~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.analysis.sensitivity.LXSensitivityAnalyzer
   lumix.analysis.sensitivity.LXVariableSensitivity
   lumix.analysis.sensitivity.LXConstraintSensitivity

The :class:`~lumix.analysis.sensitivity.LXSensitivityAnalyzer` class analyzes shadow prices,
reduced costs, and binding constraints to understand how parameter changes affect the optimal solution.

What-If Analysis
~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/
   :nosignatures:

   lumix.analysis.whatif.LXWhatIfAnalyzer
   lumix.analysis.whatif.LXWhatIfResult
   lumix.analysis.whatif.LXWhatIfChange

The :class:`~lumix.analysis.whatif.LXWhatIfAnalyzer` class provides interactive exploration of
parameter changes with immediate feedback on objective value impact.

Detailed API Reference
----------------------

Scenario Analysis
~~~~~~~~~~~~~~~~~

.. automodule:: lumix.analysis.scenario
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

Sensitivity Analysis
~~~~~~~~~~~~~~~~~~~~

.. automodule:: lumix.analysis.sensitivity
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:

What-If Analysis
~~~~~~~~~~~~~~~~

.. automodule:: lumix.analysis.whatif
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :noindex:
