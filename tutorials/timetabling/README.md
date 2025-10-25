# High School Course Timetabling Tutorial

A comprehensive 4-step tutorial demonstrating how to build a complete course timetabling solution using LumiX, progressing from basic optimization to production-ready large-scale systems with goal programming and specialized room constraints.

## 📚 Full Documentation

**For comprehensive documentation with code examples, mathematical formulations, and detailed walkthroughs, see:**

📖 **[Complete Tutorial Documentation](../../docs/source/tutorials/timetabling/index.rst)** (Sphinx/HTML)

This README provides a quick overview. The full Sphinx documentation includes:
- Step-by-step code walkthroughs with line-by-line explanations
- Mathematical formulations with LaTeX equations
- Performance benchmarks and optimization tips
- Troubleshooting guides and common pitfalls
- API cross-references and related documentation

## Overview

This tutorial teaches you how to solve a real-world high school course timetabling problem through progressive complexity:

- **Step 1**: Basic timetabling with Python lists and multi-model indexing
- **Step 2**: Database integration with SQLite and SQLAlchemy ORM
- **Step 3**: Goal programming with teacher preferences and priorities
- **Step 4**: Large-scale optimization with room types and interactive HTML reports (production-ready)

By the end of this tutorial, you'll understand:
- Multi-dimensional indexing with 3D variables
- Database-driven optimization models with ORM integration
- Multi-objective optimization with goal programming
- Scaling to production-ready problem sizes
- Room type constraints for specialized facilities
- Performance optimization patterns
- Interactive HTML report generation with modern dashboards

## Problem Description

**Scenario**: A high school needs to create a weekly timetable that assigns lectures (teacher-subject-class combinations) to specific timeslots and classrooms.

**Constraints**:
- Each lecture must be scheduled exactly once
- No classroom can host two lectures simultaneously
- Teachers can't teach two lectures at the same time
- Classes can't attend two lectures at the same time
- Classroom capacity must accommodate class size

**Data**:
- 5 Teachers
- 4 Classrooms
- 4 School Classes (9A, 9B, 10A, 10B)
- 5 Subjects (Math, English, Physics, Chemistry, History)
- 20 Lectures (individual teaching sessions)
- 30 Timeslots (5 days × 6 periods)

## Tutorial Structure

### Step 1: Basic Timetabling 📚

**Focus**: Core optimization model with multi-dimensional indexing

**What you'll learn**:
- Creating 3D indexed variables: `assignment[Lecture, TimeSlot, Classroom]`
- Building complex scheduling constraints
- Filtering infeasible combinations
- Generating tabular timetable outputs

**Key LumiX features**:
- `LXVariable` with 3D multi-model indexing
- `.indexed_by_product()` for cartesian products
- `.where_multi()` for filtering
- `add_multi_term()` with dimensional filtering

**Files**:
- `sample_data.py`: Data classes and sample data
- `timetabling.py`: Optimization model and solution display
- `README.md`: Detailed documentation

[📖 Go to Step 1](step1_basic_timetabling/)

---

### Step 2: Database Integration 💾

**Focus**: Persistent data storage with SQLite

**What you'll learn**:
- Designing database schemas for optimization problems
- Loading LumiX models from database entities
- Saving solutions to database
- Separating data from model logic

**Key features**:
- SQLite database with 7 tables
- CRUD operations for all entities
- Solution persistence
- Database-backed helper functions

**Files**:
- `database.py`: SQLite schema and operations
- `sample_data.py`: Database population script
- `timetabling_db.py`: Database-driven optimization
- `README.md`: Database documentation
- `.gitignore`: Exclude database files

[📖 Go to Step 2](step2_database_integration/)

---

### Step 3: Goal Programming with Teacher Preferences 🎯

**Focus**: Multi-objective optimization with priorities

**What you'll learn**:
- Expressing teacher preferences as soft constraints
- Assigning priorities based on seniority
- Using LumiX's goal programming feature
- Analyzing goal satisfaction

**Key features**:
- Teacher preferences (DAY_OFF, SPECIFIC_TIME)
- Priority calculation from work years
- Weighted goal programming
- Comprehensive satisfaction analysis

**Files**:
- `database.py`: Extended schema with preferences
- `sample_data.py`: Teachers with seniority and preferences
- `timetabling_goals.py`: Goal programming model
- `README.md`: Goal programming documentation

[📖 Go to Step 3](step3_goal_programming/)

---

### Step 4: Large-Scale Optimization with Room Types 🚀

**Focus**: Production-ready scale with specialized room constraints

**What you'll learn**:
- Scaling to realistic problem sizes (16x more variables)
- Room type constraints (REGULAR, LAB, GYM)
- Performance optimization with cached checkers
- Handling complex compatibility rules
- Production-ready patterns
- Generating interactive HTML reports with modern dashboards

