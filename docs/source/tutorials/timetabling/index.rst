High School Course Timetabling Tutorial
========================================

A comprehensive 4-step tutorial demonstrating how to build a complete course timetabling solution using LumiX, progressing from basic optimization to production-ready large-scale systems with goal programming.

.. toctree::
   :maxdepth: 2
   :caption: Tutorial Steps

   step1_basic
   step2_database
   step3_goals
   step4_scaled

Overview
--------

This tutorial teaches you how to solve a real-world high school course timetabling problem through progressive complexity. You'll learn to build models that assign lectures (teacher-subject-class combinations) to specific timeslots and classrooms while respecting scheduling constraints.

**By the end of this tutorial, you'll understand:**

- Multi-dimensional indexing with 3D variables (Lecture × TimeSlot × Classroom)
- Database-driven optimization models with SQLAlchemy ORM
- Multi-objective optimization using goal programming
- Performance optimization for production-scale problems
- Room type constraints for specialized facilities

Problem Description
-------------------

**Scenario**: A high school needs to create a weekly timetable that assigns lectures to specific timeslots and classrooms.

**Constraints**:

- Each lecture must be scheduled exactly once
- No classroom can host two lectures simultaneously
- Teachers can't teach two lectures at the same time
- Classes can't attend two lectures at the same time
- Classroom capacity must accommodate class size
- (Step 4) Specialized rooms: labs for science, gym for PE

**Data** (grows across steps):

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 15 15

   * - Component
     - Step 1
     - Step 2
     - Step 3
     - Step 4
   * - Teachers
     - 5
     - 5
     - 5
     - 15
   * - Classrooms
     - 4
     - 4
     - 4
     - 12
   * - Classes
     - 4
     - 4
     - 4
     - 12
   * - Lectures
     - 20
     - 20
     - 20
     - 80
   * - Timeslots
     - 30
     - 30
     - 30
     - 40
   * - Variables
     - ~2,400
     - ~2,400
     - ~2,400
     - ~38,400

Tutorial Structure
------------------

Step 1: Basic Timetabling
~~~~~~~~~~~~~~~~~~~~~~~~~~

:doc:`step1_basic` - **Core optimization model with multi-dimensional indexing**

**Focus**: Learn LumiX's multi-model indexing with a 3D variable family

**What you'll learn**:

- Creating 3D indexed variables: ``assignment[Lecture, TimeSlot, Classroom]``
- Building complex scheduling constraints
- Filtering infeasible combinations with ``where_multi()``
- Generating tabular timetable outputs

**Key LumiX features**:

- ``LXVariable`` with 3D multi-model indexing
- ``.indexed_by_product()`` for cartesian products
- ``.where_multi()`` for combination filtering
- ``add_multi_term()`` with dimensional filtering

**Files**: ``sample_data.py``, ``timetabling.py``, ``README.md``

.. code-block:: bash

   cd tutorials/timetabling/step1_basic_timetabling
   python timetabling.py

.. seealso::
   :doc:`step1_basic` for full documentation

---

Step 2: Database Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:doc:`step2_database` - **Persistent data storage with SQLite and SQLAlchemy ORM**

**Focus**: Replace Python lists with database storage

**What you'll learn**:

- Designing database schemas for optimization problems
- Using SQLAlchemy declarative models
- Loading LumiX models with ``from_model(session)``
- Saving solutions back to database
- Creating cached checkers for performance

**Key features**:

- SQLite database with 7 tables
- SQLAlchemy ORM models
- ``from_model()`` for direct database queries
- Solution persistence via ``ScheduleAssignment`` table
- Type-safe database operations

**Files**: ``database.py``, ``sample_data.py``, ``timetabling_db.py``, ``README.md``

.. code-block:: bash

   cd tutorials/timetabling/step2_database_integration
   python sample_data.py     # Populate database
   python timetabling_db.py  # Run optimization

.. seealso::
   :doc:`step2_database` for full documentation

---

Step 3: Goal Programming
~~~~~~~~~~~~~~~~~~~~~~~~~

:doc:`step3_goals` - **Multi-objective optimization with teacher preferences**

**Focus**: Add soft constraints using goal programming

**What you'll learn**:

- Expressing teacher preferences as goals
- Assigning priorities based on seniority
- Using LumiX's goal programming feature
- Analyzing goal satisfaction
- Balancing hard requirements with soft preferences

**Key features**:

- Teacher preferences: ``DAY_OFF``, ``SPECIFIC_TIME``
- Priority calculation from ``work_years``
- Weighted goal programming
- Satisfaction analysis and reporting

**Files**: ``database.py``, ``sample_data.py``, ``timetabling_goals.py``, ``README.md``

.. code-block:: bash

   cd tutorials/timetabling/step3_goal_programming
   python sample_data.py         # Populate database with preferences
   python timetabling_goals.py   # Run goal programming

.. seealso::
   :doc:`step3_goals` for full documentation

---

Step 4: Large-Scale Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:doc:`step4_scaled` - **Production-ready size with room type constraints**

**Focus**: Scale to realistic problem sizes with performance optimization

