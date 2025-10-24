"""Sample data classes for CP-SAT worker-task assignment example.

This module provides data models and sample data for the worker-task assignment
optimization example, demonstrating CP-SAT solver integration with LumiX for
combinatorial optimization problems.

Problem Description:
    An assignment problem where workers with different skills and hourly rates
    must be assigned to tasks with varying durations and priorities. Each worker
    has a maximum task capacity, and assignments have skill-based penalty costs
    reflecting worker-task compatibility.

Key Features:
    - Integer-only data (required for CP-SAT solver)
    - Worker capacity constraints
    - Task-worker compatibility matrix with skill penalties
    - Cost calculation combining base rates and skill penalties

Data Structure:
    - Workers: Individual contributors with hourly rates and task limits
    - Tasks: Work items with durations and priority levels
    - Assignment Penalties: Compatibility matrix defining skill-based costs

Use Cases:
    This data structure is ideal for modeling:
        - Project resource allocation
        - Skill-based task assignment
        - Workforce optimization
        - Team composition planning
        - Capacity-constrained scheduling

Example:
    Access worker and task data for optimization::

        from sample_data import WORKERS, TASKS, get_assignment_cost

        # Calculate assignment cost
        cost = get_assignment_cost(WORKERS[0], TASKS[0])
        print(f"Cost to assign {WORKERS[0].name} to {TASKS[0].name}: ${cost}")

Notes:
    All numeric values are integers to ensure compatibility with CP-SAT solver.
    In real applications, these dataclasses would be replaced with ORM models
    from frameworks like SQLAlchemy or Django ORM.

See Also:
    - cpsat_assignment.py: Main optimization model using this data
    - Example 02 (driver_scheduling): Similar multi-model indexing pattern
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class Worker:
    """Represents a worker with skills and availability.

    This class models a worker who can be assigned to tasks, with constraints
    on how many tasks they can handle simultaneously and their cost rate.

    Attributes:
        id: Unique identifier for the worker.
        name: Human-readable worker name.
        hourly_rate: Base cost per hour in dollars (integer for CP-SAT).
        max_tasks: Maximum number of tasks this worker can handle concurrently.

    Example:
        >>> worker = Worker(id=1, name="Alice", hourly_rate=25, max_tasks=3)
        >>> print(f"{worker.name} costs ${worker.hourly_rate}/hour")
        Alice costs $25/hour
        >>> print(f"Can handle up to {worker.max_tasks} tasks")
        Can handle up to 3 tasks

    Notes:
        The max_tasks constraint is enforced in the optimization model by
        limiting the sum of assignments for each worker across all tasks.
    """

    id: int
    name: str
    hourly_rate: int  # Integer cost (dollars per hour)
    max_tasks: int  # Maximum number of tasks this worker can handle


@dataclass
class Task:
    """Represents a task that needs to be completed.

    This class models a work item with specific duration and priority,
    to be assigned to exactly one worker in the optimization.

    Attributes:
        id: Unique identifier for the task.
        name: Human-readable task description.
        duration_hours: Time required to complete the task in hours (integer).
        priority: Importance ranking on scale of 1-10, where higher is more important.

    Example:
        >>> task = Task(id=1, name="Backend Development", duration_hours=8, priority=9)
        >>> print(f"{task.name}: {task.duration_hours} hours, priority {task.priority}/10")
        Backend Development: 8 hours, priority 9/10

    Notes:
        Priority values could be used to add soft constraints or objective
        penalties for unassigned high-priority tasks in extended formulations.
    """

    id: int
    name: str
    duration_hours: int  # Integer duration
    priority: int  # Higher priority = more important (1-10)


@dataclass
class Assignment:
    """Represents the cost/compatibility of assigning a worker to a task.

    This class captures the relationship between a specific worker and task,
    including any skill-based penalty costs that reflect how well-suited
    the worker is for that particular task.

    Attributes:
        worker_id: ID of the worker being assigned.
        task_id: ID of the task being assigned.
        skill_penalty: Additional cost if worker is not ideally suited (0-50).

    Example:
        >>> assignment = Assignment(worker_id=1, task_id=1, skill_penalty=0)
        >>> worker = Worker(id=1, name="Alice", hourly_rate=25, max_tasks=3)
        >>> task = Task(id=1, name="Backend Dev", duration_hours=8, priority=9)
        >>> total = assignment.total_cost(worker, task)
        >>> print(f"Total assignment cost: ${total}")
        Total assignment cost: $200

    Notes:
        Lower skill penalties indicate better worker-task compatibility.
        A penalty of 0 represents a perfect skill match.
    """

    worker_id: int
    task_id: int
    skill_penalty: int  # Additional cost if worker is not ideally suited (0-50)

    def total_cost(self, worker: Worker, task: Task) -> int:
        """Calculate total cost of this assignment.

        Computes the complete cost by combining the worker's hourly rate
        with the task duration and adding any skill-based penalty.

        Args:
            worker: The Worker instance being assigned.
            task: The Task instance being assigned.

        Returns:
            Total integer cost = (hourly_rate * duration) + skill_penalty.

        Example:
            >>> worker = Worker(id=1, name="Alice", hourly_rate=25, max_tasks=3)
            >>> task = Task(id=1, name="Backend", duration_hours=8, priority=9)
            >>> assignment = Assignment(worker_id=1, task_id=1, skill_penalty=10)
            >>> cost = assignment.total_cost(worker, task)
            >>> print(f"Cost: ${cost} = (${worker.hourly_rate} × {task.duration_hours}h) + ${assignment.skill_penalty}")
            Cost: $210 = ($25 × 8h) + $10

        Notes:
            This cost function is used as coefficients in the objective function
            of the assignment optimization model.
        """
        base_cost = worker.hourly_rate * task.duration_hours
        return base_cost + self.skill_penalty


# Sample workers
WORKERS = [
    Worker(1, "Alice", 25, 3),    # $25/hr, max 3 tasks
    Worker(2, "Bob", 20, 4),      # $20/hr, max 4 tasks
    Worker(3, "Charlie", 30, 2),  # $30/hr, max 2 tasks
    Worker(4, "Diana", 22, 3),    # $22/hr, max 3 tasks
]

# Sample tasks
TASKS = [
    Task(1, "Backend Development", 8, 9),
    Task(2, "Frontend Development", 6, 8),
    Task(3, "Database Optimization", 4, 7),
    Task(4, "API Design", 5, 8),
    Task(5, "Testing", 3, 6),
    Task(6, "Documentation", 2, 5),
    Task(7, "Code Review", 3, 7),
]

# Assignment compatibility matrix (skill penalties)
# Higher penalty = worker is less suited for the task
ASSIGNMENT_PENALTIES: Dict[tuple, int] = {
    # Alice: Good at backend, API design
    (1, 1): 0,   # Backend Development - perfect fit
    (1, 2): 20,  # Frontend - not ideal
    (1, 3): 10,  # Database - okay
    (1, 4): 5,   # API Design - good
    (1, 5): 15,  # Testing - not ideal
    (1, 6): 25,  # Documentation - not ideal
    (1, 7): 10,  # Code Review - okay

    # Bob: Jack of all trades, master of testing
    (2, 1): 15,  # Backend - okay
    (2, 2): 10,  # Frontend - good
    (2, 3): 15,  # Database - okay
    (2, 4): 10,  # API Design - good
    (2, 5): 0,   # Testing - perfect fit
    (2, 6): 10,  # Documentation - good
    (2, 7): 5,   # Code Review - very good

    # Charlie: Expert backend and database
    (3, 1): 0,   # Backend Development - perfect fit
    (3, 2): 30,  # Frontend - not suited
    (3, 3): 0,   # Database - perfect fit
    (3, 4): 10,  # API Design - good
    (3, 5): 20,  # Testing - not ideal
    (3, 6): 35,  # Documentation - not suited
    (3, 7): 15,  # Code Review - okay

    # Diana: Good at frontend and documentation
    (4, 1): 20,  # Backend - not ideal
    (4, 2): 0,   # Frontend - perfect fit
    (4, 3): 25,  # Database - not ideal
    (4, 4): 10,  # API Design - good
    (4, 5): 10,  # Testing - good
    (4, 6): 0,   # Documentation - perfect fit
    (4, 7): 8,   # Code Review - good
}


def get_assignment_cost(worker: Worker, task: Task) -> int:
    """Get the total cost of assigning a worker to a task.

    This function calculates the complete assignment cost by combining
    the worker's base hourly rate with the task duration and adding
    any skill-based compatibility penalty.

    Args:
        worker: Worker to assign to the task.
        task: Task to be completed by the worker.

    Returns:
        Total assignment cost as an integer. If no penalty is defined
        for this worker-task pair, uses default high penalty of 50.

    Example:
        >>> worker = WORKERS[0]  # Alice
        >>> task = TASKS[0]  # Backend Development
        >>> cost = get_assignment_cost(worker, task)
        >>> print(f"Cost: ${cost}")
        Cost: $200
        >>> # Alice is perfect for backend (penalty=0), so cost = 25*8 + 0 = 200

        >>> worker = WORKERS[0]  # Alice
        >>> task = TASKS[1]  # Frontend Development
        >>> cost = get_assignment_cost(worker, task)
        >>> print(f"Cost: ${cost}")
        Cost: $170
        >>> # Alice not ideal for frontend (penalty=20), so cost = 25*6 + 20 = 170

    Notes:
        If a worker-task pair is not in ASSIGNMENT_PENALTIES, the function
        returns a high default penalty (50) to discourage that assignment.
        This cost function is used directly in the objective function
        coefficients of the optimization model.
    """
    penalty = ASSIGNMENT_PENALTIES.get((worker.id, task.id), 50)  # Default high penalty
    base_cost = worker.hourly_rate * task.duration_hours
    return base_cost + penalty
