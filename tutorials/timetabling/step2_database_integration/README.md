# Step 2: Database Integration

## Overview

This is the second step in the High School Course Timetabling tutorial. It extends Step 1 by integrating a **SQLite database** for data storage and solution persistence.

The optimization model is identical to Step 1, but:
- **Input data** is loaded from a database instead of Python lists
- **Solutions** are saved to the database for future reference
- **Data management** is separated from optimization logic

## What's New in Step 2

### Key Changes from Step 1

1. **Data Storage**: All entities (teachers, classrooms, lectures, etc.) stored in SQLite database
2. **Data Loading**: Model reads data from database tables instead of Python lists
3. **Solution Persistence**: Optimization results saved to `schedule_assignments` table
4. **Database Operations**: CRUD operations for all entities
5. **Data Consistency**: Database constraints ensure referential integrity

### Why Use a Database?

- **Persistence**: Data survives between program runs
- **Scalability**: Handle larger datasets efficiently
- **Multi-user**: Multiple users can access the same data
- **Integration**: Easy to connect with existing school management systems
- **History**: Track multiple schedule versions over time
- **Querying**: Use SQL to analyze schedules and patterns

## Database Schema

### Entity Tables

**teachers**
```sql
CREATE TABLE teachers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
)
```

**classrooms**
```sql
CREATE TABLE classrooms (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    capacity INTEGER NOT NULL
)
```

**classes** (school classes, not classrooms)
```sql
CREATE TABLE classes (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    size INTEGER NOT NULL  -- number of students
)
```

**subjects**
```sql
CREATE TABLE subjects (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
)
```

**lectures**
```sql
CREATE TABLE lectures (
    id INTEGER PRIMARY KEY,
    subject_id INTEGER NOT NULL,
    teacher_id INTEGER NOT NULL,
    class_id INTEGER NOT NULL,
    FOREIGN KEY (subject_id) REFERENCES subjects(id),
    FOREIGN KEY (teacher_id) REFERENCES teachers(id),
    FOREIGN KEY (class_id) REFERENCES classes(id)
)
```

**timeslots**
```sql
CREATE TABLE timeslots (
    id INTEGER PRIMARY KEY,
    day_of_week INTEGER NOT NULL,  -- 0=Monday, 4=Friday
    period INTEGER NOT NULL,         -- 1-6
    day_name TEXT NOT NULL
)
```

### Solution Table

**schedule_assignments**
```sql
CREATE TABLE schedule_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lecture_id INTEGER NOT NULL,
    timeslot_id INTEGER NOT NULL,
    classroom_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lecture_id) REFERENCES lectures(id),
    FOREIGN KEY (timeslot_id) REFERENCES timeslots(id),
    FOREIGN KEY (classroom_id) REFERENCES classrooms(id)
)
```

This table stores the optimized schedule: which lecture is assigned to which timeslot and classroom.

## Files in This Example

- **`database.py`**: SQLite database operations (schema, CRUD, queries)
- **`sample_data.py`**: Script to populate database with sample data
- **`timetabling_db.py`**: Main optimization model using database
- **`README.md`**: This documentation file
- **`.gitignore`**: Exclude database files from version control
- **`school.db`**: SQLite database (created at runtime, not in git)

## Running the Example

### Step 1: Populate the Database

First, create and populate the database with sample data:

```bash
cd tutorials/timetabling/step2_database_integration
python sample_data.py
```

**Output:**
```
Creating database schema...
Clearing existing data...
Inserting teachers...
Inserting classrooms...
Inserting school classes...
Inserting subjects...
Inserting timeslots...
Inserting lectures...

============================================================
Database populated successfully!
============================================================
  Teachers:   5
  Classrooms: 4
  Classes:    4
  Subjects:   5
  Lectures:   20
  Timeslots:  30 (5 days × 6 periods)
============================================================
```

### Step 2: Run the Optimization

Now run the timetabling optimization:

```bash
python timetabling_db.py
```

The program will:
1. Load data from the database
2. Build the optimization model
3. Solve the timetabling problem
4. Display teacher and class timetables
5. Save the solution back to the database

## Expected Output

