Solvers Architecture
====================

Deep dive into the solvers module's architecture and design patterns.

Design Philosophy
-----------------

The solvers module implements a **solver-agnostic optimization interface** using three key patterns:

1. **Strategy Pattern**: Solver interface with multiple implementations
2. **Capability Detection**: Feature flags for automatic adaptation
3. **Fluent Builder**: Optimizer class with method chaining

Goals
~~~~~

1. **Solver Independence**: Write model once, solve with any solver
2. **Type Safety**: Full type checking and IDE support
3. **Feature Detection**: Automatic capability detection and adaptation
4. **Easy Migration**: Switch solvers without code changes
5. **Consistent API**: Same patterns across all solvers

Architecture Overview
---------------------

.. mermaid::

   classDiagram
       class LXOptimizer {
           +solver_name: str
           +use_rationals: bool
           +enable_sens: bool
           +orm: Optional[LXORMContext]
           +use_solver(name)
           +enable_rational_conversion()
           +enable_sensitivity()
           +enable_linearization()
           +solve(model) LXSolution
       }

       class LXSolverInterface {
           <<abstract>>
           +capability: LXSolverCapability
           +logger: LXModelLogger
           +build_model(model)*
           +solve(model)*
           +get_solver_model()*
       }

       class LXSolverCapability {
           +name: str
           +features: LXSolverFeature
           +max_variables: int
           +max_constraints: int
           +supports_warmstart: bool
           +supports_parallel: bool
           +supports_callbacks: bool
           +has_feature(feature) bool
           +needs_linearization_for_bilinear() bool
       }

       class LXSolverFeature {
           <<enumeration>>
           LINEAR
           INTEGER
           BINARY
           QUADRATIC_CONVEX
           QUADRATIC_NONCONVEX
           SOCP
           SOS1
           SOS2
           INDICATOR
           PWL
           SENSITIVITY_ANALYSIS
       }

       class LXORToolsSolver {
           -_model: LinearSolver
           -_variable_map: Dict
           -_constraint_map: Dict
           +build_model(model)
           +solve(model)
       }

       class LXGurobiSolver {
           -_model: gp.Model
           -_variable_map: Dict
           -_constraint_map: Dict
           +build_model(model)
           +solve(model)
       }

       class LXCPLEXSolver {
           -_model: Cplex
           -_variable_map: Dict
           -_constraint_map: Dict
           +build_model(model)
           +solve(model)
       }

       class LXGLPKSolver {
           -_model: glp_prob
           -_variable_map: Dict
           -_constraint_map: Dict
           +build_model(model)
           +solve(model)
       }

       class LXCPSATSolver {
           -_model: CpModel
           -_variable_map: Dict
           -_constraint_map: Dict
           +build_model(model)
           +solve(model)
       }

       LXOptimizer --> LXSolverInterface
       LXSolverInterface --> LXSolverCapability
       LXSolverCapability --> LXSolverFeature
       LXSolverInterface <|-- LXORToolsSolver
       LXSolverInterface <|-- LXGurobiSolver
       LXSolverInterface <|-- LXCPLEXSolver
       LXSolverInterface <|-- LXGLPKSolver
       LXSolverInterface <|-- LXCPSATSolver

Component Details
-----------------

LXOptimizer: Facade Pattern
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The optimizer is the main entry point, implementing the Facade pattern:

**Responsibilities:**

- Provide simple, high-level API
- Select and instantiate appropriate solver
- Configure solver options (rational conversion, linearization)
- Coordinate solving process
- Return unified solution format

**Implementation:**

.. code-block:: python

   @dataclass
   class LXOptimizer(Generic[TModel]):
       """Main optimizer with full generic support."""

       orm: Optional[LXORMContext[TModel]] = None
       solver_name: str = "ortools"
       use_rationals: bool = False
       enable_sens: bool = False
       use_linearization: bool = False
       rational_converter: Optional[LXRationalConverter] = None
       linearizer_config: Optional[LXLinearizerConfig] = None
       _solver: Optional[LXSolverInterface[TModel]] = None

       def use_solver(self, name: Literal["ortools", "gurobi", ...]) -> Self:
           self.solver_name = name
           return self

       def solve(self, model: LXModel[TModel], **params) -> LXSolution[TModel]:
           if self._solver is None:
               self._solver = self._create_solver()
           return self._solver.solve(model, enable_sensitivity=self.enable_sens, **params)