**What you'll learn**:

- Handling 16x more variables efficiently
- Room type constraints (REGULAR, LAB, GYM)
- Cached compatibility checkers for performance
- Building production-ready models
- Analyzing solution quality at scale

**Key features**:

- 15 teachers across 3 departments
- 12 classrooms with room types
- 80 lectures with realistic distribution
- Room type requirements (lab subjects need labs, PE needs gym)
- Enhanced performance with caching

**Files**: ``database.py``, ``sample_data.py``, ``timetabling_scaled.py``, ``README.md``

.. code-block:: bash

   cd tutorials/timetabling/step4_scaled_up
   python sample_data.py           # Generate large-scale data
   python timetabling_scaled.py    # Solve (10-30 seconds)

.. seealso::
   :doc:`step4_scaled` for full documentation

---

Feature Comparison
------------------

.. list-table::
   :header-rows: 1
   :widths: 25 12 12 12 12

   * - Feature
     - Step 1
     - Step 2
     - Step 3
     - Step 4
   * - **Basic Model**
     - ✓
     - ✓
     - ✓
     - ✓
   * - **3D Indexing**
     - ✓
     - ✓
     - ✓
     - ✓
   * - **Hard Constraints**
     - ✓
     - ✓
     - ✓
     - ✓
   * - **Python Lists**
     - ✓
     -
     -
     -
   * - **SQLite Database**
     -
     - ✓
     - ✓
     - ✓
   * - **SQLAlchemy ORM**
     -
     - ✓
     - ✓
     - ✓
   * - **from_model()**
     -
     - ✓
     - ✓
     - ✓
   * - **Solution Persistence**
     -
     - ✓
     - ✓
     - ✓
   * - **Teacher Seniority**
     -
     -
     - ✓
     - ✓
   * - **Goal Programming**
     -
     -
     - ✓
     - ✓
   * - **Priority Levels**
     -
     -
     - ✓
     - ✓
   * - **Room Types**
     -
     -
     -
     - ✓
   * - **Realistic Scale**
     -
     -
     -
     - ✓
   * - **Cached Checkers**
     -
     - Basic
     -
     - Advanced

Learning Path
-------------

For Beginners
~~~~~~~~~~~~~

**Start with Step 1** to learn:

- Basic LumiX modeling patterns
- Multi-dimensional indexing concepts
- Constraint formulation techniques
- Solution interpretation

Then progress sequentially through all steps.

For Intermediate Users
~~~~~~~~~~~~~~~~~~~~~~

**Skip to Step 2** if you already know LumiX basics and want to learn:

- Database integration patterns
- ORM-driven optimization
- Data persistence strategies
- Scalable data management

For Advanced Users
~~~~~~~~~~~~~~~~~~

**Jump to Step 3** to focus on:

- Goal programming techniques
- Multi-objective optimization
- Priority-based scheduling
- Trade-off analysis

Or **go directly to Step 4** for:

- Production-scale optimization
- Performance optimization patterns
- Complex constraint systems
- Real-world deployment strategies

Prerequisites
-------------

**Required:**

- Python 3.10 or higher
- Basic Python knowledge (classes, functions, loops)
- LumiX installed with a solver

**Optional:**

- Linear programming concepts (helpful but not required)
- SQLAlchemy familiarity (for database steps)
- Optimization theory (for goal programming)

Installation
~~~~~~~~~~~~

.. code-block:: bash

   # Install LumiX with OR-Tools solver (recommended for beginners)
   pip install lumix ortools

   # OR install with other solvers
   pip install lumix gurobi-solver  # Commercial/Academic
   pip install lumix cplex-solver   # Commercial/Academic

   # Install SQLAlchemy for database steps
   pip install sqlalchemy

Key Concepts Demonstrated
--------------------------

1. Multi-Dimensional Indexing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Variables indexed by **tuples of three models**:

.. literalinclude:: ../../../../tutorials/timetabling/step1_basic_timetabling/timetabling.py
   :language: python
   :lines: 110-122
   :dedent: 4

**Benefits**: Type-safe access, natural problem representation, IDE support

2. Database-Driven Models
~~~~~~~~~~~~~~~~~~~~~~~~~~

Direct integration with SQLAlchemy ORM:

.. literalinclude:: ../../../../tutorials/timetabling/step2_database_integration/timetabling_db.py
   :language: python
   :lines: 87-98
   :dedent: 4

**Benefits**: Automatic data loading, type-safe queries, solution persistence

3. Goal Programming
~~~~~~~~~~~~~~~~~~~

Mix hard constraints with soft goals:

.. code-block:: python

   # Hard constraint (must satisfy)
   model.add_constraint(
       LXConstraint("lecture_coverage")
       .expression(expr)
       .eq()
       .rhs(1)
   )

   # Soft goal (minimize violation)
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

**Benefits**: Express preferences, priority-based conflict resolution, satisfaction tracking

4. Performance Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Cached checkers for efficient lookups:

.. code-block:: python

   # Create cached compatibility checker
   compatibility_checker = create_cached_compatibility_checker(session)

   assignment = LXVariable[...]("assignment")
       .where_multi(
           lambda lec, ts, room: compatibility_checker(lec, room)
       )

