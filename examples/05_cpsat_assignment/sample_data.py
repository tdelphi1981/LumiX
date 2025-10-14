"""Sample data for CP-SAT worker-task assignment example."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class Worker:
    """Represents a worker with skills and availability."""
    id: int
    name: str
    hourly_rate: int  # Integer cost (dollars per hour)
    max_tasks: int  # Maximum number of tasks this worker can handle


@dataclass
class Task:
    """Represents a task that needs to be completed."""
    id: int
    name: str
    duration_hours: int  # Integer duration
    priority: int  # Higher priority = more important (1-10)


@dataclass
class Assignment:
    """Represents the cost/compatibility of assigning a worker to a task."""
    worker_id: int
    task_id: int
    skill_penalty: int  # Additional cost if worker is not ideally suited (0-50)

    def total_cost(self, worker: Worker, task: Task) -> int:
        """Calculate total cost of this assignment."""
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
    """
    Get the total cost of assigning a worker to a task.

    Args:
        worker: Worker to assign
        task: Task to be completed

    Returns:
        Total cost (base cost + skill penalty)
    """
    penalty = ASSIGNMENT_PENALTIES.get((worker.id, task.id), 50)  # Default high penalty
    base_cost = worker.hourly_rate * task.duration_hours
    return base_cost + penalty
