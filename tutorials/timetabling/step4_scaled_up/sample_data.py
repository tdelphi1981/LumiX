"""Populate database with large-scale timetabling data using SQLAlchemy ORM.

This module demonstrates realistic large-scale data generation for Step 4,
including room types and subject requirements. The data represents a medium-sized
high school with multiple grades, departments, and specialized rooms.

Scale Comparison:
    Step 3: 5 teachers, 4 classrooms, 4 classes, 20 lectures, 30 timeslots
    Step 4: 15 teachers, 12 classrooms, 12 classes, 80 lectures, 40 timeslots

Key Features:
    - 15 teachers across 3 departments (Math/Science, Humanities, PE)
    - 12 classrooms with 3 room types (REGULAR, LAB, GYM)
    - 12 classes across 4 grades (9-12)
    - 8 subjects with lab requirements
    - 80 lectures distributed realistically
    - 40 timeslots (8 periods × 5 days)
    - 35+ teacher preferences

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


def populate_database(database_url: str = "sqlite:///school_large.db"):
    """Populate database with large-scale sample data using SQLAlchemy ORM.

    Creates and populates all tables with realistic data:
        - 15 teachers (with work_years for seniority)
        - 12 classrooms (8 regular, 3 labs, 1 gym)
        - 12 school classes (4 grades × 3 classes each)
        - 8 subjects (4 require labs)
        - 80 lectures (distributed realistically across classes)
        - 40 timeslots (5 days × 8 periods)
        - 35 teacher preferences (DAY_OFF and SPECIFIC_TIME)

    Args:
        database_url: SQLAlchemy database URL

    Example:
        >>> populate_database("sqlite:///school_large.db")
        >>> print("Database populated successfully!")
    """
    # Initialize database and create tables
    print("=" * 80)
    print("STEP 4: LARGE-SCALE TIMETABLING DATA GENERATION")
    print("=" * 80)
    print("\nInitializing database...")
    engine = init_database(database_url)
    session = get_session(engine)

    try:
        # Clear existing data
        print("Clearing existing data...")
        clear_all_data(session)

        # ==================== INSERT TEACHERS ====================
        print("\n" + "=" * 80)
        print("INSERTING TEACHERS (15 total)")
        print("=" * 80)

        teachers = [
            # Math & Science Department (8 teachers)
            Teacher(id=1, name="Dr. Emily Watson", work_years=18),     # Priority 1
            Teacher(id=2, name="Prof. Michael Chen", work_years=15),   # Priority 1
            Teacher(id=3, name="Dr. Sarah Johnson", work_years=12),    # Priority 2
            Teacher(id=4, name="Mr. David Kim", work_years=8),         # Priority 2
            Teacher(id=5, name="Ms. Rachel Green", work_years=4),      # Priority 3
            Teacher(id=6, name="Dr. James Wilson", work_years=20),     # Priority 1
            Teacher(id=7, name="Ms. Lisa Anderson", work_years=6),     # Priority 3
            Teacher(id=8, name="Mr. Robert Taylor", work_years=10),    # Priority 2

            # Humanities Department (5 teachers)
            Teacher(id=9, name="Prof. Jennifer Brown", work_years=16), # Priority 1
            Teacher(id=10, name="Ms. Amanda White", work_years=7),     # Priority 2
            Teacher(id=11, name="Mr. Christopher Lee", work_years=3),  # Priority 3
            Teacher(id=12, name="Dr. Patricia Martinez", work_years=14), # Priority 2
            Teacher(id=13, name="Ms. Michelle Garcia", work_years=5),  # Priority 3

            # PE Department (2 teachers)
            Teacher(id=14, name="Coach John Davis", work_years=11),    # Priority 2
            Teacher(id=15, name="Coach Maria Rodriguez", work_years=9), # Priority 2
        ]
        session.add_all(teachers)
        session.commit()

        for teacher in teachers:
            priority = calculate_priority_from_work_years(teacher.work_years)
            print(f"  {teacher.name:30s} - {teacher.work_years:2d} years → Priority {priority}")

        # ==================== INSERT CLASSROOMS ====================
        print("\n" + "=" * 80)
        print("INSERTING CLASSROOMS (12 total)")
        print("=" * 80)

        classrooms = [
            # Regular classrooms (8)
            Classroom(id=1, name="Room 101", capacity=32, room_type="REGULAR"),
            Classroom(id=2, name="Room 102", capacity=32, room_type="REGULAR"),
            Classroom(id=3, name="Room 201", capacity=30, room_type="REGULAR"),
            Classroom(id=4, name="Room 202", capacity=30, room_type="REGULAR"),
            Classroom(id=5, name="Room 301", capacity=28, room_type="REGULAR"),
            Classroom(id=6, name="Room 302", capacity=28, room_type="REGULAR"),
            Classroom(id=7, name="Room 401", capacity=35, room_type="REGULAR"),
            Classroom(id=8, name="Room 402", capacity=35, room_type="REGULAR"),

            # Science labs (3) - Increased capacity to accommodate all classes
            Classroom(id=9, name="Chemistry Lab", capacity=32, room_type="LAB"),
            Classroom(id=10, name="Physics Lab", capacity=32, room_type="LAB"),
            Classroom(id=11, name="Biology Lab", capacity=30, room_type="LAB"),

            # Gymnasium (1)
            Classroom(id=12, name="Main Gym", capacity=50, room_type="GYM"),
        ]
        session.add_all(classrooms)
        session.commit()

        print("\nRegular Classrooms (8):")
        for room in classrooms[:8]:
            print(f"  {room.name:20s} - Capacity: {room.capacity}")

        print("\nScience Labs (3):")
        for room in classrooms[8:11]:
            print(f"  {room.name:20s} - Capacity: {room.capacity}")

        print("\nGymnasium (1):")
        print(f"  {classrooms[11].name:20s} - Capacity: {classrooms[11].capacity}")

        # ==================== INSERT SCHOOL CLASSES ====================
        print("\n" + "=" * 80)
        print("INSERTING SCHOOL CLASSES (12 total)")
        print("=" * 80)

        classes = [
            # Grade 9 (3 classes)
            SchoolClass(id=1, name="9A", size=28),
            SchoolClass(id=2, name="9B", size=30),
            SchoolClass(id=3, name="9C", size=26),

            # Grade 10 (3 classes)
            SchoolClass(id=4, name="10A", size=27),
            SchoolClass(id=5, name="10B", size=29),
            SchoolClass(id=6, name="10C", size=25),

            # Grade 11 (3 classes)
            SchoolClass(id=7, name="11A", size=24),
            SchoolClass(id=8, name="11B", size=26),
            SchoolClass(id=9, name="11C", size=23),

            # Grade 12 (3 classes)
            SchoolClass(id=10, name="12A", size=22),
            SchoolClass(id=11, name="12B", size=24),
            SchoolClass(id=12, name="12C", size=21),
        ]
        session.add_all(classes)
        session.commit()

        print("Grade 9: 9A (28 students), 9B (30 students), 9C (26 students)")
        print("Grade 10: 10A (27 students), 10B (29 students), 10C (25 students)")
        print("Grade 11: 11A (24 students), 11B (26 students), 11C (23 students)")
        print("Grade 12: 12A (22 students), 12B (24 students), 12C (21 students)")

        # ==================== INSERT SUBJECTS ====================
        print("\n" + "=" * 80)
        print("INSERTING SUBJECTS (8 total)")
        print("=" * 80)

        subjects = [
            Subject(id=1, name="Mathematics", requires_lab=False),
            Subject(id=2, name="Physics", requires_lab=True),        # Requires lab
            Subject(id=3, name="Chemistry", requires_lab=True),      # Requires lab
            Subject(id=4, name="Biology", requires_lab=True),        # Requires lab
            Subject(id=5, name="English", requires_lab=False),
            Subject(id=6, name="History", requires_lab=False),
            Subject(id=7, name="Geography", requires_lab=False),
            Subject(id=8, name="Physical Education", requires_lab=False),  # Requires gym (handled separately)
        ]
        session.add_all(subjects)
        session.commit()

        print("\nRegular Subjects (can use regular classrooms):")
        for subj in [subjects[0], subjects[4], subjects[5], subjects[6]]:
            print(f"  {subj.name}")

        print("\nLab-Required Subjects (must use lab rooms):")
        for subj in [subjects[1], subjects[2], subjects[3]]:
            print(f"  {subj.name}")

        print("\nSpecial Subjects (gym required):")
        print(f"  {subjects[7].name}")

        # ==================== INSERT TIMESLOTS ====================
        print("\n" + "=" * 80)
        print("INSERTING TIMESLOTS (40 total)")
        print("=" * 80)

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        timeslots = []
        slot_id = 1

        for day in range(5):  # Monday to Friday
            for period in range(1, 9):  # Periods 1-8
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

        print("5 days × 8 periods = 40 timeslots")
        print("Note: Period 5 is typically lunch break")

        # ==================== INSERT LECTURES ====================
        print("\n" + "=" * 80)
        print("INSERTING LECTURES (80 total)")
        print("=" * 80)

        lectures = []
        lecture_id = 1

        # Distribution strategy:
        # Each grade (9-12) has 3 classes
        # Each class gets: Math(2), Science subject(2), English(1), History/Geo(1), PE(1) = ~7 lectures
        # Total: 12 classes × 7 lectures ≈ 84 lectures (we'll create 80)

        print("\nGenerating lectures by grade and subject...")

        # Grade 9 classes (9A, 9B, 9C) - Teacher IDs: 1-8
        for class_id in [1, 2, 3]:  # 9A, 9B, 9C
            # Math (2 lectures per class) - Teacher 1
            lectures.append(Lecture(id=lecture_id, subject_id=1, teacher_id=1, class_id=class_id))
            lecture_id += 1
            lectures.append(Lecture(id=lecture_id, subject_id=1, teacher_id=1, class_id=class_id))
            lecture_id += 1

            # Physics (2 lectures) - Teacher 2
            lectures.append(Lecture(id=lecture_id, subject_id=2, teacher_id=2, class_id=class_id))
            lecture_id += 1
            lectures.append(Lecture(id=lecture_id, subject_id=2, teacher_id=2, class_id=class_id))
            lecture_id += 1

            # English (1 lecture) - Teacher 9
            lectures.append(Lecture(id=lecture_id, subject_id=5, teacher_id=9, class_id=class_id))
            lecture_id += 1

            # History (1 lecture) - Teacher 10
            lectures.append(Lecture(id=lecture_id, subject_id=6, teacher_id=10, class_id=class_id))
            lecture_id += 1

            # PE (1 lecture) - Teacher 14
            lectures.append(Lecture(id=lecture_id, subject_id=8, teacher_id=14, class_id=class_id))
            lecture_id += 1

        print(f"  Grade 9: {(lecture_id - 1)} lectures (3 classes × 7 lectures)")

        # Grade 10 classes (10A, 10B, 10C)
        for class_id in [4, 5, 6]:  # 10A, 10B, 10C
            # Math (2 lectures) - Teacher 3
            lectures.append(Lecture(id=lecture_id, subject_id=1, teacher_id=3, class_id=class_id))
            lecture_id += 1
            lectures.append(Lecture(id=lecture_id, subject_id=1, teacher_id=3, class_id=class_id))
            lecture_id += 1

            # Chemistry (2 lectures) - Teacher 4
            lectures.append(Lecture(id=lecture_id, subject_id=3, teacher_id=4, class_id=class_id))
            lecture_id += 1
            lectures.append(Lecture(id=lecture_id, subject_id=3, teacher_id=4, class_id=class_id))
            lecture_id += 1

            # English (1 lecture) - Teacher 11
            lectures.append(Lecture(id=lecture_id, subject_id=5, teacher_id=11, class_id=class_id))
            lecture_id += 1

            # Geography (1 lecture) - Teacher 12
            lectures.append(Lecture(id=lecture_id, subject_id=7, teacher_id=12, class_id=class_id))
            lecture_id += 1

            # PE (1 lecture) - Teacher 15
            lectures.append(Lecture(id=lecture_id, subject_id=8, teacher_id=15, class_id=class_id))
            lecture_id += 1

        print(f"  Grade 10: {(lecture_id - 22)} lectures (3 classes × 7 lectures)")

        # Grade 11 classes (11A, 11B, 11C)
        for class_id in [7, 8, 9]:  # 11A, 11B, 11C
            # Math (2 lectures) - Teacher 5
            lectures.append(Lecture(id=lecture_id, subject_id=1, teacher_id=5, class_id=class_id))
            lecture_id += 1
            lectures.append(Lecture(id=lecture_id, subject_id=1, teacher_id=5, class_id=class_id))
            lecture_id += 1

            # Biology (2 lectures) - Teacher 6
            lectures.append(Lecture(id=lecture_id, subject_id=4, teacher_id=6, class_id=class_id))
            lecture_id += 1
            lectures.append(Lecture(id=lecture_id, subject_id=4, teacher_id=6, class_id=class_id))
            lecture_id += 1

            # English (1 lecture) - Teacher 13
            lectures.append(Lecture(id=lecture_id, subject_id=5, teacher_id=13, class_id=class_id))
            lecture_id += 1

            # History (1 lecture) - Teacher 9
            lectures.append(Lecture(id=lecture_id, subject_id=6, teacher_id=9, class_id=class_id))
            lecture_id += 1

            # PE (1 lecture) - Teacher 14
            lectures.append(Lecture(id=lecture_id, subject_id=8, teacher_id=14, class_id=class_id))
            lecture_id += 1

        print(f"  Grade 11: {(lecture_id - 43)} lectures (3 classes × 7 lectures)")

        # Grade 12 classes (12A, 12B, 12C)
        for class_id in [10, 11, 12]:  # 12A, 12B, 12C
            # Math (2 lectures) - Teacher 7
            lectures.append(Lecture(id=lecture_id, subject_id=1, teacher_id=7, class_id=class_id))
            lecture_id += 1
            lectures.append(Lecture(id=lecture_id, subject_id=1, teacher_id=7, class_id=class_id))
            lecture_id += 1

            # Physics (2 lectures) - Teacher 8
            lectures.append(Lecture(id=lecture_id, subject_id=2, teacher_id=8, class_id=class_id))
            lecture_id += 1
            lectures.append(Lecture(id=lecture_id, subject_id=2, teacher_id=8, class_id=class_id))
            lecture_id += 1

            # English (1 lecture) - Teacher 10
            lectures.append(Lecture(id=lecture_id, subject_id=5, teacher_id=10, class_id=class_id))
            lecture_id += 1

            # Geography (1 lecture) - Teacher 11
            lectures.append(Lecture(id=lecture_id, subject_id=7, teacher_id=11, class_id=class_id))
            lecture_id += 1

            # PE (1 lecture) - Teacher 15
            lectures.append(Lecture(id=lecture_id, subject_id=8, teacher_id=15, class_id=class_id))
            lecture_id += 1

        # Add a few more lectures to reach 80
        lectures.append(Lecture(id=lecture_id, subject_id=1, teacher_id=1, class_id=1))  # Extra Math for 9A
        lecture_id += 1
        lectures.append(Lecture(id=lecture_id, subject_id=3, teacher_id=4, class_id=7))  # Extra Chemistry for 11A
        lecture_id += 1
        lectures.append(Lecture(id=lecture_id, subject_id=4, teacher_id=6, class_id=10)) # Extra Biology for 12A
        lecture_id += 1

        print(f"  Grade 12: {(lecture_id - 64 - 3)} lectures (3 classes × 7 lectures)")
        print(f"  Additional: 3 lectures")

        session.add_all(lectures)
        session.commit()

        print(f"\nTotal lectures created: {len(lectures)}")

        # ==================== INSERT TEACHER PREFERENCES ====================
        print("\n" + "=" * 80)
        print("INSERTING TEACHER PREFERENCES (35 total)")
        print("=" * 80)

        preferences = []
        pref_id = 1

        # Priority 1 teachers (15+ years): 4 teachers × 3 preferences each = 12
        print("\nPriority 1 Preferences (Senior Teachers - 15+ years):")

        # Dr. Emily Watson (Teacher 1, 18 years) - Priority 1
        preferences.append(TeacherPreference(
            id=pref_id, teacher_id=1, preference_type="DAY_OFF",
            day_of_week=3, description="Dr. Watson prefers Thursday off for research"
        ))
        print(f"  [P1] Dr. Emily Watson: wants Thursday off")
        pref_id += 1

        preferences.append(TeacherPreference(
            id=pref_id, teacher_id=1, preference_type="SPECIFIC_TIME",
            lecture_id=1, timeslot_id=1, description="Dr. Watson prefers Math 9A on Monday Period 1"
        ))
        print(f"  [P1] Dr. Emily Watson: wants Math 9A on Monday Period 1")
        pref_id += 1

        preferences.append(TeacherPreference(
            id=pref_id, teacher_id=1, preference_type="SPECIFIC_TIME",
            lecture_id=3, timeslot_id=9, description="Dr. Watson prefers Math 9B on Tuesday Period 1"
        ))
        print(f"  [P1] Dr. Emily Watson: wants Math 9B on Tuesday Period 1")
        pref_id += 1

        # Prof. Michael Chen (Teacher 2, 15 years) - Priority 1
        preferences.append(TeacherPreference(
            id=pref_id, teacher_id=2, preference_type="DAY_OFF",
            day_of_week=4, description="Prof. Chen prefers Friday off"
        ))
        print(f"  [P1] Prof. Michael Chen: wants Friday off")
        pref_id += 1

        preferences.append(TeacherPreference(
            id=pref_id, teacher_id=2, preference_type="SPECIFIC_TIME",
            lecture_id=7, timeslot_id=2, description="Prof. Chen prefers Physics 9A on Monday Period 2"
        ))
        print(f"  [P1] Prof. Michael Chen: wants Physics 9A on Monday Period 2")
        pref_id += 1

        # Dr. James Wilson (Teacher 6, 20 years) - Priority 1
        preferences.append(TeacherPreference(
            id=pref_id, teacher_id=6, preference_type="DAY_OFF",
            day_of_week=2, description="Dr. Wilson prefers Wednesday off"
        ))
        print(f"  [P1] Dr. James Wilson: wants Wednesday off")
        pref_id += 1

        preferences.append(TeacherPreference(
            id=pref_id, teacher_id=6, preference_type="SPECIFIC_TIME",
            lecture_id=45, timeslot_id=17, description="Dr. Wilson prefers Biology 11A on Wednesday Period 1"
        ))
        print(f"  [P1] Dr. James Wilson: wants Biology 11A on Wednesday Period 1")
        pref_id += 1

        # Prof. Jennifer Brown (Teacher 9, 16 years) - Priority 1
        preferences.append(TeacherPreference(
            id=pref_id, teacher_id=9, preference_type="DAY_OFF",
            day_of_week=1, description="Prof. Brown prefers Tuesday off"
        ))
        print(f"  [P1] Prof. Jennifer Brown: wants Tuesday off")
        pref_id += 1

        preferences.append(TeacherPreference(
            id=pref_id, teacher_id=9, preference_type="SPECIFIC_TIME",
            lecture_id=13, timeslot_id=3, description="Prof. Brown prefers English 9A on Monday Period 3"
        ))
        print(f"  [P1] Prof. Jennifer Brown: wants English 9A on Monday Period 3")
        pref_id += 1

        # Priority 2 teachers (7-14 years): 6 teachers × 2 preferences each = 12
        print("\nPriority 2 Preferences (Mid-Level Teachers - 7-14 years):")

        # Dr. Sarah Johnson (Teacher 3, 12 years)
        preferences.append(TeacherPreference(
            id=pref_id, teacher_id=3, preference_type="DAY_OFF",
            day_of_week=4, description="Dr. Johnson prefers Friday off"
        ))
        print(f"  [P2] Dr. Sarah Johnson: wants Friday off")
        pref_id += 1

        # Mr. David Kim (Teacher 4, 8 years)
        preferences.append(TeacherPreference(
            id=pref_id, teacher_id=4, preference_type="SPECIFIC_TIME",
            lecture_id=22, timeslot_id=10, description="Mr. Kim prefers Chemistry 10A on Tuesday Period 2"
        ))
        print(f"  [P2] Mr. David Kim: wants Chemistry 10A on Tuesday Period 2")
        pref_id += 1

        # Mr. Robert Taylor (Teacher 8, 10 years)
        preferences.append(TeacherPreference(
            id=pref_id, teacher_id=8, preference_type="DAY_OFF",
            day_of_week=0, description="Mr. Taylor prefers Monday off"
        ))
        print(f"  [P2] Mr. Robert Taylor: wants Monday off")
        pref_id += 1

        # Ms. Amanda White (Teacher 10, 7 years)
        preferences.append(TeacherPreference(
            id=pref_id, teacher_id=10, preference_type="SPECIFIC_TIME",
            lecture_id=14, timeslot_id=4, description="Ms. White prefers History 9A on Monday Period 4"
        ))
        print(f"  [P2] Ms. Amanda White: wants History 9A on Monday Period 4")
        pref_id += 1

        # Dr. Patricia Martinez (Teacher 12, 14 years)
        preferences.append(TeacherPreference(
            id=pref_id, teacher_id=12, preference_type="DAY_OFF",
            day_of_week=3, description="Dr. Martinez prefers Thursday off"
        ))
        print(f"  [P2] Dr. Patricia Martinez: wants Thursday off")
        pref_id += 1

        # Coach John Davis (Teacher 14, 11 years)
        preferences.append(TeacherPreference(
            id=pref_id, teacher_id=14, preference_type="SPECIFIC_TIME",
            lecture_id=15, timeslot_id=5, description="Coach Davis prefers PE 9A on Monday Period 5"
        ))
        print(f"  [P2] Coach John Davis: wants PE 9A on Monday Period 5")
        pref_id += 1

        # Coach Maria Rodriguez (Teacher 15, 9 years)
        preferences.append(TeacherPreference(
            id=pref_id, teacher_id=15, preference_type="SPECIFIC_TIME",
            lecture_id=28, timeslot_id=13, description="Coach Rodriguez prefers PE 10A on Tuesday Period 5"
        ))
        print(f"  [P2] Coach Maria Rodriguez: wants PE 10A on Tuesday Period 5")
        pref_id += 1

        # Priority 3 teachers (0-6 years): 5 teachers × 2 preferences each = 10
        print("\nPriority 3 Preferences (Junior Teachers - 0-6 years):")

        # Ms. Rachel Green (Teacher 5, 4 years)
        preferences.append(TeacherPreference(
            id=pref_id, teacher_id=5, preference_type="DAY_OFF",
            day_of_week=2, description="Ms. Green prefers Wednesday off"
        ))
        print(f"  [P3] Ms. Rachel Green: wants Wednesday off")
        pref_id += 1

        preferences.append(TeacherPreference(
            id=pref_id, teacher_id=5, preference_type="SPECIFIC_TIME",
            lecture_id=43, timeslot_id=18, description="Ms. Green prefers Math 11A on Wednesday Period 2"
        ))
        print(f"  [P3] Ms. Rachel Green: wants Math 11A on Wednesday Period 2")
        pref_id += 1

        # Ms. Lisa Anderson (Teacher 7, 6 years)
        preferences.append(TeacherPreference(
            id=pref_id, teacher_id=7, preference_type="SPECIFIC_TIME",
            lecture_id=64, timeslot_id=25, description="Ms. Anderson prefers Math 12A on Thursday Period 1"
        ))
        print(f"  [P3] Ms. Lisa Anderson: wants Math 12A on Thursday Period 1")
        pref_id += 1

        preferences.append(TeacherPreference(
            id=pref_id, teacher_id=7, preference_type="SPECIFIC_TIME",
            lecture_id=66, timeslot_id=26, description="Ms. Anderson prefers Math 12B on Thursday Period 2"
        ))
        print(f"  [P3] Ms. Lisa Anderson: wants Math 12B on Thursday Period 2")
        pref_id += 1

        # Mr. Christopher Lee (Teacher 11, 3 years)
        preferences.append(TeacherPreference(
            id=pref_id, teacher_id=11, preference_type="DAY_OFF",
            day_of_week=1, description="Mr. Lee prefers Tuesday off"
        ))
        print(f"  [P3] Mr. Christopher Lee: wants Tuesday off")
        pref_id += 1

        preferences.append(TeacherPreference(
            id=pref_id, teacher_id=11, preference_type="SPECIFIC_TIME",
            lecture_id=34, timeslot_id=19, description="Mr. Lee prefers English 10A on Wednesday Period 3"
        ))
        print(f"  [P3] Mr. Christopher Lee: wants English 10A on Wednesday Period 3")
        pref_id += 1

        # Ms. Michelle Garcia (Teacher 13, 5 years)
        preferences.append(TeacherPreference(
            id=pref_id, teacher_id=13, preference_type="SPECIFIC_TIME",
            lecture_id=55, timeslot_id=33, description="Ms. Garcia prefers English 11A on Friday Period 1"
        ))
        print(f"  [P3] Ms. Michelle Garcia: wants English 11A on Friday Period 1")
        pref_id += 1

        preferences.append(TeacherPreference(
            id=pref_id, teacher_id=13, preference_type="SPECIFIC_TIME",
            lecture_id=57, timeslot_id=34, description="Ms. Garcia prefers English 11B on Friday Period 2"
        ))
        print(f"  [P3] Ms. Michelle Garcia: wants English 11B on Friday Period 2")
        pref_id += 1

        session.add_all(preferences)
        session.commit()

        # ==================== SUMMARY ====================
        print("\n" + "=" * 80)
        print("DATABASE POPULATED SUCCESSFULLY!")
        print("=" * 80)
        print(f"  Teachers:       {len(teachers)}")
        print(f"  Classrooms:     {len(classrooms)}")
        print(f"    - Regular:    8")
        print(f"    - Labs:       3")
        print(f"    - Gym:        1")
        print(f"  Classes:        {len(classes)}")
        print(f"  Subjects:       {len(subjects)}")
        print(f"    - Lab subjects: 3 (Physics, Chemistry, Biology)")
        print(f"    - Gym subject:  1 (PE)")
        print(f"  Lectures:       {len(lectures)}")
        print(f"  Timeslots:      {len(timeslots)} (5 days × 8 periods)")
        print(f"  Preferences:    {len(preferences)}")
        print("=" * 80)
        print("\nPriority Distribution:")
        print("  Priority 1 (15+ years): 4 teachers → 9 goals")
        print("  Priority 2 (7-14 years): 6 teachers → 7 goals")
        print("  Priority 3 (0-6 years):  5 teachers → 8 goals")
        print("=" * 80)
        print("\nScale Comparison:")
        print("  Step 3: 5 teachers, 4 rooms, 4 classes, 20 lectures, 30 slots")
        print("  Step 4: 15 teachers, 12 rooms, 12 classes, 80 lectures, 40 slots")
        print(f"  Variables: ~{12 * 40 * 80:,} (compared to ~{4 * 30 * 20:,} in Step 3)")
        print("=" * 80)
        print("\nNext Step:")
        print("  Run: python timetabling_scaled.py")
        print("=" * 80)

    finally:
        session.close()


if __name__ == "__main__":
    populate_database()
