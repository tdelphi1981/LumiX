Analysis Tools
==============

This guide covers LumiX's comprehensive analysis tools for post-optimization decision support and sensitivity analysis.

Introduction
------------

After solving an optimization model, LumiX provides powerful analysis tools to help you:

- **Understand** how changes in parameters affect the optimal solution
- **Compare** different scenarios side-by-side
- **Explore** what-if questions interactively
- **Identify** bottlenecks and improvement opportunities
- **Make** better-informed business decisions

Philosophy
----------

Traditional Approach
~~~~~~~~~~~~~~~~~~~~

Traditional optimization workflows require manual experimentation:

.. code-block:: python

   # Traditional approach - manual, tedious
   # Solve baseline
   solution1 = solver.solve(model)

   # Manually modify model
   model.constraints["capacity"].rhs = 1200
   solution2 = solver.solve(model)

   # Manually compare
   print(f"Difference: {solution2.objective - solution1.objective}")

LumiX Approach
~~~~~~~~~~~~~~

LumiX provides dedicated analysis tools for systematic exploration:

.. code-block:: python

   # LumiX approach - systematic, comprehensive
   from lumix.analysis import LXWhatIfAnalyzer

   analyzer = LXWhatIfAnalyzer(model, optimizer)
   result = analyzer.increase_constraint_rhs("capacity", by=200)

   print(f"Impact: ${result.delta_objective:,.2f} ({result.delta_percentage:.1f}%)")
   print(f"Bottlenecks: {analyzer.find_bottlenecks(top_n=5)}")

**Benefits:**

- ✓ Systematic exploration of alternatives
- ✓ Automatic comparison and reporting
- ✓ Bottleneck identification
- ✓ Shadow price analysis
- ✓ Multi-scenario comparison

Analysis Tools Overview
------------------------

LumiX provides three complementary analysis approaches:

.. mermaid::

   graph LR
       A[Optimization Model] --> B[Solve]
       B --> C[Solution]
       C --> D[Sensitivity Analysis]
       C --> E[Scenario Analysis]
       C --> F[What-If Analysis]

       D --> G[Shadow Prices]
       D --> H[Reduced Costs]
       D --> I[Binding Constraints]

       E --> J[Scenario Comparison]
       E --> K[Parameter Sweep]

       F --> L[Interactive Exploration]
       F --> M[Bottleneck Finding]

       style A fill:#e8f4f8
       style C fill:#e1f5ff
       style D fill:#fff4e1
       style E fill:#ffe1e1
       style F fill:#e1ffe1

1. Sensitivity Analysis
~~~~~~~~~~~~~~~~~~~~~~~~

Analyzes how changes in parameters affect the optimal solution using shadow prices and reduced costs.

**Use Cases:**

- Understand marginal value of resources
- Identify which constraints are limiting performance
- Determine opportunity costs of decisions
- Validate solution robustness

**Quick Example:**

.. code-block:: python

   from lumix.analysis import LXSensitivityAnalyzer

   analyzer = LXSensitivityAnalyzer(model, solution)

   # Get shadow prices for all constraints
   report = analyzer.generate_report()

   # Identify bottlenecks
   bottlenecks = analyzer.identify_bottlenecks()
   for name in bottlenecks:
       sensitivity = analyzer.analyze_constraint(name)
       print(f"{name}: shadow price = ${sensitivity.shadow_price:.2f}")

2. Scenario Analysis
~~~~~~~~~~~~~~~~~~~~~

Compares multiple what-if scenarios in a systematic, organized way.

**Use Cases:**

- Compare optimistic vs. pessimistic scenarios
- Evaluate strategic alternatives
- Conduct sensitivity analysis on multiple parameters
- Stress-test business assumptions

**Quick Example:**

.. code-block:: python

   from lumix.analysis import LXScenario, LXScenarioAnalyzer

   analyzer = LXScenarioAnalyzer(model, optimizer)

   # Define scenarios
   analyzer.add_scenario(
       LXScenario("high_capacity")
       .modify_constraint_rhs("capacity", multiply=1.5)
       .describe("50% capacity increase")
   )

   analyzer.add_scenario(
       LXScenario("low_cost")
       .modify_constraint_rhs("budget", multiply=0.8)
       .describe("20% budget reduction")
   )

   # Run and compare
   results = analyzer.run_all_scenarios()
   print(analyzer.compare_scenarios())

3. What-If Analysis
~~~~~~~~~~~~~~~~~~~

Provides interactive exploration of parameter changes with immediate feedback.

**Use Cases:**

- Quick exploration of changes
- Finding the most impactful parameters
- Answering stakeholder questions on-the-fly
- Discovering improvement opportunities

**Quick Example:**

.. code-block:: python

   from lumix.analysis import LXWhatIfAnalyzer

   analyzer = LXWhatIfAnalyzer(model, optimizer)

   # Try increasing capacity
   result = analyzer.increase_constraint_rhs("capacity", by=100)
   print(f"Increasing capacity by 100 would improve profit by ${result.delta_objective:,.2f}")

   # Find bottlenecks automatically
   bottlenecks = analyzer.find_bottlenecks(top_n=5)
   for name, improvement in bottlenecks:
       print(f"{name}: ${improvement:.2f} per unit")

Choosing the Right Tool
-----------------------

.. list-table::
   :header-rows: 1
   :widths: 20 25 25 30

   * - Tool
     - Best For
     - Speed
     - Use When
   * - **Sensitivity**
     - Understanding current solution
     - Instant (no re-solve)
     - You have a solution and want to understand it
   * - **Scenario**
     - Systematic comparison
     - Moderate (multiple solves)
     - You have predefined scenarios to compare
   * - **What-If**
     - Interactive exploration
     - Fast (single re-solve)
     - You want to quickly try changes

Workflow Integration
--------------------

Typical Analysis Workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. mermaid::

   sequenceDiagram
       participant User
       participant Model
       participant Optimizer
       participant Sensitivity
       participant WhatIf
       participant Scenario

       User->>Model: Build model
       User->>Optimizer: Solve model
       Optimizer-->>User: Solution

       User->>Sensitivity: Analyze solution
       Sensitivity-->>User: Shadow prices, bottlenecks

       User->>WhatIf: Explore top bottleneck
       WhatIf-->>User: Impact estimate

       User->>Scenario: Compare alternatives
       Scenario-->>User: Best scenario

**Step-by-Step:**

1. **Build and solve** your optimization model
2. **Run sensitivity analysis** to understand the current solution
3. **Use what-if analysis** to explore promising changes
4. **Create scenarios** for systematic comparison of alternatives
5. **Make informed decisions** based on analysis results

Component Details
-----------------

Dive deeper into each analysis tool:

.. toctree::
   :maxdepth: 2

   sensitivity
   scenario
   whatif

Next Steps
----------

- :doc:`sensitivity` - Understand shadow prices and reduced costs
- :doc:`scenario` - Compare multiple scenarios systematically
- :doc:`whatif` - Interactively explore parameter changes
- :doc:`/api/analysis/index` - Detailed API reference
- :doc:`/development/analysis-architecture` - Architecture and extension guide
