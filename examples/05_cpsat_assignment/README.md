# CP-SAT Assignment Example

## Overview

This example demonstrates using **OR-Tools CP-SAT** (Constraint Programming) solver with LumiX for combinatorial optimization problems. CP-SAT excels at pure integer and binary problems like assignment, scheduling, and routing.

## Problem Description

Assign tasks to workers to minimize total cost while respecting constraints:
- Each task must be assigned to exactly one worker
- Each worker has a maximum number of tasks they can handle
- Assignment costs vary based on worker-task compatibility

### Real-World Context

This assignment problem pattern appears in:
- **Project Management**: Assigning tasks to team members
- **Manufacturing**: Assigning jobs to machines
- **Healthcare**: Assigning patients to doctors or nurses
- **Education**: Assigning students to advisors or projects
- **Cloud Computing**: Assigning workloads to servers
- **Transportation**: Assigning deliveries to drivers

## Mathematical Formulation

**Decision Variables:**
- `assignment[w,t]`: Binary variable = 1 if worker `w` is assigned to task `t`, 0 otherwise

**Objective Function:**
```
Minimize: ∑∑(cost[w,t] × assignment[w,t]) for all workers w and tasks t
```

**Constraints:**
```
Task coverage:      ∑ assignment[w,t] = 1         for each task t (sum over workers)
                    w
                    Each task assigned to exactly one worker

Worker capacity:    ∑ assignment[w,t] ≤ max[w]    for each worker w (sum over tasks)
                    t
                    Worker can't exceed capacity

Binary:             assignment[w,t] ∈ {0, 1}      for all w,t
```

Where `cost[w,t] = hourly_rate[w] × duration[t]` with adjustments for skill match.

## Key Concepts

### 1. CP-SAT Solver

**What is CP-SAT?**
- **Constraint Programming**: Different paradigm from Linear Programming
- **SAT**: Satisfiability - finding assignments that satisfy all constraints
- **Hybrid**: Combines CP, SAT, and MIP techniques
- **Specialized**: Excellent for combinatorial problems

**When to Use CP-SAT:**
- ✓ Pure integer/binary variables (no continuous variables)
- ✓ Assignment, scheduling, routing problems
- ✓ Logical constraints (AllDifferent, Circuit, Cumulative)
- ✓ Small to medium-sized combinatorial problems
- ✗ Continuous variables (use LP/MIP solvers instead)
- ✗ Very large linear programs (use Simplex/Interior Point)

### 2. Binary Assignment Variables

Multi-indexed binary variables for (worker, task) pairs:

```python
assignment = (
    LXVariable[Tuple[Worker, Task], int]("assignment")
    .binary()  # CP-SAT requires integer variables
    .indexed_by_product(
        LXIndexDimension(Worker, lambda w: w.id).from_data(WORKERS),
        LXIndexDimension(Task, lambda t: t.id).from_data(TASKS)
    )
)
```

### 3. Equality Constraints

Each task assigned to **exactly one** worker:

```python
model.add_constraint(
    LXConstraint[Task](f"task_coverage_{task.id}")
    .expression(expr)
    .eq()  # Equality constraint
    .rhs(1)  # Exactly 1
)
```

### 4. Integer Costs

CP-SAT works best with integer coefficients:

```python
def get_assignment_cost(worker: Worker, task: Task) -> int:
    base_cost = worker.hourly_rate * task.duration_hours
    # Skill matching bonus/penalty
    if task.required_skill in worker.skills:
        return int(base_cost * 0.8)  # 20% discount for skill match
    else:
        return int(base_cost * 1.2)  # 20% penalty for mismatch
```

### 5. CP-SAT Solver Options

```python
solution = optimizer.solve(
    model,
    time_limit=10.0,           # Maximum solve time in seconds
    num_search_workers=4,      # Parallel search threads
    log_search_progress=True   # Display search progress
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
cd examples/05_cpsat_assignment
python cpsat_assignment.py
```

## Expected Output

