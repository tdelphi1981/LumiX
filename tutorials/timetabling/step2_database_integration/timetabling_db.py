"""High School Course Timetabling: Step 2 - SQLAlchemy ORM Integration.

This example extends Step 1 by integrating SQLAlchemy ORM for data storage
and demonstrates LumiX's `from_model()` method for direct ORM integration.

Problem Description:
    Same as Step 1 - assign lectures to timeslots and classrooms while
    respecting scheduling constraints. The key difference is ORM integration:
        - SQLAlchemy declarative models instead of raw SQL
        - LumiX queries database directly using `from_model(session)`
        - Solution saved back to database using ORM
        - Type-safe database operations with IDE support

Key Features Demonstrated:
    - **ORM Integration**: SQLAlchemy declarative models
    - **from_model() usage**: LumiX queries database directly
    - **Type Safety**: IDE autocomplete for model attributes
    - **Solution Persistence**: Save results using ORM session

Prerequisites:
    Before running this script, populate the database:

    >>> python sample_data.py

Learning Objectives:
    1. How to use LumiX's `from_model()` with SQLAlchemy
    2. How LumiX integrates with ORM sessions
    3. How to persist optimization solutions via ORM
    4. Type-safe database operations
"""

from typing import Dict, Tuple

from lumix import (
    LXConstraint,
    LXIndexDimension,
    LXLinearExpression,
    LXModel,
    LXOptimizer,
    LXVariable,
)

from database import (
    init_database,
    get_session,
    Classroom,
    Lecture,
    SchoolClass,
    Teacher,
    TimeSlot,
    ScheduleAssignment,
    check_class_fits_classroom,
    create_cached_class_fits_checker,
    get_teacher_name,
    get_subject_name,
    get_class_name,
    get_classroom_name,
)

solver_to_use = "ortools"


# ==================== MODEL BUILDING ====================


def build_timetabling_model(session) -> LXModel:
    """Build the course timetabling model using ORM and from_model().

    This function demonstrates LumiX's ORM integration. Instead of manually
    querying the database and using from_data(), we use from_model(session)
    to let LumiX query the database directly.

    Args:
        session: SQLAlchemy Session instance.

    Returns:
        An LXModel instance ready to be solved.
    """
    print("\nBuilding course timetabling model with ORM integration...")
    print("  Using LumiX's from_model() for direct database querying")

    # Create cached checker for efficient lookups (avoids redundant DB queries)
    fits_checker = create_cached_class_fits_checker(session)

    # Decision variable: assignment[lecture, timeslot, classroom]
    # LumiX queries the database directly using from_model()
    assignment = (
        LXVariable[Tuple[Lecture, TimeSlot, Classroom], int]("assignment")
        .binary()
        .indexed_by_product(
            LXIndexDimension(Lecture, lambda lec: lec.id).from_model(session),
            LXIndexDimension(TimeSlot, lambda ts: ts.id).from_model(session),
            LXIndexDimension(Classroom, lambda room: room.id).from_model(session),
        )
        # Filter: classroom must fit the class (using cached checker for performance)
        .where_multi(
            lambda lec, ts, room: fits_checker(lec.class_id, room.id)
        )
    )

    # Create model
    model = LXModel("high_school_timetabling_orm")
    model.add_variable(assignment)

    # Get data counts for reporting (LumiX already queried via from_model)
    teachers = session.query(Teacher).all()
    classrooms = session.query(Classroom).all()
    classes = session.query(SchoolClass).all()
    lectures = session.query(Lecture).all()
    timeslots = session.query(TimeSlot).all()

    print(f"  Loaded {len(teachers)} teachers")
    print(f"  Loaded {len(classrooms)} classrooms")
    print(f"  Loaded {len(classes)} classes")
    print(f"  Loaded {len(lectures)} lectures")
    print(f"  Loaded {len(timeslots)} timeslots")

    # ========== CONSTRAINTS ==========

    # Constraint 1: Each lecture assigned exactly once
    print("\n  Adding hard constraints...")
    print("    - Lecture coverage constraints")
    for lecture in lectures:
        expr = LXLinearExpression().add_multi_term(
            assignment,
            coeff=lambda lec, ts, room: 1.0,
            where=lambda lec, ts, room, current_lecture=lecture: lec.id
            == current_lecture.id,
        )

        model.add_constraint(
            LXConstraint(f"lecture_{lecture.id}_assigned").expression(expr).eq().rhs(1)
        )

    # Constraint 2: No classroom conflicts
    print("    - Classroom conflict constraints")
    for timeslot in timeslots:
        for classroom in classrooms:
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

    # Constraint 3: No teacher conflicts
    print("    - Teacher conflict constraints")
    for teacher in teachers:
        teacher_lectures = [lec for lec in lectures if lec.teacher_id == teacher.id]

        for timeslot in timeslots:
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

    # Constraint 4: No class conflicts
    print("    - Class conflict constraints")
    for school_class in classes:
        class_lectures = [lec for lec in lectures if lec.class_id == school_class.id]

        for timeslot in timeslots:
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
    print(f"  Constraints: {len(model.constraints)} total")

    return model


