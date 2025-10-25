Tutorials
=========

Comprehensive step-by-step tutorials that teach you how to build real-world optimization solutions using LumiX. Each tutorial progresses from basic concepts to production-ready implementations.

Overview
--------

LumiX tutorials provide guided learning experiences that combine theory, code, and practical insights. Unlike standalone examples, tutorials build progressively, teaching you not just **what** to do, but **why** and **how** to apply LumiX features in realistic scenarios.

**What makes tutorials different from examples:**

- **Progressive Learning**: Each step builds on previous knowledge
- **Production Focus**: Learn patterns for real-world deployment
- **Comprehensive Coverage**: From basic modeling to advanced features
- **Best Practices**: Industry-standard approaches and optimizations

Available Tutorials
-------------------

.. toctree::
   :maxdepth: 2

   timetabling/index
   production_planning/index

High School Course Timetabling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A comprehensive 4-step tutorial demonstrating how to build a complete course timetabling solution for a high school, progressing from basic optimization to large-scale production-ready systems.

**What You'll Learn:**

- Multi-dimensional indexing with 3D variables (Lecture × TimeSlot × Classroom)
- Database integration with SQLAlchemy ORM
- Goal programming for multi-objective optimization
- Scaling to realistic problem sizes with performance optimization
- Room type constraints for specialized facilities

**Tutorial Steps:**

1. **Basic Timetabling** (:doc:`timetabling/step1_basic`) - Core optimization with multi-model indexing
2. **Database Integration** (:doc:`timetabling/step2_database`) - Persistent storage with SQLite and SQLAlchemy
3. **Goal Programming** (:doc:`timetabling/step3_goals`) - Teacher preferences with priority-based scheduling
4. **Large-Scale Optimization** (:doc:`timetabling/step4_scaled`) - Production-ready size with room type constraints

**Tutorial Path:**

.. code-block:: text

   Step 1: Basic Model          Step 2: Add Database     Step 3: Add Goals        Step 4: Scale Up
   ├─ 5 teachers               ├─ SQLite storage        ├─ Teacher preferences   ├─ 15 teachers
   ├─ 4 classrooms             ├─ SQLAlchemy ORM        ├─ Seniority priorities  ├─ 12 classrooms
   ├─ 20 lectures              ├─ from_model()          ├─ Weighted goals        ├─ 80 lectures
   ├─ 30 timeslots             ├─ Solution persistence  ├─ Satisfaction analysis ├─ Room types
   └─ Python data structures   └─ CRUD operations       └─ Goal programming      └─ 16x larger scale

**Prerequisites:**

- Basic Python knowledge (dataclasses, functions, loops)
- Understanding of linear programming concepts helpful but not required
- LumiX installed with a solver (OR-Tools recommended for beginners)

**Time to Complete:** 2-4 hours for all steps

---

Manufacturing Production Planning
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A comprehensive 3-step tutorial demonstrating how to build production planning solutions for manufacturing, progressing from basic continuous variable optimization to advanced goal programming with customer order priorities.

**What You'll Learn:**

- Continuous variables for quantity optimization (vs. binary for assignments)
- Resource consumption constraints (machines, materials)
- Profit maximization objectives
- Database integration with Bill of Materials (BOM) structure
- Goal programming for customer order fulfillment with tier-based priorities
- Multi-objective optimization balancing profit and customer satisfaction

**Tutorial Steps:**

1. **Basic Production Planning** - Core optimization with continuous variables and resource constraints
2. **Database Integration** - Persistent storage with SQLite for products, machines, materials, and BOM
3. **Goal Programming** - Customer orders as soft constraints with priority-based fulfillment

**Tutorial Path:**

.. code-block:: text

   Step 1: Basic Model         Step 2: Add Database      Step 3: Add Goals
   ├─ 3 products              ├─ SQLite storage         ├─ 5 customers (Gold/Silver/Bronze)
   ├─ 2 machines              ├─ BOM tables             ├─ 9 customer orders
   ├─ 3 materials             ├─ Recipe relationships   ├─ Tier-based priorities
   ├─ Continuous variables    ├─ Solution persistence   ├─ Order fulfillment analysis
   ├─ Profit maximization     ├─ CRUD operations        ├─ Weighted goal programming
   └─ Python data structures  └─ Database queries       └─ Satisfaction tracking

