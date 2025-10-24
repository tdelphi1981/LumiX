"""Database models using SQLAlchemy ORM for large-scale course timetabling with room types.

This module extends Step 3 by adding room type constraints for realistic scheduling.
Schools have different types of rooms (regular classrooms, labs, gym) and subjects
have different requirements (Chemistry needs a lab, PE needs gym).

Key Features:
    - SQLAlchemy declarative models with type safety
    - Room types (REGULAR, LAB, GYM) for classrooms
    - Subject requirements (requires_lab) for lab-based courses
    - Teacher preferences for goal programming (DAY_OFF, SPECIFIC_TIME)
    - Teacher seniority (work_years) for priority calculation
    - Automatic table creation from models
    - ORM-based CRUD operations
    - Integration with LumiX via `from_model()`
    - Session management for database transactions

Models:
    - Teacher: Teacher information with work_years for seniority
    - Classroom: Classroom with capacity and room_type (NEW in Step 4)
    - SchoolClass: Student class with size
    - Subject: Course subject with requires_lab flag (NEW in Step 4)
    - Lecture: Individual teaching session
    - TimeSlot: Available scheduling slots
    - TeacherPreference: Teacher scheduling preferences
    - ScheduleAssignment: Optimized schedule solutions

Room Types:
    - REGULAR: Standard classroom for most subjects
    - LAB: Science laboratory for Chemistry, Physics, Biology
    - GYM: Gymnasium for Physical Education

Example:
    >>> from database import init_database, get_session
    >>> from database import Classroom, Subject
    >>>
    >>> engine = init_database("sqlite:///school.db")
    >>> session = get_session(engine)
    >>>
    >>> # Add classroom with type using ORM
    >>> classroom = Classroom(id=1, name="Lab A", capacity=25, room_type="LAB")
    >>> session.add(classroom)
    >>> session.commit()
    >>>
    >>> # Add subject requiring lab
    >>> subject = Subject(id=1, name="Chemistry", requires_lab=True)
    >>> session.add(subject)
    >>> session.commit()
    >>>
    >>> # Check room type compatibility
    >>> compatible = check_room_type_compatible(session, subject.id, classroom.id)
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    create_engine,
    CheckConstraint,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

Base = declarative_base()


class Teacher(Base):
    """Teacher ORM model with seniority information.

    Attributes:
        id: Primary key
        name: Teacher's name
        work_years: Years of service (used for priority calculation)
    """
    __tablename__ = 'teachers'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    work_years = Column(Integer, nullable=False, default=0)

    def __repr__(self):
        return f"<Teacher(id={self.id}, name='{self.name}', work_years={self.work_years})>"


class Classroom(Base):
    """Classroom ORM model with room type (NEW in Step 4).

    Room types enable realistic constraints where certain subjects require
    specific types of rooms (e.g., Chemistry needs a lab, PE needs gym).

    Attributes:
        id: Primary key
        name: Classroom name/number
        capacity: Maximum student capacity
        room_type: Type of room ('REGULAR', 'LAB', 'GYM')
    """
    __tablename__ = 'classrooms'
    __table_args__ = (
        CheckConstraint(
            "room_type IN ('REGULAR', 'LAB', 'GYM')",
            name='check_room_type'
        ),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    capacity = Column(Integer, nullable=False)
    room_type = Column(String, nullable=False, default='REGULAR')

    def __repr__(self):
        return f"<Classroom(id={self.id}, name='{self.name}', capacity={self.capacity}, type='{self.room_type}')>"


class SchoolClass(Base):
    """School class ORM model (group of students).

    Attributes:
        id: Primary key
        name: Class name (e.g., "9A", "10B")
        size: Number of students in the class
    """
    __tablename__ = 'classes'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    size = Column(Integer, nullable=False)

    def __repr__(self):
        return f"<SchoolClass(id={self.id}, name='{self.name}', size={self.size})>"


class Subject(Base):
    """Subject ORM model with lab requirement (NEW in Step 4).

    Subjects can now specify if they require a lab. This creates a constraint
    where lab-requiring subjects can only be scheduled in LAB rooms.

    Attributes:
        id: Primary key
        name: Subject name (e.g., "Mathematics", "Chemistry")
        requires_lab: True if subject needs a laboratory
    """
    __tablename__ = 'subjects'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    requires_lab = Column(Boolean, nullable=False, default=False)

    def __repr__(self):
        lab_str = " (requires lab)" if self.requires_lab else ""
        return f"<Subject(id={self.id}, name='{self.name}'{lab_str})>"


class Lecture(Base):
    """Lecture ORM model (individual teaching session).

    Represents one instance of a teacher teaching a subject to a class.
    If a subject meets multiple times per week, each meeting is a separate Lecture.

    Attributes:
        id: Primary key
        subject_id: Foreign key to Subject
        teacher_id: Foreign key to Teacher
        class_id: Foreign key to SchoolClass
    """
    __tablename__ = 'lectures'

    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    teacher_id = Column(Integer, ForeignKey('teachers.id'), nullable=False)
    class_id = Column(Integer, ForeignKey('classes.id'), nullable=False)

    def __repr__(self):
        return f"<Lecture(id={self.id}, subject_id={self.subject_id}, teacher_id={self.teacher_id}, class_id={self.class_id})>"


class TimeSlot(Base):
    """TimeSlot ORM model (available scheduling slot).

    Attributes:
        id: Primary key
        day_of_week: Day number (0=Monday, 1=Tuesday, ..., 4=Friday)
        period: Period number (1-8 in Step 4)
        day_name: Human-readable day name
    """
    __tablename__ = 'timeslots'

    id = Column(Integer, primary_key=True)
    day_of_week = Column(Integer, nullable=False)
    period = Column(Integer, nullable=False)
    day_name = Column(String, nullable=False)

    def __repr__(self):
        return f"<TimeSlot(id={self.id}, day='{self.day_name}', period={self.period})>"


class TeacherPreference(Base):
    """Teacher preference ORM model for goal programming.

    Stores teacher scheduling preferences that are converted to soft constraints (goals).

    Preference Types:
        - DAY_OFF: Teacher wants a specific day completely free
        - SPECIFIC_TIME: Teacher wants a specific lecture at a specific timeslot

    Attributes:
        id: Primary key
        teacher_id: Foreign key to Teacher
        preference_type: Type of preference ('DAY_OFF' or 'SPECIFIC_TIME')
        day_of_week: Day number (0-4) for DAY_OFF preferences
        lecture_id: Foreign key to Lecture for SPECIFIC_TIME preferences
        timeslot_id: Foreign key to TimeSlot for SPECIFIC_TIME preferences
        description: Human-readable description of the preference

    Example:
        >>> # DAY_OFF preference
        >>> pref1 = TeacherPreference(
        ...     id=1, teacher_id=1, preference_type="DAY_OFF",
        ...     day_of_week=1, description="Dr. Smith wants Tuesday off"
        ... )
        >>>
        >>> # SPECIFIC_TIME preference
        >>> pref2 = TeacherPreference(
        ...     id=2, teacher_id=1, preference_type="SPECIFIC_TIME",
        ...     lecture_id=1, timeslot_id=1,
        ...     description="Dr. Smith wants Math 9A on Monday Period 1"
        ... )
    """
    __tablename__ = 'teacher_preferences'
    __table_args__ = (
        CheckConstraint(
            "preference_type IN ('DAY_OFF', 'SPECIFIC_TIME')",
            name='check_preference_type'
        ),
    )

    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey('teachers.id'), nullable=False)
    preference_type = Column(String, nullable=False)
    day_of_week = Column(Integer, nullable=True)  # For DAY_OFF
    lecture_id = Column(Integer, ForeignKey('lectures.id'), nullable=True)  # For SPECIFIC_TIME
    timeslot_id = Column(Integer, ForeignKey('timeslots.id'), nullable=True)  # For SPECIFIC_TIME
    description = Column(String, nullable=True)

    def __repr__(self):
        return f"<TeacherPreference(id={self.id}, teacher_id={self.teacher_id}, type='{self.preference_type}')>"


class ScheduleAssignment(Base):
    """Schedule assignment ORM model (optimization solution).

    Stores the result of the optimization: which lecture is assigned
    to which timeslot in which classroom.

    Attributes:
        id: Primary key
        lecture_id: Foreign key to Lecture
        timeslot_id: Foreign key to TimeSlot
        classroom_id: Foreign key to Classroom
    """
    __tablename__ = 'schedule_assignments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    lecture_id = Column(Integer, ForeignKey('lectures.id'), nullable=False)
    timeslot_id = Column(Integer, ForeignKey('timeslots.id'), nullable=False)
    classroom_id = Column(Integer, ForeignKey('classrooms.id'), nullable=False)

    def __repr__(self):
        return f"<ScheduleAssignment(lecture_id={self.lecture_id}, timeslot_id={self.timeslot_id}, classroom_id={self.classroom_id})>"


def init_database(database_url: str = "sqlite:///school.db"):
    """Initialize database and create all tables.

    Args:
        database_url: SQLAlchemy database URL

    Returns:
        SQLAlchemy Engine instance

    Example:
        >>> engine = init_database("sqlite:///school.db")
        >>> # Tables are now created
    """
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine) -> Session:
    """Create a new database session.

    Args:
        engine: SQLAlchemy Engine instance

    Returns:
        SQLAlchemy Session for database operations

    Example:
        >>> engine = init_database()
        >>> session = get_session(engine)
        >>> teachers = session.query(Teacher).all()
        >>> session.close()
    """
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def clear_all_data(session: Session):
    """Clear all data from all tables.

    Useful for resetting the database before inserting new sample data.

    Args:
        session: SQLAlchemy Session

    Example:
        >>> clear_all_data(session)
        >>> session.commit()
    """
    session.query(ScheduleAssignment).delete()
    session.query(TeacherPreference).delete()
    session.query(Lecture).delete()
    session.query(TimeSlot).delete()
    session.query(Subject).delete()
    session.query(SchoolClass).delete()
    session.query(Classroom).delete()
    session.query(Teacher).delete()
    session.commit()


def check_class_fits_classroom(session: Session, class_id: int, classroom_id: int) -> bool:
    """Check if a class can fit in a classroom.

    Args:
        session: SQLAlchemy Session
        class_id: SchoolClass ID
        classroom_id: Classroom ID

    Returns:
        True if class size <= classroom capacity

    Example:
        >>> fits = check_class_fits_classroom(session, class_id=1, classroom_id=2)
        >>> if fits:
        ...     print("Class fits in classroom")
    """
    school_class = session.query(SchoolClass).filter_by(id=class_id).first()
    classroom = session.query(Classroom).filter_by(id=classroom_id).first()

    if school_class and classroom:
        return school_class.size <= classroom.capacity
    return False


def check_room_type_compatible(session: Session, subject_id: int, classroom_id: int) -> bool:
    """Check if a subject can be taught in a classroom based on room type (NEW in Step 4).

    Room Type Compatibility Rules:
        - Subjects requiring lab → Must use LAB rooms
        - PE subjects (id=8) → Must use GYM
        - Other subjects → Can use REGULAR or LAB rooms

    Args:
        session: SQLAlchemy Session
        subject_id: Subject ID
        classroom_id: Classroom ID

    Returns:
        True if subject can be taught in the classroom

    Example:
        >>> # Chemistry (requires_lab=True) → Lab A (room_type=LAB)
        >>> compatible = check_room_type_compatible(session, subject_id=3, classroom_id=10)
        >>> print(compatible)  # True
        >>>
        >>> # Chemistry → Room 101 (room_type=REGULAR)
        >>> compatible = check_room_type_compatible(session, subject_id=3, classroom_id=1)
        >>> print(compatible)  # False
    """
    subject = session.query(Subject).filter_by(id=subject_id).first()
    classroom = session.query(Classroom).filter_by(id=classroom_id).first()

    if not subject or not classroom:
        return False

    # PE (id=8) requires GYM
    if subject.id == 8:
        return classroom.room_type == 'GYM'

    # Lab-requiring subjects need LAB rooms
    if subject.requires_lab:
        return classroom.room_type == 'LAB'

    # Other subjects can use REGULAR or LAB rooms (but not GYM)
    return classroom.room_type in ('REGULAR', 'LAB')


def create_cached_compatibility_checker(session: Session):
    """Create a cached checker function for both capacity and room type compatibility (NEW in Step 4).

    Combines capacity checking and room type checking into a single cached function.
    Queries all classes, classrooms, subjects, and lectures once and caches the results for
    efficient repeated lookups during variable creation.

    Performance: For a large timetabling problem with 96,000 variable combinations,
    this reduces from 192,000 database queries to just 27 queries
    (12 classes + 12 classrooms + 8 subjects + 87 lectures).

    Args:
        session: SQLAlchemy Session

    Returns:
        A checker function with signature (lecture_id, classroom_id) -> bool

    Example:
        >>> checker = create_cached_compatibility_checker(session)
        >>> compatible = checker(lecture_id=1, classroom_id=10)  # Fast cached lookup
        >>> if compatible:
        ...     print("Lecture can be assigned to this classroom")
    """
    # Query all data once upfront
    classes_dict = {c.id: c.size for c in session.query(SchoolClass).all()}
    classrooms_dict = {r.id: (r.capacity, r.room_type) for r in session.query(Classroom).all()}
    subjects_dict = {s.id: (s.requires_lab, s.name) for s in session.query(Subject).all()}
    # Cache lecture data: lecture_id -> (class_id, subject_id)
    lectures_dict = {l.id: (l.class_id, l.subject_id) for l in session.query(Lecture).all()}

    # Return closure with cached data
    def check(lecture_id: int, classroom_id: int) -> bool:
        """Check if lecture can be assigned to classroom using cached data."""
        # Get cached values
        lecture_info = lectures_dict.get(lecture_id)
        room_info = classrooms_dict.get(classroom_id)

        if lecture_info is None or room_info is None:
            return False

        class_id, subject_id = lecture_info
        class_size = classes_dict.get(class_id)
        subject_info = subjects_dict.get(subject_id)
        room_capacity, room_type = room_info

        if class_size is None or subject_info is None:
            return False

        requires_lab, subject_name = subject_info

        # Check capacity
        if class_size > room_capacity:
            return False

        # Check room type compatibility
        # PE requires GYM (check by name since ID might vary)
        if subject_name == "Physical Education":
            return room_type == 'GYM'

        # Lab-requiring subjects need LAB rooms
        if requires_lab:
            return room_type == 'LAB'

        # Other subjects can use REGULAR or LAB rooms (but not GYM)
        return room_type in ('REGULAR', 'LAB')

    return check


def get_teacher_name(session: Session, teacher_id: int) -> str:
    """Get teacher name by ID."""
    teacher = session.query(Teacher).filter_by(id=teacher_id).first()
    return teacher.name if teacher else "Unknown"


def get_subject_name(session: Session, subject_id: int) -> str:
    """Get subject name by ID."""
    subject = session.query(Subject).filter_by(id=subject_id).first()
    return subject.name if subject else "Unknown"


def get_class_name(session: Session, class_id: int) -> str:
    """Get class name by ID."""
    school_class = session.query(SchoolClass).filter_by(id=class_id).first()
    return school_class.name if school_class else "Unknown"


def get_classroom_name(session: Session, classroom_id: int) -> str:
    """Get classroom name by ID."""
    classroom = session.query(Classroom).filter_by(id=classroom_id).first()
    return classroom.name if classroom else "Unknown"


def calculate_priority_from_work_years(work_years: int) -> int:
    """Calculate goal programming priority from teacher work years.

    Priority scheme:
        - 15+ years → Priority 1 (highest)
        - 7-14 years → Priority 2
        - 0-6 years → Priority 3 (lowest)

    Args:
        work_years: Number of years the teacher has worked.

    Returns:
        Priority level (1, 2, or 3).

    Example:
        >>> priority = calculate_priority_from_work_years(15)
        >>> print(priority)  # 1 (senior teacher)
    """
    if work_years >= 15:
        return 1  # Senior teachers
    elif work_years >= 7:
        return 2  # Mid-level teachers
    else:
        return 3  # Junior teachers
