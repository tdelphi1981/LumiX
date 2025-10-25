# Step 3: Goal Programming with Teacher Preferences

## Overview

This is the final step in the High School Course Timetabling tutorial. It extends Step 2 by adding **teacher preferences** as soft constraints using LumiX's **goal programming** feature.

Teachers can express preferences like "I want Tuesdays off" or "I want to teach Math on Monday Period 1", and the optimization tries to satisfy these preferences based on teacher seniority.

## What's New in Step 3

### Key Additions

1. **Teacher Seniority**: Teachers now have a `work_years` field
2. **Teacher Preferences**: Database stores teacher scheduling preferences
3. **Priority Calculation**: Priorities assigned based on years of service
4. **Goal Programming**: Preferences converted to soft constraints (goals)
5. **Mixed Optimization**: Hard constraints (must satisfy) + soft goals (minimize violations)
6. **True ORM Pattern**: Like Step 2, uses direct ORM queries instead of loading data into lists

### Why Use Goal Programming?

In real-world scheduling, **not all constraints are equally important**:

- **Hard constraints**: MUST be satisfied (e.g., no double-booking)
- **Soft constraints**: SHOULD be satisfied, but can be violated if necessary

**Goal programming** allows us to:
- Express preferences as soft constraints
- Prioritize preferences (senior teachers first)
- Find the "best compromise" solution
- Track which preferences were satisfied

## Teacher Preference Types

### 1. DAY_OFF Preference

Teacher wants a specific day completely free (no lectures scheduled).

**Example:**
- Dr. Smith wants Tuesday off for research

**Goal Formulation:**
```
Minimize: ∑(assignment[lecture, timeslot, classroom])
          for all timeslots on Tuesday,
          for all lectures taught by Dr. Smith

Target: 0 (no lectures on Tuesday)
```

### 2. SPECIFIC_TIME Preference

Teacher wants a specific lecture at a specific timeslot.

**Example:**
- Prof. Johnson wants "English for 9A" on Monday Period 1

**Goal Formulation:**
```
Constraint: assignment[English_9A, Monday_P1, any_classroom] = 1
Target: 1 (lecture is assigned to that timeslot)
```

## Priority Calculation

Priorities are based on teacher seniority (years of service):

| Work Years | Priority | Description |
|------------|----------|-------------|
| 15+ years  | Priority 1 | Senior teachers (highest priority) |
| 7-14 years | Priority 2 | Mid-level teachers |
| 0-6 years  | Priority 3 | Junior teachers (lowest priority) |

**Rationale:**
- Senior teachers have more experience and should be rewarded
- Fair and objective (based on measurable criteria)
- Helps with teacher retention and satisfaction

## Mathematical Formulation

### Hard Constraints (unchanged from Steps 1 & 2)

1. **Lecture Coverage**: Each lecture assigned exactly once
2. **Classroom Conflicts**: Max one lecture per classroom per timeslot
3. **Teacher Conflicts**: Teacher can't teach two lectures simultaneously
4. **Class Conflicts**: Class can't attend two lectures simultaneously
5. **Capacity**: Class must fit in assigned classroom

These constraints MUST all be satisfied.

### Soft Constraints (Goals - new in Step 3)

For each teacher preference, create a goal constraint:

**DAY_OFF Goal:**
```
Expression: ∑(assignment[l, t, r])
            for all lectures l taught by teacher,
            for all timeslots t on preferred day,
            for all classrooms r

Constraint: expression ≤ 0 (goal: no lectures that day)
Priority: Based on teacher's work_years
Weight: 1.0
```

**SPECIFIC_TIME Goal:**
```
Expression: ∑(assignment[specific_lecture, specific_timeslot, r])
            for all classrooms r

Constraint: expression = 1 (goal: assigned to that timeslot)
Priority: Based on teacher's work_years
Weight: 1.0
```

### Objective Function

Goal programming minimizes weighted deviations:

```
Minimize: ∑ (priority_weight[p] × goal_weight × deviation)
          for all goals

Where:
- priority_weight[1] = 10^6 (Priority 1 goals)
- priority_weight[2] = 10^5 (Priority 2 goals)
- priority_weight[3] = 10^4 (Priority 3 goals)
- goal_weight = 1.0 (can be customized per goal)
- deviation = amount by which goal is violated
```

