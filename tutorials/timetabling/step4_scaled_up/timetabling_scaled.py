"""High School Course Timetabling: Step 4 - Large-Scale with Room Type Constraints.

This example demonstrates LumiX's capability to handle realistic large-scale problems
efficiently while introducing room type constraints for specialized classrooms.

Problem Scale Comparison:
    Step 3: 5 teachers, 4 classrooms, 4 classes, 20 lectures, 30 timeslots
    Step 4: 15 teachers, 12 classrooms, 12 classes, 80 lectures, 40 timeslots

    Variables: ~38,400 (compared to ~2,400 in Step 3)
    Constraints: ~600 hard + ~35 soft goals (compared to ~150 + ~7 in Step 3)

New Features in Step 4:
    - **Room Type Constraints**: Chemistry/Physics/Biology require LAB rooms, PE requires GYM
    - **3x Larger Scale**: More realistic high school size (4 grades × 3 classes each)
    - **More Departments**: Math/Science (8 teachers), Humanities (5), PE (2)
    - **40 Timeslots**: 8 periods per day instead of 6
    - **Enhanced Analytics**: Better solution quality reporting
    - **Interactive HTML Report**: Modern dashboard with timetables and statistics

Prerequisites:
    Before running this script, populate the database:

    >>> python sample_data.py

Learning Objectives:
    1. How LumiX handles large-scale problems efficiently
    2. How to implement room type constraints for specialized rooms
    3. How cached checkers improve performance at scale
    4. How goal programming scales with problem size
    5. How to analyze solution quality for large problems
    6. How to generate interactive HTML reports for solutions
"""

import time
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
    TeacherPreference,
    create_cached_compatibility_checker,
    calculate_priority_from_work_years,
    get_teacher_name,
    get_subject_name,
    get_class_name,
    get_classroom_name,
)
from report_generator import generate_html_report

solver_to_use = "ortools"


# ==================== MODEL BUILDING ====================


