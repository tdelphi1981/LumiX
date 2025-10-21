"""
Driver Scheduling Example: Multi-Model Indexing ⭐⭐⭐
====================================================

THIS IS THE MOST IMPORTANT LUMIX EXAMPLE!

Demonstrates multi-model indexing - variables indexed by (Driver, Date) tuples.
This is LumiX's killer feature that sets it apart from other optimization libraries.

Problem: Schedule drivers over a week, minimizing cost while meeting coverage requirements.

Key Features:
- Variable indexed by (Driver × Date) cartesian product
- IndexDimension with filters
- cost_multi() - cost function receives both models
- where_multi() - filter combinations based on both models
- Constraints that sum over specific dimensions
"""

from typing import Tuple

from lumix import (
    LXConstraint,
    LXIndexDimension,
    LXLinearExpression,
    LXModel,
    LXOptimizer,
    LXVariable,
)

from sample_data import DATES, DRIVERS, Date, Driver, calculate_cost, is_driver_available


solver_to_use = "ortools"

# ==================== MODEL BUILDING ====================


def build_scheduling_model() -> LXModel:
    """
    Build the driver scheduling model.

    This demonstrates THE KEY FEATURE of LumiX:
    Variables indexed by multiple models (Driver × Date).
    """

    # ========================================
    # MULTI-MODEL INDEXED VARIABLE
    # ========================================
    # This creates a binary variable for EACH (driver, date) combination!
    # duty[driver, date] = 1 if driver works on date, 0 otherwise

    duty = (
        LXVariable[Tuple[Driver, Date], int]("duty")
        .binary()  # Binary decision: work or not
        .indexed_by_product(
            # First dimension: Driver
            LXIndexDimension(Driver, lambda d: d.id)
            .where(lambda d: d.is_active)  # Only active drivers
            .from_data(DRIVERS),
            # Second dimension: Date
            LXIndexDimension(Date, lambda dt: dt.date).from_data(DATES),
        )
        # Cost function receives BOTH driver and date!
        .cost_multi(lambda driver, date: calculate_cost(driver, date))
        # Filter out invalid combinations
        .where_multi(lambda driver, date: is_driver_available(driver, date))
    )

    # Create model
    model = LXModel("driver_scheduling").add_variable(duty)

    # ========================================
    # OBJECTIVE: Minimize Total Cost
    # ========================================
    # Cost expression using multi-indexed variable
    # The cost function was already defined in cost_multi() above
    cost_expr = LXLinearExpression().add_multi_term(
        duty, coeff=lambda driver, date: calculate_cost(driver, date)
    )

    model.minimize(cost_expr)

    # ========================================
    # CONSTRAINT 1: Driver Max Days
    # ========================================
    # Each driver works <= max_days_per_week
    # This sums over ALL dates for EACH driver

    for driver in DRIVERS:
        if not driver.is_active:
            continue

        # Sum duty[driver, date] over all dates for this specific driver
        driver_days_expr = LXLinearExpression().add_multi_term(
            duty,
            coeff=lambda d, dt: 1.0,
            where=lambda d, dt, drv=driver: d.id == drv.id,  # Filter for this driver (capture by value)
        )

        model.add_constraint(
            LXConstraint(f"max_days_{driver.name}")
            .expression(driver_days_expr)
            .le()
            .rhs(float(driver.max_days_per_week))
        )

    # ========================================
    # CONSTRAINT 2: Daily Coverage
    # ========================================
    # Each date needs >= min_drivers_required
    # This sums over ALL drivers for EACH date

    for date in DATES:
        # Sum duty[driver, date] over all drivers for this specific date
        coverage_expr = LXLinearExpression().add_multi_term(
            duty,
            coeff=lambda d, dt: 1.0,
            where=lambda d, dt, current_date=date: dt.date == current_date.date,  # Filter for this date (capture by value)
        )

        model.add_constraint(
            LXConstraint(f"coverage_{date.date}")
            .expression(coverage_expr)
            .ge()
            .rhs(float(date.min_drivers_required))
        )

    return model


# ==================== SOLUTION DISPLAY ====================


