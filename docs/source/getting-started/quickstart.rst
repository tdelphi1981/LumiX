Quick Start Guide
=================

This guide will walk you through building your first optimization model with LumiX.

A Simple Production Planning Problem
-------------------------------------

Let's solve a classic production planning problem: maximizing profit while respecting resource constraints.

Problem Description
~~~~~~~~~~~~~~~~~~~

We manufacture two products, each requiring different amounts of two resources:

- **Product A**: Profit = $30/unit, requires 2 hours labor and 1 kg material
- **Product B**: Profit = $40/unit, requires 1 hour labor and 2 kg material

Available resources:

- **Labor**: 100 hours
- **Material**: 80 kg

**Goal**: Maximize total profit.

Step 1: Define Your Data
~~~~~~~~~~~~~~~~~~~~~~~~~

First, let's define our data using simple Python classes:

.. code-block:: python

   from dataclasses import dataclass

   @dataclass
   class Product:
       id: str
       name: str
       profit: float
       labor_required: float
       material_required: float

   # Define our products
   products = [
       Product("A", "Product A", profit=30, labor_required=2, material_required=1),
       Product("B", "Product B", profit=40, labor_required=1, material_required=2),
   ]

   # Define resource capacities
   labor_capacity = 100
   material_capacity = 80

Step 2: Build the Model
~~~~~~~~~~~~~~~~~~~~~~~~

Now, let's build the optimization model using LumiX:

.. code-block:: python

   from lumix import (
       LXModel,
       LXVariable,
       LXConstraint,
       LXLinearExpression,
   )

   # Decision variable: how much to produce of each product
   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .bounds(lower=0)  # Can't produce negative amounts
       .indexed_by(lambda p: p.id)  # Index by product ID
       .from_data(products)  # Use our product data
   )

   # Create the model
   model = LXModel("production_plan").add_variable(production)

   # Objective: Maximize total profit
   model.maximize(
       LXLinearExpression()
       .add_term(production, lambda p: p.profit)
   )

   # Constraint: Labor capacity
   model.add_constraint(
       LXConstraint("labor_capacity")
       .expression(
           LXLinearExpression()
           .add_term(production, lambda p: p.labor_required)
       )
       .le()
       .rhs(labor_capacity)
   )

   # Constraint: Material capacity
   model.add_constraint(
       LXConstraint("material_capacity")
       .expression(
           LXLinearExpression()
           .add_term(production, lambda p: p.material_required)
       )
       .le()
       .rhs(material_capacity)
   )

Step 3: Solve the Model
~~~~~~~~~~~~~~~~~~~~~~~~

Use the optimizer to solve the model:

.. code-block:: python

   from lumix import LXOptimizer

   # Create optimizer and select solver
   optimizer = LXOptimizer().use_solver("ortools")

   # Solve the model
   solution = optimizer.solve(model)

   # Check if we found an optimal solution
   if solution.is_optimal():
       print(f"Optimal profit: ${solution.objective_value:.2f}")

       # Get the production quantities
       for product in products:
           quantity = solution.variables["production"][product.id]
           print(f"Produce {quantity:.2f} units of {product.name}")
   else:
       print(f"No optimal solution found. Status: {solution.status}")

Complete Example
----------------

Here's the complete code in one place:

.. code-block:: python

   from dataclasses import dataclass
   from lumix import (
       LXModel,
       LXVariable,
       LXConstraint,
       LXLinearExpression,
       LXOptimizer,
   )

   # Step 1: Define data
   @dataclass
   class Product:
       id: str
       name: str
       profit: float
       labor_required: float
       material_required: float

   products = [
       Product("A", "Product A", profit=30, labor_required=2, material_required=1),
       Product("B", "Product B", profit=40, labor_required=1, material_required=2),
   ]

   labor_capacity = 100
   material_capacity = 80

   # Step 2: Build model
   production = (
       LXVariable[Product, float]("production")
       .continuous()
       .bounds(lower=0)
       .indexed_by(lambda p: p.id)
       .from_data(products)
   )

   model = (
       LXModel("production_plan")
       .add_variable(production)
       .maximize(
           LXLinearExpression()
           .add_term(production, lambda p: p.profit)
       )
   )

   model.add_constraint(
       LXConstraint("labor_capacity")
       .expression(
           LXLinearExpression()
           .add_term(production, lambda p: p.labor_required)
       )
       .le()
       .rhs(labor_capacity)
   )

   model.add_constraint(
       LXConstraint("material_capacity")
       .expression(
           LXLinearExpression()
           .add_term(production, lambda p: p.material_required)
       )
       .le()
       .rhs(material_capacity)
   )

   # Step 3: Solve
   optimizer = LXOptimizer().use_solver("ortools")
   solution = optimizer.solve(model)

   if solution.is_optimal():
       print(f"Optimal profit: ${solution.objective_value:.2f}")
       for product in products:
           quantity = solution.variables["production"][product.id]
           print(f"Produce {quantity:.2f} units of {product.name}")

