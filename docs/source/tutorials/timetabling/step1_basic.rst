Step 1: Basic Course Timetabling
=================================

Overview
--------

This is the first step in the High School Course Timetabling tutorial. It demonstrates how to build a basic timetabling optimization model using LumiX with **3D multi-model indexing**.

The goal is to assign lectures (teacher-subject-class combinations) to timeslots and classrooms while respecting scheduling constraints.

**What You'll Learn:**

- Creating 3D indexed variables
- Building complex scheduling constraints
- Filtering infeasible combinations
- Generating human-readable timetable outputs

**Prerequisites:**

.. code-block:: bash

   pip install lumix ortools

Problem Description
-------------------

A high school needs to create a weekly timetable for all classes. The schedule must:

1. **Assign each lecture exactly once** to a timeslot and classroom
2. **Avoid classroom conflicts** - only one lecture per classroom per timeslot
3. **Avoid teacher conflicts** - teachers can't teach two lectures simultaneously
4. **Avoid class conflicts** - classes can't attend two lectures at the same time
5. **Respect classroom capacity** - class size must fit in the assigned classroom

Problem Data
~~~~~~~~~~~~

- **5 Teachers**: Dr. Smith, Prof. Johnson, Ms. Williams, Mr. Brown, Dr. Davis
- **4 Classrooms**: Room 101 (30), Room 102 (30), Room 201 (25), Lab A (20)
- **4 Classes**: 9A (25 students), 9B (28 students), 10A (24 students), 10B (26 students)
- **5 Subjects**: Mathematics, English, Physics, Chemistry, History
- **20 Lectures**: Individual teaching sessions (e.g., "Dr. Smith teaches Math to Class 9A")
- **30 Timeslots**: 5 days × 6 periods per day (Monday-Friday, Periods 1-6)

Real-World Context
~~~~~~~~~~~~~~~~~~

This type of problem appears in:

- High school and university course scheduling
- Training session planning
- Conference scheduling
- Resource allocation with time and space constraints
- Employee shift scheduling with location assignments

Mathematical Formulation
------------------------

Decision Variables
~~~~~~~~~~~~~~~~~~

.. math::

   \text{assignment}[l, t, r] \in \{0, 1\} \quad \forall (l, t, r) \in \text{Lectures} \times \text{TimeSlots} \times \text{Classrooms}

Where:

- :math:`l \in \text{Lectures}` - a specific lecture (teacher-subject-class combination)
- :math:`t \in \text{TimeSlots}` - a specific timeslot (day, period)
- :math:`r \in \text{Classrooms}` - a specific classroom
- :math:`\text{assignment}[l, t, r] = 1` if lecture :math:`l` is assigned to timeslot :math:`t` in classroom :math:`r`
- :math:`\text{assignment}[l, t, r] = 0` otherwise

Objective Function
~~~~~~~~~~~~~~~~~~

This is a **feasibility problem** - the goal is to find any valid schedule that satisfies all constraints. There is no optimization objective (e.g., minimizing costs or maximizing preferences).

.. note::
   Steps 2-4 will introduce optimization objectives through goal programming.

Constraints
~~~~~~~~~~~

**1. Lecture Coverage** - Each lecture must be assigned exactly once:

.. math::

   \sum_{t \in \text{TimeSlots}} \sum_{r \in \text{Classrooms}} \text{assignment}[l, t, r] = 1 \quad \forall l \in \text{Lectures}

**2. Classroom Capacity** - Class must fit in assigned classroom:

.. math::

   \text{assignment}[l, t, r] = 0 \quad \text{if } \text{class\_size}(l) > \text{capacity}(r)

This is enforced through filtering in LumiX using ``where_multi()``.

**3. No Classroom Conflicts** - Maximum one lecture per classroom per timeslot:

.. math::

   \sum_{l \in \text{Lectures}} \text{assignment}[l, t, r] \leq 1 \quad \forall (t, r) \in \text{TimeSlots} \times \text{Classrooms}

