"""High School Course Timetabling: Step 3 - Goal Programming with Teacher Preferences.

This example extends Step 2 by adding teacher preferences as soft constraints
using LumiX's goal programming feature. Teachers can express preferences like
"I want Tuesdays off" or "I want to teach Math on Monday Period 1", and these
preferences are converted to goals with priorities based on teacher seniority.

Problem Description:
    Same as Steps 1 & 2, but now with:
        - Hard constraints: Basic timetabling rules (must be satisfied)
        - Soft constraints (goals): Teacher preferences (minimize violations)
        - Priority levels: Senior teachers (Priority 1) > Mid-level (Priority 2) > Junior (Priority 3)

Key Features Demonstrated:
    - **Goal programming**: Multi-objective optimization with soft constraints
    - **Priority-based scheduling**: Seniority determines goal priority
    - **Mixed constraints**: Hard constraints + soft goals
    - **Preference satisfaction analysis**: Track which goals were achieved

Mathematical Formulation:
    Hard Constraints (same as Steps 1 & 2):
        - Each lecture assigned exactly once
        - No classroom/teacher/class conflicts
        - Classroom capacity constraints

    Soft Constraints (Goals):
        - DAY_OFF preference: Minimize ∑(assignment[l, t, r]) for all timeslots t on preferred day
        - SPECIFIC_TIME preference: assignment[specific_lecture, specific_timeslot, any_room] = 1

    Priorities:
        - Priority 1: Teachers with 15+ years of service
        - Priority 2: Teachers with 7-14 years of service
        - Priority 3: Teachers with 0-6 years of service

Learning Objectives:
    1. How to convert teacher preferences to goal constraints
    2. How to assign priorities based on seniority
    3. How to mix hard and soft constraints
    4. How to analyze goal satisfaction
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

from database import (
    init_database,
    get_session,
    calculate_priority_from_work_years,
    check_class_fits_classroom,
    create_cached_class_fits_checker,
    get_teacher_name,
    get_subject_name,
    get_class_name,
    get_classroom_name,
    Classroom,
    Lecture,
    SchoolClass,
    Teacher,
    TeacherPreference,
    TimeSlot,
    ScheduleAssignment,
)

solver_to_use = "gurobi"


# ==================== MODEL BUILDING ====================


def build_timetabling_model_with_goals(session) -> LXModel:
    """Build timetabling model with goal programming for teacher preferences using ORM.

    This function builds the same basic model as Steps 1 & 2, then adds
    teacher preferences as soft goal constraints with priorities. Uses
    SQLAlchemy ORM and LumiX's from_model() for direct database integration.

    Args:
        session: SQLAlchemy Session instance.

    Returns:
        An LXModel instance with both hard constraints and soft goals.
    """
    print("\nLoading data from database using ORM...")
    teachers = session.query(Teacher).all()
    classrooms = session.query(Classroom).all()
    classes = session.query(SchoolClass).all()
    lectures = session.query(Lecture).all()
    timeslots = session.query(TimeSlot).all()
    preferences = session.query(TeacherPreference).all()

    print(f"  Loaded {len(teachers)} teachers")
    print(f"  Loaded {len(classrooms)} classrooms")
    print(f"  Loaded {len(classes)} classes")
    print(f"  Loaded {len(lectures)} lectures")
    print(f"  Loaded {len(timeslots)} timeslots")
    print(f"  Loaded {len(preferences)} teacher preferences")

    print("\nBuilding course timetabling model with goal programming...")
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
    model = LXModel("high_school_timetabling_goals")
    model.add_variable(assignment)

    # ========== HARD CONSTRAINTS (same as Steps 1 & 2) ==========

    # Constraint 1: Each lecture assigned exactly once (HARD)
    print("  Adding hard constraints...")
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

    # Constraint 2: No classroom conflicts (HARD)
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

    # Constraint 3: No teacher conflicts (HARD)
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

    # Constraint 4: No class conflicts (HARD)
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

    # ========== SOFT CONSTRAINTS (GOALS based on teacher preferences) ==========

    print("\n  Adding soft goal constraints (teacher preferences)...")

    for pref in preferences:
        teacher = next((t for t in teachers if t.id == pref.teacher_id), None)
        if not teacher:
            continue

        # Calculate priority from teacher's work years
        priority = calculate_priority_from_work_years(teacher.work_years)
        teacher_name = teacher.name

        if pref.preference_type == "DAY_OFF":
            # Goal: Minimize assignments on the preferred day off
            # Get all timeslots for the specified day
            day_timeslots = [
                ts for ts in timeslots if ts.day_of_week == pref.day_of_week
            ]

            # Get all lectures taught by this teacher
            teacher_lectures = [lec for lec in lectures if lec.teacher_id == teacher.id]

            # Sum of all assignments on that day for this teacher
            expr = LXLinearExpression().add_multi_term(
                assignment,
                coeff=lambda lec, ts, room: 1.0,
                where=lambda lec, ts, room, t_lectures=teacher_lectures, d_slots=day_timeslots: lec.id
                in [tl.id for tl in t_lectures]
                and ts.id in [ds.id for ds in d_slots],
            )

            # Goal: minimize this sum (ideally 0 = complete day off)
            day_name = day_timeslots[0].day_name if day_timeslots else "Unknown"
            goal_name = f"day_off_teacher_{teacher.id}_{day_name}"

            model.add_constraint(
                LXConstraint(goal_name)
                .expression(expr)
                .le()
                .rhs(0)  # Target: 0 assignments on this day
                .as_goal(priority=priority, weight=1.0)
            )

            print(
                f"    [P{priority}] {teacher_name}: wants {day_name} off (goal: 0 lectures)"
            )

        elif pref.preference_type == "SPECIFIC_TIME":
            # Goal: Assign specific lecture to specific timeslot
            # Expression: sum of assignments for this lecture at this timeslot (across all classrooms)
            expr = LXLinearExpression().add_multi_term(
                assignment,
                coeff=lambda lec, ts, room: 1.0,
                where=lambda lec, ts, room, target_lec=pref.lecture_id, target_ts=pref.timeslot_id: lec.id
                == target_lec
                and ts.id == target_ts,
            )

            # Goal: this sum should equal 1 (lecture is assigned to that timeslot)
            goal_name = f"specific_time_teacher_{teacher.id}_lecture_{pref.lecture_id}"

            model.add_constraint(
                LXConstraint(goal_name)
                .expression(expr)
                .eq()
                .rhs(1)  # Target: exactly 1 (assigned to this timeslot)
                .as_goal(priority=priority, weight=1.0)
            )

            lecture = next((l for l in lectures if l.id == pref.lecture_id), None)
            timeslot = next((ts for ts in timeslots if ts.id == pref.timeslot_id), None)
            if lecture and timeslot:
                subject_name = get_subject_name(session, lecture.subject_id)
                class_name = get_class_name(session, lecture.class_id)
                print(
                    f"    [P{priority}] {teacher_name}: wants {subject_name} {class_name} on {timeslot.day_name} Period {timeslot.period}"
                )

    # Set goal programming mode
    model.set_goal_mode("weighted")

    print(f"\nModel built successfully!")
    print(f"  Hard constraints: {len([c for c in model.constraints if not c.is_goal()])}")
    print(f"  Soft goals: {len([c for c in model.constraints if c.is_goal()])}")
    print(f"  Total constraints: {len(model.constraints)}")

    return model


# ==================== SOLUTION ANALYSIS ====================


def analyze_goal_satisfaction(solution, session):
    """Analyze which teacher preferences were satisfied.

    Args:
        solution: LXSolution object.
        session: SQLAlchemy Session instance.
    """
    print(f"\n{'=' * 80}")
    print("GOAL SATISFACTION ANALYSIS")
    print(f"{'=' * 80}")

    preferences = session.query(TeacherPreference).all()
    teachers = session.query(Teacher).all()

    # Group preferences by priority
    priority_groups = {1: [], 2: [], 3: []}

    for pref in preferences:
        teacher = next((t for t in teachers if t.id == pref.teacher_id), None)
        if not teacher:
            continue

        priority = calculate_priority_from_work_years(teacher.work_years)

        if pref.preference_type == "DAY_OFF":
            timeslots = session.query(TimeSlot).all()
            day_timeslots = [
                ts for ts in timeslots if ts.day_of_week == pref.day_of_week
            ]
            day_name = day_timeslots[0].day_name if day_timeslots else "Unknown"
            goal_name = f"day_off_teacher_{teacher.id}_{day_name}"
        else:  # SPECIFIC_TIME
            goal_name = f"specific_time_teacher_{teacher.id}_lecture_{pref.lecture_id}"

        # Check goal satisfaction
        try:
            deviations = solution.get_goal_deviations(goal_name)
            satisfied = solution.is_goal_satisfied(goal_name, tolerance=1e-6)

            priority_groups[priority].append(
                {
                    "teacher": teacher,
                    "preference": pref,
                    "goal_name": goal_name,
                    "satisfied": satisfied,
                    "deviations": deviations,
                }
            )
        except Exception as e:
            print(f"  Warning: Could not analyze goal {goal_name}: {e}")

    # Display by priority
    for priority in [1, 2, 3]:
        priority_name = (
            "Senior (15+ years)"
            if priority == 1
            else "Mid-level (7-14 years)" if priority == 2 else "Junior (0-6 years)"
        )
        print(f"\nPriority {priority} ({priority_name}):")
        print("-" * 80)

        group = priority_groups[priority]
        if not group:
            print("  (No preferences at this priority level)")
            continue

        satisfied_count = sum(1 for g in group if g["satisfied"])
        total_count = len(group)

        for g in group:
            teacher = g["teacher"]
            pref = g["preference"]
            satisfied = g["satisfied"]
            deviations = g["deviations"]

            status = "✓ SATISFIED" if satisfied else "✗ NOT SATISFIED"

            # Extract deviation value from the deviations structure
            if isinstance(deviations, dict):
                # Handle dict format: extract total deviation
                # deviations might be {"pos": {...}, "neg": {...}}
                pos_dict = deviations.get("pos", {})
                neg_dict = deviations.get("neg", {})

                # Extract numeric values from nested dicts
                if isinstance(pos_dict, dict):
                    # Sum all values in the pos dict
                    pos_value = sum(v for v in pos_dict.values() if isinstance(v, (int, float)))
                else:
                    pos_value = pos_dict if isinstance(pos_dict, (int, float)) else 0

                if isinstance(neg_dict, dict):
                    # Sum all values in the neg dict
                    neg_value = sum(v for v in neg_dict.values() if isinstance(v, (int, float)))
                else:
                    neg_value = neg_dict if isinstance(neg_dict, (int, float)) else 0

                dev_value = pos_value + neg_value
            else:
                # Handle numeric format
                dev_value = deviations

            if pref.preference_type == "DAY_OFF":
                timeslots = session.query(TimeSlot).all()
                day_name = next(
                    (ts.day_name for ts in timeslots if ts.day_of_week == pref.day_of_week),
                    "Unknown",
                )
                print(
                    f"  {status}: {teacher.name} wants {day_name} off (deviation: {dev_value:.0f} lectures)"
                )
            else:  # SPECIFIC_TIME
                lecture = next(
                    (l for l in session.query(Lecture).all() if l.id == pref.lecture_id), None
                )
                timeslot = next(
                    (ts for ts in session.query(TimeSlot).all() if ts.id == pref.timeslot_id),
                    None,
                )
                if lecture and timeslot:
                    subject_name = get_subject_name(session, lecture.subject_id)
                    class_name = get_class_name(session, lecture.class_id)
                    print(
                        f"  {status}: {teacher.name} wants {subject_name} {class_name} on {timeslot.day_name} P{timeslot.period} (deviation: {dev_value:.2f})"
                    )

        print(f"\nPriority {priority} Summary: {satisfied_count}/{total_count} preferences satisfied")


# ==================== SOLUTION DISPLAY ====================


def display_teacher_timetable(
    session, teacher: Teacher, schedule_data: Dict[Tuple[int, int, int], int]
):
    """Display a teacher's weekly timetable using ORM."""
    print(f"\n{'=' * 80}")
    print(f"Timetable for {teacher.name} ({teacher.work_years} years of service)")
    print(f"{'=' * 80}")

    # Create grid
    grid = [[" " for _ in range(5)] for _ in range(6)]

    # Get teacher's lectures using ORM query
    lectures = session.query(Lecture).all()
    teacher_lectures = [lec for lec in lectures if lec.teacher_id == teacher.id]
    timeslots = session.query(TimeSlot).all()
    classrooms = session.query(Classroom).all()

    # Fill grid
    for lecture in teacher_lectures:
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