Expected Output
~~~~~~~~~~~~~~~

.. code-block:: text

   Optimal profit: $2000.00
   Produce 20.00 units of Product A
   Produce 30.00 units of Product B

Understanding the Code
----------------------

Key Concepts
~~~~~~~~~~~~

**Variables with Indexing**

.. code-block:: python

   LXVariable[Product, float]("production")
   .indexed_by(lambda p: p.id)
   .from_data(products)

This creates one decision variable for each product, automatically indexed by product ID.
The type annotation ``[Product, float]`` provides IDE autocomplete and type checking.

**Data-Driven Coefficients**

.. code-block:: python

   LXLinearExpression()
   .add_term(production, lambda p: p.profit)

Coefficients are computed from your data using lambda functions. This is type-safe and
eliminates manual loops and error-prone indexing.

**Fluent API**

All LumiX objects support method chaining for readable, declarative code:

.. code-block:: python

   model = (
       LXModel("name")
       .add_variable(var1)
       .add_variable(var2)
       .add_constraint(constraint1)
       .maximize(objective)
   )

Switching Solvers
-----------------

LumiX makes it easy to switch between solvers. Just change the solver name:

.. code-block:: python

   # Use OR-Tools (free)
   optimizer = LXOptimizer().use_solver("ortools")

   # Use Gurobi (requires license)
   optimizer = LXOptimizer().use_solver("gurobi")

   # Use CPLEX (requires license)
   optimizer = LXOptimizer().use_solver("cplex")

   # Use GLPK (free)
   optimizer = LXOptimizer().use_solver("glpk")

The rest of your code stays exactly the same!

Model Summary
-------------

View a summary of your model:

.. code-block:: python

   print(model.summary())

Output:

.. code-block:: text

   Model: production_plan
   Variables: 1 family (2 instances)
   Constraints: 2
   Objective: MAXIMIZE

Next Steps
----------

Now that you've built your first model, explore:

- **Examples**: See the ``examples/`` directory for more complex scenarios
- **User Guide**: Learn about advanced features (coming soon)
- **API Reference**: Detailed API documentation (coming soon)
- :doc:`solvers`: Learn about different solver capabilities

Common Patterns
---------------

Integer Variables
~~~~~~~~~~~~~~~~~

For integer decisions (e.g., number of trucks):

.. code-block:: python

   trucks = (
       LXVariable[Route, int]("trucks")
       .integer()
       .bounds(lower=0, upper=10)
       .indexed_by(lambda r: r.id)
       .from_data(routes)
   )

Binary Variables
~~~~~~~~~~~~~~~~

For yes/no decisions (e.g., facility open/closed):

.. code-block:: python

   is_open = (
       LXVariable[Facility, int]("is_open")
       .binary()
       .indexed_by(lambda f: f.id)
       .from_data(facilities)
   )

Multi-Dimensional Indexing
~~~~~~~~~~~~~~~~~~~~~~~~~~~

For decisions indexed by multiple dimensions:

.. code-block:: python

   from lumix import LXCartesianProduct

   # Assignment of drivers to shifts on dates
   assignment = (
       LXVariable[tuple[Driver, Date, Shift], int]("assignment")
       .binary()
       .indexed_by(lambda item: (item[0].id, item[1].id, item[2].id))
       .from_data(LXCartesianProduct(drivers, dates, shifts))
   )

Getting Help
------------

- Check the examples in the repository
- Read the API documentation
- Open an issue on GitHub: https://github.com/lumix/lumix/issues
