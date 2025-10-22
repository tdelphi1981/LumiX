"""
Tests for Goal Programming functionality.

Tests:
- Goal constraint creation with .as_goal()
- Constraint relaxation (LE, GE, EQ)
- Deviation variable creation
- Objective building (weighted mode)
- Goal satisfaction checking
- Integration with LXModel
"""

import pytest
from dataclasses import dataclass

from lumix import (
    LXConstraint,
    LXLinearExpression,
    LXModel,
    LXVariable,
)
from lumix.goal_programming import (
    LXGoalMetadata,
    LXGoalMode,
    get_deviation_var_name,
    priority_to_weight,
    relax_constraint,
    build_weighted_objective,
)
from lumix.core.enums import LXConstraintSense


# Test Data Models
@dataclass
class TestProduct:
    """Simple product for testing."""

    id: int
    name: str
    target: float


# Test Data
TEST_PRODUCTS = [
    TestProduct(id=1, name="A", target=100),
    TestProduct(id=2, name="B", target=50),
]


class TestGoalMetadata:
    """Test LXGoalMetadata creation and logic."""

    def test_metadata_creation(self):
        """Test basic metadata creation."""
        metadata = LXGoalMetadata(
            priority=1,
            weight=1.0,
            constraint_sense=LXConstraintSense.GE
        )

        assert metadata.priority == 1
        assert metadata.weight == 1.0
        assert metadata.constraint_sense == LXConstraintSense.GE

    def test_le_undesired_deviations(self):
        """Test LE constraint has positive deviation undesired."""
        metadata = LXGoalMetadata(
            priority=1,
            weight=1.0,
            constraint_sense=LXConstraintSense.LE
        )

        assert metadata.is_pos_undesired()
        assert not metadata.is_neg_undesired()
        assert "pos" in metadata.undesired_deviations
        assert "neg" not in metadata.undesired_deviations

    def test_ge_undesired_deviations(self):
        """Test GE constraint has negative deviation undesired."""
        metadata = LXGoalMetadata(
            priority=1,
            weight=1.0,
            constraint_sense=LXConstraintSense.GE
        )

        assert not metadata.is_pos_undesired()
        assert metadata.is_neg_undesired()
        assert "neg" in metadata.undesired_deviations
        assert "pos" not in metadata.undesired_deviations

    def test_eq_undesired_deviations(self):
        """Test EQ constraint has both deviations undesired."""
        metadata = LXGoalMetadata(
            priority=1,
            weight=1.0,
            constraint_sense=LXConstraintSense.EQ
        )

        assert metadata.is_pos_undesired()
        assert metadata.is_neg_undesired()
        assert "pos" in metadata.undesired_deviations
        assert "neg" in metadata.undesired_deviations

    def test_custom_objective(self):
        """Test priority 0 is recognized as custom objective."""
        metadata = LXGoalMetadata(
            priority=0,
            weight=1.0,
            constraint_sense=LXConstraintSense.GE
        )

        assert metadata.is_custom_objective()


class TestPriorityToWeight:
    """Test priority-to-weight conversion."""

    def test_priority_1(self):
        """Test priority 1 gets highest weight."""
        weight = priority_to_weight(1)
        assert weight == 1e6

    def test_priority_2(self):
        """Test priority 2 gets lower weight."""
        weight = priority_to_weight(2)
        assert weight == 1e5

    def test_priority_3(self):
        """Test priority 3 gets even lower weight."""
        weight = priority_to_weight(3)
        assert weight == 1e4

    def test_priority_0(self):
        """Test priority 0 (custom objective) gets weight 1."""
        weight = priority_to_weight(0)
        assert weight == 1.0

    def test_decreasing_weights(self):
        """Test weights decrease with priority."""
        w1 = priority_to_weight(1)
        w2 = priority_to_weight(2)
        w3 = priority_to_weight(3)

        assert w1 > w2 > w3