This ensures higher-priority goals are satisfied first.

## Database Schema Extensions

### Extended Teachers Table

```sql
CREATE TABLE teachers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    work_years INTEGER NOT NULL DEFAULT 0  -- NEW: years of service
)
```

### New Teacher Preferences Table

```sql
CREATE TABLE teacher_preferences (
    id INTEGER PRIMARY KEY,
    teacher_id INTEGER NOT NULL,
    preference_type TEXT NOT NULL CHECK(preference_type IN ('DAY_OFF', 'SPECIFIC_TIME')),
    day_of_week INTEGER,           -- For DAY_OFF (0=Mon, 4=Fri)
    lecture_id INTEGER,            -- For SPECIFIC_TIME
    timeslot_id INTEGER,           -- For SPECIFIC_TIME
    description TEXT,              -- Human-readable description
    FOREIGN KEY (teacher_id) REFERENCES teachers(id),
    FOREIGN KEY (lecture_id) REFERENCES lectures(id),
    FOREIGN KEY (timeslot_id) REFERENCES timeslots(id)
)
```

## Running the Example

### Step 1: Populate the Database

```bash
cd tutorials/timetabling/step3_goal_programming
python sample_data.py
```

**Output:**
```
Creating database schema...
Clearing existing data...
Inserting teachers with seniority...
  Dr. Smith: 15 years → Priority 1
  Prof. Johnson: 10 years → Priority 2
  Ms. Williams: 5 years → Priority 3
  Mr. Brown: 20 years → Priority 1
  Dr. Davis: 3 years → Priority 3

Inserting classrooms...
Inserting school classes...
Inserting subjects...
Inserting timeslots...
Inserting lectures...

Inserting teacher preferences...
  [P1] Dr. Smith: wants Tuesday off
  [P1] Dr. Smith: wants Mathematics 9A on Monday Period 1
  [P2] Prof. Johnson: wants Wednesday off
  [P3] Ms. Williams: wants Thursday off
  [P1] Mr. Brown: wants Friday off
  [P1] Mr. Brown: wants Chemistry 10A on Monday Period 2
  [P3] Dr. Davis: wants History 9A on Friday Period 1

============================================================
Database populated successfully!
============================================================
  Teachers:    5
  Classrooms:  4
  Classes:     4
  Subjects:    5
  Lectures:    20
  Timeslots:   30 (5 days × 6 periods)
  Preferences: 7

Priority Distribution:
  Priority 1 (15+ years): 2 teachers → High priority goals
  Priority 2 (7-14 years): 1 teacher → Medium priority goals
  Priority 3 (0-6 years):  2 teachers → Low priority goals
============================================================
```

### Step 2: Run the Optimization

```bash
python timetabling_goals.py
```

The program will:
1. Query data from database using ORM (on-demand, not pre-loading into lists)
2. Build hard constraints (basic timetabling) using direct ORM queries
3. Add soft goal constraints (teacher preferences with priorities) using ORM filtering
4. Solve using goal programming
5. Display teacher timetables
6. Analyze which preferences were satisfied

## Expected Output

