Goal Programming Example
=========================

Overview
--------

This example demonstrates LumiX's built-in **goal programming** support, which allows automatic conversion of hard constraints into soft constraints (goals) that can be violated with penalties.

Goal programming enables multi-objective optimization by prioritizing multiple conflicting goals and minimizing deviations from target values.

Problem Description
-------------------

A company produces products with multiple conflicting objectives:

**Goals** (soft constraints that can be violated):

1. Meet minimum production targets (Priority 1 - highest)
2. Limit overtime hours (Priority 2 - medium)
3. Achieve target profit (Priority 3 - lowest)

**Hard Constraints** (must be satisfied):

- Total hours ≤ capacity + overtime

**Challenge**: Traditional LP requires choosing one objective. Goal programming allows pursuing multiple goals simultaneously with priorities.

Mathematical Formulation
------------------------

**Traditional LP** (Single Objective):

.. math::

   \text{Maximize} \quad \text{profit} \\
   \text{subject to:} \quad \text{production} \geq \text{target}

**Goal Programming** (Multiple Goals):

.. math::

   \text{Minimize} \quad \sum_{p=1}^{P} w_p \sum_{g \in G_p} (d_g^+ + d_g^-)

**Subject to** (relaxed constraints):

.. math::

   \text{expr}_g + d_g^- - d_g^+ &= \text{rhs}_g \\
   d_g^+, d_g^- &\geq 0

where:

- :math:`d_g^+` = positive deviation (exceeding target)
- :math:`d_g^-` = negative deviation (falling short of target)
- :math:`w_p` = priority weight (e.g., :math:`10^6, 10^5, 10^4`)
- :math:`G_p` = goals at priority level :math:`p`

Goal Types
----------

Minimize Excess (LE Constraints)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For ``expr ≤ rhs`` goals, minimize :math:`d^+` (exceeding is bad):

.. code-block:: python

   model.add_constraint(
       LXConstraint("overtime_limit")
       .expression(overtime_expr)
       .le()
       .rhs(40)
       .as_goal(priority=2, weight=1.0)
   )

Minimize Shortfall (GE Constraints)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For ``expr ≥ rhs`` goals, minimize :math:`d^-` (falling short is bad):

.. code-block:: python

   model.add_constraint(
       LXConstraint("production_target")
       .expression(production_expr)
       .ge()
       .rhs(100)
       .as_goal(priority=1, weight=1.0)
   )

Minimize Both Deviations (EQ Constraints)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For ``expr = rhs`` goals, minimize both :math:`d^+` and :math:`d^-`:

.. code-block:: python

   model.add_constraint(
       LXConstraint("profit_target")
       .expression(profit_expr)
       .eq()
       .rhs(1800)
       .as_goal(priority=3, weight=1.0)
   )

Key Features
------------

Automatic Goal Relaxation
~~~~~~~~~~~~~~~~~~~~~~~~~~

Mark constraints as goals:

.. literalinclude:: ../../../examples/11_goal_programming/01_basic_goal_programming.py
   :language: python
   :lines: 105-112
   :dedent: 8

**Key Points**:

- ``.as_goal(priority, weight)`` marks constraint as soft
- Priority determines importance (1 = highest)
- Weight allows fine-tuning within priority level

Automatic Deviation Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

LumiX automatically creates deviation variables:

.. code-block:: python

   # For each goal, LumiX creates:
   # - goal_name_pos_dev (d⁺)
   # - goal_name_neg_dev (d⁻)

   # Original: production >= 100
   # Relaxed:  production + d⁻ - d⁺ = 100

Weighted vs Sequential Mode
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Weighted Mode** (default - single solve):

.. code-block:: python

   model.set_goal_mode("weighted")
   # Priorities converted to exponential weights:
   # P1: 10^6, P2: 10^5, P3: 10^4

**Sequential Mode** (multiple solves - true preemptive):

.. code-block:: python

   model.set_goal_mode("sequential")
   # Solve priorities lexicographically:
   # 1. Minimize P1 deviations
   # 2. Fix P1, minimize P2 deviations
   # 3. Fix P2, minimize P3 deviations

Solution Analysis
~~~~~~~~~~~~~~~~~

