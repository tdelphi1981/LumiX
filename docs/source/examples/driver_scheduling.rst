Driver Scheduling Example
=========================

Overview
--------

This example demonstrates LumiX's **multi-model indexing** feature - THE KEY CAPABILITY that sets LumiX apart from traditional optimization libraries. Variables are indexed by **cartesian products** of multiple data models, allowing natural representation of relationships between entities.

The driver scheduling problem optimally assigns drivers to dates while minimizing total cost and respecting availability and capacity constraints.

Problem Description
-------------------

A delivery company needs to schedule drivers over a week to minimize labor costs while meeting daily coverage requirements.

**Objective**: Minimize total scheduling cost.

**Each Driver Has**:

- Daily rate (base cost per day)
- Maximum days they can work per week
- Scheduled days off
- Active/inactive status

**Each Date Has**:

- Minimum required drivers for coverage
- Overtime multiplier (e.g., 1.5x for weekends)

**Constraints**:

- Driver capacity: Each driver works at most `max_days_per_week`
- Daily coverage: Each date must have at least `min_drivers_required` drivers
- Availability: Drivers cannot work on their days off

Mathematical Formulation
------------------------

**Decision Variables**:

.. math::

   duty_{d,t} \in \{0, 1\}, \quad \forall d \in \text{Drivers}, t \in \text{Dates}

where :math:`duty_{d,t}` equals 1 if driver :math:`d` works on date :math:`t`, 0 otherwise.

**Objective Function**:

.. math::

   \text{Minimize} \quad \sum_{d \in \text{Drivers}} \sum_{t \in \text{Dates}}
   \text{cost}(d,t) \cdot duty_{d,t}

where :math:`\text{cost}(d,t) = \text{daily\_rate}_d \times \text{overtime\_multiplier}_t`.

**Constraints**:

1. **Driver Maximum Days**:

   .. math::

      \sum_{t \in \text{Dates}} duty_{d,t} \leq \text{max\_days}_d,
      \quad \forall d \in \text{Drivers}

2. **Daily Coverage**:

   .. math::

      \sum_{d \in \text{Drivers}} duty_{d,t} \geq \text{min\_required}_t,
      \quad \forall t \in \text{Dates}

3. **Availability**:

   .. math::

      duty_{d,t} = 0, \quad \text{if } t.\text{weekday} \in d.\text{days\_off}

Key Features
------------

Multi-Model Indexing (THE KEY FEATURE)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Variables are indexed by **tuples** of multiple model instances:

.. literalinclude:: ../../../examples/02_driver_scheduling/driver_scheduling.py
   :language: python
   :lines: 116-131
   :dedent: 4

**Key Points**:

- ``LXVariable[Tuple[Driver, Date], int]`` creates a variable family for each (driver, date) pair
- ``.indexed_by_product()`` builds the cartesian product of two dimensions
- ``LXIndexDimension`` defines each dimension with filtering and indexing
- ``.where()`` filters items in a single dimension
- ``.where_multi()`` filters combinations based on both models simultaneously
- No manual nested loops needed - cartesian product is automatic

Cartesian Product Dimensions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create variables for every valid combination:

.. literalinclude:: ../../../examples/02_driver_scheduling/driver_scheduling.py
   :language: python
   :lines: 119-126

The first dimension (Driver) is filtered to only active drivers, while the second dimension (Date) includes all dates.

Multi-Model Cost Functions
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Cost functions receive **both** index models:

.. literalinclude:: ../../../examples/02_driver_scheduling/driver_scheduling.py
   :language: python
   :lines: 127-130
   :dedent: 8

The ``lambda driver, date: calculate_cost(driver, date)`` has access to both driver and date objects.

Cross-Dimensional Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sum over one dimension while fixing the other:

.. literalinclude:: ../../../examples/02_driver_scheduling/driver_scheduling.py
   :language: python
   :lines: 153-169
   :dedent: 4

This sums over all dates for a specific driver. Note the closure capture: ``drv=driver`` captures the loop variable by value.

Type-Safe Solution Access
~~~~~~~~~~~~~~~~~~~~~~~~~~

