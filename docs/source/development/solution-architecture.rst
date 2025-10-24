Solution Module Architecture
============================

Deep dive into the solution module's architecture and design patterns.

Design Philosophy
-----------------

The solution module implements a **type-safe, data-centric** approach to solution handling
with three key principles:

1. **Dual Indexing**: Maintain both solver indices and data keys for maximum flexibility
2. **Type Safety**: Full type inference for all solution access methods
3. **Optional Metadata**: Gracefully handle solver-specific information availability

Architecture Overview
---------------------

.. mermaid::

   classDiagram
       class LXSolution {
           +objective_value: float
           +status: str
           +solve_time: float
           +variables: Dict[str, Union[float, Dict]]
           +mapped: Dict[str, Dict]
           +shadow_prices: Dict[str, float]
           +reduced_costs: Dict[str, float]
           +goal_deviations: Dict[str, Dict]
           +get_variable(var)
           +get_mapped(var)
           +get_shadow_price(name)
           +get_reduced_cost(name)
           +get_goal_deviations(name)
           +is_goal_satisfied(name, tolerance)
           +get_total_deviation(name)
           +is_optimal()
           +is_feasible()
           +summary()
       }

       class LXSolutionMapper {
           +map_variable_to_models(var, values, instances)
           +map_multi_indexed_variable(var, values)
       }

       LXSolution --> LXSolutionMapper: uses for mapping

Component Details
-----------------

LXSolution: The Solution Container
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Key Insight**: Solutions maintain TWO representations of variable values:

1. **Direct** (``variables``): Uses solver's internal indices
2. **Mapped** (``mapped``): Uses data model keys

**Implementation**:

.. code-block:: python

   @dataclass
   class LXSolution(Generic[TModel]):
       objective_value: float
       status: str
       solve_time: float

       # Direct access (solver indices)
       variables: Dict[str, Union[float, Dict[Any, float]]] = field(default_factory=dict)

       # Mapped access (data keys)
       mapped: Dict[str, Dict[Any, float]] = field(default_factory=dict)

       # Optional sensitivity data
       shadow_prices: Dict[str, float] = field(default_factory=dict)
       reduced_costs: Dict[str, float] = field(default_factory=dict)

       # Goal programming
       goal_deviations: Dict[str, Dict[str, Union[float, Dict[Any, float]]]] = field(
           default_factory=dict
       )

       # Solver-specific metadata
       gap: Optional[float] = None
       iterations: Optional[int] = None
       nodes: Optional[int] = None

**Why Two Representations?**

- **Direct**: For debugging, solver integration, raw access
- **Mapped**: For business logic, reporting, database updates

Dual Indexing Pattern
~~~~~~~~~~~~~~~~~~~~~~

Example of how dual indexing works:

.. code-block:: python

   # User defines variable
   production = (
       LXVariable[Product, float]("production")
       .indexed_by(lambda p: p.id)  # Key function
       .from_data([
           Product(id="A", name="Widget"),
           Product(id="B", name="Gadget"),
       ])
   )

   # Solver creates internal variables
   # production[0] = 10.0  (solver index)
   # production[1] = 20.0  (solver index)

   # LumiX populates solution:
   solution.variables = {
       "production": {0: 10.0, 1: 20.0}  # Solver indices
   }

   solution.mapped = {
       "production": {"A": 10.0, "B": 20.0}  # Data keys
   }

   # User can access either way:
   direct = solution.variables["production"][0]  # → 10.0
   mapped = solution.mapped["production"]["A"]    # → 10.0

Goal Programming Data Structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Goal deviations use nested dictionaries:

.. code-block:: python

   @dataclass
   class LXSolution:
       # Structure: {goal_name: {deviation_type: value}}
       goal_deviations: Dict[str, Dict[str, Union[float, Dict[Any, float]]]]

**Examples**:

.. code-block:: python

   # Scalar goal
   {
       "total_cost_target": {
           "pos": 0.0,      # No over-achievement
           "neg": 150.5     # Under by 150.5
       }
   }

   # Indexed goal
   {
       "demand_target": {
           "pos": {"product_A": 10.0, "product_B": 0.0},
           "neg": {"product_A": 0.0, "product_B": 5.0}
       }
   }

Type System
-----------

