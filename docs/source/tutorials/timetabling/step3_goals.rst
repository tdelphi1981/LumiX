Step 3: Goal Programming with Teacher Preferences
===================================================

Overview
--------

This step extends Step 2 by adding teacher preferences as soft constraints using LumiX's goal programming feature. Teachers can express preferences, and these are converted to goals with priorities based on teacher seniority.

**What's New in Step 3:**

- Teacher preferences (DAY_OFF, SPECIFIC_TIME)
- Priority-based scheduling using teacher seniority
- Goal programming with weighted objectives
- Preference satisfaction analysis

**Prerequisites:**

.. code-block:: bash

   pip install lumix gurobi sqlalchemy  # Gurobi recommended for goal programming

Problem Description
-------------------

Same as Steps 1 & 2, but now with:

- **Hard constraints**: Basic timetabling rules (must be satisfied)
- **Soft constraints (goals)**: Teacher preferences (minimize violations)
- **Priority levels**: Senior teachers (Priority 1) > Mid-level (Priority 2) > Junior (Priority 3)

Mathematical Formulation
------------------------

Hard Constraints (Same as Steps 1 & 2)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Each lecture assigned exactly once
- No classroom/teacher/class conflicts
- Classroom capacity constraints

Soft Constraints (Goals)
~~~~~~~~~~~~~~~~~~~~~~~~~

**DAY_OFF Preference**: Minimize work on preferred day off

.. math::

   \sum_{\substack{l \in \text{Lectures} \\ \text{teacher}(l) = t}} 
   \sum_{\substack{s \in \text{TimeSlots} \\ \text{day}(s) = d}} 
   \sum_{r \in \text{Classrooms}} 
   \text{assignment}[l, s, r] \leq 0 \quad \text{(Goal)}

**SPECIFIC_TIME Preference**: Assign lecture to preferred timeslot

.. math::

   \sum_{r \in \text{Classrooms}} \text{assignment}[l_{pref}, t_{pref}, r] \geq 1 \quad \text{(Goal)}

Priorities
~~~~~~~~~~

Based on years of service (``work_years``):

- **Priority 1**: Teachers with 15+ years (highest priority)
- **Priority 2**: Teachers with 7-14 years (medium priority)
- **Priority 3**: Teachers with 0-6 years (lower priority)

Key Features Demonstrated
--------------------------

1. Goal Programming
~~~~~~~~~~~~~~~~~~~

Converting preferences to soft constraints:

.. code-block:: python

   # Hard constraint (must satisfy)
   model.add_constraint(
       LXConstraint("lecture_coverage")
       .expression(expr)
       .eq()
       .rhs(1)
   )

   # Soft goal (minimize violation with priority)
   model.add_constraint(
       LXConstraint("teacher_preference")
       .expression(expr)
       .le()
       .rhs(0)
       .as_goal(priority=1, weight=1.0)  # Priority 1 = highest
   )

   # Prepare goal programming
   model.set_goal_mode("weighted")
   model.prepare_goal_programming()

2. Priority-Based Scheduling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../../tutorials/timetabling/step3_goal_programming/database.py
   :language: python
   :pyobject: calculate_priority_from_work_years

3. Preference Types
~~~~~~~~~~~~~~~~~~~

**DAY_OFF**: Teacher wants a specific day completely free

.. literalinclude:: ../../../../tutorials/timetabling/step3_goal_programming/timetabling_goals.py
   :language: python
   :lines: 223-256
   :dedent: 8

**SPECIFIC_TIME**: Teacher wants to teach a specific lecture at a specific time

.. literalinclude:: ../../../../tutorials/timetabling/step3_goal_programming/timetabling_goals.py
   :language: python
   :lines: 258-287
   :dedent: 8

Database Schema Extensions
---------------------------

New Tables
~~~~~~~~~~

**teacher_preferences** table:

- ``id``: Primary key
- ``teacher_id``: Foreign key to teachers
- ``preference_type``: 'DAY_OFF' or 'SPECIFIC_TIME'
- ``day_of_week``: Preferred day (for DAY_OFF)
- ``lecture_id``: Specific lecture (for SPECIFIC_TIME)
- ``timeslot_id``: Specific timeslot (for SPECIFIC_TIME)
- ``description``: Human-readable description

Updated Models
~~~~~~~~~~~~~~

**Teacher** model now includes ``work_years``:

.. literalinclude:: ../../../../tutorials/timetabling/step3_goal_programming/database.py
   :language: python
   :lines: 63-79
   :dedent: 0

Running the Example
-------------------

Step 1: Populate Database with Preferences
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   cd tutorials/timetabling/step3_goal_programming
   python sample_data.py

Step 2: Run Goal Programming
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   python timetabling_goals.py

Expected Output
~~~~~~~~~~~~~~~

1. Data loading with preference counts
2. Model building with goal constraints
3. Solution status
4. Timetables for teachers and classes
5. **Preference satisfaction analysis**:
   - Per-teacher satisfaction rates
   - Priority-level satisfaction rates
   - Overall satisfaction percentage

Code Walkthrough
----------------

1. Load Preferences from Database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../../tutorials/timetabling/step3_goal_programming/timetabling_goals.py
   :language: python
   :lines: 91-104
   :dedent: 4

2. Set Goal Programming Mode
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../../tutorials/timetabling/step3_goal_programming/timetabling_goals.py
   :language: python
   :lines: 261-262
   :dedent: 4

3. Add Goal Constraints
~~~~~~~~~~~~~~~~~~~~~~~~

For each preference, create a goal constraint with calculated priority.

4. Analyze Goal Satisfaction
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../../tutorials/timetabling/step3_goal_programming/timetabling_goals.py
   :language: python
   :lines: 322-378
   :dedent: 0

Key Learnings
-------------

Goal Programming Concepts
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Hard vs. Soft Constraints:**

- **Hard**: Must be satisfied (infeasible if violated)
- **Soft (Goals)**: Minimize violations weighted by priority

**Priority Levels:**

Higher priority goals are satisfied first, even if lower priority goals must be violated.

**Weighted vs. Sequential:**

- **Weighted**: Single optimization with priority weights
- **Sequential**: Multiple optimizations, one per priority level

Performance Considerations
~~~~~~~~~~~~~~~~~~~~~~~~~~

Goal programming increases solve time:

- More variables (deviation variables added automatically)
- More constraints (one per goal)
- Use commercial solvers (Gurobi, CPLEX) for better performance

Typical Results
~~~~~~~~~~~~~~~

With 7 preferences across 3 priority levels:

- **Priority 1** (Senior): 80-100% satisfaction
- **Priority 2** (Mid-level): 60-80% satisfaction
- **Priority 3** (Junior): 40-60% satisfaction
- **Overall**: 60-80% satisfaction

Next Steps
----------

After completing Step 3, proceed to:

- **Step 4** (:doc:`step4_scaled`) - Scale to production-ready size with room types

See Also
--------

**Related Examples:**

- :doc:`/examples/goal_programming` - Goal programming basics

**Related User Guide:**

- :doc:`/user-guide/goal_programming/index` - Comprehensive goal programming guide
- :doc:`/user-guide/goal_programming/weighted-mode` - Weighted goal programming
- :doc:`/user-guide/goal_programming/sequential-mode` - Sequential goal programming

**API Reference:**

- :doc:`/api/core/generated/lumix.core.model.LXModel` - Goal programming methods

---

**Tutorial Step 3 Complete!**

You've learned how to use goal programming for multi-objective optimization with teacher preferences. Now move on to :doc:`step4_scaled` to see how LumiX scales to production-ready problems.
