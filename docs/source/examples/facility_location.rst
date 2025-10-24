Facility Location Example
=========================

Overview
--------

This example demonstrates **mixed-integer programming (MIP)** in LumiX, combining binary decision variables (open/close facilities) with continuous flow variables (shipping quantities). It showcases how to model fixed costs, conditional constraints, and the classic **Big-M formulation**.

The facility location problem determines which warehouses to open and how to route shipments to minimize total cost while satisfying customer demands.

Problem Description
-------------------

A logistics company needs to decide:

1. **Which warehouses to open** from candidate locations (binary decision)
2. **How to serve customers** from open warehouses (continuous flow)

**Objective**: Minimize total cost = fixed opening costs + variable shipping costs.

**Constraints**:

- Demand satisfaction: All customer demands must be met
- Capacity limits: Warehouses cannot exceed capacity
- Conditional shipping: Can only ship from open warehouses (Big-M)
- Binary opening decisions: Warehouse is either open or closed

Mathematical Formulation
------------------------

**Decision Variables**:

.. math::

   \text{open}_w &\in \{0, 1\}, \quad \forall w \in \text{Warehouses} \\
   \text{ship}_{w,c} &\geq 0, \quad \forall w \in \text{Warehouses}, c \in \text{Customers}

**Objective Function**:

.. math::

   \text{Minimize} \quad \sum_{w \in \text{Warehouses}} \text{fixed\_cost}_w \cdot \text{open}_w
   + \sum_{w,c} \text{shipping\_cost}_{w,c} \cdot \text{ship}_{w,c}

**Constraints**:

1. **Demand Satisfaction**:

   .. math::

      \sum_{w \in \text{Warehouses}} \text{ship}_{w,c} \geq \text{demand}_c,
      \quad \forall c \in \text{Customers}

2. **Capacity with Opening**:

   .. math::

      \sum_{c \in \text{Customers}} \text{ship}_{w,c} \leq \text{capacity}_w \cdot \text{open}_w,
      \quad \forall w \in \text{Warehouses}

3. **Big-M Constraint** (can only ship if open):

   .. math::

      \text{ship}_{w,c} \leq M \cdot \text{open}_w,
      \quad \forall w \in \text{Warehouses}, c \in \text{Customers}

   where :math:`M` is a sufficiently large constant.

Key Features
------------

Binary Decision Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~

Open/close decisions using binary variables:

.. literalinclude:: ../../../examples/03_facility_location/facility_location.py
   :language: python
   :lines: 119-124
   :dedent: 4

**Key Points**:

- ``LXVariable[Warehouse, int]`` with ``.binary()`` creates 0/1 variables
- One variable per warehouse to decide opening
- Fixed costs apply only when ``open_warehouse = 1``

Continuous Flow Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~

Multi-indexed shipping quantities:

.. literalinclude:: ../../../examples/03_facility_location/facility_location.py
   :language: python
   :lines: 128-136
   :dedent: 4

The flow variables are indexed by (Warehouse, Customer) pairs using cartesian product.

Fixed Costs in Objective
~~~~~~~~~~~~~~~~~~~~~~~~~

One-time costs paid if a facility is opened:

.. literalinclude:: ../../../examples/03_facility_location/facility_location.py
   :language: python
   :lines: 142-146
   :dedent: 4

The objective combines fixed costs (binary variables) and variable costs (continuous variables).

Big-M Constraints
~~~~~~~~~~~~~~~~~

Enforce "can only ship if open" using Big-M formulation:

.. literalinclude:: ../../../examples/03_facility_location/facility_location.py
   :language: python
   :lines: 186-205
   :dedent: 4

**Big-M Logic**:

- If ``open[w] = 0``: ``ship[w,c] <= M × 0 = 0`` (cannot ship)
- If ``open[w] = 1``: ``ship[w,c] <= M × 1 = M`` (can ship up to M)

**Choosing M**: Must be large enough not to constrain feasible solutions. Here, ``M = total_demand`` is safe.

Capacity with Binary Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Conditional capacity constraints:

.. literalinclude:: ../../../examples/03_facility_location/facility_location.py
   :language: python
   :lines: 168-182
   :dedent: 4

This ensures: :math:`\sum_c \text{ship}_{w,c} \leq \text{capacity}_w \cdot \text{open}_w`.

Running the Example
-------------------

**Prerequisites**:

.. code-block:: bash

   pip install lumix[ortools]  # or cplex, gurobi (recommended for MIP)

