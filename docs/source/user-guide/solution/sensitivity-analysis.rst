Sensitivity Analysis
====================

Learn how to use shadow prices and reduced costs for sensitivity analysis.

Overview
--------

Sensitivity analysis helps you understand:

- **Shadow Prices**: How much the objective improves if a constraint is relaxed by one unit
- **Reduced Costs**: How much a variable's coefficient must improve before it enters the basis

.. note::

   Sensitivity information availability depends on the solver:

   - **Gurobi**: Full support for LP and QP
   - **CPLEX**: Full support for LP and QP
   - **OR-Tools**: Limited support
   - **GLPK**: Basic support for LP
   - **CP-SAT**: Not applicable (constraint programming)

Shadow Prices (Dual Values)
----------------------------

What Are Shadow Prices?
~~~~~~~~~~~~~~~~~~~~~~~

The **shadow price** (or dual value) of a constraint represents the rate of change in the
objective value per unit relaxation of the constraint.

**Interpretation**:

- Positive shadow price: Relaxing the constraint improves the objective
- Zero shadow price: Constraint is not binding (has slack)
- Negative shadow price: Depends on minimization vs. maximization

For **minimization problems**:

- Positive shadow price: Increasing RHS increases cost
- Negative shadow price: Increasing RHS decreases cost

For **maximization problems**:

- Positive shadow price: Increasing RHS increases profit
- Negative shadow price: Increasing RHS decreases profit

Accessing Shadow Prices
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get shadow price for a constraint
   shadow_price = solution.get_shadow_price("capacity_constraint")

   if shadow_price is not None:
       print(f"Shadow price: ${shadow_price:.2f}")
   else:
       print("Shadow prices not available from solver")

Example: Resource Value
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix import LXModel, LXVariable, LXConstraint, LXLinearExpression

   # Production model with resource constraints
   production = LXVariable[Product, float]("production").from_data(products)

   capacity = (
       LXConstraint[Resource]("capacity")
       .expression(
           LXLinearExpression()
           .add_term(production, lambda p, r: p.usage[r.id])
       )
       .le()
       .rhs(lambda r: r.capacity)
       .from_data(resources)
       .indexed_by(lambda r: r.id)
   )

   model = LXModel("production").add_variable(production).add_constraint(capacity)
   # ... set objective ...

   solution = optimizer.solve(model)

   # Analyze resource values
   for resource in resources:
       shadow_price = solution.get_shadow_price(f"capacity[{resource.id}]")

       if shadow_price and shadow_price > 0:
           print(f"{resource.name}:")
           print(f"  Shadow price: ${shadow_price:.2f} per unit")
           print(f"  → Adding 1 unit increases profit by ${shadow_price:.2f}")

Interpreting Shadow Prices
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Binding Constraints** (non-zero shadow price):

.. code-block:: python

   def analyze_bottlenecks(solution, resources):
       """Identify bottleneck resources."""

       bottlenecks = []

       for resource in resources:
           constraint_name = f"capacity[{resource.id}]"
           shadow_price = solution.get_shadow_price(constraint_name)

           if shadow_price and abs(shadow_price) > 0.01:
               bottlenecks.append((resource, shadow_price))

       # Sort by value
       bottlenecks.sort(key=lambda x: abs(x[1]), reverse=True)

       print("Bottleneck Resources:")
       for resource, price in bottlenecks[:5]:
           print(f"  {resource.name}: ${price:.2f}/unit")
           print(f"    Current capacity: {resource.capacity}")
           print(f"    Value of +100 units: ${price * 100:.2f}")

**Non-binding Constraints** (zero shadow price):

.. code-block:: python

   def find_slack_resources(solution, resources):
       """Find resources with excess capacity."""

       slack_resources = []

       for resource in resources:
           constraint_name = f"capacity[{resource.id}]"
           shadow_price = solution.get_shadow_price(constraint_name)

           if shadow_price is not None and abs(shadow_price) < 0.01:
               slack_resources.append(resource)

       print(f"Resources with slack capacity: {len(slack_resources)}")
       for resource in slack_resources:
           print(f"  {resource.name}: not fully utilized")

