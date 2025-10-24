Extending Solution Components
==============================

Guide for extending LumiX's solution functionality.

Adding Custom Solution Classes
-------------------------------

Domain-Specific Solutions
~~~~~~~~~~~~~~~~~~~~~~~~~~

Create specialized solution classes for your domain:

.. code-block:: python

   from dataclasses import dataclass, field
   from typing import Dict, List
   from lumix.solution import LXSolution

   @dataclass
   class LXProductionSolution(LXSolution[Product]):
       """Production planning solution with industry-specific metrics."""

       # Additional metrics
       total_production: float = 0.0
       production_by_category: Dict[str, float] = field(default_factory=dict)
       resource_utilization: Dict[str, float] = field(default_factory=dict)
       bottleneck_resources: List[str] = field(default_factory=list)

       def calculate_metrics(self, products, resources):
           """Calculate production-specific metrics."""

           # Total production
           prod_values = self.get_mapped(self.production_var)
           self.total_production = sum(prod_values.values())

           # By category
           products_by_id = {p.id: p for p in products}
           from collections import defaultdict
           by_category = defaultdict(float)

           for product_id, quantity in prod_values.items():
               product = products_by_id[product_id]
               by_category[product.category] += quantity

           self.production_by_category = dict(by_category)

           # Resource utilization
           for resource in resources:
               constraint_name = f"capacity[{resource.id}]"
               shadow_price = self.get_shadow_price(constraint_name)

               if shadow_price and shadow_price > 0:
                   self.resource_utilization[resource.name] = 1.0  # Bottleneck
                   self.bottleneck_resources.append(resource.name)
               else:
                   # Estimate utilization (would need actual usage data)
                   self.resource_utilization[resource.name] = 0.85

       def report(self) -> str:
           """Generate production report."""

           lines = [
               "PRODUCTION PLANNING REPORT",
               "=" * 60,
               f"Total Production: {self.total_production:,.2f} units",
               f"Objective Value: ${self.objective_value:,.2f}",
               f"Solve Time: {self.solve_time:.3f}s",
               "",
               "Production by Category:",
           ]

           for category, quantity in sorted(self.production_by_category.items()):
               lines.append(f"  {category}: {quantity:,.2f} units")

           lines.extend([
               "",
               "Resource Utilization:",
           ])

           for resource, util in sorted(self.resource_utilization.items()):
               status = "🔴 BOTTLENECK" if util >= 0.99 else ""
               lines.append(f"  {resource}: {util:.1%} {status}")

           if self.bottleneck_resources:
               lines.extend([
                   "",
                   f"Bottleneck Resources: {', '.join(self.bottleneck_resources)}",
               ])

           return "\n".join(lines)

Financial Solutions
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   @dataclass
   class LXPortfolioSolution(LXSolution):
       """Portfolio optimization solution with financial metrics."""

       portfolio_value: float = 0.0
       portfolio_return: float = 0.0
       portfolio_risk: float = 0.0
       sharpe_ratio: float = 0.0
       holdings: Dict[str, float] = field(default_factory=dict)

       def calculate_financial_metrics(self, assets, returns, covariance_matrix):
           """Calculate portfolio metrics."""

           # Get holdings
           weights = self.get_mapped(self.weight_var)
           self.holdings = {k: v for k, v in weights.items() if v > 1e-6}

           # Portfolio return
           self.portfolio_return = sum(
               weights.get(asset.id, 0) * returns[asset.id]
               for asset in assets
           )

           # Portfolio risk (simplified - would use covariance matrix)
           self.portfolio_risk = 0.15  # Placeholder

           # Sharpe ratio
           risk_free_rate = 0.02
           if self.portfolio_risk > 0:
               self.sharpe_ratio = (self.portfolio_return - risk_free_rate) / self.portfolio_risk