Generics for Type Safety
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   TModel = TypeVar("TModel")  # Data model type
   TValue = TypeVar("TValue", int, float)  # Variable value type

   class LXSolution(Generic[TModel]):
       def get_variable(
           self, var: LXVariable[TModel, TValue]
       ) -> Union[TValue, Dict[Any, TValue]]:
           """Get variable value with full type inference."""
           return self.variables.get(var.name, 0)  # type: ignore

       def get_mapped(
           self, var: LXVariable[TModel, TValue]
       ) -> Dict[Any, TValue]:
           """Get values mapped by index keys."""
           return self.mapped.get(var.name, {})  # type: ignore

**Benefits**:

- IDE autocomplete for all parameters
- mypy type checking
- Runtime type validation (if desired)

Optional Metadata Handling
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sensitivity data and solver-specific info may not always be available:

.. code-block:: python

   class LXSolution:
       def get_shadow_price(self, constraint_name: str) -> Optional[float]:
           """Get shadow price (dual value) for constraint.

           Returns:
               Shadow price if available, None otherwise
           """
           return self.shadow_prices.get(constraint_name)

       def get_reduced_cost(self, var_name: str) -> Optional[float]:
           """Get reduced cost for variable.

           Returns:
               Reduced cost if available, None otherwise
           """
           return self.reduced_costs.get(var_name)

**Why Optional?**

- Some solvers don't provide sensitivity data
- Integer programs don't have dual values
- User may disable sensitivity analysis

LXSolutionMapper: Reverse Mapping
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Maps from keys back to model instances:

.. code-block:: python

   class LXSolutionMapper(Generic[TModel]):
       def map_variable_to_models(
           self,
           var: LXVariable[TModel, Any],
           solution_values: Dict[Any, float],
           model_instances: List[TModel],
       ) -> Dict[TModel, float]:
           """Map variable values to model instances."""

           if var.index_func is None:
               return {}

           result = {}
           for instance in model_instances:
               key = var.index_func(instance)
               if key in solution_values:
                   result[instance] = solution_values[key]

           return result

**Workflow**:

1. User provides model instances and solution values (by key)
2. For each instance, compute its key using ``index_func``
3. Look up value in solution by key
4. Build mapping from instance to value

Multi-Indexed Mapping
~~~~~~~~~~~~~~~~~~~~~~

For cartesian product variables:

.. code-block:: python

   def map_multi_indexed_variable(
       self,
       var: LXVariable,
       solution_values: Dict[tuple, float],
   ) -> Dict[tuple, float]:
       """Map multi-indexed variable values to model instance tuples."""

       if var._cartesian is None or not var._cartesian.dimensions:
           return {}

       # Get instances from each dimension
       model_instances_by_dim = [
           dim.get_instances() for dim in var._cartesian.dimensions
       ]

       # Build reverse mappings: key -> instance
       reverse_maps = []
       for dim, instances in zip(var._cartesian.dimensions, model_instances_by_dim):
           key_to_instance = {dim.key_func(inst): inst for inst in instances}
           reverse_maps.append(key_to_instance)

       # Transform key tuples to instance tuples
       result = {}
       for key_tuple, value in solution_values.items():
           try:
               instance_tuple = tuple(
                   reverse_maps[i][key] for i, key in enumerate(key_tuple)
               )
               result[instance_tuple] = value
           except (KeyError, IndexError):
               continue  # Skip if mapping fails

       return result

**Key Idea**: Use dimension key functions in reverse to map keys → instances.

Data Flow
---------

Solution Building Phase
~~~~~~~~~~~~~~~~~~~~~~~

.. mermaid::

   sequenceDiagram
       participant Solver
       participant Adapter
       participant Solution

       Solver->>Adapter: Raw solution data
       Adapter->>Adapter: Extract variable values
       Adapter->>Adapter: Extract metadata
       Adapter->>Solution: Create LXSolution
       Solution->>Solution: Populate variables (solver indices)
       Solution->>Solution: Populate mapped (data keys)
       Solution->>Solution: Populate sensitivity data
       Solution-->>Adapter: Return solution

**Steps**:

1. Solver returns raw solution (solver-specific format)
2. Adapter extracts variable values, status, objective, etc.
3. Adapter builds both ``variables`` (solver indices) and ``mapped`` (data keys)
4. Adapter extracts optional sensitivity data
5. Adapter creates and returns ``LXSolution`` instance

Solution Access Phase
~~~~~~~~~~~~~~~~~~~~~