Reduced Costs
-------------

What Are Reduced Costs?
~~~~~~~~~~~~~~~~~~~~~~~

The **reduced cost** of a variable represents how much its objective coefficient must
improve before it becomes profitable to use that variable in the solution.

**Interpretation**:

- Zero reduced cost: Variable is in the basis (non-zero in solution)
- Non-zero reduced cost: Variable is at its bound

For **minimization problems**:

- Positive reduced cost: Variable is at lower bound
- Negative reduced cost: Variable is at upper bound
- Amount is cost reduction needed to make variable attractive

For **maximization problems**:

- Negative reduced cost: Variable is at lower bound
- Positive reduced cost: Variable is at upper bound
- Amount is profit increase needed to make variable attractive

Accessing Reduced Costs
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get reduced cost for a variable
   reduced_cost = solution.get_reduced_cost("production[product_A]")

   if reduced_cost is not None:
       print(f"Reduced cost: ${reduced_cost:.2f}")
   else:
       print("Reduced costs not available from solver")

Example: Product Profitability
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def analyze_product_profitability(solution, products):
       """Analyze which products should be produced."""

       production_values = solution.get_mapped(production)

       for product in products:
           var_name = f"production[{product.id}]"
           quantity = production_values.get(product.id, 0)
           reduced_cost = solution.get_reduced_cost(var_name)

           print(f"{product.name}:")
           print(f"  Production: {quantity}")

           if quantity > 0.01:
               print(f"  Status: In production")
           elif reduced_cost is not None:
               if reduced_cost > 0:
                   print(f"  Status: Not produced")
                   print(f"  Profit must increase by ${reduced_cost:.2f} to produce")
               else:
                   print(f"  Status: At upper bound")

Sensitivity Ranges
------------------

RHS Sensitivity
~~~~~~~~~~~~~~~

Estimate the range over which shadow prices are valid:

.. code-block:: python

   def estimate_rhs_range(solution, constraint_name, current_rhs, step_size=10):
       """
       Estimate valid range for RHS changes.

       Note: This is approximate. For exact ranges, use solver-specific APIs.
       """

       base_objective = solution.objective_value
       shadow_price = solution.get_shadow_price(constraint_name)

       if shadow_price is None:
           return None

       # Estimate range (simplified)
       # In practice, you'd re-solve with perturbed RHS
       print(f"Constraint: {constraint_name}")
       print(f"Current RHS: {current_rhs}")
       print(f"Shadow price: ${shadow_price:.2f}")
       print(f"Estimated objective if RHS +{step_size}: ${base_objective + shadow_price * step_size:.2f}")
       print(f"Estimated objective if RHS -{step_size}: ${base_objective - shadow_price * step_size:.2f}")

Objective Coefficient Sensitivity
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def analyze_coefficient_sensitivity(solution, variable_name, current_coeff):
       """Analyze sensitivity to objective coefficient changes."""

       reduced_cost = solution.get_reduced_cost(variable_name)

       if reduced_cost is None:
           return

       print(f"Variable: {variable_name}")
       print(f"Current coefficient: {current_coeff}")

       if abs(reduced_cost) < 0.01:
           print("Status: In basis (actively used)")
           print("Coefficient can decrease slightly before leaving basis")
       else:
           print(f"Status: At bound (not actively used)")
           print(f"Coefficient must improve by {abs(reduced_cost):.2f} to enter basis")

What-If Analysis
----------------

Simple What-If Scenarios
~~~~~~~~~~~~~~~~~~~~~~~~

Use shadow prices for quick estimates:

