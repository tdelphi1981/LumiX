Linearization Architecture
==========================

Deep dive into the linearization module's architecture and design patterns.

Design Philosophy
-----------------

The linearization module follows these key principles:

1. **Automatic Detection**: Scan models for nonlinear terms without user intervention
2. **Type-Based Selection**: Choose techniques based on variable types (binary, continuous, integer)
3. **Solver Awareness**: Leverage native solver features when available
4. **Pluggable Techniques**: Easy to add new linearization methods
5. **Late Binding**: Linearization happens during model building, not variable creation

Architecture Overview
---------------------

.. mermaid::

   classDiagram
       class LXLinearizer {
           +model: LXModel
           +capability: LXSolverCapability
           +config: LXLinearizerConfig
           +auxiliary_vars: List
           +auxiliary_constraints: List
           +needs_linearization() bool
           +linearize_model() LXModel
           -_linearize_expression() LXLinearExpression
           -_linearize_absolute() LXVariable
           -_linearize_minmax() LXVariable
           -_linearize_indicator() None
       }

       class LXBilinearLinearizer {
           +config: LXLinearizerConfig
           +auxiliary_vars: List
           +auxiliary_constraints: List
           +linearize_bilinear() LXVariable
           -_binary_and() LXVariable
           -_big_m_product() LXVariable
           -_mccormick_envelope() LXVariable
       }

       class LXPiecewiseLinearizer {
           +config: LXLinearizerConfig
           +auxiliary_vars: List
           +auxiliary_constraints: List
           +approximate_function() LXVariable
           -_generate_adaptive_breakpoints() List
           -_sos2_formulation() LXVariable
           -_incremental_formulation() LXVariable
           -_logarithmic_formulation() LXVariable
       }

       class LXLinearizerConfig {
           +default_method: LXLinearizationMethod
           +big_m_value: float
           +pwl_num_segments: int
           +pwl_method: str
           +adaptive_breakpoints: bool
           +mccormick_tighten_bounds: bool
       }

       class LXNonLinearFunctions {
           +exp() LXVariable
           +log() LXVariable
           +sqrt() LXVariable
           +power() LXVariable
           +sigmoid() LXVariable
           +sin() LXVariable
           +cos() LXVariable
           +custom() LXVariable
       }

       LXLinearizer --> LXBilinearLinearizer
       LXLinearizer --> LXPiecewiseLinearizer
       LXLinearizer --> LXLinearizerConfig
       LXNonLinearFunctions --> LXPiecewiseLinearizer

Component Details
-----------------

LXLinearizer: The Main Engine
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Responsibilities:**

- Scan model for nonlinear terms
- Coordinate linearization techniques
- Build linearized model
- Track statistics

**Key Design Decisions:**

1. **Immutability**: Original model is never modified
2. **Delegation**: Delegates to specialized linearizers
3. **Statistics**: Tracks all created auxiliary elements

**Implementation Pattern:**

.. code-block:: python

   class LXLinearizer:
       def __init__(self, model, capability, config):
           self.model = model
           self.capability = capability
           self.config = config or LXLinearizerConfig()

           # Technique instances
           self._bilinear_linearizer = LXBilinearLinearizer(self.config)
           self._piecewise_linearizer = LXPiecewiseLinearizer(self.config)

       def linearize_model(self):
           # Create new model (don't modify original)
           linearized = LXModel(f"{self.model.name}_linearized")

           # Process each nonlinear term
           for term in self.model.objective_expr.nonlinear_terms:
               self._linearize_term(term, linearized)

           # Collect auxiliary elements
           self._collect_auxiliary_elements(linearized)

           return linearized

LXBilinearLinearizer: Product Linearization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Responsibilities:**

- Detect variable type combinations
- Select appropriate linearization method
- Create auxiliary variables and constraints

**Type Dispatch Pattern:**

.. code-block:: python

   def linearize_bilinear(self, term):
       x, y = term.var1, term.var2

       # Dispatch based on types
       if x.var_type == BINARY and y.var_type == BINARY:
           return self._binary_and(x, y, term.coefficient)
       elif x.var_type == BINARY and y.var_type == CONTINUOUS:
           return self._big_m_product(x, y, term.coefficient)
       elif x.var_type == CONTINUOUS and y.var_type == CONTINUOUS:
           return self._mccormick_envelope(x, y, term.coefficient)
       else:
           raise ValueError(f"Unsupported combination")

**Auxiliary Variable Naming:**

.. code-block:: python

   def _generate_aux_name(self, prefix, name1, name2):
       self._aux_counter += 1
       return f"aux_{prefix}_{name1}_{name2}_{self._aux_counter}"

LXPiecewiseLinearizer: Function Approximation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Responsibilities:**

- Generate breakpoints (uniform or adaptive)
- Evaluate function at breakpoints
- Apply formulation method (SOS2, incremental, logarithmic)