.. mermaid::

   sequenceDiagram
       participant User
       participant Solution
       participant Variable

       User->>Solution: get_mapped(production)
       Solution->>Variable: Access var.name
       Variable-->>Solution: "production"
       Solution->>Solution: Lookup mapped["production"]
       Solution-->>User: {"A": 10.0, "B": 20.0}

       User->>Solution: get_shadow_price("capacity")
       Solution->>Solution: Lookup shadow_prices["capacity"]
       Solution-->>User: 5.25 or None

Performance Considerations
--------------------------

Memory Usage
~~~~~~~~~~~~

**Storage Overhead**:

- Solution stores values twice (direct + mapped)
- Trade-off: Memory for convenience and flexibility

**Optimization Strategies**:

.. code-block:: python

   # Only populate mapped if needed
   if user_requested_mapped:
       solution.mapped = build_mapped_values()
   else:
       solution.mapped = {}  # Empty to save memory

Lookup Performance
~~~~~~~~~~~~~~~~~~

All lookups are ``O(1)`` dictionary access:

.. code-block:: python

   # Fast
   value = solution.mapped["production"]["product_A"]  # O(1)

   # Avoid linear search
   # Bad: O(n)
   for key in solution.mapped["production"]:
       if key == "product_A":
           value = solution.mapped["production"][key]

Extension Points
----------------

Custom Solution Classes
~~~~~~~~~~~~~~~~~~~~~~~

Subclass for domain-specific solutions:

.. code-block:: python

   @dataclass
   class LXProductionSolution(LXSolution[Product]):
       """Production-specific solution with extra metrics."""

       total_production: float = 0.0
       capacity_utilization: Dict[str, float] = field(default_factory=dict)

       def calculate_metrics(self, resources):
           """Calculate production-specific metrics."""
           self.total_production = sum(self.mapped["production"].values())

           # Calculate utilization
           for resource in resources:
               shadow_price = self.get_shadow_price(f"capacity[{resource.id}]")
               if shadow_price and shadow_price > 0:
                   self.capacity_utilization[resource.id] = 1.0  # Fully utilized
               else:
                   self.capacity_utilization[resource.id] = 0.8  # Estimate

Custom Mappers
~~~~~~~~~~~~~~

Extend mapper for specialized mapping:

.. code-block:: python

   class LXORMSolutionMapper(LXSolutionMapper[TModel]):
       """Mapper with ORM integration."""

       def __init__(self, session):
           super().__init__()
           self.session = session

       def map_and_save(
           self,
           var: LXVariable[TModel, Any],
           solution_values: Dict[Any, float],
       ) -> int:
           """Map values and save to database."""

           # Get instances from database
           model_instances = self.session.query(var.model_type).all()

           # Map values
           instance_values = self.map_variable_to_models(
               var, solution_values, model_instances
           )

           # Update database
           for instance, value in instance_values.items():
               instance.optimal_value = value

           self.session.commit()
           return len(instance_values)

Testing Strategy
----------------

Unit Tests
~~~~~~~~~~

Test individual methods:

.. code-block:: python

   def test_get_variable():
       solution = LXSolution(
           objective_value=100.0,
           status="optimal",
           solve_time=1.5
       )

       production = LXVariable[Product, float]("production")
       solution.variables["production"] = {0: 10.0, 1: 20.0}

       value = solution.get_variable(production)
       assert value == {0: 10.0, 1: 20.0}

   def test_is_goal_satisfied():
       solution = LXSolution(...)
       solution.goal_deviations["demand"] = {"pos": 0.0, "neg": 0.0}

       assert solution.is_goal_satisfied("demand") is True

Integration Tests
~~~~~~~~~~~~~~~~~

Test with real solvers:

.. code-block:: python

   def test_solution_from_solver():
       model = build_production_model()
       optimizer = LXOptimizer().use_solver("gurobi")

       solution = optimizer.solve(model)

       assert solution.is_optimal()
       assert solution.objective_value > 0
       assert len(solution.mapped["production"]) > 0

Type Tests
~~~~~~~~~~

Verify type annotations:

.. code-block:: python

   # mypy should pass
   solution: LXSolution[Product] = optimizer.solve(model)
   value: Union[float, Dict[Any, float]] = solution.get_variable(production)
   mapped: Dict[Any, float] = solution.get_mapped(production)

Next Steps
----------

- :doc:`extending-solution` - How to extend solution functionality
- :doc:`design-decisions` - Why things work this way
- :doc:`/api/solution/index` - Full API reference