```
================================================================================
LumiX Tutorial: High School Course Timetabling - Step 2
================================================================================

This example demonstrates:
  ✓ Loading optimization data from SQLite database
  ✓ Building LumiX models from database entities
  ✓ Saving solutions back to database
  ✓ Persistent data storage and retrieval

Loading data from database...
  Loaded 5 teachers
  Loaded 4 classrooms
  Loaded 4 classes
  Loaded 20 lectures
  Loaded 30 timeslots

Building course timetabling model...
  Adding lecture coverage constraints...
  Adding classroom conflict constraints...
  Adding teacher conflict constraints...
  Adding class conflict constraints...

Model built successfully!
  Constraints: 620 total

Solving with ortools...

================================================================================
TIMETABLING SOLUTION
================================================================================
Status: optimal

[Teacher and Class Timetables displayed here...]

Saving solution to database...
  Saved 20 schedule assignments

================================================================================
Tutorial Step 2 Complete!
================================================================================

What changed from Step 1:
  → Data loaded from SQLite database (not Python lists)
  → Solution saved to database for persistence
  → Same optimization model, different data source

Next Steps:
  → Step 3: Add teacher preferences with goal programming
```

## Database Operations

### TimetableDatabase Class

The `TimetableDatabase` class provides convenient methods for all database operations:

**Initialization:**
```python
from database import TimetableDatabase

db = TimetableDatabase("school.db")
db.create_schema()  # Create tables if they don't exist
```

**Insertion:**
```python
from database import Teacher, Classroom

db.insert_teacher(Teacher(id=1, name="Dr. Smith"))
db.insert_classroom(Classroom(id=1, name="Room 101", capacity=30))
```

**Retrieval:**
```python
teachers = db.get_all_teachers()
classrooms = db.get_all_classrooms()
lectures = db.get_all_lectures()
```

**Solution Storage:**
```python
# Clear previous solution
db.clear_schedule_assignments()

# Save new solution
db.save_schedule_assignment(lecture_id=1, timeslot_id=5, classroom_id=2)

# Retrieve saved solution
assignments = db.get_schedule_assignments()
```

**Helper Methods:**
```python
teacher_name = db.get_teacher_name(teacher_id=1)
subject_name = db.get_subject_name(subject_id=2)
can_fit = db.check_class_fits_classroom(class_id=1, classroom_id=3)
```

**Cleanup:**
```python
db.close()  # Always close the connection when done
```

## SQL Query Examples

You can also query the database directly using SQL:

### View All Lectures with Details

```sql
SELECT
    l.id,
    s.name AS subject,
    t.name AS teacher,
    c.name AS class
FROM lectures l
JOIN subjects s ON l.subject_id = s.id
JOIN teachers t ON l.teacher_id = t.id
JOIN classes c ON l.class_id = c.id
ORDER BY l.id;
```

### View the Optimized Schedule

```sql
SELECT
    sa.id,
    s.name AS subject,
    t.name AS teacher,
    c.name AS class,
    ts.day_name || ' Period ' || ts.period AS timeslot,
    r.name AS classroom
FROM schedule_assignments sa
JOIN lectures l ON sa.lecture_id = l.id
JOIN subjects s ON l.subject_id = s.id
JOIN teachers t ON l.teacher_id = t.id
JOIN classes c ON l.class_id = c.id
JOIN timeslots ts ON sa.timeslot_id = ts.id
JOIN classrooms r ON sa.classroom_id = r.id
ORDER BY ts.day_of_week, ts.period, r.id;
```

### Count Lectures Per Teacher

```sql
SELECT
    t.name AS teacher,
    COUNT(*) AS lecture_count
FROM lectures l
JOIN teachers t ON l.teacher_id = t.id
GROUP BY t.name
ORDER BY lecture_count DESC;
```

### Find Available Timeslots for a Classroom

```sql
SELECT ts.*
FROM timeslots ts
WHERE ts.id NOT IN (
    SELECT timeslot_id
    FROM schedule_assignments
    WHERE classroom_id = 1
)
ORDER BY ts.day_of_week, ts.period;
```

## Integration with LumiX

### Loading Data from Database

The key pattern for integrating databases with LumiX:

```python
# 1. Load data from database
db = TimetableDatabase("school.db")
lectures = db.get_all_lectures()
timeslots = db.get_all_timeslots()
classrooms = db.get_all_classrooms()

# 2. Build LumiX variables using database entities
assignment = (
    LXVariable[Tuple[Lecture, TimeSlot, Classroom], int]("assignment")
    .binary()
    .indexed_by_product(
        LXIndexDimension(Lecture, lambda lec: lec.id).from_data(lectures),
        LXIndexDimension(TimeSlot, lambda ts: ts.id).from_data(timeslots),
        LXIndexDimension(Classroom, lambda room: room.id).from_data(classrooms),
    )
    .where_multi(
        lambda lec, ts, room: db.check_class_fits_classroom(lec.class_id, room.id)
    )
)

# 3. Build model, solve, and save results
model = build_model(...)
solution = optimizer.solve(model)

# 4. Save solution back to database
for (lec_id, ts_id, room_id), value in solution.variables["assignment"].items():
    if value > 0.5:
        db.save_schedule_assignment(lec_id, ts_id, room_id)
```

### Benefits of This Pattern

1. **Separation of Concerns**: Data management separate from optimization logic
2. **Testability**: Easy to test with different datasets
3. **Scalability**: Database handles large datasets efficiently
4. **Reusability**: Same model can work with different databases
5. **Collaboration**: Multiple developers can work with same data

## Key Learnings

### 1. Database as Data Source

LumiX works seamlessly with database-loaded data. The dataclasses from Step 1 are identical, just populated from a database instead of lists.

### 2. Solution Persistence

Saving solutions to a database enables:
- Comparing multiple schedule versions
- Tracking changes over time
- Auditing and accountability
- Integration with other systems (e.g., student portals)

### 3. Foreign Key Constraints

Database foreign keys ensure data integrity:
- Can't create a lecture for non-existent teacher
- Can't assign to non-existent timeslot
- Referential integrity maintained automatically

### 4. Schema Design for Optimization

Good database schema for optimization problems:
- Entity tables for each model type
- Junction/relationship tables for associations
- Solution tables separate from input tables
- Timestamps for historical tracking

## Common Patterns

### Pattern 1: Load, Solve, Save

```python
db = TimetableDatabase(db_path)
try:
    # Load
    data = db.get_all_xyz()

    # Solve
    model = build_model(data)
    solution = solve(model)

    # Save
    save_solution(solution, db)
finally:
    db.close()
```

### Pattern 2: Database-Backed Helper Functions

```python
# Use database for validation checks
.where_multi(
    lambda lec, ts, room: db.check_class_fits_classroom(lec.class_id, room.id)
)
```

### Pattern 3: Timestamped Solutions

```python
CREATE TABLE schedule_assignments (
    ...
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

This allows tracking when each solution was generated.

## Extensions and Variations

### 1. Multiple Schedule Versions

Add a `schedule_version` table to store multiple optimized schedules:

```sql
CREATE TABLE schedule_versions (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Modify schedule_assignments to reference version
ALTER TABLE schedule_assignments ADD COLUMN version_id INTEGER;
```

### 2. Historical Tracking

Track all changes to lectures, teachers, etc.:

```sql
CREATE TABLE lecture_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lecture_id INTEGER,
    change_type TEXT,  -- 'INSERT', 'UPDATE', 'DELETE'
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    old_data TEXT,  -- JSON
    new_data TEXT   -- JSON
);
```

### 3. User Authentication

Add user management for multi-user scenarios:

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL  -- 'admin', 'scheduler', 'viewer'
);
```

## Troubleshooting

### Database Not Found Error

```
FileNotFoundError: [Errno 2] No such file or directory: 'school.db'
```

**Solution:** Run `python sample_data.py` first to create and populate the database.

### Empty Database

```
❌ Database is empty! Please run sample_data.py first
```

**Solution:** The database exists but has no data. Run `python sample_data.py`.

### Foreign Key Constraint Error

```
sqlite3.IntegrityError: FOREIGN KEY constraint failed
```

**Solution:** Ensure you insert entities in the correct order:
1. Teachers, Classrooms, Classes, Subjects (no dependencies)
2. Lectures (depends on teachers, classes, subjects)
3. TimeSlots (no dependencies)
4. Schedule Assignments (depends on lectures, timeslots, classrooms)

## Next Steps

After completing Step 2, proceed to:

- **Step 3**: Add teacher preferences and goal programming with priority levels

## See Also

- **Step 1**: Basic timetabling with Python lists
- **Example 11 (Goal Programming)**: Multi-objective optimization foundation
- **SQLite Documentation**: https://www.sqlite.org/docs.html

---

**Tutorial Step 2 Complete!**

You've learned how to integrate LumiX with a SQLite database for persistent data storage. Now move on to Step 3 to add teacher preferences using goal programming.
