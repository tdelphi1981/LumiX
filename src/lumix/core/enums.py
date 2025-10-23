"""Core enumerations for LumiX optimization library.

This module defines type-safe enumerations for optimization modeling:

- **Variable Types**: Continuous, integer, and binary variables
- **Constraint Senses**: Less-than-or-equal, greater-than-or-equal, and equality
- **Objective Directions**: Minimize and maximize

These enumerations provide IDE autocomplete and type checking throughout the library.

Examples:
    Creating variables with different types::

        from lumix import LXVariable, LXVarType

        # Continuous variable (default)
        production = LXVariable[Product, float]("production").continuous()

        # Integer variable
        trucks = LXVariable[Route, int]("trucks").integer()

        # Binary variable (0 or 1)
        is_open = LXVariable[Facility, int]("is_open").binary()

    Using constraint senses::

        from lumix import LXConstraint, LXConstraintSense

        # Less-than-or-equal constraint
        constraint1 = LXConstraint("capacity").le().rhs(100)

        # Greater-than-or-equal constraint
        constraint2 = LXConstraint("minimum").ge().rhs(50)

        # Equality constraint
        constraint3 = LXConstraint("balance").eq().rhs(0)

    Setting objective direction::

        from lumix import LXModel, LXObjectiveSense

        # Maximize profit
        model.maximize(profit_expr)

        # Minimize cost
        model.minimize(cost_expr)
"""

from enum import Enum


class LXVarType(Enum):
    """Variable type enumeration for optimization variables.

    Defines the domain of decision variables in the optimization model.
    Each type has different solver representations and computational characteristics.

    Attributes:
        CONTINUOUS: Real-valued variables (floating-point)
            Range: [-inf, inf] or bounded
            Use for: Production quantities, weights, percentages
            Example: production[product] = 123.45

        INTEGER: Integer-valued variables
            Range: Whole numbers only
            Use for: Counts, discrete quantities
            Example: num_trucks[route] = 5

        BINARY: Binary variables (0 or 1)
            Range: {0, 1}
            Use for: Yes/no decisions, selection, activation
            Example: is_facility_open[location] = 1

    Note:
        - CONTINUOUS variables generally solve faster than integer variables
        - BINARY is a special case of INTEGER with automatic bounds [0, 1]
        - Mixed-integer problems combine CONTINUOUS with INTEGER/BINARY variables

    Examples:
        Variable type affects solver choice and performance::

            # Fast: Linear program with continuous variables
            production = LXVariable[Product, float]("prod").continuous()

            # Slower: Mixed-integer program
            trucks = LXVariable[Route, int]("trucks").integer()

            # Classic: Binary decision variables
            select = LXVariable[Item, int]("select").binary()
    """

    CONTINUOUS = "continuous"
    INTEGER = "integer"
    BINARY = "binary"


class LXConstraintSense(Enum):
    """Constraint sense enumeration for inequality and equality constraints.

    Defines the relationship between left-hand side (LHS) and right-hand side (RHS)
    of constraints in the optimization model.

    Attributes:
        LE: Less-than-or-equal constraint (<=)
            Meaning: LHS <= RHS
            Use for: Capacity limits, maximum bounds, upper limits
            Example: total_production <= factory_capacity

        GE: Greater-than-or-equal constraint (>=)
            Meaning: LHS >= RHS
            Use for: Minimum requirements, lower bounds, demand satisfaction
            Example: production >= minimum_quota

        EQ: Equality constraint (==)
            Meaning: LHS == RHS
            Use for: Balance equations, exact requirements, flow conservation
            Example: inflow - outflow == 0

    Note:
        - LE and GE constraints define feasible regions (inequalities)
        - EQ constraints are more restrictive and may reduce feasibility
        - All constraints must be satisfied for a solution to be feasible

    Examples:
        Different constraint types::

            # Capacity constraint (upper limit)
            LXConstraint("capacity")
                .expression(resource_usage_expr)
                .le()
                .rhs(max_capacity)

            # Demand constraint (lower limit)
            LXConstraint("demand")
                .expression(production_expr)
                .ge()
                .rhs(min_demand)

            # Balance constraint (exact equality)
            LXConstraint("flow_balance")
                .expression(inflow - outflow)
                .eq()
                .rhs(0)
    """

    LE = "<="
    GE = ">="
    EQ = "=="


class LXObjectiveSense(Enum):
    """Objective sense enumeration for optimization direction.

    Defines whether the objective function should be minimized or maximized.

    Attributes:
        MINIMIZE: Minimize the objective function
            Use for: Costs, distances, time, waste, deviations, risk
            Example: Minimize total transportation cost

        MAXIMIZE: Maximize the objective function
            Use for: Profit, revenue, efficiency, throughput, utility
            Example: Maximize total profit

    Note:
        - Every optimization model must have exactly one objective
        - Minimizing f(x) is equivalent to maximizing -f(x)
        - For multi-objective problems, use goal programming module

    Examples:
        Setting objective direction::

            # Maximize profit
            model = LXModel("production_plan")
            model.maximize(
                LXLinearExpression()
                .add_term(production, lambda p: p.profit)
            )

            # Minimize cost
            model = LXModel("logistics")
            model.minimize(
                LXLinearExpression()
                .add_term(shipment, lambda s: s.cost)
            )

            # Multi-objective (using goal programming)
            model.set_goal_mode("weighted")
            # Objectives defined via goal constraints
    """

    MINIMIZE = "min"
    MAXIMIZE = "max"


__all__ = ["LXVarType", "LXConstraintSense", "LXObjectiveSense"]
