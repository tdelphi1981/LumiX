"""High School Course Timetabling: Step 1 - Basic Timetabling.

This example demonstrates how to build a course timetabling optimization model
using LumiX with multi-dimensional indexing. The problem assigns lectures to
timeslots and classrooms while respecting various scheduling constraints.

Problem Description:
    A high school needs to create a weekly timetable that assigns lectures
    (teacher-subject-class combinations) to specific timeslots and classrooms.
    The schedule must ensure:
        - Each lecture is scheduled exactly once
        - No classroom conflicts (one lecture per room per timeslot)
        - No teacher conflicts (teacher can't teach two lectures simultaneously)
        - No class conflicts (class can't attend two lectures simultaneously)
        - Classroom capacity is sufficient for class size

Mathematical Formulation:
    Decision Variables:
        assignment[l, t, r] ∈ {0, 1} for each (lecture, timeslot, classroom) triplet

    Objective:
        Feasibility problem (find any valid schedule)

    Subject to:
        - Each lecture scheduled once: sum(assignment[l, t, r] for all t, r) = 1
        - Classroom capacity: assignment[l, t, r] = 0 if class size > room capacity
        - No classroom conflicts: sum(assignment[l, t, r] for all l) <= 1
        - No teacher conflicts: sum(assignment[l, t, r] for all l with same teacher) <= 1
        - No class conflicts: sum(assignment[l, t, r] for all l with same class) <= 1

Key Features Demonstrated:
    - **3D multi-model indexing**: Variables indexed by (Lecture, TimeSlot, Classroom)
    - **Cartesian product**: All valid combinations of three models
    - **Complex filtering**: where_multi() to exclude infeasible assignments
    - **Cross-dimensional constraints**: Summing over specific dimensions
    - **Tabular output**: Generating timetables for teachers and classes

Use Cases:
    This pattern is ideal for:
        - School and university course scheduling
        - Training session planning
        - Conference room booking
        - Resource allocation with time and space dimensions

Learning Objectives:
    1. How to create 3D indexed variables (Lecture × TimeSlot × Classroom)
    2. How to build complex scheduling constraints
    3. How to filter combinations based on multiple criteria
    4. How to generate human-readable timetable outputs
    5. How to structure a complete timetabling solution
"""

from typing import Dict, List, Tuple

from lumix import (
    LXConstraint,
    LXIndexDimension,
    LXLinearExpression,
    LXModel,
    LXOptimizer,
    LXVariable,
)

from sample_data import (
    CLASSES,
    CLASSROOMS,
    LECTURES,
    TEACHERS,
    TIMESLOTS,
    Classroom,
    Lecture,
    SchoolClass,
    Teacher,
    TimeSlot,
    check_class_fits_classroom,
    get_class_name,
    get_classroom_name,
    get_subject_name,
    get_teacher_name,
)

solver_to_use = "ortools"


# ==================== MODEL BUILDING ====================


