Step 4: Large-Scale Optimization with Room Types
==================================================

Overview
--------

This step demonstrates LumiX's capability to handle realistic large-scale problems efficiently while introducing room type constraints for specialized classrooms.

**What's New in Step 4:**

- **3x Scale Increase**: 15 teachers, 12 classrooms, 12 classes, 80 lectures, 40 timeslots
- **Room Type Constraints**: REGULAR, LAB, GYM for specialized facilities
- **Enhanced Performance**: Cached compatibility checker combining capacity and room type checks
- **Production-Ready**: Realistic high school size with 16x more variables

**Prerequisites:**

.. code-block:: bash

   pip install lumix ortools sqlalchemy

Problem Scale Comparison
-------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 15

   * - Metric
     - Step 3
     - Step 4
     - Multiplier
   * - Teachers
     - 5
     - 15
     - 3x
   * - Classrooms
     - 4
     - 12
     - 3x
   * - Classes
     - 4
     - 12
     - 3x
   * - Lectures
     - 20
     - 80
     - 4x
   * - Timeslots
     - 30
     - 40
     - 1.3x
   * - Variables
     - ~2,400
     - ~38,400
     - 16x
   * - Constraints
     - ~150
     - ~600
     - 4x
   * - Preferences
     - 7
     - 35
     - 5x

**Key Point**: Despite 16x more variables, LumiX solves this efficiently with proper caching.

Room Type System
----------------

Room Types
~~~~~~~~~~

- **REGULAR**: Standard classrooms for most subjects
- **LAB**: Science laboratories for Chemistry, Physics, Biology
- **GYM**: Gymnasium for Physical Education

Compatibility Rules
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def check_room_type_compatible(subject_id, classroom_id):
       """
       Rules:
       - Lab subjects (Chemistry, Physics, Biology) → Must use LAB rooms
       - PE → Must use GYM
       - Other subjects → Can use REGULAR or LAB rooms (not GYM)
       """

Database Schema Extensions
---------------------------

Updated Models
~~~~~~~~~~~~~~

**Classroom** with ``room_type``:

.. literalinclude:: ../../../../tutorials/timetabling/step4_scaled_up/database.py
   :language: python
   :lines: 86-113
   :dedent: 0

**Subject** with ``requires_lab``:

.. literalinclude:: ../../../../tutorials/timetabling/step4_scaled_up/database.py
   :language: python
   :lines: 133-151
   :dedent: 0

Cached Compatibility Checker
-----------------------------

The key performance optimization:

.. literalinclude:: ../../../../tutorials/timetabling/step4_scaled_up/database.py
   :language: python
   :pyobject: create_cached_compatibility_checker

**Performance Impact:**

- Without caching: ~192,000 database queries
- With caching: ~27 queries (12 classes + 12 rooms + 8 subjects)
- Speedup: ~7,000x faster

Problem Structure
-----------------

Teachers (15 total)
~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 15 40

   * - Department
     - Count
     - Seniority Distribution
   * - Math & Science
     - 8
     - 3 senior, 2 mid-level, 3 junior
   * - Humanities
     - 5
     - 2 senior, 2 mid-level, 1 junior
   * - Physical Education
     - 2
     - 0 senior, 2 mid-level, 0 junior

Classrooms (12 total)
~~~~~~~~~~~~~~~~~~~~~~

- **8 Regular rooms**: Room 101, 102, 201, 202, 301, 302, 401, 402
- **3 Labs**: Chemistry Lab, Physics Lab, Biology Lab
- **1 Gym**: Main Gym

Subjects (8 total)
~~~~~~~~~~~~~~~~~~

- **Regular**: Mathematics, English, History, Geography
- **Lab-required**: Physics, Chemistry, Biology
- **Gym-required**: Physical Education

Running the Example
-------------------

Step 1: Populate Database
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   cd tutorials/timetabling/step4_scaled_up
   python sample_data.py

Step 2: Run Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   python timetabling_scaled.py

**Expected solve time**: 10-30 seconds (depending on hardware)

Expected Output
~~~~~~~~~~~~~~~

1. Database initialization with counts
2. Variable creation with filtering statistics
3. Constraint generation progress
4. Solve time and status
5. Teacher and class timetables
6. **Enhanced analytics**:
   - Hard constraint satisfaction (100%)
   - Soft goal satisfaction by priority level
   - Overall preference satisfaction rate