Solutions preserve the multi-dimensional structure:

.. code-block:: python

   for driver in DRIVERS:
       for date in DATES:
           # Access using (driver_id, date) tuple!
           value = solution.variables["duty"].get((driver.id, date.date), 0)
           if value > 0.5:  # Driver assigned
               print(f"{driver.name} works on {date.date}")

Running the Example
-------------------

**Prerequisites**:

.. code-block:: bash

   pip install lumix[ortools]  # or cplex, gurobi

**Run**:

.. code-block:: bash

   cd examples/02_driver_scheduling
   python driver_scheduling.py

**Expected Output**:

.. code-block:: text

   ======================================================================
   LumiX Example: Driver Scheduling (Multi-Model Indexing)
   ======================================================================

   ⭐⭐⭐ THIS IS THE KEY LUMIX FEATURE! ⭐⭐⭐

   Drivers:
   ----------------------------------------------------------------------
     Alice     : $150.00/day, max 5 days/week  [Active] (off: Sun)
     Bob       : $120.00/day, max 6 days/week  [Active] (off: None)
     Charlie   : $100.00/day, max 4 days/week  [Active] (off: Sat, Sun)

   Model Summary:
     Variables: 1 family (35 binary variables from 7 drivers × 7 dates)
     Constraints: 14 (7 max days + 7 coverage)

   ======================================================================
   SOLUTION
   ======================================================================
   Status: optimal
   Optimal Cost: $2,450.00

   Schedule by Date:
   ----------------------------------------------------------------------

   Monday Jun 01, 2024:
     - Bob        ($100.00)
     - Charlie    ($150.00)
     Daily Cost: $250.00

   Driver Summary:
   ----------------------------------------------------------------------
     Alice     : 4 days (Mon 06/01, Tue 06/02, Thu 06/04, Fri 06/05) = $480.00
     Bob       : 6 days (all weekdays + Sat) = $650.00

Complete Code Walkthrough
--------------------------

Step 1: Define Data Models
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/02_driver_scheduling/sample_data.py
   :language: python
   :lines: 36-104
   :dedent: 0

Step 2: Create Multi-Indexed Variable
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/02_driver_scheduling/driver_scheduling.py
   :language: python
   :lines: 116-131
   :dedent: 4

Step 3: Set Objective
~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/02_driver_scheduling/driver_scheduling.py
   :language: python
   :lines: 138-145
   :dedent: 4

Step 4: Add Driver Capacity Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/02_driver_scheduling/driver_scheduling.py
   :language: python
   :lines: 153-169
   :dedent: 4

Step 5: Add Daily Coverage Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/02_driver_scheduling/driver_scheduling.py
   :language: python
   :lines: 177-190
   :dedent: 4

Step 6: Solve and Access Solution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   optimizer = LXOptimizer().use_solver("ortools")
   solution = optimizer.solve(model)

   if solution.is_optimal():
       for driver in DRIVERS:
           for date in DATES:
               value = solution.variables["duty"].get((driver.id, date.date), 0)

Learning Objectives
-------------------

After completing this example, you should understand:

1. **Multi-Model Variables**: How to create variables indexed by cartesian products
2. **LXIndexDimension**: How to define and filter each dimension independently
3. **Cartesian Products**: How ``indexed_by_product()`` creates all combinations
4. **Multi-Model Lambdas**: How to write functions that receive multiple index models
5. **Cross-Dimensional Sums**: How to sum over one dimension while filtering by another
6. **Closure Capture**: Why and how to capture loop variables by value (``var=loop_var``)
7. **Tuple Indexing**: How to access multi-indexed solution values

Common Patterns
---------------

Pattern 1: Multi-Model Variable Family
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   assignment = (
       LXVariable[Tuple[ModelA, ModelB], VarType]("var_name")
       .binary()  # or .continuous(), .integer()
       .indexed_by_product(
           LXIndexDimension(ModelA, lambda a: a.id)
               .where(lambda a: a.is_valid)
               .from_data(DATA_A),
           LXIndexDimension(ModelB, lambda b: b.key)
               .from_data(DATA_B)
       )
       .cost_multi(lambda a, b: compute_cost(a, b))
       .where_multi(lambda a, b: is_valid_pair(a, b))
   )

