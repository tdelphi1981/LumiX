Extending Goal Programming
===========================

Guide for extending LumiX's goal programming functionality.

Adding Custom Goal Types
-------------------------

Extended Goal Metadata
~~~~~~~~~~~~~~~~~~~~~~~

Create custom metadata with additional attributes:

.. code-block:: python

   from dataclasses import dataclass
   from lumix.goal_programming import LXGoalMetadata
   from lumix.core.enums import LXConstraintSense

   @dataclass
   class LXAsymmetricGoalMetadata(LXGoalMetadata):
       """Goal with asymmetric deviation penalties."""

       pos_penalty: float = 1.0
       neg_penalty: float = 1.0

       def get_deviation_penalty(self, deviation_type: str) -> float:
           """Get penalty for deviation type."""
           if deviation_type == "pos":
               return self.pos_penalty
           elif deviation_type == "neg":
               return self.neg_penalty
           else:
               raise ValueError(f"Unknown deviation type: {deviation_type}")

**Usage**:

.. code-block:: python

   # Under-stock is 3× worse than over-stock
   metadata = LXAsymmetricGoalMetadata(
       priority=1,
       weight=1.0,
       constraint_sense=LXConstraintSense.EQ,
       pos_penalty=1.0,  # Over-stock penalty
       neg_penalty=3.0   # Under-stock penalty (worse)
   )

Conditional Goals
~~~~~~~~~~~~~~~~~

Goals that activate based on conditions:

.. code-block:: python

   @dataclass
   class LXConditionalGoalMetadata(LXGoalMetadata):
       """Goal that activates conditionally."""

       activation_func: Callable[[Any], bool]

       def is_active(self, instance: Any) -> bool:
           """Check if goal is active for this instance."""
           return self.activation_func(instance)

**Usage**:

.. code-block:: python

   # Only apply goal to high-value customers
   metadata = LXConditionalGoalMetadata(
       priority=1,
       weight=1.0,
       constraint_sense=LXConstraintSense.GE,
       activation_func=lambda customer: customer.lifetime_value > 10000
   )

Custom Relaxation Strategies
-----------------------------

Bounded Deviations
~~~~~~~~~~~~~~~~~~

Limit maximum allowed deviation:

.. code-block:: python

   from lumix.goal_programming import relax_constraint, RelaxedConstraint
   from typing import Optional

   def relax_with_bounds(
       constraint: LXConstraint[TModel],
       metadata: LXGoalMetadata,
       max_pos_deviation: Optional[float] = None,
       max_neg_deviation: Optional[float] = None
   ) -> RelaxedConstraint[TModel]:
       """
       Relax constraint with bounded deviations.

       Args:
           constraint: Constraint to relax
           metadata: Goal metadata
           max_pos_deviation: Upper bound for positive deviation
           max_neg_deviation: Upper bound for negative deviation

       Returns:
           RelaxedConstraint with bounded deviation variables
       """
       # Standard relaxation
       relaxed = relax_constraint(constraint, metadata)

       # Add bounds
       if max_pos_deviation is not None:
           relaxed.pos_deviation.upper_bound = max_pos_deviation

       if max_neg_deviation is not None:
           relaxed.neg_deviation.upper_bound = max_neg_deviation

       return relaxed

**Usage**:

.. code-block:: python

   # Overtime can exceed target by at most 10 hours
   overtime_goal = (
       LXConstraint("overtime")
       .expression(hours_expr)
       .le()
       .rhs(40)
   )

   metadata = LXGoalMetadata(
       priority=2,
       weight=1.0,
       constraint_sense=LXConstraintSense.LE
   )

   relaxed = relax_with_bounds(
       overtime_goal,
       metadata,
       max_pos_deviation=10.0  # Can't exceed by more than 10
   )

Soft Hard Constraints
~~~~~~~~~~~~~~~~~~~~~

Goals that become hard constraints at threshold:

.. code-block:: python

   def relax_with_hard_limit(
       constraint: LXConstraint[TModel],
       metadata: LXGoalMetadata,
       hard_limit: float,
       hard_sense: LXConstraintSense
   ) -> Tuple[RelaxedConstraint[TModel], LXConstraint[TModel]]:
       """
       Relax constraint but add hard limit.

       Args:
           constraint: Constraint to relax
           metadata: Goal metadata
           hard_limit: Hard limit value
           hard_sense: Sense for hard limit (LE or GE)

       Returns:
           Tuple of (relaxed_constraint, hard_constraint)
       """
       # Relax constraint
       relaxed = relax_constraint(constraint, metadata)

       # Create hard limit constraint
       hard_constraint = (
           LXConstraint[TModel](f"{constraint.name}_hard_limit")
           .expression(constraint.lhs)
           .sense(hard_sense)
           .rhs(hard_limit)
       )

       if constraint._data:
           hard_constraint._data = constraint._data
       if constraint.index_func:
           hard_constraint.index_func = constraint.index_func

       return relaxed, hard_constraint