**Key Design Decisions:**

1. **Lazy Solver Creation**: Solver created only when needed
2. **Fluent API**: All configuration methods return ``Self``
3. **Generic Type Parameter**: Full type safety for ORM integration
4. **Optional ORM**: Can be used with or without database integration

LXSolverInterface: Strategy Pattern
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Abstract base class defining the solver contract:

**Contract:**

.. code-block:: python

   class LXSolverInterface(ABC, Generic[TModel]):
       """Abstract base class for all solver interfaces."""

       def __init__(self, capability: LXSolverCapability):
           self.capability = capability
           self.logger = LXModelLogger(f"lumix.{capability.name}")

       @abstractmethod
       def build_model(self, model: LXModel[TModel]) -> Any:
           """Build solver-specific model from LumiX model."""
           pass

       @abstractmethod
       def solve(
           self,
           model: LXModel[TModel],
           time_limit: Optional[float] = None,
           gap_tolerance: Optional[float] = None,
           **solver_params: Any,
       ) -> LXSolution[TModel]:
           """Solve the optimization model."""
           pass

       @abstractmethod
       def get_solver_model(self) -> Any:
           """Get underlying solver model for advanced usage."""
           pass

**Responsibilities:**

- Define interface all solvers must implement
- Store solver capabilities
- Provide logging infrastructure
- Maintain solver-agnostic abstraction

**Implementation Pattern:**

All solver implementations follow this pattern:

1. **Initialization**: Store capabilities, check dependencies
2. **Model Building**: Translate LXModel to solver-specific format
3. **Solving**: Execute solver and collect results
4. **Solution Extraction**: Create LXSolution from solver results

Solver Implementation Structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each solver implementation follows a consistent structure:

.. code-block:: python

   class LXSpecificSolver(LXSolverInterface):
       def __init__(self) -> None:
           super().__init__(SPECIFIC_SOLVER_CAPABILITIES)

           # Check if solver is installed
           if solver_module is None:
               raise ImportError("Solver not installed...")

           # Internal state
           self._model: Optional[SolverModel] = None
           self._variable_map: Dict[str, Union[Var, Dict[Any, Var]]] = {}
           self._constraint_map: Dict[str, Union[Constr, Dict[Any, Constr]]] = {}

       def build_model(self, model: LXModel) -> SolverModel:
           # Create native solver model
           self._model = SolverModel(model.name)

           # Build variables
           for lx_var in model.variables:
               instances = lx_var.get_instances()
               if not instances:
                   self._create_single_variable(lx_var)
               else:
                   self._create_indexed_variables(lx_var, instances)

           # Build constraints
           for lx_constraint in model.constraints:
               instances = lx_constraint.get_instances()
               if not instances:
                   self._create_single_constraint(lx_constraint)
               else:
                   self._create_indexed_constraints(lx_constraint, instances)

           # Set objective
           self._set_objective(model)

           return self._model

       def solve(self, model: LXModel, **params) -> LXSolution:
           # Build model if not already built
           if self._model is None:
               self.build_model(model)

           # Configure solver parameters
           self._configure_parameters(params)

           # Solve
           start_time = time.time()
           status = self._model.solve()
           solve_time = time.time() - start_time

           # Extract solution
           return self._extract_solution(model, status, solve_time)

**Variable Mapping Pattern:**

.. code-block:: python

   def _create_indexed_variables(self, lx_var: LXVariable, instances: List):
       var_map = {}
       for instance in instances:
           index = lx_var.index_func(instance)
           lower = lx_var.lower_bound_func(instance) if callable(...) else ...
           upper = lx_var.upper_bound_func(instance) if callable(...) else ...

           # Create solver variable
           solver_var = self._create_solver_var(
               name=f"{lx_var.name}[{index}]",
               var_type=lx_var.var_type,
               lower=lower,
               upper=upper
           )

           var_map[index] = solver_var

       self._variable_map[lx_var.name] = var_map

**Constraint Mapping Pattern:**