**Adaptive Breakpoint Algorithm:**

.. code-block:: python

   def _generate_adaptive_breakpoints(self, func, x_min, x_max, num_points):
       # 1. Sample function densely
       n_sample = num_points * 10
       x_sample = np.linspace(x_min, x_max, n_sample)
       y_sample = np.array([func(x) for x in x_sample])

       # 2. Compute second derivative (curvature)
       second_deriv = np.abs(np.diff(np.diff(y_sample)))

       # 3. Convert to probability distribution
       weights = second_deriv / (np.sum(second_deriv) + 1e-10)

       # 4. Sample according to curvature
       indices = np.random.choice(
           len(x_sample),
           size=num_points - 2,
           replace=False,
           p=weights
       )

       # 5. Include endpoints and sort
       breakpoints = [x_min] + sorted([x_sample[i] for i in indices]) + [x_max]
       return breakpoints

**Formulation Selection:**

.. code-block:: python

   def approximate_function(self, func, var, num_segments, method, ...):
       # Generate breakpoints
       if adaptive:
           breakpoints = self._generate_adaptive_breakpoints(...)
       else:
           breakpoints = np.linspace(x_min, x_max, num_segments + 1)

       # Evaluate function
       values = [func(bp) for bp in breakpoints]

       # Apply formulation
       if method == "sos2":
           return self._sos2_formulation(var, breakpoints, values)
       elif method == "incremental":
           return self._incremental_formulation(var, breakpoints, values)
       elif method == "logarithmic":
           return self._logarithmic_formulation(var, breakpoints, values)

LXLinearizerConfig: Configuration Management
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Design Pattern:** Dataclass with sensible defaults

.. code-block:: python

   @dataclass
   class LXLinearizerConfig:
       # General settings
       default_method: LXLinearizationMethod = MCCORMICK
       tolerance: float = 1e-6
       verbose_logging: bool = True

       # Big-M settings
       big_m_value: float = 1e6

       # PWL settings
       pwl_num_segments: int = 20
       pwl_method: Literal["sos2", "incremental", "logarithmic"] = "sos2"
       adaptive_breakpoints: bool = True

       # McCormick settings
       mccormick_tighten_bounds: bool = True

**Benefits:**

- Type-safe configuration
- Clear defaults
- Easy to extend

Data Flow
---------

Linearization Process
~~~~~~~~~~~~~~~~~~~~~

.. mermaid::

   sequenceDiagram
       participant User
       participant Linearizer
       participant Scanner
       participant BilinearLin
       participant PiecewiseLin
       participant Model

       User->>Linearizer: linearize_model()
       Linearizer->>Scanner: Scan objective
       Scanner-->>Linearizer: [bilinear_term, pwl_term]

       Linearizer->>BilinearLin: linearize_bilinear(term)
       BilinearLin->>BilinearLin: Detect types (continuous × continuous)
       BilinearLin->>BilinearLin: Apply McCormick
       BilinearLin-->>Linearizer: aux_var, constraints

       Linearizer->>PiecewiseLin: approximate_function(term)
       PiecewiseLin->>PiecewiseLin: Generate adaptive breakpoints
       PiecewiseLin->>PiecewiseLin: Apply SOS2 formulation
       PiecewiseLin-->>Linearizer: aux_var, constraints

       Linearizer->>Model: Build linearized model
       Model-->>User: Linearized model

Auxiliary Element Collection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def linearize_model(self):
       linearized = LXModel(f"{self.model.name}_linearized")

       # ... process terms ...

       # Collect from bilinear linearizer
       for aux_var in self._bilinear_linearizer.auxiliary_vars:
           if aux_var not in self.auxiliary_vars:
               linearized.add_variable(aux_var)
               self.auxiliary_vars.append(aux_var)

       # Collect from piecewise linearizer
       for aux_var in self._piecewise_linearizer.auxiliary_vars:
           if aux_var not in self.auxiliary_vars:
               linearized.add_variable(aux_var)
               self.auxiliary_vars.append(aux_var)

       # Similar for constraints
       ...

Extension Points
----------------

Adding New Linearization Techniques
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To add a new linearization technique:

1. **Create New Linearizer Class:**

.. code-block:: python

   class LXConicLinearizer:
       """Linearize second-order cone constraints."""

       def __init__(self, config: LXLinearizerConfig):
           self.config = config
           self.auxiliary_vars = []
           self.auxiliary_constraints = []

       def linearize_cone(self, term: LXConicTerm) -> LXVariable:
           # Implementation
           ...

2. **Integrate into Main Engine:**

.. code-block:: python

   class LXLinearizer:
       def __init__(self, model, capability, config):
           # ... existing code ...
           self._conic_linearizer = LXConicLinearizer(self.config)

       def _linearize_expression(self, expr):
           # ... existing code ...
           elif isinstance(term, LXConicTerm):
               if self.capability.needs_linearization_for_conic():
                   aux_var = self._conic_linearizer.linearize_cone(term)
                   linear_expr = linear_expr + aux_var

