Examples
========

.. note::
   Example documentation is coming soon. For now, please refer to the ``examples/`` directory in the repository.

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
   git clone https://github.com/lumix/lumix.git
   cd lumix

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

Coming Soon
-----------

We're working on adding:

- Detailed walkthrough for each example
- Jupyter notebook versions
- Interactive visualizations
- Problem descriptions and mathematical formulations
- Solution interpretation guides
- Performance comparisons across solvers

In the Meantime
---------------

- Browse the example source code in the repository
- Each example has comprehensive comments
- Examples demonstrate best practices
- Start with basic examples and progress to advanced ones

Contributing Examples
---------------------

Have an interesting use case? We welcome example contributions!

- Open an issue to discuss your example idea
- Follow the existing example structure
- Include sample data and clear comments
- Submit a pull request

Next Steps
----------

1. Browse the examples directory
2. Run examples relevant to your use case
3. Modify examples to match your problem
4. Build your own models based on the patterns you learned