.. code-block:: python

   def _create_indexed_constraints(self, lx_constraint: LXConstraint, instances: List):
       constr_map = {}
       for instance in instances:
           index = lx_constraint.index_func(instance)

           # Build expression for this instance
           expr = self._build_expression(lx_constraint.lhs, instance)

           # Get RHS value
           rhs = lx_constraint.rhs_func(instance) if callable(...) else ...

           # Create solver constraint
           solver_constr = self._create_solver_constraint(
               expr=expr,
               sense=lx_constraint.sense,
               rhs=rhs,
               name=f"{lx_constraint.name}[{index}]"
           )

           constr_map[index] = solver_constr

       self._constraint_map[lx_constraint.name] = constr_map

LXSolverCapability: Feature Detection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Describes what each solver can do:

**Design:**

.. code-block:: python

   @dataclass
   class LXSolverCapability:
       name: str
       features: LXSolverFeature  # Bit flags
       max_variables: int
       max_constraints: int
       supports_warmstart: bool
       supports_parallel: bool
       supports_callbacks: bool

       def has_feature(self, feature: LXSolverFeature) -> bool:
           return bool(self.features & feature)

       def needs_linearization_for_bilinear(self) -> bool:
           return not (
               self.has_feature(LXSolverFeature.QUADRATIC_CONVEX)
               or self.has_feature(LXSolverFeature.QUADRATIC_NONCONVEX)
           )

**Usage:**

Capabilities enable automatic feature detection and adaptation:

.. code-block:: python

   # Check if solver supports feature
   if solver.capability.has_feature(LXSolverFeature.QUADRATIC_CONVEX):
       # Use native quadratic support
       pass
   else:
       # Need linearization
       pass

LXSolverFeature: Feature Flags
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Enum with bit flags for combining features:

.. code-block:: python

   class LXSolverFeature(Flag):
       LINEAR = auto()
       INTEGER = auto()
       BINARY = auto()
       MIXED_INTEGER = LINEAR | INTEGER  # Combination

       QUADRATIC_CONVEX = auto()
       QUADRATIC_NONCONVEX = auto()
       # ... more features

**Benefits:**

- Efficient storage (single integer)
- Fast checking (bitwise operations)
- Easy combinations (``|`` operator)
- Type-safe (enum)

Data Flow
---------

Solving Process
~~~~~~~~~~~~~~~

.. mermaid::

   sequenceDiagram
       participant User
       participant Optimizer
       participant Solver
       participant SolverEngine

       User->>Optimizer: solve(model)
       Optimizer->>Optimizer: _create_solver()
       Optimizer->>Solver: __init__(capabilities)
       Optimizer->>Solver: solve(model)
       Solver->>Solver: build_model(model)

       loop For each variable family
           Solver->>Solver: _create_indexed_variables()
       end

       loop For each constraint family
           Solver->>Solver: _create_indexed_constraints()
       end

       Solver->>Solver: _set_objective()
       Solver->>SolverEngine: optimize()
       SolverEngine-->>Solver: solution
       Solver->>Solver: _extract_solution()
       Solver-->>Optimizer: LXSolution
       Optimizer-->>User: LXSolution

Model Translation
~~~~~~~~~~~~~~~~~

How LXModel is translated to solver-specific format:

1. **Variable Expansion**

   .. code-block:: python

      # LumiX model
      production = LXVariable[Product, float]("production").from_data(products)

      # Translated to solver
      for product in products:
          index = product.id
          solver_var = solver.create_var(f"production[{index}]", ...)
          variable_map["production"][index] = solver_var

2. **Constraint Expansion**

   .. code-block:: python

      # LumiX constraint
      capacity = (
          LXConstraint[Resource]("capacity")
          .expression(expr)
          .le()
          .rhs(lambda r: r.capacity)
          .from_data(resources)
      )

      # Translated to solver
      for resource in resources:
          index = resource.id
          rhs_value = resource.capacity
          solver_constr = solver.add_constraint(expr_instance <= rhs_value)
          constraint_map["capacity"][index] = solver_constr

3. **Expression Building**

   .. code-block:: python

      # LumiX expression
      expr = (
          LXLinearExpression()
          .add_term(production, lambda p: p.cost)
      )

      # Translated to solver
      solver_expr = 0
      for product in products:
          coeff = product.cost
          var = variable_map["production"][product.id]
          solver_expr += coeff * var

Extension Points
----------------