def build_timetabling_model() -> LXModel:
    """Build the course timetabling optimization model.

    This function demonstrates multi-dimensional indexing with three models:
    Lecture, TimeSlot, and Classroom. The assignment variable is indexed by
    the cartesian product (Lecture × TimeSlot × Classroom).

    Returns:
        An LXModel instance containing:
            - Variables: assignment[lecture, timeslot, classroom]
            - Objective: Feasibility (no specific objective function)
            - Constraints: Lecture coverage, room/teacher/class conflicts

    Example:
        >>> model = build_timetabling_model()
        >>> optimizer = LXOptimizer().use_solver("ortools")
        >>> solution = optimizer.solve(model)
    """
    print("\nBuilding course timetabling model...")

    # Decision variable: assignment[lecture, timeslot, classroom]
    # Binary: 1 if lecture is assigned to timeslot in classroom, 0 otherwise
    assignment = (
        LXVariable[Tuple[Lecture, TimeSlot, Classroom], int]("assignment")
        .binary()
        .indexed_by_product(
            LXIndexDimension(Lecture, lambda lec: lec.id).from_data(LECTURES),
            LXIndexDimension(TimeSlot, lambda ts: ts.id).from_data(TIMESLOTS),
            LXIndexDimension(Classroom, lambda room: room.id).from_data(CLASSROOMS),
        )
        # Filter out invalid assignments (classroom too small for class)
        .where_multi(
            lambda lec, ts, room: check_class_fits_classroom(lec.class_id, room.id)
        )
    )

    # Create model
    model = LXModel("high_school_timetabling")
    model.add_variable(assignment)

    # ========== CONSTRAINTS ==========

    # Constraint 1: Each lecture must be assigned to exactly one timeslot and classroom
    print("  Adding lecture coverage constraints...")
    for lecture in LECTURES:
        expr = LXLinearExpression().add_multi_term(
            assignment,
            coeff=lambda lec, ts, room: 1.0,
            where=lambda lec, ts, room, current_lecture=lecture: lec.id
            == current_lecture.id,
        )

        model.add_constraint(
            LXConstraint(f"lecture_{lecture.id}_assigned").expression(expr).eq().rhs(1)
        )

    # Constraint 2: No classroom conflicts (max one lecture per classroom per timeslot)
    print("  Adding classroom conflict constraints...")
    for timeslot in TIMESLOTS:
        for classroom in CLASSROOMS:
            expr = LXLinearExpression().add_multi_term(
                assignment,
                coeff=lambda lec, ts, room: 1.0,
                where=lambda lec, ts, room, current_ts=timeslot, current_room=classroom: ts.id
                == current_ts.id
                and room.id == current_room.id,
            )

            model.add_constraint(
                LXConstraint(f"room_{classroom.id}_slot_{timeslot.id}")
                .expression(expr)
                .le()
                .rhs(1)
            )

    # Constraint 3: No teacher conflicts (teacher can't teach multiple lectures at same time)
    print("  Adding teacher conflict constraints...")
    for teacher in TEACHERS:
        # Get all lectures taught by this teacher
        teacher_lectures = [lec for lec in LECTURES if lec.teacher_id == teacher.id]

        for timeslot in TIMESLOTS:
            expr = LXLinearExpression().add_multi_term(
                assignment,
                coeff=lambda lec, ts, room: 1.0,
                where=lambda lec, ts, room, current_ts=timeslot, t_lectures=teacher_lectures: ts.id
                == current_ts.id
                and lec.id in [tl.id for tl in t_lectures],
            )

            model.add_constraint(
                LXConstraint(f"teacher_{teacher.id}_slot_{timeslot.id}")
                .expression(expr)
                .le()
                .rhs(1)
            )

    # Constraint 4: No class conflicts (class can't attend multiple lectures at same time)
    print("  Adding class conflict constraints...")
    for school_class in CLASSES:
        # Get all lectures for this class
        class_lectures = [lec for lec in LECTURES if lec.class_id == school_class.id]

        for timeslot in TIMESLOTS:
            expr = LXLinearExpression().add_multi_term(
                assignment,
                coeff=lambda lec, ts, room: 1.0,
                where=lambda lec, ts, room, current_ts=timeslot, c_lectures=class_lectures: ts.id
                == current_ts.id
                and lec.id in [cl.id for cl in c_lectures],
            )

            model.add_constraint(
                LXConstraint(f"class_{school_class.id}_slot_{timeslot.id}")
                .expression(expr)
                .le()
                .rhs(1)
            )

    print(f"\nModel built successfully!")
    print(f"  Variables: {len(LECTURES)} lectures × {len(TIMESLOTS)} timeslots × {len(CLASSROOMS)} classrooms")
    print(f"  Constraints: {len(model.constraints)} total")

    return model


# ==================== SOLUTION DISPLAY ====================


def display_teacher_timetable(
    solution, teacher: Teacher, schedule_data: Dict[Tuple[int, int, int], int]
):
    """Display a teacher's weekly timetable in tabular format.

    Args:
        solution: The LXSolution object.
        teacher: The teacher whose timetable to display.
        schedule_data: Dictionary mapping (lecture_id, timeslot_id, classroom_id) to 1.
    """
    print(f"\n{'=' * 80}")
    print(f"Timetable for {teacher.name}")
    print(f"{'=' * 80}")

    # Create a grid: rows = periods, columns = days
    grid = [[" " for _ in range(5)] for _ in range(6)]  # 6 periods × 5 days

    # Get all lectures taught by this teacher
    teacher_lectures = [lec for lec in LECTURES if lec.teacher_id == teacher.id]

    # Fill the grid
    for lecture in teacher_lectures:
        for timeslot in TIMESLOTS:
            for classroom in CLASSROOMS:
                key = (lecture.id, timeslot.id, classroom.id)
                if schedule_data.get(key, 0) == 1:
                    subject = get_subject_name(lecture.subject_id)
                    class_name = get_class_name(lecture.class_id)
                    room = get_classroom_name(classroom.id)
                    cell_content = f"{subject}\n{class_name}\n{room}"
                    grid[timeslot.period - 1][timeslot.day_of_week] = cell_content

    # Print the timetable
    print(f"\n{'Period':<8} {'Monday':<20} {'Tuesday':<20} {'Wednesday':<20} {'Thursday':<20} {'Friday':<20}")
    print("-" * 108)

    for period in range(6):
        # Print first line of each period
        lines = [grid[period][day].split("\n") if grid[period][day] != " " else [" "] for day in range(5)]
        max_lines = max(len(line) for line in lines)

        for line_idx in range(max_lines):
            if line_idx == 0:
                print(f"{period + 1:<8}", end=" ")
            else:
                print(f"{'  ':<8}", end=" ")

            for day in range(5):
                if line_idx < len(lines[day]):
                    print(f"{lines[day][line_idx]:<20}", end=" ")
                else:
                    print(f"{'':<20}", end=" ")
            print()


