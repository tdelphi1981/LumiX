Step 2: Database Integration
===============================

Overview
--------

This step extends Step 1 by integrating SQLAlchemy ORM for data storage and demonstrates LumiX's ``from_model()`` method for direct ORM integration.

**What's New in Step 2:**

- SQLite database for persistent storage
- SQLAlchemy declarative ORM models
- LumiX's ``from_model()`` for automatic data loading
- Solution persistence to database
- Cached compatibility checkers for performance

**Prerequisites:**

.. code-block:: bash

   pip install lumix ortools sqlalchemy

Problem Description
-------------------

Same as Step 1 - assign lectures to timeslots and classrooms while respecting scheduling constraints. The key difference is **ORM integration**:

- SQLAlchemy declarative models instead of Python lists
- LumiX queries database directly using ``from_model(session)``
- Solution saved back to database using ORM
- Type-safe database operations with IDE support

Key Features Demonstrated
--------------------------

1. ORM Integration with SQLAlchemy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Using declarative models for type-safe database operations.

2. from_model() Usage
~~~~~~~~~~~~~~~~~~~~~

LumiX queries the database directly:

.. literalinclude:: ../../../../tutorials/timetabling/step2_database_integration/timetabling_db.py
   :language: python
   :lines: 87-98
   :dedent: 4

3. Solution Persistence
~~~~~~~~~~~~~~~~~~~~~~~

Save optimization results back to the database via ORM session.

4. Cached Compatibility Checker
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Avoid redundant database queries with caching:

.. literalinclude:: ../../../../tutorials/timetabling/step2_database_integration/database.py
   :language: python
   :pyobject: create_cached_class_fits_checker

Database Schema
---------------

The database contains 7 tables:

1. **teachers** - Teacher information
2. **classrooms** - Classroom with capacity
3. **classes** - Student classes with size
4. **subjects** - Course subjects
5. **lectures** - Individual teaching sessions
6. **timeslots** - Available scheduling slots
7. **schedule_assignments** - Optimized schedule solutions

ORM Models
~~~~~~~~~~

.. literalinclude:: ../../../../tutorials/timetabling/step2_database_integration/database.py
   :language: python
   :lines: 52-78
   :dedent: 0

Running the Example
-------------------

Step 1: Populate Database
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   cd tutorials/timetabling/step2_database_integration
   python sample_data.py

Step 2: Run Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   python timetabling_db.py

Expected Output
~~~~~~~~~~~~~~~

1. Database initialization messages
2. Data loading confirmation
3. Model building progress
4. Solution status
5. Teacher and class timetables
6. Solution saved to database confirmation

Code Walkthrough
----------------

1. Initialize Database
~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../../tutorials/timetabling/step2_database_integration/timetabling_db.py
   :language: python
   :lines: 274-277
   :dedent: 4

2. Create Variables with from_model()
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../../tutorials/timetabling/step2_database_integration/timetabling_db.py
   :language: python
   :lines: 87-98
   :dedent: 4

3. Build Constraints (Same as Step 1)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Constraint logic remains the same, but data comes from database instead of Python lists.

4. Save Solution to Database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../../tutorials/timetabling/step2_database_integration/timetabling_db.py
   :language: python
   :pyobject: save_solution_to_db

Key Learnings
-------------

Benefits of ORM Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Type Safety**: IDE autocomplete for model attributes
- **Data Persistence**: Solutions saved automatically
- **Scalability**: Handle larger datasets efficiently
- **Maintainability**: Schema changes managed via migrations
- **Testability**: Mock database sessions for unit tests

Performance Optimization
~~~~~~~~~~~~~~~~~~~~~~~~

The cached compatibility checker provides significant performance improvements:

- **Without caching**: O(n) database queries per variable
- **With caching**: O(1) lookups after initial load
- **Speedup**: 100x+ for large problems

Next Steps
----------

After completing Step 2, proceed to:

- **Step 3** (:doc:`step3_goals`) - Add teacher preferences using goal programming
- **Step 4** (:doc:`step4_scaled`) - Scale to production-ready size

See Also
--------

**Related User Guide:**

- :doc:`/user-guide/utils/orm-integration` - ORM integration patterns
- :doc:`/user-guide/indexing/multi-model` - Multi-dimensional indexing

**API Reference:**

- :doc:`/api/utils/generated/lumix.utils.orm.LXORMContext` - ORM integration utilities

---

**Tutorial Step 2 Complete!**

You've learned how to integrate LumiX with SQLAlchemy ORM for database-driven optimization. Now move on to :doc:`step3_goals` to add goal programming.
