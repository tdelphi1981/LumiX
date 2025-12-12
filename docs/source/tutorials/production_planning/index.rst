Manufacturing Production Planning Tutorial
==========================================

A comprehensive 7-step tutorial demonstrating how to build production planning solutions using LumiX, progressing from basic continuous variable optimization to advanced what-if analysis with database integration.

Overview
--------

This tutorial teaches you how to solve real-world manufacturing production planning problems through progressive complexity. You'll learn to model quantity optimization, resource constraints, multi-period planning, and perform advanced analysis.

**Problem Domain**: A furniture factory produces multiple products (chairs, tables, desks) using shared machines and raw materials. The factory must decide how many units of each product to manufacture to maximize profit while respecting resource limits and customer commitments.

Tutorial Progression
--------------------

.. list-table::
   :header-rows: 1
   :widths: 10 20 35 35

   * - Step
     - Focus
     - Key Concepts
     - Problem Scale
   * - **1**
     - Basic Optimization
     - Continuous variables, resource constraints, profit maximization
     - 3 products, 2 machines, 3 materials
   * - **2**
     - Database Integration
     - SQLAlchemy ORM, persistent storage, BOM structure
     - Same scale + database
   * - **3**
     - Goal Programming
     - Customer orders, priority tiers, multi-objective optimization
     - + 5 customers, 9 orders
   * - **4**
     - Large-Scale Multi-Period
     - Setup costs, inventory, batch constraints, 4-week planning
     - 9 products, 6 machines, 4 periods (~1,600 variables)
   * - **5**
     - Scenario Analysis
     - Comparing business scenarios, sensitivity to market conditions
     - Same scale + multiple scenarios
   * - **6**
     - Sensitivity Analysis
     - Shadow prices, marginal values, reduced costs, bottleneck identification
     - Same scale + dual analysis
   * - **7**
     - What-If Analysis
     - Interactive parameter exploration, investment ROI, risk assessment
     - Same scale + what-if scenarios

What You'll Learn
-----------------

Core Optimization
~~~~~~~~~~~~~~~~~

- **Continuous Variables**: Model production quantities (not just binary decisions)
- **Resource Constraints**: Machine hours, material availability, capacity limits
- **Profit Maximization**: Objective functions with costs and revenues
- **Variable Bounds**: Minimum/maximum production requirements

Database Integration
~~~~~~~~~~~~~~~~~~~~

- **SQLAlchemy ORM**: Type-safe database operations with declarative models
- **from_model() Method**: Load optimization data directly from database queries
- **Bill of Materials (BOM)**: Complex relationship structures for recipes
- **Solution Persistence**: Save optimization results back to database
- **Cached Helpers**: Performance optimization for repeated queries

Goal Programming
~~~~~~~~~~~~~~~~

- **Soft Constraints**: Convert customer orders to goals with priorities
- **Priority Tiers**: Gold/Silver/Bronze customer classification
- **Multi-Objective Optimization**: Balance profit maximization with service level
- **Deviation Tracking**: Monitor goal satisfaction and shortfalls
- **Weighted Goal Programming**: Combine priorities with importance weights

Multi-Period Planning
~~~~~~~~~~~~~~~~~~~~~

- **Time Horizon**: 4-week rolling planning window
- **Inventory Management**: Balance holding costs with production economies
- **Setup Costs**: Model changeover costs for batch production
- **Batch Constraints**: Minimum production quantities when scheduling
- **Large-Scale Problems**: Handle 1,600+ variables efficiently

Advanced Analysis
~~~~~~~~~~~~~~~~~

- **Scenario Analysis**: Compare optimistic, baseline, and pessimistic futures
- **Sensitivity Analysis**: Understand marginal value of resources
- **What-If Analysis**: Interactive exploration of parameter changes
- **Bottleneck Identification**: Find most valuable capacity expansions
- **Investment ROI**: Compare profitability of different investments
- **Risk Assessment**: Quantify downside scenarios