Adding New Solvers
~~~~~~~~~~~~~~~~~~

To add a new solver:

1. **Create Capability Object**

   .. code-block:: python

      MY_SOLVER_CAPABILITIES = LXSolverCapability(
          name="MySolver",
          features=LXSolverFeature.LINEAR | LXSolverFeature.INTEGER,
          # ...
      )

2. **Implement Solver Interface**

   .. code-block:: python

      class LXMySolver(LXSolverInterface):
          def __init__(self):
              super().__init__(MY_SOLVER_CAPABILITIES)
              # Initialize solver

          def build_model(self, model: LXModel):
              # Translate LXModel to solver format
              pass

          def solve(self, model: LXModel, **params) -> LXSolution:
              # Solve and return solution
              pass

          def get_solver_model(self):
              return self._model

3. **Register in Optimizer**

   .. code-block:: python

      # In LXOptimizer._create_solver()
      elif self.solver_name == "mysolver":
          from .mysolver import LXMySolver
          return LXMySolver()

4. **Add Tests**

   Create comprehensive tests following existing solver test patterns

Custom Solution Extraction
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Override ``_extract_solution()`` for custom solution handling:

.. code-block:: python

   def _extract_solution(self, model: LXModel, status, solve_time) -> LXSolution:
       # Custom solution extraction logic
       variable_values = {}
       for var_name, var_map in self._variable_map.items():
           if isinstance(var_map, dict):
               variable_values[var_name] = {
                   idx: self._get_var_value(var)
                   for idx, var in var_map.items()
               }
           else:
               variable_values[var_name] = self._get_var_value(var_map)

       return LXSolution(
           status=self._translate_status(status),
           objective_value=self._model.get_objective_value(),
           variable_values=variable_values,
           solve_time=solve_time,
       )

Performance Considerations
--------------------------

Model Building
~~~~~~~~~~~~~~

**Issue**: Building solver model can be expensive for large models

**Optimizations:**

1. **Lazy Building**: Build only when solve() called
2. **Caching**: Reuse built model if model unchanged
3. **Incremental Updates**: Update only changed parts (future work)

Variable/Constraint Mapping
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Issue**: Storing maps can use significant memory

**Optimizations:**

1. **Sparse Storage**: Only store non-default values
2. **Index Compression**: Use integer indices instead of complex keys
3. **Lazy Evaluation**: Build maps on-demand

Expression Translation
~~~~~~~~~~~~~~~~~~~~~~

**Issue**: Evaluating coefficient lambdas for every instance

**Optimizations:**

1. **Constant Detection**: Cache constant coefficients
2. **Vectorization**: Batch evaluate when possible
3. **Lazy Evaluation**: Only evaluate when needed

Testing Strategy
----------------

Unit Tests
~~~~~~~~~~

Test each component in isolation:

.. code-block:: python

   def test_capability_detection():
       assert GUROBI_CAPABILITIES.has_feature(LXSolverFeature.QUADRATIC_CONVEX)
       assert not ORTOOLS_CAPABILITIES.has_feature(LXSolverFeature.QUADRATIC_CONVEX)

   def test_variable_mapping():
       solver = LXGurobiSolver()
       # Test variable creation and mapping
       pass

Integration Tests
~~~~~~~~~~~~~~~~~

Test end-to-end workflows:

.. code-block:: python

   @pytest.mark.parametrize("solver_name", ["ortools", "gurobi", "cplex"])
   def test_production_model(solver_name):
       model = build_production_model()
       optimizer = LXOptimizer().use_solver(solver_name)
       solution = optimizer.solve(model)
       assert solution.is_optimal()
       assert abs(solution.objective_value - EXPECTED) < 0.01

Solver Availability Tests
~~~~~~~~~~~~~~~~~~~~~~~~~~

Handle missing solvers gracefully:

.. code-block:: python

   def test_gurobi_not_available():
       with pytest.raises(ImportError):
           # Simulate Gurobi not installed
           optimizer = LXOptimizer().use_solver("gurobi")

Next Steps
----------

- :doc:`extending-solvers` - How to implement custom solvers
- :doc:`design-decisions` - Why things work this way
- :doc:`/api/solvers/index` - Complete API reference
- :doc:`/user-guide/solvers/index` - User guide