**Key features**:
- 15 teachers across 3 departments
- 12 classrooms with room types (8 regular, 3 labs, 1 gym)
- 12 classes across 4 grades
- 80 lectures with realistic distribution
- 40 timeslots (8 periods per day)
- Room type requirements (lab subjects need labs, PE needs gym)
- Enhanced performance with caching (~7,000x speedup)
- Interactive HTML5 + CSS report with teacher/class/room timetables

**Files**:
- `database.py`: Extended schema with room types and subject requirements
- `sample_data.py`: Large-scale realistic data generation
- `timetabling_scaled.py`: Production-scale optimization
- `report_generator.py`: Interactive HTML report generation
- `README.md`: Scaling and performance documentation

[📖 Go to Step 4](step4_scaled_up/)

---

## Quick Start

### Prerequisites

```bash
# Install LumiX with OR-Tools solver
pip install lumix
pip install ortools
```

### Step 1: Basic Timetabling

```bash
cd tutorials/timetabling/step1_basic_timetabling
python timetabling.py
```

### Step 2: Database Integration

```bash
cd tutorials/timetabling/step2_database_integration

# First, populate the database
python sample_data.py

# Then run the optimization
python timetabling_db.py
```

### Step 3: Goal Programming

```bash
cd tutorials/timetabling/step3_goal_programming

# First, populate the database with preferences
python sample_data.py

# Then run the goal programming optimization
python timetabling_goals.py
```

### Step 4: Large-Scale Optimization

```bash
cd tutorials/timetabling/step4_scaled_up

# First, populate the database with large-scale data
python sample_data.py

# Then run the production-scale optimization (10-30 seconds)
python timetabling_scaled.py
```

## Learning Path

### For Beginners

Start with **Step 1** to learn:
- Basic LumiX modeling
- Multi-dimensional indexing
- Constraint formulation
- Solution interpretation

### For Intermediate Users

Skip to **Step 2** if you already know basics and want to learn:
- Database integration patterns
- Data persistence
- Scalable data management

### For Advanced Users

Jump to **Step 3** for:
- Goal programming
- Multi-objective optimization
- Priority-based scheduling
- Trade-off analysis

Or go straight to **Step 4** for:
- Production-scale optimization
- Performance optimization patterns
- Complex constraint systems
- Real-world deployment strategies

## Key Concepts Demonstrated

### 1. Multi-Dimensional Indexing

Variables indexed by three models simultaneously:

```python
assignment = LXVariable[Tuple[Lecture, TimeSlot, Classroom], int]("assignment")
    .binary()
    .indexed_by_product(
        LXIndexDimension(Lecture, lambda lec: lec.id).from_data(lectures),
        LXIndexDimension(TimeSlot, lambda ts: ts.id).from_data(timeslots),
        LXIndexDimension(Classroom, lambda room: room.id).from_data(classrooms),
    )
```

### 2. Database-Driven Models

Load data from database instead of hardcoded lists:

```python
db = TimetableDatabase("school.db")
teachers = db.get_all_teachers()
lectures = db.get_all_lectures()
# Use these in model building
```

### 3. Goal Programming

Mix hard constraints with soft goals:

```python
# Hard constraint (must satisfy)
model.add_constraint(
    LXConstraint("lecture_coverage")
    .expression(expr)
    .eq()
    .rhs(1)
)

# Soft goal (minimize violation)
model.add_constraint(
    LXConstraint("teacher_preference")
    .expression(expr)
    .le()
    .rhs(0)
    .as_goal(priority=1, weight=1.0)  # Mark as goal
)
```

## Feature Comparison

| Feature | Step 1 | Step 2 | Step 3 | Step 4 |
|---------|--------|--------|--------|--------|
| **Basic Model** | ✓ | ✓ | ✓ | ✓ |
| **3D Indexing** | ✓ | ✓ | ✓ | ✓ |
| **Hard Constraints** | ✓ | ✓ | ✓ | ✓ |
| **Python Lists** | ✓ | | | |
| **SQLite Database** | | ✓ | ✓ | ✓ |
| **Solution Persistence** | | ✓ | ✓ | ✓ |
| **Teacher Seniority** | | | ✓ | ✓ |
| **Teacher Preferences** | | | ✓ | ✓ |
| **Goal Programming** | | | ✓ | ✓ |
| **Priority Levels** | | | ✓ | ✓ |
| **Satisfaction Analysis** | | | ✓ | ✓ |
| **Large-Scale Data** | | | | ✓ |
| **Room Types** | | | | ✓ |
| **Room Type Constraints** | | | | ✓ |
| **Performance Caching** | | | | ✓ |
| **Interactive HTML Report** | | | | ✓ |

## Real-World Applications

This tutorial's patterns apply to many scheduling problems:

### Education
- **University course scheduling**: Larger scale, more complex constraints
- **Exam timetabling**: Resource constraints, student conflicts
- **Training session planning**: Instructor availability, room requirements