3. **Add Configuration:**

.. code-block:: python

   @dataclass
   class LXLinearizerConfig:
       # ... existing fields ...

       # Conic settings
       conic_approximation_order: int = 2

Custom Function Approximations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add to ``LXNonLinearFunctions``:

.. code-block:: python

   class LXNonLinearFunctions:
       # ... existing methods ...

       @staticmethod
       def tanh(var, linearizer, segments=40):
           """Hyperbolic tangent: tanh(x)"""
           return linearizer.approximate_function(
               lambda x: math.tanh(x),
               var,
               num_segments=segments,
               adaptive=True
           )

Testing Strategy
----------------

Unit Tests
~~~~~~~~~~

Test individual linearization techniques:

.. code-block:: python

   def test_mccormick_envelope():
       """Test McCormick envelope for continuous × continuous."""
       config = LXLinearizerConfig()
       linearizer = LXBilinearLinearizer(config)

       # Create bilinear term
       x = LXVariable[Model, float]("x").bounds(lower=0, upper=10)
       y = LXVariable[Model, float]("y").bounds(lower=0, upper=5)
       term = LXBilinearTerm(x, y, 1.0)

       # Linearize
       z = linearizer.linearize_bilinear(term)

       # Verify
       assert z is not None
       assert len(linearizer.auxiliary_vars) == 1
       assert len(linearizer.auxiliary_constraints) == 4  # McCormick

Integration Tests
~~~~~~~~~~~~~~~~~

Test end-to-end linearization:

.. code-block:: python

   def test_linearize_production_model():
       """Test linearization of production planning model."""
       model = build_production_model()  # Contains bilinear revenue

       config = LXLinearizerConfig()
       optimizer = LXOptimizer().use_solver("glpk")
       linearizer = LXLinearizer(model, optimizer.get_capability(), config)

       # Linearize
       linearized = linearizer.linearize_model()

       # Verify structure
       assert linearized.name == "production_linearized"
       assert len(linearized.variables) > len(model.variables)

       # Solve
       solution = optimizer.solve(linearized)
       assert solution.is_optimal()

Accuracy Tests
~~~~~~~~~~~~~~

Validate approximation accuracy:

.. code-block:: python

   def test_pwl_approximation_accuracy():
       """Test piecewise-linear approximation accuracy."""
       import numpy as np

       config = LXLinearizerConfig(pwl_num_segments=50)
       linearizer = LXPiecewiseLinearizer(config)

       # Test exponential approximation
       x_test = np.linspace(0, 5, 100)
       max_error = 0

       for x in x_test:
           true_value = math.exp(x)
           # Evaluate PWL approximation at x
           approx_value = evaluate_pwl_at_point(linearizer, x)
           error = abs(true_value - approx_value) / true_value
           max_error = max(max_error, error)

       # Verify accuracy
       assert max_error < 0.01, f"Approximation error too large: {max_error}"

Performance Considerations
--------------------------

Memory Management
~~~~~~~~~~~~~~~~~

**Auxiliary Variable Storage:**

- Each linearizer maintains its own auxiliary lists
- Main engine collects and deduplicates
- Use generator patterns for large models

**Optimization:**

.. code-block:: python

   # Good: Lazy evaluation
   def get_auxiliary_vars(self):
       for linearizer in self._linearizers:
           yield from linearizer.auxiliary_vars

   # Avoid: Eagerly creating large lists
   all_vars = (
       self._bilinear_linearizer.auxiliary_vars +
       self._piecewise_linearizer.auxiliary_vars +
       ...  # Memory spike!
   )

Computational Complexity
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Operation
     - Complexity
     - Notes
   * - Scan model
     - O(terms)
     - Linear in number of terms
   * - Bilinear linearization
     - O(1) per term
     - Fixed number of constraints
   * - PWL (SOS2)
     - O(n) per term
     - n = num_segments
   * - PWL (incremental)
     - O(n) per term
     - More variables than SOS2
   * - Adaptive breakpoints
     - O(n²) per function
     - Dense sampling + sorting

Future Enhancements
-------------------

Planned Features
~~~~~~~~~~~~~~~~

1. **Logarithmic Formulation**: Complete implementation of Gray code encoding
2. **Bound Tightening**: Automatic bound propagation for McCormick
3. **Conic Constraints**: Linearization of second-order cone constraints
4. **Custom SOS Types**: Support for SOS1 and higher-order SOS
5. **Parallel Linearization**: Process terms in parallel for large models

See Also
--------

- :doc:`extending-linearization` - How to extend linearization
- :doc:`design-decisions` - Design rationale
- :doc:`/user-guide/linearization/index` - User guide
- :doc:`/api/linearization/index` - API reference
