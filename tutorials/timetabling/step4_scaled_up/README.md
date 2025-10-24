# Step 4: Large-Scale Timetabling with Room Type Constraints

## Overview

This is Step 4 in the High School Course Timetabling tutorial. It demonstrates LumiX's ability to handle **realistic large-scale problems efficiently** while introducing **room type constraints** for specialized classrooms.

This step shows that LumiX can scale from toy problems (Step 1-3) to production-ready sizes without changing the modeling approach.

## What's New in Step 4

### 1. Realistic Problem Scale (3x Step 3)

| Metric | Step 3 | Step 4 | Multiplier |
|--------|--------|--------|------------|
| Teachers | 5 | 15 | 3x |
| Classrooms | 4 | 12 | 3x |
| Classes | 4 | 12 | 3x |
| Lectures | 20 | 80 | 4x |
| Timeslots | 30 | 40 | 1.3x |
| Variables | ~2,400 | ~38,400 | 16x |
| Constraints | ~150 | ~600 | 4x |
| Preferences | 7 | 35 | 5x |

**Key Point**: Despite 16x more variables, LumiX solves this efficiently with proper caching.

### 2. Room Type Constraints (NEW)

Schools have different types of rooms with specific requirements:

- **REGULAR** rooms: Standard classrooms for most subjects
- **LAB** rooms: Science laboratories for Chemistry, Physics, Biology
- **GYM**: Gymnasium for Physical Education

**Constraint**: Each subject can only be assigned to compatible room types.

### 3. Multi-Grade, Multi-Department Structure

More realistic school organization:

- **4 Grades**: 9, 10, 11, 12
- **3 Classes per grade**: A, B, C sections
- **3 Departments**:
  - Math & Science (8 teachers)
  - Humanities (5 teachers)
  - Physical Education (2 teachers)

### 4. Enhanced Performance

- **Cached compatibility checker**: Combines capacity and room type checks
- **Reduced database queries**: From ~190,000 to ~27 queries
- **Fast solve time**: 10-30 seconds for realistic-sized problem

## Room Type System

### Database Schema

```python
# Classroom with room type
Classroom(
    id=1,
    name="Chemistry Lab",
    capacity=26,
    room_type="LAB"  # NEW in Step 4
)

# Subject with lab requirement
Subject(
    id=3,
    name="Chemistry",
    requires_lab=True  # NEW in Step 4
)
```

### Compatibility Rules

```python
def check_room_type_compatible(subject_id, classroom_id):
    """
    Rules:
    - Lab subjects (Chemistry, Physics, Biology) → Must use LAB rooms
    - PE → Must use GYM
    - Other subjects → Can use REGULAR or LAB rooms (not GYM)
    """
```

### Example Data

**Classrooms (12 total)**:
- 8 Regular rooms: Room 101, 102, 201, 202, 301, 302, 401, 402
- 3 Labs: Chemistry Lab, Physics Lab, Biology Lab
- 1 Gym: Main Gym

**Subjects (8 total)**:
- Regular: Mathematics, English, History, Geography
- Lab-required: Physics, Chemistry, Biology
- Gym-required: Physical Education

## Cached Compatibility Checker

The key performance optimization in Step 4:

```python
def create_cached_compatibility_checker(session):
    """
    Combines capacity and room type checking into one cached function.

    Performance Impact:
    - Without caching: 192,000 database queries
    - With caching: 27 queries (12 classes + 12 rooms + 8 subjects)
    - Speedup: ~7,000x faster
    """
    # Query all data once upfront
    classes_dict = {c.id: c.size for c in session.query(SchoolClass).all()}
    classrooms_dict = {r.id: (r.capacity, r.room_type)
                       for r in session.query(Classroom).all()}
    subjects_dict = {s.id: (s.requires_lab, s.id)
                     for s in session.query(Subject).all()}

    # Return closure with cached data
    def check(lecture, classroom_id):
        # Check capacity: class_size <= room_capacity
        # Check room type: subject requirements match room type
        # ... (see database.py for full implementation)

    return check
```