**4. No Teacher Conflicts** - Teacher can't teach multiple lectures simultaneously:

.. math::

   \sum_{\substack{l \in \text{Lectures} \\ \text{teacher}(l) = \text{teacher}}} \sum_{r \in \text{Classrooms}} \text{assignment}[l, t, r] \leq 1 \quad \forall \text{teacher}, t

**5. No Class Conflicts** - Class can't attend multiple lectures at the same time:

.. math::

   \sum_{\substack{l \in \text{Lectures} \\ \text{class}(l) = \text{class}}} \sum_{r \in \text{Classrooms}} \text{assignment}[l, t, r] \leq 1 \quad \forall \text{class}, t

Key LumiX Concepts
------------------

1. Three-Dimensional Multi-Model Indexing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Variables indexed by **tuples of three models**:

.. literalinclude:: ../../../../tutorials/timetabling/step1_basic_timetabling/timetabling.py
   :language: python
   :lines: 110-122
   :dedent: 4

**Traditional Approach (Other Libraries)**:

.. code-block:: python

   # Manual indexing - loses semantic meaning
   assignment = {}
   for i, lecture in enumerate(lectures):
       for j, timeslot in enumerate(timeslots):
           for k, classroom in enumerate(classrooms):
               assignment[i, j, k] = model.add_var()

   # Access: assignment[0, 5, 2]
   # Which lecture? Which time? Which room? Context lost!

**LumiX Approach - THE KEY FEATURE**:

.. code-block:: python

   # Type-safe, semantic indexing
   assignment = LXVariable[Tuple[Lecture, TimeSlot, Classroom], int]("assignment")
       .binary()
       .indexed_by_product(...)

   # Access: solution.variables["assignment"][(lecture.id, timeslot.id, classroom.id)]
   # IDE knows the structure! Type-safe! Full context preserved!

**Benefits:**

- **Type Safety**: IDE autocomplete and type checking
- **Semantic Meaning**: Variable names reflect business logic
- **Maintainability**: Code reads like the problem description
- **Debugging**: Clear what each index represents

2. Cartesian Product with Three Dimensions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``.indexed_by_product()`` creates variables for every combination of Lecture × TimeSlot × Classroom:

.. code-block:: python

   .indexed_by_product(
       LXIndexDimension(Lecture, lambda lec: lec.id).from_data(LECTURES),
       LXIndexDimension(TimeSlot, lambda ts: ts.id).from_data(TIMESLOTS),
       LXIndexDimension(Classroom, lambda room: room.id).from_data(CLASSROOMS)
   )
   # Creates: 20 lectures × 30 timeslots × 4 classrooms = 2,400 binary variables

3. Filtering with where_multi()
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Filter out infeasible combinations based on relationships between models:

.. literalinclude:: ../../../../tutorials/timetabling/step1_basic_timetabling/timetabling.py
   :language: python
   :lines: 119-121
   :dedent: 8

**Purpose**: Only create variables where the class fits in the classroom. This:

- Reduces problem size (fewer variables)
- Enforces capacity constraints implicitly
- Improves solver performance

4. Multi-Dimensional Summation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sum over specific dimensions using filters:

**Pattern 1: Sum over timeslots and classrooms for a specific lecture**

.. literalinclude:: ../../../../tutorials/timetabling/step1_basic_timetabling/timetabling.py
   :language: python
   :lines: 133-138
   :dedent: 8

**Pattern 2: Sum over lectures for a specific timeslot and classroom**

.. literalinclude:: ../../../../tutorials/timetabling/step1_basic_timetabling/timetabling.py
   :language: python
   :lines: 149-155
   :dedent: 12

.. important::
   Notice the closure capture: ``current_lecture=lecture`` captures the loop variable by **value**.
   Without this, all constraints would reference the last lecture due to late binding.

Code Walkthrough
----------------