Tutorial Steps
--------------

.. toctree::
   :maxdepth: 1
   :titlesonly:

   step1_basic
   step2_database
   step3_goals
   step4_scaled
   step5_scenario
   step6_sensitivity
   step7_whatif

Step 1: Basic Production Planning
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:doc:`step1_basic`

Learn fundamental continuous variable optimization for production planning.

**Topics Covered:**

- Creating continuous variables: ``LXVariable[Product, float]``
- Resource consumption constraints (machines, materials)
- Profit maximization objectives
- Variable bounds (min/max demand)
- Basic model building and solving

**Files:** ``sample_data.py``, ``production.py``

**Time to Complete:** 30 minutes

Step 2: Database Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:doc:`step2_database`

Integrate SQLAlchemy ORM for persistent data storage and type-safe database operations.

**Topics Covered:**

- SQLAlchemy declarative models
- Loading LumiX models with ``from_model()``
- Bill of Materials (BOM) relationship structure
- Solution persistence to database
- Cached helper functions for performance

**New Files:** ``database.py``, ``production_db.py``

**Time to Complete:** 45 minutes

Step 3: Goal Programming
~~~~~~~~~~~~~~~~~~~~~~~~~

:doc:`step3_goals`

Add customer orders as soft constraints with priority-based fulfillment.

**Topics Covered:**

- Customer priority tiers (Gold/Silver/Bronze)
- Soft constraints with ``as_goal()``
- Weighted goal programming
- Multi-objective optimization
- Goal satisfaction analysis

**Files Updated:** ``database.py``, ``production_goals.py``

**Time to Complete:** 45 minutes

Step 4: Large-Scale Multi-Period
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:doc:`step4_scaled`

Scale up to multi-period planning with setup costs and inventory management.

**Topics Covered:**

- Multi-period variables (Product × Period)
- Setup costs and batch constraints
- Inventory balance equations
- Large-scale problem handling
- HTML report generation

**Problem Scale:** 9 products × 4 periods = ~1,600 variables (160x Step 1)

**Files:** ``database.py``, ``production_scaled.py``, ``report_generator.py``

**Time to Complete:** 60 minutes

Step 5: Scenario Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~

:doc:`step5_scenario`

Compare multiple business scenarios systematically.

**Topics Covered:**

- Scenario definition and comparison
- Optimistic/baseline/pessimistic scenarios
- Market demand sensitivity
- Capacity expansion scenarios
- Scenario result visualization

**Files:** ``production_scenarios.py``, ``report_generator.py``

**Time to Complete:** 45 minutes

Step 6: Sensitivity Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:doc:`step6_sensitivity`

Understand how parameter changes affect optimal solutions using dual information.

**Topics Covered:**

- Shadow prices (marginal values)
- Reduced costs (opportunity costs)
- Binding vs non-binding constraints
- Bottleneck identification
- Valid ranges for parameter changes

**Files:** ``production_sensitivity.py``, ``report_generator.py``

**Time to Complete:** 45 minutes

Step 7: What-If Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~

:doc:`step7_whatif`

Interactive exploration of parameter changes for tactical decision support.

**Topics Covered:**

- Interactive what-if scenarios
- Bottleneck identification and ranking
- Investment ROI comparison
- Sensitivity range analysis
- Risk assessment (downside scenarios)
- Model copying with ORM detachment

**Files:** ``production_whatif.py``, ``report_generator.py``

**Time to Complete:** 60 minutes

Prerequisites
-------------

Knowledge Requirements
~~~~~~~~~~~~~~~~~~~~~~

- **Python**: Basic knowledge (dataclasses, functions, loops)
- **Linear Programming**: Helpful but not required (concepts explained)
- **SQL/ORM**: Helpful for database steps (SQLAlchemy basics provided)