Logistics Solutions
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   @dataclass
   class LXRoutingSolution(LXSolution):
       """Vehicle routing solution with logistics metrics."""

       total_distance: float = 0.0
       total_cost: float = 0.0
       num_routes: int = 0
       routes: Dict[int, List[str]] = field(default_factory=dict)
       unserved_locations: List[str] = field(default_factory=list)

       def extract_routes(self, locations):
           """Extract route information from solution."""

           route_values = self.get_mapped(self.route_var)

           # Build routes
           from collections import defaultdict
           routes_dict = defaultdict(list)

           for (vehicle_id, location_id), used in route_values.items():
               if used > 0.5:  # Binary variable threshold
                   routes_dict[vehicle_id].append(location_id)

           self.routes = dict(routes_dict)
           self.num_routes = len(self.routes)

           # Calculate metrics
           # ... distance and cost calculation ...

Adding Custom Mappers
----------------------

ORM-Integrated Mapper
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from sqlalchemy.orm import Session
   from lumix.solution import LXSolutionMapper

   class LXORMSolutionMapper(LXSolutionMapper[TModel]):
       """Solution mapper with ORM database integration."""

       def __init__(self, session: Session):
           super().__init__()
           self.session = session

       def map_and_persist(
           self,
           var: LXVariable[TModel, Any],
           solution_values: Dict[Any, float],
           attribute_name: str = "optimal_value"
       ) -> int:
           """Map values and save to database.

           Args:
               var: Variable definition
               solution_values: Solution values by key
               attribute_name: Attribute to update on model

           Returns:
               Number of records updated
           """

           # Query instances from database
           instances = self.session.query(var.model_type).all()

           # Map values to instances
           instance_values = self.map_variable_to_models(
               var, solution_values, instances
           )

           # Update instances
           for instance, value in instance_values.items():
               setattr(instance, attribute_name, value)

           # Commit to database
           self.session.commit()

           return len(instance_values)

       def bulk_update(
           self,
           var: LXVariable[TModel, Any],
           solution_values: Dict[Any, float],
           key_attribute: str = "id"
       ):
           """Bulk update using SQL UPDATE statement."""

           from sqlalchemy import update

           # Build bulk update
           updates = []
           for key, value in solution_values.items():
               updates.append({
                   key_attribute: key,
                   "optimal_value": value
               })

           # Execute bulk update
           if updates:
               stmt = update(var.model_type)
               self.session.execute(stmt, updates)
               self.session.commit()

Caching Mapper
~~~~~~~~~~~~~~

.. code-block:: python

   from functools import lru_cache

   class LXCachedSolutionMapper(LXSolutionMapper[TModel]):
       """Mapper with caching for repeated access."""

       def __init__(self):
           super().__init__()
           self._instance_cache = {}

       def map_variable_to_models(
           self,
           var: LXVariable[TModel, Any],
           solution_values: Dict[Any, float],
           model_instances: List[TModel],
       ) -> Dict[TModel, float]:
           """Map with caching."""

           # Build cache key
           cache_key = (var.name, tuple(sorted(solution_values.keys())))

           if cache_key in self._instance_cache:
               return self._instance_cache[cache_key]

           # Compute mapping
           result = super().map_variable_to_models(
               var, solution_values, model_instances
           )

           # Cache result
           self._instance_cache[cache_key] = result

           return result

       def clear_cache(self):
           """Clear the mapping cache."""
           self._instance_cache.clear()

Adding Solution Validators
---------------------------