Step 1: Define Data Models
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The sample data uses dataclasses for type-safe data representation:

.. literalinclude:: ../../../../tutorials/timetabling/step1_basic_timetabling/sample_data.py
   :language: python
   :lines: 33-49
   :dedent: 0

.. literalinclude:: ../../../../tutorials/timetabling/step1_basic_timetabling/sample_data.py
   :language: python
   :lines: 109-132
   :dedent: 0

Step 2: Create 3D Decision Variable
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../../tutorials/timetabling/step1_basic_timetabling/timetabling.py
   :language: python
   :lines: 108-127
   :dedent: 4

Step 3: Add Lecture Coverage Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../../tutorials/timetabling/step1_basic_timetabling/timetabling.py
   :language: python
   :lines: 131-142
   :dedent: 4

Step 4: Add Classroom Conflict Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../../tutorials/timetabling/step1_basic_timetabling/timetabling.py
   :language: python
   :lines: 144-161
   :dedent: 4

Step 5: Add Teacher Conflict Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../../tutorials/timetabling/step1_basic_timetabling/timetabling.py
   :language: python
   :lines: 163-183
   :dedent: 4

Step 6: Add Class Conflict Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../../tutorials/timetabling/step1_basic_timetabling/timetabling.py
   :language: python
   :lines: 185-205
   :dedent: 4

Running the Example
-------------------

Prerequisites
~~~~~~~~~~~~~

Install LumiX and OR-Tools:

.. code-block:: bash

   pip install lumix
   pip install ortools

Execute
~~~~~~~

.. code-block:: bash

   cd tutorials/timetabling/step1_basic_timetabling
   python timetabling.py

Expected Output
~~~~~~~~~~~~~~~

The program will display:

1. **Model Building Information**:

   - Number of variables created
   - Number of constraints added
   - Problem size summary

2. **Solution Status**:

   - Whether a feasible solution was found
   - Solution quality

3. **Teacher Timetables** (one for each teacher):

   - Weekly schedule showing subject, class, and classroom
   - Organized by day (columns) and period (rows)

4. **Class Timetables** (one for each class):

   - Weekly schedule showing subject, teacher, and classroom
   - Organized by day (columns) and period (rows)

Example Timetable Output
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   ================================================================================
   Timetable for Dr. Smith
   ================================================================================

   Period   Monday               Tuesday              Wednesday            Thursday             Friday
   ------------------------------------------------------------------------------------------------------------
   1        Mathematics          Mathematics                               Mathematics
            9A                   10A                                       9B
            Room 101             Room 102                                  Room 101

   2                                                  Mathematics                               Mathematics
                                                      10B                                       9A
                                                      Room 102                                  Room 101
   ...

Files in This Example
---------------------

- **sample_data.py**: Data models (Teacher, Classroom, SchoolClass, Lecture, TimeSlot) and sample data
- **timetabling.py**: Main optimization model, solver, and timetable display
- **README.md**: Detailed documentation in the tutorial directory

Key Learnings
-------------

1. Multi-Dimensional Problem Representation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The 3D indexing naturally represents the timetabling decision:

- **What** (Lecture) is scheduled
- **When** (TimeSlot) it occurs
- **Where** (Classroom) it takes place

Traditional approaches use nested loops and numerical indices, losing this semantic meaning.

2. Constraint Complexity
~~~~~~~~~~~~~~~~~~~~~~~~

Timetabling involves multiple types of constraints that sum over different dimensions:

- **Lecture coverage**: Sum over time and space for each lecture
- **Room conflicts**: Sum over lectures for each time-space pair
- **Teacher conflicts**: Sum over lectures (filtered by teacher) for each time
- **Class conflicts**: Sum over lectures (filtered by class) for each time

LumiX's ``add_multi_term()`` with ``where`` filters makes these constraints readable and maintainable.

3. Feasibility vs. Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is a **constraint satisfaction problem** (CSP). The goal is to find any valid schedule, not to optimize an objective function.