class TestDeviationVariableNaming:
    """Test deviation variable naming."""

    def test_positive_deviation_name(self):
        """Test positive deviation variable naming."""
        name = get_deviation_var_name("production_goal", "pos")
        assert name == "production_goal_pos_dev"

    def test_negative_deviation_name(self):
        """Test negative deviation variable naming."""
        name = get_deviation_var_name("production_goal", "neg")
        assert name == "production_goal_neg_dev"


class TestConstraintRelaxation:
    """Test constraint relaxation logic."""

    def test_relax_single_constraint_ge(self):
        """Test relaxing a single GE constraint."""
        # Create a simple variable
        var = LXVariable[None, float]("x").continuous().bounds(lower=0)

        # Create a GE constraint
        expr = LXLinearExpression().add_term(var, coeff=1.0)
        constraint = LXConstraint("goal_x").expression(expr).ge().rhs(10.0)

        # Create metadata
        metadata = LXGoalMetadata(
            priority=1,
            weight=1.0,
            constraint_sense=LXConstraintSense.GE
        )

        # Relax the constraint
        relaxed = relax_constraint(constraint, metadata)

        # Check relaxed constraint
        assert relaxed.constraint.name == "goal_x"
        assert relaxed.constraint.sense == LXConstraintSense.EQ
        assert relaxed.constraint.rhs_value == 10.0

        # Check deviation variables
        assert relaxed.pos_deviation.name == "goal_x_pos_dev"
        assert relaxed.neg_deviation.name == "goal_x_neg_dev"

        # Check undesired variables (GE means negative is undesired)
        undesired = relaxed.get_undesired_variables()
        assert len(undesired) == 1
        assert undesired[0].name == "goal_x_neg_dev"

    def test_relax_single_constraint_le(self):
        """Test relaxing a single LE constraint."""
        var = LXVariable[None, float]("x").continuous().bounds(lower=0)
        expr = LXLinearExpression().add_term(var, coeff=1.0)
        constraint = LXConstraint("goal_x").expression(expr).le().rhs(20.0)

        metadata = LXGoalMetadata(
            priority=1,
            weight=1.0,
            constraint_sense=LXConstraintSense.LE
        )

        relaxed = relax_constraint(constraint, metadata)

        # LE means positive is undesired
        undesired = relaxed.get_undesired_variables()
        assert len(undesired) == 1
        assert undesired[0].name == "goal_x_pos_dev"

    def test_relax_single_constraint_eq(self):
        """Test relaxing a single EQ constraint."""
        var = LXVariable[None, float]("x").continuous().bounds(lower=0)
        expr = LXLinearExpression().add_term(var, coeff=1.0)
        constraint = LXConstraint("goal_x").expression(expr).eq().rhs(15.0)

        metadata = LXGoalMetadata(
            priority=1,
            weight=1.0,
            constraint_sense=LXConstraintSense.EQ
        )

        relaxed = relax_constraint(constraint, metadata)

        # EQ means both are undesired
        undesired = relaxed.get_undesired_variables()
        assert len(undesired) == 2
        undesired_names = {v.name for v in undesired}
        assert "goal_x_pos_dev" in undesired_names
        assert "goal_x_neg_dev" in undesired_names

    def test_relax_indexed_constraint(self):
        """Test relaxing an indexed constraint family."""
        var = (
            LXVariable[TestProduct, float]("production")
            .continuous()
            .bounds(lower=0)
            .indexed_by(lambda p: p.id)
            .from_data(TEST_PRODUCTS)
        )

        expr = LXLinearExpression[TestProduct]().add_term(var, coeff=1.0)

        constraint = (
            LXConstraint[TestProduct]("production_goal")
            .expression(expr)
            .ge()
            .rhs(lambda p: p.target)
            .indexed_by(lambda p: p.id)
            .from_data(TEST_PRODUCTS)
        )

        metadata = LXGoalMetadata(
            priority=1,
            weight=1.0,
            constraint_sense=LXConstraintSense.GE
        )

        relaxed = relax_constraint(constraint, metadata)

        # Check indexed deviation variables
        assert relaxed.pos_deviation.index_func is not None
        assert relaxed.neg_deviation.index_func is not None