# ==================== SOLUTION STORAGE ====================


def save_solution_to_db(solution, session):
    """Save the optimization solution to the database using ORM.

    Extracts all schedule assignments from the solution and stores
    them in the database using SQLAlchemy ORM.

    Args:
        solution: LXSolution object.
        session: SQLAlchemy Session instance.
    """
    if not solution.is_optimal() and not solution.is_feasible():
        print("\n❌ No solution to save!")
        return

    print("\nSaving solution to database using ORM...")

    # Delete existing assignments
    session.query(ScheduleAssignment).delete()

    count = 0
    assignments = []
    for (lecture_id, timeslot_id, classroom_id), value in solution.variables[
        "assignment"
    ].items():
        if value > 0.5:  # Binary variable is 1
            assignment = ScheduleAssignment(
                lecture_id=lecture_id,
                timeslot_id=timeslot_id,
                classroom_id=classroom_id,
            )
            assignments.append(assignment)
            count += 1

    session.add_all(assignments)
    session.commit()
    print(f"  Saved {count} schedule assignments")


# ==================== SOLUTION DISPLAY ====================


def display_teacher_timetable(
    session, teacher: Teacher, schedule_data: Dict[Tuple[int, int, int], int]
):
    """Display a teacher's weekly timetable."""
    print(f"\n{'=' * 80}")
    print(f"Timetable for {teacher.name}")
    print(f"{'=' * 80}")

    # Create grid
    grid = [[" " for _ in range(5)] for _ in range(6)]

    # Get teacher's lectures using ORM query
    lectures = session.query(Lecture).filter_by(teacher_id=teacher.id).all()
    timeslots = session.query(TimeSlot).all()
    classrooms = session.query(Classroom).all()

    # Fill grid
    for lecture in lectures:
        for timeslot in timeslots:
            for classroom in classrooms:
                key = (lecture.id, timeslot.id, classroom.id)
                if schedule_data.get(key, 0) == 1:
                    subject = get_subject_name(session, lecture.subject_id)
                    class_name = get_class_name(session, lecture.class_id)
                    room = get_classroom_name(session, classroom.id)
                    cell_content = f"{subject}\n{class_name}\n{room}"
                    grid[timeslot.period - 1][timeslot.day_of_week] = cell_content

    # Print timetable
    print(
        f"\n{'Period':<8} {'Monday':<20} {'Tuesday':<20} {'Wednesday':<20} {'Thursday':<20} {'Friday':<20}"
    )
    print("-" * 108)

    for period in range(6):
        lines = [
            grid[period][day].split("\n") if grid[period][day] != " " else [" "]
            for day in range(5)
        ]
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
    session,
    school_class: SchoolClass,
    schedule_data: Dict[Tuple[int, int, int], int],
):
    """Display a class's weekly timetable."""
    print(f"\n{'=' * 80}")
    print(f"Timetable for Class {school_class.name}")
    print(f"{'=' * 80}")

    # Create grid
    grid = [[" " for _ in range(5)] for _ in range(6)]

    # Get class's lectures using ORM query
    lectures = session.query(Lecture).filter_by(class_id=school_class.id).all()
    timeslots = session.query(TimeSlot).all()
    classrooms = session.query(Classroom).all()

    # Fill grid
    for lecture in lectures:
        for timeslot in timeslots:
            for classroom in classrooms:
                key = (lecture.id, timeslot.id, classroom.id)
                if schedule_data.get(key, 0) == 1:
                    subject = get_subject_name(session, lecture.subject_id)
                    teacher = get_teacher_name(session, lecture.teacher_id)
                    room = get_classroom_name(session, classroom.id)
                    cell_content = f"{subject}\n{teacher}\n{room}"
                    grid[timeslot.period - 1][timeslot.day_of_week] = cell_content

    # Print timetable
    print(
        f"\n{'Period':<8} {'Monday':<20} {'Tuesday':<20} {'Wednesday':<20} {'Thursday':<20} {'Friday':<20}"
    )
    print("-" * 108)

    for period in range(6):
        lines = [
            grid[period][day].split("\n") if grid[period][day] != " " else [" "]
            for day in range(5)
        ]
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


