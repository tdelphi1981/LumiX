Extending Solvers
=================

How to add new solver implementations to LumiX.

Overview
--------

Adding a new solver involves:

1. **Define Capabilities**: Describe what the solver supports
2. **Implement Interface**: Create solver class implementing ``LXSolverInterface``
3. **Register Solver**: Add to optimizer's solver factory
4. **Write Tests**: Comprehensive testing
5. **Document**: API docs and user guide

Step-by-Step Guide
-------------------

Step 1: Define Capabilities
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a capability object describing the solver:

.. code-block:: python

   # In src/lumix/solvers/capabilities.py

   from .capabilities import LXSolverCapability, LXSolverFeature

   MY_SOLVER_CAPABILITIES = LXSolverCapability(
       name="MySolver",
       features=(
           LXSolverFeature.LINEAR
           | LXSolverFeature.INTEGER
           | LXSolverFeature.BINARY
           | LXSolverFeature.QUADRATIC_CONVEX
           | LXSolverFeature.SOS1
           | LXSolverFeature.SOS2
           | LXSolverFeature.INDICATOR
           | LXSolverFeature.SENSITIVITY_ANALYSIS
       ),
       max_variables=10_000_000,
       max_constraints=10_000_000,
       supports_warmstart=True,
       supports_parallel=True,
       supports_callbacks=False,
   )

**Checklist:**

- [ ] Identify all supported problem types (LP, MIP, QP, SOCP, etc.)
- [ ] Check for special constraint support (SOS, indicator, etc.)
- [ ] Verify warm start capability
- [ ] Check parallel/multi-threading support
- [ ] Determine callback support
- [ ] Identify any limitations (max variables, etc.)

Step 2: Create Solver File
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a new file for your solver implementation:

.. code-block:: bash

   touch src/lumix/solvers/mysolver_solver.py

Basic structure:

.. code-block:: python

   """MySolver solver implementation for LumiX."""

   from __future__ import annotations

   import time
   from typing import Any, Dict, List, Optional, Union

   # Import solver (with try/except for graceful failure)
   try:
       import mysolver
   except ImportError:
       mysolver = None

   from ..core.constraints import LXConstraint
   from ..core.enums import LXConstraintSense, LXObjectiveSense, LXVarType
   from ..core.expressions import LXLinearExpression
   from ..core.model import LXModel
   from ..core.variables import LXVariable
   from ..solution.solution import LXSolution
   from .base import LXSolverInterface
   from .capabilities import MY_SOLVER_CAPABILITIES


   class LXMySolver(LXSolverInterface):
       """
       MySolver implementation for LumiX.

       Supports:
       - Linear Programming (LP)
       - Mixed-Integer Programming (MIP)
       - Quadratic Programming (QP)
       - Binary variables
       - Single and indexed variable families
       - Single and indexed constraint families
       """

       def __init__(self) -> None:
           """Initialize MySolver solver."""
           super().__init__(MY_SOLVER_CAPABILITIES)

           # Check if solver is installed
           if mysolver is None:
               raise ImportError(
                   "MySolver is not installed. "
                   "Install it with: pip install mysolver"
               )

           # Internal state
           self._model: Optional[mysolver.Model] = None
           self._variable_map: Dict[str, Union[Any, Dict[Any, Any]]] = {}
           self._constraint_map: Dict[str, Union[Any, Dict[Any, Any]]] = {}

       def build_model(self, model: LXModel) -> mysolver.Model:
           """Build MySolver native model from LXModel."""
           # Implementation details below
           pass

       def solve(
           self,
           model: LXModel,
           time_limit: Optional[float] = None,
           gap_tolerance: Optional[float] = None,
           **solver_params: Any,
       ) -> LXSolution:
           """Solve optimization model with MySolver."""
           # Implementation details below
           pass

       def get_solver_model(self) -> mysolver.Model:
           """Get underlying MySolver model."""
           return self._model

Step 3: Implement build_model()
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Translate LXModel to solver-specific format:

.. code-block:: python

   def build_model(self, model: LXModel) -> mysolver.Model:
       """Build MySolver native model from LXModel."""
       # Create solver model
       self._model = mysolver.Model(model.name)

       # Reset internal state
       self._variable_map = {}
       self._constraint_map = {}

       # Build variables
       for lx_var in model.variables:
           instances = lx_var.get_instances()

           if not instances:
               # Single variable (not indexed)
               self._create_single_variable(lx_var)
           else:
               # Variable family (indexed by data)
               self._create_indexed_variables(lx_var, instances)

       # Build constraints
       for lx_constraint in model.constraints:
           instances = lx_constraint.get_instances()

           if not instances:
               # Single constraint
               self._create_single_constraint(lx_constraint)
           else:
               # Constraint family (indexed by data)
               self._create_indexed_constraints(lx_constraint, instances)

       # Set objective
       self._set_objective(model)

       return self._model

