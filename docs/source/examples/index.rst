Examples
========

The LumiX examples demonstrate key features and best practices through
practical, real-world optimization problems. Each example is fully documented
with source code, mathematical formulations, and learning objectives.

Quick Start Guide
-----------------

**New to LumiX?** Start with these examples in order:

1. **Basic LP** (:doc:`basic_lp`) - The simplest introduction
2. **Production Planning** (:doc:`production_planning`) - Single-model indexing
3. **Driver Scheduling** (:doc:`driver_scheduling`) - Multi-model indexing (KEY FEATURE)

Examples by Topic
-----------------

.. toctree::
   :maxdepth: 1
   :caption: Fundamentals

   basic_lp
   production_planning
   driver_scheduling
   facility_location

.. toctree::
   :maxdepth: 1
   :caption: Advanced Techniques

   cpsat_assignment
   mccormick_bilinear
   piecewise_functions

.. toctree::
   :maxdepth: 1
   :caption: Analysis Tools

   scenario_analysis
   sensitivity_analysis
   whatif_analysis
   goal_programming

Available Examples
------------------

The LumiX repository includes 11 comprehensive examples demonstrating various features:

Basic Examples
~~~~~~~~~~~~~~

1. **Production Planning** (``01_production_planning/``)

   - Single-model indexing
   - Data-driven modeling
   - Resource capacity constraints
   - Profit maximization

2. **Driver Scheduling** (``02_driver_scheduling/``)

   - Multi-dimensional indexing
   - Complex scheduling constraints
   - Assignment problems

3. **Facility Location** (``03_facility_location/``)

   - Binary decision variables
   - Fixed costs vs. variable costs
   - Facility location optimization

4. **Basic Linear Programming** (``04_basic_lp/``)

   - Simple LP formulation
   - Getting started example
   - Basic constraints

Assignment Problems
~~~~~~~~~~~~~~~~~~~

5. **CP-SAT Assignment** (``05_cpsat_assignment/``)

   - Using CP-SAT solver
   - Integer programming
   - Assignment constraints

Advanced Techniques
~~~~~~~~~~~~~~~~~~~

6. **McCormick Bilinear Linearization** (``06_mccormick_bilinear/``)

   - Bilinear term linearization
   - McCormick envelopes
   - Non-linear optimization

7. **Piecewise Linear Functions** (``07_piecewise_functions/``)

   - Piecewise-linear approximations
   - Non-linear function modeling
   - SOS2 constraints

Analysis Examples
~~~~~~~~~~~~~~~~~

8. **Scenario Analysis** (``08_scenario_analysis/``)

   - Comparing multiple scenarios
   - Scenario management
   - Side-by-side comparison

9. **Sensitivity Analysis** (``09_sensitivity_analysis/``)

   - Parameter sensitivity
   - Shadow prices
   - Reduced costs
   - Range analysis

10. **What-If Analysis** (``10_whatif_analysis/``)

    - Quick what-if scenarios
    - Impact analysis
    - Decision support

Goal Programming
~~~~~~~~~~~~~~~~

11. **Goal Programming** (``11_goal_programming/``)

    - Multi-objective optimization
    - Weighted goals
    - Sequential (lexicographic) goals
    - Goal priorities

Running Examples
----------------

Each example is self-contained and can be run directly:

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/tdelphi1981/LumiX.git
   cd LumiX

   # Install LumiX with a solver
   pip install -e .[ortools]

   # Run an example
   python examples/01_production_planning/production_planning.py

Example Structure
-----------------

Each example directory typically contains:

- **Main script**: The optimization model and solution
- **Sample data**: Data classes and sample datasets
- **README** (coming soon): Detailed explanation

What You'll Learn
-----------------

From Basic Examples
~~~~~~~~~~~~~~~~~~~

- How to define variables with type safety
- Building expressions and constraints
- Creating and solving models
- Accessing solution values
- Working with different data structures

From Advanced Examples
~~~~~~~~~~~~~~~~~~~~~~

- Multi-dimensional indexing strategies
- Automatic linearization techniques
- Solver-specific features
- Performance optimization
- Complex constraint modeling

From Analysis Examples
~~~~~~~~~~~~~~~~~~~~~~~

- Sensitivity analysis workflows
- Scenario comparison techniques
- What-if analysis for decision making
- Interpreting optimization results

Example Categories
------------------

By Difficulty
~~~~~~~~~~~~~

**Beginner**

- Basic LP (``04_basic_lp/``)
- Production Planning (``01_production_planning/``)

**Intermediate**

- Driver Scheduling (``02_driver_scheduling/``)
- Facility Location (``03_facility_location/``)
- CP-SAT Assignment (``05_cpsat_assignment/``)

**Advanced**

- McCormick Bilinear (``06_mccormick_bilinear/``)
- Piecewise Functions (``07_piecewise_functions/``)
- Goal Programming (``11_goal_programming/``)

By Feature
~~~~~~~~~~

**Indexing**

- Single: Production Planning
- Multi-dimensional: Driver Scheduling

**Variable Types**

- Continuous: Production Planning, Basic LP
- Integer: CP-SAT Assignment
- Binary: Facility Location

**Linearization**

- Bilinear: McCormick example
- Piecewise: Piecewise functions example

**Analysis**

- Sensitivity: Sensitivity Analysis example
- Scenario: Scenario Analysis example
- What-If: What-If Analysis example

**Multi-Objective**

- Goal Programming: Goal Programming examples

Documentation Features
----------------------

Each example now includes:

✓ **Detailed walkthrough** - Step-by-step code explanation
✓ **Problem descriptions** - Real-world business context
✓ **Mathematical formulations** - LaTeX equations and constraints
✓ **Solution interpretation guides** - How to read and use results
✓ **Comprehensive README files** - Quick reference in each example directory
✓ **API cross-references** - Links to relevant LumiX classes and methods

**Coming Soon**:

- Jupyter notebook versions
- Interactive visualizations
- Performance comparisons across solvers

Contributing Examples
---------------------

Have an interesting use case? We welcome example contributions!

- Open an issue to discuss your example idea
- Follow the existing example structure
- Include sample data and clear comments
- Submit a pull request

Getting Started
---------------

**Step 1: Choose Your Starting Point**

- **Complete beginner?** → Start with :doc:`basic_lp`
- **Know linear programming?** → Jump to :doc:`production_planning`
- **Ready for advanced features?** → Explore :doc:`driver_scheduling`

**Step 2: Run the Examples**

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/tdelphi1981/LumiX.git
   cd LumiX

   # Install LumiX with a solver
   pip install -e .[ortools]

   # Run an example
   python examples/04_basic_lp/basic_lp.py

**Step 3: Explore and Modify**

- Read the documentation page for detailed explanations
- Review the source code and README files
- Try the suggested modifications
- Adapt patterns to your own problems

Next Steps
----------

After completing the examples:

1. Review the :doc:`../user-guide/index` for detailed feature documentation
2. Explore the :doc:`../api/index` for complete API reference
3. Join the community and share your use cases
4. Contribute your own examples via pull request