Software Requirements
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Core requirements
   pip install lumix[ortools]  # LumiX with OR-Tools solver

   # Database steps (Step 2+)
   pip install sqlalchemy

   # Optional: Better solvers for large-scale problems
   pip install lumix[gurobi]  # Requires Gurobi license
   pip install lumix[cplex]   # Requires CPLEX license

Getting Started
---------------

Quick Start
~~~~~~~~~~~

.. code-block:: bash

   # Clone repository
   git clone https://github.com/tdelphi1981/LumiX.git
   cd LumiX/tutorials/production_planning

   # Start with Step 1
   cd step1_basic_production
   python sample_data.py  # Review sample data
   python production.py    # Run optimization

   # Progress through steps sequentially
   cd ../step2_database_integration
   python sample_data.py  # Populate database
   python production_db.py

Learning Path
~~~~~~~~~~~~~

**For Beginners:**

1. Start with Step 1 to understand continuous variables
2. Complete all steps sequentially
3. Read all README files thoroughly
4. Experiment with modifications

**For Intermediate Users:**

1. Skim Step 1, focus on Step 2 for database integration
2. Study Step 3 for goal programming patterns
3. Analyze Step 4 for scaling techniques
4. Focus on Steps 5-7 for advanced analysis

**For Advanced Users:**

1. Review Step 4 for multi-period modeling patterns
2. Study Steps 5-7 for analysis workflows
3. Adapt patterns to your problem domain
4. Explore extension ideas in each README

Key Differences from Timetabling Tutorial
-----------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Aspect
     - Production Planning
     - Timetabling
   * - **Variable Type**
     - Continuous (quantities)
     - Binary (assignments)
   * - **Decision**
     - How much to produce?
     - Which slot to assign?
   * - **Objective**
     - Maximize profit
     - Minimize conflicts
   * - **Primary Constraints**
     - Resource consumption
     - One assignment per item
   * - **Scaling Challenge**
     - Time periods
     - Number of items
   * - **Analysis Focus**
     - ROI, marginal values
     - Satisfaction, feasibility

When to Use Each Pattern
~~~~~~~~~~~~~~~~~~~~~~~~~

**Use Production Planning Patterns For:**

- Manufacturing and production scheduling
- Resource allocation with consumption rates
- Blending and mixing problems
- Budget allocation
- Inventory management
- Supply chain optimization

**Use Timetabling Patterns For:**

- Scheduling and assignment problems
- Rostering and shift planning
- Facility allocation
- Project task assignment
- Tournament scheduling
- Exam timetabling

Real-World Applications
-----------------------

The patterns in this tutorial apply to:

Manufacturing
~~~~~~~~~~~~~

- **Production Planning**: Multi-product factories with shared resources
- **Batch Production**: Setup costs and minimum run sizes
- **Make-to-Order**: Customer priority management
- **Capacity Planning**: Investment decisions and bottleneck analysis

Supply Chain
~~~~~~~~~~~~

- **Multi-Echelon Inventory**: Warehouse and distribution center levels
- **Procurement Planning**: Supplier capacity and lead times
- **Distribution Planning**: Transportation and storage constraints

Finance & Resource Allocation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Budget Allocation**: Department budgets with competing priorities
- **Project Portfolio**: Resource allocation across projects
- **Capital Investment**: ROI analysis and risk assessment

Process Industries
~~~~~~~~~~~~~~~~~~

- **Blending Problems**: Chemical mixing with quality constraints
- **Refinery Planning**: Crude oil processing optimization
- **Food Production**: Recipe optimization with ingredient costs

Extension Ideas
---------------

After completing this tutorial, consider these extensions:

**Model Enhancements:**

- Add minimum order quantities and lot sizing
- Include transportation costs and logistics
- Model machine maintenance schedules
- Add workforce planning and shift constraints
- Include quality requirements and yield factors

**Analysis Extensions:**