**Variable Creation:**

.. code-block:: python

   def _create_single_variable(self, lx_var: LXVariable) -> None:
       """Create a single (non-indexed) variable."""
       # Get bounds
       lower = (
           lx_var.lower_bound_func(None)
           if callable(lx_var.lower_bound_func)
           else lx_var.lower_bound_func
       )
       upper = (
           lx_var.upper_bound_func(None)
           if callable(lx_var.upper_bound_func)
           else lx_var.upper_bound_func
       )

       # Map variable type
       var_type = self._map_var_type(lx_var.var_type)

       # Create solver variable
       solver_var = self._model.add_variable(
           name=lx_var.name,
           var_type=var_type,
           lower_bound=lower,
           upper_bound=upper,
       )

       # Store in map
       self._variable_map[lx_var.name] = solver_var

   def _create_indexed_variables(
       self,
       lx_var: LXVariable,
       instances: List
   ) -> None:
       """Create indexed variable family."""
       var_map = {}

       for instance in instances:
           # Get index
           index = lx_var.index_func(instance)

           # Get instance-specific bounds
           lower = (
               lx_var.lower_bound_func(instance)
               if callable(lx_var.lower_bound_func)
               else lx_var.lower_bound_func
           )
           upper = (
               lx_var.upper_bound_func(instance)
               if callable(lx_var.upper_bound_func)
               else lx_var.upper_bound_func
           )

           # Create variable
           var_type = self._map_var_type(lx_var.var_type)
           solver_var = self._model.add_variable(
               name=f"{lx_var.name}[{index}]",
               var_type=var_type,
               lower_bound=lower,
               upper_bound=upper,
           )

           var_map[index] = solver_var

       # Store family
       self._variable_map[lx_var.name] = var_map

**Variable Type Mapping:**

.. code-block:: python

   def _map_var_type(self, lx_type: LXVarType):
       """Map LumiX variable type to MySolver type."""
       mapping = {
           LXVarType.CONTINUOUS: mysolver.VarType.CONTINUOUS,
           LXVarType.INTEGER: mysolver.VarType.INTEGER,
           LXVarType.BINARY: mysolver.VarType.BINARY,
       }
       return mapping[lx_type]

**Constraint Creation:**

.. code-block:: python

   def _create_single_constraint(self, lx_constraint: LXConstraint) -> None:
       """Create a single (non-indexed) constraint."""
       # Build expression
       expr = self._build_expression(lx_constraint.lhs, None)

       # Get RHS
       rhs = (
           lx_constraint.rhs_func(None)
           if callable(lx_constraint.rhs_func)
           else lx_constraint.rhs_func
       )

       # Map sense
       sense = self._map_sense(lx_constraint.sense)

       # Create constraint
       solver_constr = self._model.add_constraint(
           expr, sense, rhs, name=lx_constraint.name
       )

       self._constraint_map[lx_constraint.name] = solver_constr

   def _create_indexed_constraints(
       self,
       lx_constraint: LXConstraint,
       instances: List
   ) -> None:
       """Create indexed constraint family."""
       constr_map = {}

       for instance in instances:
           # Get index
           index = lx_constraint.index_func(instance)

           # Build expression for this instance
           expr = self._build_expression(lx_constraint.lhs, instance)

           # Get RHS for this instance
           rhs = (
               lx_constraint.rhs_func(instance)
               if callable(lx_constraint.rhs_func)
               else lx_constraint.rhs_func
           )

           # Create constraint
           sense = self._map_sense(lx_constraint.sense)
           solver_constr = self._model.add_constraint(
               expr, sense, rhs, name=f"{lx_constraint.name}[{index}]"
           )

           constr_map[index] = solver_constr

       self._constraint_map[lx_constraint.name] = constr_map

**Expression Building:**