def display_class_timetable(
    solution, school_class: SchoolClass, schedule_data: Dict[Tuple[int, int, int], int]
):
    """Display a class's weekly timetable in tabular format.

    Args:
        solution: The LXSolution object.
        school_class: The class whose timetable to display.
        schedule_data: Dictionary mapping (lecture_id, timeslot_id, classroom_id) to 1.
    """
    print(f"\n{'=' * 80}")
    print(f"Timetable for Class {school_class.name}")
    print(f"{'=' * 80}")

    # Create a grid: rows = periods, columns = days
    grid = [[" " for _ in range(5)] for _ in range(6)]  # 6 periods × 5 days

    # Get all lectures for this class
    class_lectures = [lec for lec in LECTURES if lec.class_id == school_class.id]

    # Fill the grid
    for lecture in class_lectures:
        for timeslot in TIMESLOTS:
            for classroom in CLASSROOMS:
                key = (lecture.id, timeslot.id, classroom.id)
                if schedule_data.get(key, 0) == 1:
                    subject = get_subject_name(lecture.subject_id)
                    teacher = get_teacher_name(lecture.teacher_id)
                    room = get_classroom_name(classroom.id)
                    cell_content = f"{subject}\n{teacher}\n{room}"
                    grid[timeslot.period - 1][timeslot.day_of_week] = cell_content

    # Print the timetable
    print(f"\n{'Period':<8} {'Monday':<20} {'Tuesday':<20} {'Wednesday':<20} {'Thursday':<20} {'Friday':<20}")
    print("-" * 108)

    for period in range(6):
        # Print first line of each period
        lines = [grid[period][day].split("\n") if grid[period][day] != " " else [" "] for day in range(5)]
        max_lines = max(len(line) for line in lines)

        for line_idx in range(max_lines):
            if line_idx == 0:
                print(f"{period + 1:<8}", end=" ")
            else:
                print(f"{'  ':<8}", end=" ")

            for day in range(5):
                if line_idx < len(lines[day]):
                    print(f"{lines[day][line_idx]:<20}", end=" ")
                else:
                    print(f"{'':<20}", end=" ")
            print()


def display_solution(solution):
    """Display the complete timetabling solution.

    Args:
        solution: The LXSolution object.
    """
    if not solution.is_optimal() and not solution.is_feasible():
        print("\n❌ No feasible solution found!")
        return

    print(f"\n{'=' * 80}")
    print("TIMETABLING SOLUTION")
    print(f"{'=' * 80}")
    print(f"Status: {solution.status}")

    # Extract schedule data
    schedule_data = {}
    for (lecture_id, timeslot_id, classroom_id), value in solution.variables["assignment"].items():
        if value > 0.5:  # Binary variable is 1
            schedule_data[(lecture_id, timeslot_id, classroom_id)] = 1

    # Display timetables for all teachers
    for teacher in TEACHERS:
        display_teacher_timetable(solution, teacher, schedule_data)

    # Display timetables for all classes
    for school_class in CLASSES:
        display_class_timetable(solution, school_class, schedule_data)


# ==================== MAIN ====================


def main():
    """Run the course timetabling optimization example.

    This is the main entry point that builds the model, solves it,
    and displays the resulting timetables.
    """
    print("=" * 80)
    print("LumiX Tutorial: High School Course Timetabling - Step 1")
    print("=" * 80)
    print("\nThis example demonstrates:")
    print("  ✓ 3D multi-model indexing: LXVariable[Tuple[Lecture, TimeSlot, Classroom]]")
    print("  ✓ Cartesian product (Lecture × TimeSlot × Classroom)")
    print("  ✓ Complex scheduling constraints")
    print("  ✓ Filtering infeasible combinations with where_multi()")
    print("  ✓ Tabular timetable generation")

    print(f"\nProblem Size:")
    print(f"  Teachers: {len(TEACHERS)}")
    print(f"  Classrooms: {len(CLASSROOMS)}")
    print(f"  Classes: {len(CLASSES)}")
    print(f"  Lectures: {len(LECTURES)}")
    print(f"  Timeslots: {len(TIMESLOTS)} ({len(TIMESLOTS) // 6} days × 6 periods)")

    # Build and solve model
    model = build_timetabling_model()
    optimizer = LXOptimizer().use_solver(solver_to_use)

    print(f"\nSolving with {solver_to_use}...")
    solution = optimizer.solve(model)

    # Display results
    display_solution(solution)

    print("\n" + "=" * 80)
    print("Tutorial Step 1 Complete!")
    print("=" * 80)
    print("\nNext Steps:")
    print("  → Step 2: Add database integration (SQLite)")
    print("  → Step 3: Add teacher preferences with goal programming")


if __name__ == "__main__":
    main()
