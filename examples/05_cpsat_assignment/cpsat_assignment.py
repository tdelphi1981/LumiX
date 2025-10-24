"""Worker-Task Assignment Problem with CP-SAT Solver.

This example demonstrates OR-Tools CP-SAT solver integration with LumiX for
combinatorial optimization, specifically solving an assignment problem with
integer variables and capacity constraints.

Problem Description:
    Assign tasks to workers to minimize total cost while satisfying:
        - Each task must be assigned to exactly one worker
        - Each worker cannot exceed their maximum task capacity
        - All assignments must respect integer/binary variable requirements

Mathematical Formulation:
    Minimize:
        sum(assignment_cost[w,t] * assignment[w,t] for all worker-task pairs)

    Subject to:
        - Task coverage: sum(assignment[w,t] for all w) == 1 for each task t
        - Worker capacity: sum(assignment[w,t] for all t) <= max_tasks[w] for each worker w
        - Binary variables: assignment[w,t] ∈ {0, 1}

Key Features Demonstrated:
    - **CP-SAT solver integration**: OR-Tools constraint programming solver
    - **Binary decision variables**: 0/1 assignment decisions
    - **Cartesian product indexing**: Variables indexed by (Worker × Task) pairs
    - **Multi-model expressions**: Coefficients from lambda functions over pairs
    - **Integer programming**: All values and variables are integers
    - **Combinatorial optimization**: Assignment problem structure

Why CP-SAT?:
    CP-SAT excels at:
        - Pure integer/binary problems (no continuous variables)
        - Assignment and scheduling problems
        - Combinatorial optimization with logical constraints
        - Problems where traditional LP solvers are inefficient
        - Fast solving for discrete decision problems

Use Cases:
    This pattern applies to:
        - Project resource allocation
        - Employee shift scheduling
        - Course-instructor assignment
        - Machine-job scheduling
        - Task delegation in teams
        - Warehouse-order fulfillment assignment

Learning Objectives:
    1. How to use CP-SAT solver with LumiX
    2. How to create binary variables for assignment problems
    3. How to use cartesian product indexing for worker-task pairs
    4. How to formulate coverage and capacity constraints
    5. How to interpret assignment problem solutions

See Also:
    - Example 02 (driver_scheduling): Multi-model indexing with dates
    - Example 01 (production_planning): Single-model indexing basics
    - sample_data.py: Data models and compatibility matrix
    - LumiX documentation: CP-SAT Solver Integration

Notes:
    CP-SAT only supports integer and binary variables. For problems with
    continuous variables, use solvers like OR-Tools LP, Gurobi, or CPLEX.
"""

from dataclasses import dataclass
from typing import Tuple

from lumix import LXConstraint, LXLinearExpression, LXModel, LXOptimizer, LXVariable
from lumix.indexing import LXCartesianProduct, LXIndexDimension

from sample_data import TASKS, WORKERS, Task, Worker, get_assignment_cost


solver_to_use = "cpsat"

# ==================== MODEL BUILDING ====================


def build_assignment_model() -> Tuple[LXModel, LXVariable]:
    """Build the worker-task assignment optimization model using CP-SAT.

    This function constructs an integer programming model to minimize the total
    cost of assigning tasks to workers while respecting task coverage requirements
    and worker capacity constraints.

    The model uses cartesian product indexing where binary assignment variables
    are indexed by (Worker, Task) pairs, eliminating manual index management.

    Returns:
        A tuple containing:
            - LXModel: The optimization model with variables, objective, and constraints
            - LXVariable: The assignment variable family for solution access

    Example:
        >>> model, assignment = build_assignment_model()
        >>> print(model.summary())
        >>> optimizer = LXOptimizer().use_solver("cpsat")
        >>> solution = optimizer.solve(model)
        >>> # Access assignments
        >>> for (w_id, t_id), value in solution.get_mapped(assignment).items():
        ...     if value > 0.5:  # Assignment is active
        ...         print(f"Worker {w_id} assigned to Task {t_id}")

    Notes:
        The data-driven approach means all coefficients are extracted from
        WORKERS and TASKS data using lambda functions. The model automatically
        adapts to changes in the data without code modifications.

        CP-SAT solver configuration options (time_limit, num_search_workers)
        can be passed when calling optimizer.solve().
    """

    # Decision Variable: Binary assignment (worker i assigned to task j)
    # This creates a variable for each (worker, task) pair
    assignment = (
        LXVariable[Tuple[Worker, Task], int]("assignment")
        .binary()
        .indexed_by_product(
            LXIndexDimension(Worker, lambda w: w.id).from_data(WORKERS),
            LXIndexDimension(Task, lambda t: t.id).from_data(TASKS),
        )
    )

    # Create model
    model = LXModel("worker_task_assignment").add_variable(assignment)

    # Objective: Minimize total assignment cost
    # Sum over all (worker, task) pairs: cost[w,t] * assignment[w,t]
    cost_expr = LXLinearExpression().add_multi_term(
        assignment,
        coeff=lambda w, t: get_assignment_cost(w, t),
    )
    model.minimize(cost_expr)

    # Constraint 1: Each task must be assigned to exactly one worker
    # For each task t: sum over workers(assignment[w,t]) == 1
    for task in TASKS:
        # Capture task.id in the lambda to avoid closure issues
        task_id = task.id
        model.add_constraint(
            LXConstraint[Task](f"task_coverage_{task_id}")
            .expression(
                LXLinearExpression().add_multi_term(
                    assignment,
                    coeff=lambda w, t, tid=task_id: 1 if t.id == tid else 0,
                )
            )
            .eq()
            .rhs(1)
        )

    # Constraint 2: Each worker cannot exceed their maximum task capacity
    # For each worker w: sum over tasks(assignment[w,t]) <= max_tasks[w]
    for worker in WORKERS:
        # Capture worker.id in the lambda to avoid closure issues
        worker_id = worker.id
        model.add_constraint(
            LXConstraint[Worker](f"worker_capacity_{worker_id}")
            .expression(
                LXLinearExpression().add_multi_term(
                    assignment,
                    coeff=lambda w, t, wid=worker_id: 1 if w.id == wid else 0,
                )
            )
            .le()
            .rhs(worker.max_tasks)
        )

    return model, assignment