```
================================================================================
LumiX Tutorial: High School Course Timetabling - Step 3
================================================================================

This example demonstrates:
  ✓ SQLAlchemy ORM with goal programming
  ✓ LumiX's from_model(session) for direct database querying
  ✓ Priority-based optimization (seniority determines priority)
  ✓ Mixed hard constraints + soft goals
  ✓ Preference satisfaction analysis

Building course timetabling model with goal programming...
  Using LumiX's from_model() for direct database querying
  Loaded 5 teachers
  Loaded 4 classrooms
  Loaded 4 classes
  Loaded 20 lectures
  Loaded 30 timeslots
  Loaded 7 teacher preferences

  Adding hard constraints...
    - Lecture coverage constraints
    - Classroom conflict constraints
    - Teacher conflict constraints
    - Class conflict constraints

  Adding soft goal constraints (teacher preferences)...
    [P1] Dr. Smith: wants Tuesday off (goal: 0 lectures)
    [P1] Dr. Smith: wants Mathematics 9A on Monday Period 1
    [P2] Prof. Johnson: wants Wednesday off (goal: 0 lectures)
    [P3] Ms. Williams: wants Thursday off (goal: 0 lectures)
    [P1] Mr. Brown: wants Friday off (goal: 0 lectures)
    [P1] Mr. Brown: wants Chemistry 10A on Monday Period 2
    [P3] Dr. Davis: wants History 9A on Friday Period 1

Model built successfully!
  Hard constraints: 620
  Soft goals: 7
  Total constraints: 627

Preparing goal programming...
Solving with ortools (goal programming mode)...

================================================================================
TIMETABLING SOLUTION WITH GOAL PROGRAMMING
================================================================================
Status: optimal
Objective value: 0.0012

[Teacher timetables displayed here...]

================================================================================
GOAL SATISFACTION ANALYSIS
================================================================================

Priority 1 (Senior teachers: 15+ years):
--------------------------------------------------------------------------------
  ✓ SATISFIED: Dr. Smith wants Tuesday off (deviation: 0 lectures)
  ✓ SATISFIED: Dr. Smith wants Mathematics 9A on Monday Period 1 (deviation: 0.00)
  ✓ SATISFIED: Mr. Brown wants Friday off (deviation: 0 lectures)
  ✓ SATISFIED: Mr. Brown wants Chemistry 10A on Monday Period 2 (deviation: 0.00)

Priority 1 Summary: 4/4 preferences satisfied

Priority 2 (Mid-level teachers: 7-14 years):
--------------------------------------------------------------------------------
  ✓ SATISFIED: Prof. Johnson wants Wednesday off (deviation: 0 lectures)

Priority 2 Summary: 1/1 preferences satisfied

Priority 3 (Junior teachers: 0-6 years):
--------------------------------------------------------------------------------
  ✗ NOT SATISFIED: Ms. Williams wants Thursday off (deviation: 2 lectures)
  ✗ NOT SATISFIED: Dr. Davis wants History 9A on Friday Period 1 (deviation: 1.00)

Priority 3 Summary: 0/2 preferences satisfied

Saving solution to database...
  Saved 20 schedule assignments

================================================================================
Tutorial Step 3 Complete!
================================================================================

What's new in Step 3:
  → SQLAlchemy ORM models with teacher preferences
  → from_model(session) instead of from_data()
  → Teacher preferences as soft goal constraints
  → Priority levels based on teacher seniority (work years)
  → Goal programming: minimize preference violations
  → Comprehensive goal satisfaction analysis

ORM Benefits:
  ✓ No manual SQL queries
  ✓ IDE autocomplete for model attributes
  ✓ Automatic foreign key validation
  ✓ Type-safe database operations

Key Insights:
  • Senior teachers' preferences are prioritized
  • Hard constraints always satisfied
  • Soft goals minimized based on priority
  • Trade-offs visible in goal satisfaction report
```

## Key LumiX Concepts

### 1. Marking Constraints as Goals

Convert a constraint to a goal with priority:

```python
model.add_constraint(
    LXConstraint("goal_name")
    .expression(expr)
    .le()  # or .eq() or .ge()
    .rhs(target_value)
    .as_goal(priority=1, weight=1.0)  # Mark as goal
)
```

### 2. Setting Goal Mode

Tell the model to use goal programming:

```python
model.set_goal_mode("weighted")  # Weighted sum approach
```

### 3. Preparing Goal Programming

Transform goals before solving:

```python
model.prepare_goal_programming()  # Must call before solving
```

This automatically:
- Creates deviation variables (positive and negative)
- Relaxes goal constraints
- Builds the weighted objective function

### 4. Analyzing Goal Satisfaction

Check which goals were achieved:

```python
# Check if a goal was satisfied
satisfied = solution.is_goal_satisfied("goal_name", tolerance=1e-6)

# Get deviation values
deviations = solution.get_goal_deviations("goal_name")
pos_dev = deviations["pos"]  # Positive deviation
neg_dev = deviations["neg"]  # Negative deviation
```

## Implementation Patterns

### Pattern 1: DAY_OFF Goal (with ORM)