Check goal satisfaction:

.. literalinclude:: ../../../examples/11_goal_programming/01_basic_goal_programming.py
   :language: python
   :lines: 187-204
   :dedent: 4

Running the Example
-------------------

**Prerequisites**:

.. code-block:: bash

   pip install lumix
   pip install ortools  # or cplex, gurobi

**Run**:

.. code-block:: bash

   cd examples/11_goal_programming
   python 01_basic_goal_programming.py

**Expected Output**:

.. code-block:: text

   ======================================================================
   Basic Goal Programming Example
   ======================================================================

   Model Summary:
     Variables: 2 families + deviation variables
     Constraints: 1 hard + 7 goals
     Mode: weighted

   ======================================================================
   Solution
   ======================================================================
   Status: optimal
   Objective: 1234.56 (weighted deviations)

   ----------------------------------------------------------------------
   Production Plan:
   ----------------------------------------------------------------------
   Product A       :   105.00 units  (Target: 100.00)
   Product B       :    95.00 units  (Target: 80.00)

   Overtime        :    45.00 hours (Target: <=50.00)
   Total Profit    : $1,750.00 (Target: $1,800.00)

   ----------------------------------------------------------------------
   Goal Satisfaction:
   ----------------------------------------------------------------------
   Production Goal Product A: ✓ Satisfied
     Under-production: 0.00
     Over-production:  5.00

   Production Goal Product B: ✓ Satisfied
     Under-production: 0.00
     Over-production:  15.00

   Overtime Goal: ✓ Satisfied
     Under limit:  0.00
     Over limit:   0.00

   Profit Goal: ✗ Not Satisfied
     Under target: $50.00
     Over target:  $0.00

Complete Code Walkthrough
--------------------------

Step 1: Define Variables
~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/11_goal_programming/01_basic_goal_programming.py
   :language: python
   :lines: 66-82
   :dedent: 4

Step 2: Add Hard Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/11_goal_programming/01_basic_goal_programming.py
   :language: python
   :lines: 88-95
   :dedent: 4

Step 3: Add Goal Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/11_goal_programming/01_basic_goal_programming.py
   :language: python
   :lines: 99-137
   :dedent: 4

Step 4: Configure Goal Mode
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/11_goal_programming/01_basic_goal_programming.py
   :language: python
   :lines: 140-143
   :dedent: 4

Step 5: Solve and Analyze Goals
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/11_goal_programming/01_basic_goal_programming.py
   :language: python
   :lines: 149-157
   :dedent: 4

Learning Objectives
-------------------

After completing this example, you should understand:

1. **Multi-Objective Optimization**: Pursuing multiple goals simultaneously
2. **Soft Constraints**: Converting hard constraints to goals
3. **Deviation Variables**: How d⁺ and d⁻ represent violations
4. **Priority Levels**: Hierarchical goal importance
5. **Weighted Formulation**: Single-solve approximation of priorities
6. **Goal Satisfaction**: Analyzing which goals were achieved

Common Patterns
---------------

Pattern 1: Basic Goal Constraint
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   model.add_constraint(
       LXConstraint("goal_name")
       .expression(expr)
       .ge()  # or .le(), .eq()
       .rhs(target_value)
       .as_goal(priority=1, weight=1.0)
   )

Pattern 2: Multiple Priorities
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Priority 1 (highest - must achieve if possible)
   model.add_constraint(...).as_goal(priority=1, weight=1.0)

   # Priority 2 (second - achieve after P1)
   model.add_constraint(...).as_goal(priority=2, weight=1.0)

   # Priority 3 (lowest - nice to have)
   model.add_constraint(...).as_goal(priority=3, weight=1.0)

Pattern 3: Custom Objective (Priority 0)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Use priority 0 to incorporate custom objective
   model.add_constraint(
       LXConstraint("maximize_profit")
       .expression(profit_expr)
       .ge()
       .rhs(0)
       .as_goal(priority=0, weight=1.0)
   )

Pattern 4: Indexed Goals
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Goals for each entity
   for entity in ENTITIES:
       expr = LXLinearExpression().add_term(...)

       model.add_constraint(
           LXConstraint(f"goal_{entity.id}")
           .expression(expr)
           .ge()
           .rhs(entity.target)
           .as_goal(priority=1, weight=entity.importance)
       )

