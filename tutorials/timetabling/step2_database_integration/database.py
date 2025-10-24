"""Database models using SQLAlchemy ORM for course timetabling.

This module demonstrates LumiX's ORM integration using SQLAlchemy declarative models.
Instead of raw SQL queries, we use SQLAlchemy's ORM for type-safe database operations
and seamless integration with LumiX's `from_model()` method.

Key Features:
    - SQLAlchemy declarative models with type safety
    - Automatic table creation from models
    - ORM-based CRUD operations
    - Integration with LumiX via `from_model()`
    - Session management for database transactions

Models:
    - Teacher: Teacher information
    - Classroom: Classroom with capacity
    - SchoolClass: Student class with size
    - Subject: Course subject
    - Lecture: Individual teaching session
    - TimeSlot: Available scheduling slots
    - ScheduleAssignment: Optimized schedule solutions

Example:
    >>> from database import init_database, get_session
    >>> from database import Teacher
    >>>
    >>> engine = init_database("sqlite:///school.db")
    >>> session = get_session(engine)
    >>>
    >>> # Add teacher using ORM
    >>> teacher = Teacher(id=1, name="Dr. Smith")
    >>> session.add(teacher)
    >>> session.commit()
    >>>
    >>> # Query using ORM
    >>> teachers = session.query(Teacher).all()
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

Base = declarative_base()


class Teacher(Base):
    """Teacher ORM model.

    Attributes:
        id: Primary key
        name: Teacher's name
    """
    __tablename__ = 'teachers'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    def __repr__(self):
        return f"<Teacher(id={self.id}, name='{self.name}')>"


class Classroom(Base):
    """Classroom ORM model.

    Attributes:
        id: Primary key
        name: Classroom name/number
        capacity: Maximum student capacity
    """
    __tablename__ = 'classrooms'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    capacity = Column(Integer, nullable=False)

    def __repr__(self):
        return f"<Classroom(id={self.id}, name='{self.name}', capacity={self.capacity})>"


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
    """Subject ORM model.

    Attributes:
        id: Primary key
        name: Subject name (e.g., "Mathematics", "English")
    """
    __tablename__ = 'subjects'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    def __repr__(self):
        return f"<Subject(id={self.id}, name='{self.name}')>"


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
        period: Period number (1-6)
        day_name: Human-readable day name
    """
    __tablename__ = 'timeslots'

    id = Column(Integer, primary_key=True)
    day_of_week = Column(Integer, nullable=False)
    period = Column(Integer, nullable=False)
    day_name = Column(String, nullable=False)

    def __repr__(self):
        return f"<TimeSlot(id={self.id}, day='{self.day_name}', period={self.period})>"


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


def create_cached_class_fits_checker(session: Session):
    """Create a cached checker function for class-classroom compatibility.

    Queries all classes and classrooms once and caches the results for
    efficient repeated lookups during variable creation. This avoids
    redundant database queries when called thousands of times in where_multi().

    Performance: Reduces from O(n) queries to O(1) lookups after initial setup.
    For a typical timetabling problem with 2,400 variable combinations, this
    reduces from 4,800 database queries to just 8 queries (4 classes + 4 classrooms).

    Args:
        session: SQLAlchemy Session

    Returns:
        A checker function with signature (class_id, classroom_id) -> bool

    Example:
        >>> checker = create_cached_class_fits_checker(session)
        >>> fits = checker(class_id=1, classroom_id=2)  # Fast cached lookup
        >>> if fits:
        ...     print("Class fits in classroom")
    """
    # Query all data once upfront
    classes_dict = {c.id: c.size for c in session.query(SchoolClass).all()}
    classrooms_dict = {r.id: r.capacity for r in session.query(Classroom).all()}

    # Return closure with cached data
    def check(class_id: int, classroom_id: int) -> bool:
        """Check if class fits in classroom using cached data."""
        class_size = classes_dict.get(class_id)
        room_capacity = classrooms_dict.get(classroom_id)
        if class_size is not None and room_capacity is not None:
            return class_size <= room_capacity
        return False

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