```python
# Goal: Minimize assignments on a specific day for a teacher
# Query data using ORM filtering (not list comprehensions)
day_timeslot_ids = [
    ts.id for ts in session.query(TimeSlot).filter_by(day_of_week=preferred_day).all()
]
teacher_lecture_ids = [
    lec.id for lec in session.query(Lecture).filter_by(teacher_id=teacher.id).all()
]

expr = LXLinearExpression().add_multi_term(
    assignment,
    coeff=lambda lec, ts, room: 1.0,
    where=lambda lec, ts, room, t_lec_ids=teacher_lecture_ids, d_slot_ids=day_timeslot_ids: (
        lec.id in t_lec_ids and
        ts.id in d_slot_ids
    )
)

model.add_constraint(
    LXConstraint(f"day_off_teacher_{teacher.id}")
    .expression(expr)
    .le()
    .rhs(0)  # Target: 0 lectures that day
    .as_goal(priority=priority, weight=1.0)
)
```

### Pattern 2: SPECIFIC_TIME Goal (with ORM)

```python
# Goal: Assign specific lecture to specific timeslot
expr = LXLinearExpression().add_multi_term(
    assignment,
    coeff=lambda lec, ts, room: 1.0,
    where=lambda lec, ts, room, target_lec=pref.lecture_id, target_ts=pref.timeslot_id: (
        lec.id == target_lec and
        ts.id == target_ts
    )
)

model.add_constraint(
    LXConstraint(f"specific_time_lecture_{lecture_id}")
    .expression(expr)
    .eq()
    .rhs(1)  # Target: assigned to that timeslot
    .as_goal(priority=priority, weight=1.0)
)

# Query lecture and timeslot details using ORM (for display)
lecture = session.query(Lecture).filter_by(id=pref.lecture_id).first()
timeslot = session.query(TimeSlot).filter_by(id=pref.timeslot_id).first()
```

### Pattern 3: ORM Querying Pattern

Step 3 uses the same ORM pattern as Step 2 - **no pre-loading data into lists**:

```python
# ❌ DON'T: Load everything into lists (old approach)
teachers = session.query(Teacher).all()
lectures = session.query(Lecture).all()
timeslots = session.query(TimeSlot).all()

# ✓ DO: Query on-demand when needed (ORM pattern)
for teacher in session.query(Teacher).all():
    # Query only this teacher's lectures using ORM filtering
    teacher_lecture_ids = [
        lec.id for lec in session.query(Lecture).filter_by(teacher_id=teacher.id).all()
    ]

    for timeslot in session.query(TimeSlot).all():
        # Use the filtered data in constraints
        expr = LXLinearExpression().add_multi_term(...)
```

**Benefits:**
- More efficient memory usage
- Demonstrates proper ORM usage
- Follows SQLAlchemy best practices
- Consistent with Step 2

### Pattern 4: Priority Calculation

```python
def calculate_priority(work_years: int) -> int:
    """Calculate priority from seniority."""
    if work_years >= 15:
        return 1  # Highest priority
    elif work_years >= 7:
        return 2
    else:
        return 3  # Lowest priority
```

## Key Learnings

### 1. Goal Programming Workflow

The goal programming workflow in LumiX:

1. **Build model** with hard constraints (as usual)
2. **Add goals** using `.as_goal(priority, weight)`
3. **Set mode**: `model.set_goal_mode("weighted")`
4. **Prepare**: `model.prepare_goal_programming()`
5. **Solve**: `optimizer.solve(model)`
6. **Analyze**: Check goal satisfaction in solution

### 2. Priority Matters

Higher-priority goals dominate lower-priority goals:
- Priority 1 goals are satisfied first (if possible)
- Priority 2 goals considered only if P1 goals are met
- Priority 3 goals get lowest attention

