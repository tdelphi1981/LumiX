Advanced Solver Features
========================

This guide covers sensitivity analysis and the solver features that LumiX does
not wrap (warm start, callbacks, solution pools, IIS), which you can reach
through the underlying solver model.

Overview
--------

Advanced features available in LumiX solvers:

1. **Warm Start**: not passed to the solvers by LumiX
2. **Sensitivity Analysis**: Shadow prices and reduced costs
3. **Callbacks**: Custom heuristics and lazy constraints (Gurobi/CPLEX, through the solver model)
4. **Solution Pools**: Multiple solutions for MIP (Gurobi/CPLEX, through the solver model)
5. **IIS/Conflict Refinement**: Debug infeasible models (Gurobi/CPLEX, through the solver model)

.. note::
   Not all solvers support all features. Check :doc:`solver-capabilities` for details.

Warm Start
----------

LumiX does not pass warm starts or solution hints to the solvers yet: every
``solve()`` builds the solver model afresh, also when the same
``LXOptimizer`` solves a sequence of similar models. To solve a variant of a
model, copy it with :func:`copy.deepcopy` and change the copy (or use
:doc:`/user-guide/analysis/whatif`, which does this for you):

.. code-block:: python

   import copy

   from lumix import LXOptimizer

   optimizer = LXOptimizer().use_solver("gurobi")
   solution1 = optimizer.solve(model1)

   # A variant with more wood: copy the model and change the copy
   model2 = copy.deepcopy(model1)
   model2.get_constraint("capacity").rhs(
       lambda r: r.capacity + 10 if r.id == "wood" else r.capacity
   )
   solution2 = optimizer.solve(model2)   # model1 is unchanged

To use a solver's own MIP start, build the solver model yourself (see
`Accessing the Solver Model`_) and set it there.

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

.. versionchanged:: 0.3.0
   OR-Tools returns no shadow prices or reduced costs for MIPs (its MIP solver,
   SCIP, has none); they used to be reported as 0.

Accessing Shadow Prices
~~~~~~~~~~~~~~~~~~~~~~~~

Shadow prices are keyed by row name: ``"<constraint>[<index key>]"`` for an
indexed constraint, the constraint name for a single one.

.. code-block:: python

   for resource in resources:
       shadow_price = solution.get_shadow_price(f"capacity[{resource.id}]")
       print(f"{resource.name}: ${shadow_price:.2f} per unit")

**Interpretation:**

- Shadow price of $5 means: increasing capacity by 1 unit would increase profit by $5
- Shadow price of $0 means: constraint is not binding (has slack)
- Negative shadow price: relaxing constraint decreases objective (for maximization)

Accessing Reduced Costs
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Reduced costs are keyed by "<variable>[<index key>]"
   for product in products:
       reduced_cost = solution.get_reduced_cost(f"production[{product.id}]")
       if reduced_cost < 0:  # maximization: producing one unit lowers the profit
           print(f"{product.name}: would need ${-reduced_cost:.2f} more profit per unit to produce")

**Interpretation:**

- In a maximization, a reduced cost of -10 means: the profit would need to increase by
  10 per unit before producing this product pays off (minimization: +10, the cost would
  need to fall by 10)
- A reduced cost of 0 means: the variable is basic (usually positive in the solution)

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
   for resource in resources:
       shadow_price = solution.get_shadow_price(f"capacity[{resource.id}]")
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
     - ✓
     - LP only (GLOP); none for MIPs
   * - Gurobi
     - ✓
     - LP only
   * - CPLEX
     - ✓
     - LP only
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

Accessing the Solver Model
~~~~~~~~~~~~~~~~~~~~~~~~~~

LumiX has no callback API. Build the solver's own model with the adapter class
and use the solver's API on it. ``build_model()`` returns a ``gurobipy.Model``
for :class:`~lumix.solvers.gurobi_solver.LXGurobiSolver` and a
``cplex.Cplex`` for :class:`~lumix.solvers.cplex_solver.LXCPLEXSolver`; its
variables and rows carry the LumiX names (``x``, ``production[A]``). The
adapter does not relax goals; use it on models without goals.

Example: Lazy Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~

A Gurobi lazy constraint ``x + y <= 7``, added only when an incumbent violates
it (in a TSP the same pattern adds subtour elimination constraints):

.. code-block:: python

   import gurobipy as gp
   from gurobipy import GRB
   from lumix import LXLinearExpression, LXModel, LXVariable
   from lumix.solvers.gurobi_solver import LXGurobiSolver

   x = LXVariable("x").integer().bounds(lower=0, upper=10)
   y = LXVariable("y").integer().bounds(lower=0, upper=10)
   model = LXModel("lazy").add_variable(x).add_variable(y)
   model.maximize(LXLinearExpression().add_term(x, 2.0).add_term(y, 1.0))

   gurobi_model = LXGurobiSolver().build_model(model)
   gx = gurobi_model.getVarByName("x")
   gy = gurobi_model.getVarByName("y")
   gurobi_model.Params.LazyConstraints = 1

   def lazy_callback(m, where):
       if where == GRB.Callback.MIPSOL:
           vx, vy = m.cbGetSolution([gx, gy])
           if vx + vy > 7 + 1e-6:
               m.cbLazy(gx + gy <= 7)

   gurobi_model.optimize(lazy_callback)
   print(gurobi_model.ObjVal, gx.X, gy.X)   # objective 14, x = 7, y = 0

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
     - Through the gurobipy model
   * - CPLEX
     - ✓
     - Through the cplex model
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

   from lumix.solvers.gurobi_solver import LXGurobiSolver

   # Build the underlying Gurobi model
   gurobi_model = LXGurobiSolver().build_model(model)

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

   from lumix.solvers.gurobi_solver import LXGurobiSolver

   # Solve with the adapter, which keeps the Gurobi model it built
   solver = LXGurobiSolver()
   solution = solver.solve(model)

   if solution.status == "infeasible":
       gurobi_model = solver.get_solver_model()

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

Turn a conflicting constraint into a goal: LumiX adds deviation variables and
penalizes them, so the model is solved with the least violation
(see :doc:`/user-guide/goal_programming/index`):

.. code-block:: python

   # Before the solve: make the conflicting constraint soft
   model.get_constraint("min_output").as_goal(priority=1, weight=1.0)

   solution = optimizer.solve(model)
   print(solution.get_goal_deviations("min_output"))

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