Pattern 2: Cross-Model Cost Function
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Cost function receives both models
   cost_expr = LXLinearExpression().add_multi_term(
       assignment,
       coeff=lambda a, b: calculate_relationship_cost(a, b)
   )

Pattern 3: Sum Over One Dimension
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # For each A, sum over all B
   for a in DATA_A:
       expr = LXLinearExpression().add_multi_term(
           assignment,
           coeff=lambda a_var, b_var: 1.0,
           where=lambda a_var, b_var, current_a=a: a_var.id == current_a.id
       )
       model.add_constraint(
           LXConstraint(f"sum_for_{a.id}")
           .expression(expr)
           .le()
           .rhs(a.capacity)
       )

Pattern 4: Closure Capture (IMPORTANT!)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # CORRECT: Capture by value
   for item in DATA:
       where=lambda x, y, current_item=item: x.id == current_item.id

   # WRONG: Captures reference (always uses last item!)
   for item in DATA:
       where=lambda x, y: x.id == item.id  # BUG!

Extending the Example
---------------------

Try These Modifications
~~~~~~~~~~~~~~~~~~~~~~~

1. **Add Third Dimension**: Include shifts within each day

   .. code-block:: python

      duty = LXVariable[Tuple[Driver, Date, Shift], int]("duty")

2. **Precedence Constraints**: Drivers need rest between consecutive days
3. **Skill Requirements**: Some dates require drivers with specific skills
4. **Preference Scores**: Optimize for driver preferences (soft constraints)
5. **Multi-Week Planning**: Extend the time horizon to monthly schedules

Next Steps
----------

After mastering this example:

1. **Example 03 (Facility Location)**: Binary variables with fixed costs and Big-M
2. **Example 05 (CP-SAT Assignment)**: Worker-task assignment with CP-SAT solver
3. **Example 01 (Production Planning)**: Review single-model indexing basics
4. **User Guide - Multi-Model Indexing**: Deep dive into cartesian products

See Also
--------

**Related Examples**:

- :doc:`production_planning` - Single-model indexing foundation
- :doc:`facility_location` - Multi-model with binary and continuous variables
- :doc:`cpsat_assignment` - CP-SAT solver for assignment problems

**API Reference**:

- :class:`lumix.core.variables.LXVariable`
- :class:`lumix.indexing.LXIndexDimension`
- :class:`lumix.core.model.LXModel`
- :class:`lumix.core.constraints.LXConstraint`
- :class:`lumix.core.expressions.LXLinearExpression`

**User Guide**:

- :doc:`../user-guide/indexing/multi-model` - Multi-model indexing
- :doc:`../user-guide/core/variables` - Variable types and families
- :doc:`../user-guide/core/constraints` - Constraint modeling

Why This is LumiX's Killer Feature
-----------------------------------

Traditional Libraries
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # PuLP, Pyomo, CVXPY, etc.
   duty = {}
   for i, driver in enumerate(drivers):
       for j, date in enumerate(dates):
           duty[i, j] = model.add_var(name=f"duty_{i}_{j}")

   # Later: duty[0, 3] - which driver is 0? which date is 3?
   # Lost all context! Must maintain separate mapping dictionaries.

LumiX Approach
~~~~~~~~~~~~~~

.. code-block:: python

   duty = LXVariable[Tuple[Driver, Date], int]("duty").indexed_by_product(...)

   # Later: solution.variables["duty"][(driver.id, date.date)]
   # Full context preserved! IDE autocomplete! Type safety!

**Advantages**:

- Natural problem representation (no manual index management)
- Type-safe indexing (IDE knows the structure)
- Context preservation (never lose track of what indices mean)
- Cleaner code (no nested dictionary creation loops)
- Fewer bugs (compiler catches type errors)

Files in This Example
---------------------

- ``driver_scheduling.py`` - Main optimization model and solution display
- ``sample_data.py`` - Data models (Driver, Date) and helper functions
- ``README.md`` - Detailed documentation and usage guide