In our example:
- **All Priority 1 goals satisfied** (senior teachers happy)
- **All Priority 2 goals satisfied** (mid-level teachers happy)
- **Priority 3 goals partially violated** (junior teachers get what's left)

### 3. Trade-offs Are Explicit

Goal programming makes trade-offs visible:
- Which preferences were satisfied
- Which preferences were violated
- By how much each goal was missed

This transparency helps explain scheduling decisions.

### 4. ORM Pattern Consistency

Step 3 maintains the same ORM pattern as Step 2:
- **No pre-loading**: Data is queried on-demand, not loaded into lists upfront
- **Direct queries**: Uses `session.query()` throughout the code
- **ORM filtering**: Uses `.filter_by()` for targeted queries
- **Type safety**: Leverages SQLAlchemy's type system

This consistency makes it easier to learn and maintain the codebase.

### 5. Hard vs. Soft Constraints

Understanding the difference:

| Type | Description | Example | Violation |
|------|-------------|---------|-----------|
| **Hard** | Must be satisfied | No double-booking | Infeasible |
| **Soft (Goal)** | Should be satisfied | Teacher wants Tuesday off | Penalized |

Goal programming lets you mix both types effectively.

## Extensions and Variations

### 1. Custom Weights Within Priority

Give more important preferences higher weights:

```python
# Important preference
.as_goal(priority=2, weight=2.0)

# Less important preference
.as_goal(priority=2, weight=0.5)
```

Both at same priority level, but weighted differently.

### 2. Student Preferences

Add student/class preferences:

```sql
CREATE TABLE class_preferences (
    id INTEGER PRIMARY KEY,
    class_id INTEGER NOT NULL,
    preference_type TEXT,
    -- Similar structure to teacher_preferences
);
```

### 3. Classroom Preferences

Prefer specific subjects in specific rooms:

```python
# Preference: Physics in Lab A
.as_goal(priority=2, weight=1.0)
```

### 4. Balancing Workload

Add goals to balance lectures across days:

```python
# Goal: Equal distribution across days for each teacher
# Target: lectures_per_week / 5 lectures per day
```

### 5. Sequential Goal Programming

Use true lexicographic optimization (future LumiX feature):

```python
model.set_goal_mode("sequential")
# Solves Priority 1, fixes result, then solves Priority 2, etc.
```

## Common Challenges

### Challenge 1: Conflicting Preferences

**Problem:** Two senior teachers both want Tuesday off, but that's infeasible.

**Solution:**
- Goal programming finds best compromise
- One or both might get partial satisfaction
- Satisfaction report shows which goals were violated

### Challenge 2: Over-Constraining

**Problem:** Too many high-priority preferences make the problem infeasible.

**Solution:**
- Review preferences for necessity
- Use different priority levels
- Lower weights for less critical preferences

### Challenge 3: Interpreting Deviations

**Problem:** What does "deviation = 2" mean for a DAY_OFF goal?

**Answer:**
- For DAY_OFF: deviation = number of lectures on that day
- For SPECIFIC_TIME: deviation = 0 (satisfied) or 1 (not satisfied)

### Challenge 4: All Goals Satisfied

**Problem:** If all goals are satisfied, did we set priorities correctly?

**Analysis:**
- Problem might be under-constrained
- Add more preferences to test prioritization
- Or celebrate - the schedule is very good!

## Troubleshooting

### No Feasible Solution

```
❌ No feasible solution found!
```

**Causes:**
- Hard constraints are too restrictive
- Even with goals relaxed, still infeasible

**Solutions:**
- Check hard constraints
- Increase classrooms, timeslots, or teachers
- Review lecture assignments

### Goal Programming Not Applied

```
Warning: Model has goals but prepare_goal_programming() not called
```

**Solution:**
```python
model.set_goal_mode("weighted")
model.prepare_goal_programming()  # Don't forget this!
solution = optimizer.solve(model)
```

### All Goals Violated

**Possible Causes:**
- Preferences are impossible to satisfy together
- Weights/priorities set incorrectly
- Model overconstrained

**Solution:**
- Review preference feasibility
- Lower priority for some goals
- Reduce number of preferences

## Next Steps

Congratulations! You've completed the High School Course Timetabling tutorial. You now know how to:

1. **Build complex scheduling models** with multi-dimensional indexing
2. **Integrate databases** for persistent data storage
3. **Use goal programming** for multi-objective optimization
4. **Prioritize preferences** based on meaningful criteria
5. **Analyze solutions** to understand trade-offs

### Further Exploration

- Try adding your own preference types
- Experiment with different priority schemes
- Add more teachers and classes
- Implement student preferences
- Create a web interface for the scheduler

### Related LumiX Features

- **Scenario Analysis**: Compare different preference configurations
- **Sensitivity Analysis**: How sensitive is the solution to priorities?
- **What-If Analysis**: What if we add another teacher?

## See Also

- **Step 1**: Basic timetabling with Python lists
- **Step 2**: Database integration
- **Example 11 (Goal Programming)**: Goal programming fundamentals
- **LumiX Documentation**: Goal Programming guide

---

**Tutorial Complete!**

You've mastered the complete workflow from basic optimization to advanced goal programming with database integration. These patterns apply to many real-world scheduling and resource allocation problems.