# ==================== MAIN ====================


def main():
    """Run the complete worker-task assignment optimization example.

    This function orchestrates the entire optimization workflow:
        1. Display problem data (workers and tasks)
        2. Build the assignment optimization model
        3. Configure and create CP-SAT optimizer
        4. Solve the model with time limit and parallel workers
        5. Display and interpret the optimal assignment

    The workflow demonstrates best practices for CP-SAT usage:
        - Clear problem data presentation
        - Structured model building
        - Solver-specific configuration
        - Comprehensive result reporting

    Example:
        Run this example from the command line::

            $ python cpsat_assignment.py

        Or import and run programmatically::

            >>> from cpsat_assignment import main
            >>> main()

    Notes:
        This example uses CP-SAT solver parameters:
            - time_limit: Maximum solve time in seconds
            - num_search_workers: Number of parallel search threads

        These parameters can be adjusted based on problem size and
        available computational resources.
    """

    print("=" * 70)
    print("LumiX Example: Worker-Task Assignment with CP-SAT")
    print("=" * 70)
    print()

    # Display problem data
    print("Workers:")
    print("-" * 70)
    for w in WORKERS:
        print(f"  {w.name:12s}: ${w.hourly_rate:2d}/hr, max {w.max_tasks} tasks")
    print()

    print("Tasks:")
    print("-" * 70)
    for t in TASKS:
        print(f"  {t.name:25s}: {t.duration_hours}h, priority {t.priority}/10")
    print()

    # Build model
    print("Building optimization model...")
    model, assignment = build_assignment_model()

    # Display model summary
    print(f"Model: {model.name}")
    print(f"  Variables: {len(model.variables)} families")
    print(f"  Constraints: {len(model.constraints)}")
    print()

    # Create optimizer with CP-SAT
    print("Creating optimizer with CP-SAT solver...")
    optimizer = LXOptimizer()
    optimizer.use_solver(solver_to_use)
    print("  Solver: OR-Tools CP-SAT (constraint programming)")
    print("  Note: CP-SAT only supports integer and binary variables")
    print()

    # Solve the model
    print("Solving...")
    try:
        solution = optimizer.solve(
            model,
            time_limit=10.0,  # 10 second time limit
            num_search_workers=4,  # Use 4 parallel workers
        )
        print()

        # Display results
        print("=" * 70)
        print("SOLUTION")
        print("=" * 70)

        if solution.is_optimal():
            print(f"Status: {solution.status.upper()}")
            print(f"Total Cost: ${solution.objective_value:.0f}")
            print(f"Solve Time: {solution.solve_time:.3f}s")
            if solution.gap is not None:
                print(f"Optimality Gap: {solution.gap*100:.2f}%")
            print()

            # Extract assignments from solution
            print("Optimal Assignment:")
            print("-" * 70)

            # Create lookup dictionaries
            worker_by_id = {w.id: w for w in WORKERS}
            task_by_id = {t.id: t for t in TASKS}

            # Track worker utilization
            worker_task_count = {w.id: 0 for w in WORKERS}
            total_hours = 0

            # Get assignments (indexed by (worker_id, task_id) tuples)
            assignments = solution.get_mapped(assignment)

            # Process each assignment
            for (worker_id, task_id), value in assignments.items():
                if value > 0.5:  # Binary variable is "on"
                    worker = worker_by_id[worker_id]
                    task = task_by_id[task_id]
                    cost = get_assignment_cost(worker, task)

                    print(
                        f"  {worker.name:12s} → {task.name:25s} "
                        f"({task.duration_hours}h, ${cost:3d})"
                    )

                    worker_task_count[worker_id] += 1
                    total_hours += task.duration_hours

            print()
            print("Worker Utilization:")
            print("-" * 70)
            for worker in WORKERS:
                tasks_assigned = worker_task_count[worker.id]
                utilization = (tasks_assigned / worker.max_tasks) * 100
                print(
                    f"  {worker.name:12s}: {tasks_assigned}/{worker.max_tasks} tasks "
                    f"({utilization:5.1f}% capacity)"
                )

            print()
            print(f"Total Project Hours: {total_hours}h")

            # Show why CP-SAT is good for this problem
            print()
            print("Why CP-SAT?")
            print("-" * 70)
            print("  ✓ Pure integer/binary problem (no continuous variables)")
            print("  ✓ Combinatorial optimization (assignment problem)")
            print("  ✓ Fast for this problem size and structure")
            print("  ✓ Can easily add CP-specific constraints (e.g., AllDifferent)")

        else:
            print(f"No optimal solution found. Status: {solution.status}")
            print()
            if solution.status == "infeasible":
                print("Possible reasons:")
                print("  - Not enough workers to cover all tasks")
                print("  - Worker capacity constraints too tight")

    except ImportError as e:
        print(f"ERROR: {e}")
        print("\nPlease install OR-Tools:")
        print("  pip install ortools")
    except ValueError as e:
        print(f"ERROR: {e}")
        print("\nNote: CP-SAT only supports integer and binary variables.")
        print("For continuous variables, use 'ortools', 'gurobi', or 'cplex'.")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