def build_timetabling_model(session) -> LXModel:
    """Build the large-scale timetabling model with room type constraints.

    This function demonstrates LumiX's ability to handle realistic-sized problems
    with complex constraints. The key addition is room type constraints where
    lab subjects (Chemistry, Physics, Biology) require LAB rooms and PE requires GYM.

    Args:
        session: SQLAlchemy Session instance.

    Returns:
        An LXModel instance ready to be solved.
    """
    print("\n" + "=" * 80)
    print("BUILDING LARGE-SCALE TIMETABLING MODEL")
    print("=" * 80)
    print("\nUsing LumiX's from_model() for direct database querying...")

    start_time = time.time()

    # Create cached compatibility checker (capacity + room type)
    # This is crucial for performance - avoids thousands of database queries
    print("  Creating cached compatibility checker...")
    compatibility_checker = create_cached_compatibility_checker(session)

    # Decision variable: assignment[lecture, timeslot, classroom]
    # Now includes room type filtering
    print("  Creating 3D decision variables...")
    assignment = (
        LXVariable[Tuple[Lecture, TimeSlot, Classroom], int]("assignment")
        .binary()
        .indexed_by_product(
            LXIndexDimension(Lecture, lambda lec: lec.id).from_model(session),
            LXIndexDimension(TimeSlot, lambda ts: ts.id).from_model(session),
            LXIndexDimension(Classroom, lambda room: room.id).from_model(session),
        )
        # Filter: classroom must fit class AND room type must match subject
        .where_multi(
            lambda lec, ts, room: compatibility_checker(lec.id, room.id)
        )
    )

    # Create model
    model = LXModel("high_school_timetabling_large_scale")
    model.add_variable(assignment)

    variable_creation_time = time.time() - start_time

    # Query counts directly (not loading into lists)
    num_teachers = session.query(Teacher).count()
    num_classrooms = session.query(Classroom).count()
    num_classes = session.query(SchoolClass).count()
    num_lectures = session.query(Lecture).count()
    num_timeslots = session.query(TimeSlot).count()

    print(f"\n  Dataset Statistics:")
    print(f"    Teachers:   {num_teachers:3d}")
    print(f"    Classrooms: {num_classrooms:3d} (8 regular, 3 labs, 1 gym)")
    print(f"    Classes:    {num_classes:3d} (4 grades × 3 classes)")
    print(f"    Lectures:   {num_lectures:3d}")
    print(f"    Timeslots:  {num_timeslots:3d} (5 days × 8 periods)")
    print(f"\n  Model Size:")
    print(f"    Potential variables: {num_lectures * num_timeslots * num_classrooms:,}")
    print(f"    (Actual count reduced after room type filtering)")
    print(f"    Variable creation time: {variable_creation_time:.2f}s")

    # ========== HARD CONSTRAINTS ==========

    print(f"\n  Building hard constraints...")
    constraint_start = time.time()

    # Constraint 1: Each lecture assigned exactly once
    print("    [1/4] Lecture coverage constraints...")
    # Query lectures directly from database (no pre-loading into list)
    for lecture in session.query(Lecture).all():
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
    print("    [2/4] Classroom conflict constraints...")
    # Query timeslots and classrooms directly from database
    for timeslot in session.query(TimeSlot).all():
        for classroom in session.query(Classroom).all():
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
    print("    [3/4] Teacher conflict constraints...")
    # Query teachers directly and use ORM relationship filtering
    for teacher in session.query(Teacher).all():
        # Query only this teacher's lectures (ORM filtering, not loading all lectures)
        teacher_lecture_ids = [lec.id for lec in session.query(Lecture).filter_by(teacher_id=teacher.id).all()]

        for timeslot in session.query(TimeSlot).all():
            expr = LXLinearExpression().add_multi_term(
                assignment,
                coeff=lambda lec, ts, room: 1.0,
                where=lambda lec, ts, room, current_ts=timeslot, t_lec_ids=teacher_lecture_ids: ts.id
                == current_ts.id
                and lec.id in t_lec_ids,
            )

            model.add_constraint(
                LXConstraint(f"teacher_{teacher.id}_slot_{timeslot.id}")
                .expression(expr)
                .le()
                .rhs(1)
            )

    # Constraint 4: No class conflicts
    print("    [4/4] Class conflict constraints...")
    # Query school classes directly and use ORM relationship filtering
    for school_class in session.query(SchoolClass).all():
        # Query only this class's lectures (ORM filtering, not loading all lectures)
        class_lecture_ids = [lec.id for lec in session.query(Lecture).filter_by(class_id=school_class.id).all()]

        for timeslot in session.query(TimeSlot).all():
            expr = LXLinearExpression().add_multi_term(
                assignment,
                coeff=lambda lec, ts, room: 1.0,
                where=lambda lec, ts, room, current_ts=timeslot, c_lec_ids=class_lecture_ids: ts.id
                == current_ts.id
                and lec.id in c_lec_ids,
            )

            model.add_constraint(
                LXConstraint(f"class_{school_class.id}_slot_{timeslot.id}")
                .expression(expr)
                .le()
                .rhs(1)
            )

    constraint_time = time.time() - constraint_start

    # Count hard constraints
    hard_constraints = [c for c in model.constraints if not c.is_goal()]

    print(f"\n  Hard constraints: {len(hard_constraints):,}")
    print(f"  Constraint creation time: {constraint_time:.2f}s")

    # ========== GOAL PROGRAMMING (Soft Constraints) ==========

    print(f"\n  Building goal programming constraints...")
    goal_start = time.time()

    # Query count of teacher preferences directly
    num_preferences = session.query(TeacherPreference).count()
    print(f"    Processing {num_preferences} teacher preferences...")

    priority_counts = {1: 0, 2: 0, 3: 0}

    # Query preferences directly from database (no pre-loading into list)
    for pref in session.query(TeacherPreference).all():
        teacher = session.query(Teacher).filter_by(id=pref.teacher_id).first()
        if not teacher:
            continue

        priority = calculate_priority_from_work_years(teacher.work_years)
        priority_counts[priority] += 1

        if pref.preference_type == "DAY_OFF":
            # Goal: Minimize lectures on preferred day
            # Query only this teacher's lectures (ORM filtering)
            teacher_lecture_ids = [lec.id for lec in session.query(Lecture).filter_by(teacher_id=pref.teacher_id).all()]
            # Query only this day's timeslots (ORM filtering)
            day_timeslot_ids = [ts.id for ts in session.query(TimeSlot).filter_by(day_of_week=pref.day_of_week).all()]

            expr = LXLinearExpression().add_multi_term(
                assignment,
                coeff=lambda lec, ts, room: 1.0,
                where=lambda lec, ts, room, t_lec_ids=teacher_lecture_ids, d_slot_ids=day_timeslot_ids:
                    lec.id in t_lec_ids
                    and ts.id in d_slot_ids,
            )

            model.add_constraint(
                LXConstraint(f"pref_{pref.id}_day_off")
                .expression(expr)
                .le()
                .rhs(0)
                .as_goal(priority=priority, weight=1.0)
            )

        elif pref.preference_type == "SPECIFIC_TIME":
            # Goal: Assign lecture to specific timeslot
            expr = LXLinearExpression().add_multi_term(
                assignment,
                coeff=lambda lec, ts, room: 1.0,
                where=lambda lec, ts, room, target_lec=pref.lecture_id, target_ts=pref.timeslot_id:
                    lec.id == target_lec and ts.id == target_ts,
            )

            model.add_constraint(
                LXConstraint(f"pref_{pref.id}_specific_time")
                .expression(expr)
                .ge()
                .rhs(1)
                .as_goal(priority=priority, weight=1.0)
            )

    goal_time = time.time() - goal_start

    # Count soft constraints (goals)
    soft_constraints = [c for c in model.constraints if c.is_goal()]

    print(f"\n  Soft constraints (goals): {len(soft_constraints)}")
    print(f"    Priority 1: {priority_counts[1]} goals")
    print(f"    Priority 2: {priority_counts[2]} goals")
    print(f"    Priority 3: {priority_counts[3]} goals")
    print(f"  Goal creation time: {goal_time:.2f}s")

    total_time = time.time() - start_time

    print(f"\n{'=' * 80}")
    print(f"MODEL BUILT SUCCESSFULLY!")
    print(f"{'=' * 80}")
    print(f"  Total constraints: {len(model.constraints):,} ({len(hard_constraints):,} hard + {len(soft_constraints)} soft)")
    print(f"  Total build time: {total_time:.2f}s")
    print(f"{'=' * 80}")

    # Enable goal programming
    model.set_goal_mode("weighted")
    model.prepare_goal_programming()

    return model