**Note**: This problem uses haversine-based shipping costs (irrational numbers), which can be problematic for CP-SAT. Use OR-Tools LP, CPLEX, or Gurobi for best results.

**Run**:

.. code-block:: bash

   cd examples/03_facility_location
   python facility_location.py

**Expected Output**:

.. code-block:: text

   ======================================================================
   LumiX Example: Facility Location Problem
   ======================================================================

   Potential Warehouses:
   ----------------------------------------------------------------------
     Chicago Distribution Center : Fixed cost $50,000, Capacity 1000 units
     Atlanta Hub                 : Fixed cost $45,000, Capacity 800 units
     Los Angeles Facility        : Fixed cost $60,000, Capacity 1200 units

   Customers:
   ----------------------------------------------------------------------
     New York       : Demand 300 units
     Miami          : Demand 250 units
     Seattle        : Demand 200 units

   Total Demand: 1100 units
   Total Capacity: 3900 units

   ======================================================================
   SOLUTION
   ======================================================================
   Status: optimal
   Total Cost: $147,234.56
     Fixed Costs: $90,000.00
     Shipping Costs: $57,234.56

   Open Warehouses:
   ----------------------------------------------------------------------
     Chicago Distribution Center: Serving 2 customers (fixed cost: $50,000.00)
     Dallas Warehouse: Serving 2 customers (fixed cost: $40,000.00)

   Shipping Plan:
   ----------------------------------------------------------------------
     Chicago Distribution Center → New York: 300.0 units ($4,500.00)
     Dallas Warehouse → Miami: 250.0 units ($6,250.00)

Complete Code Walkthrough
--------------------------

Step 1: Create Binary Opening Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/03_facility_location/facility_location.py
   :language: python
   :lines: 119-124
   :dedent: 4

Step 2: Create Continuous Shipping Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/03_facility_location/facility_location.py
   :language: python
   :lines: 128-136
   :dedent: 4

Step 3: Set Objective (Fixed + Variable Costs)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/03_facility_location/facility_location.py
   :language: python
   :lines: 142-147
   :dedent: 4

Step 4: Add Demand Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/03_facility_location/facility_location.py
   :language: python
   :lines: 150-162
   :dedent: 4

Step 5: Add Capacity Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/03_facility_location/facility_location.py
   :language: python
   :lines: 165-182
   :dedent: 4

Step 6: Add Big-M Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../examples/03_facility_location/facility_location.py
   :language: python
   :lines: 186-205
   :dedent: 4

Step 7: Solve and Access Solution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   optimizer = LXOptimizer().use_solver("ortools")
   solution = optimizer.solve(model)

   if solution.is_optimal():
       # Access binary variables
       for warehouse in WAREHOUSES:
           is_open = solution.variables["open_warehouse"][warehouse.id]
           if is_open > 0.5:  # Binary variable
               print(f"Open: {warehouse.name}")

       # Access flow variables
       for warehouse in WAREHOUSES:
           for customer in CUSTOMERS:
               qty = solution.variables["ship"].get((warehouse.id, customer.id), 0)
               if qty > 0.01:
                   print(f"Ship {qty:.1f} from {warehouse.name} to {customer.name}")

Learning Objectives
-------------------

After completing this example, you should understand:

1. **Mixed-Integer Programming**: Combining binary and continuous variables
2. **Fixed Costs**: Modeling one-time costs with binary decisions
3. **Big-M Formulation**: Linking binary and continuous variables conditionally
4. **Conditional Constraints**: Enforcing "IF-THEN" logic linearly
5. **Multi-Model Flow**: Indexing flow variables by pairs of models
6. **MIP Solution**: Interpreting binary and continuous solution values

Common Patterns
---------------

Pattern 1: Binary Decision with Fixed Cost
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Binary variable for open/close decision
   open_var = (
       LXVariable[Entity, int]("open")
       .binary()
       .indexed_by(lambda e: e.id)
       .from_data(ENTITIES)
   )

   # Add fixed cost to objective
   cost_expr = LXLinearExpression().add_term(
       open_var,
       coeff=lambda e: e.fixed_cost
   )
   model.minimize(cost_expr)

