Advanced Solver Features
========================

This guide covers advanced solver features like warm start, callbacks, and sensitivity analysis.

Overview
--------

Advanced features available in LumiX solvers:

1. **Warm Start**: Use previous solution to speed up solving
2. **Sensitivity Analysis**: Shadow prices and reduced costs
3. **Callbacks**: Custom heuristics and lazy constraints (Gurobi/CPLEX only)
4. **Solution Pools**: Multiple solutions for MIP (Gurobi/CPLEX only)
5. **IIS/Conflict Refinement**: Debug infeasible models (Gurobi/CPLEX only)

.. note::
   Not all solvers support all features. Check :doc:`solver-capabilities` for details.

Warm Start
----------

Warm start uses a previous solution as a starting point for solving, which can significantly speed up solving for similar models.

When to Use
~~~~~~~~~~~

**Good for:**

- Solving a sequence of similar models
- Re-optimizing after small parameter changes
- Interactive optimization (user tweaks and re-solves)
- Rolling horizon planning

**Not useful for:**

- First solve (no previous solution)
- Completely different models
- Major structural changes

Basic Usage
~~~~~~~~~~~

Currently, warm start is primarily used internally by solvers when you solve similar models sequentially. LumiX automatically leverages this when applicable.

.. code-block:: python

   from lumix import LXOptimizer

   optimizer = LXOptimizer().use_solver("gurobi")

   # First solve
   solution1 = optimizer.solve(model1)

   # Modify model slightly
   model2 = model1.copy()
   model2.update_parameter("demand", new_demand)

   # Second solve may benefit from internal warm start
   solution2 = optimizer.solve(model2)

Supported Solvers
~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Solver
     - Supported
     - Notes
   * - OR-Tools
     - ✓
     - Automatic when solving sequentially
   * - Gurobi
     - ✓
     - Automatic MIP start
   * - CPLEX
     - ✓
     - Automatic warm start
   * - GLPK
     - ✗
     - Not supported
   * - CP-SAT
     - ✓
     - Via solution hints

Sensitivity Analysis
--------------------

Sensitivity analysis provides information about how the optimal solution changes with small changes to the model.

What is Sensitivity Analysis?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Shadow Prices** (dual values):

- How much the objective would improve if a constraint's RHS increased by 1 unit
- Only meaningful for linear programs (or LP relaxation)

**Reduced Costs**:

- How much the objective coefficient would need to change before a variable becomes positive
- Indicates "opportunity cost" of forcing a variable to be non-zero

Enabling Sensitivity
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXOptimizer

   optimizer = LXOptimizer().use_solver("gurobi").enable_sensitivity()
   solution = optimizer.solve(model)

   # Access sensitivity information
   shadow_prices = solution.shadow_prices
   reduced_costs = solution.reduced_costs

Accessing Shadow Prices
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get shadow price for a constraint
   capacity_constraint = model.get_constraint("capacity")

   for resource in resources:
       shadow_price = solution.get_shadow_price(capacity_constraint, resource)
       print(f"{resource.name}: ${shadow_price:.2f} per unit")

**Interpretation:**

- Shadow price of $5 means: increasing capacity by 1 unit would increase profit by $5
- Shadow price of $0 means: constraint is not binding (has slack)
- Negative shadow price: relaxing constraint decreases objective (for maximization)

Accessing Reduced Costs
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get reduced cost for a variable
   production = model.get_variable("production")

   for product in products:
       reduced_cost = solution.get_reduced_cost(production, product)
       if reduced_cost > 0:
           print(f"{product.name}: would need ${reduced_cost:.2f} better profit to produce")

**Interpretation:**

- Reduced cost of $10 means: profit would need to increase by $10 before producing this product
- Reduced cost of $0 means: variable is in the optimal basis (positive in solution)

Example: Resource Valuation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXModel, LXOptimizer

   # Build production model
   model = build_production_model(products, resources)

   # Enable sensitivity analysis
   optimizer = LXOptimizer().use_solver("gurobi").enable_sensitivity()
   solution = optimizer.solve(model)

   # Evaluate resources
   print("Resource Shadow Prices:")
   capacity_constraint = model.get_constraint("capacity")
   for resource in resources:
       shadow_price = solution.get_shadow_price(capacity_constraint, resource)
       current_capacity = resource.capacity

       print(f"\n{resource.name}:")
       print(f"  Current capacity: {current_capacity}")
       print(f"  Shadow price: ${shadow_price:.2f}")
       print(f"  Value of +10 units: ${shadow_price * 10:.2f}")

       # Decision: Should we buy more capacity?
       cost_per_unit = resource.expansion_cost
       if shadow_price > cost_per_unit:
           print(f"  ✓ RECOMMEND: Expand (value ${shadow_price:.2f} > cost ${cost_per_unit:.2f})")
       else:
           print(f"  ✗ Don't expand (value ${shadow_price:.2f} < cost ${cost_per_unit:.2f})")

