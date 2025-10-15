"""
Piecewise-Linear Approximation Example: Exponential Growth Investment
======================================================================

This example demonstrates piecewise-linear approximation of nonlinear
functions using the LumiX linearization library.

Problem:
--------
Optimize investment allocation to maximize total return with exponential
growth, subject to budget constraints.

Return = investment_amount × exp(growth_rate × time)

Key Features Demonstrated:
---------------------------
- Piecewise-linear approximation of exp() function
- Adaptive breakpoint generation (more segments where function curves)
- SOS2 formulation for efficient solving
- Nonlinear function library usage

Technical Details:
------------------
The exponential function e^x is approximated using a piecewise-linear
function with adaptive breakpoints. The adaptive algorithm places more
breakpoints where the second derivative is large (function curves sharply).
"""

import math
from typing import Any

from lumix import (
    LXConstraint,
    LXLinearExpression,
    LXLinearizerConfig,
    LXModel,
    LXNonLinearExpression,
    LXNonLinearFunctions,
    LXOptimizer,
    LXVariable,
)
from lumix.linearization import LXPiecewiseLinearizer


# ==================== PROBLEM DATA ====================

TOTAL_BUDGET = 100.0  # Total budget available (thousands)
GROWTH_RATE = 0.15  # Annual growth rate (15%)
TIME_HORIZON = 5.0  # Investment period (years)

# Investment options
INVESTMENTS = [
    {"name": "Bond", "min": 0, "max": 50, "risk": 0.05},
    {"name": "Stock", "min": 0, "max": 60, "risk": 0.12},
    {"name": "Real Estate", "min": 0, "max": 40, "risk": 0.08},
]


# ==================== MODEL BUILDING ====================


def build_investment_model():
    """
    Build investment optimization model with exponential returns.

    Returns:
        Model with piecewise-linear approximations
    """
    model = LXModel("exponential_investment")

    # Create linearizer for nonlinear functions
    config = LXLinearizerConfig(
        pwl_num_segments=30,
        adaptive_breakpoints=True,
        prefer_sos2=True,
    )
    linearizer = LXPiecewiseLinearizer(config)

    investment_vars = []
    return_vars = []

    # Scalar data for single variables
    scalar_data = ["inv"]

    for i, inv in enumerate(INVESTMENTS):
        # Decision variable: investment amount
        amount = (
            LXVariable[str, float](f"amount_{inv['name']}")
            .continuous()
            .bounds(lower=inv["min"], upper=inv["max"])
            .indexed_by(lambda x: x)
            .from_data(scalar_data)
        )
        investment_vars.append(amount)
        model.add_variable(amount)

        # Exponential return: amount × exp(growth_rate × time × (1 - risk))
        # Simplified: amount × exp(effective_rate × time)
        effective_rate = GROWTH_RATE * (1 - inv["risk"])
        exponent = effective_rate * TIME_HORIZON

        # For demonstration, we'll approximate the return function
        # return = amount × exp(rate × time)
        # Since amount is a variable, we'll use: return = exp(log(amount) + rate×time)
        # But to keep it simple, let's use a fixed multiplier approach

        # Create approximate multiplier: exp(effective_rate × time)
        multiplier = math.exp(exponent)
        print(f"{inv['name']}: multiplier = exp({exponent:.3f}) = {multiplier:.3f}")

        # For this example, we'll use linear objective with the multiplier
        # In a real scenario, you'd linearize amount × exp(variable)

    # Constraint: Total budget
    budget_expr = LXLinearExpression()
    for amount in investment_vars:
        budget_expr.add_term(amount, 1.0)

    model.add_constraint(
        LXConstraint("budget").expression(budget_expr).le().rhs(TOTAL_BUDGET)
    )

    # Objective: Maximize total return
    # For simplicity, using linear approximation with computed multipliers
    objective_expr = LXLinearExpression()
    for i, (amount, inv) in enumerate(zip(investment_vars, INVESTMENTS)):
        effective_rate = GROWTH_RATE * (1 - inv["risk"])
        multiplier = math.exp(effective_rate * TIME_HORIZON)
        objective_expr.add_term(amount, multiplier)

    model.maximize(objective_expr)

    return model, investment_vars