**Prerequisites:**

- Basic Python knowledge (dataclasses, functions, loops)
- Understanding of linear programming helpful but not required
- LumiX installed with a solver (OR-Tools recommended)

**Time to Complete:** 2-3 hours for all steps

Quick Start
-----------

**Step 1: Install Prerequisites**

.. code-block:: bash

   # Install LumiX with OR-Tools solver
   pip install lumix ortools

   # Optional: Install SQLAlchemy for database steps
   pip install sqlalchemy

**Step 2: Navigate to Tutorials**

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/lumix/lumix.git
   cd lumix

   # Navigate to tutorials
   cd tutorials/timetabling

**Step 3: Choose Your Starting Point**

- **Complete Beginner?** Start with :doc:`timetabling/step1_basic`
- **Know LumiX basics?** Jump to :doc:`timetabling/step2_database`
- **Ready for advanced features?** Try :doc:`timetabling/step3_goals`
- **Want production-ready patterns?** Go to :doc:`timetabling/step4_scaled`

Learning Path
-------------

Recommended Tutorial Sequence
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For New Users
^^^^^^^^^^^^^

1. **Read** :doc:`/getting-started/quickstart` to understand LumiX basics
2. **Try** :doc:`/examples/basic_lp` for a simple example
3. **Start** with :doc:`timetabling/step1_basic`
4. **Progress** through all 4 steps sequentially

For Intermediate Users
^^^^^^^^^^^^^^^^^^^^^^

1. **Review** :doc:`/user-guide/indexing/multi-model` for multi-dimensional indexing
2. **Start** with :doc:`timetabling/step1_basic` to see 3D indexing in action
3. **Skip** to :doc:`timetabling/step2_database` if you already understand multi-model variables
4. **Focus** on :doc:`timetabling/step3_goals` and :doc:`timetabling/step4_scaled` for advanced features

For Advanced Users
^^^^^^^^^^^^^^^^^^

1. **Skim** :doc:`timetabling/step1_basic` and :doc:`timetabling/step2_database`
2. **Study** :doc:`timetabling/step3_goals` for goal programming patterns
3. **Analyze** :doc:`timetabling/step4_scaled` for performance optimization techniques
4. **Adapt** the patterns to your specific problem domain

Key Concepts Covered
---------------------

Multi-Dimensional Indexing
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Variables indexed by tuples of multiple models:

.. code-block:: python

   # 3D indexing: (Lecture, TimeSlot, Classroom)
   assignment = LXVariable[Tuple[Lecture, TimeSlot, Classroom], int]("assignment")
       .binary()
       .indexed_by_product(
           LXIndexDimension(Lecture, lambda lec: lec.id).from_data(lectures),
           LXIndexDimension(TimeSlot, lambda ts: ts.id).from_data(timeslots),
           LXIndexDimension(Classroom, lambda room: room.id).from_data(classrooms),
       )

**Benefits:**

- Type-safe variable access
- Natural problem representation
- IDE autocomplete support
- Semantic meaning preserved

ORM Integration
~~~~~~~~~~~~~~~

Direct database integration using LumiX's ``from_model()`` method:

.. code-block:: python

   # Query database directly
   assignment = LXVariable[...]("assignment")
       .indexed_by_product(
           LXIndexDimension(Lecture, lambda lec: lec.id).from_model(session),
           LXIndexDimension(TimeSlot, lambda ts: ts.id).from_model(session),
           LXIndexDimension(Classroom, lambda room: room.id).from_model(session),
       )

**Benefits:**

- Automatic data loading from database
- Type-safe ORM operations
- Solution persistence
- Scalable data management

Goal Programming
~~~~~~~~~~~~~~~~

Multi-objective optimization with soft constraints:

.. code-block:: python

   # Hard constraint (must satisfy)
   model.add_constraint(
       LXConstraint("lecture_coverage").expression(expr).eq().rhs(1)
   )

   # Soft goal (minimize violation with priority)
   model.add_constraint(
       LXConstraint("teacher_preference")
       .expression(expr)
       .le()
       .rhs(0)
       .as_goal(priority=1, weight=1.0)  # Priority 1 = highest
   )

   # Prepare and solve
   model.set_goal_mode("weighted")
   model.prepare_goal_programming()

**Benefits:**

