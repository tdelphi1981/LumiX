"""Populate database with sample timetabling data using SQLAlchemy ORM.

This module demonstrates how to populate a SQLAlchemy database using ORM
session operations instead of raw SQL INSERT statements. This approach provides:
    - Type safety: IDE autocomplete for model attributes
    - Automatic foreign key handling
    - Transaction management
    - Cleaner, more maintainable code

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
    Teacher,
    Classroom,
    SchoolClass,
    Subject,
    Lecture,
    TimeSlot,
)


def populate_database(database_url: str = "sqlite:///school.db"):
    """Populate database with sample timetabling data using SQLAlchemy ORM.

    Creates and populates all tables with sample data:
        - 5 teachers
        - 4 classrooms
        - 4 school classes
        - 5 subjects
        - 20 lectures
        - 30 timeslots (5 days × 6 periods)

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

        # ==================== INSERT TEACHERS ====================
        print("Inserting teachers...")
        teachers = [
            Teacher(id=1, name="Dr. Smith"),
            Teacher(id=2, name="Prof. Johnson"),
            Teacher(id=3, name="Ms. Williams"),
            Teacher(id=4, name="Mr. Brown"),
            Teacher(id=5, name="Dr. Davis"),
        ]
        session.add_all(teachers)
        session.commit()

        # ==================== INSERT CLASSROOMS ====================
        print("Inserting classrooms...")
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
            # Mathematics lectures (Dr. Smith teaches Math)
            Lecture(id=1, subject_id=1, teacher_id=1, class_id=1),  # Math for 9A
            Lecture(
                id=2, subject_id=1, teacher_id=1, class_id=1
            ),  # Math for 9A (2nd)
            Lecture(id=3, subject_id=1, teacher_id=1, class_id=2),  # Math for 9B
            Lecture(
                id=4, subject_id=1, teacher_id=1, class_id=2
            ),  # Math for 9B (2nd)
            # English lectures (Prof. Johnson teaches English)
            Lecture(id=5, subject_id=2, teacher_id=2, class_id=1),  # English for 9A
            Lecture(id=6, subject_id=2, teacher_id=2, class_id=2),  # English for 9B
            Lecture(id=7, subject_id=2, teacher_id=2, class_id=3),  # English for 10A
            # Physics lectures (Ms. Williams teaches Physics)
            Lecture(id=8, subject_id=3, teacher_id=3, class_id=3),  # Physics for 10A
            Lecture(
                id=9, subject_id=3, teacher_id=3, class_id=3
            ),  # Physics for 10A (2nd)
            Lecture(id=10, subject_id=3, teacher_id=3, class_id=4),  # Physics for 10B
            Lecture(
                id=11, subject_id=3, teacher_id=3, class_id=4
            ),  # Physics for 10B (2nd)
            # Chemistry lectures (Mr. Brown teaches Chemistry)
            Lecture(id=12, subject_id=4, teacher_id=4, class_id=3),  # Chemistry for 10A
            Lecture(id=13, subject_id=4, teacher_id=4, class_id=4),  # Chemistry for 10B
            # History lectures (Dr. Davis teaches History)
            Lecture(id=14, subject_id=5, teacher_id=5, class_id=1),  # History for 9A
            Lecture(id=15, subject_id=5, teacher_id=5, class_id=2),  # History for 9B
            Lecture(id=16, subject_id=5, teacher_id=5, class_id=3),  # History for 10A
            Lecture(id=17, subject_id=5, teacher_id=5, class_id=4),  # History for 10B
            # Additional Math lectures for grade 10
            Lecture(id=18, subject_id=1, teacher_id=1, class_id=3),  # Math for 10A
            Lecture(id=19, subject_id=1, teacher_id=1, class_id=4),  # Math for 10B
            # Additional English lecture
            Lecture(id=20, subject_id=2, teacher_id=2, class_id=4),  # English for 10B
        ]
        session.add_all(lectures)
        session.commit()

        print(f"\n{'=' * 60}")
        print("Database populated successfully using SQLAlchemy ORM!")
        print(f"{'=' * 60}")
        print(f"  Teachers:   {len(teachers)}")
        print(f"  Classrooms: {len(classrooms)}")
        print(f"  Classes:    {len(classes)}")
        print(f"  Subjects:   {len(subjects)}")
        print(f"  Lectures:   {len(lectures)}")
        print(f"  Timeslots:  {len(timeslots)} (5 days × 6 periods)")
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
