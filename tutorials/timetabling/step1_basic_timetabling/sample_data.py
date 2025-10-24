"""Sample data for high school course timetabling example.

This module provides data models and sample data for the basic timetabling
optimization problem. The goal is to assign lectures to timeslots and classrooms
while respecting various constraints.

The timetabling problem involves:
    - Teachers who teach specific subjects to specific classes
    - Classrooms with limited capacity
    - Timeslots organized by day and period
    - Lectures that must be scheduled without conflicts

This is a classic scheduling problem that demonstrates LumiX's multi-dimensional
indexing capabilities.

Example:
    Create a timetabling model::

        assignment = LXVariable[Tuple[Lecture, TimeSlot, Classroom], int]("assignment")
            .binary()
            .indexed_by_product(...)

Notes:
    Each lecture represents one session of a subject taught by a teacher to a class.
    For example, if "Math for Class 9A" occurs 4 times per week, there would be
    4 separate Lecture objects.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class Teacher:
    """Represents a teacher in the school.

    Attributes:
        id: Unique identifier for the teacher.
        name: Teacher's name.

    Example:
        >>> teacher = Teacher(id=1, name="Dr. Smith")
        >>> print(teacher.name)
        Dr. Smith
    """

    id: int
    name: str


@dataclass
class Classroom:
    """Represents a classroom in the school.

    Attributes:
        id: Unique identifier for the classroom.
        name: Classroom name or number.
        capacity: Maximum number of students the classroom can hold.

    Example:
        >>> classroom = Classroom(id=1, name="Room 101", capacity=30)
        >>> print(f"{classroom.name} can hold {classroom.capacity} students")
        Room 101 can hold 30 students
    """

    id: int
    name: str
    capacity: int


@dataclass
class SchoolClass:
    """Represents a class (group of students) in the school.

    Attributes:
        id: Unique identifier for the class.
        name: Class name (e.g., "9A", "10B").
        size: Number of students in the class.

    Example:
        >>> school_class = SchoolClass(id=1, name="9A", size=25)
        >>> print(f"Class {school_class.name} has {school_class.size} students")
        Class 9A has 25 students
    """

    id: int
    name: str
    size: int


@dataclass
class Subject:
    """Represents a subject taught in the school.

    Attributes:
        id: Unique identifier for the subject.
        name: Subject name (e.g., "Mathematics", "English").

    Example:
        >>> subject = Subject(id=1, name="Mathematics")
        >>> print(subject.name)
        Mathematics
    """

    id: int
    name: str


@dataclass
class Lecture:
    """Represents a single lecture session.

    A lecture is a specific teaching session: a teacher teaching a subject
    to a class. If a subject meets multiple times per week, each meeting
    is a separate lecture.

    Attributes:
        id: Unique identifier for the lecture.
        subject_id: ID of the subject being taught.
        teacher_id: ID of the teacher teaching the lecture.
        class_id: ID of the class attending the lecture.

    Example:
        >>> lecture = Lecture(id=1, subject_id=1, teacher_id=1, class_id=1)
        >>> # Represents: Teacher 1 teaching Subject 1 to Class 1
    """

    id: int
    subject_id: int
    teacher_id: int
    class_id: int


@dataclass
class TimeSlot:
    """Represents a time slot in the weekly schedule.

    Attributes:
        id: Unique identifier for the timeslot.
        day_of_week: Day number (0=Monday, 1=Tuesday, ..., 4=Friday).
        period: Period number (1-6, representing class periods in the day).
        day_name: Human-readable day name.

    Example:
        >>> timeslot = TimeSlot(id=1, day_of_week=0, period=1, day_name="Monday")
        >>> print(f"{timeslot.day_name} Period {timeslot.period}")
        Monday Period 1
    """

    id: int
    day_of_week: int  # 0=Monday, 1=Tuesday, ..., 4=Friday
    period: int  # 1, 2, 3, 4, 5, 6
    day_name: str


# Sample Teachers
TEACHERS = [
    Teacher(id=1, name="Dr. Smith"),
    Teacher(id=2, name="Prof. Johnson"),
    Teacher(id=3, name="Ms. Williams"),
    Teacher(id=4, name="Mr. Brown"),
    Teacher(id=5, name="Dr. Davis"),
]

# Sample Classrooms
CLASSROOMS = [
    Classroom(id=1, name="Room 101", capacity=30),
    Classroom(id=2, name="Room 102", capacity=30),
    Classroom(id=3, name="Room 201", capacity=25),
    Classroom(id=4, name="Lab A", capacity=20),
]

# Sample School Classes
CLASSES = [
    SchoolClass(id=1, name="9A", size=25),
    SchoolClass(id=2, name="9B", size=28),
    SchoolClass(id=3, name="10A", size=24),
    SchoolClass(id=4, name="10B", size=26),
]

# Sample Subjects
SUBJECTS = [
    Subject(id=1, name="Mathematics"),
    Subject(id=2, name="English"),
    Subject(id=3, name="Physics"),
    Subject(id=4, name="Chemistry"),
    Subject(id=5, name="History"),
]

# Generate TimeSlots (5 days × 6 periods = 30 timeslots)
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


def generate_timeslots() -> List[TimeSlot]:
    """Generate all timeslots for a school week.

    Creates timeslots for 5 days (Monday-Friday) with 6 periods per day.

    Returns:
        A list of 30 TimeSlot objects.

    Example:
        >>> timeslots = generate_timeslots()
        >>> print(len(timeslots))
        30
        >>> print(timeslots[0])
        TimeSlot(id=1, day_of_week=0, period=1, day_name='Monday')
    """
    timeslots = []
    slot_id = 1
    for day in range(5):  # Monday to Friday
        for period in range(1, 7):  # Periods 1-6
            timeslots.append(
                TimeSlot(
                    id=slot_id,
                    day_of_week=day,
                    period=period,
                    day_name=DAY_NAMES[day],
                )
            )
            slot_id += 1
    return timeslots


TIMESLOTS = generate_timeslots()

# Sample Lectures
# Each lecture represents one session of a subject
# E.g., If Math for 9A meets 4 times a week, there are 4 Lecture objects
LECTURES = [
    # Mathematics lectures (Dr. Smith teaches Math)
    Lecture(id=1, subject_id=1, teacher_id=1, class_id=1),  # Math for 9A
    Lecture(id=2, subject_id=1, teacher_id=1, class_id=1),  # Math for 9A (2nd session)
    Lecture(id=3, subject_id=1, teacher_id=1, class_id=2),  # Math for 9B
    Lecture(id=4, subject_id=1, teacher_id=1, class_id=2),  # Math for 9B (2nd session)
    # English lectures (Prof. Johnson teaches English)
    Lecture(id=5, subject_id=2, teacher_id=2, class_id=1),  # English for 9A
    Lecture(id=6, subject_id=2, teacher_id=2, class_id=2),  # English for 9B
    Lecture(id=7, subject_id=2, teacher_id=2, class_id=3),  # English for 10A
    # Physics lectures (Ms. Williams teaches Physics)
    Lecture(id=8, subject_id=3, teacher_id=3, class_id=3),  # Physics for 10A
    Lecture(id=9, subject_id=3, teacher_id=3, class_id=3),  # Physics for 10A (2nd session)
    Lecture(id=10, subject_id=3, teacher_id=3, class_id=4),  # Physics for 10B
    Lecture(id=11, subject_id=3, teacher_id=3, class_id=4),  # Physics for 10B (2nd session)
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


def get_teacher_name(teacher_id: int) -> str:
    """Get teacher name by ID.

    Args:
        teacher_id: The teacher's ID.

    Returns:
        The teacher's name, or "Unknown" if not found.

    Example:
        >>> get_teacher_name(1)
        'Dr. Smith'
    """
    for teacher in TEACHERS:
        if teacher.id == teacher_id:
            return teacher.name
    return "Unknown"


def get_subject_name(subject_id: int) -> str:
    """Get subject name by ID.

    Args:
        subject_id: The subject's ID.

    Returns:
        The subject's name, or "Unknown" if not found.

    Example:
        >>> get_subject_name(1)
        'Mathematics'
    """
    for subject in SUBJECTS:
        if subject.id == subject_id:
            return subject.name
    return "Unknown"


def get_class_name(class_id: int) -> str:
    """Get class name by ID.

    Args:
        class_id: The class's ID.

    Returns:
        The class's name, or "Unknown" if not found.

    Example:
        >>> get_class_name(1)
        '9A'
    """
    for school_class in CLASSES:
        if school_class.id == class_id:
            return school_class.name
    return "Unknown"


def get_classroom_name(classroom_id: int) -> str:
    """Get classroom name by ID.

    Args:
        classroom_id: The classroom's ID.

    Returns:
        The classroom's name, or "Unknown" if not found.

    Example:
        >>> get_classroom_name(1)
        'Room 101'
    """
    for classroom in CLASSROOMS:
        if classroom.id == classroom_id:
            return classroom.name
    return "Unknown"


def check_class_fits_classroom(class_id: int, classroom_id: int) -> bool:
    """Check if a class can fit in a classroom.

    Args:
        class_id: The class's ID.
        classroom_id: The classroom's ID.

    Returns:
        True if the class size is less than or equal to classroom capacity.

    Example:
        >>> check_class_fits_classroom(1, 1)  # 9A (25 students) in Room 101 (30 capacity)
        True
    """
    school_class = next((c for c in CLASSES if c.id == class_id), None)
    classroom = next((r for r in CLASSROOMS if r.id == classroom_id), None)

    if school_class and classroom:
        return school_class.size <= classroom.capacity
    return False
