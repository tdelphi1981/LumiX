# Step 1: Basic Course Timetabling

## Overview

This is the first step in the High School Course Timetabling tutorial. It demonstrates how to build a basic timetabling optimization model using LumiX with **3D multi-model indexing**.

The goal is to assign lectures (teacher-subject-class combinations) to timeslots and classrooms while respecting scheduling constraints.

## Problem Description

A high school needs to create a weekly timetable for all classes. The schedule must:

1. **Assign each lecture exactly once** to a timeslot and classroom
2. **Avoid classroom conflicts** - only one lecture per classroom per timeslot
3. **Avoid teacher conflicts** - teachers can't teach two lectures simultaneously
4. **Avoid class conflicts** - classes can't attend two lectures at the same time
5. **Respect classroom capacity** - class size must fit in the assigned classroom

### Problem Data

- **5 Teachers**: Dr. Smith, Prof. Johnson, Ms. Williams, Mr. Brown, Dr. Davis
- **4 Classrooms**: Room 101 (30), Room 102 (30), Room 201 (25), Lab A (20)
- **4 Classes**: 9A (25 students), 9B (28 students), 10A (24 students), 10B (26 students)
- **5 Subjects**: Mathematics, English, Physics, Chemistry, History
- **20 Lectures**: Individual teaching sessions (e.g., "Dr. Smith teaches Math to Class 9A")
- **30 Timeslots**: 5 days × 6 periods per day (Monday-Friday, Periods 1-6)

### Real-World Context

This type of problem appears in:
- High school and university course scheduling
- Training session planning
- Conference scheduling
- Resource allocation with time and space constraints
- Employee shift scheduling with location assignments

## Mathematical Formulation

### Decision Variables

```
assignment[l, t, r] ∈ {0, 1} for each (lecture l, timeslot t, classroom r) triplet
```

Where:
- `l` ∈ Lectures
- `t` ∈ TimeSlots
- `r` ∈ Classrooms
- `assignment[l, t, r] = 1` if lecture l is assigned to timeslot t in classroom r
- `assignment[l, t, r] = 0` otherwise

### Objective Function

This is a **feasibility problem** - the goal is to find any valid schedule that satisfies all constraints. There is no optimization objective (e.g., minimizing costs or maximizing preferences).

### Constraints

**1. Lecture Coverage** - Each lecture must be assigned exactly once:
```
∑∑ assignment[l, t, r] = 1    for each lecture l (sum over all timeslots t and classrooms r)
```

**2. Classroom Capacity** - Class must fit in assigned classroom:
```
assignment[l, t, r] = 0    if size(class of lecture l) > capacity(classroom r)
```

**3. No Classroom Conflicts** - Maximum one lecture per classroom per timeslot:
```
∑ assignment[l, t, r] ≤ 1    for each timeslot t and classroom r (sum over all lectures l)
```

**4. No Teacher Conflicts** - Teacher can't teach multiple lectures simultaneously:
```
∑ assignment[l, t, r] ≤ 1    for each teacher and timeslot t
                              (sum over all lectures l taught by that teacher, all classrooms r)
```

**5. No Class Conflicts** - Class can't attend multiple lectures at the same time:
```
∑ assignment[l, t, r] ≤ 1    for each class and timeslot t
                              (sum over all lectures l for that class, all classrooms r)
```

## Key LumiX Concepts

### 1. Three-Dimensional Multi-Model Indexing

Variables indexed by **tuples of three models**:

```python
# Traditional approach (other libraries)
assignment = {}
for i, lecture in enumerate(lectures):
    for j, timeslot in enumerate(timeslots):
        for k, classroom in enumerate(classrooms):
            assignment[i, j, k] = model.add_var()
# Access: assignment[0, 5, 2] - which lecture? which time? which room? Lost context!

# LumiX approach - THE KEY FEATURE!
assignment = LXVariable[Tuple[Lecture, TimeSlot, Classroom], int]("assignment")
    .binary()
    .indexed_by_product(
        LXIndexDimension(Lecture, lambda lec: lec.id).from_data(LECTURES),
        LXIndexDimension(TimeSlot, lambda ts: ts.id).from_data(TIMESLOTS),
        LXIndexDimension(Classroom, lambda room: room.id).from_data(CLASSROOMS)
    )
# Access: solution.variables["assignment"][(lecture.id, timeslot.id, classroom.id)]
# IDE knows the structure! Type-safe! Full context preserved!
```

### 2. Cartesian Product with Three Dimensions

`indexed_by_product()` creates variables for every combination of Lecture × TimeSlot × Classroom:

```python
.indexed_by_product(
    LXIndexDimension(Lecture, lambda lec: lec.id).from_data(LECTURES),
    LXIndexDimension(TimeSlot, lambda ts: ts.id).from_data(TIMESLOTS),
    LXIndexDimension(Classroom, lambda room: room.id).from_data(CLASSROOMS)
)
# Creates: 20 lectures × 30 timeslots × 4 classrooms = 2,400 binary variables
```

### 3. Filtering with where_multi()

Filter out infeasible combinations based on relationships between models:

```python
.where_multi(
    lambda lec, ts, room: check_class_fits_classroom(lec.class_id, room.id)
)
# Only create variables where the class fits in the classroom
```

### 4. Multi-Dimensional Summation

Sum over specific dimensions using filters:

```python
# Sum over all timeslots and classrooms for a specific lecture
lecture_assigned = LXLinearExpression().add_multi_term(
    assignment,
    coeff=lambda lec, ts, room: 1.0,
    where=lambda lec, ts, room, current_lecture=lecture: lec.id == current_lecture.id
)

# Sum over all lectures for a specific timeslot and classroom
room_occupied = LXLinearExpression().add_multi_term(
    assignment,
    coeff=lambda lec, ts, room: 1.0,
    where=lambda lec, ts, room, current_ts=timeslot, current_room=classroom:
        ts.id == current_ts.id and room.id == current_room.id
)
```