```
======================================================================
LumiX Example: Worker-Task Assignment with CP-SAT
======================================================================

Workers:
----------------------------------------------------------------------
  Alice       : $50/hr, max 3 tasks
  Bob         : $40/hr, max 4 tasks
  Charlie     : $60/hr, max 2 tasks
  Diana       : $45/hr, max 3 tasks

Tasks:
----------------------------------------------------------------------
  Database Migration       : 8h, priority 9/10
  API Development          : 12h, priority 8/10
  UI Redesign              : 6h, priority 7/10
  Testing & QA             : 10h, priority 8/10
  Documentation            : 4h, priority 5/10
  Code Review              : 5h, priority 6/10

Building optimization model...
Model: worker_task_assignment
  Variables: 1 family (24 binary variables from 4 workers × 6 tasks)
  Constraints: 10 (6 task coverage + 4 worker capacity)

Creating optimizer with CP-SAT solver...
  Solver: OR-Tools CP-SAT (constraint programming)
  Note: CP-SAT only supports integer and binary variables

Solving...

======================================================================
SOLUTION
======================================================================
Status: OPTIMAL
Total Cost: $1,680
Solve Time: 0.123s
Optimality Gap: 0.00%

Optimal Assignment:
----------------------------------------------------------------------
  Alice        → Database Migration        (8h, $320)
  Alice        → UI Redesign               (6h, $240)
  Bob          → API Development           (12h, $384)
  Bob          → Code Review               (5h, $160)
  Charlie      → Testing & QA              (10h, $480)
  Diana        → Documentation             (4h, $144)

Worker Utilization:
----------------------------------------------------------------------
  Alice       : 2/3 tasks ( 66.7% capacity)
  Bob         : 2/4 tasks ( 50.0% capacity)
  Charlie     : 1/2 tasks ( 50.0% capacity)
  Diana       : 1/3 tasks ( 33.3% capacity)

Total Project Hours: 45h

Why CP-SAT?
----------------------------------------------------------------------
  ✓ Pure integer/binary problem (no continuous variables)
  ✓ Combinatorial optimization (assignment problem)
  ✓ Fast for this problem size and structure
  ✓ Can easily add CP-specific constraints (e.g., AllDifferent)
```

## Key Learnings

### 1. CP-SAT vs Linear Programming

| Feature | CP-SAT | LP/MIP |
|---------|--------|--------|
| **Variable Types** | Integer, Binary | Continuous, Integer, Binary |
| **Best For** | Combinatorial problems | Resource allocation, continuous optimization |
| **Constraints** | Logical, global constraints | Linear inequalities |
| **Algorithm** | Search + Propagation | Simplex, Interior Point, Branch & Bound |
| **Scaling** | Small-medium | Medium-large |
| **Speed** | Fast for combinatorial | Fast for continuous |

### 2. Assignment Problem Structure

Classic **bipartite matching** structure:
- Two sets: Workers and Tasks
- Binary decision: Assign or not
- Constraints link the two sets
- Sum constraints ensure coverage

### 3. Skill-Based Costing

Cost varies based on worker-task fit:
```python
if worker has required skill:
    cost = base_cost × 0.8  # Efficient assignment
else:
    cost = base_cost × 1.2  # Learning curve penalty
```

### 4. Capacity Constraints

Workers have limited capacity:
- Prevents overloading any worker
- Distributes workload
- Ensures feasibility

### 5. Integer Arithmetic

CP-SAT works best with integers:
- Costs in cents rather than dollars
- Hours as integers or scaled
- Avoids floating-point precision issues

## Common Patterns Demonstrated

### Pattern 1: Binary Assignment Matrix

```python
assignment = LXVariable[Tuple[A, B], int]("assignment").binary()
```

### Pattern 2: Exactly-One Constraint

```python
# Each B assigned to exactly one A
for b in B_SET:
    expr = LXLinearExpression().add_multi_term(
        assignment,
        coeff=lambda a, b_var: 1.0,
        where=lambda a, b_var, current_b=b: b_var.id == current_b.id
    )
    model.add_constraint(
        LXConstraint(f"coverage_{b.id}").expression(expr).eq().rhs(1)
    )
```

### Pattern 3: Capacity Constraint

```python
# Each A can handle at most max[a] items from B
for a in A_SET:
    expr = LXLinearExpression().add_multi_term(
        assignment,
        coeff=lambda a_var, b: 1.0,
        where=lambda a_var, b, current_a=a: a_var.id == current_a.id
    )
    model.add_constraint(
        LXConstraint(f"capacity_{a.id}").expression(expr).le().rhs(a.max_items)
    )
```

### Pattern 4: Cost Matrix

