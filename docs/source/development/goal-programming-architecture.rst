Goal Programming Architecture
==============================

Deep dive into the goal programming module's architecture and design patterns.

Design Philosophy
-----------------

The goal programming module implements a **declarative, data-driven** approach to multi-objective
optimization using four key design patterns:

1. **Automatic Transformation**: Hard constraints automatically convert to soft constraints
2. **Semantic Indexing**: Deviation variables indexed by Goal instances for business meaning
3. **Flexible Solving**: Support for both weighted (single-solve) and sequential (multi-solve) modes
4. **Type Safety**: Full generic type support throughout the module

Architecture Overview
---------------------

Module Structure
~~~~~~~~~~~~~~~~

.. mermaid::

   graph TD
       A[User Constraint] -->|.as_goal| B[LXGoalMetadata]
       B --> C[Relaxation Module]
       C --> D[RelaxedConstraint]
       D --> E[Deviation Variables]
       D --> F[Goal Instances]
       D --> G[Equality Constraint]
       E --> H[Objective Builder]
       F --> H
       H --> I[Weighted/Sequential]
       I --> J[LXGoalProgrammingSolver]
       J --> K[Solution with Deviations]

       style A fill:#e1f5ff
       style B fill:#fff4e1
       style C fill:#ffe1e1
       style D fill:#e1ffe1
       style E fill:#f0e1ff
       style F fill:#e8f4f8
       style G fill:#ffe8e8
       style H fill:#e8ffe8
       style I fill:#f0e8ff
       style J fill:#e8f4ff
       style K fill:#fff0e8

**Key modules**:

- ``goal.py``: Data structures (LXGoal, LXGoalMetadata, LXGoalMode)
- ``relaxation.py``: Constraint relaxation and deviation variable creation
- ``objective_builder.py``: Objective function construction
- ``solver.py``: Sequential solving orchestration

Component Architecture
----------------------

goal.py: Metadata and Data Structures
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Define goal programming metadata and configuration.

.. code-block:: python

   # Core data structures
   class LXGoalMode(Enum):
       WEIGHTED = "weighted"      # Single solve
       SEQUENTIAL = "sequential"  # Multiple solves

   @dataclass
   class LXGoalMetadata:
       priority: int                        # 0 = custom, 1+ = goal priorities
       weight: float                        # Relative weight within priority
       constraint_sense: LXConstraintSense  # Original constraint type
       undesired_deviations: Set[str]       # {'pos', 'neg', or both}

   @dataclass
   class LXGoal:
       id: str                    # Unique goal identifier
       constraint_name: str       # Original constraint name
       priority: int              # Priority level
       weight: float              # Goal weight
       constraint_sense: LXConstraintSense
       target_value: Optional[float]  # RHS value if constant
       instance_id: Optional[Any]     # Original data instance ID

**Design decisions**:

- **LXGoal as data model**: Deviation variables are indexed by LXGoal instances, providing
  semantic meaning to deviations (e.g., "Route 5 needs 3 buses" instead of "neg_dev[0] = 3")

- **Automatic deviation determination**: ``__post_init__`` automatically sets ``undesired_deviations``
  based on ``constraint_sense`` (LE → pos, GE → neg, EQ → both)

- **Priority 0 for custom objectives**: Allows mixing traditional objectives with goal programming

relaxation.py: Constraint Transformation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Transform hard constraints to soft constraints with deviation variables.

.. code-block:: python

   class RelaxedConstraint(Generic[TModel]):
       constraint: LXConstraint[TModel]      # Relaxed equality constraint
       pos_deviation: LXVariable[LXGoal, float]  # Positive deviation variable
       neg_deviation: LXVariable[LXGoal, float]  # Negative deviation variable
       goal_metadata: LXGoalMetadata
       goal_instances: List[LXGoal]

**Transformation process**:

1. **Create Goal instances**: One per constraint instance (or single goal for non-indexed)
2. **Create deviation variables**: Indexed by Goal instances, not original data
3. **Build equality constraint**: ``expr + neg_dev - pos_dev = rhs``
4. **Preserve metadata**: Goal metadata and instances stored in RelaxedConstraint

**Example transformation**:

.. code-block:: python

   # Original: production >= demand
   # Indexed by Product instances

   # After relaxation:
   # - Goal instances: [Goal("demand_A"), Goal("demand_B"), ...]
   # - Variables: pos_dev[Goal("demand_A")], neg_dev[Goal("demand_A")], ...
   # - Constraint: production[A] + neg_dev[Goal_A] - pos_dev[Goal_A] = demand[A]

**Design decisions**:

- **Generic type support**: ``RelaxedConstraint[TModel]`` maintains type safety
- **Goal instance creation**: Maps constraint instances to Goal instances for semantic indexing
- **Variable naming convention**: ``{constraint_name}_{pos|neg}_dev``

objective_builder.py: Objective Construction
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Build weighted or sequential objectives from relaxed constraints.