Feasibility Validator
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from typing import List, Tuple

   class LXSolutionValidator:
       """Validate solution feasibility and correctness."""

       def __init__(self, model: LXModel, tolerance: float = 1e-6):
           self.model = model
           self.tolerance = tolerance

       def validate_solution(self, solution: LXSolution) -> List[str]:
           """Validate solution and return list of violations."""

           violations = []

           # Check variable bounds
           violations.extend(self._check_bounds(solution))

           # Check constraint satisfaction
           violations.extend(self._check_constraints(solution))

           # Check integrality
           violations.extend(self._check_integrality(solution))

           return violations

       def _check_bounds(self, solution: LXSolution) -> List[str]:
           """Check variable bounds."""

           violations = []

           for var in self.model.variables:
               values = solution.get_variable(var)

               # Handle scalar vs dict
               if isinstance(values, dict):
                   for key, value in values.items():
                       if var.lower_bound and value < var.lower_bound - self.tolerance:
                           violations.append(
                               f"Variable {var.name}[{key}] = {value} "
                               f"below lower bound {var.lower_bound}"
                           )

                       if var.upper_bound and value > var.upper_bound + self.tolerance:
                           violations.append(
                               f"Variable {var.name}[{key}] = {value} "
                               f"above upper bound {var.upper_bound}"
                           )

           return violations

       def _check_constraints(self, solution: LXSolution) -> List[str]:
           """Check constraint satisfaction."""

           # Would need to re-evaluate constraints with solution values
           # This is a simplified placeholder

           return []

       def _check_integrality(self, solution: LXSolution) -> List[str]:
           """Check integer variable integrality."""

           violations = []

           for var in self.model.variables:
               if var.var_type in [LXVarType.INTEGER, LXVarType.BINARY]:
                   values = solution.get_variable(var)

                   if isinstance(values, dict):
                       for key, value in values.items():
                           if abs(value - round(value)) > self.tolerance:
                               violations.append(
                                   f"Integer variable {var.name}[{key}] = {value} "
                                   f"is not integral"
                               )

           return violations

Solution Comparison
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   class LXSolutionComparator:
       """Compare multiple solutions."""

       @staticmethod
       def compare(
           baseline: LXSolution,
           alternative: LXSolution,
           var_names: List[str]
       ) -> Dict[str, Any]:
           """Compare two solutions."""

           comparison = {
               'objective_diff': alternative.objective_value - baseline.objective_value,
               'objective_pct_change': (
                   (alternative.objective_value - baseline.objective_value) /
                   baseline.objective_value * 100
                   if baseline.objective_value != 0 else 0
               ),
               'solve_time_diff': alternative.solve_time - baseline.solve_time,
               'variable_changes': {}
           }

           # Compare variable values
           for var_name in var_names:
               baseline_vals = baseline.variables.get(var_name, {})
               alternative_vals = alternative.variables.get(var_name, {})

               if isinstance(baseline_vals, dict):
                   changes = {
                       key: alternative_vals.get(key, 0) - baseline_vals.get(key, 0)
                       for key in set(baseline_vals.keys()) | set(alternative_vals.keys())
                   }
                   comparison['variable_changes'][var_name] = changes
               else:
                   comparison['variable_changes'][var_name] = alternative_vals - baseline_vals

           return comparison

Adding Solution Exporters
--------------------------

CSV Exporter
~~~~~~~~~~~~

.. code-block:: python

   import csv
   from pathlib import Path

   class LXSolutionCSVExporter:
       """Export solution to CSV files."""

       @staticmethod
       def export_variable(
           solution: LXSolution,
           var_name: str,
           output_path: Path,
           include_zeros: bool = False
       ):
           """Export variable values to CSV."""

           values = solution.variables.get(var_name, {})

           with open(output_path, 'w', newline='') as f:
               writer = csv.writer(f)
               writer.writerow(['Index', 'Value'])

               if isinstance(values, dict):
                   for key, value in sorted(values.items()):
                       if include_zeros or abs(value) > 1e-6:
                           writer.writerow([key, value])
               else:
                   writer.writerow(['scalar', values])

       @staticmethod
       def export_summary(solution: LXSolution, output_path: Path):
           """Export solution summary to CSV."""

           with open(output_path, 'w', newline='') as f:
               writer = csv.writer(f)
               writer.writerow(['Metric', 'Value'])
               writer.writerow(['Objective', solution.objective_value])
               writer.writerow(['Status', solution.status])
               writer.writerow(['Solve Time', solution.solve_time])

               if solution.gap is not None:
                   writer.writerow(['Gap', solution.gap])
               if solution.iterations is not None:
                   writer.writerow(['Iterations', solution.iterations])

JSON Exporter
~~~~~~~~~~~~~