**Usage in model**:
```python
compatibility_checker = create_cached_compatibility_checker(session)

assignment = (
    LXVariable[...](...)
    .where_multi(lambda lec, ts, room:
        compatibility_checker(lec, room.id)  # Fast cached lookup
    )
)
```

## Problem Structure

### Teachers (15 total)

| Department | Count | Seniority Distribution |
|------------|-------|------------------------|
| Math & Science | 8 | 3 senior, 2 mid-level, 3 junior |
| Humanities | 5 | 2 senior, 2 mid-level, 1 junior |
| Physical Education | 2 | 0 senior, 2 mid-level, 0 junior |

### Lectures (80 total)

**Distribution per class** (~7 lectures):
- Mathematics: 2 lectures/week
- Science subject: 2 lectures/week (Physics, Chemistry, or Biology)
- English: 1 lecture/week
- History/Geography: 1 lecture/week
- PE: 1 lecture/week

**Total**: 12 classes × 7 lectures ≈ 80 lectures

### Timeslots (40 total)

- **5 days**: Monday - Friday
- **8 periods per day**: Periods 1-8
- **Note**: Period 5 is typically lunch break

### Teacher Preferences (35 total)

Distributed by priority:
- **Priority 1** (15+ years): 9 goals from 4 senior teachers
- **Priority 2** (7-14 years): 7 goals from 6 mid-level teachers
- **Priority 3** (0-6 years): 8 goals from 5 junior teachers

Types:
- **DAY_OFF**: Teacher wants specific day completely free (60%)
- **SPECIFIC_TIME**: Teacher wants lecture at specific time (40%)

## Running the Example

### Prerequisites

```bash
# Install LumiX with OR-Tools
pip install lumix ortools

# Optional: Install SQLAlchemy if not already installed
pip install sqlalchemy
```

### Step 1: Populate Database

```bash
cd tutorials/timetabling/step4_scaled_up
python sample_data.py
```

**Output**:
```
===============================================================================
STEP 4: LARGE-SCALE TIMETABLING DATA GENERATION
===============================================================================

Initializing database...
Clearing existing data...

===============================================================================
INSERTING TEACHERS (15 total)
===============================================================================
  Dr. Emily Watson              - 18 years → Priority 1
  Prof. Michael Chen            - 15 years → Priority 1
  ...
```

### Step 2: Run Optimization

```bash
python timetabling_scaled.py
```

**Expected solve time**: 10-30 seconds (depending on hardware)

## Key Code Patterns

### 1. Room Type Filtering in Variables

```python
assignment = (
    LXVariable[Tuple[Lecture, TimeSlot, Classroom], int]("assignment")
    .binary()
    .indexed_by_product(
        LXIndexDimension(Lecture, lambda lec: lec.id).from_model(session),
        LXIndexDimension(TimeSlot, lambda ts: ts.id).from_model(session),
        LXIndexDimension(Classroom, lambda room: room.id).from_model(session),
    )
    # NEW: Combined capacity + room type filtering
    .where_multi(lambda lec, ts, room:
        compatibility_checker(lec, room.id)
    )
)
```

### 2. Same Goal Programming (from Step 3)

```python
# DAY_OFF goal
model.add_constraint(
    LXConstraint(f"pref_{pref.id}_day_off")
    .expression(expr)
    .le()
    .rhs(0)
    .as_goal(priority=priority, weight=1.0)
)

# SPECIFIC_TIME goal
model.add_constraint(
    LXConstraint(f"pref_{pref.id}_specific_time")
    .expression(expr)
    .ge()
    .rhs(1)
    .as_goal(priority=priority, weight=1.0)
)
```

### 3. Efficient Constraint Generation

```python
# Use list comprehensions to filter lectures upfront
teacher_lectures = [lec for lec in lectures if lec.teacher_id == teacher.id]

# Then use filtered list in where clause
where=lambda lec, ts, room, t_lectures=teacher_lectures:
    lec.id in [tl.id for tl in t_lectures]
```

## Performance Benchmarks

Measured on typical laptop (8GB RAM, 4-core CPU):