**Usage**:

.. code-block:: python

   # Target 1000 units (soft), but at least 800 (hard)
   demand_goal = (
       LXConstraint[Product]("demand")
       .expression(production_expr)
       .ge()
       .rhs(lambda p: p.demand_target)
       .from_data(products)
   )

   metadata = LXGoalMetadata(
       priority=1,
       weight=1.0,
       constraint_sense=LXConstraintSense.GE
   )

   relaxed, hard = relax_with_hard_limit(
       demand_goal,
       metadata,
       hard_limit=lambda p: p.demand_target * 0.8,
       hard_sense=LXConstraintSense.GE
   )

   model.add_constraint(relaxed.constraint)
   model.add_constraint(hard)  # Hard minimum

Custom Objective Builders
--------------------------

Minimax Objective
~~~~~~~~~~~~~~~~~

Minimize maximum deviation:

.. code-block:: python

   from lumix.goal_programming import RelaxedConstraint
   from lumix.core.variables import LXVariable
   from lumix.core.expressions import LXLinearExpression

   def build_minimax_objective(
       relaxed_constraints: List[RelaxedConstraint],
       priority: Optional[int] = None
   ) -> Tuple[LXLinearExpression, LXVariable, List[LXConstraint]]:
       """
       Build minimax objective: minimize max deviation.

       Args:
           relaxed_constraints: Relaxed constraints
           priority: Only include goals at this priority (None = all)

       Returns:
           Tuple of (objective, max_var, auxiliary_constraints)
       """
       # Filter by priority if specified
       if priority is not None:
           relaxed_constraints = [
               r for r in relaxed_constraints
               if r.goal_metadata.priority == priority
           ]

       # Create max deviation variable
       max_dev = (
           LXVariable[None, float]("max_deviation")
           .continuous()
           .bounds(lower=0)
       )

       # Auxiliary constraints: max_dev >= each deviation
       aux_constraints = []

       for i, relaxed in enumerate(relaxed_constraints):
           # For each undesired deviation
           for dev_var in relaxed.get_undesired_variables():
               # max_dev >= dev_var
               constraint = (
                   LXConstraint(f"max_dev_constraint_{i}")
                   .expression(
                       LXLinearExpression()
                       .add_term(max_dev, coeff=1.0)
                       .add_term(dev_var, coeff=-1.0)
                   )
                   .ge()
                   .rhs(0)
               )
               aux_constraints.append(constraint)

       # Objective: minimize max_dev
       objective = LXLinearExpression().add_term(max_dev, coeff=1.0)

       return objective, max_dev, aux_constraints

**Usage**:

.. code-block:: python

   # Minimize worst-case deviation
   objective, max_var, aux_constraints = build_minimax_objective(relaxed_list)

   model.add_variable(max_var)
   for constraint in aux_constraints:
       model.add_constraint(constraint)
   model.minimize(objective)

Weighted Sum of Squared Deviations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lumix.core.expressions import LXQuadraticExpression, LXQuadraticTerm

   def build_quadratic_objective(
       relaxed_constraints: List[RelaxedConstraint]
   ) -> LXQuadraticExpression:
       """
       Build quadratic objective: minimize sum of squared deviations.

       Note: Requires solver with quadratic objective support.
       """
       objective = LXQuadraticExpression()

       for relaxed in relaxed_constraints:
           priority_weight = priority_to_weight(relaxed.goal_metadata.priority)
           goal_weight = relaxed.goal_metadata.weight
           combined_weight = priority_weight * goal_weight

           # Add squared deviation terms
           for dev_var in relaxed.get_undesired_variables():
               # Add dev_var^2 with weight
               quad_term = LXQuadraticTerm(dev_var, dev_var, combined_weight)
               objective.add_quadratic_term(quad_term)

       return objective

Custom Solving Modes
---------------------

Hybrid Mode
~~~~~~~~~~~

Weighted within priorities, sequential across priorities:

.. code-block:: python

   class LXHybridGoalProgrammingSolver:
       """Hybrid: weighted within priority, sequential across."""

       def __init__(self, optimizer: LXOptimizer):
           self.optimizer = optimizer

       def solve_hybrid(
           self,
           model: LXModel[TModel],
           relaxed_constraints: List[RelaxedConstraint[TModel]]
       ) -> LXSolution[TModel]:
           """
           Solve using hybrid approach.

           1. Group goals by priority
           2. For each priority, build weighted objective for that priority
           3. Solve sequentially, fixing higher priority deviations
           """
           # Group by priority
           from collections import defaultdict
           priority_groups = defaultdict(list)

           for relaxed in relaxed_constraints:
               priority = relaxed.goal_metadata.priority
               priority_groups[priority].append(relaxed)

           # Solve each priority
           final_solution = None

           for priority in sorted(priority_groups.keys()):
               if priority == 0:
                   continue  # Skip custom objectives

               # Build weighted objective for this priority only
               priority_relaxed = priority_groups[priority]
               objective = build_weighted_objective(
                   priority_relaxed,
                   base=1.0,  # No exponential scaling within priority
                   exponent_offset=0
               )

               # Set objective
               model.objective_expr = objective
               model.objective_sense = LXObjectiveSense.MINIMIZE

               # Solve
               solution = self.optimizer.solve(model)

               if not solution.is_optimal():
                   return solution

               # Fix deviations for next priority
               # (implementation similar to sequential solver)

               final_solution = solution

           return final_solution

Epsilon-Constraint Method
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def solve_epsilon_constraint(
       model: LXModel[TModel],
       optimizer: LXOptimizer,
       primary_goal: str,
       secondary_goals: List[Tuple[str, float]]  # (goal_name, epsilon)
   ) -> LXSolution[TModel]:
       """
       Epsilon-constraint method for multi-objective optimization.

       Args:
           model: Model with goals
           optimizer: Optimizer
           primary_goal: Goal to optimize
           secondary_goals: List of (goal_name, max_deviation) constraints

       Returns:
           Solution optimizing primary goal subject to epsilon constraints
       """
       # Add epsilon constraints for secondary goals
       for goal_name, epsilon in secondary_goals:
           # Find relaxed constraint for this goal
           relaxed = next(
               r for r in model._relaxed_constraints
               if r.constraint.name == goal_name
           )

           # Add constraint: total_deviation <= epsilon
           epsilon_constraint = (
               LXConstraint(f"{goal_name}_epsilon")
               .expression(
                   LXLinearExpression()
                   .add_term(relaxed.pos_deviation, coeff=1.0)
                   .add_term(relaxed.neg_deviation, coeff=1.0)
               )
               .le()
               .rhs(epsilon)
           )

           model.add_constraint(epsilon_constraint)

       # Build objective for primary goal only
       primary_relaxed = next(
           r for r in model._relaxed_constraints
           if r.constraint.name == primary_goal
       )

       objective = LXLinearExpression()
       for dev_var in primary_relaxed.get_undesired_variables():
           objective.add_term(dev_var, coeff=1.0)

       model.minimize(objective)

       return optimizer.solve(model)

Testing Extensions
------------------

Unit Tests
~~~~~~~~~~

.. code-block:: python

   import pytest
   from lumix.goal_programming import LXGoalMetadata, relax_constraint
   from lumix.core.enums import LXConstraintSense

   def test_asymmetric_goal_metadata():
       """Test asymmetric deviation penalties."""
       metadata = LXAsymmetricGoalMetadata(
           priority=1,
           weight=1.0,
           constraint_sense=LXConstraintSense.EQ,
           pos_penalty=1.0,
           neg_penalty=3.0
       )

       assert metadata.get_deviation_penalty("pos") == 1.0
       assert metadata.get_deviation_penalty("neg") == 3.0

   def test_bounded_relaxation():
       """Test relaxation with bounds."""
       constraint = build_test_constraint()
       metadata = LXGoalMetadata(1, 1.0, LXConstraintSense.LE)

       relaxed = relax_with_bounds(
           constraint,
           metadata,
           max_pos_deviation=10.0
       )

       assert relaxed.pos_deviation.upper_bound == 10.0

Integration Tests
~~~~~~~~~~~~~~~~~