def display_solution(solution, session):
    """Display the complete solution."""
    if not solution.is_optimal() and not solution.is_feasible():
        print("\n❌ No feasible solution found!")
        return

    print(f"\n{'=' * 80}")
    print("TIMETABLING SOLUTION (ORM-based)")
    print(f"{'=' * 80}")
    print(f"Status: {solution.status}")

    # Extract schedule
    schedule_data = {}
    for (lecture_id, timeslot_id, classroom_id), value in solution.variables[
        "assignment"
    ].items():
        if value > 0.5:
            schedule_data[(lecture_id, timeslot_id, classroom_id)] = 1

    # Display all timetables using ORM queries
    teachers = session.query(Teacher).all()
    classes = session.query(SchoolClass).all()

    for teacher in teachers:
        display_teacher_timetable(session, teacher, schedule_data)

    for school_class in classes:
        display_class_timetable(session, school_class, schedule_data)


# ==================== MAIN ====================


def main():
    """Run the ORM-integrated timetabling example."""
    print("=" * 80)
    print("LumiX Tutorial: High School Course Timetabling - Step 2")
    print("=" * 80)
    print("\nThis example demonstrates:")
    print("  ✓ SQLAlchemy ORM declarative models")
    print("  ✓ LumiX's from_model(session) for direct database querying")
    print("  ✓ Type-safe ORM operations with IDE support")
    print("  ✓ Saving solutions using ORM session")

    # Initialize database and create session
    engine = init_database("sqlite:///school.db")
    session = get_session(engine)

    try:
        # Verify database is populated
        teachers = session.query(Teacher).all()
        if not teachers:
            print("\n❌ Database is empty! Please run sample_data.py first:")
            print("   python sample_data.py")
            return

        # Build and solve model using from_model()
        model = build_timetabling_model(session)
        optimizer = LXOptimizer().use_solver(solver_to_use)

        print(f"\nSolving with {solver_to_use}...")
        solution = optimizer.solve(model)

        # Display results
        display_solution(solution, session)

        # Save solution to database using ORM
        save_solution_to_db(solution, session)

        print("\n" + "=" * 80)
        print("Tutorial Step 2 Complete!")
        print("=" * 80)
        print("\nWhat changed from Step 1:")
        print("  → SQLAlchemy ORM models instead of raw Python lists")
        print("  → from_model(session) instead of from_data()")
        print("  → LumiX queries database directly")
        print("  → Type-safe ORM operations")
        print("\nORM Benefits:")
        print("  ✓ No manual SQL queries")
        print("  ✓ IDE autocomplete for model attributes")
        print("  ✓ Automatic foreign key validation")
        print("  ✓ Type-safe database operations")
        print("\nNext Steps:")
        print("  → Step 3: Add teacher preferences with goal programming")

    finally:
        session.close()


if __name__ == "__main__":
    main()