class TestObjectiveBuilding:
    """Test objective function building."""

    def test_build_weighted_objective_single_goal(self):
        """Test building weighted objective with single goal."""
        var = LXVariable[None, float]("x").continuous().bounds(lower=0)
        expr = LXLinearExpression().add_term(var, coeff=1.0)
        constraint = LXConstraint("goal").expression(expr).ge().rhs(10.0)

        metadata = LXGoalMetadata(
            priority=1,
            weight=1.0,
            constraint_sense=LXConstraintSense.GE
        )

        relaxed = relax_constraint(constraint, metadata)
        objective = build_weighted_objective([relaxed])

        # Check that objective has terms (deviation variables)
        assert len(objective.terms) > 0

    def test_build_weighted_objective_multiple_priorities(self):
        """Test building weighted objective with multiple priorities."""
        var = LXVariable[None, float]("x").continuous().bounds(lower=0)

        # Priority 1 goal
        expr1 = LXLinearExpression().add_term(var, coeff=1.0)
        constraint1 = LXConstraint("goal1").expression(expr1).ge().rhs(10.0)
        metadata1 = LXGoalMetadata(priority=1, weight=1.0, constraint_sense=LXConstraintSense.GE)
        relaxed1 = relax_constraint(constraint1, metadata1)

        # Priority 2 goal
        expr2 = LXLinearExpression().add_term(var, coeff=1.0)
        constraint2 = LXConstraint("goal2").expression(expr2).le().rhs(20.0)
        metadata2 = LXGoalMetadata(priority=2, weight=1.0, constraint_sense=LXConstraintSense.LE)
        relaxed2 = relax_constraint(constraint2, metadata2)

        objective = build_weighted_objective([relaxed1, relaxed2])

        # Check that objective has terms from both goals
        assert len(objective.terms) >= 2


class TestConstraintGoalMethod:
    """Test .as_goal() method on LXConstraint."""

    def test_as_goal_creates_metadata(self):
        """Test that .as_goal() creates goal metadata."""
        constraint = LXConstraint("test").expression(LXLinearExpression()).ge().rhs(10)

        constraint.as_goal(priority=1, weight=1.0)

        assert constraint.goal_metadata is not None
        assert constraint.goal_metadata.priority == 1
        assert constraint.goal_metadata.weight == 1.0

    def test_is_goal_returns_true(self):
        """Test that .is_goal() returns True after marking as goal."""
        constraint = LXConstraint("test").expression(LXLinearExpression()).ge().rhs(10)

        constraint.as_goal(priority=1, weight=1.0)

        assert constraint.is_goal()

    def test_is_goal_returns_false(self):
        """Test that .is_goal() returns False for regular constraints."""
        constraint = LXConstraint("test").expression(LXLinearExpression()).ge().rhs(10)

        assert not constraint.is_goal()


class TestModelIntegration:
    """Test integration with LXModel."""

    def test_model_has_goals(self):
        """Test that model can detect goals."""
        model = LXModel("test")

        var = LXVariable[None, float]("x").continuous()
        model.add_variable(var)

        # Add regular constraint
        constraint1 = LXConstraint("regular").expression(LXLinearExpression()).ge().rhs(10)
        model.add_constraint(constraint1)

        # Add goal constraint
        constraint2 = LXConstraint("goal").expression(LXLinearExpression()).ge().rhs(20)
        constraint2.as_goal(priority=1, weight=1.0)
        model.add_constraint(constraint2)

        assert model.has_goals()

    def test_model_set_goal_mode(self):
        """Test setting goal mode on model."""
        model = LXModel("test")

        model.set_goal_mode("weighted")
        assert model.goal_mode == "weighted"

        model.set_goal_mode("sequential")
        assert model.goal_mode == "sequential"

    def test_model_set_invalid_goal_mode(self):
        """Test that invalid goal mode raises error."""
        model = LXModel("test")

        with pytest.raises(ValueError):
            model.set_goal_mode("invalid")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