# ==================== SOLUTION STORAGE ====================


def save_solution_to_db(solution, session):
    """Save the optimization solution to the database using ORM.

    Args:
        solution: LXSolution object.
        session: SQLAlchemy Session instance.
    """
    if not solution.is_optimal() and not solution.is_feasible():
        print("\n❌ No solution to save!")
        return

    print("\n" + "=" * 80)
    print("SAVING SOLUTION TO DATABASE")
    print("=" * 80)

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
    print(f"  ✓ Saved {count} schedule assignments")
    print("=" * 80)


# ==================== SOLUTION ANALYSIS ====================


def analyze_goal_satisfaction(solution, session):
    """Analyze which goals were satisfied and which were violated.

    Args:
        solution: LXSolution object
        session: SQLAlchemy Session
    """
    print("\n" + "=" * 80)
    print("GOAL SATISFACTION ANALYSIS")
    print("=" * 80)

    preferences = session.query(TeacherPreference).all()
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

    # Group by priority
    by_priority = {1: [], 2: [], 3: []}

    for pref in preferences:
        teacher = session.query(Teacher).filter_by(id=pref.teacher_id).first()
        if not teacher:
            continue

        priority = calculate_priority_from_work_years(teacher.work_years)
        by_priority[priority].append((pref, teacher))

    # Analyze each priority level
    for priority in [1, 2, 3]:
        prefs_at_level = by_priority[priority]
        if not prefs_at_level:
            continue

        print(f"\nPriority {priority} Goals ({len(prefs_at_level)} total):")
        print("-" * 80)

        satisfied = 0
        violated = 0

        for pref, teacher in prefs_at_level:
            constraint_name = None
            if pref.preference_type == "DAY_OFF":
                constraint_name = f"pref_{pref.id}_day_off"
            elif pref.preference_type == "SPECIFIC_TIME":
                constraint_name = f"pref_{pref.id}_specific_time"

            if constraint_name:
                deviations = solution.get_goal_deviations(constraint_name)

                # Extract deviation value from nested structure
                if isinstance(deviations, dict):
                    pos_dict = deviations.get("pos", {})
                    neg_dict = deviations.get("neg", {})

                    if isinstance(pos_dict, dict):
                        pos_value = sum(v for v in pos_dict.values() if isinstance(v, (int, float)))
                    else:
                        pos_value = pos_dict if isinstance(pos_dict, (int, float)) else 0

                    if isinstance(neg_dict, dict):
                        neg_value = sum(v for v in neg_dict.values() if isinstance(v, (int, float)))
                    else:
                        neg_value = neg_dict if isinstance(neg_dict, (int, float)) else 0

                    dev_value = pos_value + neg_value
                else:
                    dev_value = deviations if isinstance(deviations, (int, float)) else 0

                is_satisfied = dev_value < 0.1

                if is_satisfied:
                    satisfied += 1
                    status = "✓"
                else:
                    violated += 1
                    status = "✗"

                # Format description
                if pref.preference_type == "DAY_OFF":
                    day = day_names[pref.day_of_week]
                    desc = f"{teacher.name:30s} wants {day:9s} off"
                else:  # SPECIFIC_TIME
                    lecture = session.query(Lecture).filter_by(id=pref.lecture_id).first()
                    if lecture:
                        subject_name = get_subject_name(session, lecture.subject_id)
                        class_name = get_class_name(session, lecture.class_id)
                        timeslot = session.query(TimeSlot).filter_by(id=pref.timeslot_id).first()
                        if timeslot:
                            desc = f"{teacher.name:30s} wants {subject_name} {class_name} on {timeslot.day_name} P{timeslot.period}"
                        else:
                            desc = f"{teacher.name:30s} - specific time preference"
                    else:
                        desc = f"{teacher.name:30s} - specific time preference"

                print(f"  {status} {desc}")

        print(f"\n  Summary: {satisfied}/{len(prefs_at_level)} satisfied ({100*satisfied/len(prefs_at_level):.0f}%)")