### Healthcare
- **Nurse rostering**: Shift preferences, workload balancing
- **Operating room scheduling**: Surgeon availability, equipment constraints
- **Clinic appointment scheduling**: Doctor preferences, patient priorities

### Business
- **Employee shift scheduling**: Availability, workload fairness
- **Meeting room booking**: Participant conflicts, resource limits
- **Conference scheduling**: Speaker preferences, room capacity

### Transportation
- **Bus driver scheduling**: Route assignments, work hour limits
- **Airline crew rostering**: Regulations, preferences, experience levels

## Extension Ideas

After completing the tutorial, try these extensions:

### Easy Extensions
1. **Add more data**: Increase teachers, classes, and lectures
2. **Change timeslots**: Add more periods or different day structures
3. **Modify priorities**: Use different seniority rules
4. **Add preference types**: Break times, consecutive periods, etc.

### Intermediate Extensions
1. **Student preferences**: Classes prefer morning vs. afternoon
2. **Room preferences**: Certain subjects prefer specific rooms
3. **Consecutive lectures**: Some lectures must be back-to-back
4. **Balanced workload**: Distribute lectures evenly across days

### Advanced Extensions
1. **Multiple buildings**: Add travel time between buildings
2. **Specialized equipment**: Labs, projectors, computers
3. **Web interface**: Flask/Django app for schedule management
4. **Automated updates**: Daily schedule adjustments
5. **Multi-week planning**: Semester or year-long schedules
6. **Enhanced HTML reports**: Add PDF export, email distribution, or embed charts
7. **Real-time editing**: Allow users to manually adjust schedules in the HTML interface

## Tips for Success

### Understanding the Code

1. **Start with Step 1**: Even if you want database integration or goal programming, understand the basics first
2. **Read the READMEs**: Each step has comprehensive documentation
3. **Run the examples**: See the actual output to understand what's happening
4. **Modify gradually**: Change one thing at a time to see the effect

### Debugging

1. **Check hard constraints first**: If infeasible, look at hard constraints
2. **Simplify**: Reduce data size to understand the problem
3. **Print intermediate results**: Add debug prints to understand data flow
4. **Verify database**: Use SQL queries to inspect data

### Performance

1. **Start small**: Test with fewer lectures and timeslots
2. **Scale gradually**: Increase size once working correctly
3. **Use appropriate solver**: CP-SAT often better for scheduling
4. **Profile bottlenecks**: Identify slow constraint generation

## Common Pitfalls

### Pitfall 1: Forgetting prepare_goal_programming()

**Error**: Goal programming doesn't work, all constraints treated as hard

**Solution**:
```python
model.set_goal_mode("weighted")
model.prepare_goal_programming()  # Don't forget this!
solution = optimizer.solve(model)
```

### Pitfall 2: Database Not Populated

**Error**: `Database is empty!` or `No teachers found`

**Solution**: Run `python sample_data.py` first to populate the database

### Pitfall 3: Variable Capture in Lambdas

**Error**: Wrong values in where clauses due to late binding

**Solution**: Capture variables by value:
```python
# Wrong
where=lambda lec, ts: lec.id == lecture.id  # Captures reference

# Correct
where=lambda lec, ts, current=lecture: lec.id == current.id  # Captures value
```

### Pitfall 4: Inconsistent Data

**Error**: Some lectures reference non-existent teachers or classes

**Solution**: Use foreign key constraints in database to enforce consistency

## Help and Support

### Documentation

- [LumiX Documentation](https://lumix.readthedocs.io)
- [Step 1 README](step1_basic_timetabling/README.md)
- [Step 2 README](step2_database_integration/README.md)
- [Step 3 README](step3_goal_programming/README.md)
- [Step 4 README](step4_scaled_up/README.md)

### Examples

- LumiX Example 02: Driver Scheduling (2D indexing)
- LumiX Example 11: Goal Programming basics
- LumiX Example 05: CP-SAT for scheduling

### Community

- [LumiX GitHub Issues](https://github.com/lumix/lumix/issues)
- [LumiX Discussions](https://github.com/lumix/lumix/discussions)

## Summary

This tutorial has shown you:

- **Step 1**: Built a basic timetabling model with 3D multi-model indexing
- **Step 2**: Integrated SQLite database for persistent data storage
- **Step 3**: Added teacher preferences using goal programming with priorities
- **Step 4**: Built large-scale production-ready model with room type constraints and interactive HTML reports

You've learned:
- Multi-dimensional variable indexing
- Complex constraint formulation
- Database integration patterns
- Multi-objective optimization
- Priority-based decision making
- Solution analysis and interpretation
- Scaling to production sizes
- Performance optimization with caching
- Interactive visualization with modern HTML dashboards

These skills transfer to many real-world optimization problems. Happy optimizing!

---

**Tutorial Version**: 1.0
**LumiX Version**: Compatible with LumiX 0.1.0+
**Last Updated**: 2025-01-24