.. code-block:: python

   def test_minimax_objective():
       """Test minimax objective builder."""
       model = build_test_model()
       relaxed_list = get_relaxed_constraints(model)

       objective, max_var, aux_constraints = build_minimax_objective(relaxed_list)

       # Add to model
       model.add_variable(max_var)
       for constraint in aux_constraints:
           model.add_constraint(constraint)
       model.minimize(objective)

       solution = optimizer.solve(model)

       assert solution.is_optimal()

       # Verify max_var captures maximum deviation
       max_deviation = solution.get_variable(max_var)
       for relaxed in relaxed_list:
           deviations = solution.get_goal_deviations(relaxed.constraint.name)
           # All deviations should be <= max_deviation
           assert all(v <= max_deviation + 1e-6 for v in deviations['pos'].values())
           assert all(v <= max_deviation + 1e-6 for v in deviations['neg'].values())

Documentation
-------------

Docstring Template
~~~~~~~~~~~~~~~~~~

Use Google-style docstrings:

.. code-block:: python

   def custom_relaxation_function(
       constraint: LXConstraint[TModel],
       metadata: LXGoalMetadata,
       custom_param: float
   ) -> RelaxedConstraint[TModel]:
       """
       One-line summary of custom relaxation.

       Longer description explaining the relaxation strategy,
       when to use it, and any special considerations.

       Args:
           constraint: Constraint to relax
           metadata: Goal metadata with priority and weight
           custom_param: Description of custom parameter

       Returns:
           RelaxedConstraint with custom relaxation applied

       Raises:
           ValueError: If custom_param is invalid

       Examples:
           Basic usage::

               constraint = LXConstraint("demand").expression(...).ge().rhs(100)
               metadata = LXGoalMetadata(priority=1, weight=1.0, ...)
               relaxed = custom_relaxation_function(constraint, metadata, 0.5)

       Note:
           Any important notes or warnings about the function.

       See Also:
           - :func:`~lumix.goal_programming.relaxation.relax_constraint`
           - Related documentation
       """

Adding to Documentation
~~~~~~~~~~~~~~~~~~~~~~~~

1. **API Reference**: Add autodoc to ``docs/source/api/goal_programming/index.rst``

2. **User Guide**: Add usage examples to appropriate guide

3. **Development Guide**: Document architecture and design decisions

Contributing Guidelines
------------------------

Code Style
~~~~~~~~~~

Follow existing patterns:

- Use Google-style docstrings
- Type all function signatures
- Use fluent API patterns where appropriate
- Follow naming conventions (``LX`` prefix for public classes)

Example:

.. code-block:: python

   from typing_extensions import Self
   from dataclasses import dataclass

   @dataclass
   class LXCustomGoal:
       """Custom goal type."""

       name: str
       priority: int

       def with_priority(self, priority: int) -> Self:
           """Set priority (fluent API)."""
           self.priority = priority
           return self

Testing Requirements
~~~~~~~~~~~~~~~~~~~~

All extensions must have:

- Unit tests (>90% coverage)
- Integration tests with actual optimization
- Type annotations and mypy compliance
- Comprehensive docstrings

Pull Request Process
~~~~~~~~~~~~~~~~~~~~~

1. Fork the repository
2. Create feature branch: ``git checkout -b feature/custom-goal-type``
3. Add tests and documentation
4. Run full test suite: ``pytest tests/``
5. Run type checker: ``mypy src/lumix/goal_programming``
6. Submit PR with description of changes and motivation

Best Practices
--------------

1. **Maintain Type Safety**

   .. code-block:: python

      # Good: Full type annotations
      def custom_function(
          constraint: LXConstraint[TModel],
          metadata: LXGoalMetadata
      ) -> RelaxedConstraint[TModel]:
          ...

      # Bad: Missing types
      def custom_function(constraint, metadata):
          ...

2. **Follow Existing Patterns**

   .. code-block:: python

      # Study existing code in lumix.goal_programming
      # Match architectural patterns
      # Reuse utilities like priority_to_weight, get_deviation_var_name

3. **Document Thoroughly**

   - Explain *why*, not just *what*
   - Provide usage examples
   - Document edge cases and limitations

4. **Test Edge Cases**

   .. code-block:: python

      def test_edge_cases():
          # Empty constraint list
          # Single priority
          # All same priority
          # Priority 0 only
          # Mixed indexed and non-indexed
          ...

Next Steps
----------

- :doc:`goal-programming-architecture` - Understand the architecture
- :doc:`design-decisions` - Rationale for design choices
- :doc:`/api/goal_programming/index` - Full API reference
- :doc:`/user-guide/goal_programming/index` - User guide