.. code-block:: python

   def build_weighted_objective(
       relaxed_constraints: List[RelaxedConstraint],
       base: float = 10.0,
       exponent_offset: int = 6
   ) -> LXLinearExpression:
       """
       Single objective with exponential priority scaling.

       Priority 1 → 10^6
       Priority 2 → 10^5
       Priority 3 → 10^4
       """

   def build_sequential_objectives(
       relaxed_constraints: List[RelaxedConstraint]
   ) -> List[Tuple[int, LXLinearExpression]]:
       """
       Multiple objectives for lexicographic optimization.

       Returns: [(priority, objective), ...]
       """

**Weight calculation**:

.. code-block:: python

   def priority_to_weight(priority: int, base: float = 10.0,
                          exponent_offset: int = 6) -> float:
       if priority == 0:
           return 1.0  # Custom objectives
       return base ** (exponent_offset - priority)

**Design decisions**:

- **Exponential scaling**: Ensures higher priorities dominate lower priorities
- **Configurable base**: Allow custom weight scaling if needed
- **Priority 0 handling**: Custom objectives use weight 1.0 (no scaling)
- **Sequential excludes priority 0**: Custom objectives handled separately

solver.py: Orchestration
~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Orchestrate sequential (lexicographic) goal programming.

.. code-block:: python

   class LXGoalProgrammingSolver:
       def __init__(self, optimizer: LXOptimizer):
           self.optimizer = optimizer

       def solve_sequential(
           self, model: LXModel[TModel],
           relaxed_constraints: List[RelaxedConstraint[TModel]],
           **solver_params
       ) -> LXSolution[TModel]:
           """
           Solve one priority at a time:
           1. Optimize priority 1
           2. Fix priority 1 deviations
           3. Optimize priority 2
           4. Repeat
           """

       def solve_weighted(
           self, model: LXModel[TModel],
           **solver_params
       ) -> LXSolution[TModel]:
           """Pass-through to standard optimizer."""

**Sequential solving algorithm**:

1. Build objectives for each priority level
2. For each priority (sorted):
   a. Set objective for current priority
   b. Solve
   c. Record optimal deviation values
   d. Fix deviations as constraints (conceptually; currently via large weights)
3. Return final solution

**Design decisions**:

- **Weighted mode pass-through**: Weighted mode is handled in LXModel, solver just calls optimizer
- **Sequential mode complexity**: Sequential mode requires multiple solve iterations
- **Deviation fixing**: Currently uses implicit fixing via weight dominance

Data Flow
---------

Model Building Phase
~~~~~~~~~~~~~~~~~~~~

.. mermaid::

   sequenceDiagram
       participant User
       participant Constraint
       participant Metadata
       participant Relaxation
       participant Model

       User->>Constraint: .as_goal(priority, weight)
       Constraint->>Metadata: Create LXGoalMetadata
       Metadata-->>Constraint: Goal configuration
       Constraint->>Model: Add to model
       Note over Model: Stores goal metadata
       Model->>Relaxation: relax_constraint()
       Relaxation-->>Model: RelaxedConstraint

**Key point**: Relaxation happens when model is being prepared for solving, not during constraint definition.

Solving Phase (Weighted)
~~~~~~~~~~~~~~~~~~~~~~~~~

.. mermaid::

   sequenceDiagram
       participant Model
       participant Objective
       participant Solver
       participant Solution

       Model->>Model: Identify goal constraints
       Model->>Objective: build_weighted_objective()
       Objective-->>Model: Single objective expr
       Model->>Solver: solve(model)
       Solver->>Solver: Single optimization run
       Solver-->>Solution: Optimal values + deviations

Solving Phase (Sequential)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. mermaid::

   sequenceDiagram
       participant Solver
       participant Objective
       participant Optimizer
       participant Model

       Solver->>Objective: build_sequential_objectives()
       Objective-->>Solver: [(p1, obj1), (p2, obj2), ...]

       loop For each priority
           Solver->>Model: Set objective = obj_p
           Solver->>Optimizer: solve(model)
           Optimizer-->>Solver: Solution at priority p
           Solver->>Solver: Record deviation values
           Note over Solver: Fix deviations for next priority
       end

       Solver-->>Solver: Return final solution

Type System
-----------

Generic Type Flow
~~~~~~~~~~~~~~~~~

.. code-block:: python

   TModel = TypeVar("TModel")  # Original data model type

   # Constraint with original type
   constraint: LXConstraint[Product]

   # Relaxed constraint maintains type
   relaxed: RelaxedConstraint[Product]

   # Deviation variables are indexed by LXGoal
   pos_dev: LXVariable[LXGoal, float]
   neg_dev: LXVariable[LXGoal, float]

   # Goal instances map to original instances
   goal: LXGoal
   goal.instance_id: str  # Product ID

   # Solution maintains type
   solution: LXSolution[Product]

**Benefits**:

- Full IDE autocomplete for goal metadata
- Type checking catches errors at development time
- Self-documenting code through type annotations

Extension Points
----------------

Custom Goal Types
~~~~~~~~~~~~~~~~~

Extend LXGoalMetadata for specialized goal types:

.. code-block:: python

   @dataclass
   class LXWeightedGoalMetadata(LXGoalMetadata):
       """Goal with dynamic weight calculation."""

       weight_func: Callable[[Any], float]

       def get_weight(self, instance: Any) -> float:
           """Calculate weight dynamically."""
           return self.weight * self.weight_func(instance)

Custom Relaxation Strategies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Implement alternative relaxation approaches:

.. code-block:: python

   def relax_with_bounds(
       constraint: LXConstraint[TModel],
       metadata: LXGoalMetadata,
       max_deviation: float
   ) -> RelaxedConstraint[TModel]:
       """Relax with bounded deviations."""

       relaxed = relax_constraint(constraint, metadata)

       # Add bounds to deviation variables
       relaxed.pos_deviation.upper_bound = max_deviation
       relaxed.neg_deviation.upper_bound = max_deviation

       return relaxed

Custom Objective Builders
~~~~~~~~~~~~~~~~~~~~~~~~~~

Create specialized objective construction:

.. code-block:: python

   def build_minimax_objective(
       relaxed_constraints: List[RelaxedConstraint]
   ) -> Tuple[LXLinearExpression, LXVariable]:
       """
       Minimax: Minimize maximum deviation.

       Creates auxiliary variable z and constraints:
           z >= deviation_i for all i
       Objective: minimize z
       """

       # Create max deviation variable
       z = LXVariable[None, float]("max_dev").continuous().bounds(lower=0)

       # Build constraints: z >= each deviation
       max_constraints = []
       for relaxed in relaxed_constraints:
           # Implementation details...

       # Objective: minimize z
       objective = LXLinearExpression().add_term(z, coeff=1.0)

       return objective, z

Performance Considerations
--------------------------

Memory Usage
~~~~~~~~~~~~

**Goal instances**: One Goal instance per constraint instance

.. code-block:: python

   # For 1000 products with demand goals:
   #   - 1000 Goal instances (small objects)
   #   - 1000 pos_dev variables
   #   - 1000 neg_dev variables
   # Memory: ~O(n) where n = constraint instances

**Optimization**:

- Goal instances are lightweight dataclasses
- Deviation variables created lazily during solving
- No duplication of original data

Computational Complexity
~~~~~~~~~~~~~~~~~~~~~~~~

**Weighted mode**: O(1) solves (single optimization)

**Sequential mode**: O(P) solves where P = number of priority levels

**Trade-off**:

- Weighted: Faster but approximate priority enforcement
- Sequential: Slower but strict lexicographic optimization

Testing Strategy
----------------

Unit Tests
~~~~~~~~~~

Test individual components:

.. code-block:: python

   def test_goal_metadata_undesired_deviations():
       """Test automatic deviation determination."""
       metadata_le = LXGoalMetadata(1, 1.0, LXConstraintSense.LE)
       assert metadata_le.is_pos_undesired()
       assert not metadata_le.is_neg_undesired()

       metadata_ge = LXGoalMetadata(1, 1.0, LXConstraintSense.GE)
       assert not metadata_ge.is_pos_undesired()
       assert metadata_ge.is_neg_undesired()

   def test_priority_to_weight():
       """Test weight scaling."""
       assert priority_to_weight(0) == 1.0
       assert priority_to_weight(1) == 1_000_000.0
       assert priority_to_weight(2) == 100_000.0

Integration Tests
~~~~~~~~~~~~~~~~~

Test end-to-end workflows:

.. code-block:: python

   def test_weighted_goal_programming():
       """Test complete weighted GP workflow."""
       model = build_test_model_with_goals()

       solution = optimizer.solve(model)

       assert solution.is_optimal()

       # Verify goal achievement
       assert solution.is_goal_satisfied("priority_1_goal")

       # Priority 1 should have lower deviations than priority 2
       dev_p1 = solution.get_total_deviation("priority_1_goal")
       dev_p2 = solution.get_total_deviation("priority_2_goal")

       assert dev_p1 <= dev_p2

Type Tests
~~~~~~~~~~

Use mypy for static type checking:

.. code-block:: bash

   mypy src/lumix/goal_programming

Common Patterns
---------------

Adding New Deviation Types
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Current: Binary undesired deviations ({'pos', 'neg'})
   # Extension: Weighted deviations

   @dataclass
   class LXWeightedGoalMetadata(LXGoalMetadata):
       pos_weight: float = 1.0
       neg_weight: float = 1.0

       def get_deviation_weights(self) -> Dict[str, float]:
           weights = {}
           if self.is_pos_undesired():
               weights['pos'] = self.pos_weight
           if self.is_neg_undesired():
               weights['neg'] = self.neg_weight
           return weights

Custom Solving Modes
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   class LXGoalMode(Enum):
       WEIGHTED = "weighted"
       SEQUENTIAL = "sequential"
       HYBRID = "hybrid"  # New: weighted within priorities, sequential across

Next Steps
----------

- :doc:`extending-goal-programming` - How to extend the module
- :doc:`design-decisions` - Rationale for architectural choices
- :doc:`/api/goal_programming/index` - Full API reference
- :doc:`/user-guide/goal_programming/index` - User guide