.. code-block:: python

   def what_if_capacity_increase(solution, resource_name, increase):
       """Estimate impact of capacity increase."""

       constraint_name = f"capacity[{resource_name}]"
       shadow_price = solution.get_shadow_price(constraint_name)

       if shadow_price is None:
           print("Shadow price not available")
           return

       current_objective = solution.objective_value
       estimated_new_objective = current_objective + shadow_price * increase

       print(f"What-if: Increase {resource_name} capacity by {increase} units")
       print(f"Current objective: ${current_objective:,.2f}")
       print(f"Estimated new objective: ${estimated_new_objective:,.2f}")
       print(f"Estimated improvement: ${shadow_price * increase:,.2f}")

       # Calculate ROI if capacity has a cost
       capacity_cost = 1000  # Example: $1000 per unit
       total_cost = increase * capacity_cost
       benefit = shadow_price * increase

       if total_cost > 0:
           roi = (benefit / total_cost) * 100
           print(f"Cost of capacity: ${total_cost:,.2f}")
           print(f"Estimated ROI: {roi:.1f}%")

Multi-Scenario Analysis
~~~~~~~~~~~~~~~~~~~~~~~~

For more accurate analysis, re-solve:

.. code-block:: python

   def compare_scenarios(base_model, resource, capacity_increases):
       """Compare multiple capacity scenarios."""

       results = []

       for increase in capacity_increases:
           # Clone model and modify capacity
           scenario_model = base_model.copy()  # Implement model cloning
           # Modify constraint RHS...

           # Solve scenario
           scenario_solution = optimizer.solve(scenario_model)

           results.append({
               'increase': increase,
               'objective': scenario_solution.objective_value,
               'solve_time': scenario_solution.solve_time,
           })

       # Compare results
       base_objective = results[0]['objective']

       print(f"Scenario Analysis: {resource.name} Capacity")
       print(f"{'Increase':<10} {'Objective':<15} {'Improvement':<15} {'Time':<10}")
       print("-" * 60)

       for r in results:
           improvement = r['objective'] - base_objective
           print(f"{r['increase']:<10} ${r['objective']:<14,.2f} ${improvement:<14,.2f} {r['solve_time']:<10.3f}s")

Practical Applications
-----------------------

Resource Planning
~~~~~~~~~~~~~~~~~

.. code-block:: python

   def recommend_capacity_investments(solution, resources, budget):
       """Recommend capacity investments given budget constraint."""

       # Collect shadow prices
       investments = []

       for resource in resources:
           constraint_name = f"capacity[{resource.id}]"
           shadow_price = solution.get_shadow_price(constraint_name)

           if shadow_price and shadow_price > 0:
               # Calculate investment attractiveness
               cost_per_unit = resource.expansion_cost  # From data model
               value_per_unit = shadow_price
               roi = value_per_unit / cost_per_unit if cost_per_unit > 0 else 0

               investments.append({
                   'resource': resource,
                   'shadow_price': shadow_price,
                   'cost_per_unit': cost_per_unit,
                   'roi': roi,
               })

       # Sort by ROI
       investments.sort(key=lambda x: x['roi'], reverse=True)

       print(f"Investment Recommendations (Budget: ${budget:,.2f})")
       print(f"{'Resource':<20} {'Shadow Price':<15} {'Cost/Unit':<12} {'ROI':<10}")
       print("-" * 70)

       total_spent = 0
       recommended = []

       for inv in investments:
           if total_spent >= budget:
               break

           # Simplified: invest in 10-unit increments
           units = min(10, (budget - total_spent) / inv['cost_per_unit'])
           if units >= 1:
               cost = units * inv['cost_per_unit']
               benefit = units * inv['shadow_price']

               recommended.append({
                   'resource': inv['resource'].name,
                   'units': units,
                   'cost': cost,
                   'benefit': benefit,
               })

               total_spent += cost

               print(f"{inv['resource'].name:<20} ${inv['shadow_price']:<14.2f} ${inv['cost_per_unit']:<11.2f} {inv['roi']:<10.2%}")

       print(f"\nRecommended Investments:")
       for rec in recommended:
           print(f"  {rec['resource']}: +{rec['units']:.0f} units (${rec['cost']:,.2f}) → benefit ${rec['benefit']:,.2f}")

