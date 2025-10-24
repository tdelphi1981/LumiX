CP-SAT Assignment Example
==========================

Overview
--------

This example demonstrates using **OR-Tools CP-SAT** (Constraint Programming) solver with LumiX for combinatorial optimization. CP-SAT excels at pure integer and binary problems like assignment, scheduling, and routing.

The worker-task assignment problem optimally assigns tasks to workers to minimize total cost while respecting capacity constraints.

Problem Description
-------------------

Assign tasks to workers to minimize total cost while respecting constraints.

**Objective**: Minimize total assignment cost.

**Constraints**:

- Task coverage: Each task assigned to exactly one worker
- Worker capacity: Each worker has maximum number of tasks they can handle
- Skill matching: Costs vary based on worker-task compatibility

Mathematical Formulation
------------------------

**Decision Variables**:

.. math::

   x_{w,t} \in \{0,1\}, \quad \forall w \in \text{Workers}, t \in \text{Tasks}

where :math:`x_{w,t} = 1` if worker :math:`w` is assigned to task :math:`t`.

**Objective Function**:

.. math::

   \text{Minimize} \quad \sum_{w \in \text{Workers}} \sum_{t \in \text{Tasks}}
   \text{cost}_{w,t} \cdot x_{w,t}

where :math:`\text{cost}_{w,t} = \text{hourly\_rate}_w \times \text{duration}_t \times \text{skill\_factor}`.

**Constraints**:

1. **Task Coverage** (exactly one worker per task):

   .. math::

      \sum_{w \in \text{Workers}} x_{w,t} = 1, \quad \forall t \in \text{Tasks}

2. **Worker Capacity**:

   .. math::

      \sum_{t \in \text{Tasks}} x_{w,t} \leq \text{max\_tasks}_w,
      \quad \forall w \in \text{Workers}

Key Features
------------

Binary Assignment Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Multi-indexed binary variables for (worker, task) pairs:

.. literalinclude:: ../../../examples/05_cpsat_assignment/cpsat_assignment.py
   :language: python
   :lines: 50-58

**Key Points**:

- CP-SAT requires integer variables (use ``.binary()`` not ``.continuous()``)
- Cartesian product creates one variable per (worker, task) pair
- Efficient for combinatorial optimization

Equality Constraints
~~~~~~~~~~~~~~~~~~~~

Each task assigned to exactly one worker:

.. literalinclude:: ../../../examples/05_cpsat_assignment/cpsat_assignment.py
   :language: python
   :lines: 76-86

The ``.eq().rhs(1)`` ensures exactly one assignment per task.

Integer Cost Coefficients
~~~~~~~~~~~~~~~~~~~~~~~~~~

CP-SAT works best with integer coefficients:

.. code-block:: python

   def get_assignment_cost(worker: Worker, task: Task) -> int:
       base_cost = worker.hourly_rate * task.duration_hours

       # Skill matching bonus/penalty
       if task.required_skill in worker.skills:
           return int(base_cost * 0.8)  # 20% discount
       else:
           return int(base_cost * 1.2)  # 20% penalty

CP-SAT Solver Options
~~~~~~~~~~~~~~~~~~~~~

Configure CP-SAT solver parameters:

.. code-block:: python

   solution = optimizer.solve(
       model,
       time_limit=10.0,           # Maximum solve time (seconds)
       num_search_workers=4,      # Parallel search threads
       log_search_progress=True   # Display search progress
   )

Running the Example
-------------------

**Prerequisites**:

.. code-block:: bash

   pip install lumix
   pip install ortools

**Run**:

.. code-block:: bash

   cd examples/05_cpsat_assignment
   python cpsat_assignment.py

**Expected Output**:

.. code-block:: text

   ======================================================================
   LumiX Example: Worker-Task Assignment with CP-SAT
   ======================================================================

   Workers:
   ----------------------------------------------------------------------
     Alice       : $50/hr, max 3 tasks
     Bob         : $40/hr, max 4 tasks
     Charlie     : $60/hr, max 2 tasks

   Tasks:
   ----------------------------------------------------------------------
     Database Migration       : 8h, priority 9/10
     API Development          : 12h, priority 8/10
     UI Redesign              : 6h, priority 7/10

   ======================================================================
   SOLUTION
   ======================================================================
   Status: OPTIMAL
   Total Cost: $1,680
   Solve Time: 0.123s

   Optimal Assignment:
   ----------------------------------------------------------------------
     Alice        → Database Migration        (8h, $320)
     Alice        → UI Redesign               (6h, $240)
     Bob          → API Development           (12h, $384)
     Charlie      → Testing & QA              (10h, $480)

   Worker Utilization:
   ----------------------------------------------------------------------
     Alice       : 2/3 tasks ( 66.7% capacity)
     Bob         : 2/4 tasks ( 50.0% capacity)
     Charlie     : 1/2 tasks ( 50.0% capacity)

Complete Code Walkthrough
--------------------------

Step 1: Create Assignment Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/05_cpsat_assignment/cpsat_assignment.py
   :language: python
   :lines: 50-58

