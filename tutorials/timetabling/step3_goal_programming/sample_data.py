"""Populate database with timetabling data including teacher preferences using SQLAlchemy ORM.

This module demonstrates how to populate a SQLAlchemy database using ORM
session operations instead of raw SQL INSERT statements. This approach provides:
    - Type safety: IDE autocomplete for model attributes
    - Automatic foreign key handling
    - Transaction management
    - Cleaner, more maintainable code

Teacher Preferences:
    - DAY_OFF: Teacher prefers to have a specific day completely free
    - SPECIFIC_TIME: Teacher prefers a specific lecture at a specific time

Priority Assignment:
    - Priority 1 (15+ years): Senior teachers' preferences
    - Priority 2 (7-14 years): Mid-level teachers' preferences
    - Priority 3 (0-6 years): Junior teachers' preferences

Usage:
    Run this script to populate the database:

    >>> python sample_data.py

    Or import and call populate_database():

    >>> from sample_data import populate_database
    >>> populate_database()
"""

from database import (
    init_database,
    get_session,
    clear_all_data,
    calculate_priority_from_work_years,
    Teacher,
    Classroom,
    SchoolClass,
    Subject,
    Lecture,
    TimeSlot,
    TeacherPreference,
)


def populate_database(database_url: str = "sqlite:///school.db"):
    """Populate database with sample data including teacher preferences using SQLAlchemy ORM.

    Creates and populates all tables with sample data:
        - 5 teachers (with work_years for seniority)
        - 4 classrooms
        - 4 school classes
        - 5 subjects
        - 20 lectures
        - 30 timeslots (5 days × 6 periods)
        - 7 teacher preferences (DAY_OFF and SPECIFIC_TIME)

    Args:
        database_url: SQLAlchemy database URL

    Example:
        >>> populate_database("sqlite:///school.db")
        >>> print("Database populated successfully!")
    """
    # Initialize database and create tables
    print("Initializing database...")
    engine = init_database(database_url)
    session = get_session(engine)

    try:
        # Clear existing data
        print("Clearing existing data...")
        clear_all_data(session)

        # ==================== INSERT TEACHERS (with work_years) ====================
        print("\nInserting teachers with seniority...")
        teachers = [
            Teacher(id=1, name="Dr. Smith", work_years=15),  # Priority 1 (Senior)
            Teacher(id=2, name="Prof. Johnson", work_years=10),  # Priority 2 (Mid-level)
            Teacher(id=3, name="Ms. Williams", work_years=5),  # Priority 3 (Junior)
            Teacher(id=4, name="Mr. Brown", work_years=20),  # Priority 1 (Senior)
            Teacher(id=5, name="Dr. Davis", work_years=3),  # Priority 3 (Junior)
        ]
        session.add_all(teachers)
        session.commit()

        for teacher in teachers:
            priority = calculate_priority_from_work_years(teacher.work_years)
            print(f"  {teacher.name}: {teacher.work_years} years → Priority {priority}")

        # ==================== INSERT CLASSROOMS ====================
        print("\nInserting classrooms...")
        classrooms = [
            Classroom(id=1, name="Room 101", capacity=30),
            Classroom(id=2, name="Room 102", capacity=30),
            Classroom(id=3, name="Room 201", capacity=25),
            Classroom(id=4, name="Lab A", capacity=20),
        ]
        session.add_all(classrooms)
        session.commit()

        # ==================== INSERT SCHOOL CLASSES ====================
        print("Inserting school classes...")
        classes = [
            SchoolClass(id=1, name="9A", size=25),
            SchoolClass(id=2, name="9B", size=28),
            SchoolClass(id=3, name="10A", size=24),
            SchoolClass(id=4, name="10B", size=26),
        ]
        session.add_all(classes)
        session.commit()

        # ==================== INSERT SUBJECTS ====================
        print("Inserting subjects...")
        subjects = [
            Subject(id=1, name="Mathematics"),
            Subject(id=2, name="English"),
            Subject(id=3, name="Physics"),
            Subject(id=4, name="Chemistry"),
            Subject(id=5, name="History"),
        ]
        session.add_all(subjects)
        session.commit()

        # ==================== INSERT TIMESLOTS ====================
        print("Inserting timeslots...")
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        timeslots = []
        slot_id = 1
        for day in range(5):  # Monday to Friday
            for period in range(1, 7):  # Periods 1-6
                timeslot = TimeSlot(
                    id=slot_id,
                    day_of_week=day,
                    period=period,
                    day_name=day_names[day],
                )
                timeslots.append(timeslot)
                slot_id += 1

        session.add_all(timeslots)
        session.commit()

        # ==================== INSERT LECTURES ====================
        print("Inserting lectures...")
        lectures = [
            # Mathematics lectures (Dr. Smith - 15 years - Priority 1)
            Lecture(id=1, subject_id=1, teacher_id=1, class_id=1),  # Math for 9A
            Lecture(id=2, subject_id=1, teacher_id=1, class_id=1),  # Math for 9A (2nd)
            Lecture(id=3, subject_id=1, teacher_id=1, class_id=2),  # Math for 9B
            Lecture(id=4, subject_id=1, teacher_id=1, class_id=2),  # Math for 9B (2nd)
            # English lectures (Prof. Johnson - 10 years - Priority 2)
            Lecture(id=5, subject_id=2, teacher_id=2, class_id=1),  # English for 9A
            Lecture(id=6, subject_id=2, teacher_id=2, class_id=2),  # English for 9B
            Lecture(id=7, subject_id=2, teacher_id=2, class_id=3),  # English for 10A
            # Physics lectures (Ms. Williams - 5 years - Priority 3)
            Lecture(id=8, subject_id=3, teacher_id=3, class_id=3),  # Physics for 10A
            Lecture(id=9, subject_id=3, teacher_id=3, class_id=3),  # Physics for 10A (2nd)
            Lecture(id=10, subject_id=3, teacher_id=3, class_id=4),  # Physics for 10B
            Lecture(id=11, subject_id=3, teacher_id=3, class_id=4),  # Physics for 10B (2nd)
            # Chemistry lectures (Mr. Brown - 20 years - Priority 1)
            Lecture(id=12, subject_id=4, teacher_id=4, class_id=3),  # Chemistry for 10A
            Lecture(id=13, subject_id=4, teacher_id=4, class_id=4),  # Chemistry for 10B
            # History lectures (Dr. Davis - 3 years - Priority 3)
            Lecture(id=14, subject_id=5, teacher_id=5, class_id=1),  # History for 9A
            Lecture(id=15, subject_id=5, teacher_id=5, class_id=2),  # History for 9B
            Lecture(id=16, subject_id=5, teacher_id=5, class_id=3),  # History for 10A
            Lecture(id=17, subject_id=5, teacher_id=5, class_id=4),  # History for 10B
            # Additional Math lectures for grade 10 (Dr. Smith)
            Lecture(id=18, subject_id=1, teacher_id=1, class_id=3),  # Math for 10A
            Lecture(id=19, subject_id=1, teacher_id=1, class_id=4),  # Math for 10B
            # Additional English lecture (Prof. Johnson)
            Lecture(id=20, subject_id=2, teacher_id=2, class_id=4),  # English for 10B
        ]
        session.add_all(lectures)
        session.commit()

        # ==================== INSERT TEACHER PREFERENCES ====================
        print("\nInserting teacher preferences...")

        preferences = [
            # Dr. Smith (15 years, Priority 1) - wants Tuesday completely free
            TeacherPreference(
                id=1,
                teacher_id=1,
                preference_type="DAY_OFF",
                day_of_week=1,  # Tuesday (0=Mon, 1=Tue, etc.)
                description="Dr. Smith prefers Tuesday completely free for research",
            ),
            # Dr. Smith - also wants first Math lecture for 9A on Monday Period 1
            TeacherPreference(
                id=2,
                teacher_id=1,
                preference_type="SPECIFIC_TIME",
                lecture_id=1,  # Math for 9A (first lecture)
                timeslot_id=1,  # Monday Period 1
                description="Dr. Smith prefers Math 9A on Monday Period 1",
            ),
            # Prof. Johnson (10 years, Priority 2) - wants Wednesday off
            TeacherPreference(
                id=3,
                teacher_id=2,
                preference_type="DAY_OFF",
                day_of_week=2,  # Wednesday
                description="Prof. Johnson prefers Wednesday off for professional development",
            ),
            # Ms. Williams (5 years, Priority 3) - wants Thursday off
            TeacherPreference(
                id=4,
                teacher_id=3,
                preference_type="DAY_OFF",
                day_of_week=3,  # Thursday
                description="Ms. Williams prefers Thursday off",
            ),
            # Mr. Brown (20 years, Priority 1) - wants Friday off (senior privilege)
            TeacherPreference(
                id=5,
                teacher_id=4,
                preference_type="DAY_OFF",
                day_of_week=4,  # Friday
                description="Mr. Brown (senior teacher) prefers Friday off",
            ),
            # Mr. Brown - also wants Chemistry 10A on Monday Period 2
            TeacherPreference(
                id=6,
                teacher_id=4,
                preference_type="SPECIFIC_TIME",
                lecture_id=12,  # Chemistry for 10A
                timeslot_id=2,  # Monday Period 2
                description="Mr. Brown prefers Chemistry 10A on Monday Period 2",
            ),
            # Dr. Davis (3 years, Priority 3) - wants History 9A on Friday Period 1
            TeacherPreference(
                id=7,
                teacher_id=5,
                preference_type="SPECIFIC_TIME",
                lecture_id=14,  # History for 9A
                timeslot_id=25,  # Friday Period 1
                description="Dr. Davis prefers History 9A on Friday morning",
            ),
        ]

        session.add_all(preferences)
        session.commit()

        # Display preferences
        for pref in preferences:
            teacher = next((t for t in teachers if t.id == pref.teacher_id), None)
            if teacher:
                priority = calculate_priority_from_work_years(teacher.work_years)

                if pref.preference_type == "DAY_OFF":
                    day = day_names[pref.day_of_week]
                    print(f"  [P{priority}] {teacher.name}: wants {day} off")
                else:  # SPECIFIC_TIME
                    lecture = next((l for l in lectures if l.id == pref.lecture_id), None)
                    if lecture:
                        subject_name = subjects[lecture.subject_id - 1].name
                        class_name = classes[lecture.class_id - 1].name
                        # Calculate day and period from timeslot_id
                        # timeslot_id 1-6 = Monday P1-6, 7-12 = Tuesday P1-6, etc.
                        timeslot_idx = pref.timeslot_id - 1
                        day_idx = timeslot_idx // 6
                        period = (timeslot_idx % 6) + 1
                        day = day_names[day_idx]
                        print(
                            f"  [P{priority}] {teacher.name}: wants {subject_name} {class_name} on {day} Period {period}"
                        )

        print(f"\n{'=' * 60}")
        print("Database populated successfully using SQLAlchemy ORM!")
        print(f"{'=' * 60}")
        print(f"  Teachers:    {len(teachers)}")
        print(f"  Classrooms:  {len(classrooms)}")
        print(f"  Classes:     {len(classes)}")
        print(f"  Subjects:    {len(subjects)}")
        print(f"  Lectures:    {len(lectures)}")
        print(f"  Timeslots:   {len(timeslots)} (5 days × 6 periods)")
        print(f"  Preferences: {len(preferences)}")
        print(f"{'=' * 60}")
        print("\nPriority Distribution:")
        print("  Priority 1 (15+ years): 2 teachers → High priority goals")
        print("  Priority 2 (7-14 years): 1 teacher → Medium priority goals")
        print("  Priority 3 (0-6 years):  2 teachers → Low priority goals")
        print(f"{'=' * 60}")
        print("\nORM Benefits Demonstrated:")
        print("  ✓ Type-safe model creation with IDE autocomplete")
        print("  ✓ Automatic foreign key validation")
        print("  ✓ session.add_all() for batch insertion")
        print("  ✓ session.commit() for transaction management")
        print("  ✓ No manual SQL queries needed")
        print(f"{'=' * 60}")

    finally:
        session.close()


if __name__ == "__main__":
    populate_database()
