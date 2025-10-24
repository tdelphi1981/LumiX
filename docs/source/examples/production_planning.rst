Production Planning Example
============================

Overview
--------

This example demonstrates LumiX's **single-model indexing** feature, which allows
variables and constraints to be indexed directly by data model instances rather
than manual integer indices.

The production planning problem is a fundamental optimization problem in
operations research, making it an ideal introduction to data-driven modeling
with LumiX.

Problem Description
-------------------

A manufacturing company produces multiple products, each requiring different
amounts of limited resources (labor hours, machine hours, raw materials).

**Objective**: Maximize total profit from production.

**Constraints**:

- Resource capacity limits (can't exceed available labor, machine time, materials)
- Minimum production requirements (must meet customer orders)
- Non-negativity (can't produce negative quantities)

Mathematical Formulation
------------------------

**Decision Variables**:

.. math::

   x_p \in \mathbb{R}_+, \quad \forall p \in \text{Products}

where :math:`x_p` represents the production quantity for product :math:`p`.

**Objective Function**:

.. math::

   \text{Maximize} \quad \sum_{p \in \text{Products}} \text{profit}_p \cdot x_p

where :math:`\text{profit}_p = \text{selling\_price}_p - \text{unit\_cost}_p`.

**Constraints**:

1. **Resource Capacity**:

   .. math::

      \sum_{p \in \text{Products}} \text{usage}_{p,r} \cdot x_p \leq \text{capacity}_r,
      \quad \forall r \in \text{Resources}

2. **Minimum Production**:

   .. math::

      x_p \geq \text{min\_production}_p, \quad \forall p \in \text{Products}

Key Features
------------

Single-Model Indexing
~~~~~~~~~~~~~~~~~~~~~

Variables are indexed directly by ``Product`` instances:

.. literalinclude:: ../../../examples/01_production_planning/production_planning.py
   :language: python
   :lines: 33-39

**Key Points**:

- ``LXVariable[Product, float]`` creates a variable family
- ``.indexed_by(lambda p: p.id)`` specifies the index key
- ``.from_data(PRODUCTS)`` auto-creates one variable per product
- No manual loops or index management needed

Data-Driven Coefficients
~~~~~~~~~~~~~~~~~~~~~~~~~

Coefficients are extracted from data using lambda functions:

.. literalinclude:: ../../../examples/01_production_planning/production_planning.py
   :language: python
   :lines: 46-51

The ``lambda p: p.selling_price - p.unit_cost`` extracts profit per unit directly
from each Product instance.

Automatic Expression Expansion
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Expressions automatically sum over all indexed data:

.. literalinclude:: ../../../examples/01_production_planning/production_planning.py
   :language: python
   :lines: 60-66

The expression sums resource usage across all products automatically.

Constraint Families
~~~~~~~~~~~~~~~~~~~

Similar constraints can be created as families indexed by data:

.. literalinclude:: ../../../examples/01_production_planning/production_planning.py
   :language: python
   :lines: 78-86
   :dedent: 4

This creates one minimum production constraint per product.

Type-Safe Solution Access
~~~~~~~~~~~~~~~~~~~~~~~~~~

Solutions are accessed using the same indices as the original data:

.. code-block:: python

   for product in PRODUCTS:
       qty = solution.variables["production"][product.id]
       profit = (product.selling_price - product.unit_cost) * qty

Running the Example
-------------------

**Prerequisites**:

.. code-block:: bash

   pip install lumix[cplex]  # or ortools, gurobi, glpk

**Run**:

.. code-block:: bash

   cd examples/01_production_planning
   python production_planning.py

**Expected Output**:

.. code-block:: text

   ============================================================
   OptiXNG Example: Production Planning
   ============================================================

   Status: optimal
   Optimal Profit: $3,465.00

   Production Plan:
   ------------------------------------------------------------
     Widget A       :   10.0 units  (profit: $500.00)
     Widget B       :    8.6 units  (profit: $600.28)
     Gadget X       :    8.0 units  (profit: $520.00)
     Gadget Y       :   23.7 units  (profit: $1,186.50)
     Premium Z      :    3.0 units  (profit: $300.00)

Complete Code Walkthrough
--------------------------

Step 1: Define Data Models
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/01_production_planning/sample_data.py
   :language: python
   :lines: 33-70
   :dedent: 0

Step 2: Create Variables
~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/01_production_planning/production_planning.py
   :language: python
   :lines: 33-39

Step 3: Set Objective
~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/01_production_planning/production_planning.py
   :language: python
   :lines: 45-52

Step 4: Add Constraints
~~~~~~~~~~~~~~~~~~~~~~~~

**Resource Capacity**:

.. literalinclude:: ../../../examples/01_production_planning/production_planning.py
   :language: python
   :lines: 56-73

**Minimum Production**:

.. literalinclude:: ../../../examples/01_production_planning/production_planning.py
   :language: python
   :lines: 78-87

Step 5: Solve and Access Solution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   optimizer = LXOptimizer().use_solver("cplex")
   solution = optimizer.solve(model)

   if solution.is_optimal():
       for product in PRODUCTS:
           qty = solution.variables["production"][product.id]

Learning Objectives
-------------------

After completing this example, you should understand:

1. **Variable Families**: How one ``LXVariable`` expands to multiple solver variables
2. **Indexing**: How ``.indexed_by()`` and ``.from_data()`` work together
3. **Lambda Coefficients**: How to extract coefficients from data instances
4. **Automatic Summation**: How expressions sum over all indexed instances
5. **Constraint Families**: How to create multiple similar constraints
6. **Solution Mapping**: How to access results using original indices

Common Patterns
---------------

Pattern 1: Variable Family from Data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   variable = (
       LXVariable[DataModel, float]("var_name")
       .continuous()  # or .integer() or .binary()
       .bounds(lower=0, upper=100)
       .indexed_by(lambda instance: instance.id)
       .from_data(data_list)
   )

Pattern 2: Expression with Lambda Coefficients
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   expr = (
       LXLinearExpression()
       .add_term(variable, coeff=lambda instance: instance.attribute)
   )

Pattern 3: Constraint Family
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   model.add_constraint(
       LXConstraint[DataModel]("constraint_name")
       .expression(expr)
       .ge()  # or .le() or .eq()
       .rhs(lambda instance: instance.threshold)
       .from_data(data_list)
       .indexed_by(lambda instance: instance.key)
   )

Extending the Example
---------------------

Try These Modifications
~~~~~~~~~~~~~~~~~~~~~~~

1. **Add New Resource**: Introduce a storage capacity constraint
2. **Maximum Production**: Add upper bounds on production quantities
3. **Product Groups**: Group products and add category-level constraints
4. **Time Periods**: Extend to multi-period production planning
5. **Inventory**: Add inventory variables and balance constraints

Next Steps
----------

After mastering this example:

1. **Example 02 (Driver Scheduling)**: Learn multi-model indexing with cartesian products
2. **Example 03 (Facility Location)**: Binary variables and fixed costs
3. **Example 04 (Basic LP)**: Even simpler introduction if needed
4. **User Guide - Indexing**: Deep dive into single and multi-model indexing

See Also
--------

**Related Examples**:

- :doc:`basic_lp` - Simpler introduction to LumiX basics
- :doc:`driver_scheduling` - Multi-model indexing
- :doc:`facility_location` - Binary variables and MIP

**API Reference**:

- :class:`lumix.core.variables.LXVariable`
- :class:`lumix.core.model.LXModel`
- :class:`lumix.core.constraints.LXConstraint`
- :class:`lumix.core.expressions.LXLinearExpression`

**User Guide**:

- :doc:`../user-guide/indexing/single-model` - Single-model indexing
- :doc:`../user-guide/core/variables` - Variable types and families
- :doc:`../user-guide/core/constraints` - Constraint modeling

Files in This Example
---------------------

- ``production_planning.py`` - Main optimization model and solution display
- ``sample_data.py`` - Data models (Product, Resource) and sample data
- ``README.md`` - Detailed documentation and usage guide