def display_solution(model: LXModel):
    """Display the optimization results."""

    print("\n" + "=" * 70)
    print("SOLUTION")
    print("=" * 70)

    optimizer = LXOptimizer().use_solver(solver_to_use)
    solution = optimizer.solve(model)

    if solution.is_optimal():
        print(f"Status: {solution.status}")
        print(f"Optimal Cost: ${solution.objective_value:,.2f}")
        print()

        # ===== DISPLAY BY DATE =====
        print("Schedule by Date:")
        print("-" * 70)
        for date in DATES:
            day_name = date.date.strftime("%A %b %d, %Y")
            multiplier = f" ({date.overtime_multiplier}x)" if date.is_weekend else ""
            print(f"\n{day_name}{multiplier}:")

            total_cost = 0
            for driver in DRIVERS:
                if not driver.is_active:
                    continue
                if not is_driver_available(driver, date):
                    continue

                # Access multi-indexed solution!
                # KEY: solution automatically maps to (driver, date) tuples
                value = solution.variables["duty"].get((driver.id, date.date), 0)

                if value > 0.5:  # Binary variable
                    cost = calculate_cost(driver, date)
                    total_cost += cost
                    print(f"  - {driver.name:10s} (${cost:6.2f})")

            print(f"  Daily Cost: ${total_cost:6.2f}")

        # ===== DISPLAY BY DRIVER =====
        print("\n")
        print("Driver Summary:")
        print("-" * 70)
        for driver in DRIVERS:
            if not driver.is_active:
                continue

            days_worked = []
            total_earnings = 0

            for date in DATES:
                if not is_driver_available(driver, date):
                    continue

                value = solution.variables["duty"].get((driver.id, date.date), 0)

                if value > 0.5:
                    days_worked.append(date.date.strftime("%a %m/%d"))
                    total_earnings += calculate_cost(driver, date)

            if days_worked:
                days_str = ", ".join(days_worked)
                print(f"  {driver.name:10s}: {len(days_worked)} days "
                      f"({days_str}) = ${total_earnings:.2f}")
            else:
                print(f"  {driver.name:10s}: Not scheduled")
    else:
        print(f"No optimal solution found. Status: {solution.status}")


# ==================== MAIN ====================


def main():
    """Run the driver scheduling optimization."""

    print("=" * 70)
    print("LumiX Example: Driver Scheduling (Multi-Model Indexing)")
    print("=" * 70)
    print()
    print("⭐⭐⭐ THIS IS THE KEY LUMIX FEATURE! ⭐⭐⭐")
    print()
    print("This example demonstrates:")
    print("  ✓ Multi-model indexing: LXVariable[Tuple[Driver, Date]]")
    print("  ✓ LXIndexDimension with filters")
    print("  ✓ CartesianProduct (Driver × Date)")
    print("  ✓ cost_multi() - cost function receives both models")
    print("  ✓ where_multi() - filter based on both models")
    print("  ✓ Cross-model constraints (sum over specific dimensions)")
    print("  ✓ Type-safe solution mapping")
    print()

    # Display problem data
    print("Drivers:")
    print("-" * 70)
    for d in DRIVERS:
        status = "Active" if d.is_active else "Inactive"
        off_days = ", ".join(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][day] for day in d.days_off)
        if not off_days:
            off_days = "None"
        print(
            f"  {d.name:10s}: ${d.daily_rate:6.2f}/day, max {d.max_days_per_week} days/week"
            f"  [{status}] (off: {off_days})"
        )
    print()

    print("Dates:")
    print("-" * 70)
    for dt in DATES:
        day_name = dt.date.strftime("%A %b %d")
        mult_str = f"{dt.overtime_multiplier}x" if dt.is_weekend else "1.0x"
        print(
            f"  {day_name}: {dt.min_drivers_required} drivers required "
            f"(cost multiplier: {mult_str})"
        )
    print()

    # Build model
    print("Building multi-model indexed optimization model...")
    model = build_scheduling_model()
    print(model.summary())

    # Solve and display solution
    display_solution(model)

    print()
    print("=" * 70)
    print("Why This Matters:")
    print("=" * 70)
    print()
    print("Traditional libraries force numerical indices:")
    print("  duty[0][1] = 1  # Which driver? Which date? IDE doesn't know!")
    print()
    print("LumiX preserves model relationships:")
    print("  solution.variables['duty'][(driver.id, date.date)]")
    print("      # Indexed by actual data model keys")
    print("      # IDE knows the structure and types")
    print("      # Type-safe access to solution values")
    print()
    print("This is optimization that feels like normal programming!")


if __name__ == "__main__":
    main()