- Stochastic optimization with demand uncertainty
- Robust optimization for worst-case scenarios
- Rolling horizon planning with MPC
- Real-time replanning with actual data
- Integration with ERP systems

**Visualization Improvements:**

- Interactive dashboards with Plotly/Dash
- Gantt charts for production schedules
- Real-time status monitors
- Mobile-friendly reports

Common Patterns
---------------

Continuous vs Binary Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Binary decision (timetabling pattern)
   assignment = LXVariable[Tuple[Lecture, TimeSlot], int]("assignment")
       .binary()  # 0 or 1

   # Continuous quantity (production pattern)
   production = LXVariable[Product, float]("production")
       .continuous()
       .bounds(lower=0)  # Non-negative real number

Resource Consumption
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Production planning: sum of consumption rates
   machine_usage = LXLinearExpression()
   machine_usage.add_term(production, lambda p: p.machine_hours_per_unit)

   model.add_constraint(
       LXConstraint("machine_capacity")
       .expression(machine_usage)
       .le()
       .rhs(available_hours)
   )

Multi-Period Indexing
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Index by product AND period
   production = LXVariable[Tuple[Product, Period], float]("production")
       .continuous()
       .indexed_by_product(
           LXIndexDimension(Product, lambda p: p.id).from_model(session),
           LXIndexDimension(Period, lambda per: per.id).from_model(session),
       )

Goal Programming Pattern
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Hard constraint (must satisfy)
   model.add_constraint(
       LXConstraint("resource_limit").expression(expr).le().rhs(100)
   )

   # Soft goal (try to achieve, prioritized)
   model.add_constraint(
       LXConstraint("customer_order")
       .expression(expr)
       .ge()
       .rhs(order.quantity)
       .as_goal(priority=order.customer.tier, weight=1.0)
   )

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Problem**: Solver takes too long

- **Solution**: Use commercial solver (Gurobi, CPLEX) for large problems
- **Alternative**: Add tighter bounds on variables
- **Check**: Remove redundant constraints

**Problem**: Infeasible solution

- **Solution**: Relax some constraints or check data consistency
- **Debug**: Remove constraints one by one to find conflict
- **Use**: Goal programming to convert hard constraints to soft goals

**Problem**: ORM session errors in what-if analysis

- **Solution**: Use model copying with ORM detachment (Step 7)
- **Reference**: :doc:`/user-guide/utils/model-copying`

**Problem**: Database connection errors

- **Solution**: Check SQLite file path and permissions
- **Verify**: ``sample_data.py`` ran successfully

Next Steps
----------

After Completing This Tutorial
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Apply to Your Problems**: Adapt the patterns to your domain
2. **Explore Other Tutorials**: Try :doc:`../timetabling/index` for binary optimization
3. **Read User Guides**: Deep dive into specific features
4. **Join Community**: Share your implementations and get help

Related Documentation
~~~~~~~~~~~~~~~~~~~~~

- :doc:`/user-guide/core/variables` - Variable types and indexing
- :doc:`/user-guide/analysis/index` - Analysis tools overview
- :doc:`/user-guide/utils/orm-integration` - Database integration details
- :doc:`/examples/production_planning` - Standalone example

Getting Help
------------

- **Tutorial Issues**: Check README files in each step directory
- **API Questions**: Consult :doc:`/api/index`
- **Bug Reports**: https://github.com/tdelphi1981/LumiX/issues
- **Discussions**: https://github.com/tdelphi1981/LumiX/discussions

Contributing
------------

Found an issue or have an improvement? We welcome contributions!

1. Open an issue describing the problem or enhancement
2. Follow the tutorial structure and documentation style
3. Test thoroughly with multiple problem sizes
4. Submit a pull request with clear description

See Also
--------

- :doc:`../timetabling/index` - Binary variable optimization tutorial
- :doc:`/examples/index` - Standalone examples
- :doc:`/user-guide/index` - Comprehensive feature documentation
- :doc:`/api/index` - Complete API reference