.. code-block:: python

   import json
   from pathlib import Path

   class LXSolutionJSONExporter:
       """Export solution to JSON format."""

       @staticmethod
       def export(solution: LXSolution, output_path: Path):
           """Export complete solution to JSON."""

           data = {
               'metadata': {
                   'objective_value': solution.objective_value,
                   'status': solution.status,
                   'solve_time': solution.solve_time,
                   'gap': solution.gap,
                   'iterations': solution.iterations,
                   'nodes': solution.nodes,
               },
               'variables': {},
               'shadow_prices': solution.shadow_prices,
               'reduced_costs': solution.reduced_costs,
           }

           # Export variable values
           for var_name, values in solution.variables.items():
               if isinstance(values, dict):
                   # Convert keys to strings for JSON
                   data['variables'][var_name] = {
                       str(k): v for k, v in values.items()
                   }
               else:
                   data['variables'][var_name] = values

           with open(output_path, 'w') as f:
               json.dump(data, f, indent=2)

Testing Extensions
------------------

Unit Tests
~~~~~~~~~~

.. code-block:: python

   import pytest
   from lumix.solution import LXSolution

   def test_custom_solution_metrics():
       solution = LXProductionSolution(
           objective_value=1000.0,
           status="optimal",
           solve_time=1.5
       )

       # Set up test data
       products = [...]
       resources = [...]

       solution.calculate_metrics(products, resources)

       assert solution.total_production > 0
       assert len(solution.production_by_category) > 0

   def test_orm_mapper_persist():
       session = create_test_session()
       mapper = LXORMSolutionMapper(session)

       solution_values = {"A": 10.0, "B": 20.0}
       count = mapper.map_and_persist(var, solution_values)

       assert count == 2

       # Verify database
       product = session.query(Product).filter_by(id="A").first()
       assert product.optimal_value == 10.0

Integration Tests
~~~~~~~~~~~~~~~~~

.. code-block:: python

   def test_solution_workflow():
       # Build and solve model
       model = build_production_model()
       solution = optimizer.solve(model)

       # Create custom solution
       prod_solution = LXProductionSolution(**solution.__dict__)
       prod_solution.calculate_metrics(products, resources)

       # Export
       exporter = LXSolutionJSONExporter()
       exporter.export(prod_solution, "solution.json")

       # Validate
       assert prod_solution.total_production > 0
       assert Path("solution.json").exists()

Documentation
-------------

Docstring Template
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   class LXCustomSolution(LXSolution[TModel]):
       """One-line summary of custom solution class.

       Longer description explaining when to use this solution type,
       what additional functionality it provides, and any special
       considerations.

       Args:
           objective_value: Final objective function value
           status: Solution status string
           solve_time: Time taken to solve in seconds
           custom_param: Description of custom parameter

       Attributes:
           custom_metric: Description of custom metric

       Examples:
           Basic usage::

               solution = LXCustomSolution(...)
               solution.calculate_custom_metrics()
               print(solution.custom_metric)

       Note:
           Any important notes or warnings.

       See Also:
           - :class:`~lumix.solution.solution.LXSolution`
           - Related documentation
       """

Best Practices
--------------

1. **Inherit from LXSolution**

   .. code-block:: python

      # Good: Inherits all base functionality
      class LXProductionSolution(LXSolution[Product]):
          pass

      # Bad: Reimplements from scratch
      class ProductionSolution:
          pass

2. **Type All Custom Methods**

   .. code-block:: python

      def calculate_metrics(self, products: List[Product]) -> None:
          """Type-annotated for IDE support."""
          pass

3. **Document Domain-Specific Terms**

   .. code-block:: python

      # Good: Explains domain concept
      total_throughput: float = 0.0  # Total items processed per hour

      # Less clear
      total: float = 0.0

4. **Provide Factory Methods**

   .. code-block:: python

      @classmethod
      def from_base_solution(
          cls,
          base: LXSolution,
          products: List[Product],
          resources: List[Resource]
      ) -> "LXProductionSolution":
          """Create from base solution."""
          prod_solution = cls(**base.__dict__)
          prod_solution.calculate_metrics(products, resources)
          return prod_solution

Next Steps
----------

- :doc:`solution-architecture` - Deep dive into architecture
- :doc:`design-decisions` - Understand design rationale
- :doc:`/api/solution/index` - Full API reference