| Phase | Time | Notes |
|-------|------|-------|
| Variable creation | ~2-3s | Including room type filtering |
| Hard constraints | ~4-6s | 600+ constraints |
| Soft constraints | ~1-2s | 35 goal constraints |
| Model build | ~8-10s | Total preparation |
| Solve | ~10-30s | OR-Tools CP-SAT |
| **Total** | **~20-40s** | End-to-end |

**Key Performance Factors**:
1. ✅ Cached compatibility checker (7,000x speedup)
2. ✅ Efficient where_multi filtering
3. ✅ Batch constraint generation
4. ✅ OR-Tools CP-SAT solver optimization

## Solution Quality

Typical results:

### Hard Constraints
- ✅ **100% satisfied** (always)
- All lectures scheduled exactly once
- No room, teacher, or class conflicts
- All room type requirements met

### Soft Constraints (Goals)

**By Priority**:
- Priority 1: 85-95% satisfaction (senior teachers)
- Priority 2: 70-85% satisfaction (mid-level)
- Priority 3: 60-75% satisfaction (junior teachers)

**Overall**: 75-85% of preferences satisfied

**Why not 100%?**: Some preferences conflict with each other or are infeasible given hard constraints. Goal programming finds the best compromise.

## Scaling Guidelines

Want to adjust the problem size? Here's how:

### Make it Smaller (for testing)

```python
# In sample_data.py, reduce:
- Grades: 2 instead of 4 (e.g., only 9-10)
- Classes per grade: 2 instead of 3 (e.g., only A, B)
- Lectures per class: 5 instead of 7
- Periods per day: 6 instead of 8

Result: ~40 lectures, ~24 timeslots, ~5 teachers
Solve time: <10 seconds
```

### Make it Larger (more realistic)

```python
# In sample_data.py, increase:
- Classes per grade: 4 instead of 3 (add D section)
- Lectures per class: 9 instead of 7 (more subjects)
- Periods per day: 9 instead of 8
- More teacher preferences

Result: ~140 lectures, ~45 timeslots, ~20 teachers
Solve time: 30-60 seconds
```

### Scale to University Size

```python
# Major changes needed:
- 100+ courses
- 50+ instructors
- 30+ rooms
- Multiple buildings (add travel time constraints)
- Larger enrollment (100-500 students per course)

Result: ~300 lectures, ~50 timeslots, ~50 instructors
Solve time: 1-5 minutes
Recommendation: Consider CP-SAT with time limit
```

## Common Issues and Solutions

### Issue 1: Solve Time Too Long (>2 minutes)

**Causes**:
- Too many variables after filtering
- Inefficient constraint generation
- Conflicting preferences

**Solutions**:
```python
# 1. Verify caching is working
print(f"Variables after filtering: {len(assignment.indices)}")
# Should be much less than lectures × timeslots × classrooms

# 2. Reduce preference count temporarily
# Comment out some preferences in sample_data.py

# 3. Add solver time limit
optimizer = LXOptimizer().use_solver(solver_to_use)
# Add time limit if supported by solver
```

### Issue 2: Infeasible Solution

**Causes**:
- Not enough LAB rooms for lab subjects
- Not enough GYM for PE classes
- Too many preferences conflict with hard constraints

**Solutions**:
```python
# 1. Check room type distribution
classrooms = session.query(Classroom).all()
print(f"Regular: {sum(1 for r in classrooms if r.room_type == 'REGULAR')}")
print(f"Lab: {sum(1 for r in classrooms if r.room_type == 'LAB')}")

# 2. Count lectures needing labs
lectures_needing_lab = session.query(Lecture).join(Subject).filter(
    Subject.requires_lab == True
).count()
print(f"Lab lectures: {lectures_needing_lab}")
print(f"Lab capacity: {lab_count * timeslots_count}")

# 3. Reduce conflicting preferences
# Remove preferences that are impossible to satisfy
```

### Issue 3: Low Goal Satisfaction (<50%)

**Causes**:
- Too many preferences relative to schedule flexibility
- Preferences conflict with each other
- Junior teacher preferences fighting for same slots