.. seealso::
   Steps 2-4 will add optimization objectives using goal programming.

Common Patterns Demonstrated
-----------------------------

Pattern 1: 3D Multi-Model Variable
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   decision = LXVariable[Tuple[ModelA, ModelB, ModelC], type]("name")
       .indexed_by_product(
           LXIndexDimension(ModelA, key_func).from_data(DATA_A),
           LXIndexDimension(ModelB, key_func).from_data(DATA_B),
           LXIndexDimension(ModelC, key_func).from_data(DATA_C)
       )

Pattern 2: Filtering with Three Models
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   .where_multi(lambda a, b, c: is_valid_combination(a, b, c))

Pattern 3: Sum Over One Dimension
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # For each A and B, sum over all C
   for a in DATA_A:
       for b in DATA_B:
           expr = LXLinearExpression().add_multi_term(
               decision,
               coeff=lambda a_var, b_var, c_var: 1.0,
               where=lambda a_var, b_var, c_var, current_a=a, current_b=b:
                   a_var.id == current_a.id and b_var.id == current_b.id
           )

Pattern 4: Sum Over Two Dimensions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # For each A, sum over all B and C
   for a in DATA_A:
       expr = LXLinearExpression().add_multi_term(
           decision,
           coeff=lambda a_var, b_var, c_var: 1.0,
           where=lambda a_var, b_var, c_var, current_a=a:
               a_var.id == current_a.id
       )

Extensions and Variations
-------------------------

This basic timetabling model can be extended with:

1. **Soft Constraints**: Teacher preferences, time preferences (addressed in Step 3)
2. **Multiple Buildings**: Add building as a 4th dimension
3. **Resource Constraints**: Labs, equipment, projectors
4. **Consecutive Periods**: Some lectures must be in consecutive timeslots
5. **Balancing**: Distribute lectures evenly across the week
6. **Teacher Availability**: Some teachers only available on certain days

Troubleshooting
---------------

No Feasible Solution Found
~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the model returns infeasible:

1. **Reduce lecture count**: Too many lectures for available timeslots
2. **Add classrooms**: Not enough rooms to avoid conflicts
3. **Check classroom capacities**: Some classes may not fit in any room
4. **Verify data consistency**: Ensure all references (teacher_id, class_id, etc.) are valid

Slow Solving
~~~~~~~~~~~~

If the model takes too long:

1. **Use CP-SAT solver**: Better for scheduling problems (``solver_to_use = "cpsat"``)
2. **Add symmetry breaking**: Fix some lectures to specific times
3. **Reduce problem size**: Start with fewer lectures/classes/timeslots

Next Steps
----------

After completing Step 1, proceed to:

- **Step 2** (:doc:`step2_database`) - Add SQLite database integration to store and retrieve schedules
- **Step 3** (:doc:`step3_goals`) - Add teacher preferences using goal programming with priority levels
- **Step 4** (:doc:`step4_scaled`) - Scale to production-ready size with room type constraints

See Also
--------

**Related Examples:**

- :doc:`/examples/driver_scheduling` - 2D multi-model indexing example
- :doc:`/examples/cpsat_assignment` - Alternative solver for scheduling problems

**Related User Guide:**

- :doc:`/user-guide/indexing/multi-model` - Multi-dimensional indexing documentation
- :doc:`/user-guide/core/constraints` - Constraint formulation guide
- :doc:`/user-guide/solvers/index` - Solver selection guide

**API Reference:**

- :doc:`/api/core/generated/lumix.core.variables.LXVariable` - Variable creation
- :doc:`/api/core/generated/lumix.core.constraints.LXConstraint` - Constraint definition
- :doc:`/api/core/generated/lumix.core.model.LXModel` - Model building

---

**Tutorial Step 1 Complete!**

You've learned how to build a basic timetabling model with 3D multi-model indexing. Now move on to :doc:`step2_database` to add database integration.