Supported Solvers
~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Solver
     - Supported
     - Notes
   * - OR-Tools
     - ✗
     - Not available
   * - Gurobi
     - ✓
     - Full support (LP and MIP)
   * - CPLEX
     - ✓
     - Full support (LP and MIP)
   * - GLPK
     - ✓
     - LP only
   * - CP-SAT
     - ✗
     - Not available

Callbacks (Gurobi/CPLEX Only)
------------------------------

Callbacks allow you to inject custom logic during the solving process.

.. note::
   Callbacks are an advanced feature. Most users don't need them.

Types of Callbacks
~~~~~~~~~~~~~~~~~~

1. **Lazy Constraints**: Add constraints only when violated
2. **User Cuts**: Add cutting planes to improve bounds
3. **Custom Heuristics**: Generate feasible solutions during search
4. **Information Callbacks**: Monitor solve progress

When to Use
~~~~~~~~~~~

**Lazy Constraints:**

- Model has exponentially many constraints
- Can't enumerate all constraints upfront
- Example: TSP subtour elimination

**User Cuts:**

- Know valid cutting planes that improve bounds
- Cuts are expensive to generate upfront
- Example: Gomory cuts, problem-specific cuts

**Custom Heuristics:**

- Have domain knowledge for generating good solutions
- Want to guide search with problem-specific logic
- Example: Construction heuristics

Example: Lazy Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note::
   Direct callback support is planned for future LumiX versions. Currently, you can access the underlying solver model for callback implementation.

.. code-block:: python

   from lumix import LXOptimizer

   # Build model
   model = build_tsp_model(cities)

   # Create optimizer
   optimizer = LXOptimizer().use_solver("gurobi")

   # Access underlying Gurobi model
   gurobi_model = optimizer._solver.build_model(model)

   # Define lazy constraint callback (Gurobi-specific)
   def subtour_callback(model, where):
       if where == GRB.Callback.MIPSOL:
           # Get current solution
           vals = model.cbGetSolution(model._vars)
           # Check for subtours
           subtours = find_subtours(vals)
           # Add lazy constraint if subtour found
           for subtour in subtours:
               model.cbLazy(sum(vars[i,j] for i,j in subtour) <= len(subtour) - 1)

   gurobi_model.optimize(subtour_callback)

Supported Solvers
~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Solver
     - Supported
     - Notes
   * - OR-Tools
     - ✗
     - Not available
   * - Gurobi
     - ✓
     - Full callback support
   * - CPLEX
     - ✓
     - Full callback support
   * - GLPK
     - ✗
     - Not available
   * - CP-SAT
     - ✗
     - Not available

Solution Pools (Gurobi/CPLEX Only)
-----------------------------------

Solution pools store multiple feasible solutions for MIP problems.

When to Use
~~~~~~~~~~~

**Good for:**

- Need multiple diverse solutions (backup plans)
- Want to present alternatives to decision makers
- Post-processing to select "best" solution based on additional criteria

Example: Finding Multiple Solutions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXOptimizer

   # Access underlying Gurobi model
   optimizer = LXOptimizer().use_solver("gurobi")
   gurobi_model = optimizer._solver.build_model(model)

   # Request multiple solutions
   gurobi_model.setParam('PoolSolutions', 10)  # Keep up to 10 solutions
   gurobi_model.setParam('PoolSearchMode', 2)  # Find diverse solutions

   gurobi_model.optimize()

   # Access solution pool
   num_solutions = gurobi_model.SolCount
   print(f"Found {num_solutions} solutions")

   for i in range(min(5, num_solutions)):
       gurobi_model.setParam('SolutionNumber', i)
       obj_val = gurobi_model.PoolObjVal
       print(f"Solution {i+1}: objective = {obj_val}")

Supported Solvers
~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Solver
     - Supported
     - Notes
   * - OR-Tools
     - ✗
     - Not available
   * - Gurobi
     - ✓
     - Full solution pool support
   * - CPLEX
     - ✓
     - Solution pool support
   * - GLPK
     - ✗
     - Not available
   * - CP-SAT
     - ✗
     - Not available

IIS and Conflict Refinement
----------------------------

IIS (Irreducible Inconsistent Subsystem) and conflict refinement help debug infeasible models.