**Solutions**:
```python
# 1. Analyze conflicts
# Check if multiple teachers want same day off

# 2. Adjust preference counts
# In sample_data.py, reduce preferences per teacher from 3 to 2

# 3. Review preference realism
# Are SPECIFIC_TIME preferences too restrictive?
```

## Comparison with Previous Steps

### Feature Comparison

| Feature | Step 1 | Step 2 | Step 3 | Step 4 |
|---------|--------|--------|--------|--------|
| Basic Model | ✓ | ✓ | ✓ | ✓ |
| 3D Indexing | ✓ | ✓ | ✓ | ✓ |
| Hard Constraints | ✓ | ✓ | ✓ | ✓ |
| Python Lists | ✓ | | | |
| SQLAlchemy ORM | | ✓ | ✓ | ✓ |
| from_model() | | ✓ | ✓ | ✓ |
| Goal Programming | | | ✓ | ✓ |
| Teacher Seniority | | | ✓ | ✓ |
| **Room Types** | | | | ✓ |
| **Realistic Scale** | | | | ✓ |
| **Cached Checker** | | | | ✓ |

### Learning Progression

- **Step 1**: Learn basic LumiX modeling
- **Step 2**: Add database persistence
- **Step 3**: Add multi-objective optimization
- **Step 4**: Scale to production-ready size ← **You are here**

## Extension Ideas

After completing Step 4, try these extensions:

### Easy Extensions (1-2 hours)

1. **Add more preference types**:
   - `NO_EARLY_MORNING`: No lectures in period 1
   - `NO_LATE_AFTERNOON`: No lectures in period 8
   - `CONSECUTIVE_SLOTS`: Teacher wants no gaps

2. **Room preference soft constraints**:
   - Teachers prefer specific rooms
   - Minimize room changes for teachers

3. **Workload balancing**:
   - Minimize variance in lectures per day for each teacher

### Intermediate Extensions (1-2 days)

1. **Block periods** (double periods):
   - Some lectures need 2 consecutive periods
   - Add BlockPeriod table linking timeslots
   - Constraint: If assigned to slot N, must assign to slot N+1

2. **Multiple buildings**:
   - Add building field to Classroom
   - Add travel time between buildings
   - Constraint: Minimum gap between lectures in different buildings

3. **Student electives**:
   - Students choose elective subjects
   - Track student enrollments
   - Add student conflict constraints

### Advanced Extensions (1 week+)

1. **Multi-week planning**:
   - Some lectures happen biweekly
   - Different schedules for Week A and Week B
   - Constraint: Fair distribution across weeks

2. **Curriculum constraints**:
   - Prerequisites (Algebra II before Calculus)
   - Co-requisites (Lab must be same day as Lecture)
   - Balanced grade-level distribution

3. **Web interface**:
   - Flask/Django app for data entry
   - Interactive timetable display
   - Drag-and-drop manual adjustments
   - Re-optimization with locked assignments

## Key Takeaways

After completing Step 4, you should understand:

1. **Scalability**: LumiX handles realistic-sized problems efficiently with proper patterns
2. **Room Types**: Specialized resource constraints are straightforward to model
3. **Performance**: Caching is crucial when generating thousands of variables
4. **Goal Programming**: Scales well - can handle 100+ soft constraints
5. **Production Ready**: This size (80 lectures, 15 teachers) is suitable for small-to-medium schools

## Next Steps

### Apply to Your Domain

The patterns learned here apply to many scheduling problems:

- **University Course Scheduling**: Scale up to 300+ courses
- **Employee Shift Scheduling**: Add shift types, labor rules
- **Conference Scheduling**: Add speaker availability, session tracks
- **Operating Room Scheduling**: Add surgeon skills, equipment requirements

### Optimize Further

- Experiment with different solvers (Gurobi, CPLEX)
- Add more sophisticated goal weights
- Implement solution repair (fix some assignments, re-optimize)
- Add stochastic elements (demand uncertainty)

### Productionize

- Add data validation and error handling
- Create REST API for optimization service
- Implement solution comparison and archiving
- Add user authentication and permissions

---

**Tutorial Version**: 1.0
**Compatible with**: LumiX 0.1.0+
**Last Updated**: 2025-01-24