def print_solution_summary(solution, session):
    """Print a compact summary of the solution.

    Args:
        solution: LXSolution object
        session: SQLAlchemy Session
    """
    print("\n" + "=" * 80)
    print("SOLUTION SUMMARY")
    print("=" * 80)

    print(f"\nStatus: {solution.status}")

    # Count assignments
    total_assignments = sum(1 for v in solution.variables["assignment"].values() if v > 0.5)
    num_lectures = session.query(Lecture).count()

    print(f"Lectures scheduled: {total_assignments}/{num_lectures}")

    # Room type usage (query all classrooms to build room_usage dict)
    room_usage = {}
    for room in session.query(Classroom).all():
        if room.room_type not in room_usage:
            room_usage[room.room_type] = 0

    for (lecture_id, timeslot_id, classroom_id), value in solution.variables["assignment"].items():
        if value > 0.5:
            classroom = session.query(Classroom).filter_by(id=classroom_id).first()
            if classroom:
                room_usage[classroom.room_type] += 1

    print(f"\nRoom Type Usage:")
    print(f"  REGULAR: {room_usage.get('REGULAR', 0)} assignments")
    print(f"  LAB:     {room_usage.get('LAB', 0)} assignments")
    print(f"  GYM:     {room_usage.get('GYM', 0)} assignments")

    print("=" * 80)


# ==================== TIMETABLE DISPLAY ====================