Code Walkthrough
----------------

1. Create Cached Compatibility Checker
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../../tutorials/timetabling/step4_scaled_up/timetabling_scaled.py
   :language: python
   :lines: 89-92
   :dedent: 4

2. Use in Variable Filtering
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../../tutorials/timetabling/step4_scaled_up/timetabling_scaled.py
   :language: python
   :lines: 95-109
   :dedent: 4

3. Same Constraint Logic
~~~~~~~~~~~~~~~~~~~~~~~~~

Constraint formulation remains the same - scalability comes from efficient data management.

Performance Benchmarks
-----------------------

Measured on typical laptop (8GB RAM, 4-core CPU):

.. list-table::
   :header-rows: 1
   :widths: 30 15 40

   * - Phase
     - Time
     - Notes
   * - Variable creation
     - ~2-3s
     - Including room type filtering
   * - Hard constraints
     - ~4-6s
     - 600+ constraints
   * - Soft constraints
     - ~1-2s
     - 35 goal constraints
   * - Model build
     - ~8-10s
     - Total preparation
   * - Solve
     - ~10-30s
     - OR-Tools CP-SAT
   * - **Total**
     - **~20-40s**
     - End-to-end

Solution Quality
----------------

Hard Constraints
~~~~~~~~~~~~~~~~

- ✅ **100% satisfied** (always)
- All lectures scheduled exactly once
- No room, teacher, or class conflicts
- All room type requirements met

Soft Constraints (Goals)
~~~~~~~~~~~~~~~~~~~~~~~~~

**By Priority:**

- Priority 1: 85-95% satisfaction (senior teachers)
- Priority 2: 70-85% satisfaction (mid-level)
- Priority 3: 60-75% satisfaction (junior teachers)

**Overall**: 75-85% of preferences satisfied

Scaling Guidelines
------------------

Make it Smaller (for testing)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # In sample_data.py, reduce:
   - Grades: 2 instead of 4 (e.g., only 9-10)
   - Classes per grade: 2 instead of 3 (only A, B)
   - Lectures per class: 5 instead of 7
   - Periods per day: 6 instead of 8

   Result: ~40 lectures, ~24 timeslots, ~5 teachers
   Solve time: <10 seconds

Make it Larger (more realistic)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # In sample_data.py, increase:
   - Classes per grade: 4 instead of 3 (add D section)
   - Lectures per class: 9 instead of 7 (more subjects)
   - Periods per day: 9 instead of 8

   Result: ~140 lectures, ~45 timeslots, ~20 teachers
   Solve time: 30-60 seconds

Scale to University Size
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Major changes needed:
   - 100+ courses
   - 50+ instructors
   - 30+ rooms
   - Multiple buildings (add travel time constraints)

   Result: ~300 lectures, ~50 timeslots, ~50 instructors
   Solve time: 1-5 minutes
   Recommendation: CP-SAT with time limit

Key Takeaways
-------------

After completing Step 4, you should understand:

1. **Scalability**: LumiX handles realistic-sized problems efficiently with proper patterns
2. **Room Types**: Specialized resource constraints are straightforward to model
3. **Performance**: Caching is crucial when generating thousands of variables
4. **Goal Programming**: Scales well - can handle 100+ soft constraints
5. **Production Ready**: This size (80 lectures, 15 teachers) is suitable for small-to-medium schools

Next Steps
----------

Apply to Your Domain
~~~~~~~~~~~~~~~~~~~~

The patterns learned here apply to many scheduling problems:

- **University Course Scheduling**: Scale up to 300+ courses
- **Employee Shift Scheduling**: Add shift types, labor rules
- **Conference Scheduling**: Add speaker availability, session tracks
- **Operating Room Scheduling**: Add surgeon skills, equipment requirements

See Also
--------

**Related User Guide:**

- :doc:`/user-guide/indexing/filtering` - Advanced filtering techniques
- :doc:`/user-guide/solvers/solver-configuration` - Solver tuning for large problems

**Related Examples:**

- :doc:`/examples/facility_location` - Large-scale optimization example

---

**Tutorial Complete!**

You've completed the entire High School Course Timetabling tutorial and learned:

- Multi-dimensional indexing patterns
- Database integration with SQLAlchemy ORM
- Goal programming for multi-objective optimization
- Performance optimization for production-scale problems

Apply these patterns to your own scheduling and optimization problems!