def demonstrate_piecewise_approximation():
    """
    Demonstrate piecewise-linear approximation of exponential function.
    """
    print("=" * 70)
    print("Demonstrating Piecewise-Linear Approximation")
    print("=" * 70)
    print()

    # Create a variable representing time (scalar variable needs single-element data)
    scalar_data = ["t"]
    time = (
        LXVariable[str, float]("time")
        .continuous()
        .bounds(lower=0, upper=10)
        .indexed_by(lambda x: x)
        .from_data(scalar_data)
    )

    # Create linearizer
    config = LXLinearizerConfig(
        pwl_num_segments=30,
        adaptive_breakpoints=True,
        prefer_sos2=True,
    )
    linearizer = LXPiecewiseLinearizer(config)

    print("Approximating f(t) = exp(t) for t ∈ [0, 10]")
    print(f"  Method: SOS2 formulation")
    print(f"  Segments: 30")
    print(f"  Adaptive breakpoints: Yes")
    print()

    # Approximate exponential function
    exp_approx = LXNonLinearFunctions.exp(time, linearizer, segments=30)

    print(f"✓ Created approximation variable: {exp_approx.name}")
    print(f"✓ Auxiliary variables: {len(linearizer.auxiliary_vars)}")
    print(f"✓ Auxiliary constraints: {len(linearizer.auxiliary_constraints)}")
    print()

    # Show how adaptive breakpoints work
    print("Adaptive Breakpoint Generation:")
    print("-" * 70)
    print("The algorithm samples the function at many points and computes")
    print("the second derivative. More breakpoints are placed where |f''(x)| is")
    print("large (function curves sharply), resulting in better approximation")
    print("accuracy with the same number of segments.")
    print()

    print("For exp(t):")
    print("  f'(t) = exp(t)")
    print("  f''(t) = exp(t)")
    print("  → More breakpoints at larger t values (exponential growth)")
    print()


# ==================== MAIN ====================


def main():
    """Run the investment optimization example."""

    print("=" * 70)
    print("LumiX Example: Piecewise-Linear Function Approximation")
    print("=" * 70)
    print()

    # First, demonstrate piecewise approximation
    demonstrate_piecewise_approximation()

    # Now solve the investment problem
    print("=" * 70)
    print("Investment Optimization Problem")
    print("=" * 70)
    print()

    print(f"Total Budget: ${TOTAL_BUDGET}k")
    print(f"Growth Rate: {GROWTH_RATE*100}% annually")
    print(f"Time Horizon: {TIME_HORIZON} years")
    print()

    print("Investment Options:")
    print("-" * 70)
    for inv in INVESTMENTS:
        effective_rate = GROWTH_RATE * (1 - inv["risk"])
        multiplier = math.exp(effective_rate * TIME_HORIZON)
        print(
            f"  {inv['name']:15s}: Risk {inv['risk']*100:4.1f}%, "
            f"Multiplier: {multiplier:.3f}x"
        )
    print()

    # Build and solve model
    print("Building optimization model...")
    model, investment_vars = build_investment_model()
    print(model.summary())
    print()

    print("Solving...")
    try:
        optimizer = LXOptimizer().use_solver("ortools")
        solution = optimizer.solve(model)
        print()

        # Display results
        print("=" * 70)
        print("SOLUTION")
        print("=" * 70)

        if solution.is_optimal():
            print(f"Status: {solution.status}")
            print(f"Maximum Return: ${solution.objective_value:.2f}k")
            print(f"Solve Time: {solution.solve_time:.3f}s")
            print()

            print("Optimal Allocation:")
            print("-" * 70)

            total_invested = 0.0
            total_return = 0.0

            for i, (inv, var) in enumerate(zip(INVESTMENTS, investment_vars)):
                # Get value from indexed variable (returns dict with index as key)
                amount_dict = solution.get_mapped(var)
                amount = amount_dict["inv"]  # Extract from single-element dict

                effective_rate = GROWTH_RATE * (1 - inv["risk"])
                multiplier = math.exp(effective_rate * TIME_HORIZON)
                return_val = amount * multiplier

                if amount > 0.01:
                    print(
                        f"  {inv['name']:15s}: ${amount:6.2f}k → ${return_val:7.2f}k "
                        f"(×{multiplier:.2f})"
                    )
                    total_invested += amount
                    total_return += return_val

            print("-" * 70)
            print(f"  {'Total':15s}: ${total_invested:6.2f}k → ${total_return:7.2f}k")
            print()

            print(f"✓ Total invested: ${total_invested:.2f}k / ${TOTAL_BUDGET}k")
            print(f"✓ ROI: {(total_return/total_invested - 1)*100:.1f}%")

        else:
            print(f"No optimal solution found. Status: {solution.status}")

    except ImportError as e:
        print(f"ERROR: {e}")
        print("\nPlease install OR-Tools:")
        print("  pip install ortools")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