def display_solution(solution, session):
    """Display the complete solution using ORM."""
    if not solution.is_optimal() and not solution.is_feasible():
        print("\n❌ No feasible solution found!")
        return

    print(f"\n{'=' * 80}")
    print("TIMETABLING SOLUTION WITH GOAL PROGRAMMING (ORM-based)")
    print(f"{'=' * 80}")
    print(f"Status: {solution.status}")
    print(f"Objective value: {solution.objective_value:.4f}")

    # Extract schedule
    schedule_data = {}
    for (lecture_id, timeslot_id, classroom_id), value in solution.variables[
        "assignment"
    ].items():
        if value > 0.5:
            schedule_data[(lecture_id, timeslot_id, classroom_id)] = 1

    # Display teacher timetables using ORM queries
    teachers = session.query(Teacher).all()
    for teacher in teachers:
        display_teacher_timetable(session, teacher, schedule_data)

    # Analyze goal satisfaction
    analyze_goal_satisfaction(solution, session)


# ==================== MAIN ====================


def main():
    """Run the goal programming timetabling example with ORM integration."""
    print("=" * 80)
    print("LumiX Tutorial: High School Course Timetabling - Step 3")
    print("=" * 80)
    print("\nThis example demonstrates:")
    print("  ✓ SQLAlchemy ORM with goal programming")
    print("  ✓ LumiX's from_model(session) for direct database querying")
    print("  ✓ Priority-based optimization (seniority determines priority)")
    print("  ✓ Mixed hard constraints + soft goals")
    print("  ✓ Preference satisfaction analysis")

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
        model = build_timetabling_model_with_goals(session)

        # Prepare goal programming
        print("\nPreparing goal programming...")
        model.prepare_goal_programming()

        optimizer = LXOptimizer().use_solver(solver_to_use)

        print(f"\nSolving with {solver_to_use} (goal programming mode)...")
        solution = optimizer.solve(model)

        # Display results
        display_solution(solution, session)

        # Save solution to database using ORM
        print("\nSaving solution to database using ORM...")
        session.query(ScheduleAssignment).delete()

        count = 0
        assignments = []
        for (
            lecture_id,
            timeslot_id,
            classroom_id,
        ), value in solution.variables["assignment"].items():
            if value > 0.5:
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

        print("\n" + "=" * 80)
        print("Tutorial Step 3 Complete!")
        print("=" * 80)
        print("\nWhat's new in Step 3:")
        print("  → SQLAlchemy ORM models with teacher preferences")
        print("  → from_model(session) instead of from_data()")
        print("  → Teacher preferences as soft goal constraints")
        print("  → Priority levels based on teacher seniority (work years)")
        print("  → Goal programming: minimize preference violations")
        print("  → Comprehensive goal satisfaction analysis")
        print("\nORM Benefits:")
        print("  ✓ No manual SQL queries")
        print("  ✓ IDE autocomplete for model attributes")
        print("  ✓ Automatic foreign key validation")
        print("  ✓ Type-safe database operations")
        print("\nKey Insights:")
        print("  • Senior teachers' preferences are prioritized")
        print("  • Hard constraints always satisfied")
        print("  • Soft goals minimized based on priority")
        print("  • Trade-offs visible in goal satisfaction report")

    finally:
        session.close()


if __name__ == "__main__":
    main()