```python
cost_expr = LXLinearExpression().add_multi_term(
    assignment,
    coeff=lambda a, b: get_cost(a, b)
)
model.minimize(cost_expr)
```

## CP-SAT Special Features

### Global Constraints

CP-SAT supports powerful global constraints (not shown in this example):

```python
# AllDifferent: All variables must have different values
# Circuit: Variables form a Hamiltonian circuit (TSP)
# Cumulative: Resource usage over time
# NoOverlap: Intervals don't overlap (scheduling)
```

### Search Strategies

CP-SAT uses intelligent search strategies:
- Variable selection heuristics
- Value selection heuristics
- Constraint propagation
- Nogood learning

### Parallel Search

```python
solution = optimizer.solve(model, num_search_workers=8)
# Uses 8 parallel threads to explore search space
```

## Extensions and Variations

This pattern extends to:

1. **Generalized Assignment**: Tasks have different sizes, workers have different capacities
2. **Multi-Period**: Add time dimension for scheduling
3. **Precedence Constraints**: Some tasks must be completed before others
4. **Team Assignment**: Assign groups of workers to tasks
5. **Skill Requirements**: Multiple skills per task
6. **Preference Scores**: Optimize for worker preferences

## Classic Assignment Problem Variants

### 1. Hungarian Algorithm Problem

Each worker assigned to exactly one task, each task to exactly one worker:
```python
# Additional constraint: each worker assigned to exactly one task
for worker in WORKERS:
    expr = ...  # sum over tasks
    model.add_constraint(...eq().rhs(1))
```

### 2. Generalized Assignment Problem (GAP)

Tasks have sizes, workers have capacity limits (this example is GAP).

### 3. Quadratic Assignment Problem (QAP)

Assignment costs depend on proximity (facility location).

### 4. Bottleneck Assignment Problem

Minimize maximum assignment cost (min-max objective).

## Comparison with Linear Relaxation

### LP Relaxation

If we relax binary to continuous:
```python
.continuous().bounds(lower=0, upper=1)
```

- **Faster to solve** (polynomial time)
- **Fractional solutions** possible (worker 50% assigned to task)
- **Lower bound** on integer solution
- **Not practical** for assignment (need integer assignments)

### Integer Programming

Keep binary constraints:
```python
.binary()
```

- **Exact solutions** (worker fully assigned or not)
- **NP-hard** problem
- **Requires specialized solvers** (CP-SAT, CPLEX, Gurobi)
- **Practical** for real-world use

## Use Cases

1. **Project Management**: Assign tasks to team members
2. **Manufacturing**: Assign jobs to machines or production lines
3. **Logistics**: Assign deliveries to drivers or vehicles
4. **Healthcare**: Assign patients to doctors, nurses, or rooms
5. **Education**: Assign students to advisors, courses, or projects
6. **Cloud Computing**: Assign workloads to servers
7. **Call Centers**: Assign calls to agents

## Performance Considerations

### Problem Size

CP-SAT handles:
- **Small**: < 100 variables (instant)
- **Medium**: 100-10,000 variables (seconds to minutes)
- **Large**: > 10,000 variables (may be slow or require time limits)

### Improving Performance

1. **Tighter Bounds**: Reduce variable domains
2. **Redundant Constraints**: Add implied constraints to help propagation
3. **Search Hints**: Provide starting solutions
4. **Time Limits**: Set reasonable time limits
5. **Parallel Search**: Use multiple workers

## See Also

- **Example 02 (Driver Scheduling)**: Multi-model indexing with binary variables
- **Example 03 (Facility Location)**: Mixed-integer programming with Big-M
- **OR-Tools Documentation**: [CP-SAT Primer](https://developers.google.com/optimization/cp/cp_solver)
- **Hungarian Algorithm**: Classic O(n³) algorithm for assignment problems

## Files in This Example

- `cpsat_assignment.py`: Main optimization model and solution display
- `sample_data.py`: Data models (Worker, Task) and cost calculations
- `README.md`: This documentation file

## Next Steps

After understanding this example:

1. Add skill constraints (workers must have required skills)
2. Implement precedence constraints (task ordering)
3. Add time windows (tasks must be done in certain periods)
4. Implement worker preferences (soft constraints)
5. Try the Hungarian algorithm for comparison
6. Experiment with different CP-SAT search parameters
7. Add team-based assignments (groups of workers)