Product Portfolio Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def analyze_product_portfolio(solution, products):
       """Analyze and recommend product mix changes."""

       print("Product Portfolio Analysis")
       print(f"{'Product':<20} {'Quantity':<12} {'Reduced Cost':<15} {'Recommendation'}")
       print("-" * 80)

       for product in products:
           var_name = f"production[{product.id}]"
           quantity = solution.variables.get(var_name, 0)
           reduced_cost = solution.get_reduced_cost(var_name)

           if quantity > 0.01:
               recommendation = "Keep in portfolio"
           elif reduced_cost and reduced_cost > 0:
               if reduced_cost < 10:
                   recommendation = f"Consider if profit +${reduced_cost:.2f}"
               else:
                   recommendation = "Not competitive"
           else:
               recommendation = "Review"

           rc_str = f"${reduced_cost:.2f}" if reduced_cost else "N/A"
           print(f"{product.name:<20} {quantity:<12.2f} {rc_str:<15} {recommendation}")

Solver-Specific Features
-------------------------

Gurobi Sensitivity Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Gurobi provides detailed sensitivity information
   # Access via solver-specific attributes (if using Gurobi directly)

   # Example: SA RHS ranges
   # model.SAObjUp, model.SAObjLow (requires solver-specific access)

CPLEX Sensitivity Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # CPLEX provides ranges for coefficients and RHS
   # Access via CPLEX-specific APIs

Limitations
-----------

When Shadow Prices Are Not Available
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Shadow prices may not be available when:

1. Solving **integer programs** (MIP) - only at root node
2. Using certain **solvers** (CP-SAT, some OR-Tools backends)
3. Solution is **infeasible** or **unbounded**
4. Solver settings disable sensitivity analysis

.. code-block:: python

   shadow_price = solution.get_shadow_price("capacity")

   if shadow_price is None:
       print("Shadow price not available")
       print("Possible reasons:")
       print("  - Integer variables in model")
       print("  - Solver doesn't support sensitivity")
       print("  - Solution is not optimal")

Range Validity
~~~~~~~~~~~~~~

Shadow prices are only valid within a certain range:

.. code-block:: python

   # Shadow price assumes small changes
   # For large changes, re-solve the model

   def validate_sensitivity_range(change_magnitude, typical_rhs):
       """Check if change is within reasonable sensitivity range."""

       # Rule of thumb: changes < 10% of RHS
       max_reasonable_change = 0.1 * typical_rhs

       if change_magnitude > max_reasonable_change:
           print(f"Warning: Change ({change_magnitude}) may be outside valid range")
           print(f"Recommend re-solving for accurate results")
           return False

       return True

Best Practices
--------------

1. **Check Availability**

   .. code-block:: python

      shadow_price = solution.get_shadow_price("constraint")
      if shadow_price is not None:
          # Use shadow price
          pass
      else:
          # Fall back to re-solving for sensitivity

2. **Validate LP Relaxation**

   For MIP, shadow prices come from LP relaxation:

   .. code-block:: python

      if model_has_integer_variables:
          print("Note: Shadow prices from LP relaxation")
          print("May not reflect integer variable impacts")

3. **Small Changes Only**

   .. code-block:: python

      # Shadow prices valid for small changes
      max_safe_change = current_capacity * 0.05  # 5% change

      if proposed_change > max_safe_change:
          # Re-solve instead
          solution_new = optimizer.solve(modified_model)

4. **Cross-Validate with Re-solving**

   .. code-block:: python

      # Estimate with shadow price
      estimated_benefit = shadow_price * change

      # Validate by re-solving
      actual_solution = optimizer.solve(modified_model)
      actual_benefit = actual_solution.objective_value - baseline_objective

      difference = abs(estimated_benefit - actual_benefit)
      if difference > 0.01 * abs(estimated_benefit):
          print(f"Warning: Estimate differs from actual by {difference:.2f}")

Next Steps
----------

- :doc:`accessing-solutions` - Learn about accessing solution values
- :doc:`goal-programming` - Work with goal programming solutions
- :doc:`mapping` - Map solutions to ORM models
- :doc:`/api/solution/index` - Full API reference