**Benefits**: 1000x+ speedup, handles realistic scales, production-ready

Real-World Applications
-----------------------

The patterns learned here apply to many scheduling problems:

Education
~~~~~~~~~

- University course scheduling (larger scale)
- Exam timetabling (student conflicts)
- Training session planning (instructor availability)
- Classroom allocation (building constraints)

Healthcare
~~~~~~~~~~

- Nurse rostering (shift preferences, workload)
- Operating room scheduling (surgeon availability)
- Clinic appointments (doctor preferences, patient priorities)
- Medical staff rotation (specialty requirements)

Business
~~~~~~~~

- Employee shift scheduling (availability, fairness)
- Meeting room booking (participant conflicts)
- Conference scheduling (speaker preferences)
- Service technician routing (skills, locations)

Transportation
~~~~~~~~~~~~~~

- Bus driver scheduling (routes, work hours)
- Airline crew rostering (regulations, preferences)
- Delivery route planning (time windows)
- Fleet management (maintenance, assignments)

Extension Ideas
---------------

After completing the tutorial:

Easy Extensions
~~~~~~~~~~~~~~~

1. Add more data (teachers, classes, lectures)
2. Change timeslot structure (more periods, different days)
3. Modify priority rules (different seniority calculation)
4. Add preference types (break times, consecutive periods)

Intermediate Extensions
~~~~~~~~~~~~~~~~~~~~~~~

1. Student preferences (morning vs. afternoon)
2. Room preferences (subjects prefer specific rooms)
3. Consecutive lectures (back-to-back classes)
4. Balanced workload (even distribution across days)

Advanced Extensions
~~~~~~~~~~~~~~~~~~~

1. Multiple buildings (travel time constraints)
2. Specialized equipment (labs, projectors, computers)
3. Web interface (Flask/Django for schedule management)
4. Automated updates (daily schedule adjustments)
5. Multi-week planning (semester or year-long schedules)

Common Pitfalls
---------------

Pitfall 1: Forgetting ``prepare_goal_programming()``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Error**: Goal programming doesn't work, all constraints treated as hard

**Solution**:

.. code-block:: python

   model.set_goal_mode("weighted")
   model.prepare_goal_programming()  # Don't forget this!
   solution = optimizer.solve(model)

Pitfall 2: Database Not Populated
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Error**: ``Database is empty!`` or ``No teachers found``

**Solution**: Run ``python sample_data.py`` first to populate the database

Pitfall 3: Variable Capture in Lambdas
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Error**: Wrong values in where clauses due to late binding

**Solution**: Capture variables by value:

.. code-block:: python

   # Wrong
   where=lambda lec, ts: lec.id == lecture.id  # Captures reference

   # Correct
   where=lambda lec, ts, current=lecture: lec.id == current.id  # Captures value

Pitfall 4: Inconsistent Data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Error**: Lectures reference non-existent teachers or classes

**Solution**: Use foreign key constraints in database to enforce consistency

Getting Help
------------

If you encounter issues:

1. **Check the README** in each step's directory
2. **Review the source code** with detailed comments
3. **Consult the API reference** for method documentation
4. **Read Common Pitfalls** sections
5. **Search GitHub issues** for similar problems
6. **Open a new issue** with code snippet and error message

Related Documentation
---------------------

User Guide
~~~~~~~~~~

- :doc:`/user-guide/indexing/multi-model` - Multi-dimensional indexing
- :doc:`/user-guide/utils/orm-integration` - ORM integration patterns
- :doc:`/user-guide/goal_programming/index` - Goal programming guide
- :doc:`/user-guide/solvers/index` - Solver selection and configuration

Examples
~~~~~~~~

- :doc:`/examples/driver_scheduling` - 2D multi-model indexing
- :doc:`/examples/goal_programming` - Goal programming basics
- :doc:`/examples/cpsat_assignment` - CP-SAT for scheduling

API Reference
~~~~~~~~~~~~~

- :doc:`/api/core/generated/lumix.core.variables.LXVariable` - Variable creation
- :doc:`/api/core/generated/lumix.core.model.LXModel` - Model building
- :doc:`/api/solvers/generated/lumix.solvers.base.LXOptimizer` - Solving models

Summary
-------

This tutorial has shown you:

✓ **Step 1**: Built a basic timetabling model with 3D multi-model indexing
✓ **Step 2**: Integrated SQLite database for persistent data storage
✓ **Step 3**: Added teacher preferences using goal programming with priorities
✓ **Step 4**: Scaled to production size with room type constraints

You've learned:

- Multi-dimensional variable indexing patterns
- Complex constraint formulation techniques
- Database integration with SQLAlchemy ORM
- Multi-objective optimization with goal programming
- Priority-based decision making
- Performance optimization for large-scale problems
- Solution analysis and interpretation

These skills transfer to many real-world optimization problems. Happy optimizing!

---

**Tutorial Version**: 1.0

**LumiX Version**: Compatible with LumiX 0.1.0+

**Last Updated**: 2025-01-24