Pattern 2: Big-M Constraint
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # ship[w,c] <= M × open[w]
   # Rewritten as: ship[w,c] - M × open[w] <= 0

   for warehouse in WAREHOUSES:
       for customer in CUSTOMERS:
           bigm_expr = (
               LXLinearExpression()
               .add_multi_term(
                   ship,
                   coeff=lambda w, c: 1.0,
                   where=lambda w, c: w.id == warehouse.id and c.id == customer.id
               )
               .add_term(
                   open_var,
                   coeff=lambda w: -BIG_M if w.id == warehouse.id else 0
               )
           )
           model.add_constraint(
               LXConstraint(f"bigm_{warehouse.id}_{customer.id}")
               .expression(bigm_expr)
               .le()
               .rhs(0)
           )

Pattern 3: Conditional Capacity
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # flow <= capacity × open
   # Rewritten as: flow - capacity × open <= 0

   capacity_expr = (
       LXLinearExpression()
       .add_multi_term(flow, coeff=lambda src, dst: 1.0, where=...)
       .add_term(open_var, coeff=lambda src: -capacity[src])
   )
   model.add_constraint(
       LXConstraint("capacity").expression(capacity_expr).le().rhs(0)
   )

Pattern 4: Demand Satisfaction
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # For each customer: sum over sources >= demand
   for customer in CUSTOMERS:
       demand_expr = LXLinearExpression().add_multi_term(
           flow,
           coeff=lambda src, dst: 1.0,
           where=lambda src, dst: dst.id == customer.id
       )
       model.add_constraint(
           LXConstraint(f"demand_{customer.id}")
           .expression(demand_expr)
           .ge()
           .rhs(customer.demand)
       )

Extending the Example
---------------------

Try These Modifications
~~~~~~~~~~~~~~~~~~~~~~~

1. **Multi-Product**: Add product dimension to flow variables

   .. code-block:: python

      ship = LXVariable[Tuple[Warehouse, Customer, Product], float]("ship")

2. **Multi-Period**: Dynamic facility opening/closing over time
3. **Capacitated Levels**: Different capacity options (small, medium, large)
4. **Service Level**: Add maximum distance or service time constraints
5. **Hub Location**: Warehouses can ship to other warehouses
6. **Modular Capacity**: Add multiple capacity modules at each location

Improving the Formulation
--------------------------

Better Big-M Values
~~~~~~~~~~~~~~~~~~~

Instead of global Big-M, use specific bounds per (warehouse, customer):

.. code-block:: python

   # Tighter bound for each pair
   M_wc = min(warehouse.capacity, customer.demand)
   # Better LP relaxation → faster solve times

Alternative Formulations
~~~~~~~~~~~~~~~~~~~~~~~~

Consider these improvements:

1. **Aggregated Big-M**: Fewer constraints by combining
2. **Strengthening Cuts**: Add valid inequalities
3. **Variable Bounds**: Tighten upper bounds on flow variables
4. **Preprocessing**: Eliminate dominated facilities

Next Steps
----------

After mastering this example:

1. **Example 02 (Driver Scheduling)**: Multi-model indexing foundation
2. **Example 05 (CP-SAT Assignment)**: Pure integer programming with CP-SAT
3. **Example 11 (Goal Programming)**: Soft constraints for location problems
4. **User Guide - MIP**: Deep dive into mixed-integer programming

See Also
--------

**Related Examples**:

- :doc:`driver_scheduling` - Multi-model indexing with binary variables
- :doc:`cpsat_assignment` - CP-SAT solver for combinatorial problems
- :doc:`production_planning` - Single-model indexing basics

**API Reference**:

- :class:`lumix.core.variables.LXVariable`
- :class:`lumix.indexing.LXIndexDimension`
- :class:`lumix.core.model.LXModel`
- :class:`lumix.core.constraints.LXConstraint`

**User Guide**:

- :doc:`../user-guide/core/variables` - Binary and integer variables for MIP
- :doc:`../user-guide/linearization/bilinear` - Big-M method and bilinear linearization
- :doc:`../user-guide/core/variables` - Using binary variables for fixed costs

Use Cases
---------

This pattern applies to:

- **Distribution Network Design**: Minimize logistics costs
- **Server Placement**: Cloud computing infrastructure
- **Retail Site Selection**: Store location optimization
- **Emergency Services**: Hospital/fire station placement
- **Manufacturing**: Plant location and production allocation
- **Supply Chain**: Hub-and-spoke network design

Files in This Example
---------------------

- ``facility_location.py`` - Main optimization model and solution display
- ``sample_data.py`` - Data models (Warehouse, Customer) and cost calculations
- ``README.md`` - Detailed documentation and usage guide