Step 2: Set Objective
~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/05_cpsat_assignment/cpsat_assignment.py
   :language: python
   :lines: 64-69

Step 3: Add Task Coverage Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/05_cpsat_assignment/cpsat_assignment.py
   :language: python
   :lines: 73-86

Step 4: Add Worker Capacity Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/05_cpsat_assignment/cpsat_assignment.py
   :language: python
   :lines: 90-103

Step 5: Solve and Access Solution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   optimizer = LXOptimizer().use_solver("cpsat")
   solution = optimizer.solve(model)

   # Access multi-indexed assignments
   for (worker_id, task_id), value in solution.get_mapped(assignment).items():
       if value > 0.5:  # Binary variable is "on"
           worker = worker_by_id[worker_id]
           task = task_by_id[task_id]
           print(f"{worker.name} → {task.name}")

Learning Objectives
-------------------

After completing this example, you should understand:

1. **CP-SAT Solver**: When and why to use constraint programming
2. **Binary Assignment**: Modeling assignment problems with 0/1 variables
3. **Equality Constraints**: Using ``.eq()`` for exact assignment requirements
4. **Integer Costs**: Working with integer coefficients for CP-SAT
5. **Solver Options**: Configuring time limits and parallel search
6. **Solution Interpretation**: Extracting assignments from binary solutions

Common Patterns
---------------

Pattern 1: Binary Assignment Matrix
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   assignment = (
       LXVariable[Tuple[A, B], int]("assignment")
       .binary()
       .indexed_by_product(
           LXIndexDimension(A, lambda a: a.id).from_data(DATA_A),
           LXIndexDimension(B, lambda b: b.id).from_data(DATA_B)
       )
   )

Pattern 2: Exactly-One Constraint
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Each B assigned to exactly one A
   for b in B_SET:
       expr = LXLinearExpression().add_multi_term(
           assignment,
           coeff=lambda a, b_var: 1.0,
           where=lambda a, b_var: b_var.id == b.id
       )
       model.add_constraint(
           LXConstraint(f"coverage_{b.id}")
           .expression(expr)
           .eq()
           .rhs(1)
       )

Pattern 3: Capacity Constraint
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Each A can handle at most max[a] items from B
   for a in A_SET:
       expr = LXLinearExpression().add_multi_term(
           assignment,
           coeff=lambda a_var, b: 1.0,
           where=lambda a_var, b: a_var.id == a.id
       )
       model.add_constraint(
           LXConstraint(f"capacity_{a.id}")
           .expression(expr)
           .le()
           .rhs(a.max_items)
       )

CP-SAT vs Linear Programming
-----------------------------

When to Use CP-SAT
~~~~~~~~~~~~~~~~~~

**Use CP-SAT when**:

- ✓ Pure integer/binary variables (no continuous)
- ✓ Combinatorial optimization (assignment, scheduling, routing)
- ✓ Logical constraints (AllDifferent, Circuit)
- ✓ Small to medium problems

**Use LP/MIP when**:

- ✗ Continuous variables needed
- ✗ Very large linear programs
- ✗ Need continuous relaxations

Performance Comparison
~~~~~~~~~~~~~~~~~~~~~~

+------------------+----------------+------------------+
| Problem Size     | CP-SAT         | MIP Solver       |
+==================+================+==================+
| Small (< 100)    | Very Fast      | Very Fast        |
+------------------+----------------+------------------+
| Medium (100-10k) | Fast           | Fast to Medium   |
+------------------+----------------+------------------+
| Large (> 10k)    | Slow           | Variable         |
+------------------+----------------+------------------+

Extending the Example
---------------------

Try These Modifications
~~~~~~~~~~~~~~~~~~~~~~~

1. **Add Skill Requirements**: Multiple skills per task

   .. code-block:: python

      .where_multi(lambda w, t: t.required_skill in w.skills)

2. **Precedence Constraints**: Some tasks must complete before others
3. **Team Assignments**: Assign groups of workers to tasks
4. **Time Windows**: Tasks must be done in certain periods
5. **Preferences**: Soft constraints for worker preferences

Next Steps
----------

After mastering this example:

1. **Example 02 (Driver Scheduling)**: Multi-model indexing foundation
2. **Example 03 (Facility Location)**: Mixed-integer with Big-M
3. **CP-SAT Documentation**: OR-Tools CP-SAT advanced features

See Also
--------

**Related Examples**:

- :doc:`driver_scheduling` - Multi-model indexing with binary variables
- :doc:`facility_location` - Mixed-integer programming
- :doc:`production_planning` - Single-model indexing basics

**API Reference**:

- :class:`lumix.core.variables.LXVariable`
- :class:`lumix.solvers.cpsat.CPSATSolver`
- :class:`lumix.core.model.LXModel`

**External Resources**:

- `OR-Tools CP-SAT Documentation <https://developers.google.com/optimization/cp/cp_solver>`_
- Hungarian Algorithm for Assignment Problems

Files in This Example
---------------------

- ``cpsat_assignment.py`` - Main optimization model and solution display
- ``sample_data.py`` - Data models (Worker, Task) and cost calculations
- ``README.md`` - Detailed documentation and usage guide