## Running the Example

### Prerequisites

Install LumiX and OR-Tools:

```bash
pip install lumix
pip install ortools
```

### Execute

```bash
cd tutorials/timetabling/step1_basic_timetabling
python timetabling.py
```

## Expected Output

The program will display:

1. **Model Building Information**:
   - Number of variables created
   - Number of constraints added
   - Problem size summary

2. **Solution Status**:
   - Whether a feasible solution was found
   - Solution quality

3. **Teacher Timetables** (one for each teacher):
   - Weekly schedule showing subject, class, and classroom
   - Organized by day (columns) and period (rows)

4. **Class Timetables** (one for each class):
   - Weekly schedule showing subject, teacher, and classroom
   - Organized by day (columns) and period (rows)

### Example Timetable Output

```
================================================================================
Timetable for Dr. Smith
================================================================================

Period   Monday               Tuesday              Wednesday            Thursday             Friday
------------------------------------------------------------------------------------------------------------
1        Mathematics          Mathematics                               Mathematics
         9A                   10A                                       9B
         Room 101             Room 102                                  Room 101

2                                                  Mathematics                               Mathematics
                                                   10B                                       9A
                                                   Room 102                                  Room 101
...
```

## Files in This Example

- **`sample_data.py`**: Data models (Teacher, Classroom, SchoolClass, Lecture, TimeSlot) and sample data
- **`timetabling.py`**: Main optimization model, solver, and timetable display
- **`README.md`**: This documentation file

## Key Learnings

### 1. Multi-Dimensional Problem Representation

The 3D indexing naturally represents the timetabling decision:
- **What** (Lecture) is scheduled
- **When** (TimeSlot) it occurs
- **Where** (Classroom) it takes place

Traditional approaches use nested loops and numerical indices, losing this semantic meaning.

### 2. Constraint Complexity

Timetabling involves multiple types of constraints that sum over different dimensions:
- Lecture coverage: Sum over time and space for each lecture
- Room conflicts: Sum over lectures for each time-space pair
- Teacher conflicts: Sum over lectures (filtered by teacher) for each time
- Class conflicts: Sum over lectures (filtered by class) for each time

LumiX's `add_multi_term()` with `where` filters makes these constraints readable and maintainable.

### 3. Feasibility vs. Optimization

This is a **constraint satisfaction problem** (CSP). The goal is to find any valid schedule, not to optimize an objective function. In Steps 2 and 3, we'll add optimization objectives.

## Common Patterns Demonstrated

### Pattern 1: 3D Multi-Model Variable

```python
decision = LXVariable[Tuple[ModelA, ModelB, ModelC], type]("name")
    .indexed_by_product(
        LXIndexDimension(ModelA, key_func).from_data(DATA_A),
        LXIndexDimension(ModelB, key_func).from_data(DATA_B),
        LXIndexDimension(ModelC, key_func).from_data(DATA_C)
    )
```

### Pattern 2: Filtering with Three Models

```python
.where_multi(lambda a, b, c: is_valid_combination(a, b, c))
```

### Pattern 3: Sum Over One Dimension

```python
# For each A and B, sum over all C
for a in DATA_A:
    for b in DATA_B:
        expr = LXLinearExpression().add_multi_term(
            decision,
            coeff=lambda a_var, b_var, c_var: 1.0,
            where=lambda a_var, b_var, c_var, current_a=a, current_b=b:
                a_var.id == current_a.id and b_var.id == current_b.id
        )
```

### Pattern 4: Sum Over Two Dimensions

```python
# For each A, sum over all B and C
for a in DATA_A:
    expr = LXLinearExpression().add_multi_term(
        decision,
        coeff=lambda a_var, b_var, c_var: 1.0,
        where=lambda a_var, b_var, c_var, current_a=a: a_var.id == current_a.id
    )
```

## Extensions and Variations

This basic timetabling model can be extended with:

1. **Soft Constraints**: Teacher preferences, time preferences (addressed in Step 3)
2. **Multiple Buildings**: Add building as a 4th dimension
3. **Resource Constraints**: Labs, equipment, projectors
4. **Consecutive Periods**: Some lectures must be in consecutive timeslots
5. **Balancing**: Distribute lectures evenly across the week
6. **Teacher Availability**: Some teachers only available on certain days

## Next Steps

After completing Step 1, proceed to:

- **Step 2**: Add SQLite database integration to store and retrieve schedules
- **Step 3**: Add teacher preferences using goal programming with priority levels

## See Also

- **Example 02 (Driver Scheduling)**: 2D multi-model indexing example
- **Example 05 (CP-SAT Assignment)**: Alternative solver for scheduling problems
- **Example 11 (Goal Programming)**: Multi-objective optimization foundation

## Troubleshooting

### No Feasible Solution Found

If the model returns infeasible:

1. **Reduce lecture count**: Too many lectures for available timeslots
2. **Add classrooms**: Not enough rooms to avoid conflicts
3. **Check classroom capacities**: Some classes may not fit in any room
4. **Verify data consistency**: Ensure all references (teacher_id, class_id, etc.) are valid

### Slow Solving

If the model takes too long:

1. **Use CP-SAT solver**: Better for scheduling problems (`solver_to_use = "cpsat"`)
2. **Add symmetry breaking**: Fix some lectures to specific times
3. **Reduce problem size**: Start with fewer lectures/classes/timeslots

---

**Tutorial Step 1 Complete!**

You've learned how to build a basic timetabling model with 3D multi-model indexing. Now move on to Step 2 to add database integration.