def display_teacher_timetable_compact(session, teacher: Teacher, schedule_data: Dict[Tuple[int, int, int], int]):
    """Display a teacher's weekly timetable in compact format.

    For large-scale problems, we only show teachers with preferences.
    """
    print(f"\n{'=' * 80}")
    print(f"Timetable for {teacher.name} ({teacher.work_years} years)")
    print(f"{'=' * 80}")

    # Create grid
    grid = [[" " for _ in range(5)] for _ in range(8)]  # 8 periods × 5 days

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

    for period in range(8):
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
    """Display the solution with focus on teachers with preferences.

    For large-scale problems, we don't show all timetables, just those
    with preferences to keep output manageable.
    """
    if not solution.is_optimal() and not solution.is_feasible():
        print("\n❌ No feasible solution found!")
        return

    # Extract schedule
    schedule_data = {}
    for (lecture_id, timeslot_id, classroom_id), value in solution.variables[
        "assignment"
    ].items():
        if value > 0.5:
            schedule_data[(lecture_id, timeslot_id, classroom_id)] = 1

    # Display summary
    print_solution_summary(solution, session)

    # Analyze goals
    analyze_goal_satisfaction(solution, session)

    # Show timetables for teachers with preferences only
    print("\n" + "=" * 80)
    print("SAMPLE TIMETABLES (Teachers with Preferences)")
    print("=" * 80)

    teachers_with_prefs = set()
    preferences = session.query(TeacherPreference).all()
    for pref in preferences:
        teachers_with_prefs.add(pref.teacher_id)

    # Show only first 3 teachers with preferences to keep output manageable
    shown = 0
    for teacher_id in sorted(teachers_with_prefs):
        if shown >= 3:
            print(f"\n... (showing first 3 of {len(teachers_with_prefs)} teachers with preferences)")
            break

        teacher = session.query(Teacher).filter_by(id=teacher_id).first()
        if teacher:
            display_teacher_timetable_compact(session, teacher, schedule_data)
            shown += 1


# ==================== MAIN ====================


def main():
    """Run the large-scale timetabling example."""
    print("=" * 80)
    print("LUMIX TUTORIAL: HIGH SCHOOL TIMETABLING - STEP 4")
    print("LARGE-SCALE WITH ROOM TYPE CONSTRAINTS")
    print("=" * 80)
    print("\nThis example demonstrates:")
    print("  ✓ Large-scale optimization (3x the size of Step 3)")
    print("  ✓ Room type constraints (LAB for sciences, GYM for PE)")
    print("  ✓ Efficient handling via cached compatibility checker")
    print("  ✓ Goal programming at scale (35+ preferences)")
    print("  ✓ Realistic multi-grade, multi-department structure")

    # Initialize database and create session
    engine = init_database("sqlite:///school_large.db")
    session = get_session(engine)

    try:
        # Verify database is populated
        num_teachers = session.query(Teacher).count()
        if num_teachers == 0:
            print("\n❌ Database is empty! Please run sample_data.py first:")
            print("   python sample_data.py")
            return

        # Build and solve model
        start_time = time.time()
        model = build_timetabling_model(session)
        build_time = time.time() - start_time

        optimizer = LXOptimizer().use_solver(solver_to_use)

        print(f"\n{'=' * 80}")
        print(f"SOLVING WITH {solver_to_use.upper()}...")
        print(f"{'=' * 80}")
        print("This may take 10-30 seconds for a problem of this size...")

        solve_start = time.time()
        solution = optimizer.solve(model)
        solve_time = time.time() - solve_start

        print(f"\n{'=' * 80}")
        print("OPTIMIZATION COMPLETE!")
        print(f"{'=' * 80}")
        print(f"  Build time:  {build_time:.2f}s")
        print(f"  Solve time:  {solve_time:.2f}s")
        print(f"  Total time:  {build_time + solve_time:.2f}s")
        print(f"{'=' * 80}")

        # Display results
        display_solution(solution, session)

        # Save solution to database
        save_solution_to_db(solution, session)

        # Generate interactive HTML report
        generate_html_report(solution, session, "timetable_report.html")

        print("\n" + "=" * 80)
        print("TUTORIAL STEP 4 COMPLETE!")
        print("=" * 80)
        print("\nWhat's different from Step 3:")
        print("  → 3x larger scale (15 teachers, 12 rooms, 12 classes, 80 lectures)")
        print("  → Room type constraints (LAB for sciences, GYM for PE)")
        print("  → Cached compatibility checker for performance")
        print("  → 40 timeslots (8 periods per day)")
        print("  → More realistic department structure")
        print("  → Interactive HTML report with modern dashboard")
        print("\nKey Takeaways:")
        print("  ✓ LumiX handles large-scale problems efficiently")
        print("  ✓ Room type constraints are easy to model")
        print("  ✓ Caching is crucial for performance at scale")
        print("  ✓ Goal programming scales well with problem size")
        print("  ✓ Solution quality remains high even with size increase")
        print("  ✓ Rich visualization with interactive HTML reports")
        print("\n📊 Open 'timetable_report.html' in your browser to explore the interactive dashboard!")
        print("=" * 80)

    finally:
        session.close()


if __name__ == "__main__":
    main()