Priority Weighting
------------------

Weighted Mode Calculation
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Automatic weight calculation
   priority_weight = 10 ** (6 - priority)
   combined_weight = priority_weight * goal_weight

   # Examples:
   # P1, w=1.0: 10^6 × 1.0 = 1,000,000
   # P2, w=0.5: 10^5 × 0.5 =    50,000
   # P3, w=2.0: 10^4 × 2.0 =    20,000

This ensures higher priorities dominate in the objective function.

Custom Weights Within Priority
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Different weights within same priority
   model.add_constraint(...).as_goal(priority=1, weight=2.0)  # More important
   model.add_constraint(...).as_goal(priority=1, weight=1.0)  # Less important
   model.add_constraint(...).as_goal(priority=1, weight=0.5)  # Least important

Goal Satisfaction Analysis
---------------------------

Check Individual Goals
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Check if goal satisfied
   satisfied = solution.is_goal_satisfied("goal_name", tolerance=1e-6)

   # Get deviation values
   deviations = solution.get_goal_deviations("goal_name")
   pos_dev = deviations["pos"]  # Over-achievement
   neg_dev = deviations["neg"]  # Under-achievement

Indexed Goals
~~~~~~~~~~~~~

.. code-block:: python

   for entity in ENTITIES:
       goal_name = f"goal_{entity.id}"
       deviations = solution.get_goal_deviations(goal_name)

       # Deviations are dictionaries for indexed goals
       neg_dev_dict = deviations["neg"]
       pos_dev_dict = deviations["pos"]

       print(f"{entity.name}:")
       print(f"  Shortfall: {neg_dev_dict.get(entity.id, 0):.2f}")
       print(f"  Excess: {pos_dev_dict.get(entity.id, 0):.2f}")

Use Cases
---------

Business Applications
~~~~~~~~~~~~~~~~~~~~~

1. **Production Planning**: Balance profit, costs, quality goals
2. **Resource Allocation**: Satisfy competing departmental needs
3. **Project Portfolio**: Optimize across budget, risk, strategic fit
4. **Staff Scheduling**: Balance coverage, costs, preferences
5. **Supply Chain**: Optimize service level, cost, inventory goals

When to Use Goal Programming
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Use goal programming when**:

- Multiple conflicting objectives exist
- Trade-offs between goals are acceptable
- Priorities can be assigned to objectives
- Some constraints can be relaxed with penalty

**Don't use when**:

- Single objective is clear
- All constraints are hard (must be satisfied)
- Equal importance for all objectives

Extending the Example
---------------------

Try These Modifications
~~~~~~~~~~~~~~~~~~~~~~~

1. **More Priorities**: Add 4th and 5th priority levels
2. **Sequential Mode**: Enable true preemptive GP (when available)
3. **Dynamic Weights**: Adjust weights based on context
4. **Conditional Goals**: Goals that activate under conditions
5. **Interactive**: Allow user to set priorities dynamically

Next Steps
----------

After mastering this example:

1. **Example 09 (Sensitivity Analysis)**: Understanding constraint values
2. **Example 08 (Scenario Analysis)**: Testing goal achievement under scenarios
3. **Advanced GP**: Multi-priority weighted formulations

See Also
--------

**Related Examples**:

- :doc:`production_planning` - Base model for goal programming
- :doc:`scenario_analysis` - Testing goals under different scenarios
- :doc:`sensitivity_analysis` - Understanding trade-offs

**API Reference**:

- :class:`lumix.core.constraints.LXConstraint`
- :class:`lumix.core.model.LXModel`
- :class:`lumix.solution.LXSolution`

**References**:

- Charnes & Cooper (1961). "Management Models and Industrial Applications of Linear Programming"
- Ignizio (1976). "Goal Programming and Extensions"
- Romero (1991). "Handbook of Critical Issues in Goal Programming"

Files in This Example
---------------------

- ``01_basic_goal_programming.py`` - Basic goal programming demonstration
- ``02_multi_priority_weighted.py`` - Advanced multi-priority example
- ``README.md`` - Detailed documentation and usage guide