- Express preferences as soft constraints
- Priority-based conflict resolution
- Automatic deviation tracking
- Satisf satisfaction analysis

Performance Optimization
~~~~~~~~~~~~~~~~~~~~~~~~

Patterns for scaling to production sizes:

.. code-block:: python

   # Cached compatibility checker (avoid redundant DB queries)
   compatibility_checker = create_cached_compatibility_checker(session)

   assignment = LXVariable[...]("assignment")
       .where_multi(
           lambda lec, ts, room: compatibility_checker(lec, room)
       )

**Benefits:**

- 1000x+ speedup with caching
- Efficient constraint generation
- Handles realistic problem sizes
- Production-ready performance

Real-World Applications
-----------------------

The patterns learned in these tutorials apply to many optimization problems:

Education & Training
~~~~~~~~~~~~~~~~~~~~

- **University Course Scheduling**: Larger scale with complex requirements
- **Exam Timetabling**: Student conflict resolution, resource constraints
- **Training Session Planning**: Instructor availability, equipment needs
- **Classroom Allocation**: Building constraints, travel time

Healthcare
~~~~~~~~~~

- **Nurse Rostering**: Shift preferences, workload balancing, regulations
- **Operating Room Scheduling**: Surgeon availability, equipment, sterilization time
- **Clinic Appointment Scheduling**: Doctor preferences, patient priorities
- **Medical Staff Rotation**: Specialty requirements, experience levels

Business & Services
~~~~~~~~~~~~~~~~~~~

- **Employee Shift Scheduling**: Availability, workload fairness, labor rules
- **Meeting Room Booking**: Participant conflicts, resource limits, preferences
- **Conference Scheduling**: Speaker availability, session tracks, room capacity
- **Service Technician Routing**: Skills, locations, time windows

Transportation & Logistics
~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Bus Driver Scheduling**: Route assignments, work hour limits, preferences
- **Airline Crew Rostering**: Regulations, preferences, experience, locations
- **Delivery Route Planning**: Vehicle capacity, time windows, driver skills
- **Fleet Management**: Maintenance schedules, driver assignments

Tutorial Features
-----------------

Each tutorial includes:

✅ **Complete Source Code** - Fully functional, well-commented code
✅ **Sample Data** - Representative datasets for testing
✅ **Step-by-Step Walkthrough** - Detailed explanations of each component
✅ **Mathematical Formulations** - LaTeX equations and constraint descriptions
✅ **Solution Interpretation** - How to read and use optimization results
✅ **README Files** - Quick reference in each tutorial directory
✅ **Extension Ideas** - Suggestions for adapting to your needs
✅ **Common Pitfalls** - Known issues and how to avoid them
✅ **API Cross-References** - Links to relevant LumiX documentation

Coming Soon
-----------

Future tutorials will cover:

- **Logistics & Routing**: Vehicle routing with time windows
- **Portfolio Optimization**: Financial modeling with risk constraints
- **Energy Management**: Power generation scheduling with renewables
- **Supply Chain**: Multi-echelon inventory optimization
- **Blending Problems**: Chemical mixing and recipe optimization

Contributing
------------

Have a tutorial idea? We welcome contributions!

1. **Open an issue** to discuss your tutorial concept
2. **Follow the tutorial structure** (progressive steps, comprehensive docs)
3. **Include sample data** and clear comments
4. **Test thoroughly** to ensure reproducibility
5. **Submit a pull request** with complete documentation

Getting Help
------------

If you encounter issues while following tutorials:

1. **Check the README** in each tutorial directory
2. **Review Common Pitfalls** sections in the documentation
3. **Consult the API Reference** for detailed method documentation
4. **Search existing issues** on GitHub
5. **Open a new issue** with a clear description and code snippet

Next Steps
----------

Ready to start learning?

1. **Install LumiX** following :doc:`/getting-started/installation`
2. **Read the quickstart** at :doc:`/getting-started/quickstart`
3. **Choose your tutorial** from the list above
4. **Code along** and experiment with modifications
5. **Apply what you learned** to your own problems

.. seealso::

   - :doc:`/examples/index` - Standalone examples of specific features
   - :doc:`/user-guide/index` - Comprehensive feature documentation
   - :doc:`/api/index` - Complete API reference
   - :doc:`/development/index` - Contributing guidelines