.. code-block:: python

   def _build_expression(
       self,
       lx_expr: LXLinearExpression,
       constraint_instance: Optional[Any]
   ):
       """Build solver expression from LumiX expression."""
       solver_expr = 0

       # Add linear terms
       for var_name, (var_family, coeff_func, where_func) in lx_expr.terms.items():
           var_instances = var_family.get_instances()

           if not var_instances:
               # Single variable
               coeff = coeff_func(constraint_instance)
               solver_var = self._variable_map[var_name]
               solver_expr += coeff * solver_var
           else:
               # Variable family
               for var_instance in var_instances:
                   # Check where clause
                   if where_func and not where_func(var_instance, constraint_instance):
                       continue

                   # Get coefficient
                   if constraint_instance is not None:
                       coeff = coeff_func(var_instance, constraint_instance)
                   else:
                       coeff = coeff_func(var_instance)

                   # Get solver variable
                   var_index = var_family.index_func(var_instance)
                   solver_var = self._variable_map[var_name][var_index]

                   # Add term
                   solver_expr += coeff * solver_var

       # Add constant
       if lx_expr.constant:
           solver_expr += lx_expr.constant

       return solver_expr

**Sense Mapping:**

.. code-block:: python

   def _map_sense(self, lx_sense: LXConstraintSense):
       """Map LumiX constraint sense to MySolver sense."""
       mapping = {
           LXConstraintSense.LE: mysolver.Sense.LE,
           LXConstraintSense.GE: mysolver.Sense.GE,
           LXConstraintSense.EQ: mysolver.Sense.EQ,
       }
       return mapping[lx_sense]

**Objective:**

.. code-block:: python

   def _set_objective(self, model: LXModel) -> None:
       """Set objective function."""
       if model.objective_expr is None:
           return

       # Build objective expression
       obj_expr = self._build_expression(model.objective_expr, None)

       # Set objective sense
       if model.objective_sense == LXObjectiveSense.MAXIMIZE:
           self._model.set_objective(mysolver.Sense.MAXIMIZE, obj_expr)
       else:
           self._model.set_objective(mysolver.Sense.MINIMIZE, obj_expr)

Step 4: Implement solve()
~~~~~~~~~~~~~~~~~~~~~~~~~~

Solve the model and extract solution:

.. code-block:: python

   def solve(
       self,
       model: LXModel,
       time_limit: Optional[float] = None,
       gap_tolerance: Optional[float] = None,
       enable_sensitivity: bool = False,
       **solver_params: Any,
   ) -> LXSolution:
       """Solve optimization model."""
       # Build model if not already built
       if self._model is None:
           self.build_model(model)

       # Set common parameters
       if time_limit is not None:
           self._model.set_param("TimeLimit", time_limit)

       if gap_tolerance is not None:
           self._model.set_param("MIPGap", gap_tolerance)

       # Set solver-specific parameters
       for param, value in solver_params.items():
           self._model.set_param(param, value)

       # Solve
       start_time = time.time()
       self._model.optimize()
       solve_time = time.time() - start_time

       # Extract and return solution
       return self._extract_solution(
           model,
           solve_time,
           enable_sensitivity
       )

**Solution Extraction:**

.. code-block:: python

   def _extract_solution(
       self,
       model: LXModel,
       solve_time: float,
       enable_sensitivity: bool
   ) -> LXSolution:
       """Extract solution from solver."""
       # Get status
       status = self._translate_status(self._model.status)

       # Get objective value
       if status in ["optimal", "feasible"]:
           objective_value = self._model.objective_value
       else:
           objective_value = None

       # Extract variable values
       variable_values = {}
       for var_name, var_map in self._variable_map.items():
           if isinstance(var_map, dict):
               # Indexed variable
               variable_values[var_name] = {
                   idx: solver_var.value
                   for idx, solver_var in var_map.items()
               }
           else:
               # Single variable
               variable_values[var_name] = var_map.value

       # Extract sensitivity (if enabled)
       shadow_prices = None
       reduced_costs = None

       if enable_sensitivity and status == "optimal":
           shadow_prices = self._extract_shadow_prices()
           reduced_costs = self._extract_reduced_costs()

       return LXSolution(
           status=status,
           objective_value=objective_value,
           variable_values=variable_values,
           solve_time=solve_time,
           shadow_prices=shadow_prices,
           reduced_costs=reduced_costs,
       )

**Status Translation:**

.. code-block:: python

   def _translate_status(self, solver_status) -> str:
       """Translate solver status to LumiX status."""
       mapping = {
           mysolver.Status.OPTIMAL: "optimal",
           mysolver.Status.FEASIBLE: "feasible",
           mysolver.Status.INFEASIBLE: "infeasible",
           mysolver.Status.UNBOUNDED: "unbounded",
           mysolver.Status.TIME_LIMIT: "time_limit",
       }
       return mapping.get(solver_status, "unknown")