What is IIS?
~~~~~~~~~~~~

An IIS is a minimal subset of constraints that make the model infeasible:

- Removing any single constraint from the IIS makes it feasible
- Helps identify which constraints conflict

Example: Computing IIS
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXOptimizer

   # Solve model
   optimizer = LXOptimizer().use_solver("gurobi")
   solution = optimizer.solve(model)

   if solution.status == "infeasible":
       # Access underlying Gurobi model
       gurobi_model = optimizer._solver.get_solver_model()

       # Compute IIS
       gurobi_model.computeIIS()
       gurobi_model.write("model.ilp")  # Write IIS to file

       # Print conflicting constraints
       print("Conflicting constraints:")
       for constr in gurobi_model.getConstrs():
           if constr.IISConstr:
               print(f"  {constr.ConstrName}")

Debugging Infeasible Models
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Workflow:

1. **Solve and check status**

   .. code-block:: python

      solution = optimizer.solve(model)
      if solution.status == "infeasible":
          print("Model is infeasible!")

2. **Compute IIS**

   .. code-block:: python

      gurobi_model.computeIIS()

3. **Identify conflicts**

   Check which constraints are in the IIS

4. **Fix model**

   Options:

   - Remove or relax conflicting constraints
   - Adjust constraint bounds
   - Add slack variables with penalties

Example: Relaxing Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Add slack variables to constraints
   for constraint in conflicting_constraints:
       slack = LXVariable(f"slack_{constraint.name}").continuous().bounds(lower=0)
       model.add_variable(slack)

       # Add slack to constraint
       constraint.expression.add_term(slack, 1.0)

   # Add penalty for slack in objective
   for slack_var in slack_variables:
       objective.add_term(slack_var, -1000)  # Large penalty

   # Re-solve
   solution = optimizer.solve(model)

Supported Solvers
~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Solver
     - Supported
     - Notes
   * - OR-Tools
     - ✗
     - Not available
   * - Gurobi
     - ✓
     - computeIIS()
   * - CPLEX
     - ✓
     - Conflict refinement
   * - GLPK
     - ✗
     - Not available
   * - CP-SAT
     - ✗
     - Not available

Best Practices
--------------

Warm Start
~~~~~~~~~~

1. **Incremental Solving**

   Solve a sequence of similar models to benefit from warm start

2. **Small Changes Only**

   Works best when models differ only in parameter values, not structure

3. **Monitor Performance**

   Compare solve times with and without warm start

Sensitivity Analysis
~~~~~~~~~~~~~~~~~~~~

1. **LP Only (for meaningful results)**

   Shadow prices are most reliable for pure LP or after fixing integer variables

2. **Valid Range**

   Shadow prices only valid for small changes in RHS (within basis stability range)

3. **Use for Decisions**

   Identify which resources to expand, which constraints to relax

Callbacks
~~~~~~~~~

1. **Profile First**

   Only use if default solver performance is insufficient

2. **Keep Simple**

   Complex callbacks can slow solving more than they help

3. **Test Thoroughly**

   Incorrect callbacks can produce wrong results

IIS/Conflict Refinement
~~~~~~~~~~~~~~~~~~~~~~~

1. **Simplify First**

   Try to identify obvious conflicts before computing IIS

2. **Iterative Debugging**

   Fix one conflict at a time, re-solve, repeat

3. **Consider Relaxation**

   Add slack variables with penalties rather than removing constraints

Feature Availability Summary
-----------------------------

.. list-table::
   :header-rows: 1
   :widths: 25 15 15 15 15 15

   * - Feature
     - OR-Tools
     - Gurobi
     - CPLEX
     - GLPK
     - CP-SAT
   * - Warm Start
     - ✓
     - ✓
     - ✓
     - ✗
     - ✓
   * - Sensitivity Analysis
     - ✗
     - ✓
     - ✓
     - ✓ (LP)
     - ✗
   * - Callbacks
     - ✗
     - ✓
     - ✓
     - ✗
     - ✗
   * - Solution Pools
     - ✗
     - ✓
     - ✓
     - ✗
     - ✗
   * - IIS/Conflict
     - ✗
     - ✓
     - ✓
     - ✗
     - ✗

Next Steps
----------

- :doc:`solver-capabilities` - Full capability matrix
- :doc:`choosing-solver` - Choose solver based on features needed
- :doc:`using-optimizer` - Using the optimizer API
- :doc:`/development/extending-solvers` - Implementing custom solvers
- Gurobi Callback Reference: https://www.gurobi.com/documentation/
- CPLEX Callback Reference: https://www.ibm.com/docs/en/icos/