Step 5: Register Solver
~~~~~~~~~~~~~~~~~~~~~~~~

Add to optimizer's solver factory:

.. code-block:: python

   # In src/lumix/solvers/base.py

   def _create_solver(self) -> LXSolverInterface[TModel]:
       """Create solver instance based on configured solver name."""
       # ... existing solvers ...

       elif self.solver_name == "mysolver":
           from .mysolver_solver import LXMySolver
           return LXMySolver()

       else:
           raise ValueError(f"Unknown solver: {self.solver_name}")

Update ``__init__.py``:

.. code-block:: python

   # In src/lumix/solvers/__init__.py

   from .mysolver_solver import LXMySolver
   from .capabilities import MY_SOLVER_CAPABILITIES

   __all__ = [
       # ... existing exports ...
       "LXMySolver",
       "MY_SOLVER_CAPABILITIES",
   ]

Step 6: Write Tests
~~~~~~~~~~~~~~~~~~~~

Create comprehensive test suite:

.. code-block:: python

   # In tests/test_mysolver.py

   import pytest
   from lumix import LXModel, LXOptimizer

   @pytest.mark.skipif(
       not mysolver_available(),
       reason="MySolver not installed"
   )
   class TestMySolver:
       def test_simple_lp(self):
           """Test simple LP problem."""
           model = build_simple_lp()
           optimizer = LXOptimizer().use_solver("mysolver")
           solution = optimizer.solve(model)

           assert solution.is_optimal()
           assert abs(solution.objective_value - EXPECTED) < 1e-6

       def test_mip(self):
           """Test MIP problem."""
           model = build_mip_model()
           optimizer = LXOptimizer().use_solver("mysolver")
           solution = optimizer.solve(model)

           assert solution.is_optimal()
           # Verify integer constraints
           for val in solution.variable_values["x"].values():
               assert abs(val - round(val)) < 1e-6

       def test_infeasible(self):
           """Test infeasible model detection."""
           model = build_infeasible_model()
           optimizer = LXOptimizer().use_solver("mysolver")
           solution = optimizer.solve(model)

           assert solution.status == "infeasible"

       def test_sensitivity(self):
           """Test sensitivity analysis."""
           if not MY_SOLVER_CAPABILITIES.has_feature(
               LXSolverFeature.SENSITIVITY_ANALYSIS
           ):
               pytest.skip("Sensitivity not supported")

           model = build_simple_lp()
           optimizer = (
               LXOptimizer()
               .use_solver("mysolver")
               .enable_sensitivity()
           )
           solution = optimizer.solve(model)

           assert solution.shadow_prices is not None
           assert solution.reduced_costs is not None

Step 7: Document
~~~~~~~~~~~~~~~~

Add API documentation and update user guide (similar to other solvers).

Best Practices
--------------

Error Handling
~~~~~~~~~~~~~~

.. code-block:: python

   # Gracefully handle missing solver
   try:
       import mysolver
   except ImportError:
       mysolver = None

   def __init__(self):
       if mysolver is None:
           raise ImportError(
               "MySolver is not installed. "
               "Install it with: pip install mysolver\\n"
               "For licensing information, visit: https://mysolver.com"
           )

Type Hints
~~~~~~~~~~

Use comprehensive type hints:

.. code-block:: python

   def solve(
       self,
       model: LXModel[TModel],
       time_limit: Optional[float] = None,
       **params: Any
   ) -> LXSolution[TModel]:
       ...

Logging
~~~~~~~

Use the built-in logger:

.. code-block:: python

   self.logger.log_model_creation(model.name, num_vars, num_constrs)
   self.logger.log_solve_start(self.capability.name)
   self.logger.log_solve_end(status, obj_value, solve_time)

Testing Checklist
~~~~~~~~~~~~~~~~~

- [ ] Simple LP
- [ ] Simple MIP
- [ ] Binary variables
- [ ] Indexed variables
- [ ] Indexed constraints
- [ ] Multi-model expressions
- [ ] Infeasible models
- [ ] Unbounded models
- [ ] Time limits
- [ ] Gap tolerance
- [ ] Sensitivity analysis (if supported)
- [ ] Solver-specific parameters

Next Steps
----------

- :doc:`solvers-architecture` - Understanding the architecture
- :doc:`/api/solvers/index` - API reference
- :doc:`/user-guide/solvers/index` - User guide examples
- Existing solver implementations for reference
